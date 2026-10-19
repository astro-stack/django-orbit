const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const scriptPath = path.resolve(__dirname, '../../orbit/static/orbit/js/orbit-common.js');
const script = readFileSync(scriptPath, 'utf8');

class FakeElement {
    constructor(attrs = {}) {
        this.dataset = attrs;
        this.style = {};
        this.className = '';
        this.innerHTML = '';
        this.textContent = '';
        this.classes = new Set();
        this.classList = {
            toggle: (name, force) => (force ? this.classes.add(name) : this.classes.delete(name)),
        };
    }
    closest(selector) {
        const key = selector.replace(/^\[data-/, '').replace(/\]$/, '');
        const camel = key.replace(/-([a-z])/g, (_m, c) => c.toUpperCase());
        return camel in this.dataset ? this : null;
    }
}

function harness() {
    const listeners = new Map();
    const dispatched = [];
    const byId = {};
    const document = {
        body: { addEventListener() {} },
        addEventListener: (type, fn) => listeners.set(type, [...(listeners.get(type) || []), fn]),
        dispatchEvent: (event) => dispatched.push(event),
        getElementById: (id) => byId[id] || null,
    };
    const context = vm.createContext({
        Element: FakeElement,
        CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init.detail; } },
        document,
        navigator: {},
        window: {},
        lucide: { createIcons() {} },
        console,
    });
    vm.runInContext(script, context, { filename: scriptPath });
    const click = (target) => (listeners.get('click') || []).forEach((fn) => fn({ target }));
    return { context, click, dispatched, byId };
}

test('tag buttons dispatch orbit:tag without inline handlers', () => {
    const h = harness();
    h.click(new FakeElement({ orbitTag: 'checkout' }));
    assert.equal(h.dispatched.length, 1);
    assert.equal(h.dispatched[0].type, 'orbit:tag');
    assert.deepEqual({ ...h.dispatched[0].detail }, { tag: 'checkout' });
});

test('data-orbit-open-detail elements dispatch orbit:open-detail with the entry id', () => {
    const h = harness();
    h.click(new FakeElement({ orbitOpenDetail: 'abc-123' }));
    assert.equal(h.dispatched[0].type, 'orbit:open-detail');
    assert.deepEqual({ ...h.dispatched[0].detail }, { entryId: 'abc-123' });
});

test('mail tabs switch panels and tab styling', () => {
    const h = harness();
    for (const id of ['mail-panel-plain', 'mail-panel-html', 'mail-tab-plain', 'mail-tab-html']) {
        h.byId[id] = new FakeElement();
    }
    h.click(new FakeElement({ orbitMailTab: 'html' }));
    assert.ok(!h.byId['mail-panel-html'].classes.has('hidden'));
    assert.ok(h.byId['mail-panel-plain'].classes.has('hidden'));
    assert.match(h.byId['mail-tab-html'].className, /bg-orbit-bg-tertiary/);
    assert.doesNotMatch(h.byId['mail-tab-plain'].className, /bg-orbit-bg-tertiary/);
    h.click(new FakeElement({ orbitMailTab: 'plain' }));
    assert.ok(h.byId['mail-panel-html'].classes.has('hidden'));
    assert.match(h.byId['mail-tab-plain'].className, /bg-orbit-bg-tertiary/);
});

test('orbitInitDetail highlights JSON, fills the mail preview and sizes waterfall bars', () => {
    const h = harness();
    const json = new FakeElement();
    json.textContent = '{"a": 1}';
    const mailBody = new FakeElement();
    mailBody.textContent = JSON.stringify('<h1>Hello</h1>');
    const frame = new FakeElement();
    const bar = new FakeElement({ orbitLeft: '12.5', orbitWidth: '30' });
    const elements = { '#json-payload': json, '#mail-html-body': mailBody, '#mail-html-frame': frame };
    h.context.orbitInitDetail({
        querySelector: (selector) => elements[selector] || null,
        querySelectorAll: (selector) => (selector === '[data-orbit-left]' ? [bar] : []),
    });
    assert.match(json.innerHTML, /class="json-key"/);
    assert.equal(frame.srcdoc, '<h1>Hello</h1>');
    assert.equal(bar.style.left, '12.5%');
    assert.equal(bar.style.width, '30%');
});

test('orbitInitDetail tolerates a partial without optional sections', () => {
    const h = harness();
    h.context.orbitInitDetail({ querySelector: () => null, querySelectorAll: () => [] });
});
