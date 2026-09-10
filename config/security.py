"""
Password hashing and JSON web tokens.

The hash format (``pbkdf2_sha256$<iterations>$<salt>$<b64 hash>``) and the
token payload (``token_type``/``exp``/``iat``/``jti``/``user_id``) are the ones
the project already stored and issued, so existing rows and existing tokens
keep working.
"""

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from config import settings

PBKDF2_ITERATIONS = 600000
UNUSABLE_PASSWORD_PREFIX = '!'
UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40

ALGORITHM = settings.SIMPLE_JWT['ALGORITHM']
SIGNING_KEY = settings.SIMPLE_JWT['SIGNING_KEY']
USER_ID_CLAIM = settings.SIMPLE_JWT['USER_ID_CLAIM']
AUTH_HEADER_TYPES = settings.SIMPLE_JWT['AUTH_HEADER_TYPES']


def _salt():
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(alphabet) for _ in range(22))


def make_password(password):
    if password is None:
        return make_unusable_password()
    salt = _salt()
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return 'pbkdf2_sha256$%d$%s$%s' % (PBKDF2_ITERATIONS, salt, base64.b64encode(digest).decode())


def make_unusable_password():
    return UNUSABLE_PASSWORD_PREFIX + secrets.token_urlsafe(UNUSABLE_PASSWORD_SUFFIX_LENGTH)[
        :UNUSABLE_PASSWORD_SUFFIX_LENGTH
    ]


def check_password(password, encoded):
    if password is None or not encoded or encoded.startswith(UNUSABLE_PASSWORD_PREFIX):
        return False
    try:
        algorithm, iterations, salt, stored = encoded.split('$', 3)
    except ValueError:
        return False
    if algorithm != 'pbkdf2_sha256':
        return False
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations))
    return hmac.compare_digest(base64.b64encode(digest).decode(), stored)


def access_token_for(user):
    """Issue the access half of a freshly minted token pair for ``user``."""
    now = datetime.now(timezone.utc)
    payload = {
        'token_type': 'access',
        'exp': int((now + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']).timestamp()),
        'iat': int(now.timestamp()),
        'jti': uuid.uuid4().hex,
        USER_ID_CLAIM: user.id,
    }
    return jwt.encode(payload, SIGNING_KEY, algorithm=ALGORITHM)


def decode_token(token):
    """Return the payload, or ``None`` when the token is not usable."""
    try:
        return jwt.decode(token, SIGNING_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def token_lifetime_seconds():
    lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    return int(lifetime.total_seconds()) if isinstance(lifetime, timedelta) else int(lifetime)


class AccessToken:
    """Mints an access token for a user.

    The original project imported a class of this name from its authentication
    package and the tests called ``AccessToken.for_user(user)``; the same entry
    point is kept so those lines are unchanged.
    """

    @classmethod
    def for_user(cls, user):
        return access_token_for(user)
