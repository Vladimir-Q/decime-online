#!/usr/bin/env python3
"""Create or update an admin user in the local auth database (VM / self-hosted)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

os.environ.setdefault("AUTH_ENABLED", "true")

from decime_api.config import settings  # noqa: E402
from decime_api.db.user_store import get_user_store, reset_user_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Decime admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--display-name", default="Admin")
    args = parser.parse_args()

    reset_user_store()
    settings.auth_enabled = True
    store = get_user_store()
    store.init_db()

    existing = store.get_by_email(args.email)
    if existing:
        store.update_user(
            existing.id,
            display_name=args.display_name,
            role="admin",
            is_active=True,
            password=args.password,
        )
        print(f"Updated admin: {args.email} (id={existing.id})")
    else:
        user = store.create_user(
            email=args.email,
            password=args.password,
            display_name=args.display_name,
            role="admin",
            is_active=True,
        )
        print(f"Created admin: {args.email} (id={user.id})")

    print(f"Database: {settings.auth_database_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
