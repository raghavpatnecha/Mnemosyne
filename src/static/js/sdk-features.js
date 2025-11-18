/**
 * SDK Features Module
 * Handles collection management, document upload, and search mode selection
 */

// State management
const SDKState = {
    currentCollection: null,
    collections: [],
    searchMode: 'hybrid',
    graphEnabled: true
};

// API endpoints
const API = {
    BASE: window.location.origin,
    COLLECTIONS: '/api/collections',
    DOCUMENTS: '/api/documents',
    CHAT: '/api/chat',
    RETRIEVE: '/api/retrieve'
};

// ========== Collection Management ==========

async function loadCollections() {
    try {
        const response = await fetch(`${API.BASE}${API.COLLECTIONS}?limit=100`);
        const data = await response.json();

        if (data.error) {
            console.error('Error loading collections:', data.error);
            showNotification('Failed to load collections', 'error');
            return;
        }

        SDKState.collections = data.collections || [];
        updateCollectionSelector();

        // Set first collection as default if none selected
        if (!SDKState.currentCollection && SDKState.collections.length > 0) {
            SDKState.currentCollection = SDKState.collections[0].id;
        }
    } catch (error) {
        console.error('Failed to fetch collections:', error);
        showNotification('Failed to connect to backend', 'error');
    }
}

function updateCollectionSelector() {
    const selector = document.getElementById('collection-selector');
    if (!selector) return;

    selector.innerHTML = '<option value="">All Collections</option>';

    SDKState.collections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection.id;
        option.textContent = `${collection.name} (${collection.document_count})`;
        if (collection.id === SDKState.currentCollection) {
            option.selected = true;
        }
        selector.appendChild(option);
    });
}

function onCollectionChange(collectionId) {
    SDKState.currentCollection = collectionId || null;
    showNotification(`Switched to: ${collectionId ? getCollectionName(collectionId) : 'All Collections'}`, 'success');
}

function getCollectionName(collectionId) {
    const collection = SDKState.collections.find(c => c.id === collectionId);
    return collection ? collection.name : 'Unknown';
}

async function createCollection() {
    const name = prompt('Enter collection name:');
    if (!name) return;

    const description = prompt('Enter collection description (optional):');

    try {
        const response = await fetch(`${API.BASE}${API.COLLECTIONS}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });

        const data = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
            return;
        }

        showNotification(`Collection "${name}" created successfully!`, 'success');
        await loadCollections();
        SDKState.currentCollection = data.id;
        updateCollectionSelector();
    } catch (error) {
        console.error('Failed to create collection:', error);
        showNotification('Failed to create collection', 'error');
    }
}

async function deleteCurrentCollection() {
    if (!SDKState.currentCollection) {
        showNotification('Please select a collection first', 'warning');
        return;
    }

    const collectionName = getCollectionName(SDKState.currentCollection);
    if (!confirm(`Are you sure you want to delete "${collectionName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`${API.BASE}${API.COLLECTIONS}/${SDKState.currentCollection}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
            return;
        }

        showNotification(`Collection "${collectionName}" deleted`, 'success');
        SDKState.currentCollection = null;
        await loadCollections();
    } catch (error) {
        console.error('Failed to delete collection:', error);
        showNotification('Failed to delete collection', 'error');
    }
}

// ========== Document Upload ==========

async function uploadDocument(file) {
    if (!SDKState.currentCollection) {
        showNotification('Please select a collection first', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('collection_id', SDKState.currentCollection);
    formData.append('file', file);

    showNotification(`Uploading ${file.name}...`, 'info');

    try {
        const response = await fetch(`${API.BASE}${API.DOCUMENTS}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
            return;
        }

        showNotification(`Document "${file.name}" uploaded! Processing...`, 'success');
        monitorDocumentProcessing(data.id);
    } catch (error) {
        console.error('Failed to upload document:', error);
        showNotification('Failed to upload document', 'error');
    }
}

async function uploadURL(url) {
    if (!SDKState.currentCollection) {
        showNotification('Please select a collection first', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('collection_id', SDKState.currentCollection);
    formData.append('url', url);

    showNotification(`Uploading from URL...`, 'info');

    try {
        const response = await fetch(`${API.BASE}${API.DOCUMENTS}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            showNotification(`Error: ${data.error}`, 'error');
            return;
        }

        showNotification(`URL content uploaded! Processing...`, 'success');
        monitorDocumentProcessing(data.id);
    } catch (error) {
        console.error('Failed to upload URL:', error);
        showNotification('Failed to upload URL', 'error');
    }
}

async function monitorDocumentProcessing(documentId) {
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API.BASE}${API.DOCUMENTS}/${documentId}/status`);
            const data = await response.json();

            if (data.status === 'completed') {
                showNotification(`Document processed: ${data.chunk_count} chunks created`, 'success');
                await loadCollections(); // Refresh collection counts
                return true;
            } else if (data.status === 'failed') {
                showNotification(`Processing failed: ${data.error_message}`, 'error');
                return true;
            }

            return false;
        } catch (error) {
            console.error('Failed to check document status:', error);
            return true; // Stop monitoring on error
        }
    };

    // Poll every 3 seconds for up to 5 minutes
    let attempts = 0;
    const maxAttempts = 100;

    const interval = setInterval(async () => {
        attempts++;
        const done = await checkStatus();

        if (done || attempts >= maxAttempts) {
            clearInterval(interval);
            if (attempts >= maxAttempts) {
                showNotification('Processing timeout - check document status later', 'warning');
            }
        }
    }, 3000);
}

function showUploadDialog() {
    const dialog = document.getElementById('upload-dialog');
    if (dialog) {
        dialog.style.display = 'flex';
    }
}

function hideUploadDialog() {
    const dialog = document.getElementById('upload-dialog');
    if (dialog) {
        dialog.style.display = 'none';
    }
}

function handleFileSelect(event) {
    const files = event.target.files;
    for (let file of files) {
        uploadDocument(file);
    }
    event.target.value = ''; // Reset file input
}

function handleURLUpload() {
    const input = document.getElementById('url-input');
    const url = input.value.trim();

    if (!url) {
        showNotification('Please enter a URL', 'warning');
        return;
    }

    uploadURL(url);
    input.value = '';
    hideUploadDialog();
}

// ========== Search Mode Selection ==========

function updateSearchMode(mode) {
    SDKState.searchMode = mode;
    document.querySelectorAll('.mode-option').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelector(`.mode-option[data-mode="${mode}"]`)?.classList.add('active');
    showNotification(`Search mode: ${mode.toUpperCase()}`, 'info');
}

function toggleGraphEnhancement() {
    SDKState.graphEnabled = !SDKState.graphEnabled;
    const toggle = document.getElementById('graph-toggle');
    if (toggle) {
        toggle.classList.toggle('active', SDKState.graphEnabled);
    }
    showNotification(`Graph enhancement: ${SDKState.graphEnabled ? 'ON' : 'OFF'}`, 'info');
}

function getSearchParams() {
    return {
        collection_id: SDKState.currentCollection,
        mode: SDKState.searchMode,
        enable_graph: SDKState.graphEnabled
    };
}

// ========== Notifications ==========

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container') || createNotificationContainer();

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    container.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'notification-container';
    container.className = 'notification-container';
    document.body.appendChild(container);
    return container;
}

// ========== Initialization ==========

function initSDKFeatures() {
    // Load collections on startup
    loadCollections();

    // Set up event listeners
    const collectionSelector = document.getElementById('collection-selector');
    if (collectionSelector) {
        collectionSelector.addEventListener('change', (e) => onCollectionChange(e.target.value));
    }

    const createBtn = document.getElementById('create-collection-btn');
    if (createBtn) {
        createBtn.addEventListener('click', createCollection);
    }

    const deleteBtn = document.getElementById('delete-collection-btn');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteCurrentCollection);
    }

    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', showUploadDialog);
    }

    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }

    const urlSubmit = document.getElementById('url-submit-btn');
    if (urlSubmit) {
        urlSubmit.addEventListener('click', handleURLUpload);
    }

    const closeUpload = document.getElementById('close-upload-dialog');
    if (closeUpload) {
        closeUpload.addEventListener('click', hideUploadDialog);
    }

    // Search mode options
    document.querySelectorAll('.mode-option').forEach(el => {
        el.addEventListener('click', () => updateSearchMode(el.dataset.mode));
    });

    const graphToggle = document.getElementById('graph-toggle');
    if (graphToggle) {
        graphToggle.addEventListener('click', toggleGraphEnhancement);
    }

    // Initialize default search mode
    updateSearchMode('hybrid');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSDKFeatures);
} else {
    initSDKFeatures();
}
