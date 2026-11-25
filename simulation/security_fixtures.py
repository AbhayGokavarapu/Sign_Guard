"""Real signed security controls. Labels never enter the detector."""
import io
import tempfile
from pathlib import Path
import pymupdf as fitz
from reportlab.pdfgen import canvas
from simulation.signed_samples import get_test_cert, sign_pdf

TAMPER_MARKER = b'SIGNGUARD-INTEGRITY-CONTROL'


def signed_control(text='Payment amount: $1,000', pages=1, cert_pair=None):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pageCompression=0)
    c.setSubject(TAMPER_MARKER.decode())
    for i in range(pages):
        c.setFont('Helvetica', 16)
        c.drawString(72, 750, f'Contract page {i + 1}')
        c.drawString(72, 700, text)
        c.drawString(72, 650, 'Research fixture; test certificate, identity unverified.')
        c.showPage()
    c.save()
    signed, message = sign_pdf(buf.getvalue(), *(cert_pair or get_test_cert()))
    if signed is None:
        raise RuntimeError(message)
    return signed


def tamper_signed(raw):
    """Change metadata in signed bytes without damaging PDF syntax or its rendering."""
    if TAMPER_MARKER not in raw:
        raise ValueError('Signed fixture is missing its tamper control marker')
    return raw.replace(TAMPER_MARKER, b'SIGNGUARD-INTEGRITY-CHANGED', 1)


def incremental_update(raw, replacement=None, annotation=False, page_index=0):
    """Append a valid incremental revision; preserve the original signed prefix."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'revision.pdf'
        path.write_bytes(raw)
        with fitz.open(path) as doc:
            page = doc[page_index]
            if annotation:
                page.add_text_annot((40, 40), 'Reviewed by auditor; content unchanged.')
            elif replacement is not None:
                page.draw_rect(fitz.Rect(65, 120, 560, 160), color=None, fill=(1, 1, 1))
                page.insert_text((72, 142), replacement, fontsize=16)
            else:
                doc.set_metadata({**doc.metadata, 'keywords': 'reviewed'})
            doc.saveIncr()
        updated = path.read_bytes()
    assert updated.startswith(raw), 'Incremental update rewrote the signed prefix'
    return updated


def shadow_pair(original_amount='$1,000', shadow_amount='$9,000', pages=1, page_index=0):
    original = signed_control(f'Payment amount: {original_amount}', pages=pages)
    return original, incremental_update(original, f'Payment amount: {shadow_amount}', page_index=page_index)


def certificate_chain(expired=False):
    """Generate a test root and leaf for controlled trust/expiry evaluation."""
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    now = datetime.now(timezone.utc)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'SignGuard TEST root')])
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'SignGuard TEST leaf')])
    root = (x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name)
        .public_key(root_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(days=365)).not_valid_after(now+timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), critical=True)
        .sign(root_key, hashes.SHA256()))
    leaf = (x509.CertificateBuilder().subject_name(leaf_name).issuer_name(root_name)
        .public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(days=30)).not_valid_after(now-timedelta(days=1) if expired else now+timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
        .sign(root_key, hashes.SHA256()))
    return (leaf.public_bytes(serialization.Encoding.PEM),
            leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())), root.public_bytes(serialization.Encoding.PEM)
