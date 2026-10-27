"""Test plumbing.

The original project inherited all of this from its web framework: a test case
class that stood up a throwaway database, a test client that spoke to the
application in-process and remembered an ``Authorization`` header between
calls, and a helper that turned a route name into a path.  None of that is
application behaviour, so it is reimplemented here rather than ported.

Importing this module has a side effect on purpose: it points the database
settings at a throwaway database *before* anything else reads them, which is
the same trick the original test runner played.  That is why every test module
imports this one first.
"""

import json
import os
import unittest
from urllib.parse import urlsplit

import psycopg2
from fastapi.testclient import TestClient

SOURCE_DATABASE = os.environ.get('POSTGRES_DB', 'postgres')
# The suffix is not decoration.  The conventional name for a throwaway database
# is ``test_<database>``, and that is exactly the name the project's previous
# test runner also claimed.  When both suites are pointed at one PostgreSQL
# server at the same time, whichever finishes first drops the database out from
# under the other, and the second suite fails from that point on.  Owning a
# distinct name removes the collision entirely.
TEST_DATABASE = 'test_' + SOURCE_DATABASE + '_fastapi'
os.environ['POSTGRES_DB'] = TEST_DATABASE

from config import settings  # noqa: E402  (must follow the override above)


def _create_test_database():
    """Create the throwaway database, dropping any leftover from a crash."""
    options = settings.DATABASES['default']
    connection = psycopg2.connect(
        dbname=SOURCE_DATABASE,
        user=options['USER'],
        password=options['PASSWORD'],
        host=options['HOST'],
        port=options['PORT'],
    )
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('DROP DATABASE IF EXISTS "%s"' % TEST_DATABASE)
            cursor.execute('CREATE DATABASE "%s"' % TEST_DATABASE)
    finally:
        connection.close()


_create_test_database()

from sqlalchemy import text  # noqa: E402

from config.database import Base, SessionLocal, create_all  # noqa: E402
from config.main import app  # noqa: E402
from config.security import AccessToken  # noqa: E402

create_all()

session = SessionLocal()

_NAMED_ROUTES = {
    'account-login': '/api/users/login',
    'account-registration': '/api/users',
    'user-account': '/api/user',
    'user-list': '/api/profiles',
    'comment-article': '/api/articles/{slug}/comments',
    'comment-delete': '/api/articles/{slug}/comments/{id}',
}


def reverse(name, **kwargs):
    """Turn a route name into a path, as the original ``reverse`` did."""
    return _NAMED_ROUTES[name].format(**kwargs)


def create_user(**kwargs):
    """Replaces the framework manager call the original tests used."""
    from accounts.models import UserManager

    user = UserManager(session).create_user(**kwargs)
    session.commit()
    session.refresh(user)
    return user


def create(model, **kwargs):
    """Replaces ``Model.objects.create(**kwargs)``."""
    instance = model(**kwargs)
    save = getattr(instance, 'save', None)
    if save is not None:
        save()
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


class APIClient:
    """In-process client with the credential memory the original one had."""

    def __init__(self):
        self._client = TestClient(app, base_url='http://testserver', raise_server_exceptions=False)
        self._headers = {}

    def credentials(self, **kwargs):
        headers = {}
        for key, value in kwargs.items():
            name = key[5:] if key.startswith('HTTP_') else key
            headers[name.replace('_', '-').title()] = value
        self._headers = headers

    def _request(self, method, url, data=None, format='json', headers=None):
        parts = urlsplit(url)
        sent = dict(self._headers)
        body = None
        if data is not None:
            if format == 'json':
                sent['Content-Type'] = 'application/json'
                body = json.dumps(data).encode()
            else:
                body = data
        if headers:
            sent.update(headers)
        sent = {name: value for name, value in sent.items() if value is not None}
        return self._client.request(
            method,
            parts.path,
            params=parts.query or None,
            content=body,
            headers=sent,
        )

    def get(self, url, data=None, format='json', headers=None):
        return self._request('GET', url, None, format, headers)

    def post(self, url, data=None, format='json', headers=None):
        return self._request('POST', url, data, format, headers)

    def put(self, url, data=None, format='json', headers=None):
        return self._request('PUT', url, data, format, headers)

    def delete(self, url, data=None, format='json', headers=None):
        return self._request('DELETE', url, data, format, headers)

    def patch(self, url, data=None, format='json', headers=None):
        return self._request('PATCH', url, data, format, headers)

    def head(self, url, headers=None):
        return self._request('HEAD', url, None, 'json', headers)

    def options(self, url, headers=None):
        return self._request('OPTIONS', url, None, 'json', headers)


class APITestCase(unittest.TestCase):
    """Gives every test an empty database and a fresh client."""

    def setUp(self):
        session.rollback()
        tables = ', '.join('"%s"' % table.name for table in Base.metadata.sorted_tables)
        session.execute(text('TRUNCATE %s RESTART IDENTITY CASCADE' % tables))
        session.commit()
        self.session = session
        self.client = APIClient()

    def tearDown(self):
        session.rollback()


__all__ = [
    'APIClient',
    'APITestCase',
    'AccessToken',
    'create',
    'create_user',
    'reverse',
    'session',
]
