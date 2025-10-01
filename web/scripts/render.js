import { escapeHtml, formatTimestamp, cloneData } from "./utils.js";
import { renderContentSegments, renderTextWithCustomEmojis, createMediaElement } from "./media.js";
import { state } from "./state.js";

let runtimeConfig = null;
let scrollToBottom = () => {};
const EMBED_ACCENT_FALLBACK = "rgba(88, 101, 242, 0.85)";

function safeString(value) {
    if (typeof value !== "string") {
        return "";
    }
    return value.trim();
}

function appendTextWithBreaks(target, text) {
    if (!target || typeof text !== "string") {
        return;
    }
    const parts = text.split(/\r?\n/);
    parts.forEach((part, index) => {
        if (part) {
            target.appendChild(document.createTextNode(part));
        }
        if (index < parts.length - 1) {
            target.appendChild(document.createElement("br"));
        }
    });
}

function formatEmbedTimestampValue(timestampIso) {
    if (!timestampIso || typeof timestampIso !== "string") {
        return "";
    }
    const showTimestamps = runtimeConfig ? runtimeConfig.showMessageTimestamps : true;
    const formatted = formatTimestamp(timestampIso, showTimestamps);
    if (formatted) {
        return formatted;
    }
    try {
        const date = new Date(timestampIso);
        if (!Number.isNaN(date.getTime())) {
            return date.toLocaleString(undefined, { hour: '2-digit', minute: '2-digit' });
        }
    } catch (error) {
        // ignore invalid dates
    }
    return timestampIso;
}

function renderEmbedBlocks(embeds) {
    if (!Array.isArray(embeds) || embeds.length === 0) {
        return null;
    }
    const container = document.createElement("div");
    container.classList.add("message-embeds");
    embeds.forEach(embed => {
        const element = createEmbedElement(embed);
        if (element) {
            container.appendChild(element);
        }
    });
    return container.childNodes.length > 0 ? container : null;
}

function createEmbedElement(embed) {
    if (!embed || typeof embed !== "object") {
        return null;
    }

    const title = safeString(embed.title);
    const description = safeString(embed.description);
    const imageUrl = safeString(embed.image_url);
    const thumbnailUrl = safeString(embed.thumbnail_url);
    const videoUrl = safeString(embed.video_url);
    const fields = Array.isArray(embed.fields) ? embed.fields : [];
    const hasFieldContent = fields.some(field => field && (safeString(field.name) || safeString(field.value)));

    const author = embed.author && typeof embed.author === "object" ? embed.author : null;
    const authorName = author ? safeString(author.name) : "";
    const authorIcon = author ? safeString(author.icon_url) : "";
    const authorUrl = author ? safeString(author.url) : "";

    const footer = embed.footer && typeof embed.footer === "object" ? embed.footer : null;
    const footerTextRaw = footer ? safeString(footer.text) : "";
    const footerIcon = footer ? safeString(footer.icon_url) : "";

    const timestampText = formatEmbedTimestampValue(safeString(embed.timestamp));

    const hasTextContent = Boolean(title || description || authorName || footerTextRaw || timestampText || hasFieldContent);

    if (!hasTextContent && !thumbnailUrl && !imageUrl && !videoUrl) {
        return null;
    }

    const wrapper = document.createElement("div");
    wrapper.classList.add("message-embed");

    const accent = document.createElement("div");
    accent.classList.add("embed-accent");
    const color = safeString(embed.color);
    accent.style.backgroundColor = color || EMBED_ACCENT_FALLBACK;
    wrapper.appendChild(accent);

    const main = document.createElement("div");
    main.classList.add("embed-main");
    wrapper.appendChild(main);

    const body = document.createElement("div");
    body.classList.add("embed-body");
    main.appendChild(body);

    const content = document.createElement("div");
    content.classList.add("embed-content");
    body.appendChild(content);

    if (authorName || authorIcon) {
        const authorRow = document.createElement("div");
        authorRow.classList.add("embed-author");
        if (authorIcon) {
            const authorImage = document.createElement("img");
            authorImage.src = authorIcon;
            authorImage.alt = authorName || 'Embed author';
            authorImage.loading = "lazy";
            authorImage.decoding = "async";
            authorImage.addEventListener("error", () => authorImage.remove());
            authorRow.appendChild(authorImage);
        }
        if (authorName) {
            if (authorUrl) {
                const authorLink = document.createElement("a");
                authorLink.href = authorUrl;
                authorLink.rel = "noopener noreferrer";
                authorLink.target = "_blank";
                authorLink.textContent = authorName;
                authorLink.classList.add("embed-author-name");
                authorRow.appendChild(authorLink);
            } else {
                const authorSpan = document.createElement("span");
                authorSpan.classList.add("embed-author-name");
                authorSpan.textContent = authorName;
                authorRow.appendChild(authorSpan);
            }
        }
        content.appendChild(authorRow);
    }

    if (title) {
        const titleElement = document.createElement("div");
        titleElement.classList.add("embed-title");
        const titleUrl = safeString(embed.url);
        if (titleUrl) {
            const titleLink = document.createElement("a");
            titleLink.href = titleUrl;
            titleLink.rel = "noopener noreferrer";
            titleLink.target = "_blank";
            titleLink.textContent = title;
            titleElement.appendChild(titleLink);
        } else {
            titleElement.textContent = title;
        }
        content.appendChild(titleElement);
    }

    if (description) {
        const descriptionElement = document.createElement("div");
        descriptionElement.classList.add("embed-description");
        appendTextWithBreaks(descriptionElement, description);
        content.appendChild(descriptionElement);
    }

    if (fields.length > 0) {
        const fieldsContainer = document.createElement("div");
        fieldsContainer.classList.add("embed-fields");
        fields.forEach(field => {
            if (!field || typeof field !== "object") {
                return;
            }
            const name = safeString(field.name);
            const value = safeString(field.value);
            if (!name && !value) {
                return;
            }
            const fieldElement = document.createElement("div");
            fieldElement.classList.add("embed-field");
            if (field.inline) {
                fieldElement.classList.add("inline");
            }
            if (name) {
                const nameElement = document.createElement("div");
                nameElement.classList.add("embed-field-name");
                appendTextWithBreaks(nameElement, name);
                fieldElement.appendChild(nameElement);
            }
            if (value) {
                const valueElement = document.createElement("div");
                valueElement.classList.add("embed-field-value");
                appendTextWithBreaks(valueElement, value);
                fieldElement.appendChild(valueElement);
            }
            fieldsContainer.appendChild(fieldElement);
        });
        if (fieldsContainer.childNodes.length > 0) {
            content.appendChild(fieldsContainer);
        }
    }

    if (footerIcon || footerTextRaw || timestampText) {
        const footerRow = document.createElement("div");
        footerRow.classList.add("embed-footer");
        if (footerIcon) {
            const footerImage = document.createElement("img");
            footerImage.classList.add("embed-footer-icon");
            footerImage.src = footerIcon;
            footerImage.alt = '';
            footerImage.loading = "lazy";
            footerImage.decoding = "async";
            footerImage.addEventListener("error", () => footerImage.remove());
            footerRow.appendChild(footerImage);
        }
        const footerPieces = [];
        if (footerTextRaw) {
            footerPieces.push(footerTextRaw);
        }
        if (timestampText) {
            footerPieces.push(timestampText);
        }
        if (footerPieces.length > 0) {
            const footerTextElement = document.createElement("span");
            footerTextElement.classList.add("embed-footer-text");
            appendTextWithBreaks(footerTextElement, footerPieces.join(' \u2022 '));
            footerRow.appendChild(footerTextElement);
        }
        if (footerRow.childNodes.length > 0) {
            content.appendChild(footerRow);
        }
    }

    if (thumbnailUrl) {
        const thumbnailElement = document.createElement("img");
        thumbnailElement.classList.add("embed-thumbnail");
        thumbnailElement.src = thumbnailUrl;
        thumbnailElement.alt = '';
        thumbnailElement.loading = "lazy";
        thumbnailElement.decoding = "async";
        thumbnailElement.addEventListener("load", scrollToBottom);
        thumbnailElement.addEventListener("error", () => thumbnailElement.remove());
        body.appendChild(thumbnailElement);
    }

    if (imageUrl) {
        const imageElement = document.createElement("img");
        imageElement.classList.add("embed-image");
        imageElement.src = imageUrl;
        imageElement.alt = '';
        imageElement.loading = "lazy";
        imageElement.decoding = "async";
        imageElement.addEventListener("load", scrollToBottom);
        imageElement.addEventListener("error", () => imageElement.remove());
        main.appendChild(imageElement);
    }

    return wrapper;
}

export function configureRenderer(context) {
    runtimeConfig = context.config;
    scrollToBottom = context.scrollToBottom || (() => {});
    return {
        renderChat: data => renderChatInternal(data),
    };
}

function applyMessageTemplate(template, context, buildMessageFragment, fallbackText) {
    let html = template && typeof template === "string" ? template : '{{author}}{{timestamp}}: {{message}}';
    html = html.replace(/\r\n\r\n|\r\n/g, "\r\n");
    html = html.replace(/\r\n/g, "<br>");
    html = html.replace(/{{\s*newline\s*}}/gi, "<br>");
    html = html.replace(/{{\s*message\s*}}/gi, '<span data-template-placeholder="message"></span>');

    const replacements = {
        author: escapeHtml(context.author || ""),
        timestamp: escapeHtml(context.timestamp || ""),
        timestamp_raw: escapeHtml(context.timestamp_raw || ""),
        role_color: escapeHtml(context.role_color || ""),
        avatar_url: escapeHtml(context.avatar_url || ""),
    };

    // Respect whitespace around tokens like {{  author  }}
    Object.entries(replacements).forEach(([key, value]) => {
        const pattern = new RegExp(`{{\\s*${key}\\s*}}`, "gi");
        html = html.replace(pattern, value);
    });

    html = html.replace(/{{\s*[a-z_]+\s*}}/gi, "");

    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;

    let inserted = false;
    wrapper.querySelectorAll('[data-template-placeholder="message"]').forEach(placeholder => {
        const fragment = buildMessageFragment();
        const hasNodes = fragment && fragment.childNodes && fragment.childNodes.length > 0;
        if (hasNodes) {
            placeholder.replaceWith(fragment);
            inserted = true;
        } else {
            // Nothing useful produced; remove placeholder so we can fall back.
            placeholder.remove();
        }
    });

    if (!inserted) {
        const fallback = buildMessageFragment();
        const hasFallbackNodes = fallback && fallback.childNodes && fallback.childNodes.length > 0;
        if (hasFallbackNodes) {
            wrapper.appendChild(fallback);
            inserted = true;
        }
    }

    if (!inserted && typeof fallbackText === "string") {
        const trimmedContent = fallbackText.trim();
        if (trimmedContent) {
            const plainFallback = document.createElement("span");
            plainFallback.textContent = trimmedContent;
            wrapper.appendChild(plainFallback);
            inserted = true;
        }
    }

    const fragment = document.createDocumentFragment();
    while (wrapper.firstChild) {
        fragment.appendChild(wrapper.firstChild);
    }
    return fragment;
}

function renderMessage(message) {
    if (!runtimeConfig) {
        throw new Error("Renderer not configured.");
    }

    const messageElement = document.createElement("div");
    messageElement.classList.add("chat-message");

    // Avatar (show/hide based on runtimeConfig.showAvatars; default = show)
    const avatarUrl = typeof message.avatar_url === "string" ? message.avatar_url.trim() : "";
    const showAvatar = runtimeConfig.showAvatars !== false;
    if (showAvatar && avatarUrl) {
        const avatarWrapper = document.createElement("div");
        avatarWrapper.classList.add("message-avatar");

        const avatarImage = document.createElement("img");
        avatarImage.classList.add("avatar-image");
        avatarImage.src = avatarUrl;
        avatarImage.alt = `${message.author || "User"} avatar`;
        avatarImage.decoding = "async";
        avatarImage.loading = "lazy";
        avatarImage.addEventListener("load", scrollToBottom);
        avatarImage.addEventListener("error", () => avatarWrapper.remove());

        avatarWrapper.appendChild(avatarImage);
        messageElement.appendChild(avatarWrapper);
    }

    const contentWrapper = document.createElement("div");
    contentWrapper.classList.add("message-content");

    // Username/timestamp line
    const shouldShowUsername = !runtimeConfig.embedOptions.hideUsernames;
    const timestampIso = typeof message.timestamp === "string" ? message.timestamp : "";
    const timestampClock = formatTimestamp(timestampIso, runtimeConfig.showMessageTimestamps);
    let timestampDecorated = "";
    if (shouldShowUsername && timestampClock) {
        const template = (typeof runtimeConfig.timestampTemplate === "string" && runtimeConfig.timestampTemplate)
            ? runtimeConfig.timestampTemplate
            : " ({{time}})";
        timestampDecorated = template.replace(/{{\s*time\s*}}/gi, timestampClock);
    }

    // Content sources
    const primaryContent = typeof message.content === "string" ? message.content : "";
    const cleanContent = typeof message.clean_content === "string" ? message.clean_content : "";
    const rawContent   = typeof message.raw_content === "string" ? message.raw_content : "";
    const segments = Array.isArray(message.content_segments) ? message.content_segments : null;
    // If there is playable media (e.g., Tenor mp4/gif), do not echo the raw URL text.
    const hasMedia = Array.isArray(message.media) && message.media.length > 0;
    const fallbackTextCandidates = [primaryContent, cleanContent, rawContent];
    const fallbackText = hasMedia ? "" : (fallbackTextCandidates.find(t => typeof t === "string" && t.trim()) || "");

    const buildMessageFragment = () => {
        if (Array.isArray(segments) && segments.length > 0) {
            return renderContentSegments(segments);
        }
        if (!hasMedia && fallbackText && fallbackText.trim().length > 0) {
            return renderTextWithCustomEmojis(fallbackText);
        }
        return null;
    };

    const template = shouldShowUsername ? runtimeConfig.messageTemplate : runtimeConfig.messageHideTemplate;
    const layoutFragment = applyMessageTemplate(
        template,
        {
            author: message.author || "Unknown",
            timestamp: shouldShowUsername ? timestampDecorated : "",
            timestamp_raw: timestampIso,
            role_color: message.role_color || "",
            avatar_url: avatarUrl,
        },
        buildMessageFragment,
        fallbackText
    );

    if (layoutFragment && layoutFragment.childNodes.length > 0) {
        contentWrapper.appendChild(layoutFragment);
    } else if (!hasMedia && fallbackText) {
        // final safeguard if template produced nothing
        const fallbackNode = document.createElement("span");
        fallbackNode.textContent = fallbackText;
        contentWrapper.appendChild(fallbackNode);
    }

    // Apply Discord role color (template may hard-code a color; override it when enabled)
    const useRoleColor = ("applyRoleColors" in runtimeConfig) ? runtimeConfig.applyRoleColors !== false : true;
    if (useRoleColor && typeof message.role_color === "string" && message.role_color) {
        try {
            // 1) prefer CSS variable used by templates like color: var(--author-color)
            contentWrapper.style.setProperty("--author-color", message.role_color);
            // 2) hard override first likely header element as a fallback
            const headerEl = contentWrapper.querySelector("strong, .username, [data-author]");
            if (headerEl) headerEl.style.color = message.role_color;
        } catch {}
    }

    // Embeds: keep real embeds, but skip "thumbnail-only" embeds when we already have media
    const embeds = Array.isArray(message.embeds) ? message.embeds : [];
    const pureMediaEmbedsOnly = embeds.length > 0 && embeds.every(e => {
        if (!e || typeof e !== "object") return true;
        const title = (e.title || "").trim();
        const desc = (e.description || "").trim();
        const fields = Array.isArray(e.fields) ? e.fields : [];
        const hasFieldText = fields.some(f => f && ((f.name && String(f.name).trim()) || (f.value && String(f.value).trim())));
        const authorName = e.author && (e.author.name || "").trim();
        const footerText = e.footer && (e.footer.text || "").trim();
        const ts = e.timestamp ? String(e.timestamp).trim() : "";
        const hasText = Boolean(title || desc || authorName || footerText || ts || hasFieldText);
        return !hasText;
    });

    if (!(hasMedia && pureMediaEmbedsOnly)) {
        const embedsContainer = renderEmbedBlocks(embeds);
        if (embedsContainer) {
            contentWrapper.appendChild(embedsContainer);
        }
    }

    // Media gallery (declare AFTER logic above; safe to use now)
    const mediaItems = Array.isArray(message.media) ? message.media : [];
    if (mediaItems.length > 0) {
        const gallery = document.createElement("div");
        gallery.classList.add("media-gallery");
        mediaItems.forEach(media => {
            const el = createMediaElement(media);
            if (el) gallery.appendChild(el);
        });
        if (gallery.children.length > 0) {
            contentWrapper.appendChild(gallery);
        }
    }

    messageElement.appendChild(contentWrapper);
    return messageElement;
}


function renderChatInternal(data) {
    if (!runtimeConfig) {
        throw new Error("Renderer not configured.");
    }

    const payload = JSON.stringify(data);
    if (payload === state.lastRenderedPayload) {
        // If DOM is empty (remount) but payload is same, rebuild it.
        const chatBox = document.getElementById("chat");
        if (chatBox && chatBox.childNodes.length === 0) { /* fall through */ } else return;
    }

    const chatBox = document.getElementById("chat");
    if (!chatBox) {
        return;
    }

    const previousCount = state.lastRenderedSnapshot.length;
    const newCount = data.length;

    const samePrefix = previousCount > 0 && newCount >= previousCount
        ? JSON.stringify(data.slice(0, previousCount)) === JSON.stringify(state.lastRenderedSnapshot)
        : false;

    if (!samePrefix) {
        chatBox.innerHTML = "";
    }

    const startIndex = samePrefix ? previousCount : 0;
    for (let i = startIndex; i < newCount; i += 1) {
        chatBox.appendChild(renderMessage(data[i]));
    }

    state.lastRenderedPayload = payload;
    state.lastRenderedSnapshot = cloneData(data);

    scrollToBottom();
}
