from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.utils.module_loading import import_string

from orbit.conf import get_config


class OrbitProtectedView(UserPassesTestMixin):
    """
    Mixin that protects Orbit views based on the AUTH_CHECK configuration.
    
    If AUTH_CHECK is None (default), allows access (assuming DEBUG=True usually handles safety 
    or the user enabled it explicitly).
    
    If AUTH_CHECK is a string (dotted path), imports and calls it.
    If AUTH_CHECK is a callable, calls it.
    """

    def test_func(self):
        config = get_config()
        auth_check = config.get("AUTH_CHECK")

        # If no auth check defined, allow access
        # Users should ensure they only enable Orbit in safe environments if using this default
        if auth_check is None:
            return True

        # Import string path if needed
        if isinstance(auth_check, str):
            try:
                auth_check = import_string(auth_check)
            except ImportError:
                # If we can't import the check, fail safe (deny)
                return False

        # Call the check function
        if callable(auth_check):
            return auth_check(self.request)

        # Fallback deny
        return False
