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
| `python demo.py setup` | Create sample data (books, reviews, logs, jobs) |
| `python demo.py simulate` | Simulate live traffic (60 seconds) |
| `python demo.py simulate -d 30` | Simulate for 30 seconds |
| `python demo.py clear` | Clear all Orbit entries |
| `python demo.py status` | Show current entry counts |

## Demo URLs

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | Demo home with test endpoints |
| http://localhost:8000/orbit/ | Orbit dashboard |

## Recording Tips

For promotional videos:

1. **Setup fresh data:**
   ```bash
   python demo.py setup
   ```

2. **Start server:**
   ```bash
   python manage.py runserver
   ```

3. **Open dashboard:** http://localhost:8000/orbit/

4. **In another terminal, simulate traffic:**
   ```bash
   python demo.py simulate
   ```

5. **Record** showing:
   - Live feed updating
   - Clicking entries for details
   - Filtering by type
   - Slow queries (amber)
   - Errors (rose)

## Test Endpoints

| Endpoint | What it generates |
|----------|-------------------|
| `/books/` | SQL queries |
| `/books/create/` | INSERT query + log |
| `/slow/` | Slow request (1s) |
| `/log/` | Log messages (all levels) |
| `/error/` | Exception with traceback |
| `/duplicate-queries/` | N+1 query problem |
| `POST /api/data/` | POST request with body |

## PowerShell Note

PowerShell's `curl` is an alias. Use:

```powershell
# Option 1: Invoke-RestMethod
Invoke-RestMethod "http://localhost:8000/books/"

# Option 2: curl.exe
curl.exe http://localhost:8000/books/
```
