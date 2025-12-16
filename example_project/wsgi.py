"""
Django Orbit - Example Project WSGI Configuration
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'example_project.settings')

application = get_wsgi_application()
