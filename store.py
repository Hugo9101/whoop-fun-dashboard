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
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=300)
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


def _sql_type(series):
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE PRECISION"
    return "TEXT"


def _add_missing_columns(df, table, engine):
    """WHOOP adds new fields over time (e.g. cycles.step_count) — add them to
    the table instead of crashing the whole daily sync."""
    with engine.begin() as conn:
        existing = {
            row[0] for row in conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t"
            ), {"t": table})
        }
        if not existing:
            return  # table doesn't exist yet — to_sql will create it
        for col in df.columns:
            if col not in existing:
                conn.execute(text(
                    f'ALTER TABLE {table} ADD COLUMN "{col}" {_sql_type(df[col])}'
                ))
                print(f"   + {table}: added new column {col}")


def _save(records, table, id_key):
    if not records:
        print(f"   → {table}: no data")
        return

    df = pd.DataFrame([_flatten(r) for r in records])
    df[id_key] = df[id_key].astype(str)

    engine = _get_engine()
    _add_missing_columns(df, table, engine)

    try:
        existing = pd.read_sql(f'SELECT "{id_key}" FROM {table}', engine)
        existing_ids = set(existing[id_key].astype(str))
        new_df = df[~df[id_key].isin(existing_ids)]
        update_df = df[df[id_key].isin(existing_ids)]
    except Exception:
        new_df = df
        update_df = pd.DataFrame()

    inserted = 0
    updated = 0

    if not new_df.empty:
        new_df.to_sql(table, engine, if_exists="append", index=False)
        inserted = len(new_df)

    if not update_df.empty:
        cols = [c for c in update_df.columns if c != id_key]
        set_clause = ", ".join(f'"{c}" = :{c}' for c in cols)
        update_sql = text(
            f'UPDATE {table} SET {set_clause} WHERE "{id_key}" = :{id_key}'
        )
        for _, row in update_df.iterrows():
            params = {c: (None if pd.isna(row[c]) else row[c]) for c in cols}
            params[id_key] = row[id_key]
            with engine.begin() as conn:
                conn.execute(update_sql, params)
        updated = len(update_df)

    print(f"   → {table}: +{inserted} new, ~{updated} updated")

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
