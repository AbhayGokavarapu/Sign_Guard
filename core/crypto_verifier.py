"""
Module 3 — Cryptographic verification (mandatory pyHanko path).

Uses pyHanko's validate_pdf_signature() for genuine CMS/PKCS#7 verification.
Fallback returns UNSUPPORTED — never silently marks a document valid.

Separates:
  1. Signed-byte integrity      (digest of signed bytes matches recorded value)
  2. Mathematical validity      (public-key signature over digest verifies)
  3. Certificate trust          (chain evaluation against trust store)
  4. Modification-policy        (DocMDP / FieldMDP permissions respected)
  5. Signer identity status     (derived from cert trust, NOT from #1-2 alone)
  6. Analysis completeness      (which checks ran / which failed)
"""

from __future__ import annotations

import hashlib, io, logging, re
import config
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Suppress verbose pyHanko / certvalidator logging
logging.getLogger("pyhanko").setLevel(logging.ERROR)
logging.getLogger("certvalidator").setLevel(logging.ERROR)
logging.getLogger("asn1crypto").setLevel(logging.ERROR)

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from cryptography.x509.oid import NameOID


# ── Data structures ────────────────────────────────────────────────────────

class IntegrityStatus:
    PASS    = "PASS"
    FAIL    = "FAIL"
    UNKNOWN = "UNKNOWN"      # could not be evaluated
    NA      = "NOT APPLICABLE"


class TrustStatus:
    TRUSTED        = "TRUSTED"
    SELF_SIGNED    = "SELF-SIGNED (untrusted)"
    UNKNOWN_ISSUER = "UNKNOWN ISSUER (untrusted)"
    NOT_EVALUATED  = "NOT EVALUATED"
    EXPIRED = "EXPIRED OR NOT YET VALID"


class ModpolicyStatus:
    COMPLIANT  = "COMPLIANT"
    VIOLATION  = "VIOLATION"
    UNKNOWN    = "UNKNOWN"


class IdentityStatus:
    ESTABLISHED     = "ESTABLISHED (trusted cert)"
    UNVERIFIED      = "UNVERIFIED (untrusted cert)"
    NOT_ESTABLISHED = "NOT ESTABLISHED"


@dataclass
class ByteRangeInfo:
    raw_values:         Optional[List[int]]   # [off1, len1, off2, len2]
    structurally_valid: bool
    covers_full_file:   bool
    covers_signed_rev:  bool
    validation_notes:   List[str] = field(default_factory=list)


@dataclass
class CertInfo:
    subject:        str
    issuer:         str
    serial:         str
    not_before:     str
    not_after:      str
    is_self_signed: bool
    is_test_cert:   bool
    key_algorithm:  str = "unknown"


@dataclass
class SigVerificationResult:
    sig_index:          int
    field_name:         str

    # Separated verification results
    integrity_status:   str    # IntegrityStatus constant
    math_valid:         Optional[bool]
    trust_status:       str    # TrustStatus constant
    modpolicy_status:   str    # ModpolicyStatus constant
    identity_status:    str    # IdentityStatus constant
    completeness:       str    # which checks ran

    # Details
    byte_range:         Optional[ByteRangeInfo]
    cert_info:          Optional[CertInfo]
    digest_alg:         str
    sig_alg:            str
    signing_time:       str
    signed_attrs_ok:    Optional[bool]
    details:            List[str] = field(default_factory=list)
    error:              Optional[str] = None
    modification_level: str = "UNKNOWN"
    revocation_status: str = "NOT CHECKED (offline)"
    timestamp_status: str = "NOT VALIDATED"
    timestamp_details: dict = field(default_factory=dict)
    coverage_level: str = "UNKNOWN"

    # Legacy compat helpers (used by dashboard/reporting)
    @property
    def integrity_ok(self) -> Optional[bool]:
        if self.integrity_status == IntegrityStatus.PASS:   return True
        if self.integrity_status == IntegrityStatus.FAIL:   return False
        return None

    @property
    def cert_trusted(self) -> Optional[bool]:
        if self.trust_status == TrustStatus.TRUSTED:        return True
        if self.trust_status in (TrustStatus.SELF_SIGNED,
                                 TrustStatus.UNKNOWN_ISSUER, TrustStatus.EXPIRED, "REVOKED"): return False
        return None

    @property
    def byte_range_valid(self) -> Optional[bool]:
        return self.byte_range.structurally_valid if self.byte_range else None

    @property
    def revision_covers_all(self) -> Optional[bool]:
        return self.byte_range.covers_full_file if self.byte_range else None

    @property
    def post_signing_mods(self) -> Optional[bool]:
        if self.modpolicy_status == ModpolicyStatus.VIOLATION: return True
        if self.modpolicy_status == ModpolicyStatus.COMPLIANT: return False
        return None


@dataclass
class CryptoReport:
    results:      List[SigVerificationResult]
    total_sigs:   int
    all_valid:    bool
    summary:      str
    pyhanko_used: bool
    byterange_analysis_available: bool = True
    total_discovered: int = 0


# ── Public API ─────────────────────────────────────────────────────────────

def verify(raw: bytes, trust_roots=None, skip_diff=False, crls=None, ocsps=None) -> CryptoReport:
    """
    Main entry point.  Returns a CryptoReport with per-signature results.
    Uses pyHanko when available; otherwise returns explicit UNSUPPORTED results.
    """
    if trust_roots is None and config.TRUST_ROOTS_FILE:
        from asn1crypto import x509 as asn1_x509
        with open(config.TRUST_ROOTS_FILE, 'rb') as root_file:
            trust_roots = [asn1_x509.Certificate.load(c.public_bytes(Encoding.DER))
                           for c in x509.load_pem_x509_certificates(root_file.read())]
    try:
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko.pdf_utils.reader import PdfFileReader
        results = _verify_with_pyhanko(raw, trust_roots=trust_roots, skip_diff=skip_diff, crls=crls, ocsps=ocsps)
        pyhanko_used = True
    except ImportError:
        results = _verify_no_pyhanko(raw)
        pyhanko_used = False

    if not results:
        return CryptoReport([], 0, False,
            "No cryptographic signatures found in this document.", pyhanko_used)

    all_valid = all(r.integrity_status == IntegrityStatus.PASS and
                    r.math_valid is True and r.byte_range is not None and
                    r.byte_range.structurally_valid and r.byte_range.covers_signed_rev and
                    r.coverage_level in ("ENTIRE_FILE", "ENTIRE_REVISION")
                    for r in results)
    summary   = _build_summary(results)
    discovered = len(results)
    if pyhanko_used:
        try:
            discovered = len(PdfFileReader(io.BytesIO(raw), strict=False).embedded_signatures)
        except Exception:
            pass
    return CryptoReport(results, len(results), all_valid and discovered == len(results), summary, pyhanko_used, total_discovered=discovered)


# ── ByteRange structural validation ───────────────────────────────────────

def validate_byte_range(raw: bytes, br: List[int]) -> ByteRangeInfo:
    """
    Thorough ByteRange structural validation.
    br = [off1, len1, off2, len2]  — the four integers from /ByteRange.
    """
    notes: List[str] = []
    total = len(raw)

    # 1. Must be exactly 4 non-negative integers
    if len(br) != 4:
        return ByteRangeInfo(br, False, False, False,
                             [f"Expected 4 values, got {len(br)}"])
    if any(not isinstance(v, int) for v in br):
        return ByteRangeInfo(br, False, False, False, ["Non-integer ByteRange values"])
    if any(v < 0 for v in br):
        return ByteRangeInfo(br, False, False, False, ["Negative ByteRange values"])

    off1, len1, off2, len2 = br

    # 2. Regions must be within file bounds
    if off1 + len1 > total or off2 + len2 > total:
        notes.append("ByteRange region extends beyond file end.")
        return ByteRangeInfo(br, False, False, False, notes)

    # 3. Ordering: off1 < off1+len1 <= off2 < off2+len2
    if not (off1 < off1 + len1 <= off2 < off2 + len2):
        notes.append("ByteRange regions are not in ascending, non-overlapping order.")
        return ByteRangeInfo(br, False, False, False, notes)

    # 4. off1 should be 0 (PDF spec §12.8.1)
    if off1 != 0:
        return ByteRangeInfo(br, False, False, False, ["ByteRange must start at offset 0."])

    # 5. The gap between region 1 and region 2 is the /Contents hex blob
    gap_start = off1 + len1
    gap_end   = off2
    gap_size  = gap_end - gap_start
    if gap_size <= 0:
        notes.append("No gap between ByteRange regions — /Contents may be missing.")
        return ByteRangeInfo(br, False, False, False, notes)
    notes.append(f"Signature contents gap: bytes {gap_start}–{gap_end} ({gap_size} bytes).")

    # 6. Covers full file?
    covers_full = (off2 + len2 == total)
    if not covers_full:
        notes.append(
            f"ByteRange ends at {off2+len2}, file is {total} bytes — "
            f"{total - (off2+len2)} trailing bytes not covered (incremental update likely)."
        )

    # 7. Covers a valid signed revision even if not the whole file
    end = off2 + len2
    covers_signed_rev = False
    try:
        from core.revision_analyzer import _discover_revisions_pymupdf
        revisions, _ = _discover_revisions_pymupdf(raw)
        boundary_matches = any(rev.is_signed and rev.end_offset == end for rev in revisions)
        from pyhanko.pdf_utils.reader import PdfFileReader
        reader=PdfFileReader(io.BytesIO(raw),strict=False)
        covers_signed_rev=boundary_matches and any(
            list(map(int,sig.sig_object['/ByteRange']))==br and
            sig.evaluate_signature_coverage().name in ('ENTIRE_FILE','ENTIRE_REVISION')
            for sig in reader.embedded_signatures)
    except Exception:
        pass
    gap = raw[gap_start:gap_end].strip()
    if not (gap.startswith(b"<") and gap.endswith(b">")):
        return ByteRangeInfo(br, False, False, False, ["Contents gap is not a PDF hex string."])

    if covers_full:
        notes.append("Signature covers the complete current document.")
    else:
        notes.append("Signature covers an earlier revision; later content is not signed.")

    return ByteRangeInfo(
        raw_values=br,
        structurally_valid=True,
        covers_full_file=covers_full,
        covers_signed_rev=covers_signed_rev,
        validation_notes=notes,
    )


# ── pyHanko verification path ─────────────────────────────────────────────

def _verify_with_pyhanko(raw: bytes, trust_roots=None, skip_diff=False, crls=None, ocsps=None) -> List[SigVerificationResult]:
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.pdf_utils.reader import PdfFileReader

    try:
        reader = PdfFileReader(io.BytesIO(raw), strict=False)
        embedded_sigs = reader.embedded_signatures
    except Exception as exc:
        return [SigVerificationResult(
            0, "unknown",
            IntegrityStatus.UNKNOWN, None,
            TrustStatus.NOT_EVALUATED, ModpolicyStatus.UNKNOWN,
            IdentityStatus.NOT_ESTABLISHED,
            "pyHanko reader failed — document may be malformed or corrupt",
            None, None, "unknown", "unknown", "", None,
            error=str(exc)
        )]

    if not embedded_sigs:
        return []

    from pyhanko_certvalidator import ValidationContext
    from core.certificate_lifecycle import load_evidence, revocation_result, timestamp_result
    configured_crls,configured_ocsps=load_evidence()
    crls=list(crls or [])+configured_crls;ocsps=list(ocsps or [])+configured_ocsps
    evidence_supplied=bool(crls or ocsps)
    context = ValidationContext(trust_roots=list(trust_roots or []),
        other_certs=[c for c in (trust_roots or []) if hasattr(c,"subject")], allow_fetching=False,
        crls=crls,ocsps=ocsps,revocation_mode='require' if evidence_supplied else 'soft-fail')
    out: List[SigVerificationResult] = []
    for idx, sig in enumerate(embedded_sigs[:config.MAX_SIGNATURES]):   # max 10 sigs
        try:
            document_timestamp=str(sig.sig_object.get('/Type',''))=='/DocTimeStamp'
            if document_timestamp:
                from pyhanko.sign.validation import validate_pdf_timestamp
                status=validate_pdf_timestamp(sig,validation_context=context,skip_diff=skip_diff)
            else:
                status = validate_pdf_signature(sig, signer_validation_context=context,
                    ts_validation_context=context,skip_diff=skip_diff)
            revocation=revocation_result(status,evidence_supplied)
            timestamp_label,timestamp_details=timestamp_result(status,document_timestamp)
        except Exception as exc:
            out.append(SigVerificationResult(
                idx, getattr(sig, "field_name", f"sig_{idx}"),
                IntegrityStatus.UNKNOWN, None,
                TrustStatus.NOT_EVALUATED, ModpolicyStatus.UNKNOWN,
                IdentityStatus.NOT_ESTABLISHED,
                "pyHanko validation raised an exception",
                None, None, "unknown", "unknown", "", None,
                error=str(exc)
            ))
            continue

        # ── Integrity ──────────────────────────────────────────────────
        intact       = getattr(status, "intact", None)
        int_status   = (IntegrityStatus.PASS if intact else
                        IntegrityStatus.FAIL if intact is False else
                        IntegrityStatus.UNKNOWN)

        # ── Mathematical validity ──────────────────────────────────────
        valid        = getattr(status, "valid", None)

        # ── Trust ──────────────────────────────────────────────────────
        trusted_raw  = getattr(status, "trusted", None)
        cert         = getattr(status, "signing_cert", None)
        self_signed  = False
        test_cert    = False
        cert_info    = None
        trust_status = TrustStatus.NOT_EVALUATED

        if cert is not None:
            try:
                cert = x509.load_der_x509_certificate(cert.dump())
                self_signed = (cert.subject == cert.issuer)
                subj_str    = _cert_cn(cert.subject)
                iss_str     = _cert_cn(cert.issuer)
                test_cert   = (self_signed or
                               "TEST" in subj_str.upper() or
                               "DEMO" in subj_str.upper() or
                               "SIGNGUARD" in subj_str.upper())
                nb = str(cert.not_valid_before_utc)
                na = str(cert.not_valid_after_utc)
                key_alg = type(cert.public_key()).__name__
                cert_info = CertInfo(subj_str, iss_str,
                                     str(cert.serial_number),
                                     nb, na, self_signed, test_cert, key_alg)

                now = datetime.now(timezone.utc)
                if revocation=="REVOKED":
                    trust_status = "REVOKED"
                elif not (cert.not_valid_before_utc <= now <= cert.not_valid_after_utc):
                    trust_status = TrustStatus.EXPIRED
                elif trusted_raw is True:
                    trust_status = TrustStatus.TRUSTED
                elif self_signed:
                    trust_status = TrustStatus.SELF_SIGNED
                elif trusted_raw is False:
                    trust_status = TrustStatus.UNKNOWN_ISSUER
                else:
                    trust_status = TrustStatus.UNKNOWN_ISSUER
            except Exception as ce:
                trust_status = TrustStatus.NOT_EVALUATED

        # ── Modification policy ────────────────────────────────────────
        docmdp_ok    = getattr(status, "docmdp_ok", None)
        modpol       = (ModpolicyStatus.COMPLIANT  if docmdp_ok is True else
                        ModpolicyStatus.VIOLATION  if docmdp_ok is False else
                        ModpolicyStatus.UNKNOWN)

        # ── Signer identity ────────────────────────────────────────────
        if trust_status == TrustStatus.TRUSTED and valid is True and int_status == IntegrityStatus.PASS and not test_cert:
            identity = IdentityStatus.ESTABLISHED
        elif trust_status in (TrustStatus.SELF_SIGNED, TrustStatus.UNKNOWN_ISSUER, TrustStatus.EXPIRED):
            identity = IdentityStatus.UNVERIFIED
        else:
            identity = IdentityStatus.NOT_ESTABLISHED

        # ── ByteRange ──────────────────────────────────────────────────
        br_obj = None
        try:
            br_values = list(sig.sig_object.get("/ByteRange"))
            br_obj    = validate_byte_range(raw, [int(v) for v in br_values])
        except Exception:
            pass

        # ── Digest / sig alg ──────────────────────────────────────────
        dig_alg = getattr(status, "md_algorithm", "unknown") or "unknown"
        sig_alg = "RSA" if (cert_info and "Rsa" in cert_info.key_algorithm) else \
                  "EC"  if (cert_info and "Ec"  in cert_info.key_algorithm) else "unknown"

        # ── Signing time ───────────────────────────────────────────────
        st = getattr(status, "signer_reported_dt", None)
        signing_time = str(st) if st else ""

        # ── Signed attributes ──────────────────────────────────────────
        signed_attrs_ok = valid   # pyHanko bundles this into .valid

        # ── Completeness ──────────────────────────────────────────────
        checks = []
        checks.append("integrity" if int_status != IntegrityStatus.UNKNOWN else "integrity:incomplete")
        checks.append("math"      if valid      is not None                 else "math:incomplete")
        checks.append("trust"     if trust_status != TrustStatus.NOT_EVALUATED else "trust:incomplete")
        checks.append("modpolicy" if docmdp_ok  is not None                 else "modpolicy:incomplete")
        completeness = " | ".join(checks)

        # ── Details narrative ──────────────────────────────────────────
        details = []
        if hasattr(status, "summary"):
            try:
                details.append(str(status.summary()))
            except Exception:
                pass
        if int_status == IntegrityStatus.FAIL:
            details.append("INTEGRITY FAILURE: signed bytes have been modified.")
        if valid is False:
            details.append("MATH FAILURE: public-key verification failed.")
        if test_cert:
            details.append("NOTE: Test/self-signed certificate — signer identity CANNOT be established from this certificate.")
        if br_obj and not br_obj.covers_full_file:
            details.append("ByteRange does not cover the full current file — incremental update likely present.")

        out.append(SigVerificationResult(
            sig_index=idx,
            field_name=getattr(sig, "field_name", f"sig_{idx}") or f"sig_{idx}",
            integrity_status=int_status,
            math_valid=valid,
            trust_status=trust_status,
            modpolicy_status=modpol,
            identity_status=identity,
            completeness=completeness,
            byte_range=br_obj,
            cert_info=cert_info,
            digest_alg=dig_alg,
            sig_alg=sig_alg,
            signing_time=signing_time,
            signed_attrs_ok=signed_attrs_ok,
            details=details,
            revocation_status=revocation,
            timestamp_status=timestamp_label,
            timestamp_details=timestamp_details,
            coverage_level=getattr(getattr(status,"coverage",None),"name","UNKNOWN"),
            modification_level=getattr(getattr(status, "modification_level", None), "name", "UNKNOWN"),
        ))

    return out


def _cert_cn(name_obj) -> str:
    try:
        attrs = name_obj.get_attributes_for_oid(NameOID.COMMON_NAME)
        if attrs:
            return attrs[0].value
    except Exception:
        pass
    try:
        return name_obj.rfc4514_string()
    except Exception:
        return str(name_obj)


def _verify_no_pyhanko(raw: bytes) -> List[SigVerificationResult]:
    """
    pyHanko is not installed — scan for sig dicts and return UNSUPPORTED.
    Never silently mark the document valid.
    """
    sigs = _scan_sig_entries(raw)
    if not sigs:
        return []
    out = []
    for idx, _ in enumerate(sigs):
        out.append(SigVerificationResult(
            idx, f"sig_{idx}",
            IntegrityStatus.UNKNOWN, None,
            TrustStatus.NOT_EVALUATED, ModpolicyStatus.UNKNOWN,
            IdentityStatus.NOT_ESTABLISHED,
            "pyHanko not installed — cryptographic verification not available",
            None, None, "unknown", "unknown", "", None,
            error="pyHanko package not installed. Run: pip install pyhanko pyhanko-certvalidator"
        ))
    return out


def _scan_sig_entries(raw: bytes) -> list:
    sigs = []
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        for xref in range(1, doc.xref_length()):
            try:
                obj = doc.xref_object(xref, compressed=False)
                if "/ByteRange" in obj and "/Contents" in obj:
                    sigs.append(xref)
            except Exception:
                pass
        doc.close()
    except Exception:
        pass
    return sigs


def _build_summary(results: List[SigVerificationResult]) -> str:
    parts = []
    for r in results:
        parts.append(
            f"[{r.field_name}] integrity={r.integrity_status} "
            f"| math={r.math_valid} "
            f"| trust={r.trust_status} "
            f"| modpolicy={r.modpolicy_status}"
        )
    return " || ".join(parts)
