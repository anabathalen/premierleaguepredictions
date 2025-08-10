import streamlit as st
from config import ConfigManager


class AuthManager:
    def __init__(self):
        self.config = ConfigManager()

    def authenticate_user(self, username, passcode):
        """Authenticate user credentials"""
        users = self.config.get_users()
        if username in users and users[username]["passcode"] == passcode:
            return {
                "username": username,
                "display_name": users[username]["display_name"],
                "is_admin": users[username].get("is_admin", False)
            }
        return None

    def login_form(self):
        """Display login form"""
        st.title("🏆 Premier League Predictions League")
        st.markdown("---")

        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            passcode = st.text_input("Passcode", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if username and passcode:
                    user = self.authenticate_user(username, passcode)
                    if user:
                        st.session_state.user = user
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("Invalid username or passcode!")
                else:
                    st.warning("Please enter both username and passcode")

    def logout(self):
        """Logout current user"""
        if "user" in st.session_state:
            del st.session_state.user
        if "logged_in" in st.session_state:
            del st.session_state.logged_in
        st.rerun()

    def require_login(self):
        """Check if user is logged in, redirect to login if not"""
        if "logged_in" not in st.session_state or not st.session_state.logged_in:
            return False
        return True

    def is_admin(self):
        """Check if current user is admin"""
        return (st.session_state.get("user", {}).get("is_admin", False))

    def get_current_user(self):
        """Get current logged in user"""
        return st.session_state.get("user", {})