import os
from crypto_utils import DataEncryption

# Configuration
ADMIN_USERNAME = "admin"
ADMIN_PASSCODE = "admin123"  # Change this!
CURRENT_WEEK_FILE = "current_week.txt"

# Points system
POINTS_CORRECT_RESULT = 3  # Win/Draw/Loss correct
POINTS_EXACT_SCORE = 5  # Exact score correct
POINTS_GOAL_DIFFERENCE = 1  # Goal difference correct


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
        """Initialize users file if it doesn't exist"""
        users_file = "users.json"
        if not os.path.exists(users_file):
            # Default users - you should modify this
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
                }
            }
            self.encryption.save_encrypted_file(default_users, users_file)
            return default_users
        return self.encryption.load_encrypted_file(users_file)

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