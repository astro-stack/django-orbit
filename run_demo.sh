#!/bin/bash
# Django Orbit - Quick Demo Setup (macOS/Linux)
#
# This script sets up everything needed for a demo:
# 1. Creates virtual environment
# 2. Installs dependencies
# 3. Runs migrations
# 4. Creates sample data
# 5. Starts the server

echo ""
echo "================================================"
echo "  Django Orbit - Demo Setup"
echo "================================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
echo "Installing dependencies..."
source venv/bin/activate
pip install django requests -q
pip install -e . -q

# Migrations
echo "Running migrations..."
python manage.py migrate --run-syncdb -v 0

# Setup demo data
echo "Creating demo data..."
python demo.py setup

echo ""
echo "================================================"
echo "  Ready! Starting server..."
echo "================================================"
echo ""
echo "  Demo:  http://localhost:8000/"
echo "  Orbit: http://localhost:8000/orbit/"
echo ""
echo "  To simulate activity (in another terminal):"
echo "  python demo.py simulate"
echo ""
echo "================================================"
echo ""

python manage.py runserver
