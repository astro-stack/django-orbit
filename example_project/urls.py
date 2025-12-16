"""
Django Orbit - Example Project URL Configuration
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('orbit/', include('orbit.urls')),
    path('', include('example_project.demo.urls')),
]
