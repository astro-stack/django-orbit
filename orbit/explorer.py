"""Filter parsing and scoped queryset helpers for the Explorer feed."""

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Avg, BooleanField, Count, F, Func, Q

from orbit.models import OrbitEntry

FILTER_KEYS = (
    "type",
    "q",
    "tag",
    "family",
    "range",
    "path",
    "method",
    "status_class",
    "min_duration_ms",
)
METHODS = {
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "CONNECT",
    "TRACE",
}
RANGES = {"all": None, "15m": 15, "1h": 60, "24h": 1440}
STATUS_CLASSES = {
    "2xx": (200, 299),
    "3xx": (300, 399),
    "4xx": (400, 499),
    "5xx": (500, 599),
}
NEW_FILTER_KEYS = ("range", "path", "method", "status_class", "min_duration_ms")


class _JSONPathIsString(Func):
    """Boolean guard that requires a named top-level JSON value to be a string."""

    output_field = BooleanField()
    _allowed_keys = frozenset(("path", "request_path"))

    def __init__(self, expression, key):
        if key not in self._allowed_keys:
            raise ValueError("Unsupported JSON path key.")
        self.key = key
        super().__init__(expression, output_field=self.output_field)

    def as_sql(self, compiler, connection):
        expression_sql, expression_params = compiler.compile(self.source_expressions[0])
        if connection.vendor == "sqlite":
            return (
                "JSON_TYPE(%s, %%s) = 'text'" % expression_sql,
                expression_params + ["$." + self.key],
            )
        if connection.vendor == "postgresql":
            return (
                "jsonb_typeof(%s -> %%s) = 'string'" % expression_sql,
                expression_params + [self.key],
            )
        if connection.vendor == "mysql":
            return (
                "JSON_TYPE(JSON_EXTRACT(%s, %%s)) = 'STRING'" % expression_sql,
                expression_params + ["$." + self.key],
            )
        return "1=0", []


def _scalar(params, key, errors):
    values = params.getlist(key) if hasattr(params, "getlist") else [params[key]]
    if len(values) == 1 and isinstance(values[0], (list, tuple)):
        values = list(values[0])
    if key in NEW_FILTER_KEYS and len(values) != 1:
        errors[key] = "Provide exactly one value."
        return ""
    return values[-1]


@dataclass(frozen=True)
class ExplorerFilters:
    type: str = "all"
    q: str = ""
    tag: str = ""
    family: str = ""
    range: str = "all"
    path: str = ""
    method: str = ""
    status_class: str = ""
    min_duration_ms: str = ""

    @property
    def canonical(self):
        return {key: getattr(self, key) for key in FILTER_KEYS}

    @classmethod
    def parse(cls, params):
        errors = {}
        values = {
            key: _scalar(params, key, errors) for key in FILTER_KEYS if key in params
        }
        if errors:
            return None, errors
        data = {key: values.get(key, "") for key in FILTER_KEYS}
        data["type"] = values.get("type", "all")
        data["range"] = values.get("range", "all")
        valid_types = {key for key, _ in OrbitEntry.TYPE_CHOICES}
        if data["type"] not in valid_types and data["type"] != "all":
            data["type"] = "all"
        if data["range"] == "":
            data["range"] = "all"
        if data["range"] not in RANGES:
            errors.setdefault("range", "Choose a supported time range.")
        data["path"] = data["path"].strip()
        if len(data["path"]) > 512:
            errors.setdefault("path", "Path must be at most 512 characters.")
        method = data["method"].strip().upper()
        if method and method not in METHODS:
            errors.setdefault("method", "Choose a supported HTTP method.")
        data["method"] = method
        if data["status_class"] and data["status_class"] not in STATUS_CLASSES:
            errors.setdefault("status_class", "Choose a supported status class.")
        duration = data["min_duration_ms"]
        if duration:
            if len(duration) > 8 or not duration.isascii() or not duration.isdigit():
                errors.setdefault(
                    "min_duration_ms", "Enter a whole number from 0 to 86400000."
                )
            elif int(duration) > 86400000:
                errors.setdefault(
                    "min_duration_ms", "Enter a whole number from 0 to 86400000."
                )
            else:
                data["min_duration_ms"] = str(int(duration))
        if errors:
            return None, errors
        return cls(**data), {}


def _query_text(queryset, query):
    if not query:
        return queryset
    import uuid

    try:
        return queryset.filter(id=uuid.UUID(query))
    except ValueError:
        from django.db.models import TextField
        from django.db.models.functions import Cast

        return queryset.annotate(payload_text=Cast("payload", TextField())).filter(
            payload_text__icontains=query
        )


def scoped_entries(filters, now):
    queryset = OrbitEntry.objects.filter()
    if filters.type != "all":
        queryset = queryset.filter(type=filters.type)
    if filters.family:
        queryset = queryset.filter(family_hash=filters.family)
    tag = filters.tag
    query = filters.q
    if not tag and query.lower().startswith("tag:"):
        tag, query = query[4:].strip(), ""
    if tag:
        queryset = queryset.filter(tags__contains="," + tag + ",")
    queryset = _query_text(queryset, query)
    if filters.range != "all":
        start = now - timedelta(minutes=RANGES[filters.range])
        queryset = queryset.filter(created_at__gte=start, created_at__lte=now)
    if filters.path:
        request_path = (
            Q(type=OrbitEntry.TYPE_REQUEST)
            & Q(payload__path__icontains=filters.path)
            & Q(_JSONPathIsString(F("payload"), "path"))
        )
        exception_path = (
            Q(type=OrbitEntry.TYPE_EXCEPTION)
            & Q(payload__request_path__icontains=filters.path)
            & Q(_JSONPathIsString(F("payload"), "request_path"))
        )
        queryset = queryset.filter(request_path | exception_path)
    if filters.method:
        queryset = queryset.filter(
            Q(type=OrbitEntry.TYPE_REQUEST, payload__method=filters.method)
            | Q(type=OrbitEntry.TYPE_EXCEPTION, payload__request_method=filters.method)
        )
    if filters.status_class:
        low, high = STATUS_CLASSES[filters.status_class]
        queryset = queryset.filter(
            type=OrbitEntry.TYPE_REQUEST,
            payload__status_code__in=range(low, high + 1),
        )
    if filters.min_duration_ms:
        queryset = queryset.filter(duration_ms__gte=int(filters.min_duration_ms))
    return queryset


def calculate_metrics(queryset):
    failed = Q(type=OrbitEntry.TYPE_REQUEST, payload__status_code__in=range(400, 600))
    request = Q(type=OrbitEntry.TYPE_REQUEST)
    query = Q(type=OrbitEntry.TYPE_QUERY)
    values = queryset.aggregate(
        entry_count=Count("id"),
        request_count=Count("id", filter=request),
        query_count=Count("id", filter=query),
        avg_response_time=Avg("duration_ms", filter=request),
        failed_request_count=Count("id", filter=failed),
        exception_count=Count("id", filter=Q(type=OrbitEntry.TYPE_EXCEPTION)),
        slow_query_count=Count("id", filter=query & Q(payload__is_slow=True)),
        duplicate_query_count=Count("id", filter=query & Q(payload__is_duplicate=True)),
    )
    return {
        **values,
        "error_rate_pct": (
            values["failed_request_count"] * 100 / values["request_count"]
            if values["request_count"]
            else 0
        ),
    }


def exception_groups(queryset):
    from django.db.models import Count, Max, Min

    base = queryset.filter(type=OrbitEntry.TYPE_EXCEPTION).annotate(
        group_key=OrbitEntry.objects._exception_group_key()
    )
    aggregates = (
        base.values("group_key")
        .annotate(
            count=Count("id"), first_seen=Min("created_at"), last_seen=Max("created_at")
        )
        .order_by("-last_seen", "group_key")
    )
    return aggregates


def exception_group_page(queryset, page, per_page, total_count=None):
    aggregates = exception_groups(queryset)
    if total_count is None:
        total_count = aggregates.count()
    page_rows = list(aggregates[(page - 1) * per_page : page * per_page])
    scoped = queryset.filter(type=OrbitEntry.TYPE_EXCEPTION).annotate(
        group_key=OrbitEntry.objects._exception_group_key()
    )
    output = []
    for aggregate in page_rows:
        representative = (
            scoped.filter(group_key=aggregate["group_key"])
            .order_by("-created_at", "-id")
            .first()
        )
        if representative is not None:
            output.append({"entry": representative, **aggregate})
    return output, total_count
