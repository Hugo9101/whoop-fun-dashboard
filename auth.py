import requests
import secrets
import os
from urllib.parse import urlencode, urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI  = "https://whoop.com"

auth_url = "https://api.prod.whoop.com/oauth/oauth2/auth?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "read:sleep read:recovery read:workout read:profile read:cycles offline",
    "state": secrets.token_hex(8)
})

print("🔐 Visit this URL in your browser:")
print(auth_url)

raw = input("\n📌 Paste the full redirect URL (or just the code): ").strip()
if raw.startswith("http"):
    parsed = parse_qs(urlparse(raw).query)
    code = parsed.get("code", [raw])[0]
else:
    code = raw

response = requests.post(
    "https://api.prod.whoop.com/oauth/oauth2/token",
    data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
)

token_info = response.json()
access_token  = token_info["access_token"]
refresh_token = token_info.get("refresh_token")

# Auto-save tokens to .env
with open(".env", "r") as f:
    env_contents = f.read()

for key, value in [("WHOOP_ACCESS_TOKEN", access_token), ("WHOOP_REFRESH_TOKEN", refresh_token)]:
    if key in env_contents:
        env_contents = "\n".join(
            [line if not line.startswith(key) else f"{key}={value}" 
             for line in env_contents.splitlines()]
        )
    else:
        env_contents += f"\n{key}={value}"

with open(".env", "w") as f:
    f.write(env_contents)

print("\n✅ Tokens saved to .env")
print(f"Access Token:  {access_token[:20]}...")
print(f"Refresh Token: {refresh_token[:20]}...")