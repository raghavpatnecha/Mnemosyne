// Constants and utility functions
const CONSTANTS = {
    APP_ID: "", // paste your opengraph.io key here optional
    API_ID: window.location.origin + "/mnemosyne/api/v1/search",
    CACHE_PREFIX: "mnemosyne_search_",
    CACHE_EXPIRY: 30 * 60 * 1000 // 30 minutes
};
const encodeQuery = query => query.replace(/\s+/g, '-').toLowerCase();
const generateUniqueId = () => Math.random().toString(36).substring(2, 15);
const isValidUrl = url => /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(url);
const mainContent = document.getElementById('main-content');
const sidebar = document.getElementById('sidebar');
const closeBtn = document.getElementById('btn-search-close');

// Search State Cache
const SearchCache = {
    save: function(searchId, data) {
        const cacheEntry = {
            timestamp: Date.now(),
            data: data
        };
        try {
            sessionStorage.setItem(CONSTANTS.CACHE_PREFIX + searchId, JSON.stringify(cacheEntry));
        } catch (e) {
            console.warn('Failed to cache search result:', e);
        }
    },

    get: function(searchId) {
        try {
            const cached = sessionStorage.getItem(CONSTANTS.CACHE_PREFIX + searchId);
            if (!cached) return null;

            const entry = JSON.parse(cached);
            // Check if cache is expired
            if (Date.now() - entry.timestamp > CONSTANTS.CACHE_EXPIRY) {
                sessionStorage.removeItem(CONSTANTS.CACHE_PREFIX + searchId);
                return null;
            }
            return entry.data;
        } catch (e) {
            return null;
        }
    },

    clear: function(searchId) {
        sessionStorage.removeItem(CONSTANTS.CACHE_PREFIX + searchId);
    }
};

// Current search state
let currentSearchId = null;
let currentSearchState = {
    query: '',
    answer: '',
    sources: [],
    images: [],
    media: [],
    followUps: [],
    metadata: {}
};

// Main search function
function performSearch(query, isFollowUp = false) {
    query = query || document.getElementById('search-input').value;
    if (!query.trim()) {
        alert('Please enter a search query');
        return;
    }

    isFollowUp ? handleFollowUpSearch(query) : handleInitialSearch(query);
    closeSearch();
    updateUIPostSearch(isFollowUp);

    const encodedQuery = encodeQuery(query);
    const uniqueId = generateUniqueId();
    const searchId = `${encodedQuery}-${uniqueId}`;

    // Store current search ID for caching
    if (!isFollowUp) {
        currentSearchId = searchId;
        currentSearchState = {
            query: query,
            answer: '',
            sources: [],
            images: [],
            media: [],
            followUps: [],
            metadata: {}
        };
    }

    // Build API URL for fetching results
    let apiUrl = `${CONSTANTS.API_ID}/${searchId}`;

    // Add collection_id as query parameter if available
    const collectionId = window.SDKState?.currentCollection;
    if (collectionId) {
        apiUrl += `?collection_id=${collectionId}`;
    }

    // Update browser URL (use /search/ path, not the API path)
    if (!isFollowUp && window.location.protocol !== 'file:') {
        let browserUrl = `/search/${searchId}`;
        if (collectionId) {
            browserUrl += `?collection_id=${collectionId}`;
        }
        window.history.pushState({ query: query, searchId: searchId, collectionId: collectionId }, '', browserUrl);
    }

    streamResults(apiUrl, isFollowUp);
}

// Handle page load - check if we're on a search URL and restore from cache or re-fetch
function handleSearchPageLoad() {
    const path = window.location.pathname;
    if (path.startsWith('/search/')) {
        const searchId = path.replace('/search/', '');

        // Get collection_id from URL params if present
        const urlParams = new URLSearchParams(window.location.search);
        const collectionId = urlParams.get('collection_id');
        if (collectionId && window.SDKState) {
            window.SDKState.currentCollection = collectionId;
        }

        // Try to restore from cache first
        const cachedState = SearchCache.get(searchId);
        if (cachedState) {
            console.log('Restoring from cache:', searchId);
            restoreSearchState(cachedState, collectionId);
            return;
        }

        // No cache - decode query and re-execute search
        const parts = searchId.split('-');
        // Remove the last part (unique ID) if it looks like one
        if (parts.length > 1 && parts[parts.length - 1].length >= 10) {
            parts.pop();
        }
        const decodedQuery = parts.join(' ');

        if (decodedQuery) {
            console.log('No cache found, re-executing search:', decodedQuery);
            performSearch(decodedQuery, false);
        }
    }
}

// Restore search state from cache
function restoreSearchState(state, collectionId) {
    // Set up UI
    handleInitialSearch(state.query);
    closeSearch();
    updateUIPostSearch(false);

    // Restore answer
    const answerContainer = document.getElementById('answer-container');
    if (answerContainer && state.answer) {
        answerContainer.innerHTML = parseMarkdown(state.answer);

        // Add completion elements
        const completionDiv = document.createElement('div');
        completionDiv.setAttribute('data-orientation', 'horizontal');
        completionDiv.setAttribute('role', 'none');
        completionDiv.classList.add('answer-complete');

        const warningDiv = document.createElement('div');
        warningDiv.className = 'warning-text';
        warningDiv.textContent = 'Mnemosyne can make mistakes. Verify response and sources.';

        answerContainer.appendChild(completionDiv);
        answerContainer.appendChild(warningDiv);
    }

    // Restore sources, images, follow-ups via displayResults
    if (state.metadata) {
        displayResults(state.metadata, false);
    }

    // Create follow-up input
    manageFollowUpInput();
}

// Run on page load
document.addEventListener('DOMContentLoaded', handleSearchPageLoad);

//For Initial Search
function handleInitialSearch(query) {
    clearPage();
    document.getElementById('query').textContent = query;
}

//For Follow-ups
function handleFollowUpSearch(query) {
    const followUpQueryText = document.createElement('div');
    followUpQueryText.className = 'follow-up-query-text';
    followUpQueryText.textContent = `Follow-up: ${query}`;
    mainContent.appendChild(followUpQueryText);
    createNewContainers();
}


function updateUIPostSearch(isFollowUp) {
    const mainWrapElement = document.querySelector('.main-wrap');
    if (mainWrapElement) {
        mainWrapElement.classList.add('main-wrap-post-search');
        mainWrapElement.classList.remove('main-wrap');
    }
    if (closeBtn) {
        closeBtn.style.display = 'block';
    }
    document.getElementById('content-wrapper').style.display = 'flex';
    showLoaders(isFollowUp);
}

function clearPage() {
    mainContent.innerHTML = `
        <div class="follow-up-images">
             <svg class="lucid-images-svg mr-1.5 text-muted-foreground" style="margin-right: 0.375rem; margin-bottom: 0.175rem; display: inline-block; vertical-align: middle; width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <use xlink:href="#icon-images"></use>
             </svg>
             <h2 class="lucid-images">Images</h2>
        </div>
        <div id="images-section">
            <button id="more-images" class="more-button" style="display: none;">+</button>
            <div id="images-container" class="images-container"></div>
        </div>
        <div class="follow-up-answer">
            <svg width="16" height="16" class="lucide lucid-images-svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <use xlink:href="#icon-answer"></use>
            </svg>
            <h2 class="lucid-images">Answer</h2>
        </div>
        <div id="answer-container"></div>
       <div class="follow-up-text">
            <svg width="16" height="16" class="lucide lucid-images-svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <use xlink:href="#icon-follow-up"></use>
            </svg>
            <h2 class="lucid-images">Follow-up Questions</h2>
        </div>
        <div id="follow-up-container"></div>

    `;

    sidebar.innerHTML = `
         <div class="follow-up-sources">
             <svg width="16" height="16" class="lucide lucide-newspaper" style="margin-right: 0.675rem; display: inline-block;" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
             <use xlink:href="#icon-newspaper"></use>
             </svg>
             <h2 class="lucid">Sources</h2>
         </div>
        <div id="sources-container"></div>
    `;
}

function createNewContainers() {
    const newQuerySection = document.createElement('div');
    newQuerySection.className = 'query-section';
    newQuerySection.innerHTML = `
        <div class="query-content">
            <div class="follow-up-images">
                <svg class="lucid-images-svg mr-1.5 text-muted-foreground" style="margin-right: 0.375rem; margin-bottom: 0.175rem; display: inline-block; vertical-align: middle; width: 16px; height: 16px;" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <use xlink:href="#icon-images"></use>
                </svg>
                <h2 class="lucid-images">Images</h2>
            </div>
            <div class="images-section">
                <button class="more-images more-button" style="display: none;">+</button>
                <div class="images-container"></div>
            </div>
            <div class="follow-up-answer">
                <svg width="16" height="16" class="lucide lucid-images-svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <use xlink:href="#icon-answer"></use>
                </svg>
                <h2 class="lucid-images">Answer</h2>
            </div>
            <div class="answer-container"></div>
            <div class="follow-up-text">
                <svg width="16" height="16" class="lucide lucid-images-svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <use xlink:href="#icon-follow-up"></use>
                </svg>
                <h2 class="lucid-images">Follow-up Questions</h2>
            </div>
            <div class="follow-up-container"></div>
        </div>
        <div class="sources-section">
            <div class="follow-up-sources">
                <svg width="16" height="16" class="lucide lucide-newspaper mr-1.5 text-muted-foreground" style="margin-right: 0.675rem; display: inline-block;" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <use xlink:href="#icon-newspaper"></use>
                </svg>
                <h2 class="lucid">Sources</h2>
            </div>
            <div class="sources-container"></div>
        </div>
    `;
    mainContent.appendChild(newQuerySection);
}

function clearAllContainers(data = {}, isFollowUp = false) {
    const currentQuerySection = document.querySelector('.query-section:last-child') || document;
    const currentSourcesSection = currentQuerySection.querySelector('.sources-section') || document;

    updateContainerVisibility(currentQuerySection, data, isFollowUp);
    updateSourcesContainer(currentSourcesSection, data, isFollowUp);

    if (data.error) {
        displayErrorMessage(data.error);
    }
}

function updateContainerVisibility(section, data, isFollowUp) {

    // Handle images container
    const imagesContainer = section.querySelector('.images-container') || document.getElementById('images-container');
    const followUpImagesText = section.querySelector('.follow-up-images');
    if (imagesContainer) {
        if (!data.images || data.images.length === 0) {
            imagesContainer.innerHTML = '';
            imagesContainer.style.display = 'none';
            if (followUpImagesText) followUpImagesText.style.display = 'none';
        } else {
            imagesContainer.style.display = 'flex';
            if (followUpImagesText) followUpImagesText.style.display = 'block';
        }
    }

    // Handle follow-up container
    const followUpContainer = section.querySelector('.follow-up-container') || document.getElementById('follow-up-container');
    const followUpText = section.querySelector('.follow-up-text');
    if (followUpContainer) {
        if (!data.follow_up || data.follow_up.length === 0) {
            followUpContainer.innerHTML = '';
            followUpContainer.style.display = 'none';
            if (followUpText) followUpText.style.display = 'none';
        } else {
            followUpContainer.style.display = 'block';
            if (followUpText) followUpText.style.display = 'block';
        }
    }

	 // Handle 'More Images' button
    const moreImagesButton = section.querySelector('.more-images') || document.getElementById('more-images');
    if (moreImagesButton) {
        moreImagesButton.style.display = (!data.images || data.images.length === 0) ? 'none' : 'block';
    }

    // Handle confidence score
    const confidenceContainer = section.querySelector('.confidence-container');
    if (confidenceContainer) {
        if (data.confidence_score === undefined) {
            confidenceContainer.remove();
        }
    }

}

function updateSourcesContainer(section, data = {}, isFollowUp = false) {
    // Handle sources container
    const sourcesContainer = section.querySelector('.sources-container') || document.getElementById('sources-container');;
    const followUpSourcesText = section.querySelector('.follow-up-sources');
    if (sourcesContainer) {
        if (isFollowUp) {
            // For follow-up queries, don't clear existing sources
            // But hide follow-up-sources if there are no new sources
            if (!data.sources || data.sources.length === 0) {
                sourcesContainer.innerHTML = '';
                if (followUpSourcesText) followUpSourcesText.style.display = 'none';
            } else {
                sourcesContainer.style.display = 'block';
                if (followUpSourcesText) followUpSourcesText.style.display = 'block';
            }
        } else if (!data.sources || data.sources.length === 0) {
            sourcesContainer.innerHTML = '';
            sourcesContainer.style.display = 'none';
            if (followUpSourcesText) followUpSourcesText.style.display = 'none';
        } else {
            sourcesContainer.style.display = 'block';
            if (followUpSourcesText) followUpSourcesText.style.display = 'block';
        }
    }
    else{
      if (followUpSourcesText) followUpSourcesText.style.display = 'none';
    }
}


function displayErrorMessage(errorMessage) {
    const currentQuerySection = document.querySelector('.query-section:last-child') || document;
    const answerContainer = currentQuerySection.querySelector('.answer-container') || document.getElementById('answer-container');

    if (answerContainer) {
        answerContainer.innerHTML = `
            <div class="error-message">
                <p>Well, this is embarrassing! An unexpected anomaly occurred while fetching your results:</p>
                <p>${errorMessage}</p>
                <p>But fear not! Unlike the probability of getting struck by lightning twice, this issue is solvable. Kindly rephrase your query, try again, or perform the tried-and-true method of turning it off and on again.</p>
            </div>
        `;
        answerContainer.style.display = 'block';
    }
}

// Follow-up input create and management
function manageFollowUpInput() {
    let container = document.querySelector('.follow-up-input-container');
    const mainContent = document.querySelector('main') || document.getElementById('main-content');

    if (!container) {
        container = createFollowUpInputContainer();
        mainContent.appendChild(container);
    }

    updateFollowUpInputPosition();

    const input = container.querySelector('#follow-up-input');
    const sendButton = container.querySelector('.follow-up-send-button');

    input.addEventListener('input', () => {
        sendButton.disabled = input.value.trim() === '';
    });

    sendButton.addEventListener('click', handleFollowUpSend);
}

function createFollowUpInputContainer() {
    const container = document.createElement('div');
    container.className = 'follow-up-input-container';
    container.innerHTML = `
        <input type="text" id="follow-up-input" class="follow-up-input" placeholder="Ask a follow-up">
        <button type="submit" class="follow-up-send-button" disabled>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="19" x2="12" y2="5"></line>
                <polyline points="5 12 12 5 19 12"></polyline>
            </svg>
        </button>
    `;
    return container;
}

function updateFollowUpInputPosition() {
    const container = document.querySelector('.follow-up-input-container');
    const mainContent = document.querySelector('main') || document.getElementById('main-content');
    if (container && mainContent) {
        const mainRect = mainContent.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        container.style.bottom = `${mainRect.innerHeight - containerRect.bottom + 20}px`;
    }
}

function handleFollowUpSend() {
    const container = document.querySelector('.follow-up-input-container');
	const sendButton = container.querySelector('.follow-up-send-button');
    const input = container.querySelector('#follow-up-input');
    const followUpQuery = input.value.trim();
    if (followUpQuery !== '') {
        performSearch(followUpQuery, true);
        input.value = '';
        sendButton.disabled = true;
    }
}

function showLoaders(isFollowUp = false) {
    const currentQuerySection = document.querySelector('.query-section:last-child') || document;
    const imagesContainer = currentQuerySection.querySelector('.images-container') || document.getElementById('images-container');
    const answerContainer = currentQuerySection.querySelector('.answer-container') || document.getElementById('answer-container');
    const followUpContainer = currentQuerySection.querySelector('.follow-up-container') || document.getElementById('follow-up-container');
    const sourcesContainer = currentQuerySection.querySelector('.sources-container') || document.getElementById('sources-container');

    imagesContainer.innerHTML = '<div class="image-wrapper"><div class="image-loader"></div></div>'.repeat(3);
    answerContainer.innerHTML = '<div class="answer-loader"></div>';
    followUpContainer.innerHTML = '<div class="follow-up-loader"></div>'.repeat(2);

    if (!isFollowUp) {
        sourcesContainer.innerHTML = '<div class="source-loader"></div>'.repeat(2);
    } else {
        // For follow-up queries, append new loaders instead of replacing existing content
        sourcesContainer.innerHTML += '<div class="source-loader"></div>'.repeat(2);
    }
}

// Result streaming and display
function streamResults(query, isFollowUp) {
    let fullAnswer = '';
    let buffer = '';
    let inCodeBlock = false;
    let currentCodeBlock = '';
    let language = '';
    let isFirstLine = true;
    let customStyledFirstLine = '';
    let hasStartedStreaming = false;

    const currentAnswerContainer = document.querySelector('.query-section:last-child .answer-container') || document.getElementById('answer-container');

    fetch(query)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.body;
        })
        .then(body => {
            const reader = body.getReader();
            const decoder = new TextDecoder();

            function read() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        finishStreaming();
                        return;
                    }

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    lines.forEach(line => {
                        if (line.startsWith('data: ')) {
                            const content = line.slice(6);
                            try {
                                const data = JSON.parse(content);
                                if (data.type === 'delta' && data.content) {
                                    // Delta text chunks - use processText which handles streaming display
                                    processText(data.content);
                                } else if (data.type) {
                                    // Other typed SSE events
                                    handleTypedEvent(data, isFollowUp);
                                } else {
                                    // Legacy format
                                    displayResults(data, isFollowUp);
                                }
                            } catch (error) {
                                // Plain text content - process as answer text
                                processText(content);
                            }
                        }
                    });

                    read();
                });
            }

            read();
        })
        .catch(error => {
            console.error("Error fetching results:", error);
            clearAllContainers({ error: error.message }, isFollowUp);
        });

    function processText(text) {
        // Filter out [DONE] marker and empty content
        if (!text || text.trim() === '[DONE]' || text.trim() === '') {
            return;
        }

        if (!hasStartedStreaming) {
            currentAnswerContainer.innerHTML = '';
            hasStartedStreaming = true;
        }

        // During streaming, tokens come one at a time
        // Don't split by newlines - just accumulate the raw text
        // We'll handle newlines properly in the final markdown parse

        if (isFirstLine && text.trim()) {
            const trimmedText = text.trim();
            // Check if first meaningful content is a header pattern
            if (trimmedText.startsWith('##') ||
                (trimmedText.startsWith('**') && trimmedText.endsWith('**') && trimmedText.length > 4)) {
                let processedText;
                if (trimmedText.startsWith('##')) {
                    processedText = trimmedText.slice(trimmedText.lastIndexOf('#') + 1).trim();
                } else {
                    processedText = trimmedText.slice(2, -2).trim();
                }
                if (processedText) {
                    customStyledFirstLine = renderCustomBoldText(processedText);
                    fullAnswer += '%%%CUSTOM_STYLED_FIRST_LINE%%%';
                    isFirstLine = false;
                    updateDisplay();
                    return;
                }
            }
            isFirstLine = false;
        }

        // Handle code blocks
        if (text.trim().startsWith('```')) {
            handleCodeBlock(text);
        } else if (inCodeBlock) {
            currentCodeBlock += text;
        } else {
            // Simply accumulate text as-is
            fullAnswer += text;
        }

        updateDisplay();
    }

    function handleCodeBlock(line) {
        if (!inCodeBlock) {
            inCodeBlock = true;
            language = line.trim().slice(3).trim() || 'plaintext';
            currentCodeBlock = '';
            fullAnswer += `<pre><code class="hljs language-${language}">`;
        } else {
            inCodeBlock = false;
            fullAnswer += `${currentCodeBlock}</code></pre>\n`;
            currentCodeBlock = '';
        }
    }

    function updateDisplay(isFinal = false) {
        let displayContent = fullAnswer;
        if (inCodeBlock) {
            displayContent += escapeHtml(currentCodeBlock);
        }

        // Clean up empty brackets [] and [DONE] markers
        displayContent = displayContent.replace(/\[\]/g, '');
        displayContent = displayContent.replace(/\[DONE\]/g, '');

        let parsedContent;
        if (isFinal) {
            // Final render: apply full markdown parsing
            displayContent = displayContent.replace(/<pre><code class="hljs language-(\w+)">([\s\S]*?)<\/code><\/pre>/g, (match, lang, code) => {
                const highlightedCode = hljs.highlight(code.trim(), { language: lang }).value;
                return `<pre><code class="hljs language-${lang}">${highlightedCode}</code></pre>`;
            });
            parsedContent = parseMarkdown(displayContent);
        } else {
            // During streaming: convert newlines to <br> for proper line breaks
            let escaped = escapeHtml(displayContent);
            // Convert double newlines to paragraph breaks, single newlines to <br>
            escaped = escaped.replace(/\n\n/g, '</p><p>');
            escaped = escaped.replace(/\n/g, '<br>');
            parsedContent = '<p>' + escaped + '</p>';
        }

        parsedContent = parsedContent.replace('%%%CUSTOM_STYLED_FIRST_LINE%%%', customStyledFirstLine);
        parsedContent = parsedContent.replace(/&amp;#37;&amp;#37;&amp;#37;CUSTOM_STYLED_FIRST_LINE&amp;#37;&amp;#37;&amp;#37;/g, customStyledFirstLine);
        currentAnswerContainer.innerHTML = parsedContent;

        mainContent.scrollTo({
            top: mainContent.scrollHeight,
            behavior: 'smooth'
        });

        manageFollowUpInput();
    }

    function finishStreaming() {
        console.log('Stream complete');

        if (inCodeBlock) {
            fullAnswer += `${escapeHtml(currentCodeBlock)}</code></pre>\n`;
            inCodeBlock = false;
        }
        updateDisplay(true);  // Final render with full markdown parsing

        const completionDiv = document.createElement('div');
        completionDiv.setAttribute('data-orientation', 'horizontal');
        completionDiv.setAttribute('role', 'none');
        completionDiv.classList.add('answer-complete');

        const warningDiv = document.createElement('div');
        warningDiv.className = 'warning-text';
        warningDiv.textContent = 'Mnemosyne can make mistakes. Verify response and sources.';

        currentAnswerContainer.appendChild(completionDiv);
        currentAnswerContainer.appendChild(warningDiv);

        mainContent.scrollTo({
            top: mainContent.scrollHeight,
            behavior: 'smooth'
        });

        // Save to cache for page reload
        if (currentSearchId && !isFollowUp) {
            // Clean the answer before caching
            let cleanAnswer = fullAnswer.replace(/\[\]/g, '').replace(/\[DONE\]/g, '');
            currentSearchState.answer = cleanAnswer;
            SearchCache.save(currentSearchId, currentSearchState);
            console.log('Search cached:', currentSearchId);
        }
    }
}

// Handle typed SSE events from backend
function handleTypedEvent(data, isFollowUp) {
    const currentQuerySection = document.querySelector('.query-section:last-child') || document;

    switch (data.type) {
        case 'sources':
            if (data.sources && data.sources.length > 0) {
                displaySources(data.sources, currentQuerySection, isFollowUp);
                if (!isFollowUp && currentSearchState) {
                    currentSearchState.sources = data.sources;
                }
            }
            break;

        case 'media':
            // Map media items to images display format
            if (data.media && data.media.length > 0) {
                const images = data.media.map(m => ({
                    url: m.url,
                    description: m.description || `${m.type} from ${m.source_document_title || 'document'}`
                }));
                displayImages(images, currentQuerySection);
                if (!isFollowUp && currentSearchState) {
                    currentSearchState.media = data.media;
                }
            }
            break;

        case 'follow_up':
            // Map follow_up_questions to string array for existing display
            if (data.follow_up_questions && data.follow_up_questions.length > 0) {
                const questions = data.follow_up_questions.map(q => q.question);
                displayFollowUp(questions, currentQuerySection);
                if (!isFollowUp && currentSearchState) {
                    currentSearchState.followUps = data.follow_up_questions;
                }
            }
            break;

        case 'done':
            if (!isFollowUp && currentSearchState && data.metadata) {
                currentSearchState.metadata = { ...currentSearchState.metadata, ...data.metadata };
            }
            if (data.metadata && data.metadata.confidence !== undefined) {
                displayConfidenceScore(data.metadata.confidence, currentQuerySection);
            }
            break;

        case 'error':
            if (data.error) {
                displayErrorMessage(data.error);
            }
            break;

        case 'reasoning_step':
            // Deep reasoning progress
            console.log(`Reasoning step ${data.step}: ${data.description}`);
            break;

        case 'sub_query':
            // Sub-query during deep reasoning
            console.log(`Sub-query: ${data.query}`);
            break;

        case 'usage':
            // Token usage stats - informational
            break;

        default:
            console.log('Unknown SSE event:', data.type, data);
    }
}

function renderCustomBoldText(text) {
    return `<div class="answer-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-search">
                    <circle cx="11" cy="11" r="8"></circle>
                    <path d="m21 21-4.3-4.3"></path>
                </svg>
                 <span class="ml-1">${escapeHtml(text)}</span>
            </div>`;
}


//Utility Functions
function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
}



function setupMarked() {
    // Configure marked with GitHub Flavored Markdown support
    // Use minimal customization to ensure inline markdown (bold, italic, etc.) works correctly
    marked.setOptions({
        gfm: true,
        breaks: true,
        headerIds: false,
        mangle: false
    });
}

function ensureString(content) {
    if (typeof content === 'string') {
        return content;
    } else if (typeof content === 'object' && content !== null) {
        if (content.href) return content.href;
        if (content.text) return content.text;
        if (content.raw) return content.raw;
        if (Array.isArray(content)) {
            return content.map(ensureString).join(' ');
        }
        return Object.values(content).map(ensureString).join(' ');
    }
    return '';
}

function parseMarkdown(text) {
    try {
        // Preprocess: Add line breaks before section headers for proper markdown parsing
        // This handles cases where the LLM doesn't send newlines before headers
        let processedText = text
            // Convert ".." or ". ." separators to proper line breaks (common LLM output pattern)
            .replace(/\s*\.\.\s*/g, '\n\n')
            // Add line breaks before bold section headers like **Be a Secure Base:**
            .replace(/([.!?:)\]])\s*(\*\*[A-Z][^*]+\*\*:?)/g, '$1\n\n$2')
            // Add line breaks before underscored section headers like _Be a Secure Base_:
            .replace(/([.!?:)\]])\s*(_[A-Z][^_]+_:)/g, '$1\n\n$2')
            // Add line breaks before plain section headers
            .replace(/([.!?\]])\s*((?:Detailed Analysis|Gaps|Key Takeaways|Summary|Conclusion|Overview|Background|Recommendations|Next Steps|References|Notes|Introduction|Methods|Results|Discussion):)/g, '$1\n\n$2')
            // Ensure numbered lists get proper line breaks
            .replace(/([.!?])\s*(\d+\.\s+\*\*)/g, '$1\n\n$2')
            // Ensure bullet points get proper line breaks
            .replace(/([.!?])\s*([•\-\*]\s+)/g, '$1\n\n$2')
            // Normalize multiple newlines to double newlines
            .replace(/\n{3,}/g, '\n\n')
            // Trim leading/trailing whitespace
            .trim();

        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(processedText, {
                gfm: true,
                breaks: true
            });
        } else {
            console.warn('Marked library not loaded. Using fallback markdown parser.');
            return fallbackMarkdownParse(processedText);
        }
    } catch (error) {
        console.error('Error parsing markdown:', error);
        return fallbackMarkdownParse(text);
    }
}

function fallbackMarkdownParse(text) {
    // Simple fallback markdown parser for basic formatting
    // First apply the same preprocessing as parseMarkdown
    let processedText = text
        // Convert ".." separators to line breaks
        .replace(/\s*\.\.\s*/g, '\n\n')
        // Add line breaks before bold section headers
        .replace(/([.!?:)\]])\s*(\*\*[A-Z][^*]+\*\*:?)/g, '$1\n\n$2')
        // Normalize multiple newlines
        .replace(/\n{3,}/g, '\n\n')
        .trim();

    return processedText
        // Bold text: **text** or __text__
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        // Italic text: *text* or _text_
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/_(.+?)_/g, '<em>$1</em>')
        // Inline code: `code`
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Headers: ## Header
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Paragraphs: double newlines become paragraphs
        .replace(/\n\n/g, '</p><p>')
        // Single line breaks
        .replace(/\n/g, '<br>')
        // Wrap in paragraph tags
        .replace(/^(.+)$/, '<p>$1</p>');
}


function truncateText(text, maxLength) {
    return text.length > maxLength ? text.substr(0, maxLength - 1) + '…' : text;
}


async function displayResults(data, isFollowUp) {
    clearAllContainers(data, isFollowUp);
    const currentQuerySection = document.querySelector('.query-section:last-child') || document;

    displayImages(data.images, currentQuerySection);
    displayFollowUp(data.follow_up, currentQuerySection);
    displaySources(data.sources, currentQuerySection, isFollowUp);
    displayConfidenceScore(data.confidence_score, currentQuerySection);

    // Store metadata for caching
    if (!isFollowUp && currentSearchState) {
        currentSearchState.metadata = data;
        currentSearchState.images = data.images || [];
        currentSearchState.sources = data.sources || [];
        currentSearchState.followUps = data.follow_up || [];
    }
}

function displayImages(images, container) {
    const imagesContainer = container.querySelector('.images-container') || document.getElementById('images-container');
    const moreImagesButton = container.querySelector('.more-images') || document.getElementById('more-images');

    //clear images loading state
    imagesContainer.innerHTML = '';

    if (images && images.length > 0) {
        imagesContainer.innerHTML = images.map(img => `
            <div class="image-wrapper">
                <img src="${img.url}" alt="${img.description}">
            </div>
        `).join('');

        setTimeout(() => {
            moreImagesButton.style.display = imagesContainer.scrollWidth > imagesContainer.clientWidth ? 'block' : 'none';
        }, 0);
    } else {
        imagesContainer.style.display = 'none';
        moreImagesButton.style.display = 'none';
    }
}

function displayFollowUp(followUp, container) {
    const followUpContainer = container.querySelector('.follow-up-container') || document.getElementById('follow-up-container');

    //clear follow up loading state
    followUpContainer.innerHTML = '';

    if (followUp && followUp.length > 0) {
        followUpContainer.innerHTML = followUp.map(question => `
            <div class="flex items-start w-full follow-up-item">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right h-4 w-4 mr-2 mt-1 flex-shrink-0 text-accent-foreground/50">
                    <path d="M5 12h14"></path>
                    <path d="m12 5 7 7-7 7"></path>
                </svg>
                <button class="follow-up-button" type="submit" name="related_query">
                    ${question}
                </button>
            </div>
        `).join('');
    } else {
        followUpContainer.style.display = 'none';
    }
}

function displaySources(sources, container, isFollowUp) {
    const sourcesContainer = container.querySelector('.sources-container') || document.getElementById('sources-container');
    sourcesContainer.innerHTML = '';
    if (!sources || sources.length === 0) {
        if (!isFollowUp) sourcesContainer.style.display = 'none';
        return;
    }

    // Handle multiple source formats:
    // 1. SDK chat sources: document_id, title, filename, chunk_index, score
    // 2. Metadata sources: title, url, filename, relevance, snippet
    // 3. Legacy sources: url (valid http), title, content
    const sourceElements = sources.map(source => {
        if (source.document_id) {
            // SDK chat source format
            return createSDKSourceHTML(source);
        } else if (source.relevance !== undefined || source.snippet) {
            // Metadata source format (from _extract_rich_metadata)
            return Promise.resolve(createMetadataSourceHTML(source));
        } else if (source.url && isValidUrl(source.url)) {
            // Legacy format with valid external URL
            return fetchSourcePreview(source);
        } else {
            return Promise.resolve(createFallbackSourceHTML(source));
        }
    });

    Promise.all(sourceElements).then(elements => {
        if (isFollowUp) {
            sourcesContainer.innerHTML += elements.join('');
        } else {
            sourcesContainer.innerHTML = elements.join('');
        }
    });
}

function createSDKSourceHTML(source) {
    const scorePercent = source.score ? Math.round(source.score * 100) : 0;

    return `
        <div class="source">
            <div class="source-preview">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'%3E%3C/path%3E%3Cpolyline points='14 2 14 8 20 8'%3E%3C/polyline%3E%3C/svg%3E" alt="Document" class="favicon">
                <div class="preview-content">
                    <h3>${source.title || source.filename || 'Document'}</h3>
                    <p class="source-description">${source.filename || ''}</p>
                    <p class="site-name">Relevance: ${scorePercent}%${source.chunk_index !== undefined ? ` | Chunk #${source.chunk_index + 1}` : ''}</p>
                </div>
            </div>
        </div>
    `;
}

function createMetadataSourceHTML(source) {
    // Handle metadata sources from _extract_rich_metadata
    // Format: title, url, filename, relevance, snippet
    const relevancePercent = source.relevance ? Math.round(source.relevance * 100) : 0;
    const snippetText = source.snippet ? truncateText(source.snippet, 150) : '';

    return `
        <div class="source">
            <div class="source-preview">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'%3E%3C/path%3E%3Cpolyline points='14 2 14 8 20 8'%3E%3C/polyline%3E%3C/svg%3E" alt="Document" class="favicon">
                <div class="preview-content">
                    <h3>${source.title || source.filename || 'Document'}</h3>
                    ${snippetText ? `<p class="source-description">${snippetText}</p>` : ''}
                    <p class="site-name">Relevance: ${relevancePercent}%</p>
                </div>
            </div>
        </div>
    `;
}

async function fetchSourcePreview(source) {
    if (!isValidUrl(source.url)) return '';

    try {
        const encodedUrl = encodeURIComponent(source.url);
        const response = await fetch(`https://opengraph.io/api/1.1/site/${encodedUrl}?app_id=${CONSTANTS.APP_ID}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const preview = await response.json();
        const hybridGraph = preview.hybridGraph;

        return createSourceHTML(hybridGraph);
    } catch (error) {
        console.error('Error fetching preview for', source.url, error);
        return createFallbackSourceHTML(source);
    }
}

function createSourceHTML(hybridGraph) {
    return `
        <div class="source">
            <div class="source-preview">
                ${hybridGraph.favicon ? `<img src="${hybridGraph.favicon}" alt="Favicon" class="favicon">` : ''}
                <div class="preview-content">
                    <h3>${hybridGraph.title || 'No Title'}</h3>
                    <a href="${hybridGraph.url}" target="_blank" class="source-link">${hybridGraph.url}</a>
                    <p class="source-description">${hybridGraph.description || 'No description available'}</p>
                    ${hybridGraph.site_name ? `<p class="site-name">${hybridGraph.site_name}</p>` : ''}
                    ${hybridGraph.articlePublishedTime ? `<p class="publish-date">Published: ${new Date(hybridGraph.articlePublishedTime).toLocaleDateString()}</p>` : ''}
                </div>
            </div>
        </div>
    `;
}

function createFallbackSourceHTML(source) {
    const description = source.content || source.snippet || source.description || '';
    const url = source.url || '';

    return `
        <div class="source">
            <div class="source-preview">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'%3E%3C/path%3E%3Cpolyline points='14 2 14 8 20 8'%3E%3C/polyline%3E%3C/svg%3E" alt="Document" class="favicon">
                <div class="preview-content">
                    <h3>${source.title || source.filename || 'Document'}</h3>
                    ${url ? `<a href="${url}" target="_blank" class="source-link">${truncateText(url, 50)}</a>` : ''}
                    ${description ? `<p class="source-description">${truncateText(description, 150)}</p>` : ''}
                </div>
            </div>
        </div>
    `;
}

function displayConfidenceScore(confidenceScore, container) {
    const confidenceContainer = document.createElement('div');
    confidenceContainer.className = 'confidence-container';
    confidenceContainer.textContent = confidenceScore !== undefined ?
        `Confidence Score: ${confidenceScore.toFixed(2)}` : '';

    const followUpImagesDiv = container.querySelector('.follow-up-images');
    if (followUpImagesDiv) {
        followUpImagesDiv.parentNode.insertBefore(confidenceContainer, followUpImagesDiv);
    } else {
        const queryContent = container.querySelector('.query-content');
        if (queryContent) {
            queryContent.insertBefore(confidenceContainer, queryContent.firstChild);
        }
    }
}

// Event listeners
function addEventListeners() {
    document.addEventListener('click', handleGlobalClick);
    window.addEventListener('resize', updateFollowUpInputPosition);
    mainContent.addEventListener('scroll', updateFollowUpInputPosition);
    document.getElementById('search-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});
}

function handleGlobalClick(e) {
    if (e.target.classList.contains('follow-up-button')) {
        const followUpQuery = e.target.textContent.trim();
        performSearch(followUpQuery, true);
    } else if (e.target.matches('#more-images, .more-images')) {
            const currentQuerySection = e.target.closest('.query-section');
            const imagesContainer = currentQuerySection
                ? currentQuerySection.querySelector('.images-container')
                : document.getElementById('images-container');
            // Only scroll if imagesContainer exists
            if (imagesContainer) {
                imagesContainer.scrollLeft += imagesContainer.clientWidth;
            }
        }
}

// Initialize the script
function init() {
    setupMarked();
    addEventListeners();
}

// Call the init function when the script loads
init();


/* ------------------------ Search button js (Please Ignore) ----------------------- */
const createSVG = (width, height, className, childType, childAttributes) => {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");

  const child = document.createElementNS(
    "http://www.w3.org/2000/svg",
    childType
  );

  for (const attr in childAttributes) {
    child.setAttribute(attr, childAttributes[attr]);
  }

  svg.appendChild(child);

  return { svg, child };
};

document.querySelectorAll(".generate-button").forEach((button) => {
  const width = button.offsetWidth;
  const height = button.offsetHeight;

  const style = getComputedStyle(button);

  const strokeGroup = document.createElement("div");
  strokeGroup.classList.add("stroke");

  const { svg: stroke } = createSVG(width, height, "stroke-line", "rect", {
    x: "0",
    y: "0",
    width: "100%",
    height: "100%",
    rx: parseInt(style.borderRadius, 10),
    ry: parseInt(style.borderRadius, 10),
    pathLength: "30"
  });

  strokeGroup.appendChild(stroke);
  button.appendChild(strokeGroup);

});
