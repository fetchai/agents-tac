# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
#
#   Copyright 2018-2019 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
import logging

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

logger = logging.getLogger(__name__)


class CryptoError(Exception):
    """Exception to be thrown when cryptographic signatures don't match!."""


class Crypto(object):
    def __init__(self):
        """
        Instantiate a price bandit object.

        :param price: the price this bandit is modelling
        :param beta_a: the a parameter of the beta distribution
        :param beta_b: the b parameter of the beta distribution
        """
        self._chosen_ec = ec.SECP384R1()
        self._chosen_hash = hashes.SHA256()
        self._private_key = self._generate_pk()
        self._public_key_obj = self._compute_pbk()
        self._public_key = self._pbk_to_str(self._public_key_obj)
        assert self._pbk_to_str(self._public_key_obj) == self._pbk_to_str(self._pbk_to_obj(self._public_key))

    @property
    def public_key(self):
        return self._public_key

    def _generate_pk(self) -> object:
        """
        Generates a private key.

        :return: private key
        """
        private_key = ec.generate_private_key(self._chosen_ec, default_backend())
        return private_key

    def _compute_pbk(self) -> object:
        """
        Derives the public key from the private key.

        :return: public key
        """
        public_key = self._private_key.public_key()
        return public_key

    def _pbk_to_str(self, pbk: object) -> str:
        """
        Converts the public key from object to string.

        :param pbk: the public key as an object

        :return: the public key as a string
        """
        serialized_public_key = pbk.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        serialized_public_key = b''.join(serialized_public_key.splitlines()[1:-1])
        return serialized_public_key.decode("utf-8")

    def _pbk_to_obj(self, pbk: str) -> object:
        """
        Converts the public key from string to object.

        :param pbk: the public key as a string

        :return: the public key object
        """
        serialized_pbk = str.encode(pbk)
        serialized_pbk = serialized_pbk[0:64] + b'\n' + serialized_pbk[64:128] + b'\n' + serialized_pbk[128:] + b'\n'
        serialized_pbk = b'-----BEGIN PUBLIC KEY-----\n' + serialized_pbk + b'-----END PUBLIC KEY-----\n'
        pbk_object = serialization.load_pem_public_key(serialized_pbk, backend=default_backend())
        return pbk_object

    def sign_data(self, data: bytes) -> bytes:
        """
        Sign data with your own private key.

        :param data: the data to sign
        :return: the signature
        """
        digest = self._hash_data(data)
        signature = self._private_key.sign(digest, ec.ECDSA(utils.Prehashed(self._chosen_hash)))
        return signature

    def is_confirmed_integrity(self, data: bytes, signature: bytes, signer_pbk: str) -> bool:
        """
        Confirrms the integrity of the data with respect to its signature.

        :param data: the data to be confirmed
        :param signature: the signature associated with the data
        :param signer_pbk:  the public key of the signer

        :return: bool indicating whether the integrity is confirmed or not
        """
        signer_pbk = self._pbk_to_obj(signer_pbk)
        digest = self._hash_data(data)
        try:
            signer_pbk.verify(signature, digest, ec.ECDSA(utils.Prehashed(self._chosen_hash)))
            return True
        except CryptoError as e:
            logger.exception(str(e))
            return False

    def _hash_data(self, data: bytes) -> bytes:
        """
        Hashes data.

        :param data: the data to be hashed
        :return: digest of the data
        """
        hasher = hashes.Hash(self._chosen_hash, default_backend())
        hasher.update(data)
        digest = hasher.finalize()
        return digest
