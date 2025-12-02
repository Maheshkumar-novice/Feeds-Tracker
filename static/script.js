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

// Init
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
    }
};

// Close sidebar when clicking a feed on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (e.target.closest('.feed') && !e.target.closest('.feed-delete')) {
            sidebar.classList.remove('open');
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
                <div class="feed-name">${f.title || 'Untitled'}</div>
            </div>
        </div>
    `).join('');

    updateActiveStates();
}

async function addFeed() {
    const url = newFeedUrl.value.trim();
    if (!url) return;

    try {
        const res = await fetch('/api/feeds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(err.error || 'Failed to add feed');
            return;
        }

        newFeedUrl.value = '';
        await loadFeeds();
        renderManageFeeds();

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
                <div class="manage-feed-title">${f.title || 'Untitled'}</div>
                <div class="manage-feed-url">${f.url}</div>
            </div>
            <button class="btn-delete" onclick="deleteFeedFromManage(${f.id}, '${(f.title || 'Untitled').replace(/'/g, "&apos;")}')">Delete</button>
        </div>
    `).join('');
}

async function deleteFeedFromManage(id, title) {
    if (!confirm(`Delete "${title}"?`)) return;

    await fetch(`/api/feeds/${id}`, { method: 'DELETE' });
    await loadFeeds();
    renderManageFeeds();
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
        <div class="article ${a.read ? 'read' : ''}" onclick="openArticle(${a.id}, '${a.link}')">
            <div class="article-top">
                <div class="article-title">${a.title}</div>
            </div>
            <div class="article-meta">${!currentFeedId && a.feed_title ? a.feed_title + ' • ' : ''}${formatDate(a.published)}</div>
            ${a.description ? `<div class="article-excerpt">${stripTags(a.description).substring(0, 150)}...</div>` : ''}
        </div>
    `).join('');
}

async function openArticle(id, link) {
    // Mark as read
    await fetch(`/api/articles/${id}/read`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: true })
    });

    // Open in new tab
    window.open(link, '_blank');

    // Update UI
    const article = articles.find(a => a.id === id);
    if (article) article.read = true;
    renderArticles();
    loadFeeds(); // Update unread counts
}

async function refreshAll() {
    refreshAllBtn.textContent = 'Refreshing...';
    refreshAllBtn.disabled = true;

    for (const feed of feeds) {
        try {
            await fetch(`/api/feeds/${feed.id}/refresh`, { method: 'POST' });
        } catch (err) {
            console.error('Error refreshing:', err);
        }
    }

    refreshAllBtn.textContent = 'Refresh All';
    refreshAllBtn.disabled = false;

    await loadFeeds();
    renderManageFeeds();
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
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || '';
}

function toggleSidebar() {
    sidebar.classList.toggle('open');
}
