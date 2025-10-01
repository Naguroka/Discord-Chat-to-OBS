import { paramIsTrue, paramIsFalse, parsePositiveNumber, normalizeTemplate } from './utils.js';

export const SHOW_MESSAGE_TIMESTAMPS = true;
export const CHAT_POLL_INTERVAL_MS = 1000;
export const DEFAULT_API_PROTOCOL = window.location.protocol === 'https:' ? 'https:' : 'http:';
export const DEFAULT_API_HOST = window.location.hostname && window.location.hostname !== '' ? window.location.hostname : '127.0.0.1';
export const FALLBACK_API_ORIGIN = ``;
export const SHOW_EMBED_SCROLLBAR = false;
export const SHOW_AVATARS = true;       // show profile pictures by default
export const APPLY_ROLE_COLORS = true;  // tint author by Discord role color by default
export const MESSAGE_LAYOUT_TEMPLATE = '<strong style="color:#ffffff">{{author}} {{timestamp}}</strong><span style="font-size:16px;">{{message}}</span>';
export const MESSAGE_HIDE_USERNAME_TEMPLATE = '{{message}}';
export const TIMESTAMP_TEMPLATE = ' {{time}}';
export const BACKGROUND_MEDIA_URL = '';
export const CUSTOM_EMOJI_PATTERN = /<a?:([a-zA-Z0-9_]+)(?::(\d+))?>/g;
export const CUSTOM_EMOJI_CDN_BASE = 'https://cdn.discordapp.com/emojis';
export const LOTTIE_CDN_URL = 'https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js';

const DEFAULT_MESSAGE_TEMPLATE = '{{author}}{{timestamp}}: {{message}}';
const DEFAULT_HIDE_TEMPLATE = '{{message}}';
const DEFAULT_TIMESTAMP_TEMPLATE = ' ({{time}})';

export function createConfig() {
    const urlParams = new URLSearchParams(window.location.search);
    const embedMode = urlParams.get('embed') === '1' || window !== window.parent;
    const forcedApiOrigin = urlParams.get('api_origin') || urlParams.get('chat_origin') || urlParams.get('origin');

    const currentHost = window.location.host;
    const currentOrigin = `${window.location.protocol}//${currentHost}`;
    const defaultOrigin = window.location.port === '8000' || !currentHost ? FALLBACK_API_ORIGIN : currentOrigin;
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

    const requestedAutoResize = urlParams.get('auto_resize');
    const autoResize = embedMode ? paramIsTrue(requestedAutoResize) : !paramIsFalse(requestedAutoResize);

    const embedOptions = {
        embedMode,
        feedTarget,
        autoResize,
        hideUsernames: paramIsTrue(urlParams.get('hide_usernames')),
    };

    const embedHeightParam = urlParams.get('frame_height') || urlParams.get('embed_height') || (embedMode ? urlParams.get('height') : null);
    const embedMaxHeightParam = urlParams.get('max_height') || urlParams.get('maxHeight');
    if (embedMode) {
        const frameHeightValue = parsePositiveNumber(embedHeightParam, 480);
        const maxHeightValue = parsePositiveNumber(embedMaxHeightParam, frameHeightValue) || frameHeightValue;
        embedOptions.frameHeight = frameHeightValue;
        embedOptions.maxHeight = maxHeightValue;
    }

    const backgroundMediaParam = urlParams.get('background_media') || urlParams.get('backgroundMedia');
    let backgroundMediaPreference = typeof window.BACKGROUND_MEDIA_URL === 'string' ? window.BACKGROUND_MEDIA_URL : BACKGROUND_MEDIA_URL;
    if (backgroundMediaParam != null) {
        try {
            backgroundMediaPreference = decodeURIComponent(backgroundMediaParam);
        } catch (error) {
            backgroundMediaPreference = backgroundMediaParam;
        }
    }
    if (typeof backgroundMediaPreference === 'string') {
        backgroundMediaPreference = backgroundMediaPreference.trim();
    }
    if (backgroundMediaPreference && backgroundMediaPreference.toLowerCase() === 'none') {
        backgroundMediaPreference = '';
    }

    const messageTemplate = normalizeTemplate(MESSAGE_LAYOUT_TEMPLATE, DEFAULT_MESSAGE_TEMPLATE);
    const messageHideTemplate = normalizeTemplate(MESSAGE_HIDE_USERNAME_TEMPLATE, DEFAULT_HIDE_TEMPLATE);
    const timestampTemplate = normalizeTemplate(TIMESTAMP_TEMPLATE, DEFAULT_TIMESTAMP_TEMPLATE);

    // UI/URL toggles
    const hideAvatarsParam = urlParams.get('hide_avatars');
    const showAvatarsParam = urlParams.get('show_avatars');
    const showAvatars = showAvatarsParam != null
        ? paramIsTrue(showAvatarsParam)
        : (hideAvatarsParam != null ? !paramIsTrue(hideAvatarsParam) : SHOW_AVATARS);
    const roleColorsParam = urlParams.get('role_colors');
    const applyRoleColors = roleColorsParam == null ? APPLY_ROLE_COLORS : paramIsTrue(roleColorsParam);

    return {
        urlParams,
        embedMode,
        embedOptions,
        feedTarget,
        chatEndpoint,
        chatApiOrigin,
        chatEndpointPath,
        chatPollIntervalMs: CHAT_POLL_INTERVAL_MS,
        showMessageTimestamps: SHOW_MESSAGE_TIMESTAMPS,
        messageTemplate,
        messageHideTemplate,
        timestampTemplate,
        backgroundMediaPreference,
        showEmbedScrollbar: SHOW_EMBED_SCROLLBAR,
        customEmojiPattern: CUSTOM_EMOJI_PATTERN,
        customEmojiCdnBase: CUSTOM_EMOJI_CDN_BASE,
        lottieCdnUrl: LOTTIE_CDN_URL,
        showAvatars,
        applyRoleColors,
    };
}
