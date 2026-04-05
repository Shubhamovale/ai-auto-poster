from google_auth_oauthlib.flow import InstalledAppFlow
import glob

# Check JSON files available
files = glob.glob("*.json")
print("JSON files found:", files)

CLIENT_SECRET_FILE = "client_secret.json"  # change after checking above

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
creds = flow.run_local_server(port=8080)

print("\n✅ YOUR REFRESH TOKEN:")
print(creds.refresh_token)