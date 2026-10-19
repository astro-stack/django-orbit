const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const scriptPath = path.resolve(__dirname, '../../orbit/static/orbit/js/orbit-common.js');
const script = readFileSync(scriptPath, 'utf8');
assert.ok(script.includes('function copyRemoteText('), 'The shared shell script must contain the remote clipboard handler');

const handoff = 'Masked evidence\n## Fix hypotheses\nDo not infer a root cause.\n';

function harness(options = {}) {
    const calls = { writes: [], fetches: [], commands: [], selections: [], errors: [] };
    const listeners = new Map();
    const timers = [];
    const textareas = [];
    let document;

    class Element {
        constructor(tagName = 'DIV', className = '') {
            this.tagName = tagName;
            this.className = className;
            this.dataset = {};
            this.attributes = {};
            this.children = [];
            this.parentElement = null;
            this.disabled = false;
            this.value = '';
            this._html = '';
        }

        get innerHTML() { return this._html; }
        set innerHTML(value) { this._html = String(value); }
        get textContent() { return this._html.replace(/<[^>]*>/g, ''); }
        set textContent(value) { this._html = String(value); }

        setAttribute(name, value) { this.attributes[name] = String(value); }
        getAttribute(name) { return this.attributes[name] ?? null; }

        appendChild(child) {
            child.parentElement = this;
            this.children.push(child);
            return child;
        }

        remove() {
            if (this.parentElement) {
                this.parentElement.children = this.parentElement.children.filter(
                    (child) => child !== this,
                );
                this.parentElement = null;
            }
        }

        closest(selector) {
            if (selector.startsWith('.') && this.className.split(/\s+/).includes(selector.slice(1))) {
                return this;
            }
            return this.parentElement?.closest(selector) ?? null;
        }

        focus() { document.activeElement = this; }
        select() {
            this.focus();
            calls.selections.push(this.value);
        }

        addEventListener() {}
    }

    const body = new Element('BODY');
    document = {
        body,
        activeElement: body,
        createElement(tag) {
            const element = new Element(tag.toUpperCase());
            if (tag.toLowerCase() === 'textarea') textareas.push(element);
            return element;
        },
        getElementById() { return null; },
        addEventListener(type, callback) {
            listeners.set(type, [...(listeners.get(type) ?? []), callback]);
        },
        execCommand(command) {
            calls.commands.push(command);
            if (options.fallbackError) throw options.fallbackError;
            return options.fallbackResult ?? true;
        },
    };
    const navigator = {};
    if (options.api !== 'absent') {
        navigator.clipboard = {
            async writeText(text) {
                calls.writes.push(text);
                if (options.api === 'reject') throw new Error('NotAllowedError');
            },
        };
    }
    const context = vm.createContext({
        Element,
        document,
        navigator,
        window: { isSecureContext: options.secure ?? true },
        lucide: { createIcons() {} },
        console: { error: (...args) => calls.errors.push(args) },
        setTimeout(callback) { timers.push(callback); return timers.length; },
        async fetch(url, init) {
            calls.fetches.push({ url, init });
            if (options.fetchError) throw options.fetchError;
            if (options.response) return options.response;
            return { ok: options.httpOk ?? true, text: async () => handoff };
        },
    });
    vm.runInContext(script, context, { filename: scriptPath, timeout: 1000 });

    function button(url = '/orbit/entries/current/agent-handoff/') {
        const element = new Element('BUTTON', 'orbit-copy-remote-btn');
        element.dataset.agentHandoffUrl = url;
        element.innerHTML = '<i data-lucide="clipboard-check"></i>Copy fix handoff';
        body.appendChild(element);
        return element;
    }

    return {
        calls, context, document, textareas, button,
        icon(parent) { return parent.appendChild(new Element('SVG')); },
        click(target) {
            for (const callback of listeners.get('click') ?? []) {
                callback({ target, preventDefault() {}, stopPropagation() {} });
            }
        },
        restore() {
            assert.ok(timers.length, 'Copy completion must schedule button restoration');
            for (const callback of timers.splice(0)) callback();
        },
    };
}

function assertCleanFallback(h, focused) {
    assert.equal(h.textareas.length, 1);
    assert.equal(h.textareas[0].parentElement, null, 'Temporary textarea must be removed');
    assert.equal(h.document.activeElement, focused, 'Fallback must restore prior focus');
}

test('secure Clipboard API copies the exact handoff without creating a fallback', async () => {
    const h = harness();
    await h.context.copyTextWithFallback(handoff);
    assert.deepEqual(h.calls.writes, [handoff]);
    assert.deepEqual(h.calls.commands, []);
    assert.equal(h.textareas.length, 0);
});

test('Clipboard API rejection tries fallback, preserves text, cleans up and restores focus', async () => {
    const h = harness({ api: 'reject' });
    const focused = h.button();
    focused.focus();
    await h.context.copyTextWithFallback(handoff);
    assert.deepEqual(h.calls.writes, [handoff]);
    assert.deepEqual(h.calls.commands, ['copy']);
    assert.deepEqual(h.calls.selections, [handoff]);
    assertCleanFallback(h, focused);
});

for (const options of [{ api: 'absent' }, { secure: false }]) {
    test(`fallback works with ${options.api === 'absent' ? 'no Clipboard API' : 'an insecure context'}`, async () => {
        const h = harness(options);
        const focused = h.button();
        focused.focus();
        await h.context.copyTextWithFallback(handoff);
        assert.deepEqual(h.calls.writes, []);
        assert.deepEqual(h.calls.commands, ['copy']);
        assert.deepEqual(h.calls.selections, [handoff]);
        assertCleanFallback(h, focused);
    });
}

for (const failure of [
    { fallbackResult: false },
    { fallbackError: new Error('Legacy clipboard failed') },
]) {
    test(`failed fallback ${failure.fallbackError ? 'throw' : 'false result'} rejects and still cleans up`, async () => {
        const h = harness({ api: 'absent', ...failure });
        const focused = h.button();
        focused.focus();
        await assert.rejects(h.context.copyTextWithFallback(handoff));
        assert.deepEqual(h.calls.commands, ['copy']);
        assertCleanFallback(h, focused);
    });
}

test('successful remote copy disables immediately and restores the original button', async () => {
    let resolveResponse;
    const response = new Promise((resolve) => { resolveResponse = resolve; });
    const h = harness({ response });
    const button = h.button();
    const original = button.innerHTML;
    const pending = h.context.copyRemoteText(button);
    assert.equal(button.disabled, true);
    await h.context.copyRemoteText(button);
    assert.equal(h.calls.fetches.length, 1, 'Disabled button must prevent duplicate requests');
    resolveResponse({ ok: true, text: async () => handoff });
    await pending;
    assert.deepEqual(h.calls.writes, [handoff]);
    assert.equal(h.calls.fetches[0].init.headers.Accept, 'text/plain');
    assert.notEqual(button.innerHTML, original, 'Completion must display a status');
    h.restore();
    assert.equal(button.disabled, false);
    assert.equal(button.innerHTML, original);
});

test('delegated nested icon clicks work for details inserted and replaced after shell initialization', async () => {
    const h = harness();
    const first = h.button('/orbit/entries/first/agent-handoff/');
    h.click(h.icon(first));
    await new Promise(setImmediate);
    assert.equal(h.calls.fetches[0].url, first.dataset.agentHandoffUrl);
    assert.deepEqual(h.calls.writes, [handoff]);
    first.remove();
    const replacement = h.button('/orbit/entries/replacement/agent-handoff/');
    h.click(h.icon(replacement));
    await new Promise(setImmediate);
    assert.deepEqual(h.calls.fetches.map((call) => call.url), [
        first.dataset.agentHandoffUrl, replacement.dataset.agentHandoffUrl,
    ]);
    assert.deepEqual(h.calls.writes, [handoff, handoff]);
    h.restore();
    assert.equal(first.disabled, false);
    assert.equal(replacement.disabled, false);
});

for (const [name, options] of [
    ['non-OK HTTP response', { httpOk: false }],
    ['network rejection', { fetchError: new Error('Offline') }],
    ['response body rejection', { response: {
        ok: true, text: async () => { throw new Error('Interrupted body'); },
    } }],
    ['both clipboard mechanisms failing', { api: 'reject', fallbackResult: false }],
]) {
    test(`${name} offers Preview recovery and restores the button`, async () => {
        const h = harness(options);
        const button = h.button();
        const original = button.innerHTML;
        await h.context.copyRemoteText(button);
        assert.match(button.textContent, /preview/i, 'Failure must point to manual recovery');
        if (name !== 'both clipboard mechanisms failing') {
            assert.deepEqual(h.calls.writes, [], 'Fetch errors must never reach the clipboard');
            assert.deepEqual(h.calls.commands, []);
        } else {
            assert.deepEqual(h.calls.commands, ['copy']);
            assert.equal(h.textareas[0].parentElement, null);
        }
        h.restore();
        assert.equal(button.disabled, false);
        assert.equal(button.innerHTML, original);
    });
}

test('missing handoff URL and already disabled buttons do not fetch or copy', async () => {
    const h = harness();
    const missing = h.button('');
    const disabled = h.button();
    disabled.disabled = true;
    await h.context.copyRemoteText(missing);
    await h.context.copyRemoteText(disabled);
    assert.deepEqual(h.calls.fetches, []);
    assert.deepEqual(h.calls.writes, []);
    assert.equal(missing.disabled, false);
    assert.equal(disabled.disabled, true);
});
