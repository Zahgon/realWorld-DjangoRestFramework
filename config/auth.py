"""Bearer-token authentication.

The original project authenticated with a JSON Web Token carried in an
``Authorization`` header whose scheme was ``Token`` rather than ``Bearer``.
The header is inspected once, in the middleware that fronts the whole
application, so that an unusable header is reported before the router has a
chance to reject the method -- that is the order the original used and the
order the recorded contract expects.

The middleware stores the authenticated user's primary key on the request
state.  The dependencies below re-load the user in the request's own session,
so a detached instance never escapes the middleware's session.
"""

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from accounts.models import User
from config.database import get_session
from config.security import AUTH_HEADER_TYPES, USER_ID_CLAIM, decode_token

WWW_AUTHENTICATE = 'Token realm="api"'

BAD_AUTHORIZATION_HEADER = {
    "detail": "Authorization header must contain two space-delimited values",
    "code": "bad_authorization_header",
}

TOKEN_NOT_VALID = {
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "Token is invalid or expired",
        }
    ],
}

USER_NOT_FOUND = {"detail": "User not found", "code": "user_not_found"}

USER_INACTIVE = {"detail": "User is inactive", "code": "user_inactive"}


class NotAuthenticated(Exception):
    """No usable credentials were presented."""

    detail = {"detail": "Authentication credentials were not provided."}


class AuthenticationFailed(Exception):
    """Credentials were presented but could not be accepted."""

    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail


def resolve_user(request: Request, session: Session):
    """Return the user the request authenticates as, or ``None``.

    Raises :class:`AuthenticationFailed` when a header is present but cannot
    be used; an absent header, or one carrying an unknown scheme, is simply
    anonymous -- exactly as the original behaved.
    """
    header = request.headers.get("authorization")
    if not header:
        return None

    parts = header.split()
    if not parts or parts[0] not in AUTH_HEADER_TYPES:
        return None
    if len(parts) != 2:
        raise AuthenticationFailed(BAD_AUTHORIZATION_HEADER)

    payload = decode_token(parts[1])
    if payload is None or payload.get("token_type") != "access":
        raise AuthenticationFailed(TOKEN_NOT_VALID)

    user_id = payload.get(USER_ID_CLAIM)
    if user_id is None:
        raise AuthenticationFailed(TOKEN_NOT_VALID)

    user = session.get(User, user_id)
    if user is None:
        raise AuthenticationFailed(USER_NOT_FOUND)
    if not user.is_active:
        raise AuthenticationFailed(USER_INACTIVE)
    return user


def current_user_or_none(request: Request, session: Session = Depends(get_session)):
    """The authenticated user for this request, or ``None``."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        return None
    return session.scalars(select(User).where(User.id == user_id)).first()


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    """The authenticated user for this request; never ``None``."""
    user = current_user_or_none(request, session)
    if user is None:
        raise NotAuthenticated()
    return user
