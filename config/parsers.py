"""
Request-body parsing.

Views read the body themselves so that a malformed payload raises inside the
same ``try`` that guards the rest of the handler, which is what produces the
empty ``400`` the account endpoints have always answered with.
"""

import json
from urllib.parse import parse_qsl

from fastapi import Request

JSON_TYPES = ('application/json',)
FORM_TYPES = ('application/x-www-form-urlencoded',)


async def raw_body(request: Request) -> bytes:
    return await request.body()


def parse_body(request: Request, body: bytes):
    """Return the decoded payload, raising for anything unparseable."""
    content_type = request.headers.get('content-type', '')
    media_type = content_type.split(';')[0].strip().lower()

    if media_type in FORM_TYPES:
        return dict(parse_qsl(body.decode('utf-8')))

    # An absent Content-Type is not a licence to guess: the original refused to
    # select a parser and the request collapsed into the empty 400 below.
    if not media_type:
        raise UnsupportedMediaType(media_type)

    if media_type not in JSON_TYPES and not media_type.startswith('multipart/'):
        raise UnsupportedMediaType(media_type)

    return json.loads(body.decode('utf-8'))


class UnsupportedMediaType(Exception):
    def __init__(self, media_type):
        self.media_type = media_type
        super().__init__(f'Unsupported media type "{media_type}" in request.')
