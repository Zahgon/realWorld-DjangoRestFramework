"""The URL table.

The original project built its URLs from two routers plus a handful of explicit
paths.  Those routers generated more than the obvious endpoints: a browsable API
root at ``/api/``, and a ``.<format>`` suffixed twin of every registered route.
They also decided *which* HTTP methods each URL answers, which in turn decides
the ``Allow`` header and the 405 responses.  All of that is reproduced here as
an explicit, ordered table so the middleware in :mod:`config.main` can resolve a
request exactly the way the original did.

Order matters: the first pattern that matches wins, and the accounts routes are
registered before the articles routes, which is why ``/api/`` lists only the
profiles endpoint.
"""
import re
from dataclasses import dataclass, field

API_PREFIX = "/api"

#: Methods a router-backed view treats as reads.  ``HEAD`` is mapped onto the
#: ``GET`` action by the router, which is why it is here, while ``OPTIONS`` is
#: not mapped at all and therefore falls through to the authenticated branch.
ROUTER_SAFE = frozenset({"GET", "HEAD"})
ALL_METHODS = frozenset(
    {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE", "TRACE"}
)


@dataclass(frozen=True)
class Route:
    """One resolvable URL pattern."""

    pattern: re.Pattern
    allow: str
    anonymous: frozenset
    name: str = ""
    description: str = ""
    template: str | None = None
    actions: dict = field(default_factory=dict)

    def rewrite(self, path: str) -> str:
        """Return the path the application router should see."""
        if self.template is None:
            return path
        return self.pattern.sub(self.template, path)

    @property
    def methods(self) -> frozenset:
        return frozenset(part.strip() for part in self.allow.split(","))


def _route(regex, allow, anonymous, **kwargs):
    return Route(re.compile(regex), allow, frozenset(anonymous), **kwargs)


#: The serializer field description the original metadata class emitted for the
#: comment endpoint.  It is part of the OPTIONS response body.
_COMMENT_ACTIONS = {
    "POST": {
        "id": {"type": "integer", "required": False, "read_only": True, "label": "ID"},
        "createdAt": {
            "type": "datetime",
            "required": False,
            "read_only": False,
            "label": "Createdat",
        },
        "updatedAt": {
            "type": "datetime",
            "required": False,
            "read_only": False,
            "label": "Updatedat",
        },
        "body": {
            "type": "string",
            "required": True,
            "read_only": False,
            "label": "Body",
        },
        "author": {
            "type": "field",
            "required": False,
            "read_only": True,
            "label": "Author",
        },
    }
}

ROUTES = [
    # ---- accounts: explicit paths -------------------------------------
    _route(r"^/api/users/login$", "OPTIONS, POST", ALL_METHODS, name="Account Login"),
    _route(r"^/api/users$", "OPTIONS, POST", ALL_METHODS, name="Account Registration"),
    _route(r"^/api/user$", "GET, PUT, HEAD, OPTIONS", (), name="User"),
    # ---- accounts: profile router -------------------------------------
    _route(r"^/api/profiles$", "GET, POST", ROUTER_SAFE, name="User List"),
    _route(
        r"^/api/profiles\.[a-z0-9]+/?$",
        "GET, POST",
        ROUTER_SAFE,
        name="User List",
        template="/api/profiles",
    ),
    _route(r"^/api/profiles/[^/.]+/follow$", "POST, DELETE", (), name="User Follow"),
    _route(
        r"^/api/profiles/([^/.]+)/follow\.[a-z0-9]+/?$",
        "POST, DELETE",
        (),
        name="User Follow",
        template=r"/api/profiles/\1/follow",
    ),
    _route(r"^/api/profiles/[^/.]+$", "GET, DELETE", (), name="User Detail"),
    _route(
        r"^/api/profiles/([^/.]+)\.[a-z0-9]+/?$",
        "GET, DELETE",
        (),
        name="User Detail",
        template=r"/api/profiles/\1",
    ),
    # The router mounted first also owns the API root.
    _route(
        r"^/api/$",
        "GET, HEAD, OPTIONS",
        ALL_METHODS,
        name="Api Root",
        description="The default basic root view for DefaultRouter",
    ),
    _route(
        r"^/api/\.[a-z0-9]+/?$",
        "GET, HEAD, OPTIONS",
        ALL_METHODS,
        name="Api Root",
        description="The default basic root view for DefaultRouter",
        template="/api/",
    ),
    # ---- articles router ----------------------------------------------
    _route(r"^/api/articles$", "GET, POST", ROUTER_SAFE, name="Articles List"),
    _route(
        r"^/api/articles\.[a-z0-9]+/?$",
        "GET, POST",
        ROUTER_SAFE,
        name="Articles List",
        template="/api/articles",
    ),
    _route(r"^/api/articles/feed$", "GET", (), name="Articles Feed"),
    _route(
        r"^/api/articles/feed\.[a-z0-9]+/?$",
        "GET",
        (),
        name="Articles Feed",
        template="/api/articles/feed",
    ),
    _route(
        r"^/api/articles/[^/.]+/favorite$", "POST, DELETE", (), name="Articles Favorite"
    ),
    _route(
        r"^/api/articles/([^/.]+)/favorite\.[a-z0-9]+/?$",
        "POST, DELETE",
        (),
        name="Articles Favorite",
        template=r"/api/articles/\1/favorite",
    ),
    _route(r"^/api/tags$", "GET", ALL_METHODS, name="Tag List"),
    _route(
        r"^/api/tags\.[a-z0-9]+/?$",
        "GET",
        ALL_METHODS,
        name="Tag List",
        template="/api/tags",
    ),
    _route(
        r"^/api/articles/[^/.]+$", "GET, PUT, DELETE", ROUTER_SAFE, name="Articles Detail"
    ),
    _route(
        r"^/api/articles/([^/.]+)\.[a-z0-9]+/?$",
        "GET, PUT, DELETE",
        ROUTER_SAFE,
        name="Articles Detail",
        template=r"/api/articles/\1",
    ),
    # ---- comments: explicit paths --------------------------------------
    # The original path converter for the slug accepted dots, unlike the
    # router-generated ones above, so this pattern is deliberately wider.
    _route(
        r"^/api/articles/[^/]+/comments$",
        "GET, POST, HEAD, OPTIONS",
        ("GET",),
        name="Comment",
        actions=_COMMENT_ACTIONS,
    ),
    _route(
        r"^/api/articles/[^/]+/comments/[0-9]+$",
        "DELETE, OPTIONS",
        ALL_METHODS,
        name="Delete Comment",
    ),
]


def resolve(path: str) -> Route | None:
    """Return the first route matching ``path``, or ``None``."""
    for route in ROUTES:
        if route.pattern.match(path):
            return route
    return None
