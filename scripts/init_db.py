#!/usr/bin/env python3
"""Initialize the grant writer database and seed with Altus org profile."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db, seed_altus_org

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database tables created.")

    print("Seeding Altus Solutions org profile...")
    org_id = seed_altus_org()
    print(f"Altus Solutions org created (ID: {org_id})")

    print("Done. Database ready at data/grant_writer.db")
