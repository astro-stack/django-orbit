/*
 * Stats page: shared ApexCharts defaults, the statsPage() Alpine component and
 * the lazy-section chart initialisers.
 *
 * Stats sections are fetched by htmx and swapped in; chart data arrives in
 * json_script blocks inside each section and is rendered on htmx:afterSwap.
 */
// Shared ApexCharts defaults for lazily-loaded chart sections (see DESIGN.md).
window.ORBIT_CHART_DEFAULTS = {
    chart: { background: 'transparent', toolbar: { show: false }, zoom: { enabled: false }, fontFamily: 'inherit' },
    theme: { mode: 'dark' },
    grid: { borderColor: 'rgba(255,255,255,0.05)', strokeDashArray: 4 },
    tooltip: { theme: 'dark', style: { fontSize: '12px' } },
};

// Alpine.js component for the stats page
function statsPage() {
    return {
        detailOpen: false,
        detailLoading: false,

        async openDetail(entryId) {
            this.detailLoading = true;
            this.detailOpen = true;
            const root = document.getElementById('orbit-stats-config');
            const base = root.dataset.detailUrlTemplate;
            try {
                const response = await fetch(base.replace('00000000-0000-0000-0000-000000000000', entryId));
                const content = document.getElementById('stats-detail-content');
                content.innerHTML = await response.text();
                if (typeof lucide !== 'undefined') lucide.createIcons();
                if (typeof orbitInitDetail === 'function') orbitInitDetail(content);
            } catch (error) {
                document.getElementById('stats-detail-content').innerHTML =
                    `<div class="p-4 bg-rose-500/10 rounded-lg text-rose-400">Error loading entry details: ${error.message}</div>`;
            } finally {
                this.detailLoading = false;
            }
        }
    };
}

// ---------------------------------------------------------------------------
// Lazy stats sections (htmx swaps them in; see partials/stats_*.html)
// ---------------------------------------------------------------------------

function orbitReadJson(id, fallback) {
    const el = document.getElementById(id);
    if (!el) return fallback;
    try {
        return JSON.parse(el.textContent);
    } catch (error) {
        return fallback;
    }
}

function orbitChartEmpty(selector, message, sizeClass) {
    const el = document.querySelector(selector);
    if (el) el.innerHTML = '<div class="flex items-center justify-center h-full text-orbit-text-muted ' + sizeClass + '">' + message + '</div>';
}

function orbitInitTrendCharts() {
    if (typeof ApexCharts === 'undefined' || !document.getElementById('response-time-chart')) return;
    const D = window.ORBIT_CHART_DEFAULTS || {};

    const responseTimeData = orbitReadJson('orbit-response-time-data', []);
    if (responseTimeData && responseTimeData.length) {
        new ApexCharts(document.querySelector('#response-time-chart'), {
            ...D,
            chart: { ...D.chart, type: 'area', height: 256 },
            series: [{ name: 'Avg Response Time', data: responseTimeData.map(d => ({ x: new Date(d.timestamp), y: d.avg })) }],
            stroke: { curve: 'smooth', width: 2 },
            fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05 } },
            colors: ['#22d3ee'],
            markers: { size: responseTimeData.length < 5 ? 5 : 0, colors: ['#22d3ee'], strokeWidth: 0, hover: { size: 7 } },
            xaxis: { type: 'datetime', labels: { style: { colors: '#64748b' } } },
            yaxis: { labels: { style: { colors: '#64748b' }, formatter: v => v ? v.toFixed(0) + 'ms' : '0ms' } },
        }).render();
    } else { orbitChartEmpty('#response-time-chart', 'No data for this time range', 'text-sm'); }

    const throughputData = orbitReadJson('orbit-throughput-data', []);
    if (throughputData && throughputData.length) {
        new ApexCharts(document.querySelector('#throughput-chart'), {
            ...D,
            chart: { ...D.chart, type: 'bar', height: 256 },
            series: [{ name: 'Requests', data: throughputData.map(d => ({ x: new Date(d.timestamp), y: d.count })) }],
            colors: ['#a78bfa'],
            plotOptions: { bar: { borderRadius: 4, columnWidth: '60%' } },
            xaxis: { type: 'datetime', labels: { style: { colors: '#64748b' } } },
            yaxis: { labels: { style: { colors: '#64748b' } } },
        }).render();
    } else { orbitChartEmpty('#throughput-chart', 'No data for this time range', 'text-sm'); }

    const errorData = orbitReadJson('orbit-error-trend-data', []);
    if (errorData && errorData.length) {
        new ApexCharts(document.querySelector('#error-rate-chart'), {
            ...D,
            chart: { ...D.chart, type: 'line', height: 192 },
            series: [{ name: 'Error Rate', data: errorData.map(d => ({ x: new Date(d.timestamp), y: d.rate })) }],
            stroke: { curve: 'straight', width: 2 },
            colors: ['#fb7185'],
            xaxis: { type: 'datetime', labels: { style: { colors: '#64748b' } } },
            yaxis: { labels: { style: { colors: '#64748b' }, formatter: v => v.toFixed(1) + '%' }, min: 0 },
            annotations: { yaxis: [{ y: 5, borderColor: '#fb7185', strokeDashArray: 4, label: { text: 'Threshold' } }] },
        }).render();
    } else { orbitChartEmpty('#error-rate-chart', 'No error data for this time range', 'text-sm'); }
}

function orbitInitCacheChart() {
    if (typeof ApexCharts === 'undefined' || !document.getElementById('cache-chart')) return;
    const D = window.ORBIT_CHART_DEFAULTS || {};
    const cacheData = orbitReadJson('orbit-cache-trend-data', []);
    if (cacheData && cacheData.length) {
        new ApexCharts(document.querySelector('#cache-chart'), {
            ...D,
            chart: { ...D.chart, type: 'area', height: 128, sparkline: { enabled: true } },
            series: [{ name: 'Hit Rate', data: cacheData.map(d => d.hit_rate) }],
            stroke: { curve: 'smooth', width: 2 },
            fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05 } },
            colors: ['#34d399'],
            tooltip: { fixed: { enabled: false }, y: { formatter: v => v + '%' } },
        }).render();
    } else {
        orbitChartEmpty('#cache-chart', 'No cache data', 'text-xs');
    }
}

// Render each lazily loaded section's charts once its HTML is in the DOM.
document.body.addEventListener('htmx:afterSwap', function (event) {
    const section = event.target;
    if (!section || !section.querySelector) return;
    if (section.querySelector('#response-time-chart')) orbitInitTrendCharts();
    if (section.querySelector('#cache-chart')) orbitInitCacheChart();
});
