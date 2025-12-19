"""
Django Orbit Stats Module

Data aggregation and calculation functions for the Stats Dashboard.
"""

from datetime import timedelta
from typing import Dict, List, Any, Optional
from django.db import models
from django.db.models import Avg, Count, Sum, Min, Max, F, Q
from django.db.models.functions import TruncHour, TruncMinute, TruncDay
from django.utils import timezone

from orbit.models import OrbitEntry


def get_time_range(range_key: str) -> tuple:
    """
    Get start/end times for a given time range.
    
    Args:
        range_key: One of '1h', '6h', '24h', '7d'
    
    Returns:
        Tuple of (start_time, end_time, bucket_function, bucket_minutes)
    """
    now = timezone.now()
    
    ranges = {
        '1h': (timedelta(hours=1), TruncMinute, 5),
        '6h': (timedelta(hours=6), TruncMinute, 30),
        '24h': (timedelta(hours=24), TruncHour, 60),
        '7d': (timedelta(days=7), TruncHour, 360),
    }
    
    delta, trunc_func, bucket_minutes = ranges.get(range_key, ranges['24h'])
    return (now - delta, now, trunc_func, bucket_minutes)


def calculate_apdex(threshold_ms: float = 500, time_range: str = '24h') -> float:
    """
    Calculate Apdex score for requests.
    
    Apdex = (Satisfied + Tolerated/2) / Total
    - Satisfied: response < threshold
    - Tolerated: threshold <= response < 4*threshold
    - Frustrated: response >= 4*threshold
    
    Returns:
        Apdex score between 0 and 1
    """
    start_time, end_time, _, _ = get_time_range(time_range)
    
    requests = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        created_at__gte=start_time,
        created_at__lte=end_time,
        duration_ms__isnull=False,
    )
    
    total = requests.count()
    if total == 0:
        return 1.0  # No data = perfect score
    
    satisfied = requests.filter(duration_ms__lt=threshold_ms).count()
    tolerated = requests.filter(
        duration_ms__gte=threshold_ms,
        duration_ms__lt=threshold_ms * 4
    ).count()
    
    return (satisfied + (tolerated / 2)) / total


def get_percentiles(time_range: str = '24h') -> Dict[str, float]:
    """
    Calculate response time percentiles.
    
    Returns:
        Dict with p50, p75, p95, p99 values in ms
    """
    start_time, end_time, _, _ = get_time_range(time_range)
    
    durations = list(OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        created_at__gte=start_time,
        created_at__lte=end_time,
        duration_ms__isnull=False,
    ).values_list('duration_ms', flat=True).order_by('duration_ms'))
    
    if not durations:
        return {'p50': 0, 'p75': 0, 'p95': 0, 'p99': 0}
    
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f)
    
    return {
        'p50': round(percentile(durations, 50), 2),
        'p75': round(percentile(durations, 75), 2),
        'p95': round(percentile(durations, 95), 2),
        'p99': round(percentile(durations, 99), 2),
    }


def get_throughput_data(time_range: str = '24h') -> List[Dict]:
    """
    Get request throughput over time, broken down by status code category.
    
    Returns:
        List of dicts with timestamp, success_count, client_error_count, server_error_count
    """
    start_time, end_time, trunc_func, _ = get_time_range(time_range)
    
    entries = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        created_at__gte=start_time,
        created_at__lte=end_time,
    ).annotate(
        bucket=trunc_func('created_at')
    ).values('bucket').annotate(
        total=Count('id')
    ).order_by('bucket')
    
    return [
        {
            'timestamp': e['bucket'].isoformat() if e['bucket'] else None,
            'count': e['total'],
        }
        for e in entries
    ]


def get_response_time_trend(time_range: str = '24h') -> List[Dict]:
    """
    Get response time trend over time with percentiles.
    
    Returns:
        List of dicts with timestamp, avg, p50, p95
    """
    start_time, end_time, trunc_func, _ = get_time_range(time_range)
    
    entries = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        created_at__gte=start_time,
        created_at__lte=end_time,
        duration_ms__isnull=False,
    ).annotate(
        bucket=trunc_func('created_at')
    ).values('bucket').annotate(
        avg=Avg('duration_ms'),
        count=Count('id'),
    ).order_by('bucket')
    
    return [
        {
            'timestamp': e['bucket'].isoformat() if e['bucket'] else None,
            'avg': round(e['avg'], 2) if e['avg'] else 0,
            'count': e['count'],
        }
        for e in entries
    ]


def get_error_rate_trend(time_range: str = '24h') -> List[Dict]:
    """
    Get error rate trend over time.
    
    Returns:
        List of dicts with timestamp, error_rate (percentage)
    """
    start_time, end_time, trunc_func, _ = get_time_range(time_range)
    
    # Get all requests bucketed by time
    request_buckets = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        created_at__gte=start_time,
        created_at__lte=end_time,
    ).annotate(
        bucket=trunc_func('created_at')
    ).values('bucket').annotate(
        total=Count('id'),
    )
    
    # Get exceptions bucketed by time
    exception_buckets = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_EXCEPTION,
        created_at__gte=start_time,
        created_at__lte=end_time,
    ).annotate(
        bucket=trunc_func('created_at')
    ).values('bucket').annotate(
        errors=Count('id'),
    )
    
    # Merge data
    request_data = {e['bucket']: e['total'] for e in request_buckets}
    exception_data = {e['bucket']: e['errors'] for e in exception_buckets}
    
    all_buckets = sorted(set(request_data.keys()) | set(exception_data.keys()))
    
    return [
        {
            'timestamp': bucket.isoformat() if bucket else None,
            'total': request_data.get(bucket, 0),
            'errors': exception_data.get(bucket, 0),
            'rate': round(
                (exception_data.get(bucket, 0) / request_data.get(bucket, 1)) * 100, 2
            ) if request_data.get(bucket, 0) > 0 else 0,
        }
        for bucket in all_buckets
    ]


def get_database_metrics(time_range: str = '24h') -> Dict[str, Any]:
    """
    Get database/query analytics.
    
    Returns:
        Dict with query stats, slow queries, duplicates, etc.
    """
    start_time, end_time, _, _ = get_time_range(time_range)
    
    queries = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_QUERY,
        created_at__gte=start_time,
        created_at__lte=end_time,
    )
    
    total = queries.count()
    
    # Get aggregate stats
    stats = queries.aggregate(
        avg_time=Avg('duration_ms'),
        max_time=Max('duration_ms'),
        total_time=Sum('duration_ms'),
    )
    
    # Slow queries (>100ms)
    slow_count = queries.filter(payload__is_slow=True).count()
    slow_pct = (slow_count / total * 100) if total > 0 else 0
    
    # Duplicate queries
    duplicate_count = queries.filter(payload__is_duplicate=True).count()
    
    # Top slow queries
    slow_queries = queries.filter(payload__is_slow=True).order_by('-duration_ms')[:10]
    
    return {
        'total_queries': total,
        'avg_time': round(stats['avg_time'] or 0, 2),
        'max_time': round(stats['max_time'] or 0, 2),
        'total_time': round(stats['total_time'] or 0, 2),
        'slow_count': slow_count,
        'slow_pct': round(slow_pct, 1),
        'duplicate_count': duplicate_count,
        'top_slow': [
            {
                'id': str(q.id),
                'sql': q.payload.get('sql', '')[:100] + '...' if len(q.payload.get('sql', '')) > 100 else q.payload.get('sql', ''),
                'duration_ms': q.duration_ms,
                'timestamp': q.created_at.isoformat(),
            }
            for q in slow_queries
        ],
    }


def get_cache_metrics(time_range: str = '24h') -> Dict[str, Any]:
    """
    Get cache analytics.
    
    Returns:
        Dict with hit rate, hits/misses counts, trend data
    """
    start_time, end_time, trunc_func, _ = get_time_range(time_range)
    
    cache_ops = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_CACHE,
        created_at__gte=start_time,
        created_at__lte=end_time,
    )
    
    hits = cache_ops.filter(payload__hit=True).count()
    misses = cache_ops.filter(payload__hit=False).count()
    total = hits + misses
    
    hit_rate = (hits / total * 100) if total > 0 else 0
    
    # Trend data
    trend_data = []
    for t in cache_ops.annotate(
        bucket=trunc_func('created_at')
    ).values('bucket').annotate(
        total=Count('id'),
    ).order_by('bucket'):
        bucket_hits = cache_ops.filter(
            created_at__gte=t['bucket'],
            payload__hit=True
        ).count()
        trend_data.append({
            'timestamp': t['bucket'].isoformat() if t['bucket'] else None,
            'total': t['total'],
            'hit_rate': round((bucket_hits / t['total'] * 100), 1) if t['total'] > 0 else 0,
        })
    
    return {
        'hits': hits,
        'misses': misses,
        'total': total,
        'hit_rate': round(hit_rate, 1),
        'trend': trend_data,
    }


def get_jobs_metrics(time_range: str = '24h') -> Dict[str, Any]:
    """
    Get background jobs analytics.
    
    Returns:
        Dict with success rate, failed jobs, duration stats
    """
    start_time, end_time, _, _ = get_time_range(time_range)
    
    jobs = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_JOB,
        created_at__gte=start_time,
        created_at__lte=end_time,
    )
    
    total = jobs.count()
    success = jobs.filter(payload__status='success').count()
    failed = jobs.filter(payload__status='failed').count()
    
    success_rate = (success / total * 100) if total > 0 else 100
    
    # Average duration
    stats = jobs.aggregate(avg_duration=Avg('duration_ms'))
    
    # Failed jobs list
    failed_jobs = jobs.filter(payload__status='failed').order_by('-created_at')[:10]
    
    return {
        'total': total,
        'success': success,
        'failed': failed,
        'success_rate': round(success_rate, 1),
        'avg_duration': round(stats['avg_duration'] or 0, 2),
        'failed_jobs': [
            {
                'id': str(j.id),
                'name': j.payload.get('name', 'Unknown'),
                'error': j.payload.get('error', '')[:100],
                'timestamp': j.created_at.isoformat(),
            }
            for j in failed_jobs
        ],
    }


def get_security_metrics(time_range: str = '24h') -> Dict[str, Any]:
    """
    Get security/permission analytics.
    
    Returns:
        Dict with granted/denied counts, top denied permissions
    """
    start_time, end_time, _, _ = get_time_range(time_range)
    
    gates = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_GATE,
        created_at__gte=start_time,
        created_at__lte=end_time,
    )
    
    granted = gates.filter(payload__result='granted').count()
    denied = gates.filter(payload__result='denied').count()
    total = granted + denied
    
    # Top denied permissions
    denied_entries = gates.filter(payload__result='denied').values('payload')[:50]
    
    permission_counts = {}
    for entry in denied_entries:
        perm = entry['payload'].get('permission', 'unknown')
        permission_counts[perm] = permission_counts.get(perm, 0) + 1
    
    top_denied = sorted(permission_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'total': total,
        'granted': granted,
        'denied': denied,
        'denial_rate': round((denied / total * 100), 1) if total > 0 else 0,
        'top_denied': [
            {'permission': perm, 'count': count}
            for perm, count in top_denied
        ],
    }


def get_summary_stats(time_range: str = '24h') -> Dict[str, Any]:
    """
    Get overall summary statistics for the health overview.
    
    Returns:
        Dict with apdex, avg_response_time, error_rate, throughput
    """
    start_time, end_time, _, _ = get_time_range(time_range)
    
    # Calculate time delta in minutes
    delta_minutes = (end_time - start_time).total_seconds() / 60
    
    requests = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_REQUEST,
        created_at__gte=start_time,
        created_at__lte=end_time,
    )
    
    exceptions = OrbitEntry.objects.filter(
        type=OrbitEntry.TYPE_EXCEPTION,
        created_at__gte=start_time,
        created_at__lte=end_time,
    )
    
    request_count = requests.count()
    exception_count = exceptions.count()
    
    stats = requests.aggregate(avg_time=Avg('duration_ms'))
    
    # Calculate throughput with appropriate unit
    delta_hours = (end_time - start_time).total_seconds() / 3600
    if time_range == '1h':
        throughput = round(request_count / (delta_minutes or 1), 1)
        throughput_unit = '/min'
    else:
        throughput = round(request_count / (delta_hours or 1), 1)
        throughput_unit = '/hr'
    
    return {
        'apdex': round(calculate_apdex(time_range=time_range), 2),
        'avg_response_time': round(stats['avg_time'] or 0, 1),
        'error_count': exception_count,
        'error_rate': round((exception_count / request_count * 100), 2) if request_count > 0 else 0,
        'throughput': throughput,
        'throughput_unit': throughput_unit,
        'total_requests': request_count,
        'percentiles': get_percentiles(time_range),
    }
