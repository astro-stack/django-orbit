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
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: 'Inter', system-ui, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #020617;
                color: #f1f5f9;
                line-height: 1.6;
            }
            h1 { 
                color: #22d3ee; 
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
            }
            h2 { 
                color: #f1f5f9;
                margin-top: 2rem;
                font-size: 1.25rem;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .subtitle {
                color: #94a3b8;
                font-size: 1.1rem;
                margin-bottom: 1.5rem;
            }
            a { color: #22d3ee; text-decoration: none; }
            a:hover { text-decoration: underline; }
            
            .quick-start {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 24px;
                margin: 24px 0;
            }
            .quick-start h3 {
                margin: 0 0 12px 0;
                color: #22d3ee;
                font-size: 1rem;
            }
            .quick-start code {
                display: block;
                background: #020617;
                padding: 16px;
                border-radius: 8px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.9rem;
                color: #a5f3fc;
                margin: 8px 0;
                border: 1px solid #1e293b;
            }
            .quick-start .comment { color: #64748b; }
            .quick-start .highlight { color: #fbbf24; }
            
            .buttons {
                display: flex;
                gap: 12px;
                margin: 24px 0;
            }
            .btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                transition: all 0.2s;
            }
            .btn-primary {
                background: linear-gradient(135deg, #22d3ee, #a78bfa);
                color: #020617;
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 20px rgba(34, 211, 238, 0.3);
                text-decoration: none;
            }
            .btn-secondary {
                background: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
            }
            .btn-secondary:hover {
                background: #334155;
                text-decoration: none;
            }
            
            .endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 12px;
            }
            .endpoint { 
                background: #0f172a;
                padding: 16px;
                border-radius: 8px;
                border: 1px solid #1e293b;
                transition: all 0.2s;
            }
            .endpoint:hover {
                border-color: #22d3ee;
                background: #1e293b;
            }
            .endpoint h3 { 
                margin: 0 0 6px 0; 
                font-size: 0.95rem;
            }
            .endpoint p { 
                margin: 0; 
                color: #64748b; 
                font-size: 0.85rem;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 600;
                margin-left: 8px;
            }
            .badge-get { background: #22d3ee20; color: #22d3ee; }
            .badge-post { background: #a78bfa20; color: #a78bfa; }
            
            .features {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin: 24px 0;
            }
            .feature {
                text-align: center;
                padding: 16px;
            }
            .feature-icon {
                font-size: 1.5rem;
                margin-bottom: 8px;
            }
            .feature-title {
                font-weight: 600;
                color: #f1f5f9;
                font-size: 0.9rem;
            }
            .feature-desc {
                color: #64748b;
                font-size: 0.8rem;
            }
            
            footer {
                margin-top: 48px;
                padding-top: 24px;
                border-top: 1px solid #1e293b;
                color: #64748b;
                font-size: 0.85rem;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>🛰️ Django Orbit</h1>
        <p class="subtitle">Satellite Observability for Django — Debug without touching your DOM</p>
        
        <div class="features">
            <div class="feature">
                <div class="feature-icon">🌐</div>
                <div class="feature-title">Request Tracking</div>
                <div class="feature-desc">Every HTTP request logged</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🗄️</div>
                <div class="feature-title">SQL Recording</div>
                <div class="feature-desc">N+1 & slow query detection</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🚨</div>
                <div class="feature-title">Exception Capture</div>
                <div class="feature-desc">Full traceback history</div>
            </div>
        </div>
        
        <div class="buttons">
            <a href="/orbit/" class="btn btn-primary">🛰️ Open Orbit Dashboard</a>
            <a href="https://github.com/astro-stack/django-orbit" class="btn btn-secondary" target="_blank">⭐ GitHub</a>
        </div>
        
        <div class="quick-start">
            <h3>⚡ Try it in 30 seconds</h3>
            <code>
<span class="comment"># Clone and run</span>
<br/>git clone https://github.com/astro-stack/django-orbit.git
<br/>cd django-orbit
<br/><span class="highlight">python demo.py setup</span>    <span class="comment"># Creates sample data</span>
<br/>python manage.py runserver

<br/><span class="comment"># Then open: http://localhost:8000/orbit/</span>
            </code>
        </div>
        
        <h2>🧪 Test Endpoints</h2>
        <p style="color: #64748b; margin-bottom: 16px;">Click these to generate different types of events in Orbit:</p>
        
        <div class="endpoints">
            <div class="endpoint">
                <h3><a href="/books/">📚 /books/</a><span class="badge badge-get">GET</span></h3>
                <p>List books — generates SQL queries</p>
            </div>
            
            <div class="endpoint">
                <h3><a href="/books/create/">➕ /books/create/</a><span class="badge badge-get">GET</span></h3>
                <p>Create book — INSERT query + log</p>
            </div>
            
            <div class="endpoint">
                <h3><a href="/slow/">🐢 /slow/</a><span class="badge badge-get">GET</span></h3>
                <p>Slow endpoint — 1 second delay</p>
            </div>
            
            <div class="endpoint">
                <h3><a href="/log/">📝 /log/</a><span class="badge badge-get">GET</span></h3>
                <p>Generate logs — all levels</p>
            </div>
            
            <div class="endpoint">
                <h3><a href="/error/">💥 /error/</a><span class="badge badge-get">GET</span></h3>
                <p>Trigger exception — with traceback</p>
            </div>
            
            <div class="endpoint">
                <h3><a href="/duplicate-queries/">🔄 /duplicate-queries/</a><span class="badge badge-get">GET</span></h3>
                <p>N+1 problem — duplicate detection</p>
            </div>
        </div>
        
        <footer>
            Django Orbit v0.1.0 • MIT License • Made with ❤️ by <a href="https://astro-stack.github.io">Astro Stack</a>
        </footer>
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
