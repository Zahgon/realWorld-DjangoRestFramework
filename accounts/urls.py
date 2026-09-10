"""Route table for the accounts app.

The original project exposed ``urlpatterns`` here; the router below plays the
same role and is mounted under the ``api`` prefix by :mod:`config.urls`.
"""
from .views import router

__all__ = ["router"]
