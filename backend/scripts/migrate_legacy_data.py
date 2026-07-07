#!/usr/bin/env python3
"""One-time migration: hand the legacy single-user database to an owner account.

Before multi-user auth, all data lived in data/linkedin_jobs.db. This script
assigns that data to a real user account so it shows up after they log in.

Usage:
    python backend/scripts/migrate_legacy_data.py --email you@example.com --password yourpass

Idempotent and non-destructive:
  - Creates the user (or reuses an existing one).
  - Copies data/linkedin_jobs.db -> data/users/<id>/data.db (only if not already present).
  - Leaves the original in place and writes a .bak alongside it.
"""

import os
import sys
import shutil
import sqlite3
import argparse
from pathlib import Path

# Make backend/ importable whether run from repo root or backend/.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "backend"))
os.chdir(_ROOT)

import db  # noqa: E402
from auth import register_user, authenticate_user, AuthError  # noqa: E402


def _ensure_user(email: str, password: str, name: str) -> dict:
    try:
        user = register_user(email, password, name)
        print(f"Created user {user['email']} (id={user['id']})")
        return user
    except AuthError as e:
        if e.status == 409:
            user = authenticate_user(email, password)
            if not user:
                sys.exit(f"User {email} already exists but the password is wrong. Re-run with the correct password.")
            print(f"Reusing existing user {user['email']} (id={user['id']})")
            return user
        sys.exit(f"Could not create user: {e.message}")


def main():
    ap = argparse.ArgumentParser(description="Assign legacy data to an owner account")
    ap.add_argument("--email", required=True, help="Owner account email")
    ap.add_argument("--password", required=True, help="Owner account password (used to create or verify the account)")
    ap.add_argument("--name", default="", help="Owner display name")
    args = ap.parse_args()

    legacy = db.DB_PATH
    if not legacy.exists():
        sys.exit(f"No legacy database found at {legacy} — nothing to migrate.")

    user = _ensure_user(args.email, args.password, args.name)
    dest = db._user_db_path(user["id"])  # also creates data/users/<id>/

    if dest.exists():
        sys.exit(f"Destination {dest} already exists — refusing to overwrite. Migration appears already done.")

    # Fold the WAL into the main file so a plain copy is complete.
    src_conn = sqlite3.connect(str(legacy))
    try:
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        src_conn.close()

    shutil.copy2(legacy, dest)
    print(f"Copied {legacy} -> {dest}")

    # Apply any pending schema migrations to the user's copy.
    conn = db.init_db(dest)
    conn.close()
    print("Applied schema migrations to the user's database.")

    # Back up the original for rollback (don't delete it).
    bak = legacy.with_suffix(legacy.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(legacy, bak)
        print(f"Wrote rollback backup -> {bak}")

    print(f"\nDone. Log in as {user['email']} to see the migrated data.")


if __name__ == "__main__":
    main()
