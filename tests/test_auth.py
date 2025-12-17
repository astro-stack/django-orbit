
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
    # Use built-in classifier validation as a dummy function that returns False for empty input
    # Or better, use 'django.contrib.auth.mixins.LoginRequiredMixin' logic simulation
    # Let's use a lambda assigned to a module variable if possible, 
    # but for string import we need a real path.
    # We can use `orbit.conf.is_enabled` which returns True/False based on config
    
    auth_settings.ORBIT_CONFIG["AUTH_CHECK"] = "orbit.conf.is_enabled"
    # is_enabled returns True by default
    
    view = MockProtectedView()
    request = rf.get("/")
    view.request = request
    
    assert view.test_func() is True
