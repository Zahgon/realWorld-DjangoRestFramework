"""
Payload shapes for accounts.

Key order is contract, so the dictionaries are built in the order the fields
were declared: ``username, email, bio, image`` for a user (the password is
write-only) and ``username, bio, image, following`` for a profile.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

USER_FIELDS = ('username', 'email', 'password', 'bio', 'image')
PROFILE_FIELDS = ('username', 'bio', 'image', 'following')

_EMAIL_USER = re.compile(r"^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*$", re.IGNORECASE)
_EMAIL_DOMAIN = re.compile(
    r'^((?!-)[A-Z0-9-]{1,63}(?<!-)\.)+[A-Z]{2,63}$', re.IGNORECASE
)
_URL = re.compile(
    r'^(?:[a-z0-9\.\-\+]*)://'
    r'(?:\S+(?::\S*)?@)?'
    r'(?:\[[0-9a-f:\.]+\]|[^\s/?#@]+)'
    r'(?::\d{2,5})?'
    r'(?:[/?#][^\s]*)?$',
    re.IGNORECASE,
)


def is_email(value):
    if not isinstance(value, str) or '@' not in value or len(value) > 254:
        return False
    local, _, domain = value.rpartition('@')
    return bool(_EMAIL_USER.match(local) and _EMAIL_DOMAIN.match(domain))


def is_url(value):
    return isinstance(value, str) and len(value) <= 200 and bool(_URL.match(value))


class UserSerializer(BaseModel):
    """Validates a registration payload; ``password`` never leaves the server."""

    model_config = ConfigDict(extra='ignore', str_strip_whitespace=False)

    username: str = Field(min_length=1, max_length=60)
    email: str
    password: str = Field(min_length=1, max_length=128)
    bio: str = ''
    image: str | None = None

    @field_validator('email')
    @classmethod
    def _email(cls, value):
        if not is_email(value):
            raise ValueError('Enter a valid email address.')
        return value

    @field_validator('image')
    @classmethod
    def _image(cls, value):
        if value is not None and not is_url(value):
            raise ValueError('Enter a valid URL.')
        return value


def user_data(user):
    return {
        'username': user.username,
        'email': user.email,
        'bio': user.bio,
        'image': user.image,
    }


def profile_data(user, request_user=None):
    following = False
    if request_user is not None:
        following = any(follower.id == request_user.id for follower in user.followers)
    return {
        'username': user.username,
        'bio': user.bio,
        'image': user.image,
        'following': following,
    }
