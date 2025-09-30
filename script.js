const urlParams = new URLSearchParams(window.location.search);
const embedMode = urlParams.get('embed') === '1' || window !== window.parent;
const forcedApiOrigin = urlParams.get('api_origin') || urlParams.get('chat_origin') || urlParams.get('origin');

const FALLBACK_API_ORIGIN = 'http://localhost:8080';
const currentOrigin = `${window.location.protocol}//${window.location.host}`;
const defaultOrigin = window.location.port === '8000' ? FALLBACK_API_ORIGIN : currentOrigin;
const selectedApiOrigin = (forcedApiOrigin || window.CHAT_API_ORIGIN || defaultOrigin || '').replace(/\/$/, '');
const chatApiOrigin = selectedApiOrigin || defaultOrigin;
const forcedFeedTargetRaw = (urlParams.get('chat_target') || urlParams.get('target') || '').toLowerCase();
const feedTarget = forcedFeedTargetRaw === 'embed'
    ? 'embed'
    : forcedFeedTargetRaw === 'obs'
        ? 'obs'
        : (embedMode ? 'embed' : 'obs');
const chatEndpointPath = feedTarget === 'embed' ? '/embed-chat' : '/chat';
const chatEndpoint = `${chatApiOrigin}${chatEndpointPath}`;
const CUSTOM_EMOJI_PATTERN = /<a?:([a-zA-Z0-9_]+)(?::(\d+))?>/g;
const CUSTOM_EMOJI_CDN_BASE = 'https://cdn.discordapp.com/emojis';

const LOTTIE_CDN_URL = 'https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js';
let lottieLoaderPromise = null;
const lottieDataCache = new Map();
const lottieDataPromises = new Map();

function paramIsTrue(value) {
    if (value == null) {
        return false;
    }
    const normalized = String(value).toLowerCase();
    return normalized === '1' || normalized === 'true' || normalized === 'yes';
}

function paramIsFalse(value) {
    if (value == null) {
        return false;
    }
    const normalized = String(value).toLowerCase();
    return normalized === '0' || normalized === 'false' || normalized === 'no';
}

function parsePositiveNumber(value, fallback) {
    if (value == null) {
        return fallback;
    }
    const trimmed = String(value).trim();
    if (!trimmed) {
        return fallback;
    }
    const match = trimmed.match(/^(\d+(?:\.\d+)?)/);
    if (!match) {
        return fallback;
    }
    const parsed = Number(match[1]);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return fallback;
    }
    return parsed;
}

const requestedAutoResize = urlParams.get('auto_resize');
const autoResize = embedMode ? paramIsTrue(requestedAutoResize) : !paramIsFalse(requestedAutoResize);

const embedOptions = {
    embedMode,
    feedTarget,
    autoResize,
    hideUsernames: paramIsTrue(urlParams.get('hide_usernames')),
};

document.documentElement.dataset.chatTarget = feedTarget;

const embedHeightParam = urlParams.get('frame_height') || urlParams.get('embed_height') || (embedMode ? urlParams.get('height') : null);
const embedMaxHeightParam = urlParams.get('max_height') || urlParams.get('maxHeight');

if (embedMode) {
    const frameHeightValue = parsePositiveNumber(embedHeightParam, 480);
    const maxHeightValue = parsePositiveNumber(embedMaxHeightParam, frameHeightValue) || frameHeightValue;
    embedOptions.frameHeight = frameHeightValue;
    embedOptions.maxHeight = maxHeightValue;
    setCssVariable('--chat-frame-height', `${frameHeightValue}px`);
    setCssVariable('--chat-frame-max-height', `${maxHeightValue}px`);
} else {
    setCssVariable('--chat-frame-height', 'auto');
    setCssVariable('--chat-frame-max-height', 'none');
}

function setCssVariable(name, value) {
    if (!name || value == null) {
        return;
    }
    const trimmed = String(value).trim();
    if (!trimmed) {
        return;
    }
    document.documentElement.style.setProperty(name, trimmed);
}

function normalizeColor(value) {
    if (!value) {
        return null;
    }
    const trimmed = String(value).trim();
    if (!trimmed) {
        return null;
    }
    const lower = trimmed.toLowerCase();
    if (lower === 'transparent') {
        return 'transparent';
    }
    if (trimmed.startsWith('#')) {
        return trimmed;
    }
    if (/^[0-9a-f]{3,4}$/i.test(trimmed) || /^[0-9a-f]{6,8}$/i.test(trimmed)) {
        return `#${trimmed}`;
    }
    return trimmed;
}

function normalizeFont(value) {
    if (!value) {
        return null;
    }
    const trimmed = String(value).trim();
    if (!trimmed) {
        return null;
    }
    switch (trimmed.toLowerCase()) {
        case 'system':
            return 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
        case 'serif':
            return 'Georgia, "Times New Roman", serif';
        case 'mono':
        case 'monospace':
            return 'Menlo, Monaco, Consolas, "Courier New", monospace';
        default:
            return trimmed;
    }
}

function applyColorOption(variableName, ...paramNames) {
    for (const name of paramNames) {
        const raw = urlParams.get(name);
        if (!raw) {
            continue;
        }
        const normalized = normalizeColor(raw);
        if (normalized) {
            setCssVariable(variableName, normalized);
            return;
        }
    }
}

function applyVisualOptions() {
    if (paramIsTrue(urlParams.get('transparent'))) {
        setCssVariable('--chat-background', 'transparent');
    }
    applyColorOption('--chat-background', 'background', 'bg', 'chat_bg');
    applyColorOption('--message-background', 'message_background', 'message_bg', 'bubble_bg');
    applyColorOption('--message-color', 'text_color', 'message_color');
    applyColorOption('--username-color-default', 'username_color', 'name_color');

    const fontParam = urlParams.get('font');
    const normalizedFont = normalizeFont(fontParam);
    if (normalizedFont) {
        setCssVariable('--chat-font-family', normalizedFont);
    }

    if (embedOptions.embedMode) {
        document.documentElement.classList.add('embed-mode');
        if (document.body) {
            document.body.classList.add('embed-mode');
        } else {
            window.addEventListener('DOMContentLoaded', () => {
                document.body.classList.add('embed-mode');
            }, { once: true });
        }
    }
}

applyVisualOptions();

function scrollChatToBottom() {
    const chatBox = document.getElementById('chat');
    if (!chatBox) {
        return;
    }
    const schedule = window.requestAnimationFrame || function (fn) { return setTimeout(fn, 16); };
    schedule(() => {
        try {
            chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: 'smooth' });
        } catch (error) {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        reportEmbedSize(chatBox);
    });
}

let lastReportedHeight = 0;

function reportEmbedSize(chatElement) {
    if (!embedOptions.embedMode || !embedOptions.autoResize || window === window.parent) {
        return;
    }
    const element = chatElement || document.getElementById('chat');
    if (!element) {
        return;
    }
    const rect = element.getBoundingClientRect();
    const renderedHeight = Math.ceil((rect && rect.height) || element.clientHeight || element.scrollHeight);
    const frameHeight = typeof embedOptions.frameHeight === 'number' ? embedOptions.frameHeight : null;
    const maxHeight = typeof embedOptions.maxHeight === 'number' ? embedOptions.maxHeight : frameHeight;
    const targetHeight = maxHeight ? Math.min(renderedHeight, maxHeight) : renderedHeight;
    if (targetHeight !== lastReportedHeight) {
        lastReportedHeight = targetHeight;
        try {
            window.parent.postMessage({
                source: 'discord-chat-to-obs',
                type: 'size',
                height: targetHeight,
            }, '*');
        } catch (error) {
            // Ignored: parent window may not accept messages in some contexts.
        }
    }
}

function loadLottieLibrary() {
    if (window.lottie) {
        return Promise.resolve(window.lottie);
    }
    if (lottieLoaderPromise) {
        return lottieLoaderPromise;
    }
    lottieLoaderPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = LOTTIE_CDN_URL;
        script.async = true;
        script.onload = () => {
            if (window.lottie) {
                resolve(window.lottie);
            } else {
                reject(new Error('Lottie library failed to initialize.'));
            }
        };
        script.onerror = () => reject(new Error('Failed to load Lottie script.'));
        document.head.appendChild(script);
    }).catch(error => {
        lottieLoaderPromise = null;
        throw error;
    });
    return lottieLoaderPromise;
}

function collectFallbackSources(media) {
    const sources = [];
    if (media && typeof media === 'object') {
        if (typeof media.fallback_url === 'string') {
            sources.push(media.fallback_url);
        }
        if (Array.isArray(media.fallback_urls)) {
            media.fallback_urls.forEach(url => {
                if (typeof url === 'string') {
                    sources.push(url);
                }
            });
        }
    }
    return [...new Set(sources)];
}

function collectLottieSources(media) {
    const sources = [];
    if (media && typeof media === 'object') {
        if (typeof media.url === 'string') {
            sources.push(media.url);
        }
        if (typeof media.source_url === 'string') {
            sources.push(media.source_url);
        }
        if (Array.isArray(media.lottie_urls)) {
            media.lottie_urls.forEach(url => {
                if (typeof url === 'string') {
                    sources.push(url);
                }
            });
        }
    }
    return [...new Set(sources)];
}

function fetchLottieData(url) {
    if (!url || typeof url !== 'string') {
        return Promise.reject(new Error('Invalid Lottie URL.'));
    }
    if (lottieDataCache.has(url)) {
        return Promise.resolve(lottieDataCache.get(url));
    }
    if (lottieDataPromises.has(url)) {
        return lottieDataPromises.get(url);
    }

    const request = fetch(url, {
        mode: 'cors',
        credentials: 'omit',
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Lottie request failed with status ${response.status}.`);
            }
            return response.json();
        })
        .then(data => {
            lottieDataCache.set(url, data);
            lottieDataPromises.delete(url);
            return data;
        })
        .catch(error => {
            lottieDataPromises.delete(url);
            throw error;
        });

    lottieDataPromises.set(url, request);
    return request;
}

function fetchLottieAnimationData(urls) {
    const uniqueUrls = Array.isArray(urls) ? urls.filter(url => typeof url === 'string' && url) : [];
    if (uniqueUrls.length === 0) {
        return Promise.reject(new Error('No Lottie sources available.'));
    }

    let attemptIndex = 0;
    const attempt = (lastError) => {
        if (attemptIndex >= uniqueUrls.length) {
            return Promise.reject(lastError || new Error('All Lottie sources failed.'));
        }
        const currentUrl = uniqueUrls[attemptIndex];
        attemptIndex += 1;
        return fetchLottieData(currentUrl)
            .then(data => ({ data, url: currentUrl }))
            .catch(error => attempt(error));
    };

    return attempt();
}

function createFallbackImage(media) {
    const sources = collectFallbackSources(media);
    if (sources.length === 0) {
        return null;
    }

    const img = document.createElement('img');
    img.classList.add('chat-image');
    img.alt = '';
    img.loading = 'lazy';
    let index = 0;

    const applySource = () => {
        if (index >= sources.length) {
            img.remove();
            return;
        }
        img.src = sources[index];
    };

    img.addEventListener('load', scrollChatToBottom);
    img.addEventListener('error', () => {
        index += 1;
        applySource();
    });

    applySource();
    return img;
}

function createLottieElement(media) {
    if (!media || typeof media !== 'object') {
        return createFallbackImage(media);
    }

    const lottieSources = collectLottieSources(media);
    if (lottieSources.length === 0) {
        return createFallbackImage(media);
    }

    const container = document.createElement('div');
    container.classList.add('chat-lottie');

    Promise.all([loadLottieLibrary(), fetchLottieAnimationData(lottieSources)])
        .then(([lottie, payload]) => {
            if (!container.isConnected) {
                return;
            }
            const animation = lottie.loadAnimation({
                container,
                renderer: 'svg',
                loop: media.loop !== false,
                autoplay: media.autoplay !== false,
                animationData: payload.data,
                rendererSettings: {
                    preserveAspectRatio: 'xMidYMid meet',
                },
            });
            container.dataset.lottieUrl = payload.url;
            container._lottieAnimation = animation;
            animation.addEventListener('DOMLoaded', scrollChatToBottom);
        })
        .catch(error => {
            if (!container.isConnected) {
                return;
            }
            console.warn('Failed to load Lottie animation.', error);
            const fallback = createFallbackImage(media);
            if (fallback) {
                container.replaceWith(fallback);
                scrollChatToBottom();
            } else {
                container.remove();
            }
        });

    return container;
}

function createCustomEmojiElement(name, id, animated) {
    if (!id) {
        return document.createTextNode(`:${name}:`);
    }

    const img = document.createElement('img');
    img.classList.add('custom-emoji');
    img.alt = `:${name}:`;
    img.decoding = 'async';
    img.loading = 'lazy';
    img.addEventListener('load', scrollChatToBottom);

    const extensions = animated ? ['gif', 'webp', 'png'] : ['webp', 'png', 'gif'];
    let index = 0;

    const buildUrl = (ext, bust = false) => {
        const queryParts = ext === 'gif' ? ['size=96'] : ['size=96', 'quality=lossless'];
        if (bust) {
            queryParts.push(`retry=${Date.now()}`);
        }
        const query = queryParts.length ? `?${queryParts.join('&')}` : '';
        return `${CUSTOM_EMOJI_CDN_BASE}/${id}.${ext}${query}`;
    };

    const applySource = (bust = false) => {
        const ext = extensions[index];
        img.src = buildUrl(ext, bust);
    };

    img.addEventListener('error', () => {
        index += 1;
        if (index < extensions.length) {
            applySource(true);
            return;
        }
        img.replaceWith(document.createTextNode(`:${name}:`));
    });

    applySource();
    return img;
}

function renderContentSegments(segments) {
    const fragment = document.createDocumentFragment();
    if (!Array.isArray(segments) || segments.length === 0) {
        return fragment;
    }

    segments.forEach(segment => {
        if (!segment || typeof segment !== 'object') {
            return;
        }
        if (segment.type === 'emoji' && segment.id) {
            fragment.appendChild(
                createCustomEmojiElement(segment.name, segment.id, Boolean(segment.animated))
            );
            return;
        }
        if (segment.type === 'text' && typeof segment.content === 'string') {
            const parts = segment.content.split(/\n/);
            parts.forEach((part, index) => {
                if (part) {
                    fragment.appendChild(document.createTextNode(part));
                }
                if (index < parts.length - 1) {
                    fragment.appendChild(document.createElement('br'));
                }
            });
        }
    });

    return fragment;
}

function renderTextWithCustomEmojis(text) {
    const fragment = document.createDocumentFragment();
    if (!text) {
        return fragment;
    }

    CUSTOM_EMOJI_PATTERN.lastIndex = 0;
    let lastIndex = 0;
    let match;

    while ((match = CUSTOM_EMOJI_PATTERN.exec(text)) !== null) {
        const before = text.slice(lastIndex, match.index);
        if (before) {
            fragment.appendChild(document.createTextNode(before));
        }
        const name = match[1];
        const id = match[2] || '';
        const animated = match[0].startsWith('<a:');
        if (id) {
            fragment.appendChild(createCustomEmojiElement(name, id, animated));
        } else {
            fragment.appendChild(document.createTextNode(match[0]));
        }
        lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    return fragment;
}


let lastRenderedPayload = '';
let lastRenderedSnapshot = [];

function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
}

function createMediaElement(media) {
    if (!media) {
        return null;
    }

    const type = (media.type || '').toLowerCase();

    if (type === 'lottie') {
        const element = createLottieElement(media);
        if (element) {
            return element;
        }
        return null;
    }

    if (!media.url) {
        return createFallbackImage(media);
    }

    if (type === 'video') {
        const video = document.createElement('video');
        video.src = media.url;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.preload = 'auto';
        video.classList.add('chat-video');
        video.addEventListener('loadeddata', scrollChatToBottom);
        return video;
    }

    const img = document.createElement('img');
    img.alt = '';
    img.loading = 'lazy';
    img.classList.add('chat-image');
    img.addEventListener('load', scrollChatToBottom);

    const fallbackSources = collectFallbackSources(media);
    let fallbackIndex = 0;
    if (fallbackSources.length > 0) {
        img.addEventListener('error', () => {
            if (fallbackIndex >= fallbackSources.length) {
                img.remove();
                return;
            }
            img.src = fallbackSources[fallbackIndex];
            fallbackIndex += 1;
        });
    }

    img.src = media.url;
    return img;
}

function renderMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message');

    const contentWrapper = document.createElement('div');
    contentWrapper.classList.add('message-content');

    const shouldShowUsername = !embedOptions.hideUsernames;
    if (shouldShowUsername) {
        const header = document.createElement('span');
        header.classList.add('username');
        header.style.color = message.role_color || 'var(--username-color-default)';
        header.textContent = `${message.author}:`;
        contentWrapper.appendChild(header);
    }

    const segments = Array.isArray(message.content_segments) ? message.content_segments : null;
    const textContent = (message.content || '').trim();
    const hasSegments = Array.isArray(segments) && segments.length > 0;

    if (hasSegments || textContent.length > 0) {
        const contentText = document.createElement('span');
        contentText.classList.add('message-text');
        if (shouldShowUsername) {
            contentText.appendChild(document.createTextNode(' '));
        }

        if (hasSegments) {
            const segmentFragment = renderContentSegments(segments);
            if (segmentFragment.childNodes.length > 0) {
                contentText.appendChild(segmentFragment);
            }
        } else {
            contentText.appendChild(renderTextWithCustomEmojis(textContent));
        }

        const minimumNodes = shouldShowUsername ? 2 : 1;
        if (contentText.childNodes.length >= minimumNodes) {
            contentWrapper.appendChild(contentText);
        }
    }

    const mediaItems = Array.isArray(message.media) ? message.media : [];
    if (mediaItems.length > 0) {
        const gallery = document.createElement('div');
        gallery.classList.add('media-gallery');
        mediaItems.forEach(media => {
            const element = createMediaElement(media);
            if (element) {
                gallery.appendChild(element);
            }
        });
        if (gallery.children.length > 0) {
            contentWrapper.appendChild(gallery);
        }
    }

    messageElement.appendChild(contentWrapper);
    return messageElement;
}

function renderChat(data) {
    const payload = JSON.stringify(data);
    if (payload === lastRenderedPayload) {
        return;
    }

    const chatBox = document.getElementById('chat');

    const previousCount = lastRenderedSnapshot.length;
    const newCount = data.length;

    const samePrefix = previousCount > 0 && newCount >= previousCount
        ? JSON.stringify(data.slice(0, previousCount)) === JSON.stringify(lastRenderedSnapshot)
        : false;

    if (!samePrefix) {
        chatBox.innerHTML = '';
    }

    const startIndex = samePrefix ? previousCount : 0;
    for (let i = startIndex; i < newCount; i += 1) {
        chatBox.appendChild(renderMessage(data[i]));
    }

    lastRenderedPayload = payload;
    lastRenderedSnapshot = cloneData(data);

    scrollChatToBottom();
}

function fetchChat() {
    fetch(chatEndpoint, {
        headers: {
            Accept: 'application/json',
        },
    })
        .then(response => response.json())
        .then(renderChat)
        .catch(error => console.error('Error fetching chat messages:', error));
}

fetchChat();
setInterval(fetchChat, 1000);
