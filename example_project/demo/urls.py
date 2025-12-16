"""
Demo App URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('books/', views.books_list, name='books_list'),
    path('books/create/', views.books_create, name='books_create'),
    path('slow/', views.slow_endpoint, name='slow'),
    path('log/', views.log_messages, name='log'),
    path('error/', views.error_endpoint, name='error'),
    path('duplicate-queries/', views.duplicate_queries, name='duplicate_queries'),
    path('api/data/', views.ApiDataView.as_view(), name='api_data'),
]
