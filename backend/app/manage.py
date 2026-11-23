"""Installation-operator account provisioning, using an interactive password prompt."""

import argparse
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import make_engine
from app.core.security import passwords
from app.models import AuditLog, Role, User


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--name", required=True)
    parser.add_argument("--station", required=True)
    args = parser.parse_args()
    from app.schemas import OfficerCreate

    password = getpass("New administrator password (14+ characters): ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords differ")
    values = OfficerCreate(username=args.username, name=args.name, role=Role.SP, temporary_password=password)
    if not 1 <= len(args.station.strip()) <= 40:
        raise SystemExit("Station must contain 1–40 characters")
    options = Settings()
    if options.environment == "production" and values.username.lower().startswith("demo."):
        raise SystemExit("Demo account names are reserved for training")
    engine = make_engine(options.database_url)
    with Session(engine) as db:
        if db.scalar(select(User.id).where(User.username == values.username.lower())):
            raise SystemExit("Username already exists; account was not changed")
        user = User(username=values.username.lower(), name=values.name, role=Role.SP, station=args.station.strip(),
            password_hash=passwords.hash(password), is_admin=True)
        db.add(user)
        db.flush()
        db.add(AuditLog(user_id=user.id, action="account.operator_created", entity="user", entity_id=str(user.id), payload={}))
        db.commit()
    engine.dispose()
    print("Administrator created. No sample accounts or cases were added.")


if __name__ == "__main__":
    main()
