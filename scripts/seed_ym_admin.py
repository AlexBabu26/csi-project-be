"""Seed the first Yuvalokham admin user."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.common.db import session_scope
from app.common.security import get_password_hash
from app.yuvalokham.models import YMUser, YuvalokhamUserRole


def seed():
    with session_scope() as db:
        existing = db.query(YMUser).filter(
            YMUser.role == YuvalokhamUserRole.ADMIN
        ).first()
        if existing:
            print(f"Admin already exists: {existing.email}")
            return

        admin = YMUser(
            name="Yuvalokham Admin",
            email="yuvalokham.admin@csi.org",
            phone="0000000000",
            password_hash=get_password_hash("admin@123"),
            role=YuvalokhamUserRole.ADMIN,
        )
        db.add(admin)
        print(f"Created admin: {admin.email} (password: admin@123)")
        print("Change the password immediately after first login!")


if __name__ == "__main__":
    seed()
