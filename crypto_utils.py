import os
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class DataEncryption:
    def __init__(self, password: str = None):
        """Initialize encryption with password from Streamlit secrets or parameter"""
        if password is None:
            try:
                import streamlit as st
                password = st.secrets["ENCRYPTION_KEY"]
            except:
                # Fallback for local development
                password = os.getenv('ENCRYPTION_KEY', 'default_key_change_this_for_local_dev_only')

        # Generate a key from password
        password_bytes = password.encode()
        salt = b'salt_'  # In production, use a random salt stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        self.cipher_suite = Fernet(key)

    def encrypt_data(self, data):
        """Encrypt data (dict or list) and return base64 string"""
        json_str = json.dumps(data)
        encrypted_data = self.cipher_suite.encrypt(json_str.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def decrypt_data(self, encrypted_str):
        """Decrypt base64 string and return original data"""
        try:
            encrypted_data = base64.urlsafe_b64decode(encrypted_str.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def save_encrypted_file(self, data, filepath):
        """Save encrypted data to file"""
        encrypted_str = self.encrypt_data(data)
        with open(filepath, 'w') as f:
            f.write(encrypted_str)

    def load_encrypted_file(self, filepath):
        """Load and decrypt data from file"""
        try:
            with open(filepath, 'r') as f:
                encrypted_str = f.read()
            return self.decrypt_data(encrypted_str)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading file {filepath}: {e}")
            return None