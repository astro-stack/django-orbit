# Stats Dashboard

The Stats Dashboard provides advanced analytics and visualizations for your application's performance. Access it at `/orbit/stats/` or via the **Stats** button in the main dashboard.

## Overview

The Stats Dashboard offers:

- **Real-time metrics** with interactive charts
- **Multiple time ranges** (1h, 6h, 24h, 7d)
- **Apdex scoring** for user satisfaction
- **Response time percentiles** (P50, P75, P95, P99)
- **Error rate tracking**
- **Database performance analytics**
- **Cache hit rate monitoring**
- **Background job metrics**
- **Permission check analytics**

## Time Range Selection

Use the time range buttons in the header to filter data:

| Range | Description |
|-------|-------------|
| **1h** | Last hour |
| **6h** | Last 6 hours |
| **24h** | Last 24 hours (default) |
| **7d** | Last 7 days |

## Health Overview

### Apdex Score

The [Apdex](https://en.wikipedia.org/wiki/Apdex) (Application Performance Index) score indicates user satisfaction:

| Score | Rating | Color |
|-------|--------|-------|
| 0.94 - 1.00 | Excellent | Green |
| 0.85 - 0.93 | Good | Green |
| 0.70 - 0.84 | Fair | Yellow |
| 0.50 - 0.69 | Poor | Orange |
| 0.00 - 0.49 | Unacceptable | Red |

**Calculation**: Based on response times where T=500ms threshold:
- Satisfied: response ≤ T
- Tolerating: T < response ≤ 4T
- Frustrated: response > 4T

### Key Metrics

| Metric | Description |
|--------|-------------|
| **Avg Response Time** | Average request duration |
| **Error Rate** | Percentage of failed requests |
| **Throughput** | Requests per minute (1h) or per hour (other ranges) |

### Response Time Percentiles

| Percentile | Description |
|------------|-------------|
| **P50** | Median - 50% of requests faster |
| **P75** | 75% of requests faster |
| **P95** | 95% of requests faster |
| **P99** | 99% of requests faster |

## Charts

### Response Time Trend

Area chart showing response time over the selected period. Markers appear for data points when data is sparse.

### Request Throughput

Bar chart showing request volume over time, helping identify traffic patterns.

### Error Rate Trend

Line chart with a threshold marker at 5% to highlight concerning error rates.

### Cache Hit Rate

Sparkline showing cache efficiency over time.

## Database Performance

| Metric | Description |
|--------|-------------|
| **Total Queries** | Number of SQL queries executed |
| **Total Duration** | Cumulative query time |
| **Slow Queries** | Queries exceeding threshold (500ms default) |
| **Duplicate (N+1)** | Repeated identical queries |

### Top Slow Queries

Lists the slowest queries with:

- Duration in milliseconds
- Timestamp
- SQL preview

**Click any slow query** to open its full details and see related duplicate queries.

## Cache Performance

| Metric | Description |
|--------|-------------|
| **Hits** | Successful cache reads |
| **Misses** | Cache misses requiring DB fetch |
| **Hit Rate** | Percentage of successful cache hits |

A sparkline chart shows hit rate trend over time.

## Background Jobs

| Metric | Description |
|--------|-------------|
| **Total Jobs** | Number of job executions |
| **Success Rate** | Percentage of successful jobs |
| **Avg Duration** | Average job execution time |

### Recent Failures

Lists failed jobs with:

- Job name
- Error message
- Timestamp

**Click any failed job** to view full stack trace and details.

Orbit supports:

- **Celery**
- **Django-Q**
- **RQ (Redis Queue)**
- **APScheduler**
- **django-celery-beat**

## Permission Checks

| Metric | Description |
|--------|-------------|
| **Total Checks** | Number of permission checks |
| **Granted** | Permissions allowed |
| **Denied** | Permissions denied |

### Top Denied Permissions

Lists the most frequently denied permissions to help identify authorization issues.

## Transaction Monitoring (v0.6.0)

| Metric | Description |
|--------|-------------|
| **Total Transactions** | Number of `atomic()` blocks executed |
| **Committed** | Successfully completed transactions |
| **Rolled Back** | Transactions that were rolled back |
| **Commit Rate** | Percentage of successful commits |
| **Avg Duration** | Average transaction duration |

### Recent Rollbacks

Lists recent failed transactions with:

- Exception that caused the rollback
- Database alias (default, replica, etc.)
- Duration in milliseconds
- Timestamp

**Click any rollback** to view full details and related queries.

## Storage Operations (v0.6.0)

| Metric | Description |
|--------|-------------|
| **Total Operations** | Number of file operations |
| **Saves** | Files uploaded/saved |
| **Opens** | Files read/opened |
| **Deletes** | Files deleted |
| **Exists Checks** | Existence checks |
| **Avg Duration** | Average operation duration |

### Top Storage Backends

Lists the most used storage backends (FileSystemStorage, S3Boto3Storage, etc.).

## Interactive Features

### Clickable Entries

Slow queries and failed jobs are clickable. When clicked, a slide-over panel shows the full entry details without leaving the Stats Dashboard.

### Data Export

Use the main dashboard's export feature to download raw data for external analysis.

## Configuration

The Stats Dashboard uses data from these watchers:

```python
ORBIT_CONFIG = {
    'RECORD_REQUESTS': True,    # For response time, throughput
    'RECORD_QUERIES': True,     # For database metrics
    'RECORD_EXCEPTIONS': True,  # For error rate
    'RECORD_CACHE': True,       # For cache metrics
    'RECORD_JOBS': True,        # For job metrics
    'RECORD_GATES': True,       # For permission metrics
    'RECORD_TRANSACTIONS': True, # For transaction metrics (v0.6.0)
    'RECORD_STORAGE': True,     # For storage metrics (v0.6.0)
}
```

## Next Steps

- [Dashboard Guide](dashboard.md)
- [Configuration](configuration.md)
- [Troubleshooting](troubleshooting.md)
