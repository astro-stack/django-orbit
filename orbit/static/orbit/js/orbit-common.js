/*
 * Orbit dashboard shell: icons, JSON highlighting, clipboard helpers and the
 * detail-panel helpers shared by the dashboard and stats pages.
 *
 * Loaded as a classic (non-deferred) script at the end of <body>. Keep it free
 * of template interpolation; pass data from Django with json_script or data-*.
 */
// Initialize Lucide icons
lucide.createIcons();

// Re-initialize icons after HTMX swaps
document.body.addEventListener('htmx:afterSwap', function(event) {
    lucide.createIcons();
});

// JSON syntax highlighting function
function syntaxHighlight(json) {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, null, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

async function copyElement(button) {
    const target = document.getElementById(button.dataset.copyTarget);

    if (!target || button.disabled) {
        return;
    }

    button.disabled = true;

    try {
        await navigator.clipboard.writeText(target.textContent.trim());

        const original = button.innerHTML;

        button.innerHTML = `
            <span class="flex items-center gap-1 text-emerald-400 text-xs">
                <i data-lucide="check" class="w-4 h-4"></i>
                Copied
            </span>
        `;

        lucide.createIcons();

        setTimeout(() => {
            button.innerHTML = original;
            button.disabled = false;
            lucide.createIcons();
        }, 1500);

    } catch (err) {
        button.disabled = false;
        console.error("Failed to copy:", err);
    }
}

async function copyTextWithFallback(text) {
    if (navigator.clipboard && window.isSecureContext) {
        try {
            await navigator.clipboard.writeText(text);
            return;
        } catch (error) {
            // Browser permissions can reject the API even in a secure context.
        }
    }

    const previousFocus = document.activeElement;
    const fallback = document.createElement("textarea");
    fallback.value = text;
    fallback.setAttribute("readonly", "");
    fallback.className = "fixed -left-full top-0 opacity-0";
    document.body.appendChild(fallback);
    fallback.select();

    let copied = false;
    try {
        copied = document.execCommand("copy");
    } finally {
        fallback.remove();
        if (previousFocus && typeof previousFocus.focus === "function") {
            previousFocus.focus({preventScroll: true});
        }
    }

    if (!copied) {
        throw new Error("Clipboard access is unavailable");
    }
}

async function copyRemoteText(button) {
    const url = button.dataset.agentHandoffUrl;
    const original = button.innerHTML;

    if (!url || button.disabled) {
        return;
    }

    button.disabled = true;

    try {
        const response = await fetch(url, {headers: {Accept: "text/plain"}});
        const text = await response.text();

        if (!response.ok) {
            throw new Error("Could not build handoff");
        }

        await copyTextWithFallback(text);
        button.innerHTML = '<i data-lucide="check" class="w-4 h-4"></i><span>Fix handoff copied</span>';
    } catch (error) {
        button.innerHTML = '<i data-lucide="alert-triangle" class="w-4 h-4"></i><span>Copy failed; use Preview handoff</span>';
        console.error("Failed to copy Orbit handoff:", error);
    } finally {
        lucide.createIcons();
        setTimeout(() => {
            button.innerHTML = original;
            button.disabled = false;
            lucide.createIcons();
        }, 1800);
    }
}

document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) {
        return;
    }

    const handoffButton = target.closest(".orbit-copy-remote-btn");

    if (handoffButton) {
        copyRemoteText(handoffButton);
        return;
    }

    const button = target.closest(".orbit-copy-btn");

    if (!button) {
        return;
    }

    copyElement(button);
});

// ---------------------------------------------------------------------------
// Detail panel (partials/detail.html)
//
// The detail partial is inserted with innerHTML, where inline <script> tags
// never run, so its behaviour lives here: delegated click handlers for
// [data-orbit-*] attributes plus orbitInitDetail(), which the dashboard and
// stats pages call after every insertion.
// ---------------------------------------------------------------------------

const ORBIT_MAIL_TAB_ACTIVE = 'text-xs px-3 py-1.5 rounded-md font-medium transition-colors bg-orbit-bg-tertiary text-orbit-text-primary';
const ORBIT_MAIL_TAB_IDLE = 'text-xs px-3 py-1.5 rounded-md font-medium transition-colors text-orbit-text-muted hover:text-orbit-text-secondary';

function orbitMailTab(tab) {
    var isHtml = tab === 'html';
    document.getElementById('mail-panel-plain').classList.toggle('hidden', isHtml);
    document.getElementById('mail-panel-html').classList.toggle('hidden', !isHtml);
    document.getElementById('mail-tab-plain').className = isHtml ? ORBIT_MAIL_TAB_IDLE : ORBIT_MAIL_TAB_ACTIVE;
    document.getElementById('mail-tab-html').className = isHtml ? ORBIT_MAIL_TAB_ACTIVE : ORBIT_MAIL_TAB_IDLE;
}

function orbitInitDetail(root) {
    root = root || document;

    // JSON payload syntax highlighting
    var json = root.querySelector('#json-payload');
    if (json) {
        json.innerHTML = syntaxHighlight(json.textContent);
    }

    // Mail HTML preview: inject through JS so the template engine never escapes it
    var mailBody = root.querySelector('#mail-html-body');
    var mailFrame = root.querySelector('#mail-html-frame');
    if (mailBody && mailFrame) {
        mailFrame.srcdoc = JSON.parse(mailBody.textContent);
    }

    // Query waterfall bars: position/size come from data-* (no inline styles)
    root.querySelectorAll('[data-orbit-left]').forEach(function (bar) {
        bar.style.left = bar.dataset.orbitLeft + '%';
        bar.style.width = bar.dataset.orbitWidth + '%';
    });
}

document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) {
        return;
    }

    const tagButton = target.closest('[data-orbit-tag]');
    if (tagButton) {
        document.dispatchEvent(new CustomEvent('orbit:tag', {detail: {tag: tagButton.dataset.orbitTag}}));
        return;
    }

    const opener = target.closest('[data-orbit-open-detail]');
    if (opener) {
        document.dispatchEvent(new CustomEvent('orbit:open-detail', {detail: {entryId: opener.dataset.orbitOpenDetail}}));
        return;
    }

    const mailTab = target.closest('[data-orbit-mail-tab]');
    if (mailTab) {
        orbitMailTab(mailTab.dataset.orbitMailTab);
    }
});
