import os
from config import ConfigManager
from crypto_utils import DataEncryption

# Debug script to check user creation
config = ConfigManager()
encryption = DataEncryption()

print("=== Debug User Authentication ===")

# Check if users.json exists
if os.path.exists("users.json"):
    print("✅ users.json file exists")
    
    # Try to load and decrypt users
    try:
        users = config.get_users()
        print(f"✅ Successfully loaded {len(users)} users:")
        for username, data in users.items():
            print(f"   - {username}: {data['display_name']} (admin: {data.get('is_admin', False)})")
    except Exception as e:
        print(f"❌ Error loading users: {e}")
        print("🔧 Recreating users file...")
        
        # Force recreate users
        os.remove("users.json")
        users = config.initialize_users()
        print(f"✅ Recreated users file with {len(users)} users")
else:
    print("❌ users.json file not found")
    print("🔧 Creating users file...")
    users = config.initialize_users()
    print(f"✅ Created users file with {len(users)} users")

print("\n=== Testing Authentication ===")
# Test authentication
from auth import AuthManager
auth = AuthManager()

test_result = auth.authenticate_user("admin", "admin123")
if test_result:
    print(f"✅ Admin authentication successful: {test_result}")
else:
    print("❌ Admin authentication failed")
    
    # Show what's actually in the users file
    users = config.get_users()
    if "admin" in users:
        print(f"Admin user exists with passcode: '{users['admin']['passcode']}'")
        print("Check if there are any extra spaces or characters")
    else:
        print("Admin user not found in users file!")

print("\n=== Current Encryption Key ===")
# Check encryption key (don't show the actual key for security)
try:
    import streamlit as st
    key_source = "Streamlit secrets"
    # Don't actually print the key
except:
    key_source = "Environment variable"

print(f"Encryption key source: {key_source}")
print("If using Streamlit Cloud, make sure ENCRYPTION_KEY is set in secrets!")
