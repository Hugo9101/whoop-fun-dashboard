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

def _save_tokens_to_db(access_token, refresh_token):
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO whoop_tokens (id, access_token, refresh_token)
                VALUES (1, :at, :rt)
                ON CONFLICT (id) DO UPDATE
                SET access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token
            """), {"at": access_token, "rt": refresh_token})
    except Exception as e:
        print(f"  ⚠ Could not save tokens to DB: {e}")


def load_tokens_from_db():
    """Load latest tokens from Supabase — used by remote runners that have no .env."""
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT access_token, refresh_token FROM whoop_tokens WHERE id = 1"
            )).fetchone()
            if row:
                os.environ["WHOOP_ACCESS_TOKEN"] = row[0]
                os.environ["WHOOP_REFRESH_TOKEN"] = row[1]
                print("✅ Tokens loaded from Supabase")
    except Exception as e:
        print(f"  ⚠ Could not load tokens from DB: {e}")


def refresh_access_token():
    print("🔄 Refreshing access token...")
    client_id     = (CLIENT_ID or "").strip()
    client_secret = (CLIENT_SECRET or "").strip()
    refresh_token = (os.getenv("WHOOP_REFRESH_TOKEN") or "").strip()
    missing = [name for name, value in [
        ("WHOOP_CLIENT_ID", client_id),
        ("WHOOP_CLIENT_SECRET", client_secret),
        ("WHOOP_REFRESH_TOKEN", refresh_token),
    ] if not value]
    if missing:
        raise RuntimeError(
            f"❌ Missing credentials: {', '.join(missing)} — "
            "set them in .env locally or as GitHub Actions secrets in CI"
        )
    response = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type":    "refresh_token",
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    )
    tokens = response.json()
    if "access_token" not in tokens:
        raise RuntimeError(f"❌ Token refresh failed: {tokens}")

    set_key(ENV_FILE, "WHOOP_ACCESS_TOKEN", tokens["access_token"])
    set_key(ENV_FILE, "WHOOP_REFRESH_TOKEN", tokens["refresh_token"])
    os.environ["WHOOP_ACCESS_TOKEN"] = tokens["access_token"]
    os.environ["WHOOP_REFRESH_TOKEN"] = tokens["refresh_token"]
    _save_tokens_to_db(tokens["access_token"], tokens["refresh_token"])
    print("✅ Token refreshed and saved")
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