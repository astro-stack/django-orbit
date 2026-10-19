/*
 * Alpine.js component behind the Orbit dashboard (orbit/dashboard.html).
 *
 * Server-provided values are read from the #orbit-dashboard-config element's
 * data-* attributes (feed-url, detail-url, clear-url, current-type), never
 * interpolated into this file. Loaded as a classic script before Alpine starts
 * so that x-data="orbitDashboard()" resolves.
 */
function orbitDashboard() {
    // URLs and initial type passed from the Django view as data-* attributes
    const config = (document.getElementById('orbit-dashboard-config') || {}).dataset || {};
    const URLS = {
        feed: config.feedUrl || '',
        detail: config.detailUrl || '',
        clear: config.clearUrl || ''
    };
    const initial = new URLSearchParams(window.location.search);
    const FILTER_KEYS = ['type', 'q', 'tag', 'family', 'range', 'path', 'method', 'status_class', 'min_duration_ms'];
    const FILTER_LABELS = { range: 'Time range', path: 'Path', method: 'HTTP method', status_class: 'Status', min_duration_ms: 'Minimum duration' };
    const ENTRY_TYPES = new Set(['all', 'request', 'query', 'log', 'exception', 'job', 'command', 'cache', 'model', 'http_client', 'dump', 'mail', 'signal', 'redis', 'gate', 'transaction', 'storage', 'llm']);
    const HTTP_METHODS = new Set(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'CONNECT', 'TRACE']);
    const STATUS_CLASSES = new Set(['2xx', '3xx', '4xx', '5xx']);
    const RANGE_MINUTES = { '15m': 15, '1h': 60, '24h': 1440 };
    const emptyFilters = () => ({ type: 'all', q: '', tag: '', family: '', range: 'all', path: '', method: '', status_class: '', min_duration_ms: '' });
    const readFilters = (params) => {
        const filters = emptyFilters();
        for (const key of FILTER_KEYS) {
            const values = params.getAll(key);
            if (values.length) filters[key] = values[values.length - 1];
        }
        if (!filters.type) filters.type = 'all';
        return filters;
    };
    const hasRepeatedNewFilter = (params) => ['range', 'path', 'method', 'status_class', 'min_duration_ms'].some((key) => params.getAll(key).length > 1);
    const pageNumber = (value, fallback, maximum = Number.MAX_SAFE_INTEGER) => {
        if (value === null || !/^[+-]?\d+$/.test(value) || value.length > 64) return fallback;
        const number = Number(value);
        if (!Number.isSafeInteger(number)) return fallback;
        return Math.max(1, Math.min(number, maximum));
    };

    return {
        currentType: readFilters(initial).type || config.currentType || 'all',
        appliedFilters: emptyFilters(),
        draftFilters: readFilters(initial),
        scopeValidationBlocked: false,
        metricsHTML: '',
        emptyScope: false,
        draftVersion: 0,
        isPaused: false,
        initialized: false,
        detailOpen: false,
        detailEntryId: null,
        detailIndex: -1,
        detailTotal: 0,
        pollingInterval: null,
        currentPage: pageNumber(initial.get('page'), 1),
        perPage: pageNumber(initial.get('per_page'), 25, 100),
        searchQuery: readFilters(initial).q,
        familyFilter: readFilters(initial).family,
        tagFilter: readFilters(initial).tag,
        showOnboarding: false,
        isLoading: false,
        isLoadingDetail: false,
        feedRequestVersion: 0,
        detailRequestVersion: 0,
        feedPending: false,
        feedError: '',
        detailError: '',
        
        search() {
            this.draftFilters.q = this.searchQuery;
            this.applyFilters();
        },

        applyFilters(historyMode = 'push') {
            this.draftFilters.q = this.searchQuery;
            this.draftVersion++;
            this.refreshFeed(false, true, historyMode, { ...this.draftFilters }, 1, null, true, true);
        },

        clearFilters() {
            const reset = emptyFilters();
            reset.type = this.currentType;
            this.searchQuery = '';
            this.draftFilters = reset;
            this.applyFilters();
        },

        scopeSummary() {
            const f = this.appliedFilters;
            const active = [];
            if (f.range !== 'all') active.push(f.range);
            if (f.path) active.push(`path: ${f.path}`);
            if (f.method) active.push(f.method);
            if (f.status_class) active.push(f.status_class);
            if (f.min_duration_ms) active.push(`>= ${f.min_duration_ms} ms`);
            if (f.q) active.push(`search: ${f.q}`);
            if (f.tag) active.push(`tag: ${f.tag}`);
            if (f.family) active.push(`family: ${f.family}`);
            return active.length ? `Applied scope: ${active.join(' · ')}` : 'Applied scope: all recorded entries';
        },
        
        init() {
            if (this.initialized) return;
            this.initialized = true;
            // Route HTMX pagination through the same ordered fetch path as polling.
            document.body.addEventListener('htmx:beforeRequest', (e) => {
                if (e.detail?.target?.id !== 'feed-container') return;
                const path = e.detail.requestConfig?.path;
                if (!path) return;
                const url = new URL(path, window.location.origin);
                const page = pageNumber(url.searchParams.get('page'), 1);
                const perPage = pageNumber(url.searchParams.get('per_page'), this.perPage, 100);
                e.preventDefault();
                this.refreshFeed(true, true, 'push', { ...this.appliedFilters }, page, perPage);
            });
            window.addEventListener('popstate', () => {
                const params = new URLSearchParams(window.location.search);
                const candidate = readFilters(params);
                this.draftFilters = { ...candidate };
                this.searchQuery = candidate.q;
                this.draftVersion++;
                if (hasRepeatedNewFilter(params)) {
                    this.feedRequestVersion++;
                    this.feedPending = false;
                    this.isLoading = false;
                    this.scopeValidationBlocked = true;
                    this.feedError = 'Repeated filter values are invalid. Use one value per filter.';
                    return;
                }
                this.refreshFeed(true, true, 'replace', candidate, pageNumber(params.get('page'), 1), pageNumber(params.get('per_page'), 25, 100), true, true);
            });
            // Show the onboarding tour on first visit only
            if (!localStorage.getItem('orbit:onboarded')) {
                this.showOnboarding = true;
                this.$nextTick(() => lucide.createIcons());
            }

            // Initial URL values are a candidate until the server confirms them.
            if (hasRepeatedNewFilter(initial)) {
                this.scopeValidationBlocked = true;
                this.feedError = 'Repeated filter values are invalid. Use one value per filter.';
            } else {
                this.refreshFeed(true, false, 'replace', { ...this.draftFilters }, this.currentPage, this.perPage, true, true);
            }

            // Start polling
            this.startPolling();
            
            // Handle entry clicks
            document.addEventListener('click', (e) => {
                const row = e.target.closest('[data-entry-id]');
                if (row) {
                    this.openDetail(row.dataset.entryId);
                }
            });
            
            // Handle custom event for opening details (from duplicate queries, etc.)
            document.addEventListener('orbit:open-detail', (e) => {
                if (e.detail && e.detail.entryId) {
                    this.openDetail(e.detail.entryId);
                }
            });

            // Filter the feed by a tag (clicked from the detail panel)
            document.addEventListener('orbit:tag', (e) => {
                if (e.detail && e.detail.tag) {
                    this.searchQuery = 'tag:' + e.detail.tag;
                    this.closeDetail();
                    this.search();
                }
            });

            // Show a success checkmark only after a valid explain plan is loaded
            document.body.addEventListener("htmx:afterSwap", (e) => {
                if (!e.target.id.startsWith("explain-")) return;

                const id = e.target.id.replace("explain-", "");
                const successIcon = document.getElementById(`explain-success-${id}`);
                const loadedPlan = e.target.querySelector('[data-orbit-explain-status="success"]');

                successIcon?.classList.toggle("hidden", !loadedPlan);
                lucide.createIcons();
            });

            // Keyboard shortcuts: Esc closes, j/k move between entries (Vim-style)
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    if (this.detailOpen) this.closeDetail();
                    return;
                }
                // Don't hijack keys while typing in the search box
                const tag = (e.target.tagName || '').toLowerCase();
                if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;

                if (e.key === 'j' || e.key === 'ArrowDown') {
                    if (this.detailOpen) { e.preventDefault(); this.navigateDetail(1); }
                } else if (e.key === 'k' || e.key === 'ArrowUp') {
                    if (this.detailOpen) { e.preventDefault(); this.navigateDetail(-1); }
                }
            });
        },
        
        startPolling() {
            // Clear existing interval
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
            }
            
            // Poll every 3 seconds
            this.pollingInterval = setInterval(() => {
                if (!this.isPaused && !this.feedPending && !this.scopeValidationBlocked) {
                    this.refreshFeed();
                }
            }, 3000);
        },
        
        setType(type) {
            this.draftFilters.type = type;
            this.applyFilters();
        },
        
        getTypeLabel() {
            const labels = {
                'all': 'All Events',
                'request': 'Requests',
                'query': 'Queries',
                'log': 'Logs',
                'exception': 'Exceptions',
                'job': 'Jobs',
                'transaction': 'Transactions',
                'storage': 'Storage'
            };
            return labels[this.currentType] || 'Events';
        },
        
        togglePause() {
            this.isPaused = !this.isPaused;
            // Reinitialize icons for the button
            this.$nextTick(() => lucide.createIcons());
        },

        dismissOnboarding() {
            this.showOnboarding = false;
            localStorage.setItem('orbit:onboarded', '1');
        },

        
        async refreshFeed(preservePage = true, showLoading = false, historyMode = 'replace', filterSnapshot = null, pageSnapshot = null, perPageSnapshot = null, hydrateDraft = false, allowValidationRecovery = false) {
            if (this.scopeValidationBlocked && !allowValidationRecovery) return;
            const version = ++this.feedRequestVersion;
            this.feedPending = true;
            const container = document.getElementById('feed-container');
            const page = pageSnapshot === null ? (preservePage ? this.currentPage : 1) : pageSnapshot;
            const requestedFilters = { ...(filterSnapshot || this.appliedFilters) };
            const requestedPerPage = perPageSnapshot || this.perPage;
            const requestedDraftVersion = this.draftVersion;
            let validationError = '';
            this.feedError = '';

            // Only show loading for user-initiated actions (not polling)
            if (showLoading) {
                this.isLoading = true;
            }

            // Preserve scroll position so background polling doesn't jump the feed to top
            const prevScroll = container.scrollTop;

            try {
                const queryParams = new URLSearchParams();
                for (const key of FILTER_KEYS) if (requestedFilters[key]) queryParams.set(key, requestedFilters[key]);
                queryParams.set('page', page);
                queryParams.set('per_page', requestedPerPage);
                const response = await fetch(`${URLS.feed}?${queryParams}`);
                if (!response.ok) {
                    if (response.status === 400) {
                        let fields = [];
                        try {
                            const payload = await response.json();
                            if (payload?.error === 'invalid_filters' && payload.fields && typeof payload.fields === 'object' && !Array.isArray(payload.fields)) {
                                fields = Object.keys(payload.fields).filter((key) => Object.prototype.hasOwnProperty.call(FILTER_LABELS, key));
                            }
                        } catch {
                            fields = [];
                        }
                        if (version !== this.feedRequestVersion) return;
                        this.scopeValidationBlocked = true;
                        validationError = fields.length
                            ? `Invalid filters: ${fields.map((key) => FILTER_LABELS[key]).join(', ')}. Correct them and apply again.`
                            : 'Some filters are invalid. Correct them and apply again.';
                    }
                    throw new Error('Feed request failed');
                }
                const html = await response.text();
                if (version === this.feedRequestVersion) {
                    const parsed = new DOMParser().parseFromString(html, 'text/html');
                    const feed = parsed.querySelector('[data-orbit-feed]');
                    const metrics = parsed.querySelector('template[data-orbit-metrics]');
                    const stateElement = parsed.getElementById('orbit-explorer-state');
                    if (!feed || !metrics || !stateElement || stateElement.type !== 'application/json'
                        || parsed.querySelectorAll('[data-orbit-feed]').length !== 1
                        || parsed.querySelectorAll('template[data-orbit-metrics]').length !== 1
                        || parsed.querySelectorAll('script#orbit-explorer-state[type="application/json"]').length !== 1
                        || feed.querySelector('script, [hx-swap-oob]')
                        || metrics.content.querySelector('script')) throw new Error('Invalid explorer response');
                    const explorerState = JSON.parse(stateElement.textContent);
                    const isCount = (value, minimum) => Number.isSafeInteger(value) && value >= minimum;
                    const isIso = (value) => typeof value === 'string'
                        && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)
                        && Number.isFinite(Date.parse(value));
                    if (!explorerState || !explorerState.filters || !isCount(explorerState.page, 1)
                        || !isCount(explorerState.per_page, 1) || explorerState.per_page > 100
                        || !isCount(explorerState.total_count, 0) || !isCount(explorerState.total_entries, 0)
                        || typeof explorerState.grouped !== 'boolean' || !explorerState.window) throw new Error('Invalid explorer state');
                    for (const key of FILTER_KEYS) if (typeof explorerState.filters[key] !== 'string') throw new Error('Invalid explorer filters');
                    const filters = explorerState.filters;
                    if (!ENTRY_TYPES.has(filters.type) || !['all', ...Object.keys(RANGE_MINUTES)].includes(filters.range)
                        || filters.path.length > 512 || filters.path !== filters.path.trim()
                        || (filters.method !== '' && !HTTP_METHODS.has(filters.method))
                        || (filters.status_class !== '' && !STATUS_CLASSES.has(filters.status_class))
                        || (filters.min_duration_ms !== '' && (!/^(0|[1-9]\d*)$/.test(filters.min_duration_ms) || Number(filters.min_duration_ms) > 86400000))) throw new Error('Invalid explorer filters');
                    const maxPage = Math.max(1, Math.ceil(explorerState.total_count / explorerState.per_page));
                    if (explorerState.page > maxPage || (explorerState.grouped && explorerState.total_count > explorerState.total_entries)) throw new Error('Invalid explorer pagination');
                    const scopeWindow = explorerState.window;
                    if (filters.range === 'all') {
                        if (scopeWindow.start !== null || scopeWindow.end !== null) throw new Error('Invalid explorer window');
                    } else if (!isIso(scopeWindow.start) || !isIso(scopeWindow.end)
                        || Date.parse(scopeWindow.end) < Date.parse(scopeWindow.start)
                        || Date.parse(scopeWindow.end) - Date.parse(scopeWindow.start) !== RANGE_MINUTES[filters.range] * 60000) {
                        throw new Error('Invalid explorer window');
                    }
                    const metricsHTML = metrics.innerHTML;
                    const canonicalFilters = { ...explorerState.filters };
                    const currentUrl = new URL(window.location.href || `${window.location.pathname}${window.location.search}${window.location.hash}`, window.location.origin);
                    currentUrl.search = '';
                    for (const key of FILTER_KEYS) if (canonicalFilters[key]) currentUrl.searchParams.set(key, canonicalFilters[key]);
                    currentUrl.searchParams.set('page', String(explorerState.page));
                    currentUrl.searchParams.set('per_page', String(explorerState.per_page));
                    container.innerHTML = feed.innerHTML;
                    document.getElementById('orbit-metrics-container').innerHTML = metricsHTML;
                    this.metricsHTML = metricsHTML;
                    this.appliedFilters = canonicalFilters;
                    if (hydrateDraft && this.draftVersion === requestedDraftVersion) {
                        this.draftFilters = { ...canonicalFilters };
                        this.searchQuery = canonicalFilters.q;
                    }
                    this.currentType = canonicalFilters.type;
                    this.familyFilter = canonicalFilters.family;
                    this.tagFilter = canonicalFilters.tag;
                    this.currentPage = explorerState.page;
                    this.perPage = explorerState.per_page;
                    this.emptyScope = explorerState.total_entries === 0;
                    if (historyMode !== 'none') window.history[historyMode === 'push' ? 'pushState' : 'replaceState']({}, '', `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
                    this.scopeValidationBlocked = false;
                    this.feedError = '';
                    htmx.process(container);  // Process HTMX attributes on new content
                    lucide.createIcons();
                    container.scrollTop = prevScroll;

                    // Keep the open panel's prev/next bounds in sync with the new rows
                    if (this.detailOpen) this.updateDetailPosition();
                    this.syncDetailWithFeed();

                }
            } catch (error) {
                if (version === this.feedRequestVersion) {
                    if (hydrateDraft) this.scopeValidationBlocked = true;
                    this.feedError = validationError || 'Could not refresh entries. Showing the last loaded results.';
                }
            } finally {
                if (version === this.feedRequestVersion) {
                    this.isLoading = false;
                    this.feedPending = false;
                }
            }
        },
        
        async openDetail(entryId, force = false) {
            // If clicking the same entry while panel is open, close it
            if (!force && this.detailOpen && this.detailEntryId === entryId) {
                this.closeDetail();
                return;
            }
            
            // If clicking a different entry, just update the content (don't close/reopen)
            const version = ++this.detailRequestVersion;
            this.detailEntryId = entryId;
            this.detailError = '';
            this.updateDetailPosition();
            this.isLoadingDetail = true;
            
            this.detailOpen = true;
            
            const container = document.getElementById('detail-container');
            
            // Show loading spinner immediately
            container.innerHTML = `
                <div class="flex flex-col items-center justify-center h-full min-h-[200px] gap-3">
                    <div class="animate-spin rounded-full h-8 w-8 border-2 border-orbit-accent-cyan border-t-transparent"></div>
                    <span class="text-sm text-orbit-text-muted">Loading details...</span>
                </div>
            `;
            
            try {
                const response = await fetch(`${URLS.detail}${entryId}/`);
                if (!response.ok) throw new Error('Detail request failed');
                const html = await response.text();
                if (version === this.detailRequestVersion) {
                    container.innerHTML = html;
                    if (window.htmx) {
                        htmx.process(container);
                    }
                    lucide.createIcons();

                    // JSON highlighting, mail preview and other detail-panel setup
                    if (typeof orbitInitDetail === 'function') orbitInitDetail(container);
                }
            } catch (error) {
                if (version === this.detailRequestVersion) {
                    container.innerHTML = '';
                    this.detailError = 'Could not load details. Retry or select another event.';
                }
            } finally {
                if (version === this.detailRequestVersion) this.isLoadingDetail = false;
            }
        },
        
        handleDetailOutside(event) {
            // Selecting a feed row replaces the detail; it is not a dismissal.
            if (event.target.closest('#feed-container [data-entry-id]')) return;
            this.closeDetail();
        },

        closeDetail() {
            this.detailRequestVersion++;
            this.isLoadingDetail = false;
            this.detailError = '';
            this.detailOpen = false;
            this.detailEntryId = null;
            this.detailIndex = -1;
            this.detailTotal = 0;
        },

        // Ordered entry IDs currently visible in the feed (drives prev/next)
        getFeedEntryIds() {
            return Array.from(
                document.querySelectorAll('#feed-container [data-entry-id]')
            ).map(el => el.dataset.entryId);
        },

        // Recompute the open entry's position within the current feed
        updateDetailPosition() {
            const ids = this.getFeedEntryIds();
            this.detailIndex = ids.indexOf(this.detailEntryId);
            this.detailTotal = ids.length;
        },

        // Move to the prev/next entry in the current feed (dir = -1 | +1)
        navigateDetail(dir) {
            if (!this.detailOpen) return;
            const ids = this.getFeedEntryIds();
            const idx = ids.indexOf(this.detailEntryId);
            if (idx === -1) return;
            const nextIdx = idx + dir;
            if (nextIdx < 0 || nextIdx >= ids.length) return;
            const nextId = ids[nextIdx];
            const row = document.querySelector(`#feed-container [data-entry-id="${nextId}"]`);
            if (row) row.scrollIntoView({ block: 'nearest' });
            this.openDetail(nextId);
        },

        // Close the panel if its entry dropped out of the feed after a filter/search
        syncDetailWithFeed() {
            if (!this.detailOpen || !this.detailEntryId) return;
            const stillThere = document.querySelector(
                `#feed-container [data-entry-id="${this.detailEntryId}"]`
            );
            if (stillThere) {
                this.updateDetailPosition();
            } else {
                this.closeDetail();
            }
        },
        
        async clearAll() {
            if (!confirm('Clear all Orbit entries?')) return;
            
            try {
                const response = await fetch(URLS.clear, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });
                
                if (response.ok) {
                    this.refreshFeed();
                }
            } catch (error) {
                console.error('Failed to clear entries:', error);
            }
        },
        
        getCSRFToken() {
            // Try to get from cookie
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'csrftoken') {
                    return value;
                }
            }
            return '';
        }
    };
}
