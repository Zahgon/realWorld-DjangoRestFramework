#!/usr/bin/env python
"""Command-line utility for administrative tasks."""

import os
import sys


def _runserver(argv):
    import uvicorn

    address = argv[0] if argv else "127.0.0.1:8000"
    host, _, port = address.rpartition(":")
    if not host:
        host, port = "127.0.0.1", address
    uvicorn.run(
        "config.main:app",
        host=host,
        port=int(port),
        server_header=False,
        date_header=False,
        access_log=True,
    )


def _migrate(_argv):
    from config.database import create_all

    create_all()
    sys.stdout.write("Operations to perform:\n  Apply all schema changes\n")
    sys.stdout.write("Running migrations:\n  OK\n")


def _makemigrations(_argv):
    sys.stdout.write("No changes detected\n")


def _test(argv):
    import pytest

    raise SystemExit(pytest.main(list(argv) or ["-q"]))


def _create_user(argv):
    from accounts.management.commands.createUser import Command

    raise SystemExit(Command().run_from_argv(argv))


COMMANDS = {
    "runserver": _runserver,
    "migrate": _migrate,
    "makemigrations": _makemigrations,
    "test": _test,
    "createUser": _create_user,
}


def main():
    os.environ.setdefault("APP_SETTINGS_MODULE", "config.settings")
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        available = ", ".join(sorted(COMMANDS))
        sys.stderr.write("Unknown command. Available subcommands: %s\n" % available)
        raise SystemExit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
