"""
Demo App Views

Sample views to generate various types of Orbit events.
"""

import logging
import time
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from orbit import __version__ as ORBIT_VERSION
from .models import Book, Review

logger = logging.getLogger(__name__)


def home(request):
    """Home page with links to test endpoints."""
    return render(
        request,
        "orbit/welcome.html",
        {
            "orbit_version": ORBIT_VERSION,
        },
    )


def books_list(request):
    """List all books, generating SQL queries."""
    books = Book.objects.all()[:20]

    logger.info(f"Fetched {len(books)} books")

    data = [
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
        }
        for book in books
    ]

    return JsonResponse({"books": data})


def books_create(request):
    """Create a random book."""
    import random
    import uuid

    book = Book.objects.create(
        title=f"Book {uuid.uuid4().hex[:8]}",
        author=f"Author {random.randint(1, 100)}",
        isbn=f"{random.randint(1000000000000, 9999999999999)}",
        pages=random.randint(100, 500),
    )

    logger.info(f"Created book: {book.title}")

    return JsonResponse(
        {
            "created": True,
            "book": {
                "id": book.id,
                "title": book.title,
                "author": book.author,
            },
        }
    )


def slow_endpoint(request):
    """Simulate a slow endpoint."""
    delay = float(request.GET.get("delay", 1.0))

    logger.warning(f"Starting slow operation (delay={delay}s)")
    time.sleep(delay)
    logger.info("Slow operation completed")

    return JsonResponse(
        {
            "message": f"Completed after {delay} seconds",
            "delay": delay,
        }
    )


def log_messages(request):
    """Generate various log messages."""
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")

    # Don't actually error, just log
    logger.error("This is an ERROR message (not a real error)")

    return JsonResponse(
        {
            "message": "Generated log messages at all levels",
            "levels": ["DEBUG", "INFO", "WARNING", "ERROR"],
        }
    )


def error_endpoint(request):
    """Trigger an exception to test exception capture."""
    # Intentionally raise an exception
    user_id = request.GET.get("user_id")

    if not user_id:
        raise ValueError("user_id parameter is required")

    if not user_id.isdigit():
        raise TypeError(f"user_id must be numeric, got: {user_id}")

    return JsonResponse({"user_id": int(user_id)})


def duplicate_queries(request):
    """Demonstrate N+1 query problem."""
    books = Book.objects.all()[:10]

    # This is intentionally inefficient to demonstrate duplicate detection
    data = []
    for book in books:
        # Each iteration causes a new query (N+1 problem)
        reviews = list(book.reviews.all())
        data.append(
            {
                "title": book.title,
                "review_count": len(reviews),
            }
        )

    logger.warning("This endpoint has an N+1 query problem!")

    return JsonResponse({"books": data})


@method_decorator(csrf_exempt, name="dispatch")
class ApiDataView(View):
    """API endpoint for testing POST requests with body."""

    def post(self, request):
        import json

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        logger.info(f"Received API data: {data}")

        return JsonResponse(
            {
                "received": True,
                "data": data,
            },
            status=201,
        )

    def get(self, request):
        return JsonResponse(
            {
                "message": "Use POST to submit data",
                "example": {"name": "test", "value": 123},
            }
        )
