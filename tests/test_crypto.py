# -*- coding: utf-8 -*-

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, \
    load_pem_private_key

from tac.helpers.crypto import Crypto
from .conftest import ROOT_DIR


def test_initialization_from_existing_private_key():
    """Test that the initialization from an existing private key works correctly."""

    private_key_pem_path = ROOT_DIR + "/tests/data/priv.pem"

    private_key = load_pem_private_key(open(private_key_pem_path, "rb").read(), None, default_backend())

    c = Crypto(private_key_pem_path=private_key_pem_path)

    expected_public_key = private_key.public_key().public_bytes(encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo)
    actual_public_key = c.public_key_pem
    assert expected_public_key == actual_public_key
