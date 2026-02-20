"""RSA key pair for JWT tests. Generated at build time, not a real secret."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _b64url(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    b = n.to_bytes(length, "big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
_pub_nums = _public_key.public_numbers()

TEST_PEM_PRIVATE_KEY: str = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

TEST_JWKS: dict = {
    "keys": [
        {
            "kty": "RSA",
            "kid": "test-kid-001",
            "use": "sig",
            "n": _b64url(_pub_nums.n),
            "e": _b64url(_pub_nums.e),
        }
    ]
}
