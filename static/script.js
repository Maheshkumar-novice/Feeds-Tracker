// State
let feeds = [];
let articles = [];
let currentFeedId = null;
let isManageView = false;

// DOM
const feedsList = document.getElementById('feedsList');
const articlesList = document.getElementById('articlesList');
const manageFeedsView = document.getElementById('manageFeedsView');
const feedsManageList = document.getElementById('feedsManageList');
const feedTitle = document.getElementById('feedTitle');
const newFeedUrl = document.getElementById('newFeedUrl');
const addNewFeed = document.getElementById('addNewFeed');
const refreshAllBtn = document.getElementById('refreshAllBtn');
const menuBtn = document.getElementById('menuBtn');
const closeSidebarBtn = document.getElementById('closeSidebarBtn');
const appTitle = document.getElementById('appTitle');
const sidebar = document.querySelector('.sidebar');

// Auth
let authToken = localStorage.getItem('authToken');
let authRequired = false;

async function checkAuthRequirement() {
    try {
        const res = await fetch('/api/config');
        const config = await res.json();
        authRequired = config.auth_required;
        updateAuthState();
    } catch (e) {
        console.error('Failed to check auth config', e);
    }
}

async function toggleAuth() {
    if (authToken) {
        if (confirm('Logout?')) {
            authToken = null;
            localStorage.removeItem('authToken');
            updateAuthState();
        }
    } else {
        const token = prompt('Enter admin token:');
        if (!token) return;

        try {
            // Verify token with backend
            const res = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (res.ok) {
                authToken = token;
                localStorage.setItem('authToken', token);
                updateAuthState();
            } else {
                alert('Invalid token');
            }
        } catch (e) {
            alert('Error verifying token');
            console.error(e);
        }
    }
}

function updateAuthState() {
    const authBtn = document.getElementById('authBtn');
    const authBtnText = document.getElementById('authBtnText');
    const manageFeed = document.getElementById('manageFeed');
    const addNewFeedContainer = document.querySelector('.add-feed-section');
    const refreshAllBtn = document.getElementById('refreshAllBtn');

    // If auth is NOT required by backend, show everything and hide login button
    if (!authRequired) {
        authBtn.style.display = 'none';
        manageFeed.style.display = 'block';
        addNewFeedContainer.style.display = 'flex';
        refreshAllBtn.style.display = 'block';
        document.body.classList.add('authenticated');
        return;
    }

    // Auth IS required
    authBtn.style.display = 'block';

    if (authToken) {
        authBtnText.textContent = '🔓 Logout';
        manageFeed.style.display = 'block';
        addNewFeedContainer.style.display = 'flex';
        refreshAllBtn.style.display = 'block';
        document.body.classList.add('authenticated');
    } else {
        authBtnText.textContent = '🔒 Login';
        manageFeed.style.display = 'none';
        addNewFeedContainer.style.display = 'none';
        refreshAllBtn.style.display = 'none';
        document.body.classList.remove('authenticated');

        // If in manage view, go back to home
        if (isManageView) {
            appTitle.click();
        }
    }
}

// Helper for authenticated fetch
async function authFetch(url, options = {}) {
    if (!authToken) return null;

    const headers = options.headers || {};
    headers['Authorization'] = `Bearer ${authToken}`;
    options.headers = headers;

    const res = await fetch(url, options);

    if (res.status === 401) {
        alert('Session expired or invalid token');
        authToken = null;
        localStorage.removeItem('authToken');
        updateAuthState();
        return null;
    }

    return res;
}

// Init
checkAuthRequirement();
loadFeeds();
loadAllArticles(); // Load all articles on startup

// Events
addNewFeed.onclick = addFeed;
newFeedUrl.onkeypress = (e) => e.key === 'Enter' && addFeed();
refreshAllBtn.onclick = refreshAll;
menuBtn.onclick = toggleSidebar;
closeSidebarBtn.onclick = toggleSidebar;
appTitle.onclick = () => {
    isManageView = false;
    articlesList.style.display = 'block';
    manageFeedsView.style.display = 'none';
    loadAllArticles();
    renderFeeds();
    updateActiveStates();

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('open');
        document.getElementById('sidebarOverlay').classList.remove('active');
    }
};

// Close sidebar when clicking a feed on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (e.target.closest('.feed') && !e.target.closest('.feed-delete')) {
            sidebar.classList.remove('open');
            document.getElementById('sidebarOverlay').classList.remove('active');
        }
    }
});

// Functions
async function loadFeeds() {
    const res = await fetch('/api/feeds');
    feeds = await res.json();
    renderFeeds();
}

function renderFeeds() {
    if (!feeds.length) {
        feedsList.innerHTML = '<div class="empty">No feeds yet<br>Click "Manage Feeds"</div>';
        return;
    }

    feedsList.innerHTML = feeds.map(f => `
        <div class="feed" onclick="selectFeed(${f.id})">
            <div class="feed-info">
                <div class="feed-name">${escapeHtml(f.title || 'Untitled')}</div>
            </div>
        </div>
    `).join('');

    updateActiveStates();
}

async function addFeed() {
    const url = newFeedUrl.value.trim();
    if (!url) return;

    try {
        const res = await authFetch('/api/feeds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!res) return; // Auth failed

        if (!res.ok) {
            const err = await res.json();
            alert(err.error || 'Failed to add feed');
            return;
        }

        newFeedUrl.value = '';
        await loadFeeds();
        if (isManageView) renderManageFeeds();

    } catch (err) {
        alert('Error: ' + err.message);
    }
}

function selectFeed(id) {
    isManageView = false;
    currentFeedId = id;

    const feed = feeds.find(f => f.id === id);
    if (feed) {
        feedTitle.textContent = feed.title || 'Untitled';
        loadArticles(id);
    }

    articlesList.style.display = 'block';
    manageFeedsView.style.display = 'none';
    renderFeeds();
    updateActiveStates();
}

function showManageFeeds() {
    isManageView = true;
    currentFeedId = null;

    feedTitle.textContent = 'Manage Feeds';
    articlesList.style.display = 'none';
    manageFeedsView.style.display = 'block';

    renderManageFeeds();
    updateActiveStates();
}

function renderManageFeeds() {
    if (!feeds.length) {
        feedsManageList.innerHTML = '<div class="empty">No feeds yet</div>';
        return;
    }

    feedsManageList.innerHTML = feeds.map(f => `
        <div class="manage-feed-item">
            <div class="manage-feed-info">
                <div class="manage-feed-title">${escapeHtml(f.title || 'Untitled')}</div>
                <div class="manage-feed-url">${escapeHtml(f.url)}</div>
            </div>
            <button class="btn-delete" onclick="deleteFeedFromManage(${f.id}, '${escapeHtml(f.title || 'Untitled').replace(/'/g, "\\'")}')">Delete</button>
        </div>
    `).join('');
}

async function deleteFeedFromManage(id, title) {
    if (!confirm(`Delete "${title}"?`)) return;

    const res = await authFetch(`/api/feeds/${id}`, { method: 'DELETE' });
    if (res && res.ok) {
        await loadFeeds();
        renderManageFeeds();
    }
}

function updateActiveStates() {
    // Update feed list active states
    document.querySelectorAll('.feeds .feed').forEach(f => f.classList.remove('active'));
    if (!isManageView && currentFeedId) {
        const activeFeed = document.querySelector(`.feeds .feed[onclick*="${currentFeedId}"]`);
        if (activeFeed) activeFeed.classList.add('active');
    }

    // Update manage feed active state
    const manageFeed = document.getElementById('manageFeed');
    if (manageFeed) {
        manageFeed.classList.toggle('active', isManageView);
    }
}

async function loadArticles(feedId) {
    const res = await fetch(`/api/articles?feed_id=${feedId}&limit=50`);
    articles = await res.json();
    renderArticles();
}

async function loadAllArticles() {
    feedTitle.textContent = 'Recent Articles';
    currentFeedId = null;
    const res = await fetch(`/api/articles?limit=100`);
    articles = await res.json();
    renderArticles();
}

function renderArticles() {
    if (!articles.length) {
        articlesList.innerHTML = '<div class="empty">No articles</div>';
        return;
    }

    articlesList.innerHTML = articles.map(a => `
        <div class="article" onclick="openArticle(${a.id}, '${escapeHtml(a.link)}')">
            <div class="article-top">
                <div class="article-title">${escapeHtml(a.title)}</div>
            </div>
            <div class="article-meta">${!currentFeedId && a.feed_title ? escapeHtml(a.feed_title) + ' • ' : ''}${formatDate(a.published)}</div>
            ${a.description ? `<div class="article-excerpt">${escapeHtml(stripTags(a.description)).substring(0, 150)}...</div>` : ''}
        </div>
    `).join('');
}

async function openArticle(id, link) {
    // Open in new tab
    window.open(link, '_blank');
}

async function refreshAll() {
    refreshAllBtn.textContent = 'Refreshing...';
    refreshAllBtn.disabled = true;

    for (const feed of feeds) {
        try {
            await authFetch(`/api/feeds/${feed.id}/refresh`, { method: 'POST' });
        } catch (err) {
            console.error('Error refreshing:', err);
        }
    }

    refreshAllBtn.textContent = 'Refresh All';
    refreshAllBtn.disabled = false;

    await loadFeeds();
    if (isManageView) renderManageFeeds();
}

function formatDate(dateStr) {
    if (!dateStr) return '';

    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function stripTags(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || '';
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function toggleSidebar() {
    sidebar.classList.toggle('open');
    document.getElementById('sidebarOverlay').classList.toggle('active');
}

// Close sidebar when clicking overlay
document.getElementById('sidebarOverlay').onclick = toggleSidebar;
