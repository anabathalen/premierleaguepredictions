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
    page_title="Premier League Predictions 2025-26",
    page_icon="⚽",
    layout="wide"
)

# Test encryption key and show helpful error message
try:
    from crypto_utils import DataEncryption
    test_encryption = DataEncryption()
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
    users = config_manager.initialize_users()
    
    if not users:
        st.error("Failed to initialize users. Please check your encryption key.")
        st.stop()
        
except Exception as e:
    st.error(f"Error initializing users: {e}")
    st.write("**Common solutions:**")
    st.write("1. Make sure ENCRYPTION_KEY is set in Streamlit Cloud app settings → Secrets")
    st.write("2. The encryption key should be at least 8 characters long")
    st.write("3. Try clicking the 'Reboot app' button in Streamlit Cloud")
    st.stop()

def display_front_page_blurb():
    """Display admin-configured front page message"""
    try:
        # Try to load front page message from config
        blurb = config_manager.get_front_page_blurb()
        if blurb:
            st.info(blurb)
    except:
        # If no blurb exists, show default
        pass

def main():
    # Check authentication
    if not auth_manager.require_login():
        display_front_page_blurb()
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
            st.markdown("### Results Management")
            results_management_panel()
            st.markdown("### Front Page Settings")
            front_page_management_panel()
            
            # Only show debug info for admin
            with st.expander("🔧 Debug Info"):
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
        
        if st.button("Logout"):
            auth_manager.logout()
    
    # Main content
    current_week = config_manager.get_current_week()
    
    # Title
    st.title("🏆 Premier League Predictions 2025-26")
    st.markdown(f"**Current Week:** {current_week}")
    
    # Show front page blurb for logged in users too
    display_front_page_blurb()
    
    st.markdown("---")
    
    # Navigation
    tab1, tab2 = st.tabs(["📊 LEADERBOARD", "⚽ DO PREDICTIONS"])
    
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

def results_management_panel():
    """Admin panel to input results and generate results files"""
    with st.expander("📊 Input Match Results"):
        current_week = config_manager.get_current_week()
        
        # Week selector
        selected_week = st.selectbox(
            "Select week to input results:", 
            range(1, current_week + 1),
            index=current_week - 1
        )
        
        # Check if fixtures exist for selected week
        fixtures = data_manager.load_fixtures(selected_week)
        if fixtures is None:
            st.error(f"No fixtures found for week {selected_week}")
            return
        
        # Check if results already exist
        existing_results = data_manager.load_results(selected_week)
        results_exist = existing_results is not None
        
        if results_exist:
            st.info(f"Results already exist for week {selected_week}")
            if st.checkbox("Edit existing results"):
                show_results_form = True
            else:
                st.dataframe(existing_results)
                show_results_form = False
        else:
            show_results_form = True
        
        if show_results_form:
            with st.form(f"results_form_week_{selected_week}"):
                st.write(f"**Input results for Week {selected_week}:**")
                
                results_data = []
                
                for i, (_, fixture) in enumerate(fixtures.iterrows()):
                    st.markdown(f"**{fixture['home_team']} vs {fixture['away_team']}**")
                    
                    # Get existing results if available
                    existing_home = 0
                    existing_away = 0
                    if results_exist and i < len(existing_results):
                        existing_home = existing_results.iloc[i]['home_score']
                        existing_away = existing_results.iloc[i]['away_score']
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        home_score = st.number_input(
                            f"{fixture['home_team']}:", 
                            min_value=0, max_value=20, 
                            value=int(existing_home), 
                            key=f"result_home_{selected_week}_{i}"
                        )
                    with col2:
                        away_score = st.number_input(
                            f"{fixture['away_team']}:", 
                            min_value=0, max_value=20, 
                            value=int(existing_away), 
                            key=f"result_away_{selected_week}_{i}"
                        )
                    
                    results_data.append({
                        'home_team': fixture['home_team'],
                        'away_team': fixture['away_team'],
                        'home_score': home_score,
                        'away_score': away_score
                    })
                
                if st.form_submit_button("Save Results"):
                    try:
                        # Create results DataFrame
                        results_df = pd.DataFrame(results_data)
                        
                        # Create results directory if it doesn't exist
                        os.makedirs("results", exist_ok=True)
                        
                        # Save results file
                        results_file = f"results/week{selected_week}.csv"
                        results_df.to_csv(results_file, index=False)
                        
                        st.success(f"Results saved for week {selected_week}!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error saving results: {e}")

def front_page_management_panel():
    """Admin panel to manage front page message"""
    with st.expander("📢 Front Page Message"):
        st.write("Set a message that appears on the front page before login")
        
        # Get current blurb
        try:
            current_blurb = config_manager.get_front_page_blurb()
        except:
            current_blurb = ""
        
        # Text area for the blurb
        new_blurb = st.text_area(
            "Front page message:",
            value=current_blurb,
            height=100,
            help="This message will appear on the login page. Leave empty to show no message."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Message"):
                try:
                    config_manager.set_front_page_blurb(new_blurb)
                    st.success("Front page message updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving message: {e}")
        
        with col2:
            if st.button("Clear Message"):
                try:
                    config_manager.set_front_page_blurb("")
                    st.success("Front page message cleared!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing message: {e}")
        
        # Preview
        if new_blurb:
            st.write("**Preview:**")
            st.info(new_blurb)

def display_leaderboard():
    """Display the leaderboard"""
    st.subheader("🏆 Leaderboard")
    
    leaderboard = data_manager.get_leaderboard()
    
    if not leaderboard:
        st.info("No scores yet! Either it is week 1 or Ana has fucked up.")
        
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
            "Pos": i + 1,
            "Player": user["display_name"],
            "Points": user["total_points"],
            "Weeks": user["weeks_played"],
            "Avg": user["average_points"]
        })
    
    df = pd.DataFrame(df_data)
    
    # Display leaderboard with better mobile formatting
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Show top 3 with medals
    if len(leaderboard) >= 3:
        st.markdown("### 🏆 Top 3")
        medals = ["🥇", "🥈", "🥉"]
        for i in range(min(3, len(leaderboard))):
            user = leaderboard[i]
            st.markdown(f"{medals[i]} **{user['display_name']}** - {user['total_points']} points")
    
    # Show weekly breakdown for top 3
    if len(leaderboard) > 0:
        st.subheader("📈 Weekly Breakdown")
        
        for i, user in enumerate(leaderboard[:3]):
            with st.expander(f"{i+1}. {user['display_name']} - {user['total_points']} points"):
                breakdown = user["weekly_breakdown"]
                if breakdown:
                    # Simple text breakdown instead of chart for mobile compatibility
                    for week, points in breakdown.items():
                        week_num = week.replace("week_", "")
                        st.write(f"Week {week_num}: {points} points")
                else:
                    st.write("No completed weeks yet")

def prediction_form(week_num, username):
    st.subheader(f"⚽ Week {week_num} Predictions")
    fixtures = data_manager.load_fixtures(week_num)
    if fixtures is None:
        st.error(f"Fixtures for week {week_num} not found! Please contact admin.")
        return

    has_predicted = data_manager.has_user_predicted(username, week_num)
    edit_mode = st.session_state.get("edit_predictions", False)

    # If user has predicted and is NOT editing, show predictions + edit button
    if has_predicted and not edit_mode:
        st.info("You have already submitted predictions for this week!")

        existing_predictions = data_manager.load_predictions(week_num, username)
        st.subheader("Your Current Predictions:")
        for i, (_, fixture) in enumerate(fixtures.iterrows()):
            if i < len(existing_predictions):
                pred = existing_predictions[i]
                st.write(f"⚽ **{fixture['home_team']} {pred['home_score']}-{pred['away_score']} {fixture['away_team']}**")

        st.markdown("---")
        if st.button("Edit Predictions"):
            st.session_state.edit_predictions = True
            st.rerun()
        return

    # If in edit mode or making new predictions, show the prediction form
    with st.form("predictions_form"):
        st.write("Make your predictions for this week's fixtures:")

        predictions = []
        existing_predictions = data_manager.load_predictions(week_num, username) if edit_mode else []

        for i, (_, fixture) in enumerate(fixtures.iterrows()):
            existing_home = existing_predictions[i]['home_score'] if i < len(existing_predictions) else 0
            existing_away = existing_predictions[i]['away_score'] if i < len(existing_predictions) else 0

            home_score = st.number_input(
                f"{fixture['home_team']}:",
                min_value=0, max_value=10,
                value=existing_home,
                key=f"home_{i}"
            )
            away_score = st.number_input(
                f"{fixture['away_team']}:",
                min_value=0, max_value=10,
                value=existing_away,
                key=f"away_{i}"
            )

            predictions.append({
                "home_team": fixture['home_team'],
                "away_team": fixture['away_team'],
                "home_score": home_score,
                "away_score": away_score
            })
            st.markdown("---")

        if st.form_submit_button("Submit Predictions" if not edit_mode else "Update Predictions"):
            data_manager.save_predictions(username, week_num, predictions)
            st.success("Predictions submitted successfully!")
            if "edit_predictions" in st.session_state:
                del st.session_state.edit_predictions
            st.rerun()


if __name__ == "__main__":
    main()
