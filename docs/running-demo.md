# Running the Demo

Everything for demos is in one file: **`demo.py`**

## Quick Start

### Option 1: One-Click Setup

**Windows:**
```batch
run_demo.bat
```

**macOS/Linux:**
```bash
chmod +x run_demo.sh
./run_demo.sh
```

### Option 2: Manual Setup

```bash
# 1. Create venv and install
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
pip install django requests
pip install -e .

# 2. Run migrations
python manage.py migrate --run-syncdb

# 3. Setup demo data
python demo.py setup

# 4. Start server
python manage.py runserver
```

## Demo Commands

| Command | Description |
|---------|-------------|
| `python demo.py setup` | Create a balanced corpus for every event family, including AI/LLM and query patterns |
| `python demo.py simulate` | Simulate live traffic (60 seconds) |
| `python demo.py simulate -d 30` | Simulate for 30 seconds |
| `python demo.py clear` | Clear all Orbit entries |
| `python demo.py status` | Show current entry counts |

## Demo URLs

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | Demo home with test endpoints |
| http://localhost:8000/orbit/ | Orbit dashboard |

## Test Endpoints

| Endpoint | What it generates |
|----------|-------------------|
| `/books/` | SQL queries |
| `/books/create/` | INSERT query + log |
| `/slow/` | Slow request (1s) |
| `/log/` | Log messages (all levels) |
| `/error/` | Exception with traceback |
| `/duplicate-queries/` | Backward-compatible alias for relational N+1 |
| `/query-patterns/n-plus-one/` | Relational N+1 with varying parameters |
| `/query-patterns/per-row-aggregate/` | One aggregate query per parent row |
| `/query-patterns/exact-duplicate/` | Exact SQL and parameter repetition, not N+1 |
| `POST /api/data/` | POST request with body |

The three query-pattern routes are deterministic. `setup` also inserts
representative request findings so Stats and the feed are populated before a
server is started. `fill` calls the live routes so Orbit's recorder and analyzer
produce the same classifications from actual SQL execution.

The setup corpus includes successful and failed AI/LLM events, multiple
providers, token usage and tool-call metadata. Prompt and response content
remain absent, matching Orbit's safe defaults.

## PowerShell Note

PowerShell's `curl` is an alias. Use:

```powershell
# Option 1: Invoke-RestMethod
Invoke-RestMethod "http://localhost:8000/books/"

# Option 2: curl.exe
curl.exe http://localhost:8000/books/
```
