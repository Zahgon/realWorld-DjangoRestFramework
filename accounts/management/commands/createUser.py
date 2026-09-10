"""Create a user from the command line.

Kept as it was found, including the lookup on a field the user table has not
had since it was renamed -- running this command has always failed on that
line and the port does not quietly repair it.
"""

import argparse

from sqlalchemy import select

from accounts.models import User, UserManager
from config.database import SessionLocal


class Command:
    help = "Create a user"

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="Email of the user")
        parser.add_argument("--name", type=str, help="Name of the user")
        parser.add_argument("--password", type=str, help="Password of the user")

    def run_from_argv(self, argv):
        parser = argparse.ArgumentParser(prog="createUser", description=self.help)
        self.add_arguments(parser)
        options = vars(parser.parse_args(argv))
        return self.handle(**options)

    def handle(self, *args, **options):
        email = options["email"]
        name = options["name"]
        password = options["password"]

        session = SessionLocal()
        try:
            if session.scalars(select(User).where(User.name == name)).first():
                print("User already exists")
                return 1
            UserManager(session).create_user(
                email=email, password=password, name=name
            )
            session.commit()
            print("User created successfully")
            return 0
        finally:
            session.close()
