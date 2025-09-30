(function () {
    const DEFAULTS = {
        width: '100%',
        height: '480px',
        minHeight: 0,
        maxHeight: null,
        transparent: false,
        autoResize: false,
        hideUsernames: false,
        loading: 'lazy',
        title: 'Discord Chat',
    };
    const iframeRegistry = new Map();
    let messageListenerRegistered = false;
    function parseBoolean(value, fallback) {
        if (value == null) {
            return fallback;
        }
        const normalized = String(value).trim().toLowerCase();
        if (!normalized) {
            return fallback;
        }
        if (['1', 'true', 'yes', 'y'].includes(normalized)) {
            return true;
        }
        if (['0', 'false', 'no', 'n'].includes(normalized)) {
            return false;
        }
        return fallback;
    }
    function parseNumber(value) {
        if (value == null || value === '') {
            return null;
        }
        const number = Number(value);
        return Number.isFinite(number) ? number : null;
    }
    function normalizeBase(origin) {
        if (!origin) {
            throw new Error('DiscordChatEmbed: "origin" option is required.');
        }
        const url = new URL(origin);
        let path = url.pathname || '/';
        const lowerPath = path.toLowerCase();
        if (lowerPath.endsWith('/index.html')) {
            path = path.slice(0, -'/index.html'.length);
        }
        const pathAfterIndex = path || '/';
        let lower = pathAfterIndex.toLowerCase();
        if (lower.endsWith('/chat/')) {
            path = pathAfterIndex.slice(0, -'/chat/'.length);
        } else if (lower.endsWith('/chat')) {
            path = pathAfterIndex.slice(0, -'/chat'.length);
        } else {
            path = pathAfterIndex;
        }
        if (!path) {
            path = '/';
        }
        if (!path.endsWith('/')) {
            path += '/';
        }
        url.pathname = path;
        url.search = '';
        url.hash = '';
        return url;
    }
    function setOptionalParam(url, key, value) {
        if (value == null || value === '') {
            return;
        }
        url.searchParams.set(key, value);
    }
    function buildEmbedUrl(origin, options = {}) {
        const originValue = (options.origin || origin || '').trim();
        if (!originValue) {
            throw new Error('DiscordChatEmbed: "origin" is required to build an embed URL.');
        }
        const base = normalizeBase(originValue);
        const embedUrl = new URL(base.toString());
        embedUrl.searchParams.set('embed', '1');

        const requestedTarget = (options.chatTarget || options.feedTarget || '').toString().trim().toLowerCase();
        if (requestedTarget) {
            embedUrl.searchParams.set('chat_target', requestedTarget);
        }

        if (parseBoolean(options.transparent, DEFAULTS.transparent)) {
            embedUrl.searchParams.set('transparent', '1');
        }
        const hideNames = parseBoolean(options.hideUsernames, DEFAULTS.hideUsernames);
        embedUrl.searchParams.set('hide_usernames', hideNames ? '1' : '0');
        const autoResize = parseBoolean(options.autoResize, DEFAULTS.autoResize);
        embedUrl.searchParams.set('auto_resize', autoResize ? '1' : '0');
        setOptionalParam(embedUrl, 'bg', options.background);
        setOptionalParam(embedUrl, 'background', options.background);
        setOptionalParam(embedUrl, 'message_bg', options.messageBackground);
        setOptionalParam(embedUrl, 'message_background', options.messageBackground);
        setOptionalParam(embedUrl, 'text_color', options.textColor);
        setOptionalParam(embedUrl, 'message_color', options.textColor);
        setOptionalParam(embedUrl, 'username_color', options.usernameColor);
        setOptionalParam(embedUrl, 'name_color', options.usernameColor);
        setOptionalParam(embedUrl, 'font', options.font);
        setOptionalParam(embedUrl, 'api_origin', options.chatApiOrigin);
        if (options.params && typeof options.params === 'object') {
            Object.keys(options.params).forEach(key => {
                const value = options.params[key];
                if (value != null && value !== '') {
                    embedUrl.searchParams.set(key, value);
                }
            });
        }
        return embedUrl.toString();
    }
    function registerMessageListener() {
        if (messageListenerRegistered) {
            return;
        }
        window.addEventListener('message', handleMessage);
        messageListenerRegistered = true;
    }
    function handleMessage(event) {
        const { data, source } = event;
        if (!data || data.source !== 'discord-chat-to-obs' || data.type !== 'size') {
            return;
        }
        for (const [iframe, options] of iframeRegistry.entries()) {
            if (iframe.contentWindow !== source) {
                continue;
            }
            if (!iframe.isConnected) {
                iframeRegistry.delete(iframe);
                break;
            }
            if (options.autoResize && typeof data.height === 'number') {
                let nextHeight = data.height;
                if (typeof options.minHeight === 'number') {
                    nextHeight = Math.max(nextHeight, options.minHeight);
                }
                if (typeof options.maxHeight === 'number') {
                    nextHeight = Math.min(nextHeight, options.maxHeight);
                }
                iframe.style.height = `${Math.ceil(Math.max(nextHeight, 0))}px`;
            }
            if (typeof options.onResize === 'function') {
                options.onResize({
                    height: data.height,
                    event,
                    iframe,
                });
            }
            break;
        }
    }
    function createIframe(userOptions = {}) {
        const options = { ...DEFAULTS, ...userOptions };
        if (!options.origin) {
            throw new Error('DiscordChatEmbed: "origin" option is required when creating an iframe.');
        }
        const src = buildEmbedUrl(options.origin, options);
        const iframe = document.createElement('iframe');
        iframe.src = src;
        iframe.style.border = '0';
        iframe.style.width = options.width || DEFAULTS.width;
        const initialHeight = options.height || DEFAULTS.height;
        if (initialHeight) {
            iframe.style.height = initialHeight;
        }
        if (options.maxHeight != null) {
            const maxHeightValue = typeof options.maxHeight === 'number' ? `${options.maxHeight}px` : String(options.maxHeight);
            iframe.style.maxHeight = maxHeightValue;
        }
        if (options.minHeight != null) {
            const minHeightValue = typeof options.minHeight === 'number' ? `${options.minHeight}px` : String(options.minHeight);
            iframe.style.minHeight = minHeightValue;
        }
        iframe.setAttribute('allow', 'autoplay');
        iframe.setAttribute('scrolling', 'no');
        iframe.loading = options.loading || DEFAULTS.loading;
        iframe.title = options.title || DEFAULTS.title;
        iframe.dataset.discordChatEmbed = 'true';
        if (parseBoolean(options.transparent, DEFAULTS.transparent)) {
            iframe.setAttribute('allowtransparency', 'true');
            iframe.style.backgroundColor = 'transparent';
        }
        if (options.className) {
            iframe.className = options.className;
        }
        const registryEntry = {
            autoResize: parseBoolean(options.autoResize, DEFAULTS.autoResize),
            minHeight: parseNumber(options.minHeight),
            maxHeight: parseNumber(options.maxHeight),
            onResize: typeof options.onResize === 'function' ? options.onResize : null,
        };
        if (registryEntry.autoResize || registryEntry.onResize) {
            if (registryEntry.minHeight == null) {
                registryEntry.minHeight = DEFAULTS.minHeight;
            }
            if (registryEntry.maxHeight == null && DEFAULTS.maxHeight != null) {
                registryEntry.maxHeight = DEFAULTS.maxHeight;
            }
            iframeRegistry.set(iframe, registryEntry);
            registerMessageListener();
        }
        return iframe;
    }
    function resolveTarget(target) {
        if (target instanceof Element) {
            return target;
        }
        if (typeof target === 'string') {
            const element = document.querySelector(target);
            if (!element) {
                throw new Error(`DiscordChatEmbed: Unable to find target element for selector "${target}".`);
            }
            return element;
        }
        throw new Error('DiscordChatEmbed: target must be a DOM element or selector string.');
    }
    function mount(target, userOptions = {}) {
        const container = resolveTarget(target);
        const iframe = createIframe(userOptions);
        container.appendChild(iframe);
        return iframe;
    }
    function getCurrentScript() {
        return document.currentScript || (function () {
            const scripts = document.getElementsByTagName('script');
            return scripts[scripts.length - 1] || null;
        })();
    }
    function autoMountFromScript(script) {
        if (!script) {
            return;
        }
        const dataset = script.dataset || {};
        const origin = (dataset.origin || dataset.chatOrigin || '').trim();
        const targetSelector = (dataset.target || dataset.chatTarget || '').trim();
        if (!origin || !targetSelector) {
            return;
        }
        const options = {
            origin,
            width: dataset.width || dataset.chatWidth || DEFAULTS.width,
            height: dataset.height || dataset.chatHeight || DEFAULTS.height,
            background: dataset.background || dataset.bg,
            messageBackground: dataset.messageBackground || dataset.messageBg,
            textColor: dataset.textColor || dataset.messageColor || dataset.textColour,
            usernameColor: dataset.usernameColor || dataset.nameColor,
            font: dataset.font || dataset.fontFamily,
            transparent: parseBoolean(dataset.transparent, DEFAULTS.transparent),
            hideUsernames: parseBoolean(dataset.hideUsernames, DEFAULTS.hideUsernames),
            autoResize: parseBoolean(dataset.autoResize, DEFAULTS.autoResize),
            minHeight: parseNumber(dataset.minHeight),
            maxHeight: parseNumber(dataset.maxHeight),
            className: dataset.className,
            loading: dataset.loading,
            title: dataset.title,
        };
        if (dataset.apiOrigin) {
            options.chatApiOrigin = dataset.apiOrigin;
        }
        const datasetTarget = (dataset.chatTarget || dataset.feedTarget || '').trim();
        if (datasetTarget) {
            options.chatTarget = datasetTarget;
        }
        try {
            mount(targetSelector, options);
        } catch (error) {
            console.error('DiscordChatEmbed: failed to mount widget automatically.', error);
        }
    }
    const api = {
        buildUrl: buildEmbedUrl,
        createIframe,
        mount,
    };
    Object.defineProperty(window, 'DiscordChatEmbed', {
        value: api,
        writable: false,
        configurable: false,
    });
    autoMountFromScript(getCurrentScript());
})();
