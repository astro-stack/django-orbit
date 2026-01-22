#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django Orbit Demo Tool

Unified script for setting up and running demos.

Usage:
    python demo.py setup     - Create sample data: books, reviews + ALL Orbit entry types
    python demo.py fill      - Test live watchers by making requests (requires running server)
    python demo.py simulate  - Simulate continuous traffic for testing
    python demo.py clear     - Clear all Orbit entries
    python demo.py status    - Show current entry counts

Quick Start:
    1. python demo.py setup        # Create sample data (no server needed)
    2. python manage.py runserver  # Start server
    3. Open http://localhost:8000/orbit/
"""

import os
import sys

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
import random
import argparse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'example_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()


# ============================================================================
# SETUP COMMAND - Create sample data
# ============================================================================

BOOK_TITLES = [
    "The Pragmatic Programmer", "Clean Code", "Design Patterns",
    "Refactoring", "The Mythical Man-Month", "Code Complete",
    "Domain-Driven Design", "Continuous Delivery", "Programming Pearls",
    "Working Effectively with Legacy Code", "Test Driven Development",
    "Head First Design Patterns", "The Clean Coder", "Release It!",
]

AUTHORS = [
    "David Thomas", "Andrew Hunt", "Robert C. Martin", "Erich Gamma",
    "Martin Fowler", "Fred Brooks", "Steve McConnell", "Eric Evans",
    "Jez Humble", "Donald Knuth", "Jon Bentley", "Michael Feathers",
]

REVIEWER_NAMES = [
    "Alice Developer", "Bob Engineer", "Charlie Coder",
    "Diana Programmer", "Eve Hacker", "Frank Builder",
]


def generate_historical_data():
    """Generate historical data spread over time for stats charts."""
    from orbit.models import OrbitEntry
    from datetime import timedelta
    from django.utils import timezone
    
    print("\n📊 Generating historical data for stats charts...")
    
    now = timezone.now()
    entries_to_create = []
    
    # Generate requests distributed over the last 7 days
    print("   Generating time-distributed requests...")
    paths = ['/', '/books/', '/api/users/', '/api/products/', '/admin/', '/api/orders/']
    methods = ['GET', 'GET', 'GET', 'POST', 'PUT', 'DELETE']
    status_codes = [200, 200, 200, 201, 404, 500]
    
    for hours_ago in range(0, 168, 4):  # Every 4 hours for 7 days = 42 time slots
        time_offset = timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        created_time = now - time_offset
        
        # More requests during business hours
        num_requests = random.randint(1, 3) if 8 <= created_time.hour <= 20 else random.randint(0, 1)
        
        for _ in range(num_requests):
            entries_to_create.append(OrbitEntry(
                type='request',
                payload={
                    'method': random.choice(methods),
                    'path': random.choice(paths),
                    'status_code': random.choices(status_codes, weights=[50, 30, 10, 5, 3, 2])[0],
                    'client_ip': f'192.168.1.{random.randint(1, 255)}',
                },
                duration_ms=random.uniform(10, 500),
                created_at=created_time,
            ))
    
    # Generate exceptions distributed over time
    print("   Generating time-distributed exceptions...")
    exception_types = ['ValueError', 'KeyError', 'TypeError', 'AttributeError', 'PermissionDenied']
    
    for hours_ago in range(0, 168, 12):  # Every 12 hours
        if random.random() < 0.7:
            time_offset = timedelta(hours=hours_ago, minutes=random.randint(0, 59))
            created_time = now - time_offset
            
            entries_to_create.append(OrbitEntry(
                type='exception',
                payload={
                    'exception_type': random.choice(exception_types),
                    'message': f'Error in operation at {created_time.strftime("%H:%M")}',
                    'request_method': 'POST',
                    'request_path': '/api/action/',
                },
                created_at=created_time,
            ))
    
    # Generate queries distributed over time
    print("   Generating time-distributed queries...")
    for hours_ago in range(0, 168, 6):  # Every 6 hours
        time_offset = timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        created_time = now - time_offset
        
        for _ in range(random.randint(1, 4)):
            is_slow = random.random() < 0.1
            is_dup = random.random() < 0.15
            
            entries_to_create.append(OrbitEntry(
                type='query',
                payload={
                    'sql': f'SELECT * FROM table_{random.randint(1, 5)} WHERE id = %s',
                    'params': [random.randint(1, 100)],
                    'is_slow': is_slow,
                    'is_duplicate': is_dup,
                },
                duration_ms=random.uniform(200, 800) if is_slow else random.uniform(1, 20),
                created_at=created_time,
            ))
    
    # Generate cache ops distributed over time
    print("   Generating time-distributed cache ops...")
    for hours_ago in range(0, 168, 8):  # Every 8 hours
        time_offset = timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        created_time = now - time_offset
        
        for _ in range(random.randint(1, 3)):
            entries_to_create.append(OrbitEntry(
                type='cache',
                payload={
                    'operation': random.choice(['get', 'get', 'get', 'set']),
                    'key': f'cache_key_{random.randint(1, 20)}',
                    'hit': random.random() < 0.7,
                },
                duration_ms=random.uniform(0.1, 5),
                created_at=created_time,
            ))
    
    # Generate transactions distributed over time (v0.6.0)
    print("   Generating time-distributed transactions...")
    for hours_ago in range(0, 168, 8):  # Every 8 hours
        time_offset = timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        created_time = now - time_offset
        
        for _ in range(random.randint(1, 3)):
            is_rollback = random.random() < 0.15  # 15% rollback rate
            entries_to_create.append(OrbitEntry(
                type='transaction',
                payload={
                    'status': 'rolled_back' if is_rollback else 'committed',
                    'using': 'default',
                    'exception': 'IntegrityError' if is_rollback else None,
                },
                duration_ms=random.uniform(5, 100),
                created_at=created_time,
            ))
    
    # Generate storage ops distributed over time (v0.6.0)
    print("   Generating time-distributed storage ops...")
    for hours_ago in range(0, 168, 12):  # Every 12 hours
        time_offset = timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        created_time = now - time_offset
        
        for _ in range(random.randint(1, 2)):
            op = random.choice(['save', 'open', 'delete', 'exists'])
            entries_to_create.append(OrbitEntry(
                type='storage',
                payload={
                    'operation': op,
                    'path': f'uploads/file_{random.randint(1, 100)}.pdf',
                    'backend': random.choice(['FileSystemStorage', 'S3Boto3Storage']),
                    'size': random.randint(1000, 50000) if op == 'save' else None,
                },
                duration_ms=random.uniform(10, 200),
                created_at=created_time,
            ))
    
    # Bulk create all entries at once
    print(f"   Bulk inserting {len(entries_to_create)} entries...")
    OrbitEntry.objects.bulk_create(entries_to_create, batch_size=100)
    
    print("   ✓ Historical data generated!")



def setup_demo():
    """Create all sample data for demos."""
    from example_project.demo.models import Book, Review
    from orbit.models import OrbitEntry
    
    print("\n" + "="*60)
    print("🛰️  Django Orbit - Demo Setup")
    print("="*60)
    
    # Clear existing data
    print("\n🗑️  Clearing existing data...")
    Book.objects.all().delete()
    OrbitEntry.objects.all().delete()
    print("   ✓ Cleared all data")
    
    # Create books
    print("\n📚 Creating sample books...")
    books = []
    for i, title in enumerate(BOOK_TITLES[:12]):
        book = Book.objects.create(
            title=f"{title} (Ed. {random.randint(1, 3)})",
            author=random.choice(AUTHORS),
            isbn=f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}",
            pages=random.randint(200, 600),
        )
        books.append(book)
        print(f"   ✓ {book.title[:45]}...")
    
    # Create reviews
    print("\n⭐ Creating reviews...")
    for book in books:
        for _ in range(random.randint(1, 3)):
            Review.objects.create(
                book=book,
                reviewer_name=random.choice(REVIEWER_NAMES),
                rating=random.randint(3, 5),
                comment="Great resource for developers!",
            )
    print(f"   ✓ Created {Review.objects.count()} reviews")
    
    # Create sample query entries
    print("\n🗄️ Creating sample query entries...")
    query_samples = [
        {'sql': 'SELECT * FROM demo_book WHERE id = %s', 'params': [1], 'duration_ms': 2.3, 'is_slow': False, 'is_duplicate': False},
        {'sql': 'SELECT * FROM demo_book ORDER BY created_at DESC LIMIT 10', 'params': [], 'duration_ms': 5.1, 'is_slow': False, 'is_duplicate': False},
        {'sql': 'SELECT COUNT(*) FROM demo_review WHERE book_id = %s', 'params': [5], 'duration_ms': 1.2, 'is_slow': False, 'is_duplicate': True},
        {'sql': 'SELECT * FROM auth_user WHERE email LIKE %s', 'params': ['%@example.com'], 'duration_ms': 650.5, 'is_slow': True, 'is_duplicate': False},
        {'sql': 'UPDATE demo_book SET title = %s WHERE id = %s', 'params': ['New Title', 3], 'duration_ms': 3.4, 'is_slow': False, 'is_duplicate': False},
    ]
    for query in query_samples:
        OrbitEntry.objects.create(
            type='query',
            payload=query,
            duration_ms=query['duration_ms'],
        )
        slow_tag = " [SLOW]" if query['is_slow'] else ""
        dup_tag = " [DUP]" if query['is_duplicate'] else ""
        print(f"   ✓ {query['sql'][:45]}...{slow_tag}{dup_tag}")
    
    # Create sample logs
    print("\n📝 Creating sample log entries...")
    log_samples = [
        {'level': 'INFO', 'message': 'User john@example.com logged in', 'logger': 'auth.views'},
        {'level': 'WARNING', 'message': 'Rate limit approaching for API key abc123', 'logger': 'api.middleware'},
        {'level': 'DEBUG', 'message': 'Cache hit for key: user_profile_123', 'logger': 'cache.utils'},
        {'level': 'ERROR', 'message': 'Failed to connect to payment gateway', 'logger': 'payments.gateway'},
        {'level': 'INFO', 'message': 'Order #789 processed successfully', 'logger': 'orders.views'},
    ]
    for log in log_samples:
        OrbitEntry.objects.create(type='log', payload=log)
        print(f"   ✓ {log['level']}: {log['message'][:40]}...")
    
    # Create sample exceptions
    print("\n🚨 Creating sample exception entries...")
    exception_samples = [
        {
            'exception_type': 'ValueError',
            'message': 'Invalid input: expected integer, got string',
            'request_method': 'POST',
            'request_path': '/api/users/',
            'traceback': [
                {'filename': '/app/views.py', 'lineno': 42, 'name': 'create_user', 'line': 'age = int(data["age"])'},
            ]
        },
        {
            'exception_type': 'KeyError',
            'message': "'email'",
            'request_method': 'POST',
            'request_path': '/api/register/',
            'traceback': [
                {'filename': '/app/auth.py', 'lineno': 18, 'name': 'register', 'line': 'email = request.data["email"]'},
            ]
        },
        {
            'exception_type': 'PermissionDenied',
            'message': 'You do not have permission to access this resource',
            'request_method': 'DELETE',
            'request_path': '/api/admin/users/5/',
            'traceback': []
        },
    ]
    for exc in exception_samples:
        OrbitEntry.objects.create(type='exception', payload=exc)
        print(f"   ✗ {exc['exception_type']}: {exc['message'][:40]}...")
    
    # Create sample request entries
    print("\n🌐 Creating sample request entries...")
    request_samples = [
        {'method': 'GET', 'path': '/', 'status_code': 200, 'client_ip': '192.168.1.1'},
        {'method': 'GET', 'path': '/books/', 'status_code': 200, 'client_ip': '192.168.1.2'},
        {'method': 'POST', 'path': '/api/login/', 'status_code': 200, 'client_ip': '10.0.0.1'},
        {'method': 'GET', 'path': '/admin/', 'status_code': 302, 'client_ip': '127.0.0.1'},
        {'method': 'POST', 'path': '/api/checkout/', 'status_code': 500, 'client_ip': '192.168.1.5'},
        {'method': 'GET', 'path': '/api/products/999/', 'status_code': 404, 'client_ip': '192.168.1.10'},
    ]
    for req in request_samples:
        OrbitEntry.objects.create(
            type='request',
            payload=req,
            duration_ms=random.uniform(10, 300),
        )
        emoji = "✓" if req['status_code'] < 400 else "✗"
        print(f"   {emoji} {req['method']} {req['path']} → {req['status_code']}")
    
    # Create sample jobs
    print("\n⏰ Creating sample job entries...")
    job_samples = [
        {'name': 'send_welcome_email', 'queue': 'email', 'status': 'completed'},
        {'name': 'process_payment', 'queue': 'payments', 'status': 'completed'},
        {'name': 'generate_report', 'queue': 'reports', 'status': 'failed', 'error': 'Timeout'},
        {'name': 'sync_inventory', 'queue': 'sync', 'status': 'completed'},
        {'name': 'send_newsletter', 'queue': 'email', 'status': 'processing'},
    ]
    for job in job_samples:
        OrbitEntry.objects.create(
            type='job',
            payload=job,
            duration_ms=random.uniform(100, 2000),
        )
        emoji = "✓" if job['status'] == 'completed' else ("⏳" if job['status'] == 'processing' else "✗")
        print(f"   {emoji} {job['name']} ({job['status']})")
    
    # Create sample command entries (Phase 1)
    print("\n🟣 Creating sample command entries...")
    command_samples = [
        {'command': 'migrate', 'args': [], 'options': {'database': 'default'}, 'exit_code': 0, 'output': 'Migrations applied successfully'},
        {'command': 'collectstatic', 'args': [], 'options': {'no_input': True}, 'exit_code': 0, 'output': '120 static files copied'},
        {'command': 'createsuperuser', 'args': [], 'options': {}, 'exit_code': 1, 'output': 'Error: That username is already taken'},
        {'command': 'makemigrations', 'args': ['demo'], 'options': {}, 'exit_code': 0, 'output': 'No changes detected'},
    ]
    for cmd in command_samples:
        OrbitEntry.objects.create(
            type='command',
            payload=cmd,
            duration_ms=random.uniform(500, 3000),
        )
        emoji = "✓" if cmd['exit_code'] == 0 else "✗"
        print(f"   {emoji} {cmd['command']} → exit {cmd['exit_code']}")
    
    # Create sample cache entries (Phase 1)
    print("\n🟠 Creating sample cache entries...")
    cache_samples = [
        {'operation': 'get', 'key': 'user_profile_123', 'hit': True, 'backend': 'default'},
        {'operation': 'get', 'key': 'session_abc', 'hit': False, 'backend': 'default'},
        {'operation': 'set', 'key': 'user_profile_456', 'ttl': 3600, 'backend': 'default'},
        {'operation': 'delete', 'key': 'old_session_xyz', 'backend': 'default'},
        {'operation': 'get', 'key': 'api_ratelimit_192.168.1.1', 'hit': True, 'backend': 'redis'},
    ]
    for cache in cache_samples:
        OrbitEntry.objects.create(
            type='cache',
            payload=cache,
        )
        hit_str = "(hit)" if cache.get('hit') else "(miss)" if cache.get('hit') is False else ""
        print(f"   ✓ {cache['operation'].upper()} {cache['key'][:30]} {hit_str}")
    
    # Create sample model events (Phase 1)
    print("\n🔵 Creating sample model event entries...")
    model_samples = [
        {'model': 'demo.Book', 'action': 'created', 'pk': '1', 'representation': 'The Pragmatic Programmer'},
        {'model': 'demo.Book', 'action': 'updated', 'pk': '2', 'changes': {'title': {'old': 'Old Title', 'new': 'Clean Code'}}},
        {'model': 'auth.User', 'action': 'created', 'pk': '5', 'representation': 'john@example.com'},
        {'model': 'demo.Review', 'action': 'deleted', 'pk': '3', 'representation': 'Review by Alice'},
    ]
    for model in model_samples:
        OrbitEntry.objects.create(
            type='model',
            payload=model,
        )
        print(f"   ✓ {model['model']} {model['action']} (pk={model['pk']})")
    
    # Create sample HTTP client entries (Phase 1)
    print("\n🩷 Creating sample HTTP client entries...")
    http_samples = [
        {'method': 'POST', 'url': 'https://api.stripe.com/v1/charges', 'status_code': 200, 'response_size': 1234},
        {'method': 'GET', 'url': 'https://api.github.com/users/django', 'status_code': 200, 'response_size': 4567},
        {'method': 'POST', 'url': 'https://api.sendgrid.com/v3/mail/send', 'status_code': 202, 'response_size': 89},
        {'method': 'GET', 'url': 'https://api.openai.com/v1/models', 'status_code': 401, 'error': 'Unauthorized'},
    ]
    for http in http_samples:
        OrbitEntry.objects.create(
            type='http_client',
            payload=http,
            duration_ms=random.uniform(100, 800),
        )
        emoji = "✓" if http['status_code'] < 400 else "✗"
        print(f"   {emoji} {http['method']} {http['url'][:40]}... → {http['status_code']}")
    
    # Create sample mail entries (v0.4.0)
    print("\n📧 Creating sample mail entries...")
    mail_samples = [
        {'subject': 'Welcome to Our Platform!', 'from_email': 'noreply@example.com', 'to': ['john@example.com'], 'cc': [], 'bcc': [], 'body': 'Welcome John! Your account is ready.'},
        {'subject': 'Password Reset Request', 'from_email': 'security@example.com', 'to': ['jane@example.com'], 'cc': [], 'bcc': ['audit@example.com'], 'body': 'Click here to reset your password...'},
        {'subject': 'Order Confirmation #12345', 'from_email': 'orders@shop.com', 'to': ['customer@example.com', 'billing@example.com'], 'cc': [], 'bcc': [], 'body': 'Thank you for your order!', 'attachments': [{'name': 'invoice.pdf', 'size': 45678, 'content_type': 'application/pdf'}]},
        {'subject': 'Weekly Newsletter', 'from_email': 'newsletter@company.com', 'to': ['subscribers@example.com'], 'cc': [], 'bcc': [], 'body': 'This week in tech...', 'html_body': '<h1>Weekly Newsletter</h1><p>This week...</p>'},
    ]
    for mail in mail_samples:
        OrbitEntry.objects.create(
            type='mail',
            payload=mail,
        )
        to_str = mail['to'][0] if mail['to'] else '?'
        if len(mail['to']) > 1:
            to_str += f" (+{len(mail['to']) - 1})"
        print(f"   ✓ {mail['subject'][:35]}... → {to_str}")
    
    # Create sample signal entries (v0.4.0)
    print("\n⚡ Creating sample signal entries...")
    signal_samples = [
        {'signal': 'django.db.models.signals.post_save', 'sender': 'demo.Book', 'receivers_count': 2, 'kwargs': {'created': 'True', 'instance': '<Book: Clean Code>'}},
        {'signal': 'django.db.models.signals.post_delete', 'sender': 'demo.Review', 'receivers_count': 1, 'kwargs': {'instance': '<Review: 5 stars>'}},
        {'signal': 'django.contrib.auth.signals.user_logged_in', 'sender': 'auth.User', 'receivers_count': 3, 'kwargs': {'user': '<User: admin>'}},
        {'signal': 'payments.signals.payment_completed', 'sender': 'payments.Payment', 'receivers_count': 2, 'kwargs': {'amount': '99.99', 'order_id': '12345'}},
    ]
    for sig in signal_samples:
        OrbitEntry.objects.create(
            type='signal',
            payload=sig,
        )
        print(f"   ✓ {sig['signal'].split('.')[-1]} from {sig['sender']}")
    
    # Create sample Redis entries (v0.5.0)
    print("\n🔴 Creating sample Redis entries...")
    redis_samples = [
        {'operation': 'GET', 'key': 'user:1234:session', 'result_size': 256},
        {'operation': 'SET', 'key': 'cache:homepage', 'result_size': None},
        {'operation': 'HGETALL', 'key': 'user:1234:profile', 'result_size': 12},
        {'operation': 'LPUSH', 'key': 'queue:emails', 'result_size': 1},
        {'operation': 'INCR', 'key': 'stats:page_views', 'result_size': None},
    ]
    for redis_op in redis_samples:
        OrbitEntry.objects.create(
            type='redis',
            payload=redis_op,
            duration_ms=random.uniform(0.5, 5.0),
        )
        print(f"   ✓ {redis_op['operation']} {redis_op['key']}")
    
    # Create sample Gate entries (v0.5.0)
    print("\n🛡️ Creating sample Gate entries...")
    gate_samples = [
        {'user': 'admin', 'permission': 'auth.add_user', 'result': 'granted', 'backend': 'ModelBackend'},
        {'user': 'john_doe', 'permission': 'books.change_book', 'result': 'granted', 'backend': 'ModelBackend'},
        {'user': 'guest', 'permission': 'admin.view_logentry', 'result': 'denied', 'backend': 'ModelBackend'},
        {'user': 'john_doe', 'permission': 'books.delete_review', 'result': 'denied', 'object': 'Review:42', 'backend': 'ModelBackend'},
        {'user': 'admin', 'permission': 'auth.change_user', 'result': 'granted', 'backend': 'ModelBackend'},
    ]
    for gate in gate_samples:
        OrbitEntry.objects.create(
            type='gate',
            payload=gate,
        )
        icon = "✓" if gate['result'] == 'granted' else "✗"
        print(f"   {icon} {gate['permission']} → {gate['user']}")
    
    # Create sample Transaction entries (v0.6.0)
    print("\n🔄 Creating sample Transaction entries...")
    transaction_samples = [
        {'status': 'committed', 'using': 'default', 'exception': None},
        {'status': 'committed', 'using': 'default', 'exception': None},
        {'status': 'rolled_back', 'using': 'default', 'exception': 'IntegrityError: duplicate key'},
        {'status': 'committed', 'using': 'replica', 'exception': None},
        {'status': 'rolled_back', 'using': 'default', 'exception': 'ValueError: invalid data'},
    ]
    for tx in transaction_samples:
        OrbitEntry.objects.create(
            type='transaction',
            payload=tx,
            duration_ms=random.uniform(5, 100),
        )
        icon = "✓" if tx['status'] == 'committed' else "✗"
        print(f"   {icon} transaction.{tx['status']} ({tx['using']})")
    
    # Create sample Storage entries (v0.6.0)
    print("\n📁 Creating sample Storage entries...")
    storage_samples = [
        {'operation': 'save', 'path': 'uploads/report_2025.pdf', 'backend': 'FileSystemStorage', 'size': 45678},
        {'operation': 'save', 'path': 'media/avatars/user_123.jpg', 'backend': 'S3Boto3Storage', 'size': 12500},
        {'operation': 'open', 'path': 'uploads/report_2025.pdf', 'backend': 'FileSystemStorage'},
        {'operation': 'exists', 'path': 'media/avatars/user_456.jpg', 'backend': 'S3Boto3Storage', 'exists': False},
        {'operation': 'delete', 'path': 'temp/old_cache.tmp', 'backend': 'FileSystemStorage'},
    ]
    for st in storage_samples:
        OrbitEntry.objects.create(
            type='storage',
            payload=st,
            duration_ms=random.uniform(10, 200),
        )
        print(f"   ✓ {st['operation'].upper()} {st['path'][:35]}...")
    
    # Generate historical data for stats charts
    generate_historical_data()
    
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    print(f"\n   📚 Books: {Book.objects.count()}")
    print(f"   ⭐ Reviews: {Review.objects.count()}")
    print(f"\n   � Orbit Entries:")
    print(f"   🌐 Requests: {OrbitEntry.objects.requests().count()}")
    print(f"   🗄️  Queries: {OrbitEntry.objects.queries().count()}")
    print(f"   �📝 Logs: {OrbitEntry.objects.logs().count()}")
    print(f"   🚨 Exceptions: {OrbitEntry.objects.exceptions().count()}")
    print(f"   ⏰ Jobs: {OrbitEntry.objects.jobs().count()}")
    print(f"   🟣 Commands: {OrbitEntry.objects.commands().count()}")
    print(f"   🟠 Cache: {OrbitEntry.objects.cache_ops().count()}")
    print(f"   🔵 Models: {OrbitEntry.objects.models().count()}")
    print(f"   🩷 HTTP Client: {OrbitEntry.objects.http_client().count()}")
    print(f"   📧 Mail: {OrbitEntry.objects.mails().count()}")
    print(f"   ⚡ Signals: {OrbitEntry.objects.signals().count()}")
    print(f"   🔴 Redis: {OrbitEntry.objects.redis_ops().count()}")
    print(f"   🛡️ Gates: {OrbitEntry.objects.gates().count()}")
    print(f"   🔄 Transactions: {OrbitEntry.objects.filter(type='transaction').count()}")
    print(f"   📁 Storage: {OrbitEntry.objects.filter(type='storage').count()}")
    print(f"   ─────────────")
    print(f"   Total: {OrbitEntry.objects.count()}")
    print(f"\n🌐 Demo: http://localhost:8000/")
    print(f"🛰️  Orbit: http://localhost:8000/orbit/")
    print(f"\n💡 TIP: Run 'python demo.py fill' to generate live events!\n")



def fill_dashboard():
    """Fill dashboard with all event types by hitting endpoints."""
    import requests
    
    BASE_URL = "http://localhost:8000"
    
    print("\n" + "="*60)
    print("🛰️  Django Orbit - Fill Dashboard")
    print("="*60)
    print("\nGenerating all event types...")
    
    # Check server
    try:
        requests.get(f"{BASE_URL}/", timeout=3)
    except:
        print(f"\n❌ Server not responding at {BASE_URL}")
        print("   Start the server first: python manage.py runserver\n")
        return
    
    print("\n🌐 Generating Requests + Queries...")
    
    # Generate requests and queries
    endpoints = [
        ("/", "Home page"),
        ("/books/", "List books (queries)"),
        ("/books/", "List books (queries)"),
        ("/books/create/", "Create book"),
        ("/duplicate-queries/", "N+1 queries"),
        ("/slow/?delay=0.3", "Slow request"),
    ]
    
    for path, desc in endpoints:
        try:
            r = requests.get(f"{BASE_URL}{path}", timeout=10)
            print(f"   ✓ {desc} → {r.status_code}")
        except Exception as e:
            print(f"   ✗ {desc} → Error")
    
    print("\n📝 Generating Logs...")
    try:
        r = requests.get(f"{BASE_URL}/log/", timeout=5)
        print(f"   ✓ Log messages → {r.status_code}")
    except:
        print(f"   ✗ Log messages → Error")
    
    print("\n🚨 Generating Exceptions...")
    # Generate multiple exceptions with different types
    exception_endpoints = [
        ("/error/", "ValueError"),
        ("/error/?user_id=abc", "TypeError"),  # Different error
    ]
    for path, error_type in exception_endpoints:
        try:
            r = requests.get(f"{BASE_URL}{path}", timeout=5)
            print(f"   ✓ {error_type} captured → {r.status_code}")
        except:
            print(f"   ✓ {error_type} captured (500)")
    
    print("\n📮 Generating POST request...")
    try:
        r = requests.post(f"{BASE_URL}/api/data/", 
                         json={"name": "demo_user", "action": "test"},
                         timeout=5)
        print(f"   ✓ POST /api/data/ → {r.status_code}")
    except:
        print(f"   ✗ POST request → Error")
    
    # Show final counts
    from orbit.models import OrbitEntry
    
    print("\n🟠 Testing Cache Watcher...")
    try:
        from django.core.cache import cache
        # These will trigger the cache watcher
        cache.set('demo_test_key', 'demo_value', 60)
        cache.get('demo_test_key')
        cache.get('nonexistent_key')  # Will be a miss
        cache.delete('demo_test_key')
        print("   ✓ Cache operations recorded")
    except Exception as e:
        print(f"   ✗ Cache test failed: {e}")
    
    print("\n🔵 Model events are tracked automatically!")
    print("   ✓ Creating/updating books triggers model watcher")
    
    print("\n🩷 Testing HTTP Client Watcher...")
    print("   ✓ All requests above were tracked (outgoing HTTP)")
    
    print("\n" + "="*60)
    print("📊 Dashboard Filled!")
    print("="*60)
    print(f"\n   🌐 Requests: {OrbitEntry.objects.requests().count()}")
    print(f"   🗄️  Queries: {OrbitEntry.objects.queries().count()}")
    print(f"   📝 Logs: {OrbitEntry.objects.logs().count()}")
    print(f"   🚨 Exceptions: {OrbitEntry.objects.exceptions().count()}")
    print(f"   ⏰ Jobs: {OrbitEntry.objects.jobs().count()}")
    print(f"   🟣 Commands: {OrbitEntry.objects.commands().count()}")
    print(f"   🟠 Cache: {OrbitEntry.objects.cache_ops().count()}")
    print(f"   🔵 Models: {OrbitEntry.objects.models().count()}")
    print(f"   🩷 HTTP Client: {OrbitEntry.objects.http_client().count()}")
    print(f"\n🛰️  Open: http://localhost:8000/orbit/\n")


# ============================================================================
# SIMULATE COMMAND - Generate live activity
# ============================================================================

def simulate_activity(duration=60, interval=0.5):
    """Simulate realistic traffic patterns."""
    import requests
    
    BASE_URL = "http://localhost:8000"
    
    print("\n" + "="*60)
    print("🛰️  Django Orbit - Activity Simulator")
    print("="*60)
    print(f"\n📡 Target: {BASE_URL}")
    print(f"⏱️  Duration: {duration}s | Interval: {interval}s")
    print("\n" + "-"*60)
    print("Starting... (Press Ctrl+C to stop)")
    print("-"*60 + "\n")
    
    # Check server
    try:
        requests.get(f"{BASE_URL}/", timeout=3)
    except:
        print(f"❌ Server not responding at {BASE_URL}")
        print("   Start the server first: python manage.py runserver\n")
        return
    
    endpoints = [
        ("GET", "/", 30),
        ("GET", "/books/", 25),
        ("GET", "/books/create/", 10),
        ("GET", "/slow/?delay=0.5", 5),
        ("GET", "/log/", 15),
        ("GET", "/duplicate-queries/", 5),
        ("POST", "/api/data/", 8),
        ("GET", "/error/", 2),
    ]
    
    # Create weighted list
    weighted = []
    for method, path, weight in endpoints:
        weighted.extend([(method, path)] * weight)
    
    start_time = time.time()
    count = 0
    errors = 0
    
    try:
        while time.time() - start_time < duration:
            method, path = random.choice(weighted)
            url = f"{BASE_URL}{path}"
            
            try:
                if method == "POST":
                    data = {"name": f"test_{random.randint(1, 100)}", "value": random.randint(1, 1000)}
                    r = requests.post(url, json=data, timeout=10)
                else:
                    r = requests.get(url, timeout=10)
                
                emoji = "✅" if r.status_code < 400 else "❌"
                print(f"{emoji} {method} {path} → {r.status_code}")
                count += 1
                
            except Exception as e:
                errors += 1
                print(f"⚠️  {method} {path} → Error")
            
            time.sleep(interval * random.uniform(0.5, 1.5))
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
    
    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print("📊 Simulation Complete!")
    print("="*60)
    print(f"\n   Requests: {count}")
    print(f"   Errors: {errors}")
    print(f"   Duration: {elapsed:.1f}s")
    print(f"   Rate: {count/elapsed:.1f} req/s")
    print(f"\n🛰️  Check dashboard: {BASE_URL}/orbit/\n")


# ============================================================================
# CLEAR COMMAND - Clear all Orbit entries
# ============================================================================

def clear_entries():
    """Clear all Orbit entries."""
    from orbit.models import OrbitEntry
    
    count = OrbitEntry.objects.count()
    OrbitEntry.objects.all().delete()
    print(f"\n🗑️  Cleared {count} Orbit entries\n")


# ============================================================================
# STATUS COMMAND - Show current counts
# ============================================================================

def show_status():
    """Show current entry counts."""
    from orbit.models import OrbitEntry
    from example_project.demo.models import Book, Review
    
    print("\n" + "="*40)
    print("🛰️  Django Orbit - Status")
    print("="*40)
    print(f"\n📊 Demo Data:")
    print(f"   📚 Books: {Book.objects.count()}")
    print(f"   ⭐ Reviews: {Review.objects.count()}")
    print(f"\n📊 Orbit Entries:")
    print(f"   🌐 Requests: {OrbitEntry.objects.requests().count()}")
    print(f"   🗄️  Queries: {OrbitEntry.objects.queries().count()}")
    print(f"   📝 Logs: {OrbitEntry.objects.logs().count()}")
    print(f"   🚨 Exceptions: {OrbitEntry.objects.exceptions().count()}")
    print(f"   ⏰ Jobs: {OrbitEntry.objects.jobs().count()}")
    print(f"   🟣 Commands: {OrbitEntry.objects.commands().count()}")
    print(f"   🟠 Cache: {OrbitEntry.objects.cache_ops().count()}")
    print(f"   🔵 Models: {OrbitEntry.objects.models().count()}")
    print(f"   🩷 HTTP Client: {OrbitEntry.objects.http_client().count()}")
    print(f"   📧 Mail: {OrbitEntry.objects.mails().count()}")
    print(f"   ⚡ Signals: {OrbitEntry.objects.signals().count()}")
    print(f"   🔴 Redis: {OrbitEntry.objects.redis_ops().count()}")
    print(f"   🛡️ Gates: {OrbitEntry.objects.gates().count()}")
    print(f"   🔄 Transactions: {OrbitEntry.objects.filter(type='transaction').count()}")
    print(f"   📁 Storage: {OrbitEntry.objects.filter(type='storage').count()}")
    print(f"   ─────────────")
    print(f"   Total: {OrbitEntry.objects.count()}")
    print()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Django Orbit Demo Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo.py setup              Create sample data (books, reviews, logs, jobs)
  python demo.py fill               Fill dashboard with all event types (requires server)
  python demo.py simulate           Simulate live activity for 60 seconds
  python demo.py simulate -d 30     Simulate for 30 seconds
  python demo.py clear              Clear all Orbit entries
  python demo.py status             Show current counts
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Setup command
    subparsers.add_parser('setup', help='Create sample data (books, reviews, logs, jobs)')
    
    # Fill command
    subparsers.add_parser('fill', help='Fill dashboard with all event types (requires running server)')
    
    # Simulate command
    sim_parser = subparsers.add_parser('simulate', help='Simulate live activity')
    sim_parser.add_argument('-d', '--duration', type=int, default=60, help='Duration in seconds (default: 60)')
    sim_parser.add_argument('-i', '--interval', type=float, default=0.5, help='Interval between requests (default: 0.5)')
    
    # Clear command
    subparsers.add_parser('clear', help='Clear all Orbit entries')
    
    # Status command
    subparsers.add_parser('status', help='Show current entry counts')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        setup_demo()
    elif args.command == 'fill':
        fill_dashboard()
    elif args.command == 'simulate':
        simulate_activity(duration=args.duration, interval=args.interval)
    elif args.command == 'clear':
        clear_entries()
    elif args.command == 'status':
        show_status()
    else:
        parser.print_help()
        print("\n💡 Quick start:")
        print("   1. python demo.py setup        # Create sample data")
        print("   2. python manage.py runserver  # Start server")
        print("   3. python demo.py fill         # Fill all event types")
        print("   4. Open http://localhost:8000/orbit/\n")


if __name__ == "__main__":
    main()
