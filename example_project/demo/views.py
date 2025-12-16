"""
Demo App Views

Sample views to generate various types of Orbit events.
"""

import logging
import time
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Book, Review

logger = logging.getLogger(__name__)


def home(request):
    """Home page with links to test endpoints."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Django Orbit Demo</title>
        <style>
            body { 
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #0f172a;
                color: #f1f5f9;
            }
            h1 { color: #22d3ee; }
            a { color: #22d3ee; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .endpoint { 
                background: #1e293b;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 3px solid #22d3ee;
            }
            .endpoint h3 { margin: 0 0 10px 0; }
            .endpoint p { margin: 0; color: #94a3b8; }
            code { 
                background: #334155;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 0.9em;
            }
            .orbit-link {
                display: inline-block;
                background: linear-gradient(135deg, #22d3ee, #a78bfa);
                color: #020617;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <h1>🛰️ Django Orbit Demo</h1>
        <p>Welcome to the Django Orbit demo project. Use these endpoints to generate events.</p>
        
        <a href="/orbit/" class="orbit-link">Open Orbit Dashboard →</a>
        
        <h2>Test Endpoints</h2>
        
        <div class="endpoint">
            <h3><a href="/books/">GET /books/</a></h3>
            <p>List all books (generates SQL queries)</p>
        </div>
        
        <div class="endpoint">
            <h3><a href="/books/create/">GET /books/create/</a></h3>
            <p>Create a random book (generates INSERT query)</p>
        </div>
        
        <div class="endpoint">
            <h3><a href="/slow/">GET /slow/</a></h3>
            <p>Slow endpoint (demonstrates duration tracking)</p>
        </div>
        
        <div class="endpoint">
            <h3><a href="/log/">GET /log/</a></h3>
            <p>Generate log messages (demonstrates log capture)</p>
        </div>
        
        <div class="endpoint">
            <h3><a href="/error/">GET /error/</a></h3>
            <p>Trigger an exception (demonstrates exception capture)</p>
        </div>
        
        <div class="endpoint">
            <h3><a href="/duplicate-queries/">GET /duplicate-queries/</a></h3>
            <p>Generate duplicate queries (demonstrates N+1 detection)</p>
        </div>
        
        <div class="endpoint">
            <h3>POST /api/data/</h3>
            <p>Submit JSON data: <code>curl -X POST -H "Content-Type: application/json" -d '{"name":"test"}' http://localhost:8000/api/data/</code></p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)


def books_list(request):
    """List all books, generating SQL queries."""
    books = Book.objects.all()[:20]
    
    logger.info(f"Fetched {len(books)} books")
    
    data = [
        {
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'isbn': book.isbn,
        }
        for book in books
    ]
    
    return JsonResponse({'books': data})


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
    
    return JsonResponse({
        'created': True,
        'book': {
            'id': book.id,
            'title': book.title,
            'author': book.author,
        }
    })


def slow_endpoint(request):
    """Simulate a slow endpoint."""
    delay = float(request.GET.get('delay', 1.0))
    
    logger.warning(f"Starting slow operation (delay={delay}s)")
    time.sleep(delay)
    logger.info("Slow operation completed")
    
    return JsonResponse({
        'message': f'Completed after {delay} seconds',
        'delay': delay,
    })


def log_messages(request):
    """Generate various log messages."""
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    
    # Don't actually error, just log
    logger.error("This is an ERROR message (not a real error)")
    
    return JsonResponse({
        'message': 'Generated log messages at all levels',
        'levels': ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
    })


def error_endpoint(request):
    """Trigger an exception to test exception capture."""
    # Intentionally raise an exception
    user_id = request.GET.get('user_id')
    
    if not user_id:
        raise ValueError("user_id parameter is required")
    
    if not user_id.isdigit():
        raise TypeError(f"user_id must be numeric, got: {user_id}")
    
    return JsonResponse({'user_id': int(user_id)})


def duplicate_queries(request):
    """Demonstrate N+1 query problem."""
    books = Book.objects.all()[:10]
    
    # This is intentionally inefficient to demonstrate duplicate detection
    data = []
    for book in books:
        # Each iteration causes a new query (N+1 problem)
        reviews = list(book.reviews.all())
        data.append({
            'title': book.title,
            'review_count': len(reviews),
        })
    
    logger.warning("This endpoint has an N+1 query problem!")
    
    return JsonResponse({'books': data})


@method_decorator(csrf_exempt, name='dispatch')
class ApiDataView(View):
    """API endpoint for testing POST requests with body."""
    
    def post(self, request):
        import json
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        logger.info(f"Received API data: {data}")
        
        return JsonResponse({
            'received': True,
            'data': data,
        }, status=201)
    
    def get(self, request):
        return JsonResponse({
            'message': 'Use POST to submit data',
            'example': {'name': 'test', 'value': 123},
        })
