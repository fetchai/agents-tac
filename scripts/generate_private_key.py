# /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a private key to be used for the Trading Agent Competition.
It prints the key in PEM format to stdout.
"""
from tac.helpers.crypto import Crypto
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

if __name__ == '__main__':
    crypto = Crypto()
    pem = crypto._private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    print(pem)
