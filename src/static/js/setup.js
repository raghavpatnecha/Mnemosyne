/**
 * Setup Module
 * Handles SDK configuration, user registration, and API key management
 */

// State management for setup
const SetupState = {
    configured: false,
    hasApiKey: false,
    backendUrl: ''
};

// Initialize setup check on page load
window.addEventListener('DOMContentLoaded', async () => {
    await checkSetupStatus();
    initializeSetupModal();
});

/**
 * Check if SDK is configured and show setup modal if needed
 */
async function checkSetupStatus() {
    try {
        const response = await fetch('/api/setup/status');
        const data = await response.json();

        SetupState.configured = data.configured;
        SetupState.hasApiKey = data.has_api_key;
        SetupState.backendUrl = data.backend_url;

        if (!SetupState.configured) {
            showSetupModal();
        }
    } catch (error) {
        console.error('Failed to check setup status:', error);
    }
}

/**
 * Initialize setup modal and event listeners
 */
function initializeSetupModal() {
    const modalHTML = `
        <div id="setup-modal" class="modal-overlay setup-modal" style="display: none;">
            <div class="modal-content setup-content">
                <div class="modal-header">
                    <h2>Welcome to Mnemosyne</h2>
                    <p class="setup-subtitle">Setup required to get started</p>
                </div>
                <div class="modal-body">
                    <div class="setup-tabs">
                        <button class="setup-tab active" data-tab="register">New User</button>
                        <button class="setup-tab" data-tab="configure">Have API Key</button>
                    </div>

                    <!-- Register Tab -->
                    <div id="register-tab" class="setup-tab-content active">
                        <p class="setup-info">Create an account to get your API key</p>
                        <form id="register-form" class="setup-form">
                            <div class="form-group">
                                <label for="register-email">Email</label>
                                <input type="email" id="register-email" required
                                       placeholder="your@email.com" autocomplete="email">
                            </div>
                            <div class="form-group">
                                <label for="register-password">Password</label>
                                <input type="password" id="register-password" required
                                       placeholder="Choose a secure password"
                                       autocomplete="new-password" minlength="8">
                                <small>Minimum 8 characters</small>
                            </div>
                            <div class="form-group">
                                <label for="register-password-confirm">Confirm Password</label>
                                <input type="password" id="register-password-confirm" required
                                       placeholder="Confirm your password"
                                       autocomplete="new-password">
                            </div>
                            <button type="submit" class="toolbar-btn primary">
                                Register & Get API Key
                            </button>
                        </form>
                        <div id="register-result" class="setup-result" style="display: none;"></div>
                    </div>

                    <!-- Configure Tab -->
                    <div id="configure-tab" class="setup-tab-content">
                        <p class="setup-info">Enter your existing API key</p>
                        <form id="configure-form" class="setup-form">
                            <div class="form-group">
                                <label for="api-key-input">API Key</label>
                                <input type="text" id="api-key-input" required
                                       placeholder="mn_test_..." autocomplete="off">
                                <small>Your API key starts with "mn_test_"</small>
                            </div>
                            <button type="submit" class="toolbar-btn primary">
                                Configure
                            </button>
                        </form>
                        <div id="configure-result" class="setup-result" style="display: none;"></div>
                    </div>

                    <div class="setup-footer">
                        <p><strong>Backend:</strong> <code>${SetupState.backendUrl}</code></p>
                        <p class="setup-note">Make sure the FastAPI backend is running</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Setup event listeners
    document.querySelectorAll('.setup-tab').forEach(tab => {
        tab.addEventListener('click', switchSetupTab);
    });

    document.getElementById('register-form').addEventListener('submit', handleRegister);
    document.getElementById('configure-form').addEventListener('submit', handleConfigure);
}

/**
 * Show setup modal
 */
function showSetupModal() {
    const modal = document.getElementById('setup-modal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Hide setup modal
 */
function hideSetupModal() {
    const modal = document.getElementById('setup-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Switch between setup tabs
 */
function switchSetupTab(event) {
    const targetTab = event.target.dataset.tab;

    // Update tab buttons
    document.querySelectorAll('.setup-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.setup-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${targetTab}-tab`).classList.add('active');

    // Clear results
    document.querySelectorAll('.setup-result').forEach(result => {
        result.style.display = 'none';
        result.innerHTML = '';
    });
}

/**
 * Handle user registration
 */
async function handleRegister(event) {
    event.preventDefault();

    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-password-confirm').value;
    const resultDiv = document.getElementById('register-result');

    // Validate passwords match
    if (password !== confirmPassword) {
        showSetupResult(resultDiv, 'error', 'Passwords do not match');
        return;
    }

    // Validate password length
    if (password.length < 8) {
        showSetupResult(resultDiv, 'error', 'Password must be at least 8 characters');
        return;
    }

    showSetupResult(resultDiv, 'info', 'Registering user...');

    try {
        const response = await fetch('/api/setup/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            showSetupResult(resultDiv, 'success',
                `Registration successful! Your API key: <br><code>${data.api_key}</code>`);

            // Auto-configure with the new API key
            setTimeout(async () => {
                await configureApiKey(data.api_key);
            }, 1500);
        } else {
            showSetupResult(resultDiv, 'error', data.error || 'Registration failed');
        }
    } catch (error) {
        showSetupResult(resultDiv, 'error', `Failed to connect to backend: ${error.message}`);
    }
}

/**
 * Handle API key configuration
 */
async function handleConfigure(event) {
    event.preventDefault();

    const apiKey = document.getElementById('api-key-input').value.trim();
    const resultDiv = document.getElementById('configure-result');

    if (!apiKey.startsWith('mn_')) {
        showSetupResult(resultDiv, 'error', 'Invalid API key format (should start with "mn_")');
        return;
    }

    await configureApiKey(apiKey, resultDiv);
}

/**
 * Configure API key in the Flask app
 */
async function configureApiKey(apiKey, resultDiv = null) {
    const displayDiv = resultDiv || document.getElementById('configure-result');

    showSetupResult(displayDiv, 'info', 'Configuring API key...');

    try {
        const response = await fetch('/api/setup/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        const data = await response.json();

        if (response.ok) {
            showSetupResult(displayDiv, 'success', 'Configuration successful! Loading application...');

            // Update state
            SetupState.configured = true;
            SetupState.hasApiKey = true;

            // Hide modal and reload page after short delay
            setTimeout(() => {
                hideSetupModal();
                location.reload();
            }, 1500);
        } else {
            showSetupResult(displayDiv, 'error', data.error || 'Configuration failed');
        }
    } catch (error) {
        showSetupResult(displayDiv, 'error', `Failed to configure: ${error.message}`);
    }
}

/**
 * Show result message in setup modal
 */
function showSetupResult(element, type, message) {
    element.style.display = 'block';
    element.className = `setup-result ${type}`;
    element.innerHTML = message;
}

/**
 * Export functions for external use
 */
window.MnemosyneSetup = {
    checkStatus: checkSetupStatus,
    showModal: showSetupModal,
    hideModal: hideSetupModal
};
