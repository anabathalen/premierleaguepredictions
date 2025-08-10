import os
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_utils import DataEncryption

# Configuration
ADMIN_USERNAME = "admin"
ADMIN_PASSCODE = "admin123"  # Change this!
CURRENT_WEEK_FILE = "current_week.txt"

# Points system
POINTS_CORRECT_RESULT = 3  # Win/Draw/Loss correct
POINTS_EXACT_SCORE = 5     # Exact score correct
POINTS_GOAL_DIFFERENCE = 1 # Goal difference correct

class ConfigManager:
    def __init__(self):
        self.encryption = DataEncryption()
        
    def get_current_week(self):
        """Get current gameweek number"""
        try:
            with open(CURRENT_WEEK_FILE, 'r') as f:
                return int(f.read().strip())
        except FileNotFoundError:
            # Default to week 1 if file doesn't exist
            self.set_current_week(1)
            return 1
    
    def set_current_week(self, week_num):
        """Set current gameweek number (admin only)"""
        with open(CURRENT_WEEK_FILE, 'w') as f:
            f.write(str(week_num))
    
    def initialize_users(self):
        """Initialize users file if it doesn't exist - for cloud deployment"""
        users_file = "users.json"
        
        # Always try to load existing file first
        existing_users = self.encryption.load_encrypted_file(users_file)
        if existing_users:
            return existing_users
        
        # If no file exists or file is corrupted, create default users
        print("Creating new users file...")
        default_users = {
            "admin": {
                "passcode": "admin123",
                "is_admin": True,
                "display_name": "Administrator"
            },
            "user1": {
                "passcode": "pass1",
                "is_admin": False,
                "display_name": "User One"
            },
            "user2": {
                "passcode": "pass2", 
                "is_admin": False,
                "display_name": "User Two"
            },
            "user3": {
                "passcode": "pass3", 
                "is_admin": False,
                "display_name": "User Three"
            }
        }
        
        try:
            self.encryption.save_encrypted_file(default_users, users_file)
            print(f"Successfully created users file with {len(default_users)} users")
            return default_users
        except Exception as e:
            print(f"Error saving users file: {e}")
            raise Exception(f"Failed to create users file: {e}")
    
    def get_users(self):
        """Get all users"""
        return self.encryption.load_encrypted_file("users.json") or {}
    
    def add_user(self, username, passcode, display_name, is_admin=False):
        """Add a new user"""
        users = self.get_users()
        users[username] = {
            "passcode": passcode,
            "is_admin": is_admin,
            "display_name": display_name
        }
        self.encryption.save_encrypted_file(users, "users.json")
        return True
