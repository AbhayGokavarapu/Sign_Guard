"""Real signed CRL, OCSP and RFC3161 controls; no certificate URL retrieval."""
from datetime import datetime,timedelta,timezone
import io
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID,AuthorityInformationAccessOID
from asn1crypto import x509 as asn_x509,crl as asn_crl,ocsp as asn_ocsp,keys
from simulation.security_fixtures import signed_control
from core.crypto_verifier import verify


def make_chain(tsa=False):
    now=datetime.now(timezone.utc)
    root_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    leaf_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    root_name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Lifecycle TEST Root')])
    leaf_name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Lifecycle TEST TSA' if tsa else 'Lifecycle TEST Signer')])
    root=(x509.CertificateBuilder().subject_name(root_name).issuer_name(root_name).public_key(root_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=2)).not_valid_after(now+timedelta(days=10))
        .add_extension(x509.BasicConstraints(ca=True,path_length=1),critical=True)
        .add_extension(x509.KeyUsage(True,False,False,False,False,True,True,False,False),critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()),critical=False)
        .sign(root_key,hashes.SHA256()))
    builder=(x509.CertificateBuilder().subject_name(leaf_name).issuer_name(root_name).public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=5))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.KeyUsage(True,not tsa,False,False,False,False,False,False,False),critical=True)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),critical=False))
    if not tsa:
        builder=builder.add_extension(x509.AuthorityInformationAccess([x509.AccessDescription(AuthorityInformationAccessOID.OCSP,x509.UniformResourceIdentifier('https://ocsp.example.invalid/status'))]),critical=False)
    if tsa:builder=builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.TIME_STAMPING]),critical=True)
    leaf=builder.sign(root_key,hashes.SHA256())
    return root,root_key,leaf,leaf_key


def asn(cert):return asn_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER))
def pair(cert,key):return (cert.public_bytes(serialization.Encoding.PEM),key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))


def make_crl(root,root_key,leaf,revoked=False,stale=False):
    now=datetime.now(timezone.utc)
    builder=(x509.CertificateRevocationListBuilder().issuer_name(root.subject)
        .last_update(now-timedelta(days=2) if stale else now-timedelta(minutes=1))
        .next_update(now-timedelta(days=1) if stale else now+timedelta(days=1))
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),critical=False))
    if revoked:builder=builder.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(leaf.serial_number).revocation_date(now-timedelta(hours=1)).build())
    return asn_crl.CertificateList.load(builder.sign(root_key,hashes.SHA256()).public_bytes(serialization.Encoding.DER))


@pytest.fixture(scope='module')
def lifecycle():
    root,key,leaf,leaf_key=make_chain()
    return root,key,leaf,leaf_key,signed_control(cert_pair=pair(leaf,leaf_key))


def test_current_signed_crl_establishes_non_revocation(lifecycle):
    root,key,leaf,_,raw=lifecycle
    sig=verify(raw,trust_roots=[asn(root)],crls=[make_crl(root,key,leaf)]).results[0]
    assert sig.integrity_status=='PASS'
    assert sig.revocation_status=='GOOD (validated offline evidence)'


def test_revoked_certificate_is_not_trusted(lifecycle):
    root,key,leaf,_,raw=lifecycle
    sig=verify(raw,trust_roots=[asn(root)],crls=[make_crl(root,key,leaf,revoked=True)]).results[0]
    assert sig.math_valid is True
    assert sig.revocation_status=='REVOKED'
    assert sig.cert_trusted is False


def test_stale_crl_is_not_good(lifecycle):
    root,key,leaf,_,raw=lifecycle
    sig=verify(raw,trust_roots=[asn(root)],crls=[make_crl(root,key,leaf,stale=True)]).results[0]
    assert sig.revocation_status.startswith('UNKNOWN')


def test_signed_ocsp_good_response(lifecycle):
    from cryptography.x509 import ocsp
    root,key,leaf,_,raw=lifecycle;now=datetime.now(timezone.utc)
    response=(ocsp.OCSPResponseBuilder().add_response(cert=leaf,issuer=root,algorithm=hashes.SHA1(),
        cert_status=ocsp.OCSPCertStatus.GOOD,this_update=now-timedelta(minutes=1),next_update=now+timedelta(days=1),
        revocation_time=None,revocation_reason=None)
        .responder_id(ocsp.OCSPResponderEncoding.HASH,root).sign(key,hashes.SHA256()))
    sig=verify(raw,trust_roots=[asn(root)],ocsps=[asn_ocsp.OCSPResponse.load(response.public_bytes(serialization.Encoding.DER))]).results[0]
    assert sig.revocation_status=='GOOD (validated offline evidence)'


def test_rfc3161_timestamp_is_validated_against_explicit_tsa_root():
    from pyhanko.sign.timestamps import DummyTimeStamper
    from simulation.signed_samples import get_test_cert,sign_pdf
    from simulation.sample_generator import build_unsigned
    root,root_key,tsa,tsa_key=make_chain(tsa=True)
    stamper=DummyTimeStamper(asn(tsa),keys.PrivateKeyInfo.load(tsa_key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())))
    signed,message=sign_pdf(build_unsigned('Timestamped test control'),*get_test_cert(),timestamper=stamper)
    assert signed,message
    sig=verify(signed,trust_roots=[asn(root)]).results[0]
    assert sig.timestamp_status=='VALID / TRUSTED TSA'
    assert sig.timestamp_details['math_valid'] is True
    assert sig.timestamp_details['timestamp']


def test_timestamp_without_trusted_tsa_is_not_called_trusted():
    from pyhanko.sign.timestamps import DummyTimeStamper
    from simulation.signed_samples import get_test_cert,sign_pdf
    from simulation.sample_generator import build_unsigned
    root,root_key,tsa,tsa_key=make_chain(tsa=True)
    stamper=DummyTimeStamper(asn(tsa),keys.PrivateKeyInfo.load(tsa_key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())))
    signed,message=sign_pdf(build_unsigned('Timestamped test control'),*get_test_cert(),timestamper=stamper)
    assert signed,message
    sig=verify(signed).results[0]
    assert sig.timestamp_status=='VALID / UNTRUSTED TSA'


def test_signed_ocsp_revoked_response_is_not_good(lifecycle):
    from cryptography.x509 import ocsp
    root,key,leaf,_,raw=lifecycle;now=datetime.now(timezone.utc)
    response=(ocsp.OCSPResponseBuilder().add_response(cert=leaf,issuer=root,algorithm=hashes.SHA1(),
        cert_status=ocsp.OCSPCertStatus.REVOKED,this_update=now-timedelta(minutes=1),next_update=now+timedelta(days=1),
        revocation_time=now-timedelta(hours=1),revocation_reason=x509.ReasonFlags.key_compromise)
        .responder_id(ocsp.OCSPResponderEncoding.HASH,root).sign(key,hashes.SHA256()))
    sig=verify(raw,trust_roots=[asn(root)],ocsps=[asn_ocsp.OCSPResponse.load(response.public_bytes(serialization.Encoding.DER))]).results[0]
    assert sig.revocation_status=='REVOKED'
    assert sig.cert_trusted is False


def test_corrupted_timestamp_is_not_trusted():
    from pyhanko.sign.timestamps import DummyTimeStamper
    from simulation.signed_samples import get_test_cert,sign_pdf
    from simulation.sample_generator import build_unsigned
    from pyhanko.pdf_utils.reader import PdfFileReader
    from asn1crypto import cms
    root,_,tsa,tsa_key=make_chain(tsa=True)
    stamper=DummyTimeStamper(asn(tsa),keys.PrivateKeyInfo.load(tsa_key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())))
    raw,message=sign_pdf(build_unsigned('Timestamp integrity control'),*get_test_cert(),timestamper=stamper)
    assert raw,message
    sig=PdfFileReader(io.BytesIO(raw)).embedded_signatures[0]
    _,start,end,_=map(int,sig.sig_object['/ByteRange'])
    content=bytes.fromhex(raw[start+1:end-1].decode())
    signed_data=cms.ContentInfo.load(content)
    for attribute in signed_data['content']['signer_infos'][0]['unsigned_attrs']:
        if attribute['type'].native=='signature_time_stamp_token':
            signature=attribute['values'][0]['content']['signer_infos'][0]['signature'].native
            attribute['values'][0]['content']['signer_infos'][0]['signature']=bytes([signature[0]^1])+signature[1:]
            break
    else:pytest.fail('Timestamp attribute missing from control')
    changed=raw[:start]+b'<'+signed_data.dump().ljust(len(content),b'\0').hex().encode()+b'>'+raw[end:]
    result=verify(changed,trust_roots=[asn(root)]).results[0]
    assert result.timestamp_status=='INVALID TIMESTAMP'
    assert result.timestamp_details['math_valid'] is False
