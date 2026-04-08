"""
patch_passwords.py — Updates a handful of users to have bcrypt-verifiable
passwords so the frontend login flow works.

Run from cluster/:  .venv/bin/python patch_passwords.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select
from api.database import engine
from api.models.user import UserAuth, UserProfile
from api.security import get_password_hash
from api.triggers import apply_triggers_now

# Apply triggers to the freshly populated DB
print("⚡ Applying triggers...")
try:
    apply_triggers_now(engine)
except Exception as e:
    print(f"   (triggers may already exist: {e})")

PASSWORD = "password123"
hashed = get_password_hash(PASSWORD)

with Session(engine) as session:
    # Get the first 10 users that have emails
    users = session.exec(
        select(UserAuth).where(UserAuth.email != None).limit(10)
    ).all()

    print(f"\n🔑 Patching {len(users)} users with password: '{PASSWORD}'")
    for u in users:
        u.password_hash = hashed
        session.add(u)
        # Get their profile name
        profile = session.get(UserProfile, u.uid)
        name = profile.name if profile else "?"
        print(f"   ✅ {u.email} ({name})")

    session.commit()
    print(f"\n🎉 Done! You can now log in with any of the emails above.")
    print(f"   Example: {users[0].email} / {PASSWORD}")
