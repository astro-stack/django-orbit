from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.utils.module_loading import import_string

from orbit.conf import get_config


def is_orbit_request_authorized(request):
    """Return whether a request passes Orbit's configured authorization check."""
    auth_check = get_config().get("AUTH_CHECK")

    if auth_check is None:
        return True

    if isinstance(auth_check, str):
        try:
            auth_check = import_string(auth_check)
        except ImportError:
            return False

    return bool(auth_check(request)) if callable(auth_check) else False


class OrbitProtectedView(UserPassesTestMixin):
    """
    Mixin that protects Orbit views based on the AUTH_CHECK configuration.

    If AUTH_CHECK is None (default), allows access (assuming DEBUG=True usually handles safety
    or the user enabled it explicitly).

    If AUTH_CHECK is a string (dotted path), imports and calls it.
    If AUTH_CHECK is a callable, calls it.
    """

    def test_func(self):
        return is_orbit_request_authorized(self.request)

    def handle_no_permission(self):
        from django.shortcuts import render
        from django.conf import settings
        from django.contrib.auth import REDIRECT_FIELD_NAME

        login_url = getattr(settings, "LOGIN_URL", "/admin/login/")

        return render(
            self.request,
            "orbit/locked.html",
            {"login_url": login_url, "redirect_field_name": REDIRECT_FIELD_NAME},
            status=403,
        )
