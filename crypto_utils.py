import json
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class DataEncryption:
    def __init__(self):
        # Get encryption key from environment variable or generate one
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_key(self):
        """Get encryption key from environment or generate a new one"""
        # Check if key exists in environment variable
        env_key = os.getenv('ENCRYPTION_KEY')
        if env_key:
            return env_key.encode()
        
        # Generate key from password (you should set this as an environment variable)
        password = os.getenv('ENCRYPTION_PASSWORD', 'default-password-change-me').encode()
        salt = b'prediction-league-salt'  # In production, use a random salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_data(self, data):
        """Encrypt data (dict or list) and return as string"""
        try:
            # Convert to JSON string
            json_data = json.dumps(data, default=str)
            
            # Encrypt the JSON string
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Return as base64 string for storage
            return base64.urlsafe_b64encode(encrypted_data).decode()
        
        except Exception as e:
            print(f"Encryption error: {e}")
            return None
    
    def decrypt_data(self, encrypted_string):
        """Decrypt string and return as original data structure"""
        try:
            # Decode from base64
            encrypted_data = base64.urlsafe_b64decode(encrypted_string.encode())
            
            # Decrypt to get JSON string
            decrypted_bytes = self.fernet.decrypt(encrypted_data)
            json_string = decrypted_bytes.decode()
            
            # Parse JSON back to Python object
            return json.loads(json_string)
        
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    # Legacy methods for backward compatibility
    def save_encrypted_file(self, data, filename):
        """Legacy method - now returns encrypted string instead of saving file"""
        return self.encrypt_data(data)
    
    def load_encrypted_file(self, filename):
        """Legacy method - now expects encrypted string instead of filename"""
        if isinstance(filename, str) and filename.startswith('{'):
            # If it looks like JSON, try to parse directly
            try:
                return json.loads(filename)
            except:
                pass
        return self.decrypt_data(filename) if filename else None
