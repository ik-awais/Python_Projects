'use strict';

let currentSessionId = null;

// ── Auto-resize textarea ────────────────────────
const questionInput = document.getElementById('questionInput');
questionInput.addEventListener('input', () => {
    questionInput.style.height = 'auto';
    questionInput.style.height = Math.min(questionInput.scrollHeight, 160) + 'px';
});

// ── Load subjects ───────────────────────────────
async function loadSubjects() {
    try {
        const res = await fetch('/subjects');
        if (!res.ok) return;
        const subjects = await res.json();
        const select = document.getElementById('subjectSelect');
        subjects.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load subjects:', e);
    }
}

// ── Chip suggestion fill ────────────────────────
function fillQuestion(btn) {
    questionInput.value = btn.textContent;
    questionInput.focus();
    questionInput.dispatchEvent(new Event('input'));
}

// ── Render helpers ──────────────────────────────
function getHistory() {
    return document.getElementById('chatHistory');
}

function clearWelcome() {
    const w = getHistory().querySelector('.welcome-screen');
    if (w) w.remove();
}

function addUserMessage(text) {
    clearWelcome();
    const row = document.createElement('div');
    row.className = 'message-row user';
    row.innerHTML = `<div class="bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
    getHistory().appendChild(row);
    scrollBottom();
}

function addAssistantMessage(text, citations) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `<div class="bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
    getHistory().appendChild(row);

    if (citations && citations.length > 0) {
        const citDiv = document.createElement('div');
        citDiv.className = 'citations';
        const tags = citations.map(c => {
            const label = c.filename
                ? `${c.filename}${c.page ? ' · p.' + c.page : ''}`
                : JSON.stringify(c);
            return `<span class="citation-tag">${escapeHtml(label)}</span>`;
        }).join('');
        citDiv.innerHTML = `<div class="citations-inner"><span class="citations-label">Sources</span>${tags}</div>`;
        getHistory().appendChild(citDiv);
    }

    scrollBottom();
}

function addErrorMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    row.innerHTML = `<div class="bubble error-bubble">${escapeHtml(text)}</div>`;
    getHistory().appendChild(row);
    scrollBottom();
}

function showLoading() {
    const div = document.createElement('div');
    div.className = 'loading-row';
    div.id = 'loadingIndicator';
    div.innerHTML = `
        <div class="loading-bubble">
            <div class="dots"><span></span><span></span><span></span></div>
            Thinking…
        </div>`;
    getHistory().appendChild(div);
    scrollBottom();
}

function hideLoading() {
    const el = document.getElementById('loadingIndicator');
    if (el) el.remove();
}

function scrollBottom() {
    const h = getHistory();
    h.scrollTop = h.scrollHeight;
}

function escapeHtml(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── Send question ───────────────────────────────
async function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    const subject = document.getElementById('subjectSelect').value;
    const sendBtn = document.getElementById('sendBtn');

    sendBtn.disabled = true;
    questionInput.disabled = true;

    addUserMessage(question);
    questionInput.value = '';
    questionInput.style.height = 'auto';
    showLoading();

    try {
        const payload = { question };
        if (subject) payload.subject = subject;
        if (currentSessionId) payload.session_id = currentSessionId;

        const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.session_id) currentSessionId = data.session_id;

        hideLoading();
        addAssistantMessage(data.answer || 'No answer returned.', data.citations || []);

    } catch (err) {
        hideLoading();
        addErrorMessage('Something went wrong. Please try again.');
        console.error(err);
    } finally {
        sendBtn.disabled = false;
        questionInput.disabled = false;
        questionInput.focus();
    }
}

// ── New chat ────────────────────────────────────
function newChat() {
    currentSessionId = null;
    getHistory().innerHTML = `
        <div class="welcome-screen">
            <div class="welcome-icon">◈</div>
            <h2 class="welcome-title">What would you like to learn?</h2>
            <p class="welcome-sub">Select a subject from the sidebar or ask across all your materials.</p>
            <div class="suggestion-chips">
                <button class="chip" onclick="fillQuestion(this)">Summarize key concepts</button>
                <button class="chip" onclick="fillQuestion(this)">Explain this topic in simple terms</button>
                <button class="chip" onclick="fillQuestion(this)">What are the main differences between...</button>
            </div>
        </div>`;
}

// ── Event listeners ─────────────────────────────
document.getElementById('sendBtn').addEventListener('click', sendQuestion);

questionInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuestion();
    }
});

document.getElementById('newChatBtn').addEventListener('click', newChat);

// ── Init ────────────────────────────────────────
loadSubjects();