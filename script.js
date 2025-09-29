const FALLBACK_API_ORIGIN = 'http://localhost:8080';
const currentOrigin = `${window.location.protocol}//${window.location.host}`;
const chatApiOrigin = (window.CHAT_API_ORIGIN || (window.location.port === '8000' ? FALLBACK_API_ORIGIN : currentOrigin)).replace(/\/$/, '');

let lastRenderedPayload = '';
let lastRenderedSnapshot = [];

function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
}

function createMediaElement(media) {
    if (!media || !media.url) {
        return null;
    }

    const type = (media.type || '').toLowerCase();

    if (type === 'video') {
        const video = document.createElement('video');
        video.src = media.url;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.preload = 'auto';
        video.classList.add('chat-video');
        return video;
    }

    const img = document.createElement('img');
    img.src = media.url;
    img.alt = '';
    img.loading = 'lazy';
    img.classList.add('chat-image');
    return img;
}

function renderMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message');

    const contentWrapper = document.createElement('div');
    contentWrapper.classList.add('message-content');

    const header = document.createElement('span');
    header.classList.add('username');
    header.style.color = message.role_color || '#99aab5';
    header.textContent = `${message.author}:`;
    contentWrapper.appendChild(header);

    const textContent = (message.content || '').trim();
    if (textContent.length > 0) {
        const contentText = document.createElement('span');
        contentText.classList.add('message-text');
        contentText.textContent = ` ${textContent}`;
        contentWrapper.appendChild(contentText);
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

    chatBox.scrollTop = chatBox.scrollHeight;
}

function fetchChat() {
    fetch(`${chatApiOrigin}/chat`, {
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
