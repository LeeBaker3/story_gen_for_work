#!/usr/bin/env python3
"""Script to create an admin user"""

from sqlalchemy.orm import Session
from backend.schemas import UserCreate
from backend.crud import create_user, get_user_by_username
from backend.database import SessionLocal, User
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))


def create_admin_user():
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = get_user_by_username(db, username='admin')
        if existing_admin:
            print(
                f"Admin user already exists: {existing_admin.username} (role: {existing_admin.role})")
            if existing_admin.role != 'admin':
                # Update role to admin
                existing_admin.role = 'admin'
                db.commit()
                print("Updated existing user to admin role")
            return existing_admin

        # Create new admin user
        admin_data = UserCreate(
            username='admin',
            email='admin@example.com',
            password='admin123'  # Change this to a secure password
        )

        admin_user = create_user(db, admin_data)
        # Update role to admin
        admin_user.role = 'admin'
        db.commit()
        db.refresh(admin_user)

        print(
            f"Created admin user: {admin_user.username} (role: {admin_user.role})")
        return admin_user

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
