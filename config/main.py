"""The application object and the request pipeline that fronts it.

The original project put a stack of middleware in front of a view layer that
resolved the URL, negotiated the response type, authenticated the caller,
checked permissions and only then looked for a handler for the request
method.  That ordering is observable -- an anonymous ``PATCH`` is answered
with 401 rather than 405, and an unsatisfiable ``Accept`` header beats both --
so it is reproduced here in one middleware rather than scattered across the
endpoints.

The original also mounted a file server at the root as a catch-all, an
accident of a debug-only branch that referred to two settings the project
never defined.  It is preserved: any path the table below does not claim is
answered by serving a file from the project directory.

The interactive documentation is published at ``/swagger/`` as before.  The
original never published a machine-readable schema alongside it -- that URL
answered 404 -- and that is preserved too.
"""

import mimetypes
import os
import posixpath
import sys
from email.utils import formatdate
from html import escape

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html

from accounts.urls import router as accounts_router
from accounts.views import NotFound
from articles.filters import FilterValidationError
from articles.urls import router as articles_router
from comments.urls import router as comments_router
from config import settings
from config.auth import (
    WWW_AUTHENTICATE,
    AuthenticationFailed,
    NotAuthenticated,
    resolve_user,
)
from config.database import SessionLocal, create_all
from config.responses import (
    SECURITY_TRAILER,
    api_response,
    current_allow,
    file_response,
    html_response,
)
from config.urls import API_PREFIX, resolve

SERVER = "WSGIServer/0.2 CPython/%d.%d.%d" % tuple(sys.version_info[:3])

#: The response types the original was able to produce.  A caller that
#: insists on anything else is refused before it is authenticated.
RENDERS = ["application/json", "text/html"]
PARSES = [
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
]

NOT_ACCEPTABLE = {"detail": "Could not satisfy the request Accept header."}

SWAGGER_SPEC_URL = "/swagger.json"


api = FastAPI(
    title="Real World API",
    version="v1",
    description="Real World API Documentation",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)

api.include_router(accounts_router, prefix=API_PREFIX)
api.include_router(articles_router, prefix=API_PREFIX)
api.include_router(comments_router, prefix=API_PREFIX)


@api.on_event("startup")
def _startup() -> None:
    create_all()


@api.get(API_PREFIX + "/")
def api_root(request: Request):
    """The router index.

    Two routers were mounted at this prefix and each contributed an index of
    its own; the first one registered is the one that answers, which is why
    only the profile collection is listed here.
    """
    base = str(request.base_url).rstrip("/")
    return api_response({"profiles": "%s%s/profiles" % (base, API_PREFIX)})


@api.get("/swagger/", include_in_schema=False)
def swagger_ui():
    """The interactive documentation the original published at this path."""
    page = get_swagger_ui_html(openapi_url=SWAGGER_SPEC_URL, title="Real World API")
    return html_response(
        page.body, status_code=200, vary="Accept, Cookie", allow="GET, HEAD, OPTIONS"
    )


@api.exception_handler(NotAuthenticated)
def _not_authenticated(request: Request, exc: NotAuthenticated):
    return api_response(
        exc.detail,
        status_code=401,
        allow=_allow_of(request),
        www_authenticate=WWW_AUTHENTICATE,
    )


@api.exception_handler(AuthenticationFailed)
def _authentication_failed(request: Request, exc: AuthenticationFailed):
    return api_response(
        exc.detail,
        status_code=401,
        allow=_allow_of(request),
        www_authenticate=WWW_AUTHENTICATE,
    )


@api.exception_handler(NotFound)
def _not_found(request: Request, exc: NotFound):
    return api_response(exc.detail, status_code=404, allow=_allow_of(request))


@api.exception_handler(FilterValidationError)
def _filter_invalid(request: Request, exc: FilterValidationError):
    return api_response(exc.detail, status_code=400, allow=_allow_of(request))


@api.exception_handler(Exception)
def _server_error(request: Request, exc: Exception):
    return html_response(_error_page(request, exc), status_code=500)


def _allow_of(request: Request):
    return (request.scope.get("state") or {}).get("allow")


def _error_page(request: Request, exc: BaseException) -> bytes:
    title = "%s at %s" % (type(exc).__name__, request.url.path)
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><title>%s</title></head>'
        "<body><h1>%s</h1><pre>%s</pre></body></html>"
        % (escape(title), escape(title), escape(str(exc)))
    ).encode()


def _not_found_page(path: str) -> bytes:
    title = "Page not found at %s" % path
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><title>%s</title></head>'
        "<body><h1>Not Found</h1><p>The requested resource was not found on "
        "this server.</p></body></html>" % escape(title)
    ).encode()


def _serve_media(path: str):
    """Serve a file from the project directory, as the original's catch-all did.

    Components that would climb out of the directory are dropped rather than
    honoured, and a directory is never listed.
    """
    relative = posixpath.normpath(path.lstrip("/"))
    parts = [part for part in relative.split("/") if part not in ("", ".", "..")]
    full = os.path.join(str(settings.MEDIA_ROOT), *parts) if parts else ""
    if not parts or not os.path.isfile(full):
        return html_response(_not_found_page(path), status_code=404)

    content_type, _encoding = mimetypes.guess_type(full)
    with open(full, "rb") as handle:
        body = handle.read()
    return file_response(
        body,
        content_type=content_type or "application/octet-stream",
        filename=os.path.basename(full),
        last_modified=formatdate(os.path.getmtime(full), usegmt=True),
    )


def _accepts(header) -> bool:
    """Whether a response this project can produce would satisfy the header."""
    if not header:
        return True
    for chunk in header.split(","):
        media = chunk.split(";")[0].strip()
        if not media or media == "*/*" or media in RENDERS:
            return True
        main, _, sub = media.partition("/")
        if sub == "*" and any(known.startswith(main + "/") for known in RENDERS):
            return True
    return False


def _metadata(route) -> dict:
    payload = {
        "name": route.name or "",
        "description": route.description or "",
        "renders": list(RENDERS),
        "parses": list(PARSES),
    }
    if route.actions:
        payload["actions"] = route.actions
    return payload


def _head_send(send):
    """A response to ``HEAD`` carries the headers of the ``GET`` but no body.

    The declared length is deliberately left in place. The framing headers of a
    ``HEAD`` response are chosen as though the request had been a ``GET``, so a
    response that declares no length at all is treated as being of unknown
    length and acquires a chunked transfer encoding instead -- a larger
    departure than carrying the length the matching ``GET`` would have carried.
    """

    async def wrapper(message):
        if message["type"] == "http.response.body":
            message = {"type": "http.response.body", "body": b"", "more_body": False}
        await send(message)

    return wrapper


class Gate:
    """Resolve, negotiate, authenticate, then check the method -- in that order."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]

        if path == "/swagger/":
            await self.app(scope, receive, send)
            return

        route = resolve(path)
        if route is None:
            await _serve_media(path)(scope, receive, send)
            return

        request = Request(scope, receive)

        if not _accepts(request.headers.get("accept")):
            await self._reply(
                scope,
                receive,
                send,
                method,
                api_response(NOT_ACCEPTABLE, status_code=406, allow=route.allow),
            )
            return

        session = SessionLocal()
        try:
            user = resolve_user(request, session)
            user_id = None if user is None else user.id
        except AuthenticationFailed as exc:
            await self._reply(
                scope,
                receive,
                send,
                method,
                api_response(
                    exc.detail,
                    status_code=401,
                    allow=route.allow,
                    www_authenticate=WWW_AUTHENTICATE,
                ),
            )
            return
        finally:
            session.close()

        if user_id is None and method not in route.anonymous:
            await self._reply(
                scope,
                receive,
                send,
                method,
                api_response(
                    NotAuthenticated.detail,
                    status_code=401,
                    allow=route.allow,
                    www_authenticate=WWW_AUTHENTICATE,
                ),
            )
            return

        if method not in route.methods:
            await self._reply(
                scope,
                receive,
                send,
                method,
                api_response(
                    {"detail": 'Method "%s" not allowed.' % method},
                    status_code=405,
                    allow=route.allow,
                ),
            )
            return

        if method == "OPTIONS":
            await self._reply(
                scope,
                receive,
                send,
                method,
                api_response(_metadata(route), allow=route.allow),
            )
            return

        scope = dict(scope)
        scope["path"] = route.rewrite(path)
        scope["raw_path"] = scope["path"].encode()
        scope["state"] = dict(scope.get("state") or {})
        scope["state"]["user_id"] = user_id
        scope["state"]["allow"] = route.allow
        current_allow.set(route.allow)
        if method == "HEAD":
            scope["method"] = "GET"
            await self.app(scope, receive, _head_send(send))
            return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reply(scope, receive, send, method, response):
        if method == "HEAD":
            send = _head_send(send)
        await response(scope, receive, send)


class Headers:
    """Stamp the two server-generated headers and the security trailer."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def wrapper(message):
            if message["type"] == "http.response.start":
                message = dict(message)
                headers = [
                    (b"Date", formatdate(usegmt=True).encode()),
                    (b"Server", SERVER.encode()),
                ]
                headers.extend(message["headers"])
                headers.extend(SECURITY_TRAILER)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapper)


#: The ASGI application.
app = Headers(Gate(api))
