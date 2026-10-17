const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const template = readFileSync(path.resolve(__dirname, '../../orbit/templates/orbit/dashboard.html'), 'utf8');
const script = [...template.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
    .map((match) => match[1]).find((source) => source.includes('function orbitDashboard('));

function deferred() {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
}

function fragment({ feed = '<article data-entry-id="row-1">row</article>', metrics = '<b>3</b>', state } = {}) {
    const explorerState = state || {
        filters: { type: 'all', q: '', tag: '', family: '', range: 'all', path: '', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 1, total_entries: 1, grouped: false,
        window: { start: null, end: null },
    };
    return `<div data-orbit-feed>${feed}</div><template data-orbit-metrics>${metrics}</template><script id="orbit-explorer-state" type="application/json">${JSON.stringify(explorerState)}</script>`;
}

function harness(search = '') {
    const listeners = new Map();
    const feed = { id: 'feed-container', innerHTML: '', scrollTop: 35 };
    const metrics = { id: 'orbit-metrics-container', innerHTML: '' };
    const detail = { id: 'detail-container', innerHTML: '' };
    const calls = [];
    const timers = [];
    const errors = [];
    const addEventListener = (type, fn) => listeners.set(type, [...(listeners.get(type) || []), fn]);
    const historyCalls = [];
    const location = { search, pathname: '/orbit/', hash: '#feed', origin: 'https://example.test' };
    class DetachedParser {
        parseFromString(html) {
            const feedMatch = html.match(/<div data-orbit-feed>([\s\S]*)<\/div><template data-orbit-metrics>/);
            const metricsMatch = html.match(/<template data-orbit-metrics>([\s\S]*?)<\/template>/);
            const stateMatch = html.match(/<script id="orbit-explorer-state" type="application\/json">([\s\S]*?)<\/script>/);
            const feedRoot = feedMatch && { innerHTML: feedMatch[1], querySelector: () => null };
            const metricsTemplate = metricsMatch && { innerHTML: metricsMatch[1], content: { querySelector: () => null } };
            return {
                querySelector(selector) {
                    if (selector === '[data-orbit-feed]') return feedRoot;
                    if (selector === 'template[data-orbit-metrics]') return metricsTemplate;
                    return null;
                },
                querySelectorAll(selector) {
                    if (selector === '[data-orbit-feed]') return feedRoot ? [feedRoot] : [];
                    if (selector === 'template[data-orbit-metrics]') return metricsTemplate ? [metricsTemplate] : [];
                    if (selector === 'script#orbit-explorer-state[type="application/json"]') return stateMatch ? [{}] : [];
                    return [];
                },
                getElementById(id) { return id === 'orbit-explorer-state' && stateMatch ? { textContent: stateMatch[1], type: 'application/json' } : null; },
            };
        }
    }
    const context = vm.createContext({
        URL, URLSearchParams,
        DOMParser: DetachedParser,
        URLS: { feed: '/orbit/feed/', detail: '/orbit/entry/' },
        window: {
            location,
            htmx: {},
            history: {
                pushState(_state, _title, url) { historyCalls.push(['push', url]); location.search = new URL(url, location.origin).search; },
                replaceState(_state, _title, url) { historyCalls.push(['replace', url]); location.search = new URL(url, location.origin).search; },
            },
            addEventListener,
        },
        document: {
            body: { addEventListener }, addEventListener,
            getElementById: (id) => ({ 'feed-container': feed, 'detail-container': detail, 'orbit-metrics-container': metrics }[id] || null),
            querySelectorAll: () => [], querySelector: () => null,
        },
        fetch(url) {
            const result = deferred();
            calls.push({ url, ...result });
            return result.promise;
        },
        htmx: { process() {} }, lucide: { createIcons() {} },
        localStorage: { getItem: () => '1', setItem() {} },
        setInterval(fn) { timers.push(fn); return timers.length; }, clearInterval() {},
        setTimeout(fn) { fn(); }, console: { error(error) { errors.push(error); } },
    });
    vm.runInContext(script.replace('{{ current_type }}', 'all').replace('{{ orbit_urls.feed }}', '/orbit/feed/').replace('{{ orbit_urls.detail_base }}', '/orbit/entry/').replace('{{ orbit_urls.clear }}', '/orbit/clear/'), context);
    const state = context.orbitDashboard();
    state.$nextTick = (fn) => fn();
    const emit = (type, event) => (listeners.get(type) || []).forEach((fn) => fn(event));
    return { state, feed, metrics, detail, calls, timers, listeners, emit, historyCalls, location, errors };
}

const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
test('outside click on another feed row preserves the pending detail selection', async () => {
    const h = harness();
    h.state.detailOpen = true;
    h.state.detailEntryId = 'first';
    const pending = h.state.openDetail('second');
    h.state.handleDetailOutside({ target: { closest: (selector) => selector === '#feed-container [data-entry-id]' ? {} : null } });
    await tick();
    assert.equal(h.state.detailOpen, true);
    assert.equal(h.state.detailEntryId, 'second');
    reply(h.calls[0], '<article>Second detail</article>');
    await pending;
    assert.match(h.detail.innerHTML, /Second detail/);
    h.state.handleDetailOutside({ target: { closest: () => null } });
    assert.equal(h.state.detailOpen, false);
});

test('clicking the selected row still toggles the detail closed', async () => {
    const h = harness();
    h.state.detailOpen = true;
    h.state.detailEntryId = 'first';
    await h.state.openDetail('first');
    assert.equal(h.state.detailOpen, false);
    assert.equal(h.calls.length, 0);
});

test('template wires outside handling and either listener order preserves row selection', async () => {
    assert.match(template, /@click\.away="handleDetailOutside\(\$event\)"/);
    for (const outsideFirst of [true, false]) {
        const h = harness();
        h.state.init();
        h.state.detailOpen = true;
        h.state.detailEntryId = 'first';
        const row = { dataset: { entryId: 'second' } };
        const event = { target: { closest: () => row } };
        if (outsideFirst) h.state.handleDetailOutside(event);
        h.emit('click', event);
        if (!outsideFirst) h.state.handleDetailOutside(event);
        reply(h.calls[1], 'second detail');
        await tick();
        assert.equal(h.state.detailEntryId, 'second');
        assert.equal(h.state.detailOpen, true);
        assert.equal(h.detail.innerHTML, 'second detail');
    }
});

const reply = (call, html, status = 200, jsonPayload = null) => {
    if (status < 400 && new URL(call.url, 'https://example.test').pathname === '/orbit/feed/' && !html.includes('data-orbit-feed')) {
        const params = new URL(call.url, 'https://example.test').searchParams;
        const rangeMinutes = { '15m': 15, '1h': 60, '24h': 1440 };
        const range = params.get('range') || 'all';
        const windowEnd = Date.UTC(2026, 9, 16, 13);
        const state = {
            filters: { type: params.get('type') || 'all', q: params.get('q') || '', tag: params.get('tag') || '', family: params.get('family') || '', range, path: params.get('path') || '', method: params.get('method') || '', status_class: params.get('status_class') || '', min_duration_ms: params.get('min_duration_ms') || '' },
            page: Number(params.get('page') || 1), per_page: Number(params.get('per_page') || 25), total_count: Math.max(1, Number(params.get('page') || 1) * Number(params.get('per_page') || 25)), total_entries: Math.max(1, Number(params.get('page') || 1) * Number(params.get('per_page') || 25)), grouped: false,
            window: range === 'all' ? { start: null, end: null } : { start: new Date(windowEnd - rangeMinutes[range] * 60000).toISOString(), end: new Date(windowEnd).toISOString() },
        };
        html = fragment({ feed: html, state });
    }
    call.resolve({ ok: status < 400, status, text: async () => html, json: async () => jsonPayload || JSON.parse(html) });
};

test('URL initializes query, family, tag, page and per_page for polling and search', async () => {
    const h = harness('?type=query&q=slow+SQL&family=f-1&tag=urgent&page=4&per_page=50');
    h.state.init();
    assert.equal(h.state.searchQuery, 'slow SQL');
    assert.equal(h.state.currentPage, 4);
    for (const key of ['q', 'family', 'tag', 'page', 'per_page', 'type']) {
        const expected = new URLSearchParams('?type=query&q=slow+SQL&family=f-1&tag=urgent&page=4&per_page=50');
        assert.equal(new URL(h.calls[0].url, 'https://example.test').searchParams.get(key), expected.get(key));
    }
    h.state.searchQuery = 'changed';
    h.state.search();
    h.timers[0]();
    for (const call of h.calls.slice(1)) {
        const params = new URL(call.url, 'https://example.test').searchParams;
        assert.equal(params.get('family'), 'f-1');
        assert.equal(params.get('tag'), 'urgent');
        assert.equal(params.get('q'), 'changed');
        assert.equal(params.get('page'), '1');
    }
});

test('a successful response commits feed, metrics, applied scope, and canonical URL together', async () => {
    const h = harness();
    h.state.init();
    const html = fragment({ metrics: '<b>9</b>', state: {
        filters: { type: 'request', q: 'needle', tag: '', family: '', range: '24h', path: '/checkout', method: 'POST', status_class: '5xx', min_duration_ms: '12' },
        page: 3, per_page: 50, total_count: 108, total_entries: 109, grouped: false,
        window: { start: '2026-10-15T13:00:00Z', end: '2026-10-16T13:00:00Z' },
    } });
    reply(h.calls[0], html);
    await tick();
    assert.match(h.feed.innerHTML, /row-1/);
    assert.equal(h.metrics.innerHTML, '<b>9</b>');
    assert.equal(h.state.appliedFilters.range, '24h');
    assert.equal(h.state.currentPage, 3);
    assert.deepEqual(h.historyCalls.map((call) => call[0]), ['replace']);
    assert.match(h.historyCalls[0][1], /range=24h/);
});

test('invalid composite response preserves the last good feed and metrics', async () => {
    const h = harness();
    h.feed.innerHTML = 'last good feed';
    h.metrics.innerHTML = 'last good metrics';
    const pending = h.state.refreshFeed();
    reply(h.calls[0], '<div data-orbit-feed>untrusted</div>');
    await pending;
    assert.equal(h.feed.innerHTML, 'last good feed');
    assert.equal(h.metrics.innerHTML, 'last good metrics');
    assert.match(h.state.feedError, /refresh|load/i);
});

test('draft edits do not change applied polling scope until Apply', async () => {
    const h = harness('?range=1h&path=%2Fapi');
    h.state.init();
    reply(h.calls[0], fragment({ state: {
        filters: { type: 'all', q: '', tag: '', family: '', range: '1h', path: '/api', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 0, total_entries: 0, grouped: false, window: { start: '2026-10-16T12:00:00Z', end: '2026-10-16T13:00:00Z' },
    } }));
    await tick();
    h.state.draftFilters.path = '/checkout';
    h.timers[0]();
    assert.equal(new URL(h.calls[1].url, 'https://example.test').searchParams.get('path'), '/api');
    h.state.applyFilters();
    assert.equal(new URL(h.calls[2].url, 'https://example.test').searchParams.get('path'), '/checkout');
});

test('a completed poll never hydrates over a draft edited before the poll began', async () => {
    const h = harness('?range=1h&path=%2Fapi');
    h.state.init();
    reply(h.calls[0], fragment({ state: {
        filters: { type: 'all', q: '', tag: '', family: '', range: '1h', path: '/api', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 1, total_entries: 1, grouped: false, window: { start: '2026-10-16T12:00:00Z', end: '2026-10-16T13:00:00Z' },
    } }));
    await tick();
    h.state.draftFilters.path = '/draft';
    h.state.draftVersion++;
    h.timers[0]();
    reply(h.calls[1], fragment({ state: {
        filters: { type: 'all', q: '', tag: '', family: '', range: '1h', path: '/api', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 1, total_entries: 1, grouped: false, window: { start: '2026-10-16T12:00:00Z', end: '2026-10-16T13:00:00Z' },
    } }));
    await tick();
    assert.equal(h.state.draftFilters.path, '/draft');
});

test('a response does not overwrite search text edited while it is pending', async () => {
    const h = harness();
    const pending = h.state.refreshFeed(false, true, 'push', { ...h.state.appliedFilters, q: 'old' }, 1);
    h.state.searchQuery = 'new draft';
    h.state.draftVersion++;
    reply(h.calls[0], fragment({ state: {
        filters: { type: 'all', q: 'old', tag: '', family: '', range: 'all', path: '', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 1, total_entries: 1, grouped: false, window: { start: null, end: null },
    } }));
    await pending;
    assert.equal(h.state.searchQuery, 'new draft');
    assert.equal(h.state.appliedFilters.q, 'old');
});

test('search input marks draft edits immediately and debounces only applying them', () => {
    assert.match(template, /@input="draftVersion\+\+"[\s\S]*?@input\.debounce\.300ms="search\(\)"/);
});

test('popstate hydrates scope without pushing history and refetches', async () => {
    const h = harness();
    h.state.init();
    reply(h.calls[0], fragment());
    await tick();
    h.location.search = '?type=query&page=2&per_page=50';
    h.emit('popstate', {});
    await tick();
    reply(h.calls[1], fragment({ state: {
        filters: { type: 'query', q: '', tag: '', family: '', range: 'all', path: '', method: '', status_class: '', min_duration_ms: '' },
        page: 2, per_page: 50, total_count: 53, total_entries: 53, grouped: false, window: { start: null, end: null },
    } }));
    await tick();
    assert.equal(h.state.currentType, 'query');
    assert.equal(h.state.currentPage, 2);
    assert.deepEqual(h.historyCalls.map((call) => call[0]), ['replace', 'replace']);
    assert.equal(new URL(h.calls[1].url, 'https://example.test').searchParams.get('type'), 'query');
});

test('an invalid initial range is sent unchanged for explicit server validation', () => {
    const h = harness('?range=not-a-range');
    h.state.init();
    assert.equal(new URL(h.calls[0].url, 'https://example.test').searchParams.get('range'), 'not-a-range');
    assert.equal(h.state.appliedFilters.range, 'all');
});

test('failed popstate response retains the last applied scope and metrics', async () => {
    const h = harness('?range=1h');
    h.state.init();
    reply(h.calls[0], fragment({ metrics: 'confirmed metrics', state: {
        filters: { type: 'all', q: '', tag: '', family: '', range: '1h', path: '', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 1, total_entries: 1, grouped: false, window: { start: '2026-10-16T12:00:00Z', end: '2026-10-16T13:00:00Z' },
    } }));
    await tick();
    h.location.search = '?range=invalid';
    h.emit('popstate', {});
    assert.equal(h.state.appliedFilters.range, '1h');
    reply(h.calls[1], '<div data-orbit-feed>bad response</div>', 400);
    await tick();
    assert.equal(h.state.appliedFilters.range, '1h');
    assert.equal(h.metrics.innerHTML, 'confirmed metrics');
    assert.equal(h.feed.innerHTML.includes('bad response'), false);
    assert.match(h.state.feedError, /filters are invalid/i);
    const callsBeforePoll = h.calls.length;
    h.timers[0]();
    assert.equal(h.calls.length, callsBeforePoll);
    assert.match(h.state.feedError, /filters are invalid/i);
    assert.equal(h.location.search, '?range=invalid');
});

test('a failed popstate network response stays unresolved and blocks normalization polls', async () => {
    const h = harness('?range=1h');
    h.state.init();
    reply(h.calls[0], fragment({ metrics: 'confirmed metrics', state: {
        filters: { type: 'all', q: '', tag: '', family: '', range: '1h', path: '', method: '', status_class: '', min_duration_ms: '' },
        page: 1, per_page: 25, total_count: 1, total_entries: 1, grouped: false, window: { start: '2026-10-16T12:00:00Z', end: '2026-10-16T13:00:00Z' },
    } }));
    await tick();
    h.location.search = '?range=15m';
    h.emit('popstate', {});
    h.calls[1].reject(new Error('temporary network failure'));
    await tick();
    assert.equal(h.state.appliedFilters.range, '1h');
    assert.equal(h.metrics.innerHTML, 'confirmed metrics');
    assert.equal(h.location.search, '?range=15m');
    assert.equal(h.state.scopeValidationBlocked, true);
    const callsBeforePoll = h.calls.length;
    h.timers[0]();
    assert.equal(h.calls.length, callsBeforePoll);
    assert.equal(h.location.search, '?range=15m');
});

test('invalid initial scope blocks polling until the user applies or clears it', async () => {
    const h = harness('?range=bad-range');
    h.state.init();
    reply(h.calls[0], JSON.stringify({ error: 'invalid_filters', fields: { range: 'invalid' } }), 400, { error: 'invalid_filters', fields: { range: 'invalid' } });
    await tick();
    const callsBeforePoll = h.calls.length;
    h.timers[0]();
    assert.equal(h.calls.length, callsBeforePoll);
    assert.equal(h.location.search, '?range=bad-range');
    assert.match(h.state.feedError, /Time range/);
});

test('repeated new URL filters are explicitly rejected without collapsing values', () => {
    const h = harness('?range=1h&range=24h');
    h.state.init();
    assert.equal(h.calls.length, 0);
    assert.match(h.state.feedError, /repeated/i);
});

for (const settleAs of ['success', 'failure']) {
    test(`a repeated-filter popstate invalidates pending ${settleAs} responses`, async () => {
        const h = harness();
        h.state.init();
        const version = h.state.feedRequestVersion;
        h.location.search = '?range=1h&range=24h';
        h.emit('popstate', {});
        assert.ok(h.state.feedRequestVersion > version);
        assert.equal(h.state.feedPending, false);
        assert.equal(h.state.isLoading, false);
        const rejectedVersion = h.state.feedRequestVersion;
        if (settleAs === 'success') reply(h.calls[0], 'late success');
        else h.calls[0].reject(new Error('late failure detail'));
        await tick();
        assert.equal(h.state.feedRequestVersion, rejectedVersion);
        assert.match(h.state.feedError, /repeated/i);
        assert.equal(h.feed.innerHTML, '');
        assert.equal(h.historyCalls.length, 0);
    });
}

for (const [label, mutate] of [
    ['range', (state) => { state.filters.range = 'forever'; }],
    ['method', (state) => { state.filters.method = 'BREW'; }],
    ['status', (state) => { state.filters.status_class = '9xx'; }],
    ['duration', (state) => { state.filters.min_duration_ms = 'NaN'; }],
    ['page bounds', (state) => { state.page = 2; state.total_count = 1; }],
    ['per page', (state) => { state.per_page = 1000; }],
    ['group totals', (state) => { state.grouped = true; state.total_count = 2; state.total_entries = 1; }],
    ['window range', (state) => { state.filters.range = 'all'; state.window = { start: '2026-10-16T12:00:00Z', end: '2026-10-16T13:00:00Z' }; }],
]) {
    test(`malformed composite ${label} state preserves all committed UI and URL state`, async () => {
        const h = harness();
        h.state.init();
        reply(h.calls[0], fragment({ feed: 'last-good-row', metrics: 'last-good-metrics' }));
        await tick();
        const previous = {
            feed: h.feed.innerHTML, metrics: h.metrics.innerHTML,
            filters: { ...h.state.appliedFilters }, page: h.state.currentPage,
            perPage: h.state.perPage, search: h.location.search,
        };
        const state = {
            filters: { ...h.state.appliedFilters }, page: 3, per_page: 50,
            total_count: 10, total_entries: 10, grouped: false,
            window: { start: null, end: null },
        };
        mutate(state);
        const pending = h.state.refreshFeed(false, true, 'push', { ...h.state.appliedFilters }, 1);
        reply(h.calls[1], fragment({ feed: 'bad-row', metrics: 'bad-metrics', state }));
        await pending;
        assert.equal(h.feed.innerHTML, previous.feed);
        assert.equal(h.metrics.innerHTML, previous.metrics);
        assert.deepEqual(JSON.parse(JSON.stringify(h.state.appliedFilters)), previous.filters);
        assert.equal(h.state.currentPage, previous.page);
        assert.equal(h.state.perPage, previous.perPage);
        assert.equal(h.location.search, previous.search);
    });
}

test('field-keyed 400 identifies only the known invalid filter without rendering server text', async () => {
    const h = harness('?range=1h');
    const pending = h.state.refreshFeed(true, true);
    reply(h.calls[0], '', 400, { error: 'invalid_filters', fields: { path: 'private server wording', unexpected: 'do not display' } });
    await pending;
    assert.match(h.state.feedError, /Path/);
    assert.doesNotMatch(h.state.feedError, /private server|unexpected/);
});

test('legacy repeated q parameters use the final value', () => {
    const h = harness('?q=first&q=last');
    h.state.init();
    const params = new URL(h.calls[0].url, 'https://example.test').searchParams;
    assert.equal(params.get('q'), 'last');
    assert.equal(h.state.searchQuery, 'last');
});

test('a late feed body cannot overwrite newer content or loading state', async () => {
    const h = harness();
    const body = deferred();
    const first = h.state.refreshFeed(true, true);
    h.calls[0].resolve({ ok: true, text: () => body.promise });
    await tick();
    const second = h.state.refreshFeed(true, true);
    body.resolve('stale');
    await first;
    assert.equal(h.feed.innerHTML, '');
    assert.equal(h.state.isLoading, true);
    reply(h.calls[1], 'new');
    await second;
    assert.equal(h.feed.innerHTML, 'new');
    assert.equal(h.state.isLoading, false);
    assert.equal(h.feed.scrollTop, 35);
});

test('stale feed failures cannot replace current success with an error', async () => {
    const h = harness();
    const first = h.state.refreshFeed();
    const second = h.state.refreshFeed();
    reply(h.calls[1], 'new');
    await second;
    h.calls[0].reject(new Error('offline'));
    await first;
    assert.equal(h.feed.innerHTML, 'new');
    assert.equal(h.state.feedError, '');
});

for (const failure of ['http', 'network']) {
    test(`feed ${failure} error is visible, leaves existing rows and supports retry`, async () => {
        const h = harness();
        h.feed.innerHTML = 'last good rows';
        const request = h.state.refreshFeed(true, true);
        if (failure === 'http') reply(h.calls[0], '<secret>server error</secret>', 503);
        else h.calls[0].reject(new Error('private network detail'));
        await request;
        assert.equal(h.state.isLoading, false);
        assert.match(h.state.feedError, /refresh|load/i);
        assert.doesNotMatch(h.state.feedError, /secret|private/);
        assert.equal(h.feed.innerHTML, 'last good rows');
        assert.match(template, /x-show="feedError"/);
        assert.match(template, /@click="refreshFeed\(true, true\)"/);
        const retry = h.state.refreshFeed(true, true);
        reply(h.calls[1], 'recovered');
        await retry;
        assert.equal(h.state.feedError, '');
        assert.equal(h.feed.innerHTML, 'recovered');
    });
}

test('out-of-order detail bodies cannot overwrite the selected entry', async () => {
    const h = harness();
    const body = deferred();
    const first = h.state.openDetail('a');
    await tick();
    h.calls[0].resolve({ ok: true, text: () => body.promise });
    await tick();
    const second = h.state.openDetail('b');
    await tick();
    reply(h.calls[1], 'entry b');
    await second;
    body.resolve('entry a');
    await first;
    assert.equal(h.detail.innerHTML, 'entry b');
    assert.equal(h.state.detailEntryId, 'b');
});

test('detail opens immediately and close invalidates its pending request', async () => {
    const h = harness();
    const pending = h.state.openDetail('a');
    assert.equal(h.state.detailOpen, true);
    h.state.closeDetail();
    reply(h.calls[0], 'obsolete');
    await pending;
    assert.equal(h.state.detailOpen, false);
    assert.equal(h.state.isLoadingDetail, false);
    assert.equal(h.calls.length, 1);
    assert.doesNotMatch(h.detail.innerHTML, /obsolete/);
});

test('close invalidates a pending detail body', async () => {
    const h = harness();
    const pending = h.state.openDetail('a');
    await tick();
    h.state.closeDetail();
    h.detail.innerHTML = 'closed';
    reply(h.calls[0], 'late content');
    await pending;
    assert.equal(h.state.detailOpen, false);
    assert.equal(h.detail.innerHTML, 'closed');
    assert.equal(h.state.isLoadingDetail, false);
});

for (const failure of ['http', 'network']) {
    test(`detail ${failure} error stops spinner and retries the same entry`, async () => {
        const h = harness();
        const pending = h.state.openDetail('a');
        await tick();
        if (failure === 'http') reply(h.calls[0], 'private server text', 404);
        else h.calls[0].reject(new Error('private network text'));
        await pending;
        assert.equal(h.state.isLoadingDetail, false);
        assert.doesNotMatch(h.detail.innerHTML, /animate-spin|private/);
        assert.match(h.state.detailError, /detail/i);
        assert.match(template, /x-show="detailError"/);
        assert.match(template, /@click="openDetail\(detailEntryId, true\)"/);
        const retry = h.state.openDetail('a', true);
        await tick();
        reply(h.calls[1], 'recovered');
        await retry;
        assert.equal(h.detail.innerHTML, 'recovered');
        assert.equal(h.state.detailError, '');
        assert.equal(h.state.detailOpen, true);
    });
}

test('HTMX pagination uses one delegated handler and invalidates in-flight polling', async () => {
    const h = harness('?q=needle&family=f&tag=t');
    h.state.init();
    reply(h.calls[0], 'current page');
    await tick();
    h.state.draftFilters.path = '/unapplied';
    const event = {
        detail: { target: h.feed, requestConfig: { path: '/orbit/feed/?page=3&per_page=50' } },
        preventDefault() { this.cancelled = true; },
    };
    h.emit('htmx:beforeRequest', event);
    assert.equal(event.cancelled, true);
    assert.equal(h.state.currentPage, 1);
    const params = new URL(h.calls[1].url, 'https://example.test').searchParams;
    assert.equal(params.get('page'), '3');
    assert.equal(params.get('family'), 'f');
    assert.equal(params.get('tag'), 't');
    assert.equal(params.get('q'), 'needle');
    assert.equal(params.get('path'), null);
    assert.equal(params.get('per_page'), '50');
    reply(h.calls[1], 'page three');
    await tick();
    assert.equal(h.state.currentPage, 3);
    reply(h.calls[0], 'old page');
    await tick();
    assert.equal(h.feed.innerHTML, 'page three');
    h.timers[0]();
    assert.equal(new URL(h.calls[2].url, 'https://example.test').searchParams.get('page'), '3');
    assert.equal(h.listeners.get('htmx:beforeRequest').length, 1);
    assert.equal(h.listeners.get('htmx:afterRequest'), undefined);
    const unrelated = { detail: { target: h.detail }, preventDefault() { throw new Error('unrelated HTMX cancelled'); } };
    h.emit('htmx:beforeRequest', unrelated);
});

test('pause only stops live polling, never claims recording status; manual refresh works', async () => {
    const h = harness();
    h.state.init();
    h.state.togglePause();
    h.timers[0]();
    assert.equal(h.calls.length, 1);
    assert.doesNotMatch(template, /Recording Active/);
    assert.match(template, /Live feed paused/);
    const manual = h.state.refreshFeed();
    reply(h.calls[1], 'manual');
    await manual;
    assert.equal(h.feed.innerHTML, 'manual');
});
