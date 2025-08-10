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

# Initialize managers
auth_manager = AuthManager()
data_manager = DataManager()
config_manager = ConfigManager()

# Initialize users file
config_manager.initialize_users()


def main():
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


def display_leaderboard():
    """Display the leaderboard"""
    st.subheader("🏆 Leaderboard")

    leaderboard = data_manager.get_leaderboard()

    if not leaderboard:
        st.info("No predictions submitted yet!")
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
            with st.expander(f"{i + 1}. {user['display_name']} - {user['total_points']} points"):
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