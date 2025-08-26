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
            st.markdown("### Score Management")
            score_management_panel()
            st.markdown("### Results Management")
            results_management_panel()
            st.markdown("### Prediction Export")
            prediction_export_panel()
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
                
                # Test GitHub configuration
                st.write("**GitHub Configuration:**")
                try:
                    github_token = data_manager._get_secret('GITHUB_TOKEN')
                    github_repo_owner = data_manager._get_secret('GITHUB_REPO_OWNER')
                    github_repo_name = data_manager._get_secret('GITHUB_REPO_NAME')
                    
                    st.write(f"GITHUB_TOKEN: {'✅ Set' if github_token else '❌ Not set'}")
                    st.write(f"GITHUB_REPO_OWNER: {'✅ ' + github_repo_owner if github_repo_owner else '❌ Not set'}")
                    st.write(f"GITHUB_REPO_NAME: {'✅ ' + github_repo_name if github_repo_name else '❌ Not set'}")
                    
                    if all([github_token, github_repo_owner, github_repo_name]):
                        st.write("✅ GitHub configuration complete")
                    else:
                        st.write("❌ GitHub configuration incomplete")
                        
                except Exception as e:
                    st.write(f"Error checking GitHub config: {e}")
                
                # Test GitHub connection
                if st.button("Test GitHub Connection"):
                    try:
                        # Try to get a simple file from GitHub
                        test_result = data_manager._get_file_from_github("settings.json")
                        if test_result[0] is not None:
                            st.success("✅ GitHub connection successful!")
                        else:
                            st.warning("⚠️ GitHub connected but settings.json not found")
                    except Exception as e:
                        st.error(f"❌ GitHub connection failed: {e}")
        
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
    tab1, tab2, tab3 = st.tabs(["📊 LEADERBOARD", "⚽ DO PREDICTIONS", "📜 MY PREDICTIONS"])
    
    with tab1:
        display_leaderboard()
    
    with tab2:
        prediction_form(current_week, current_user['username'])
    
    with tab3:
        view_user_predictions(current_user['username'])

def admin_panel():
    """Admin control panel"""
    st.markdown("#### Week Management")
    current_week = config_manager.get_current_week()
    
    new_week = st.number_input("Set Current Week", 
                              min_value=1, 
                              max_value=38, 
                              value=current_week)
    
    if st.button("Update Week"):
        old_week = current_week
        config_manager.set_current_week(new_week)
        st.success(f"Week updated from {old_week} to {new_week}")
        
        # Show information about leaderboard recalculation
        if new_week > old_week:
            st.info(f"📊 Leaderboard will now include results through Week {new_week - 1}")
        elif new_week < old_week:
            st.info(f"📊 Leaderboard will now only include results through Week {new_week - 1}")
        
        st.rerun()
    
    st.markdown("#### Prediction Settings")
    predictions_open = config_manager.are_predictions_open()
    
    new_predictions_status = st.checkbox("Accept Predictions", value=predictions_open)
    
    if st.button("Update Prediction Settings"):
        config_manager.set_predictions_open(new_predictions_status)
        status_text = "open" if new_predictions_status else "closed"
        st.success(f"Predictions are now {status_text}")
        st.rerun()
    
    st.markdown("#### File Status")
    # Check what files exist in GitHub (not local files)
    fixtures_exist = data_manager.load_fixtures(current_week) is not None
    results_exist = data_manager.load_results(current_week) is not None
    
    st.write(f"Week {current_week} fixtures: {'✅' if fixtures_exist else '❌'}")
    st.write(f"Week {current_week} results: {'✅' if results_exist else '❌'}")
    st.write(f"Predictions: {'✅ Open' if predictions_open else '❌ Closed'}")
    
    # Show leaderboard calculation info
    if current_week > 1:
        st.markdown("#### Leaderboard Info")
        st.write(f"📊 Current leaderboard includes completed weeks: 1 to {current_week - 1}")
        
        # Check how many weeks have results
        completed_weeks = 0
        for week in range(1, current_week):
            if data_manager.load_results(week) is not None:
                completed_weeks += 1
        
        st.write(f"📈 Weeks with results uploaded: {completed_weeks} out of {current_week - 1}")
    else:
        st.write("📊 No completed weeks yet - leaderboard will show after Week 1 results are uploaded")

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
                        
                        # Save results using data manager (saves to GitHub)
                        with st.spinner("Saving results to GitHub..."):
                            data_manager.save_results(selected_week, results_df)
                        
                        st.success(f"✅ Results saved for week {selected_week}!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Failed to save results: {str(e)}")
                        if "GitHub API Error" in str(e):
                            st.error("Check your GitHub token permissions and repository settings.")
                        elif "verification failed" in str(e):
                            st.error("Results were not properly saved to GitHub.")
                        else:
                            st.error("Please check your GitHub configuration in Streamlit secrets.")

def score_management_panel():
    """Admin panel to manually adjust user scores"""
    with st.expander("🔢 Manual Score Management"):
        st.subheader("Adjust User Scores")
        
        try:
            # Get current leaderboard
            leaderboard = data_manager.get_leaderboard()
            
            if not leaderboard:
                st.info("No users with scores yet.")
                return
            
            # Select user
            user_options = [f"{user['display_name']} ({user['username']})" for user in leaderboard]
            selected_user_idx = st.selectbox("Select User", range(len(user_options)), 
                                           format_func=lambda x: user_options[x])
            
            if selected_user_idx is not None:
                selected_user = leaderboard[selected_user_idx]
                username = selected_user['username']
                
                st.write(f"**Current Score:** {selected_user['total_points']} points")
                st.write(f"**Weeks Played:** {selected_user['weeks_played']}")
                
                # Show weekly breakdown
                if selected_user['weekly_breakdown']:
                    st.write("**Weekly Breakdown:**")
                    for week, points in selected_user['weekly_breakdown'].items():
                        week_num = week.replace("week_", "")
                        st.write(f"Week {week_num}: {points} points")
                
                st.markdown("---")
                
                # Manual score adjustment
                st.subheader("Manual Adjustment")
                adjustment_type = st.radio("Adjustment Type", 
                                         ["Add Points", "Subtract Points", "Set Total Points"])
                
                if adjustment_type in ["Add Points", "Subtract Points"]:
                    points_change = st.number_input("Points to adjust", min_value=1, max_value=100, value=1)
                    reason = st.text_input("Reason for adjustment")
                    
                    if st.button(f"{adjustment_type}"):
                        if reason:
                            try:
                                # Calculate the actual points change
                                if adjustment_type == "Add Points":
                                    actual_change = points_change
                                else:
                                    actual_change = -points_change
                                
                                # Save the manual adjustment
                                current_user = auth_manager.get_current_user()
                                success = data_manager.save_manual_adjustment(
                                    username, 
                                    actual_change, 
                                    reason, 
                                    current_user['username']
                                )
                                
                                if success:
                                    st.success(f"Successfully adjusted {selected_user['display_name']}'s score by {actual_change} points!")
                                    st.info(f"Reason: {reason}")
                                    st.rerun()
                                else:
                                    st.error("Failed to save adjustment.")
                            except Exception as e:
                                st.error(f"Error adjusting score: {e}")
                        else:
                            st.warning("Please provide a reason for the adjustment")
                
                elif adjustment_type == "Set Total Points":
                    new_total = st.number_input("New total points", min_value=0, value=selected_user['total_points'])
                    reason = st.text_input("Reason for setting new total")
                    
                    if st.button("Set Total Points"):
                        if reason:
                            try:
                                # Calculate what adjustment is needed to reach the new total
                                current_total = selected_user['total_points']
                                points_change = new_total - current_total
                                
                                # Save the manual adjustment
                                current_user = auth_manager.get_current_user()
                                success = data_manager.save_manual_adjustment(
                                    username, 
                                    points_change, 
                                    f"Set total to {new_total}: {reason}", 
                                    current_user['username']
                                )
                                
                                if success:
                                    st.success(f"Successfully set {selected_user['display_name']}'s score to {new_total} points!")
                                    st.info(f"Reason: {reason}")
                                    st.rerun()
                                else:
                                    st.error("Failed to save adjustment.")
                            except Exception as e:
                                st.error(f"Error setting total points: {e}")
                        else:
                            st.warning("Please provide a reason for the adjustment")
                
                # Show manual adjustments history
                adjustments = data_manager.get_manual_adjustments(username)
                if adjustments:
                    st.markdown("---")
                    st.subheader("Manual Adjustment History")
                    for adj in reversed(adjustments[-5:]):  # Show last 5 adjustments
                        st.write(f"**{adj['timestamp'][:19]}** by {adj['admin_user']}: {'+' if adj['points_change'] > 0 else ''}{adj['points_change']} points")
                        st.write(f"Reason: {adj['reason']}")
                        st.write("")
                            
        except Exception as e:
            st.error(f"Error in score management: {e}")

def prediction_export_panel():
    """Admin panel to export predictions as spreadsheet"""
    with st.expander("📊 Export Predictions"):
        st.subheader("Download Unencrypted Predictions")
        
        current_week = config_manager.get_current_week()
        
        # Week selector for export
        available_weeks = []
        for week in range(1, current_week + 1):
            predictions = data_manager.load_predictions(week)
            if predictions:
                available_weeks.append(week)
        
        if not available_weeks:
            st.info("No predictions available for export yet.")
            return
        
        selected_weeks = st.multiselect("Select weeks to export", 
                                       available_weeks, 
                                       default=available_weeks)
        
        export_format = st.radio("Export Format", ["CSV", "Excel"])
        
        if st.button("Generate Export"):
            try:
                # Create export data
                export_data = []
                users = config_manager.get_users()
                
                for week in selected_weeks:
                    predictions = data_manager.load_predictions(week)
                    fixtures = data_manager.load_fixtures(week)
                    results = data_manager.load_results(week)
                    
                    if not predictions or fixtures is None:
                        continue
                    
                    for username, pred_data in predictions.items():
                        if username == "admin":
                            continue
                            
                        # Handle both old and new prediction formats
                        if isinstance(pred_data, dict) and "predictions" in pred_data:
                            user_predictions = pred_data["predictions"]
                            submitted_at = pred_data.get("submitted_at", "")
                        else:
                            user_predictions = pred_data
                            submitted_at = ""
                        
                        user_info = users.get(username, {})
                        display_name = user_info.get("display_name", username)
                        
                        for i, prediction in enumerate(user_predictions):
                            if i < len(fixtures):
                                fixture = fixtures.iloc[i]
                                
                                # Get actual result if available
                                actual_home = actual_away = ""
                                if results is not None and i < len(results):
                                    result_row = results.iloc[i]
                                    actual_home = result_row.get('home_score', '')
                                    actual_away = result_row.get('away_score', '')
                                
                                export_data.append({
                                    'Week': week,
                                    'Username': username,
                                    'Display_Name': display_name,
                                    'Home_Team': fixture['home_team'],
                                    'Away_Team': fixture['away_team'],
                                    'Predicted_Home': prediction.get('home_score', ''),
                                    'Predicted_Away': prediction.get('away_score', ''),
                                    'Actual_Home': actual_home,
                                    'Actual_Away': actual_away,
                                    'Submitted_At': submitted_at
                                })
                
                if export_data:
                    import pandas as pd
                    df = pd.DataFrame(export_data)
                    
                    if export_format == "CSV":
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"predictions_weeks_{'-'.join(map(str, selected_weeks))}.csv",
                            mime='text/csv'
                        )
                    else:  # Excel
                        from io import BytesIO
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Predictions')
                        
                        st.download_button(
                            label="Download Excel",
                            data=output.getvalue(),
                            file_name=f"predictions_weeks_{'-'.join(map(str, selected_weeks))}.xlsx",
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    
                    st.success(f"Export ready! {len(export_data)} prediction records found.")
                    
                    # Show preview
                    st.subheader("Preview (First 10 rows)")
                    st.dataframe(df.head(10))
                    
                else:
                    st.warning("No prediction data found for selected weeks.")
                    
            except Exception as e:
                st.error(f"Error generating export: {e}")

def prediction_export_panel():
    """Admin panel to export predictions to Excel"""
    with st.expander("📊 Export Predictions"):
        st.subheader("Export Predictions to Excel")
        
        current_week = config_manager.get_current_week()
        
        # Week selector for export
        available_weeks = []
        for week in range(1, current_week + 1):
            predictions = data_manager.load_predictions(week)
            if predictions:  # Only show weeks that have predictions
                available_weeks.append(week)
        
        if not available_weeks:
            st.info("No weeks with predictions available for export.")
            return
        
        selected_week = st.selectbox(
            "Select week to export:",
            available_weeks,
            index=len(available_weeks) - 1  # Default to latest week
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export to Excel"):
                try:
                    workbook = data_manager.export_predictions_to_excel(selected_week)
                    
                    if workbook:
                        # Save to bytes buffer
                        from io import BytesIO
                        buffer = BytesIO()
                        workbook.save(buffer)
                        buffer.seek(0)
                        
                        # Create download button
                        st.download_button(
                            label="⬇️ Download Excel File",
                            data=buffer,
                            file_name=f"Week_{selected_week}_Predictions.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success(f"Excel file ready for download!")
                        
                        # Show preview
                        predictions = data_manager.load_predictions(selected_week)
                        st.write(f"**Preview:** {len(predictions)} users made predictions for week {selected_week}")
                        
                    else:
                        st.error("Failed to create Excel file.")
                        
                except Exception as e:
                    st.error(f"Error exporting predictions: {e}")
        
        with col2:
            # Show current week status
            st.write("**Week Status:**")
            for week in available_weeks[-5:]:  # Show last 5 weeks
                predictions = data_manager.load_predictions(week)
                user_count = len([u for u in predictions.keys() if u != "admin"])
                st.write(f"Week {week}: {user_count} predictions")

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
    current_week = config_manager.get_current_week()
    
    for i, user in enumerate(leaderboard):
        df_data.append({
            "Pos": i + 1,
            "Player": user["display_name"],
            "Points": user["total_points"],
            "Last Week": user["current_week_points"] if current_week > 1 else 0
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
    
    # Check if predictions are open
    if not config_manager.are_predictions_open():
        st.error("🔒 Predictions are currently closed!")
        st.info("Contact the admin if you think this is a mistake.")
        return
    
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


def view_user_predictions(username):
    """Display user's predictions for any given week"""
    st.subheader("📜 Your Prediction History")
    
    current_week = config_manager.get_current_week()
    
    # Week selector
    selected_week = st.selectbox(
        "Select Week to View:",
        options=list(range(1, current_week + 1)),
        index=current_week - 1 if current_week > 1 else 0
    )
    
    # Get user's predictions for the selected week
    user_predictions = data_manager.get_user_predictions_for_week(username, selected_week)
    
    if user_predictions is None:
        st.info(f"No predictions found for Week {selected_week}")
        return
    
    if not user_predictions:
        st.info(f"You haven't made predictions for Week {selected_week} yet")
        return
    
    st.subheader(f"Your Predictions for Week {selected_week}")
    
    # Display predictions in a nice format
    for pred in user_predictions:
        col1, col2, col3 = st.columns([3, 1, 3])
        
        with col1:
            st.write(f"**{pred['home_team']}**")
        
        with col2:
            st.write(f"**{pred['predicted_home_score']}-{pred['predicted_away_score']}**")
        
        with col3:
            st.write(f"**{pred['away_team']}**")
    
    # Check if results are available for this week
    results = data_manager.load_results(selected_week)
    if results is not None and len(results) > 0:
        st.markdown("---")
        st.subheader(f"Actual Results for Week {selected_week}")
        
        total_points = 0
        for i, (_, result) in enumerate(results.iterrows()):
            if i < len(user_predictions):
                pred = user_predictions[i]
                
                # Calculate points for this match
                prediction_data = {
                    'home_score': pred['predicted_home_score'],
                    'away_score': pred['predicted_away_score']
                }
                points = data_manager.calculate_points(prediction_data, result)
                total_points += points
                
                col1, col2, col3, col4 = st.columns([3, 1, 3, 1])
                
                with col1:
                    st.write(f"{result['home_team']}")
                
                with col2:
                    st.write(f"**{int(result['home_score'])}-{int(result['away_score'])}**")
                
                with col3:
                    st.write(f"{result['away_team']}")
                
                with col4:
                    st.write(f"**{points} pts**")
        
        st.markdown("---")
        st.write(f"**Total Points for Week {selected_week}: {total_points}**")


if __name__ == "__main__":
    main()
