import pandas as pd
import os
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_utils import DataEncryption
from config import ConfigManager, POINTS_CORRECT_RESULT, POINTS_EXACT_SCORE, POINTS_GOAL_DIFFERENCE

class DataManager:
    def __init__(self):
        self.encryption = DataEncryption()
        self.config = ConfigManager()
        
        # Create directories if they don't exist
        os.makedirs("predictions", exist_ok=True)
        os.makedirs("results", exist_ok=True)
        os.makedirs("fixtures", exist_ok=True)
    
    def load_fixtures(self, week_num):
        """Load fixtures for a specific week"""
        fixture_file = f"fixtures/week{week_num}.csv"
        try:
            return pd.read_csv(fixture_file)
        except FileNotFoundError:
            return None
    
    def load_results(self, week_num):
        """Load results for a specific week"""
        results_file = f"results/week{week_num}.csv"
        try:
            return pd.read_csv(results_file)
        except FileNotFoundError:
            return None
    
    def save_predictions(self, username, week_num, predictions):
        """Save user predictions for a week"""
        predictions_file = f"predictions/week{week_num}.json"
        
        # Load existing predictions for this week
        all_predictions = self.encryption.load_encrypted_file(predictions_file) or {}
        
        # Update predictions for this user
        all_predictions[username] = {
            "predictions": predictions,
            "submitted_at": pd.Timestamp.now().isoformat()
        }
        
        # Save back to file
        self.encryption.save_encrypted_file(all_predictions, predictions_file)
    
    def load_predictions(self, week_num, username=None):
        """Load predictions for a week, optionally for a specific user"""
        predictions_file = f"predictions/week{week_num}.json"
        all_predictions = self.encryption.load_encrypted_file(predictions_file) or {}
        
        if username:
            return all_predictions.get(username, {}).get("predictions", [])
        return all_predictions
    
    def calculate_points(self, prediction, actual_result):
        """Calculate points for a single match prediction"""
        if not actual_result or pd.isna(actual_result.get('home_score')) or pd.isna(actual_result.get('away_score')):
            return 0
        
        pred_home = prediction.get('home_score', 0)
        pred_away = prediction.get('away_score', 0)
        actual_home = int(actual_result['home_score'])
        actual_away = int(actual_result['away_score'])
        
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

    def has_user_predicted(self, username, week_num):
        """Check if user has already made predictions for a week"""
        predictions = self.load_predictions(week_num, username)
        return len(predictions) > 0
