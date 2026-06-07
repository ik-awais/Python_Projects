'use strict';

// ════════════════════════════════════════════════
//  CONFIG
// ════════════════════════════════════════════════

const ADMIN_PASSWORD = (() => {
    let pw = sessionStorage.getItem('ll_admin_pw');
    if (!pw) {
        pw = prompt('Admin password:');
        if (pw) sessionStorage.setItem('ll_admin_pw', pw);
    }
    return pw || '';
})();

const PAGE_SIZE = 20;

// ════════════════════════════════════════════════
//  API LAYER
// ════════════════════════════════════════════════

const api = {
    _headers() {
        return {
            'Content-Type': 'application/json',
            'X-Admin-Password': ADMIN_PASSWORD,
        };
    },

    async _fetch(url, options = {}) {
        const res = await fetch(url, {
            ...options,
            headers: { ...this._headers(), ...(options.headers || {}) },
        });
        if (res.status === 401) {
            sessionStorage.removeItem('ll_admin_pw');
            toast('Authentication failed. Reload to re-enter password.', 'error');
            throw new Error('Unauthorized');
        }
        if (!res.ok) {
            let msg = `HTTP ${res.status}`;
            try { const d = await res.json(); msg = d.error || d.message || msg; } catch (_) {}
            throw new Error(msg);
        }
        return res.json();
    },

    getStats()                     { return this._fetch('/admin/stats'); },
    getHealth()                    { return this._fetch('/admin/health'); },
    getSubjects()                  { return this._fetch('/admin/subjects'); },
    getDocuments()                 { return this._fetch('/admin/documents'); },
    getDocument(id)                { return this._fetch(`/admin/documents/${id}`); },
    deleteDocument(id)             { return this._fetch(`/admin/documents/${id}`, { method: 'DELETE' }); },
    reindexDocument(id)            { return this._fetch(`/admin/documents/${id}/reindex`, { method: 'POST' }); },
};

// ════════════════════════════════════════════════
//  TOAST
// ════════════════════════════════════════════════

function toast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<div class="toast-dot"></div><span>${escapeHtml(message)}</span>`;
    container.appendChild(el);
    setTimeout(() => {
        el.classList.add('removing');
        el.addEventListener('animationend', () => el.remove());
    }, duration);
}

// ════════════════════════════════════════════════
//  UTILITIES
// ════════════════════════════════════════════════

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function formatDate(str) {
    if (!str) return '–';
    try {
        return new Date(str).toLocaleString(undefined, {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch (_) { return str; }
}

function formatNumber(n) {
    if (n === null || n === undefined) return '–';
    return Number(n).toLocaleString();
}

function statusBadge(status) {
    const s = (status || 'unknown').toLowerCase();
    return `<span class="status-badge ${s}">${escapeHtml(s)}</span>`;
}

function setLastUpdated() {
    document.getElementById('lastUpdated').textContent =
        'Updated ' + new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

function setSpinning(btn, active) {
    if (!btn) return;
    btn.classList.toggle('spinning', active);
}

// ════════════════════════════════════════════════
//  NAVIGATION
// ════════════════════════════════════════════════

const SECTION_TITLES = {
    overview:  'Overview',
    documents: 'Documents',
    subjects:  'Subjects',
    health:    'Health',
};

function navigateTo(sectionKey) {
    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.toggle('active', el.dataset.section === sectionKey);
    });
    document.querySelectorAll('.section').forEach(el => {
        el.classList.toggle('active', el.id === `section-${sectionKey}`);
    });
    document.getElementById('pageTitle').textContent = SECTION_TITLES[sectionKey] || sectionKey;

    switch (sectionKey) {
        case 'overview':  loadOverview();  break;
        case 'documents': loadDocuments(); break;
        case 'subjects':  loadSubjects();  break;
        case 'health':    loadHealth();    break;
    }
}

document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', e => {
        e.preventDefault();
        navigateTo(el.dataset.section);
    });
});

// ════════════════════════════════════════════════
//  OVERVIEW
// ════════════════════════════════════════════════

async function loadOverview() {
    try {
        const [stats, health] = await Promise.all([api.getStats(), api.getHealth()]);
        renderStats(stats);
        renderStatusPanel(health);
        setLastUpdated();
    } catch (err) {
        toast('Failed to load overview: ' + err.message, 'error');
    }
}

function renderStats(stats) {
    document.querySelectorAll('#statsGrid [data-key]').forEach(el => {
        const key = el.dataset.key;
        const val = stats[key];
        el.textContent = val !== undefined ? formatNumber(val) : '0';
    });
    document.querySelectorAll('#statsGrid .stat-card').forEach(el => el.classList.remove('skeleton'));
}

function renderStatusPanel(health) {
    // Use flat fields returned by /admin/health
    const queueStatus = health.queue_status || 'unknown';
    const queueWorkers = health.queue_workers || 0;
    const chromaStatus = health.chroma_status || health.chromadb || 'unknown';
    const dbStatus = health.db_status || health.database || 'unknown';

    function applyStatus(dotId, detailId, status, detail) {
        const dot = document.getElementById(dotId);
        const det = document.getElementById(detailId);
        if (dot) {
            dot.className = 'status-dot';
            if (status === 'healthy') dot.classList.add('green');
            else if (status === 'degraded') dot.classList.add('yellow');
            else dot.classList.add('red');
        }
        if (det) det.textContent = detail || status;
    }

    applyStatus('dotSqlite', 'detailSqlite', dbStatus,
        dbStatus === 'healthy' ? 'Metadata DB ready' : dbStatus);
    applyStatus('dotChroma', 'detailChroma', chromaStatus,
        chromaStatus === 'healthy' ? 'Vector store ready' : chromaStatus);
    applyStatus('dotModel', 'detailModel', 'healthy', 'BGE-small (384-dim)');
    applyStatus('dotQueue', 'detailQueue', queueStatus,
        queueStatus === 'healthy' ? `${queueWorkers} worker(s)` : queueStatus);

    document.querySelectorAll('#statusGrid .status-item').forEach(el => el.classList.remove('skeleton'));
}

// ════════════════════════════════════════════════
//  DOCUMENTS
// ════════════════════════════════════════════════

let docsState = {
    all:      [],
    filtered: [],
    page:     1,
};

async function loadDocuments() {
    showDocsLoading(true);
    try {
        const data = await api.getDocuments();
        docsState.all = data.documents || [];
        populateSubjectFilter(docsState.all);
        applyDocFilters();
        setLastUpdated();
    } catch (err) {
        showDocsLoading(false);
        toast('Failed to load documents: ' + err.message, 'error');
    }
}

function populateSubjectFilter(docs) {
    const select = document.getElementById('docSubjectFilter');
    const current = select.value;
    const subjects = [...new Set(docs.map(d => d.subject).filter(Boolean))].sort();
    while (select.options.length > 1) select.remove(1);
    subjects.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s;
        opt.textContent = s;
        select.appendChild(opt);
    });
    if (current) select.value = current;
}

function applyDocFilters() {
    const search  = document.getElementById('docSearch').value.trim().toLowerCase();
    const subject = document.getElementById('docSubjectFilter').value;
    const status  = document.getElementById('docStatusFilter').value;

    docsState.filtered = docsState.all.filter(doc => {
        if (search  && !(doc.filename || '').toLowerCase().includes(search))   return false;
        if (subject && doc.subject !== subject)                                 return false;
        if (status  && (doc.status || '').toLowerCase() !== status.toLowerCase()) return false;
        return true;
    });
    docsState.page = 1;
    renderDocsPage();
}

function renderDocsPage() {
    const { filtered, page } = docsState;
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    const safePage   = Math.min(page, totalPages);
    docsState.page   = safePage;
    const start = (safePage - 1) * PAGE_SIZE;
    const slice = filtered.slice(start, start + PAGE_SIZE);
    const tbody  = document.getElementById('docsTableBody');
    const empty  = document.getElementById('docsEmpty');
    const loading = document.getElementById('docsLoading');

    loading.style.display  = 'none';
    tbody.innerHTML        = '';
    document.getElementById('docCount').textContent = formatNumber(filtered.length);

    if (slice.length === 0) {
        empty.style.display = 'flex';
    } else {
        empty.style.display = 'none';
        slice.forEach(doc => tbody.appendChild(buildDocRow(doc)));
    }

    const pageInfo = document.getElementById('docsPageInfo');
    const prevBtn  = document.getElementById('docsPrev');
    const nextBtn  = document.getElementById('docsNext');
    pageInfo.textContent = `Page ${safePage} of ${totalPages}`;
    prevBtn.disabled = safePage <= 1;
    nextBtn.disabled = safePage >= totalPages;
}

function buildDocRow(doc) {
    const tr = document.createElement('tr');
    tr.dataset.docId = doc.document_id;
    tr.innerHTML = `
        <td class="filename" title="${escapeHtml(doc.filename || '')}">${escapeHtml(doc.filename || '–')}</td>
        <td>${escapeHtml(doc.subject || '–')}</td>
        <td>${statusBadge(doc.status)}</td>
        <td>${escapeHtml(formatDate(doc.created_at || doc.upload_time))}</td>
        <td>${formatNumber(doc.chunk_count)}</td>
        <td>
            <div class="action-group">
                <button class="btn-action view" data-action="view" data-id="${escapeHtml(doc.document_id)}">View</button>
                <button class="btn-action reindex" data-action="reindex" data-id="${escapeHtml(doc.document_id)}"
                    ${doc.status === 'indexing' ? 'disabled' : ''}>Reindex</button>
                <button class="btn-action delete" data-action="delete" data-id="${escapeHtml(doc.document_id)}"
                    data-filename="${escapeHtml(doc.filename || doc.document_id)}"
                    ${doc.status === 'indexing' ? 'disabled' : ''}>Delete</button>
            </div>
        </td>`;
    return tr;
}

function showDocsLoading(show) {
    document.getElementById('docsLoading').style.display  = show ? 'flex' : 'none';
    document.getElementById('docsTableBody').innerHTML    = '';
    document.getElementById('docsEmpty').style.display    = 'none';
}

document.getElementById('docsTableBody').addEventListener('click', async e => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const action = btn.dataset.action;
    const id     = btn.dataset.id;
    if (action === 'view')    { await openDetailModal(id); return; }
    if (action === 'delete')  { openDeleteModal(id, btn.dataset.filename); return; }
    if (action === 'reindex') { await triggerReindex(id, btn); return; }
});

document.getElementById('docSearch').addEventListener('input', debounce(applyDocFilters, 200));
document.getElementById('docSubjectFilter').addEventListener('change', applyDocFilters);
document.getElementById('docStatusFilter').addEventListener('change', applyDocFilters);

document.getElementById('docsPrev').addEventListener('click', () => {
    if (docsState.page > 1) { docsState.page--; renderDocsPage(); }
});
document.getElementById('docsNext').addEventListener('click', () => {
    const total = Math.ceil(docsState.filtered.length / PAGE_SIZE);
    if (docsState.page < total) { docsState.page++; renderDocsPage(); }
});
document.getElementById('docsRefresh').addEventListener('click', () => loadDocuments());

// ════════════════════════════════════════════════
//  DELETE MODAL
// ════════════════════════════════════════════════

let pendingDeleteId = null;

function openDeleteModal(id, filename) {
    pendingDeleteId = id;
    document.getElementById('deleteModalBody').textContent =
        `"${filename}" will be permanently removed from SQLite, ChromaDB, and the FTS index. This action cannot be undone.`;
    document.getElementById('deleteModal').classList.add('open');
    document.getElementById('deleteConfirmBtn').disabled = false;
    document.getElementById('deleteConfirmText').style.display  = '';
    document.getElementById('deleteSpinner').style.display      = 'none';
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('open');
    pendingDeleteId = null;
}

document.getElementById('deleteCancelBtn').addEventListener('click', closeDeleteModal);
document.getElementById('deleteModal').addEventListener('click', e => {
    if (e.target === document.getElementById('deleteModal')) closeDeleteModal();
});

document.getElementById('deleteConfirmBtn').addEventListener('click', async () => {
    if (!pendingDeleteId) return;
    const id = pendingDeleteId;
    const confirmBtn = document.getElementById('deleteConfirmBtn');
    confirmBtn.disabled = true;
    document.getElementById('deleteConfirmText').style.display = 'none';
    document.getElementById('deleteSpinner').style.display     = '';
    try {
        await api.deleteDocument(id);
        toast('Document deleted successfully.', 'success');
        docsState.all      = docsState.all.filter(d => d.document_id !== id);
        docsState.filtered = docsState.filtered.filter(d => d.document_id !== id);
        renderDocsPage();
    } catch (err) {
        toast('Delete failed: ' + err.message, 'error');
        confirmBtn.disabled = false;
        document.getElementById('deleteConfirmText').style.display = '';
        document.getElementById('deleteSpinner').style.display     = 'none';
    } finally {
        closeDeleteModal();
    }
});

// ════════════════════════════════════════════════
//  REINDEX
// ════════════════════════════════════════════════

async function triggerReindex(id, btn) {
    btn.disabled    = true;
    btn.textContent = '…';
    try {
        await api.reindexDocument(id);
        toast('Reindex queued successfully.', 'success');
        const doc = docsState.all.find(d => d.document_id === id);
        if (doc) doc.status = 'indexing';
        applyDocFilters();
    } catch (err) {
        toast('Reindex failed: ' + err.message, 'error');
        btn.disabled    = false;
        btn.textContent = 'Reindex';
    }
}

// ════════════════════════════════════════════════
//  DETAIL MODAL
// ════════════════════════════════════════════════

async function openDetailModal(id) {
    document.getElementById('detailContent').innerHTML =
        '<div class="table-loading"><div class="spinner"></div></div>';
    document.getElementById('detailModal').classList.add('open');
    try {
        const doc = await api.getDocument(id);
        renderDetailContent(doc);
    } catch (err) {
        document.getElementById('detailContent').innerHTML =
            `<div class="empty-state"><p>Failed to load document: ${escapeHtml(err.message)}</p></div>`;
    }
}

function renderDetailContent(doc) {
    document.getElementById('detailModalTitle').textContent = doc.filename || 'Document';
    const fields = [
        { key: 'Document ID',    val: doc.document_id,  mono: true,  full: true },
        { key: 'Filename',       val: doc.filename },
        { key: 'Subject',        val: doc.subject },
        { key: 'Status',         val: doc.status,       badge: true },
        { key: 'Chunk Count',    val: formatNumber(doc.chunk_count) },
        { key: 'File Hash',      val: doc.file_hash,    mono: true,  full: true },
        { key: 'Created',        val: formatDate(doc.created_at || doc.upload_time), full: false },
        { key: 'Updated',        val: formatDate(doc.updated_at) },
    ];
    const html = `<div class="detail-grid">` + fields.map(f => {
        if (!f.val && f.val !== 0) return '';
        const cls = `detail-field${f.full ? ' full' : ''}`;
        const valHtml = f.badge
            ? statusBadge(f.val)
            : `<span class="detail-value${f.mono ? ' mono' : ''}">${escapeHtml(String(f.val))}</span>`;
        return `<div class="${cls}">
            <div class="detail-key">${escapeHtml(f.key)}</div>
            <div>${valHtml}</div>
        </div>`;
    }).join('') + `</div>`;
    document.getElementById('detailContent').innerHTML = html;
}

document.getElementById('detailCloseBtn').addEventListener('click', () => {
    document.getElementById('detailModal').classList.remove('open');
});
document.getElementById('detailModal').addEventListener('click', e => {
    if (e.target === document.getElementById('detailModal'))
        document.getElementById('detailModal').classList.remove('open');
});

// ════════════════════════════════════════════════
//  SUBJECTS
// ════════════════════════════════════════════════

async function loadSubjects() {
    const grid    = document.getElementById('subjectsGrid');
    const empty   = document.getElementById('subjectsEmpty');
    const loading = document.getElementById('subjectsLoading');
    empty.style.display   = 'none';
    loading.style.display = 'flex';
    grid.innerHTML        = '';
    grid.appendChild(loading);
    try {
        const data = await api.getSubjects();
        const subjects = data.subjects || [];
        loading.style.display = 'none';
        if (subjects.length === 0) {
            empty.style.display = 'flex';
        } else {
            const maxDocs = Math.max(...subjects.map(s => s.document_count || 0), 1);
            subjects.forEach(s => grid.appendChild(buildSubjectCard(s, maxDocs)));
        }
        setLastUpdated();
    } catch (err) {
        loading.style.display = 'none';
        empty.style.display   = 'flex';
        toast('Failed to load subjects: ' + err.message, 'error');
    }
}

function buildSubjectCard(subject, maxDocs) {
    const pct = maxDocs > 0 ? Math.round((subject.document_count || 0) / maxDocs * 100) : 0;
    const div = document.createElement('div');
    div.className = 'subject-card';
    div.innerHTML = `
        <div class="subject-name">${escapeHtml(subject.name || subject.subject || '–')}</div>
        <div class="subject-stats">
            <div class="subject-stat">
                <div class="subject-stat-value">${formatNumber(subject.document_count)}</div>
                <div class="subject-stat-label">Documents</div>
            </div>
            <div class="subject-stat">
                <div class="subject-stat-value">${formatNumber(subject.vector_count)}</div>
                <div class="subject-stat-label">Vectors</div>
            </div>
            <div class="subject-stat">
                <div class="subject-stat-value">${formatNumber(subject.chunk_count)}</div>
                <div class="subject-stat-label">Chunks</div>
            </div>
        </div>
        <div class="subject-bar-wrap">
            <div class="subject-bar" style="width: ${pct}%"></div>
        </div>`;
    return div;
}

document.getElementById('subjectsRefresh').addEventListener('click', loadSubjects);

// ════════════════════════════════════════════════
//  HEALTH
// ════════════════════════════════════════════════

async function loadHealth() {
    const healthDiv = document.getElementById('healthDetail');
    const chromaDiv = document.getElementById('chromaCollections');
    healthDiv.innerHTML = '<div class="table-loading"><div class="spinner"></div></div>';
    chromaDiv.innerHTML = '<div class="table-loading"><div class="spinner"></div></div>';
    try {
        const [health, stats] = await Promise.all([api.getHealth(), api.getStats()]);
        renderHealthDetail(health, stats);
        renderChromaCollections();
        setLastUpdated();
    } catch (err) {
        healthDiv.innerHTML = `<div class="empty-state"><p>${escapeHtml(err.message)}</p></div>`;
        chromaDiv.innerHTML = `<div class="empty-state"><p>Could not load ChromaDB data.</p></div>`;
        toast('Failed to load health: ' + err.message, 'error');
    }
}

function renderHealthDetail(health, stats) {
    const rows = [
        {
            label: 'SQLite',
            sub: 'Metadata & FTS5 database',
            status: health.db_status || health.database || 'unknown',
            detail: `${stats.total_documents || 0} documents, ${stats.total_subjects || 0} subjects`,
        },
        {
            label: 'ChromaDB',
            sub: 'Vector store',
            status: health.chroma_status || health.chromadb || 'unknown',
            detail: `${stats.total_vectors || 0} vectors`,
        },
        {
            label: 'Embedding Model',
            sub: 'BAAI/bge-small-en-v1.5',
            status: 'healthy',
            detail: '384 dimensions, CPU',
        },
        {
            label: 'Indexing Queue',
            sub: 'Background workers',
            status: health.queue_status || 'unknown',
            detail: `${health.queue_workers || 0} worker(s) · ${health.queue_pending || 0} pending`,
        },
    ];
    const colorMap = { healthy: 'green', degraded: 'yellow', unhealthy: 'red', unknown: 'grey' };
    const html = `<div class="health-rows">` + rows.map(r => {
        const cls = colorMap[r.status] || 'grey';
        return `<div class="health-row">
            <div class="health-row-left">
                <div class="health-dot ${cls}"></div>
                <div>
                    <div class="health-label">${escapeHtml(r.label)}</div>
                    <div class="health-sub">${escapeHtml(r.sub)}</div>
                </div>
            </div>
            <div class="health-row-right">${escapeHtml(r.detail)}</div>
        </div>`;
    }).join('') + `</div>`;
    document.getElementById('healthDetail').innerHTML = html;
}

async function renderChromaCollections() {
    try {
        const subjectsData = await api.getSubjects();
        const subjects = subjectsData.subjects || [];
        if (subjects.length === 0) {
            document.getElementById('chromaCollections').innerHTML =
                '<div class="empty-state"><p>No subjects found.</p></div>';
            return;
        }
        const rows = subjects.map(s => `
            <tr>
                <td><span class="collection-name">${escapeHtml(s.name)}</span></td>
                <td><span class="vector-count">${formatNumber(s.vector_count)}</span></td>
                <td>${formatNumber(s.document_count)} docs, ${formatNumber(s.chunk_count)} chunks</td>
            </tr>
        `).join('');
        document.getElementById('chromaCollections').innerHTML = `
            <table class="chroma-table">
                <thead><tr><th>Subject</th><th>Vectors</th><th>Documents/Chunks</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
    } catch (err) {
        document.getElementById('chromaCollections').innerHTML =
            `<div class="empty-state"><p>Could not load subject data: ${escapeHtml(err.message)}</p></div>`;
    }
}

document.getElementById('healthRefresh').addEventListener('click', loadHealth);

// ════════════════════════════════════════════════
//  GLOBAL REFRESH
// ════════════════════════════════════════════════

document.getElementById('globalRefresh').addEventListener('click', async () => {
    const btn = document.getElementById('globalRefresh');
    setSpinning(btn, true);
    try {
        const active = document.querySelector('.nav-item.active')?.dataset?.section || 'overview';
        navigateTo(active);
        await new Promise(r => setTimeout(r, 600));
    } finally {
        setSpinning(btn, false);
    }
});

// ════════════════════════════════════════════════
//  DEBOUNCE
// ════════════════════════════════════════════════

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// ════════════════════════════════════════════════
//  KEYBOARD SHORTCUTS
// ════════════════════════════════════════════════

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        document.getElementById('deleteModal').classList.remove('open');
        document.getElementById('detailModal').classList.remove('open');
    }
});

// ════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════

navigateTo('overview');