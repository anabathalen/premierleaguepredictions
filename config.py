import json
import os
import base64
import requests
from datetime import datetime

# Points configuration
POINTS_EXACT_SCORE = 2
POINTS_CORRECT_RESULT = 1
POINTS_GOAL_DIFFERENCE = 0

class GitHubConfigManager:
    def __init__(self):
        # GitHub configuration
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = os.getenv('GITHUB_REPO_OWNER')
        self.repo_name = os.getenv('GITHUB_REPO_NAME')
        self.branch = 'main'
        
        if not all([self.github_token, self.repo_owner, self.repo_name]):
            raise ValueError("GitHub configuration missing. Set GITHUB_TOKEN, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME environment variables.")
        
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents"
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Configuration file paths
        self.users_file = "users.json"
        self.settings_file = "settings.json"
        
        # Initialize with default data if files don't exist
        self._initialize_config_files()
    
    def _get_file_from_github(self, file_path):
        """Get file content from GitHub"""
        url = f"{self.base_url}/{file_path}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            file_data = response.json()
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return content, file_data['sha']
        elif response.status_code == 404:
            return None, None
        else:
            response.raise_for_status()
    
    def _save_file_to_github(self, file_path, content, message, sha=None):
        """Save file content to GitHub"""
        url = f"{self.base_url}/{file_path}"
        
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            'message': message,
            'content': encoded_content,
            'branch': self.branch
        }
        
        if sha:
            data['sha'] = sha
        
        response = requests.put(url, headers=self.headers, json=data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            response.raise_for_status()
    
    def _initialize_config_files(self):
        """Initialize config files with default data if they don't exist"""
        
        # Check and create users.json
        users_content, _ = self._get_file_from_github(self.users_file)
        if not users_content:
            default_users = {
                "admin": {
                    "passcode": "admin_hash_here",  # You should hash this properly
                    "display_name": "Administrator",
                    "is_admin": True,
                    "created_at": datetime.now().isoformat()
                }
            }
            self._save_file_to_github(
                self.users_file, 
                json.dumps(default_users, indent=2), 
                "Initialize users configuration"
            )
        
        # Check and create settings.json
        settings_content, _ = self._get_file_from_github(self.settings_file)
        if not settings_content:
            default_settings = {
                "current_week": 1,
                "season_start": datetime.now().isoformat(),
                "league_name": "Prediction League",
                "points_system": {
                    "exact_score": POINTS_EXACT_SCORE,
                    "correct_result": POINTS_CORRECT_RESULT,
                    "goal_difference": POINTS_GOAL_DIFFERENCE
                },
                "front_page_blurb": "",
                "predictions_open": True,
                "settings_updated_at": datetime.now().isoformat()
            }
            self._save_file_to_github(
                self.settings_file,
                json.dumps(default_settings, indent=2),
                "Initialize league settings"
            )
    
    def get_users(self):
        """Get all users from GitHub"""
        try:
            content, _ = self._get_file_from_github(self.users_file)
            if content:
                return json.loads(content)
            return {}
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    
    def add_user(self, username, passcode, display_name, is_admin=False):
        """Add a new user"""
        try:
            users_content, sha = self._get_file_from_github(self.users_file)
            users = json.loads(users_content) if users_content else {}
            
            users[username] = {
                "passcode": passcode,
                "display_name": display_name,
                "is_admin": is_admin,
                "created_at": datetime.now().isoformat()
            }
            
            self._save_file_to_github(
                self.users_file,
                json.dumps(users, indent=2),
                f"Add new user: {username}",
                sha
            )
            return True
        except Exception as e:
            print(f"Error adding user {username}: {e}")
            return False

    
    def user_exists(self, username):
        """Check if user exists"""
        users = self.get_users()
        return username in users
    
    def verify_user(self, username, passcode):
        """Verify user credentials"""
        users = self.get_users()
        if username in users:
            return users[username]["passcode"] == passcode
        return False
    
    def get_user_info(self, username):
        """Get user information"""
        users = self.get_users()
        return users.get(username, {})
    
    def get_current_week(self):
        """Get current week number"""
        try:
            content, _ = self._get_file_from_github(self.settings_file)
            if content:
                settings = json.loads(content)
                return settings.get("current_week", 1)
            return 1
        except Exception as e:
            print(f"Error getting current week: {e}")
            return 1
    
    def set_current_week(self, week_num):
        """Set current week number"""
        try:
            content, sha = self._get_file_from_github(self.settings_file)
            settings = json.loads(content) if content else {}
            
            settings["current_week"] = week_num
            settings["settings_updated_at"] = datetime.now().isoformat()
            
            self._save_file_to_github(
                self.settings_file,
                json.dumps(settings, indent=2),
                f"Update current week to {week_num}",
                sha
            )
            return True
        except Exception as e:
            print(f"Error setting current week: {e}")
            return False
    
    def get_league_settings(self):
        """Get league settings"""
        try:
            content, _ = self._get_file_from_github(self.settings_file)
            if content:
                return json.loads(content)
            return {}
        except Exception as e:
            print(f"Error getting league settings: {e}")
            return {}
    
    def update_league_settings(self, **kwargs):
        """Update league settings"""
        try:
            content, sha = self._get_file_from_github(self.settings_file)
            settings = json.loads(content) if content else {}
            
            # Update provided settings
            for key, value in kwargs.items():
                settings[key] = value
            
            settings["settings_updated_at"] = datetime.now().isoformat()
            
            self._save_file_to_github(
                self.settings_file,
                json.dumps(settings, indent=2),
                "Update league settings",
                sha
            )
            return True
        except Exception as e:
            print(f"Error updating league settings: {e}")
            return False
    
    def is_admin(self, username):
        """Check if user is admin"""
        users = self.get_users()
        user_info = users.get(username, {})
        return user_info.get("is_admin", False)
    
    def get_front_page_blurb(self):
        """Get the front page blurb text"""
        settings = self.get_league_settings()
        return settings.get("front_page_blurb", "")

    def set_front_page_blurb(self, blurb):
        """Set the front page blurb text"""
        content, sha = self._get_file_from_github(self.settings_file)
        settings = json.loads(content) if content else {}
        settings["front_page_blurb"] = blurb
        settings["settings_updated_at"] = datetime.now().isoformat()
        
        self._save_file_to_github(
            self.settings_file,
            json.dumps(settings, indent=2),
            "Update front page blurb",
            sha
        )
        return True
    
    def are_predictions_open(self):
        """Check if predictions are currently being accepted"""
        settings = self.get_league_settings()
        return settings.get("predictions_open", True)
    
    def set_predictions_open(self, open_status):
        """Set whether predictions are being accepted"""
        content, sha = self._get_file_from_github(self.settings_file)
        settings = json.loads(content) if content else {}
        settings["predictions_open"] = open_status
        settings["settings_updated_at"] = datetime.now().isoformat()
        
        self._save_file_to_github(
            self.settings_file,
            json.dumps(settings, indent=2),
            f"Set predictions open to {open_status}",
            sha
        )
        return True

class ConfigManager(GitHubConfigManager):
    def initialize_users(self):
        # Just re-run the file initializer (users.json and settings.json)
        self._initialize_config_files()
        return self.get_users()


