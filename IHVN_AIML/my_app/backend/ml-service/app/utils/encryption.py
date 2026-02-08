"""
Encryption utility functions for IIT ML Service
"""
import os
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


def generate_key() -> bytes:
    """Generate a new encryption key"""
    return Fernet.generate_key()


def encrypt_data(data: str, key: bytes) -> str:
    """Encrypt string data using Fernet symmetric encryption"""
    try:
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """Decrypt string data using Fernet symmetric encryption"""
    try:
        f = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = f.decrypt(encrypted_bytes)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        raise


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash a password using PBKDF2 with a random salt"""
    if salt is None:
        salt = os.urandom(32)

    # Use PBKDF2 with SHA-256
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    key = kdf.derive(password.encode())
    # Store salt with hash for verification
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Decode the stored hash
        decoded = base64.b64decode(hashed_password.encode())
        salt = decoded[:32]  # First 32 bytes are salt
        stored_key = decoded[32:]  # Rest is the key

        # Hash the provided password with the same salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = kdf.derive(password.encode())

        # Compare keys using constant-time comparison
        return key == stored_key

    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return base64.b64encode(os.urandom(length)).decode()


def hash_data(data: str, algorithm: str = 'sha256') -> str:
    """Hash data using specified algorithm"""
    if algorithm == 'sha256':
        return hashlib.sha256(data.encode()).hexdigest()
    elif algorithm == 'md5':
        return hashlib.md5(data.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def encrypt_file(file_path: str, key: bytes, output_path: Optional[str] = None) -> str:
    """Encrypt a file"""
    if output_path is None:
        output_path = file_path + '.encrypted'

    try:
        f = Fernet(key)

        with open(file_path, 'rb') as file:
            file_data = file.read()

        encrypted_data = f.encrypt(file_data)

        with open(output_path, 'wb') as file:
            file.write(encrypted_data)

        return output_path

    except Exception as e:
        logger.error(f"File encryption error: {e}")
        raise


def decrypt_file(file_path: str, key: bytes, output_path: Optional[str] = None) -> str:
    """Decrypt a file"""
    if output_path is None:
        output_path = file_path.replace('.encrypted', '.decrypted')

    try:
        f = Fernet(key)

        with open(file_path, 'rb') as file:
            encrypted_data = file.read()

        decrypted_data = f.decrypt(encrypted_data)

        with open(output_path, 'wb') as file:
            file.write(decrypted_data)

        return output_path

    except Exception as e:
        logger.error(f"File decryption error: {e}")
        raise
