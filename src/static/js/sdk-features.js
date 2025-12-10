/**
 * SDK Features Module
 * Handles collections, documents, API key management, and uploads
 */

// State
const AppState = {
    apiConfigured: false,
    currentCollection: null,
    collections: [],
    documents: []
};

// API Base
const API_BASE = window.location.origin;

// ========== Initialization ==========

async function initApp() {
    // Check API status
    await checkApiStatus();

    // Load collections if configured
    if (AppState.apiConfigured) {
        await loadCollections();
    }

    // Setup event listeners
    setupEventListeners();
}

function setupEventListeners() {
    // Settings buttons (overlay and page header)
    document.getElementById('overlay-settings-btn')?.addEventListener('click', openSettingsModal);
    document.getElementById('page-settings-btn')?.addEventListener('click', openSettingsModal);
    document.getElementById('generate-key-btn')?.addEventListener('click', openSettingsModal);
    document.getElementById('save-api-key-btn')?.addEventListener('click', saveApiKey);
    document.getElementById('register-btn')?.addEventListener('click', registerAndGenerateKey);

    // Collections
    document.getElementById('new-collection-btn')?.addEventListener('click', openCollectionModal);
    document.getElementById('create-collection-btn')?.addEventListener('click', createCollection);

    // Upload
    document.getElementById('upload-doc-btn')?.addEventListener('click', openUploadModal);
    document.getElementById('url-upload-btn')?.addEventListener('click', uploadFromUrl);

    // Dropzone
    const dropzone = document.getElementById('upload-dropzone');
    const fileInput = document.getElementById('file-input');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', handleDragOver);
        dropzone.addEventListener('dragleave', handleDragLeave);
        dropzone.addEventListener('drop', handleDrop);
        fileInput.addEventListener('change', handleFileSelect);
    }

    // Modal close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.style.display = 'none';
            }
        });
    });
}

// ========== API Status ==========

async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/setup/status`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();

        AppState.apiConfigured = data.configured;
        updateSetupUI(data.configured);
        updateApiStatusUI(data.configured);

        return data.configured;
    } catch (error) {
        console.error('Failed to check API status:', error);
        AppState.apiConfigured = false;
        updateSetupUI(false);
        updateApiStatusUI(false);
        return false;
    }
}

function updateSetupUI(configured) {
    const notConfigured = document.getElementById('setup-not-configured');
    const isConfigured = document.getElementById('setup-configured');

    if (notConfigured && isConfigured) {
        notConfigured.style.display = configured ? 'none' : 'block';
        isConfigured.style.display = configured ? 'block' : 'none';
    }
}

function updateApiStatusUI(connected) {
    const statusEl = document.getElementById('api-status');
    if (statusEl) {
        statusEl.className = `api-status ${connected ? 'connected' : 'disconnected'}`;
        statusEl.querySelector('.status-text').textContent = connected ? 'Connected' : 'Not configured';
    }
}

// ========== Settings Modal ==========

function openSettingsModal() {
    document.getElementById('settings-modal').style.display = 'flex';
    checkApiStatus();
}

function closeSettingsModal() {
    document.getElementById('settings-modal').style.display = 'none';
}

function toggleApiKeyVisibility() {
    const input = document.getElementById('api-key-input');
    const btn = event.target;

    if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = 'Hide';
    } else {
        input.type = 'password';
        btn.textContent = 'Show';
    }
}

async function saveApiKey() {
    const apiKey = document.getElementById('api-key-input').value.trim();

    if (!apiKey) {
        showNotification('Please enter an API key', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/setup/configure`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        const data = await response.json();

        if (!response.ok) {
            showNotification(data.error || `Failed: HTTP ${response.status}`, 'error');
            return;
        }

        if (data.configured) {
            showNotification('API key configured successfully!', 'success');
            AppState.apiConfigured = true;
            updateSetupUI(true);
            updateApiStatusUI(true);
            closeSettingsModal();

            // Load collections and documents after configuring API key
            try {
                await loadCollections();
                // If there's a current collection, also load its documents
                if (AppState.currentCollection) {
                    await loadDocuments(AppState.currentCollection);
                }
            } catch (e) {
                console.error('Failed to load collections after config:', e);
                showNotification('API configured, but failed to load collections. Try refreshing the page.', 'warning');
            }
        } else {
            showNotification(data.error || 'Failed to configure API key', 'error');
        }
    } catch (error) {
        console.error('Save API key error:', error);
        showNotification('Failed to save API key: ' + error.message, 'error');
    }
}

async function registerAndGenerateKey() {
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;

    if (!email || !password) {
        showNotification('Please enter email and password', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/setup/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (data.api_key) {
            // Put the API key in the input box for user to see/copy
            const apiKeyInput = document.getElementById('api-key-input');
            apiKeyInput.value = data.api_key;
            apiKeyInput.type = 'text'; // Show the key so user can see it

            // Clear registration fields
            document.getElementById('register-email').value = '';
            document.getElementById('register-password').value = '';

            showNotification('API key generated! Click "Save API Key" to configure.', 'success');
        } else {
            showNotification(data.error || 'Registration failed', 'error');
        }
    } catch (error) {
        showNotification('Registration failed', 'error');
    }
}

// ========== Collections ==========

async function loadCollections() {
    if (!AppState.apiConfigured) return;

    try {
        const response = await fetch(`${API_BASE}/api/collections?limit=100`);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Error loading collections:', response.status, errorData);
            const errorMsg = errorData.error || `Failed to load collections: HTTP ${response.status}`;
            const errorType = errorData.type ? ` (${errorData.type})` : '';
            showNotification(errorMsg + errorType, 'error');
            return;
        }

        const data = await response.json();

        if (data.error) {
            console.error('Error loading collections:', data.error);
            showNotification(data.error, 'error');
            return;
        }

        AppState.collections = data.collections || [];
        renderCollections();

        // Select first collection if none selected
        if (!AppState.currentCollection && AppState.collections.length > 0) {
            selectCollection(AppState.collections[0].id);
        }
    } catch (error) {
        console.error('Failed to load collections:', error);
        showNotification('Failed to load collections: ' + error.message, 'error');
    }
}

function renderCollections() {
    const container = document.getElementById('collections-list');
    if (!container) return;

    // Update documents section visibility based on collections
    updateDocumentsSectionVisibility();

    if (AppState.collections.length === 0) {
        container.innerHTML = '<div class="empty-state">Create your first collection to start uploading your documents</div>';
        return;
    }

    container.innerHTML = AppState.collections.map(c => `
        <div class="collection-item ${c.id === AppState.currentCollection ? 'active' : ''}"
             onclick="selectCollection('${c.id}')">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <use xlink:href="#icon-folder"></use>
            </svg>
            <div class="item-info">
                <div class="item-name">${escapeHtml(c.name)}</div>
                <div class="item-meta">${c.document_count || 0} documents</div>
            </div>
        </div>
    `).join('');
}

async function selectCollection(collectionId) {
    AppState.currentCollection = collectionId;
    renderCollections();
    await loadDocuments(collectionId);
}

function openCollectionModal() {
    if (!AppState.apiConfigured) {
        showNotification('Please configure your API key first', 'warning');
        openSettingsModal();
        return;
    }
    document.getElementById('collection-modal').style.display = 'flex';
}

function closeCollectionModal() {
    document.getElementById('collection-modal').style.display = 'none';
    document.getElementById('collection-name').value = '';
    document.getElementById('collection-desc').value = '';
}

async function createCollection() {
    const name = document.getElementById('collection-name').value.trim();
    const description = document.getElementById('collection-desc').value.trim();

    if (!name) {
        showNotification('Please enter a collection name', 'warning');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/collections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });

        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }

        showNotification(`Collection "${name}" created!`, 'success');
        closeCollectionModal();
        await loadCollections();
        selectCollection(data.id);
    } catch (error) {
        showNotification('Failed to create collection', 'error');
    }
}

// ========== Documents ==========

async function loadDocuments(collectionId) {
    if (!collectionId) {
        renderDocuments([]);
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/documents?collection_id=${collectionId}&limit=100`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading documents:', data.error);
            return;
        }

        AppState.documents = data.documents || [];
        renderDocuments(AppState.documents);
    } catch (error) {
        console.error('Failed to load documents:', error);
    }
}

function renderDocuments(documents) {
    const container = document.getElementById('documents-list');
    if (!container) return;

    if (!AppState.currentCollection) {
        container.innerHTML = '<div class="empty-state">Select a collection</div>';
        return;
    }

    if (documents.length === 0) {
        container.innerHTML = '<div class="empty-state">No documents yet</div>';
        return;
    }

    container.innerHTML = documents.map(d => `
        <div class="document-item">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <use xlink:href="#icon-file"></use>
            </svg>
            <div class="item-info">
                <div class="item-name">${escapeHtml(d.title || d.filename || 'Document')}</div>
                <div class="item-meta">${d.filename || ''}</div>
            </div>
            <span class="item-status ${d.status}">${d.status}</span>
        </div>
    `).join('');
}

// ========== Upload ==========

function openUploadModal() {
    if (!AppState.apiConfigured) {
        showNotification('Please configure your API key first', 'warning');
        openSettingsModal();
        return;
    }
    if (!AppState.currentCollection) {
        showNotification('Please select or create a collection first', 'warning');
        return;
    }
    document.getElementById('upload-modal').style.display = 'flex';
}

function closeUploadModal() {
    document.getElementById('upload-modal').style.display = 'none';
    document.getElementById('upload-queue').innerHTML = '';
    document.getElementById('url-input').value = '';
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFiles(files);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFiles(files);
    }
}

function handleFiles(files) {
    for (const file of files) {
        uploadFile(file);
    }
}

async function uploadFile(file) {
    const queue = document.getElementById('upload-queue');
    const itemId = `upload-${Date.now()}`;

    // Add to queue UI
    queue.innerHTML += `
        <div class="upload-item" id="${itemId}">
            <div class="upload-item-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <use xlink:href="#icon-file"></use>
                </svg>
            </div>
            <div class="upload-item-info">
                <div class="upload-item-name">${escapeHtml(file.name)}</div>
                <div class="upload-item-size">${formatFileSize(file.size)} - Uploading...</div>
            </div>
        </div>
    `;

    const formData = new FormData();
    formData.append('collection_id', AppState.currentCollection);
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/api/documents`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        const itemEl = document.getElementById(itemId);

        if (data.error) {
            if (itemEl) {
                itemEl.querySelector('.upload-item-size').textContent = 'Failed';
                itemEl.style.background = '#fef2f2';
            }
            showNotification(`Failed to upload ${file.name}`, 'error');
        } else {
            if (itemEl) {
                itemEl.querySelector('.upload-item-size').textContent = 'Processing...';
            }
            showNotification(`${file.name} uploaded!`, 'success');

            // Monitor processing
            monitorDocumentStatus(data.id, itemId);
        }
    } catch (error) {
        showNotification(`Failed to upload ${file.name}`, 'error');
    }
}

async function uploadFromUrl() {
    const url = document.getElementById('url-input').value.trim();

    if (!url) {
        showNotification('Please enter a URL', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('collection_id', AppState.currentCollection);
    formData.append('url', url);

    try {
        const response = await fetch(`${API_BASE}/api/documents`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showNotification(data.error, 'error');
        } else {
            showNotification('URL content uploaded! Processing...', 'success');
            document.getElementById('url-input').value = '';
            monitorDocumentStatus(data.id);
        }
    } catch (error) {
        showNotification('Failed to upload URL', 'error');
    }
}

async function monitorDocumentStatus(documentId, itemId) {
    let attempts = 0;
    const maxAttempts = 60;

    const check = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/documents/${documentId}/status`);
            const data = await response.json();

            const itemEl = itemId ? document.getElementById(itemId) : null;

            if (data.status === 'completed') {
                if (itemEl) {
                    itemEl.querySelector('.upload-item-size').textContent = `${data.chunk_count} chunks`;
                    itemEl.style.background = '#f0fdf4';
                }
                await loadDocuments(AppState.currentCollection);
                await loadCollections();
                return true;
            } else if (data.status === 'failed') {
                if (itemEl) {
                    itemEl.querySelector('.upload-item-size').textContent = 'Failed';
                    itemEl.style.background = '#fef2f2';
                }
                showNotification(`Processing failed: ${data.error_message}`, 'error');
                return true;
            }

            return false;
        } catch (error) {
            return false;
        }
    };

    const interval = setInterval(async () => {
        attempts++;
        const done = await check();

        if (done || attempts >= maxAttempts) {
            clearInterval(interval);
        }
    }, 3000);
}

// ========== Utilities ==========

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    container.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// ========== UI Visibility ==========

function updateDocumentsSectionVisibility() {
    const docsWrapper = document.getElementById('documents-section-wrapper');
    if (docsWrapper) {
        if (AppState.collections.length > 0) {
            docsWrapper.classList.add('visible');
        } else {
            docsWrapper.classList.remove('visible');
        }
    }
}

// ========== Search Integration ==========

function getSearchParams() {
    return {
        collection_id: AppState.currentCollection,
        mode: 'hybrid',
        enable_graph: true
    };
}

// Expose to global scope for search.js integration
window.SDKState = AppState;
window.getSearchParams = getSearchParams;

// Initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
