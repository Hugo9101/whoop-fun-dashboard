import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── Engine ─────────────────────────────────────────────────────────────────────
# Falls back to CSV-only mode if DATABASE_URL is not set.

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not set in .env")
        _engine = create_engine(url)
    return _engine


# ── Helpers ────────────────────────────────────────────────────────────────────

def _flatten(record, prefix=""):
    out = {}
    for k, v in record.items():
        key = f"{prefix}{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key + "_"))
        else:
            out[key] = v
    return out


def _save(records, table, id_key):
    if not records:
        print(f"   → {table}: no data")
        return

    df = pd.DataFrame([_flatten(r) for r in records])
    df[id_key] = df[id_key].astype(str)

    engine = _get_engine()

    # Read existing IDs from Supabase (table may not exist yet on first run)
    try:
        existing = pd.read_sql(f'SELECT "{id_key}" FROM {table}', engine)
        existing_ids = set(existing[id_key].astype(str))
        new_df = df[~df[id_key].isin(existing_ids)]
    except Exception:
        new_df = df  # Table doesn't exist yet — will be created below

    if new_df.empty:
        print(f"   → {table}: 0 new records")
        return

    new_df.to_sql(table, engine, if_exists="append", index=False)
    print(f"   → {table}: +{len(new_df)} new records")

    # Keep a local CSV backup as well
    _backup_csv(df, table, id_key)


def _backup_csv(df, table, id_key):
    path = DATA_DIR / f"{table}.csv"
    if path.exists():
        existing = pd.read_csv(path, dtype=str)
        existing_ids = set(existing[id_key].astype(str))
        new_rows = df[~df[id_key].astype(str).isin(existing_ids)]
        if not new_rows.empty:
            new_rows.to_csv(path, mode="a", header=False, index=False)
    else:
        df.to_csv(path, index=False)


# ── Public API ─────────────────────────────────────────────────────────────────

def save_sleep(records):
    print("💾 Saving sleep...")
    _save(records, "sleep", "id")

def save_recovery(records):
    print("💾 Saving recovery...")
    _save(records, "recovery", "cycle_id")

def save_workouts(records):
    print("💾 Saving workouts...")
    _save(records, "workouts", "id")

def save_cycles(records):
    print("💾 Saving cycles...")
    _save(records, "cycles", "id")

def save_profile(profile):
    path = DATA_DIR / "profile.json"
    with open(path, "w") as f:
        json.dump(profile, f)
    print("💾 Saving profile...")
