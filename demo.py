#!/usr/bin/env python
"""
Django Orbit Demo Tool

Unified script for setting up and running demos.

Usage:
    python demo.py setup     - Create sample data (books, reviews, logs, jobs)
    python demo.py simulate  - Simulate live activity (requests to various endpoints)
    python demo.py clear     - Clear all Orbit entries
    python demo.py status    - Show current entry counts
"""

import os
import sys
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
    
    # Create sample jobs
    print("\n⏰ Creating sample job entries...")
    job_samples = [
        {'job_name': 'send_welcome_email', 'queue': 'email', 'status': 'completed'},
        {'job_name': 'process_payment', 'queue': 'payments', 'status': 'completed'},
        {'job_name': 'generate_report', 'queue': 'reports', 'status': 'failed', 'error': 'Timeout'},
        {'job_name': 'sync_inventory', 'queue': 'sync', 'status': 'completed'},
        {'job_name': 'send_newsletter', 'queue': 'email', 'status': 'processing'},
    ]
    for job in job_samples:
        OrbitEntry.objects.create(
            type='job',
            payload=job,
            duration_ms=random.uniform(100, 2000),
        )
        emoji = "✓" if job['status'] == 'completed' else ("⏳" if job['status'] == 'processing' else "✗")
        print(f"   {emoji} {job['job_name']} ({job['status']})")
    
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    print(f"\n   📚 Books: {Book.objects.count()}")
    print(f"   ⭐ Reviews: {Review.objects.count()}")
    print(f"   📝 Logs: {OrbitEntry.objects.logs().count()}")
    print(f"   ⏰ Jobs: {OrbitEntry.objects.jobs().count()}")
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
    
    print("\n" + "="*60)
    print("📊 Dashboard Filled!")
    print("="*60)
    print(f"\n   🌐 Requests: {OrbitEntry.objects.requests().count()}")
    print(f"   🗄️  Queries: {OrbitEntry.objects.queries().count()}")
    print(f"   📝 Logs: {OrbitEntry.objects.logs().count()}")
    print(f"   🚨 Exceptions: {OrbitEntry.objects.exceptions().count()}")
    print(f"   ⏰ Jobs: {OrbitEntry.objects.jobs().count()}")
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
