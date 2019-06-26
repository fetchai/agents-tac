# /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a private key to be used for the Trading Agent Competition.
It prints the key in PEM format to stdout.
"""
from tac.helpers.crypto import Crypto
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

import argparse
parser = argparse.ArgumentParser("generate_private_key")
parser.add_argument("out_file", type=str, help="Where to save the private key.")

if __name__ == '__main__':
    args = parser.parse_args()
    crypto = Crypto()
    pem = crypto._private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    file = open(args.out_file, "wb")
    file.write(pem)
    file.close()
