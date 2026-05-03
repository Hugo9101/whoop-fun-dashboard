# WHOOP API — Authentication Guide

## Overview

WHOOP uses **OAuth 2.0 Authorization Code Flow** to grant access to user data.
This means you never handle the user's password — WHOOP does. You just receive a
temporary code and exchange it for tokens.

---

## Prerequisites

### 1. Create a WHOOP Developer App
1. Go to [developer.whoop.com](https://developer.whoop.com)
2. Create an app and fill in:
   - **Contact:** your email
   - **Privacy Policy URL:** any valid https URL (e.g. `https://whoop.com`)
   - **Redirect URL:** `https://whoop.com`
3. Copy your `CLIENT_ID` and `CLIENT_SECRET`

### 2. Store credentials in `.env`
Create a `.env` file in your project root:

```
WHOOP_CLIENT_ID=your-client-id
WHOOP_CLIENT_SECRET=your-client-secret
WHOOP_REDIRECT_URI=https://whoop.com
```

> ⚠️ Never commit `.env` to Git. Make sure `.env` is in your `.gitignore`.

---

## How the Auth Flow Works

```
Your Script          Browser              WHOOP Server
     │                   │                     │
     │── Build auth URL ─▶│                     │
     │                   │── User clicks Allow ▶│
     │                   │◀─ Redirect with code ─│
     │◀─ You paste code ──│                     │
     │─────────────────────────────────────────▶│
     │                   Exchange code for token │
     │◀─────────────────────────────────────────│
     │           access_token + refresh_token    │
```

### Step 1 — Build the Authorization URL
The script constructs a URL with these parameters:

| Parameter       | Value                                                  |
|----------------|--------------------------------------------------------|
| `client_id`    | Your app's client ID                                   |
| `redirect_uri` | Must match exactly what's registered in the WHOOP app  |
| `response_type`| Always `code`                                          |
| `scope`        | What data you want access to (see Scopes below)        |
| `state`        | Random string (min 8 chars) to prevent CSRF attacks    |

### Step 2 — User Authorizes in Browser
Open the printed URL in a browser. WHOOP shows a consent screen.
After clicking **Allow**, the browser redirects to:
```
https://whoop.com?code=XXXXXX&state=YYYYYYYY
```
Copy the `code` value from the URL bar.

### Step 3 — Exchange Code for Tokens
The script POSTs the code to WHOOP's token endpoint and receives:

| Token           | Description                              | Lifetime  |
|----------------|------------------------------------------|-----------|
| `access_token`  | Used in API requests as Bearer token     | 1 hour    |
| `refresh_token` | Used to get a new access_token           | Long-lived |

---

## Scopes

| Scope             | Data access                              |
|------------------|------------------------------------------|
| `read:sleep`      | Sleep duration, stages, performance      |
| `read:recovery`   | Recovery score, HRV, resting heart rate  |
| `read:workout`    | Workouts, strain, calories               |
| `read:profile`    | Name, email, profile info                |
| `read:cycles`     | Day strain and average heart rate        |
| `offline`         | Allows use of refresh_token              |

---

## Token Expiry & Refresh

The `access_token` expires after **1 hour**. Use the `refresh_token` to get a
new one without re-authorizing:

```python
response = requests.post(
    "https://api.prod.whoop.com/oauth/oauth2/token",
    data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
    }
)
new_tokens = response.json()
```

---

## When to Re-run `auth.py`

You only need to re-run the full auth flow if:
- Your `refresh_token` has expired (rare, but possible after long inactivity)
- You revoke access in your WHOOP account settings
- You change the scopes your app requests

For day-to-day use, just refresh the `access_token` automatically.

---

## Files in This Project

```
Whoop_APP/
├── .env          ← credentials & tokens (never commit this)
├── .gitignore    ← excludes .env from Git
├── auth.py       ← run once manually to get tokens
├── fetch.py      ← pulls data from all endpoints
├── store.py      ← saves data to CSV or Postgres
└── main.py       ← runs everything day-to-day
```
