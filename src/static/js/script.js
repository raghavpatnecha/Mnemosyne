// Constants and utility functions
const CONSTANTS = {
    APP_ID: "", // paste your opengraph.io key here optional
    API_ID: "http://127.0.0.1:5000/mnemosyne/api/v1/search"
};
const encodeQuery = query => query.replace(/\s+/g, '-').toLowerCase();
const generateUniqueId = () => Math.random().toString(36).substring(2, 15);
const isValidUrl = url => /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/.test(url);
const mainContent = document.getElementById('main-content');
const sidebar = document.getElementById('sidebar');
const closeBtn = document.getElementById('btn-search-close');

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
    const searchUrl = `${CONSTANTS.API_ID}/${encodedQuery}-${uniqueId}`;
    if (!isFollowUp && window.location.protocol !== 'file:') {
        window.history.pushState({}, '', searchUrl);
    }
    streamResults(searchUrl, isFollowUp);
}

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
                                displayResults(data, isFollowUp);
                            } catch (error) {
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
        if (!hasStartedStreaming) {
            currentAnswerContainer.innerHTML = '';
            hasStartedStreaming = true;
        }

        const lines = text.split('\n');
        lines.forEach(line => {
            if (isFirstLine) {
                const trimmedLine = line.trim();
                if (trimmedLine.startsWith('##') ||
                    (trimmedLine.startsWith('**') && trimmedLine.endsWith('**'))) {
                    let processedText;
                    if (trimmedLine.startsWith('##')) {
                        processedText = trimmedLine.slice(trimmedLine.lastIndexOf('#') + 1).trim();
                    } else {
                        processedText = trimmedLine.slice(2, -2).trim();
                    }
                    customStyledFirstLine = renderCustomBoldText(processedText);
                    fullAnswer += '%%%CUSTOM_STYLED_FIRST_LINE%%%\n';
                } else {
                    // Normal text - process it like any other line
                    fullAnswer += escapeHtml(line) + '\n';
                }
                isFirstLine = false;
            } else if (line.trim().startsWith('```')) {
                handleCodeBlock(line);
            } else if (inCodeBlock) {
                currentCodeBlock += line + '\n';
            } else {
                fullAnswer += escapeHtml(line) + '\n';
            }
        });

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

    function updateDisplay() {
        let displayContent = fullAnswer;
        if (inCodeBlock) {
            displayContent += escapeHtml(currentCodeBlock);
        }

        displayContent = displayContent.replace(/<pre><code class="hljs language-(\w+)">([\s\S]*?)<\/code><\/pre>/g, (match, lang, code) => {
            const highlightedCode = hljs.highlight(code.trim(), { language: lang }).value;
            return `<pre><code class="hljs language-${lang}">${highlightedCode}</code></pre>`;
        });

        let parsedContent = parseMarkdown(displayContent);
        parsedContent = parsedContent.replace('%%%CUSTOM_STYLED_FIRST_LINE%%%', customStyledFirstLine);

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
        updateDisplay();

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
marked.use({
    renderer: {
        heading(text) {
            const tag = `h${text.depth}`;
            const className = `custom-heading-${text.depth}`;
            text = ensureString(text);
            return `<${tag} class="${className}">${text}</${tag}>`;
        },
        paragraph(text) {
            text = ensureString(text);
            return `<p class="custom-paragraph">${marked.parseInline(text)}</p>`;
        },
        blockquote(quote) {
            quote = ensureString(quote);
            return `<blockquote class="custom-blockquote">${marked.parseInline(quote)}</blockquote>`;
        },
        code(code, language) {
            code = ensureString(code);
            return `<div class="code-preview">
                        <pre><code class="hljs language-${language}">${code}</code></pre>
                    </div>`;
        },
        link(href, title, text) {
            return marked.Renderer.prototype.link.call(this, href, title, text);
        }
    }
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
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(text, {
                gfm: true, // Enable GitHub Flavored Markdown
                breaks: true // Allow line breaks in paragraphs
            });
        } else {
            console.warn('Marked library not loaded correctly. Displaying raw text.');
            return text.replace(/\n/g, '<br>');
        }
    } catch (error) {
        console.error('Error parsing markdown:', error);
        return text.replace(/\n/g, '<br>');
    }
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

    const sourcePromises = sources.map(fetchSourcePreview);

    Promise.all(sourcePromises).then(sourceElements => {
        if (isFollowUp) {
            sourcesContainer.innerHTML += sourceElements.join('');
        } else {
            sourcesContainer.innerHTML = sourceElements.join('');
        }
    });
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
    return `
        <div class="source">
            <h3>${source.title || 'No Title'}</h3>
            <a href="${source.url}" target="_blank" class="source-link">${source.url}</a>
            <p class="source-description">${source.content}</p>
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


// Check if we're loading a search result page
const path = window.location.pathname;
const match = path.match(/^\/search\/(.+)-[a-z0-9]+$/);
if (match) {
    const encodedQuery = match[1];
    document.getElementById('search-input').value = encodedQuery.replace(/-/g, ' ');
    streamResults(`/search/${encodedQuery}`);
}


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
