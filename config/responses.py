"""
The wire contract.

Responses are assembled header by header, in the order the project has always
emitted them, because the header block is part of the public interface just as
much as the body is.  Six shapes exist:

  A  json           Content-Type, Vary, Allow, X-Frame-Options, Content-Length
  B  json + 401     as A with WWW-Authenticate straight after Content-Type
  C  empty body     as A but with no Content-Type at all
  D  html error     Content-Type, X-Frame-Options, Content-Length
  E  served file    Content-Type, Content-Length, Content-Disposition,
                    Last-Modified, X-Frame-Options
  F  redirect       Content-Type, Location, Expires, Cache-Control,
                    X-Frame-Options, Content-Length, Vary

``Date`` and ``Server`` are prepended, and the three security headers are
appended, by the middleware in :mod:`config.main`.
"""

import json
from contextvars import ContextVar

from starlette.responses import Response

#: Set per request by :mod:`config.main` from the route it matched.
current_allow = ContextVar('current_allow', default=None)

SECURITY_TRAILER = [
    (b'X-Content-Type-Options', b'nosniff'),
    (b'Referrer-Policy', b'same-origin'),
    (b'Cross-Origin-Opener-Policy', b'same-origin'),
]

_UNSET = object()


def render(payload):
    """Compact JSON, no trailing newline, non-ASCII left as-is."""
    return json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode()


class RawResponse(Response):
    """A response whose header block is dictated verbatim, not assembled."""

    def __init__(self, body=b'', status_code=200, raw_headers=None):
        self.body = body
        self.status_code = status_code
        self.background = None
        self.raw_headers = list(raw_headers or [])


def api_response(payload=_UNSET, status_code=200, allow=_UNSET, www_authenticate=None,
                 content_length=True):
    """Shapes A, B and C."""
    if allow is _UNSET:
        allow = current_allow.get()
    headers = []
    if payload is _UNSET:
        body = b''
    else:
        body = render(payload)
        headers.append((b'Content-Type', b'application/json'))
    if www_authenticate:
        headers.append((b'WWW-Authenticate', www_authenticate.encode()))
    headers.append((b'Vary', b'Accept'))
    if allow:
        headers.append((b'Allow', allow.encode()))
    headers.append((b'X-Frame-Options', b'DENY'))
    if content_length:
        headers.append((b'Content-Length', str(len(body)).encode()))
    return RawResponse(body, status_code, headers)


def html_response(body, status_code, vary=None, allow=None):
    """Shape D.

    ``vary`` and ``allow`` are optional because the error pages carry neither,
    while the documentation page carries both.
    """
    if isinstance(body, str):
        body = body.encode()
    headers = [(b'Content-Type', b'text/html; charset=utf-8')]
    if vary:
        headers.append((b'Vary', vary.encode()))
    if allow:
        headers.append((b'Allow', allow.encode()))
    headers.append((b'X-Frame-Options', b'DENY'))
    headers.append((b'Content-Length', str(len(body)).encode()))
    return RawResponse(body, status_code, headers)


def file_response(body, content_type, filename, last_modified):
    """Shape E."""
    headers = [
        (b'Content-Type', content_type.encode()),
        (b'Content-Length', str(len(body)).encode()),
        (b'Content-Disposition', ('inline; filename="%s"' % filename).encode()),
        (b'Last-Modified', last_modified.encode()),
        (b'X-Frame-Options', b'DENY'),
    ]
    return RawResponse(body, 200, headers)
