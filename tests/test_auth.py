
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.generic import View

from orbit.mixins import OrbitProtectedView
from orbit.conf import DEFAULTS

# Mock View for testing
class MockProtectedView(OrbitProtectedView, View):
    def get(self, request):
        return "Allowed"

@pytest.fixture
def rf():
    return RequestFactory()

@pytest.fixture
def auth_settings(settings):
    """Fixture to ensure clean config settings for each test"""
    # Create fresh config dict
    settings.ORBIT_CONFIG = DEFAULTS.copy()
    return settings

def test_auth_none_allows_all(rf, auth_settings):
    """Test that AUTH_CHECK=None allows everyone (default)"""
    auth_settings.ORBIT_CONFIG["AUTH_CHECK"] = None
    
    view = MockProtectedView()
    request = rf.get("/")
    request.user = AnonymousUser()
    view.request = request
    
    assert view.test_func() is True

def test_auth_callable_allow(rf, auth_settings):
    """Test that callable returning True allows access"""
    auth_settings.ORBIT_CONFIG["AUTH_CHECK"] = lambda r: True
    
    view = MockProtectedView()
    request = rf.get("/")
    view.request = request
    
    assert view.test_func() is True

def test_auth_callable_deny(rf, auth_settings):
    """Test that callable returning False denies access"""
    auth_settings.ORBIT_CONFIG["AUTH_CHECK"] = lambda r: False
    
    view = MockProtectedView()
    request = rf.get("/")
    view.request = request
    
    assert view.test_func() is False

def test_auth_string_path(rf, auth_settings):
    """Test using a string path to a function"""
    # Use a real Django function that accepts a request/user object
    # django.contrib.auth.validators.UnicodeUsernameValidator doesn't take request, but 
    # let's use a lambda or just a simple function we know exists and takes 1 arg?
    # Actually, let's just mock 'django.utils.html.escape' - it takes 1 arg (text) and returns valid truthy string
    auth_settings.ORBIT_CONFIG["AUTH_CHECK"] = "django.utils.html.escape"
    
    view = MockProtectedView()
    request = rf.get("/")
    view.request = request

    # escape(request) will be truthy (str) which acts as True
    assert view.test_func() is not False
