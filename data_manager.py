import pandas as pd
import os
import sys
import json
import base64
import requests
from datetime import datetime

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_utils import DataEncryption
from config import ConfigManager, POINTS_CORRECT_RESULT, POINTS_EXACT_SCORE, POINTS_GOAL_DIFFERENCE

class GitHubDataManager:
    def __init__(self):
        self.encryption = DataEncryption()
        self.config = ConfigManager()
        
        # GitHub configuration - get these from environment variables or config
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_owner = os.getenv('GITHUB_REPO_OWNER')  # e.g., 'yourusername'
        self.repo_name = os.getenv('GITHUB_REPO_NAME')   # e.g., 'prediction-league-data'
        self.branch = 'main'
        
        if not all([self.github_token, self.repo_owner, self.repo_name]):
            raise ValueError("GitHub configuration missing. Set GITHUB_TOKEN, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME environment variables.")
        
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents"
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def _get_file_from_github(self, file_path):
        """Get file content from GitHub"""
        url = f"{self.base_url}/{file_path}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            file_data = response.json()
            # Decode base64 content
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return content, file_data['sha']
        elif response.status_code == 404:
            return None, None
        else:
            response.raise_for_status()
    
    def _save_file_to_github(self, file_path, content, message, sha=None):
        """Save file content to GitHub"""
        url = f"{self.base_url}/{file_path}"
        
        # Encode content as base64
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            'message': message,
            'content': encoded_content,
            'branch': self.branch
        }
        
        # If file exists, include SHA for update
        if sha:
            data['sha'] = sha
        
        response = requests.put(url, headers=self.headers, json=data)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            response.raise_for_status()
    
    def load_fixtures(self, week_num):
        """Load fixtures for a specific week from GitHub"""
        file_path = f"fixtures/week{week_num}.csv"
        try:
            content, _ = self._get_file_from_github(file_path)
            if content:
                # Convert CSV string to DataFrame
                from io import StringIO
                return pd.read_csv(StringIO(content))
            return None
        except Exception as e:
            print(f"Error loading fixtures for week {week_num}: {e}")
            return None
    
    def load_results(self, week_num):
        """Load results for a specific week from GitHub"""
        file_path = f"results/week{week_num}.csv"
        try:
            content, _ = self._get_file_from_github(file_path)
            if content:
                from io import StringIO
                return pd.read_csv(StringIO(content))
            return None
        except Exception as e:
            print(f"Error loading results for week {week_num}: {e}")
            return None
    
    def save_predictions(self, username, week_num, predictions):
        """Save user predictions for a week to GitHub"""
        file_path = f"predictions/week{week_num}.json"
        
        try:
            # Load existing predictions for this week
            content, sha = self._get_file_from_github(file_path)
            if content:
                # Decrypt existing data
                all_predictions = self.encryption.decrypt_data(content) or {}
            else:
                all_predictions = {}
            
            # Update predictions for this user
            all_predictions[username] = {
                "predictions": predictions,
                "submitted_at": datetime.now().isoformat()
            }
            
            # Encrypt and save back to GitHub
            encrypted_content = self.encryption.encrypt_data(all_predictions)
            
            commit_message = f"Update predictions for {username} - Week {week_num}"
            self._save_file_to_github(file_path, encrypted_content, commit_message, sha)
            
            return True
            
        except Exception as e:
            print(f"Error saving predictions for {username}, week {week_num}: {e}")
            return False
    
    def load_predictions(self, week_num, username=None):
        """Load predictions for a week from GitHub, optionally for a specific user"""
        file_path = f"predictions/week{week_num}.json"
        try:
            content, _ = self._get_file_from_github(file_path)
            if content:
                all_predictions = self.encryption.decrypt_data(content) or {}
            else:
                all_predictions = {}
            
            if username:
                return all_predictions.get(username, {}).get("predictions", [])
            return all_predictions
            
        except Exception as e:
            print(f"Error loading predictions for week {week_num}: {e}")
            return {} if not username else []
    
    def calculate_points(self, prediction, actual_result):
        """Calculate points for a single match prediction"""
        # Handle pandas Series properly
        if actual_result is None:
            return 0
            
        # Convert pandas Series to dict if needed
        if hasattr(actual_result, 'to_dict'):
            actual_result = actual_result.to_dict()
        
        # Check if we have valid scores
        home_score = actual_result.get('home_score')
        away_score = actual_result.get('away_score')
        
        if home_score is None or away_score is None or pd.isna(home_score) or pd.isna(away_score):
            return 0
        
        # Get prediction scores
        pred_home = prediction.get('home_score', 0)
        pred_away = prediction.get('away_score', 0)
        actual_home = int(home_score)
        actual_away = int(away_score)
        
        points = 0
        
        # Exact score
        if pred_home == actual_home and pred_away == actual_away:
            return POINTS_EXACT_SCORE
        
        # Correct result (win/draw/loss)
        pred_result = "draw" if pred_home == pred_away else ("home" if pred_home > pred_away else "away")
        actual_result_outcome = "draw" if actual_home == actual_away else ("home" if actual_home > actual_away else "away")
        
        if pred_result == actual_result_outcome:
            points += POINTS_CORRECT_RESULT
        
        # Goal difference
        pred_diff = pred_home - pred_away
        actual_diff = actual_home - actual_away
        if pred_diff == actual_diff:
            points += POINTS_GOAL_DIFFERENCE
        
        return points
    
    def calculate_user_scores(self):
        """Calculate scores for all users across all completed weeks"""
        users = self.config.get_users()
        user_scores = {}
        
        # Initialize scores
        for username in users:
            if username != "admin":  # Skip admin from leaderboard
                user_scores[username] = {
                    "display_name": users[username]["display_name"],
                    "total_points": 0,
                    "weeks_played": 0,
                    "weekly_breakdown": {}
                }
        
        current_week = self.config.get_current_week()
        
        # Calculate points for each completed week
        for week in range(1, current_week):
            results = self.load_results(week)
            if results is None:
                continue  # Skip weeks without results
            
            predictions = self.load_predictions(week)
            
            for username in user_scores:
                if username in predictions:
                    week_points = 0
                    user_predictions = predictions[username]["predictions"]
                    
                    for i, result_row in results.iterrows():
                        if i < len(user_predictions):
                            points = self.calculate_points(user_predictions[i], result_row)
                            week_points += points
                    
                    user_scores[username]["total_points"] += week_points
                    user_scores[username]["weeks_played"] += 1
                    user_scores[username]["weekly_breakdown"][f"week_{week}"] = week_points
        
        return user_scores
    
    def get_leaderboard(self):
        """Get leaderboard sorted by total points"""
        user_scores = self.calculate_user_scores()
        
        # Convert to list and sort by total points
        leaderboard = []
        for username, data in user_scores.items():
            avg_points = data["total_points"] / max(data["weeks_played"], 1)
            leaderboard.append({
                "username": username,
                "display_name": data["display_name"],
                "total_points": data["total_points"],
                "weeks_played": data["weeks_played"],
                "average_points": round(avg_points, 2),
                "weekly_breakdown": data["weekly_breakdown"]
            })
        
        return sorted(leaderboard, key=lambda x: x["total_points"], reverse=True)
    
    def has_user_predicted(self, username, week_num):
        """Check if user has already made predictions for a week"""
        predictions = self.load_predictions(week_num, username)
        return len(predictions) > 0
    
    def save_fixtures(self, week_num, fixtures_df):
        """Save fixtures for a week to GitHub"""
        file_path = f"fixtures/week{week_num}.csv"
        try:
            csv_content = fixtures_df.to_csv(index=False)
            commit_message = f"Add fixtures for Week {week_num}"
            
            # Check if file already exists
            _, sha = self._get_file_from_github(file_path)
            if sha:
                commit_message = f"Update fixtures for Week {week_num}"
            
            self._save_file_to_github(file_path, csv_content, commit_message, sha)
            return True
        except Exception as e:
            print(f"Error saving fixtures for week {week_num}: {e}")
            return False
    
    def save_results(self, week_num, results_df):
        """Save results for a week to GitHub"""
        file_path = f"results/week{week_num}.csv"
        try:
            csv_content = results_df.to_csv(index=False)
            commit_message = f"Add results for Week {week_num}"
            
            # Check if file already exists
            _, sha = self._get_file_from_github(file_path)
            if sha:
                commit_message = f"Update results for Week {week_num}"
            
            self._save_file_to_github(file_path, csv_content, commit_message, sha)
            return True
        except Exception as e:
            print(f"Error saving results for week {week_num}: {e}")
            return False

# Keep the original class name for backward compatibility
class DataManager(GitHubDataManager):
    pass
