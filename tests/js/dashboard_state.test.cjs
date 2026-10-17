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

function harness(search = '') {
    const listeners = new Map();
    const feed = { id: 'feed-container', innerHTML: '', scrollTop: 35 };
    const detail = { id: 'detail-container', innerHTML: '' };
    const calls = [];
    const timers = [];
    const addEventListener = (type, fn) => listeners.set(type, [...(listeners.get(type) || []), fn]);
    const context = vm.createContext({
        URL, URLSearchParams,
        URLS: { feed: '/orbit/feed/', detail: '/orbit/entry/' },
        window: { location: { search, origin: 'https://example.test' }, htmx: {} },
        document: {
            body: { addEventListener }, addEventListener,
            getElementById: (id) => ({ 'feed-container': feed, 'detail-container': detail }[id] || null),
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
        setTimeout(fn) { fn(); }, console: { error() {} },
    });
    vm.runInContext(script.replace('{{ current_type }}', 'all'), context);
    const state = context.orbitDashboard();
    state.$nextTick = (fn) => fn();
    const emit = (type, event) => (listeners.get(type) || []).forEach((fn) => fn(event));
    return { state, feed, detail, calls, timers, listeners, emit };
}

const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
const reply = (call, html, status = 200) => call.resolve({ ok: status < 400, status, text: async () => html });

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

test('close invalidates the detail opening delay', async () => {
    const h = harness();
    const pending = h.state.openDetail('a');
    h.state.closeDetail();
    await pending;
    assert.equal(h.state.detailOpen, false);
    assert.equal(h.state.isLoadingDetail, false);
    assert.equal(h.calls.length, 0);
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
    const event = {
        detail: { target: h.feed, requestConfig: { path: '/orbit/feed/?page=3&per_page=50' } },
        preventDefault() { this.cancelled = true; },
    };
    h.emit('htmx:beforeRequest', event);
    assert.equal(event.cancelled, true);
    assert.equal(h.state.currentPage, 3);
    const params = new URL(h.calls[1].url, 'https://example.test').searchParams;
    assert.equal(params.get('page'), '3');
    assert.equal(params.get('family'), 'f');
    assert.equal(params.get('tag'), 't');
    assert.equal(params.get('q'), 'needle');
    assert.equal(params.get('per_page'), '50');
    reply(h.calls[1], 'page three');
    await tick();
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
