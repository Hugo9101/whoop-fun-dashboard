import requests
import os
from dotenv import load_dotenv, set_key

load_dotenv()

BASE_URL      = "https://api.prod.whoop.com/developer"
CLIENT_ID     = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
ENV_FILE      = ".env"

# ── Token Management ───────────────────────────────────────────────────────────

def get_access_token():
    return os.getenv("WHOOP_ACCESS_TOKEN")

def refresh_access_token():
    print("🔄 Refreshing access token...")
    response = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type":    "refresh_token",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": os.getenv("WHOOP_REFRESH_TOKEN"),
        }
    )
    tokens = response.json()
    if "access_token" not in tokens:
        raise RuntimeError(f"❌ Token refresh failed: {tokens}")

    set_key(ENV_FILE, "WHOOP_ACCESS_TOKEN", tokens["access_token"])
    set_key(ENV_FILE, "WHOOP_REFRESH_TOKEN", tokens["refresh_token"])
    os.environ["WHOOP_ACCESS_TOKEN"] = tokens["access_token"]
    os.environ["WHOOP_REFRESH_TOKEN"] = tokens["refresh_token"]
    print("✅ Token refreshed and saved to .env")
    return tokens["access_token"]

def make_request(endpoint):
    """Makes API request, auto-refreshes token if expired."""
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)

    if response.status_code == 401:
        token = refresh_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)

    if not response.ok:
        print(f"  !! {response.status_code} from {endpoint}: {response.text}")
    response.raise_for_status()
    return response.json()

# ── Endpoints ──────────────────────────────────────────────────────────────────

def get_profile():
    print("👤 Fetching profile...")
    return make_request("/v2/user/profile/basic")

def get_sleep():
    print("😴 Fetching sleep data...")
    data = make_request("/v2/activity/sleep")
    records = data.get("records", [])
    print(f"   → {len(records)} records found")
    return records

def get_recovery():
    print("💚 Fetching recovery data...")
    data = make_request("/v2/recovery")
    records = data.get("records", [])
    print(f"   → {len(records)} records found")
    return records

def get_workouts():
    print("🏋️ Fetching workout data...")
    data = make_request("/v2/activity/workout")
    records = data.get("records", [])
    print(f"   → {len(records)} records found")
    return records

def get_cycles():
    print("🔁 Fetching cycle data...")
    data = make_request("/v2/cycle")
    records = data.get("records", [])
    print(f"   → {len(records)} records found")
    return records

# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    profile = get_profile()
    print(f"\n👤 Logged in as: {profile.get('first_name')} {profile.get('last_name')}")

    sleep    = get_sleep()
    recovery = get_recovery()
    workouts = get_workouts()
    cycles   = get_cycles()

    print("\n✅ All data fetched successfully")