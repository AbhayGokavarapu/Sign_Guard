"""
Genuine digital signature creation using pyHanko.

Generates RSA-2048 self-signed test certificates and applies real
CMS/PKCS#7 digital signatures to synthetic PDFs.

IMPORTANT: These use self-signed certificates generated locally.
They are labelled TEST CERTIFICATE and are NOT trusted root CAs.
Mathematical signature validity and byte integrity are real.
Certificate trust is explicitly NOT established.
"""

from __future__ import annotations

import datetime, io, os, tempfile
from typing import Optional, Tuple

import logging
logging.getLogger("pyhanko").setLevel(logging.ERROR)
logging.getLogger("certvalidator").setLevel(logging.ERROR)

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# Cache so we don't regenerate on every call
_CACHED_CERT: Optional[Tuple[bytes, bytes]] = None


def generate_test_certificate() -> Tuple[bytes, bytes]:
    """
    Generate a self-signed RSA-2048 certificate for test use.
    Returns (cert_pem, key_pem).
    Explicitly labelled [TEST] in CN to prevent identity confusion.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,         "XX"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,    "SignGuard Test CA"),
        x509.NameAttribute(NameOID.COMMON_NAME,
                           "SignGuard Demo Signer [TEST — NOT TRUSTED]"),
    ])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(digital_signature=True, key_cert_sign=True,
                          content_commitment=False, key_encipherment=False,
                          data_encipherment=False, key_agreement=False,
                          crl_sign=True, encipher_only=False,
                          decipher_only=False),
            critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem  = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return cert_pem, key_pem


def get_test_cert() -> Tuple[bytes, bytes]:
    global _CACHED_CERT
    if _CACHED_CERT is None:
        _CACHED_CERT = generate_test_certificate()
    return _CACHED_CERT


def sign_pdf(pdf_bytes: bytes,
             cert_pem:  bytes,
             key_pem:   bytes,
             field_name: str = "Signature1") -> Tuple[Optional[bytes], str]:
    """
    Sign a PDF using pyHanko.
    Returns (signed_bytes, status_message).
    Returns (None, error_msg) if signing fails.
    """
    try:
        from pyhanko.sign import signers, fields as sig_fields
        from pyhanko.sign.fields import SigFieldSpec
        from pyhanko.pdf_utils import incremental_writer
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.signers import SimpleSigner
    except ImportError:
        return None, "pyHanko not installed — pip install pyhanko pyhanko-certvalidator"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = os.path.join(tmpdir, "cert.pem")
            key_path  = os.path.join(tmpdir, "key.pem")
            pdf_in    = os.path.join(tmpdir, "in.pdf")
            step1_out = os.path.join(tmpdir, "step1.pdf")
            step2_out = os.path.join(tmpdir, "signed.pdf")

            with open(cert_path, "wb") as f: f.write(cert_pem)
            with open(key_path,  "wb") as f: f.write(key_pem)
            with open(pdf_in,    "wb") as f: f.write(pdf_bytes)

            signer_obj = SimpleSigner.load(
                key_file=key_path,
                cert_file=cert_path,
                ca_chain_files=(),
                key_passphrase=None,
            )

            # Step 1: add signature field
            with open(pdf_in, "rb") as fin:
                reader = PdfFileReader(fin, strict=False)
                w = incremental_writer.IncrementalPdfFileWriter(fin)
                sig_fields.append_signature_field(
                    w, SigFieldSpec(field_name, on_page=0))
                with open(step1_out, "wb") as fout:
                    w.write(fout)

            # Step 2: sign
            with open(step1_out, "rb") as fin:
                w2   = incremental_writer.IncrementalPdfFileWriter(fin)
                meta = signers.PdfSignatureMetadata(field_name=field_name)
                with open(step2_out, "wb") as fout:
                    signers.sign_pdf(w2, meta, signer=signer_obj, output=fout)

            with open(step2_out, "rb") as f:
                signed = f.read()

        return signed, "OK"

    except Exception as exc:
        return None, f"Signing failed: {exc}"


def build_signed_pdf(content_text: str = "This document is digitally signed.") -> bytes:
    """
    Build and sign a synthetic PDF.
    If pyHanko signing fails, returns a plain PDF with an explicit note —
    never pretends to be signed when signing failed.
    """
    from simulation.sample_generator import build_signed_looking_pdf

    plain = build_signed_looking_pdf(
        title="DIGITALLY SIGNED DOCUMENT",
        body_lines=[
            content_text,
            "",
            "Document Reference: SG-TEST-001",
            "This document was digitally signed using a test RSA-2048 certificate.",
            "The certificate is self-signed and is NOT trusted by any root CA.",
            "Mathematical signature validity and byte integrity are genuine.",
            "Certificate trust is NOT established.",
        ],
        status="SIGNED WITH TEST CERTIFICATE",
        status_color=(21, 128, 61),
        footer="SignGuard Test Certificate — NOT for production use"
    )

    cert_pem, key_pem = get_test_cert()
    signed, msg = sign_pdf(plain, cert_pem, key_pem)

    if signed:
        return signed

    # Explicit fallback — annotated, NOT labelled as signed
    from simulation.sample_generator import build_unsigned
    fallback_text = (
        f"SIGNING UNAVAILABLE: {msg}\n\n"
        "This is a plain PDF without a real digital signature.\n"
        "Install pyHanko for genuine signing: pip install pyhanko pyhanko-certvalidator"
    )
    return build_unsigned(fallback_text)
