# _*_ coding: utf-8 _*_
"""内网自签名 HTTPS 证书生成。

证书含本机内网 IP 与 localhost 的 SAN；自签名证书无法避免浏览器"不安全"提示，
访问时信任一次即可（与原 Vite basicSsl 行为一致）。
"""

import datetime
import ipaddress
import os
import socket

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

SSL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ssl")
CERT_FILE = os.path.join(SSL_DIR, "server.crt")
KEY_FILE = os.path.join(SSL_DIR, "server.key")


def _get_local_ips():
    """收集本机 IP，用于证书 SAN（去重，含回环与内网地址）。"""
    ips = {"127.0.0.1"}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        ips.add(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    return ips


def ensure_ssl_cert():
    """返回 (cert_path, key_path)；文件不存在则生成有效期 10 年的自签名证书。"""
    if os.path.isfile(CERT_FILE) and os.path.isfile(KEY_FILE):
        return CERT_FILE, KEY_FILE

    os.makedirs(SSL_DIR, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "HongHuangHou Self-Signed")])
    san = [x509.DNSName("localhost")]
    san += [x509.IPAddress(ipaddress.ip_address(ip)) for ip in sorted(_get_local_ips())]
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .sign(key, hashes.SHA256())
    )
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return CERT_FILE, KEY_FILE
