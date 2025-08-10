import streamlit as st
import pandas as pd
import os
from auth import AuthManager
from data_manager import DataManager
from config import ConfigManager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Page config
st.set_page_config(
    page_title="Premier League Predictions",
    page_icon="⚽",
    layout="wide"
)

# Test encryption key and show helpful error message
try:
    from crypto_utils import DataEncryption
    test_encryption = DataEncryption()
    st.success("🔑 Encryption key loaded successfully!")
except Exception as e:
    st.error("🔑 Encryption Key Problem!")
    st.write("**Error:**", str(e))
    st.write("**Solution:** Go to your Streamlit Cloud app settings → Secrets and add:")
    st.code('ENCRYPTION_KEY = "YourSecretKeyHere"')
    st.write("Make sure the key is at least 8 characters long!")
    st.stop()

# Initialize managers
auth_manager = AuthManager()
data_manager = DataManager()
config_manager = ConfigManager()

# Initialize users file
try:
    st.info("🔄 Initializing users...")
    users = config_manager.initialize_users()
    
    if not users:
        st.error("❌ No users found after initialization")
        
        # Try to debug the issue
        st.write("**Debugging the issue:**")
        
        # Check if file exists
        users_file_exists = os.path.exists("users.json")
        st.write(f"users.json file exists: {users_file_exists}")
        
        if users_file_exists:
            # Try to read the raw file
            try:
                with open("users.json", "r") as f:
                    file_content = f.read()
                st.write(f"File size: {len(file_content)} characters")
                st.write("File starts with:", file_content[:50] + "..." if len(file_content) > 50 else file_content)
                
                # Try to decrypt
                from crypto_utils import DataEncryption
                enc = DataEncryption()
                decrypted = enc.decrypt_data(file_content)
                if decrypted:
                    st.write(f"✅ File decrypts successfully with {len(decrypted)} users")
                else:
                    st.write("❌ File exists but won't decrypt - wrong encryption key?")
            except Exception as e:
                st.write(f"Error reading file: {e}")
        else:
            st.write("File doesn't exist - trying to create it...")
            try:
                # Force create users
                test_users = {
                    "admin": {
                        "passcode": "admin123",
                        "is_admin": True,
                        "display_name": "Administrator"
                    }
                }
                from crypto_utils import DataEncryption
                enc = DataEncryption()
                enc.save_encrypted_file(test_users, "users.json")
                st.write("✅ Created users file successfully!")
                st.rerun()
            except Exception as e:
                st.write(f"❌ Failed to create users file: {e}")
        
        st.stop()
    else:
        st.success(f"✅ Loaded {len(users)} users successfully")
        
except Exception as e:
    st.error(f"❌ Error initializing users: {e}")
    st.write("**Common solutions:**")
    st.write("1. Make sure ENCRYPTION_KEY is set in Streamlit Cloud app settings → Secrets")
    st.write("2. The encryption key should be at least 8 characters long")
    st.write("3. Try clicking the 'Reboot app' button in Streamlit Cloud")
    st.stop()

def main():
    # Debug mode - add this temporarily
    with st.sidebar.expander("🔧 Debug Info"):
        if st.button("Reset Users File"):
            if os.path.exists("users.json"):
                os.remove("users.json")
            config_manager.initialize_users()
            st.success("Users file reset!")
            st.rerun()
        
        # Show file status
        st.write("File status:")
        st.write(f"users.json exists: {os.path.exists('users.json')}")
        
        # Test encryption
        try:
            users = config_manager.get_users()
            st.write(f"Users loaded: {len(users)} users")
            if "admin" in users:
                st.write("✅ Admin user found")
            else:
                st.write("❌ Admin user not found")
        except Exception as e:
            st.write(f"Error loading users: {e}")
    
    # Check authentication
    if not auth_manager.require_login():
        auth_manager.login_form()
        return
    
    # Get current user
    current_user = auth_manager.get_current_user()
    
    # Sidebar
    with st.sidebar:
        st.write(f"Welcome, {current_user['display_name']}!")
        
        if auth_manager.is_admin():
            st.markdown("### Admin Controls")
            admin_panel()
            st.markdown("### User Management")
            user_management_panel()
            st.markdown("### Scoring Test")
            scoring_test_panel()
        
        if st.button("Logout"):
            auth_manager.logout()
    
    # Main content
    current_week = config_manager.get_current_week()
    
    # Title
    st.title("🏆 Premier League Predictions League")
    st.markdown(f"**Current Week:** {current_week}")
    st.markdown("---")
    
    # Navigation
    tab1, tab2 = st.tabs(["📊 Leaderboard", "⚽ Make Predictions"])
    
    with tab1:
        display_leaderboard()
    
    with tab2:
        prediction_form(current_week, current_user['username'])

def admin_panel():
    """Admin control panel"""
    st.markdown("#### Week Management")
    current_week = config_manager.get_current_week()
    
    new_week = st.number_input("Set Current Week", 
                              min_value=1, 
                              max_value=38, 
                              value=current_week)
    
    if st.button("Update Week"):
        config_manager.set_current_week(new_week)
        st.success(f"Week updated to {new_week}")
        st.rerun()
    
    st.markdown("#### File Status")
    # Check what files exist
    fixtures_exist = os.path.exists(f"fixtures/week{current_week}.csv")
    results_exist = os.path.exists(f"results/week{current_week}.csv")
    
    st.write(f"Week {current_week} fixtures: {'✅' if fixtures_exist else '❌'}")
    st.write(f"Week {current_week} results: {'✅' if results_exist else '❌'}")

def user_management_panel():
    """Admin panel for managing users"""
    with st.expander("👥 Manage Users"):
        st.subheader("Current Users")
        
        # Show current users
        try:
            users = config_manager.get_users()
            for username, data in users.items():
                admin_badge = " 👑" if data.get('is_admin') else ""
                st.write(f"**{data['display_name']}** ({username}){admin_badge}")
        except Exception as e:
            st.error(f"Error loading users: {e}")
        
        st.subheader("Add New User")
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_passcode = st.text_input("Passcode")
            new_display_name = st.text_input("Display Name")
            is_admin = st.checkbox("Admin User")
            
            if st.form_submit_button("Add User"):
                if new_username and new_passcode and new_display_name:
                    try:
                        config_manager.add_user(new_username, new_passcode, new_display_name, is_admin)
                        st.success(f"Added user: {new_display_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding user: {e}")
                else:
                    st.warning("Please fill in all fields")

def scoring_test_panel():
    """Admin panel to test scoring system"""
    with st.expander("🧮 Test Scoring System"):
        st.write("This will show you how scoring works")
        
        current_week = config_manager.get_current_week()
        
        # Show completed weeks with results
        completed_weeks = []
        for week in range(1, current_week):
            results = data_manager.load_results(week)
            if results is not None:
                completed_weeks.append(week)
        
        if completed_weeks:
            selected_week = st.selectbox("Select week to view scores:", completed_weeks)
            
            if st.button("Calculate Scores for This Week"):
                try:
                    results = data_manager.load_results(selected_week)
                    predictions = data_manager.load_predictions(selected_week)
                    
                    if results is None:
                        st.error(f"No results file found for week {selected_week}")
                        return
                        
                    if not predictions:
                        st.warning(f"No predictions found for week {selected_week}")
                        return
                    
                    st.write(f"**Week {selected_week} Results:**")
                    st.dataframe(results)
                    
                    st.write(f"**User Predictions and Scores:**")
                    
                    for username, user_data in predictions.items():
                        if username == "admin":  # Skip admin
                            continue
                            
                        # Get display name
                        users = config_manager.get_users()
                        display_name = users.get(username, {}).get("display_name", username)
                        
                        st.write(f"**{display_name}:**")
                        
                        user_predictions = user_data["predictions"]
                        total_points = 0
                        
                        for i, result_row in results.iterrows():
                            if i < len(user_predictions):
                                pred = user_predictions[i]
                                points = data_manager.calculate_points(pred, result_row)
                                total_points += points
                                
                                result_str = f"{result_row['home_team']} {result_row['home_score']}-{result_row['away_score']} {result_row['away_team']}"
                                pred_str = f"Predicted: {pred['home_score']}-{pred['away_score']}"
                                
                                if points == 5:
                                    points_str = f"**{points} points** (Exact score! 🎯)"
                                elif points == 3:
                                    points_str = f"**{points} points** (Correct result! ✅)"
                                elif points == 1:
                                    points_str = f"**{points} points** (Correct goal difference! 📊)"
                                else:
                                    points_str = f"{points} points"
                                
                                st.write(f"   {result_str} | {pred_str} | {points_str}")
                        
                        st.write(f"   **Total: {total_points} points**")
                        st.markdown("---")
                        
                except Exception as e:
                    st.error(f"Error calculating scores: {e}")
                    st.write("Make sure your results CSV has the correct format:")
                    st.code("home_team,away_team,home_score,away_score")
        else:
            st.info(f"No completed weeks found. Add results files to test scoring.")
            
            # Show what files are needed
            st.write("**Files needed for scoring:**")
            for week in range(1, current_week):
                results_exist = os.path.exists(f"results/week{week}.csv")
                st.write(f"Week {week}: {'✅' if results_exist else '❌ Missing'} results/week{week}.csv")

def display_leaderboard():
    """Display the leaderboard"""
    st.subheader("🏆 Leaderboard")
    
    leaderboard = data_manager.get_leaderboard()
    
    if not leaderboard:
        st.info("No scores yet! Here's why:")
        st.write("📋 **To get scores on the leaderboard:**")
        st.write("1. Users make predictions for the current week")
        st.write("2. Admin adds results CSV after games are played")
        st.write("3. Admin advances to the next week")
        st.write("4. Scores appear here automatically!")
        
        # Show current status
        current_week = config_manager.get_current_week()
        st.write(f"**Current Status:** Week {current_week}")
        
        # Show who has made predictions for current week
        predictions = data_manager.load_predictions(current_week)
        if predictions:
            st.write(f"**Users who have predicted for Week {current_week}:**")
            for username in predictions.keys():
                if username != "admin":
                    user_info = config_manager.get_users().get(username, {})
                    display_name = user_info.get("display_name", username)
                    st.write(f"✅ {display_name}")
        else:
            st.write("No predictions submitted yet for the current week.")
        
        return
    
    # Create leaderboard dataframe
    df_data = []
    for i, user in enumerate(leaderboard):
        df_data.append({
            "Position": i + 1,
            "Player": user["display_name"],
            "Total Points": user["total_points"],
            "Weeks Played": user["weeks_played"],
            "Average Points": user["average_points"]
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Show weekly breakdown for top 3
    if len(leaderboard) > 0:
        st.subheader("📈 Weekly Breakdown (Top 3)")
        
        for i, user in enumerate(leaderboard[:3]):
            with st.expander(f"{i+1}. {user['display_name']} - {user['total_points']} points"):
                breakdown = user["weekly_breakdown"]
                if breakdown:
                    breakdown_df = pd.DataFrame([
                        {"Week": k.replace("week_", ""), "Points": v} 
                        for k, v in breakdown.items()
                    ])
                    st.bar_chart(breakdown_df.set_index("Week")["Points"])
                else:
                    st.write("No completed weeks yet")

def prediction_form(week_num, username):
    """Display prediction form for current week"""
    st.subheader(f"⚽ Week {week_num} Predictions")
    
    # Check if fixtures exist
    fixtures = data_manager.load_fixtures(week_num)
    if fixtures is None:
        st.error(f"Fixtures for week {week_num} not found! Please contact admin.")
        return
    
    # Check if user has already predicted
    has_predicted = data_manager.has_user_predicted(username, week_num)
    
    if has_predicted:
        st.info("You have already submitted predictions for this week!")
        
        # Show existing predictions
        existing_predictions = data_manager.load_predictions(week_num, username)
        st.subheader("Your Predictions:")
        
        for i, (_, fixture) in enumerate(fixtures.iterrows()):
            if i < len(existing_predictions):
                pred = existing_predictions[i]
                st.write(f"{fixture['home_team']} {pred['home_score']}-{pred['away_score']} {fixture['away_team']}")
        
        if st.button("Edit Predictions"):
            st.session_state.edit_predictions = True
            st.rerun()
        
        return
    
    # Check if in edit mode
    edit_mode = st.session_state.get("edit_predictions", False)
    if not edit_mode and has_predicted:
        return
    
    # Prediction form
    with st.form("predictions_form"):
        st.write("Make your predictions for this week's fixtures:")
        
        predictions = []
        
        # Load existing predictions if editing
        existing_predictions = data_manager.load_predictions(week_num, username) if edit_mode else []
        
        for i, (_, fixture) in enumerate(fixtures.iterrows()):
            st.markdown(f"**{fixture['home_team']} vs {fixture['away_team']}**")
            
            col1, col2, col3 = st.columns([2, 1, 2])
            
            # Get existing prediction if available
            existing_home = existing_predictions[i]['home_score'] if i < len(existing_predictions) else 0
            existing_away = existing_predictions[i]['away_score'] if i < len(existing_predictions) else 0
            
            with col1:
                st.write(fixture['home_team'])
            with col2:
                home_score = st.number_input(f"", min_value=0, max_value=10, 
                                           value=existing_home, key=f"home_{i}")
                away_score = st.number_input(f"", min_value=0, max_value=10, 
                                           value=existing_away, key=f"away_{i}")
            with col3:
                st.write(fixture['away_team'])
            
            predictions.append({
                "home_team": fixture['home_team'],
                "away_team": fixture['away_team'],
                "home_score": home_score,
                "away_score": away_score
            })
            
            st.markdown("---")
        
        submit_button = st.form_submit_button("Submit Predictions" if not edit_mode else "Update Predictions")
        
        if submit_button:
            # Save predictions
            data_manager.save_predictions(username, week_num, predictions)
            st.success("Predictions submitted successfully!")
            
            # Clear edit mode
            if "edit_predictions" in st.session_state:
                del st.session_state.edit_predictions
            
            st.rerun()

if __name__ == "__main__":
    main()
