import { paramIsTrue, setCssVariable, normalizeFont } from "./utils.js";

function normalizeColor(value) {
    if (!value) {
        return null;
    }
    const trimmed = String(value).trim();
    if (!trimmed) {
        return null;
    }
    const lower = trimmed.toLowerCase();
    if (lower === "transparent") {
        return "transparent";
    }
    if (trimmed.startsWith("#")) {
        return trimmed;
    }
    if (/^[0-9a-f]{3,4}$/i.test(trimmed) || /^[0-9a-f]{6,8}$/i.test(trimmed)) {
        return `#${trimmed}`;
    }
    return trimmed;
}

export function applyBackgroundMedia(url) {
    const root = document.documentElement;
    const body = document.body;
    const existingVideo = document.getElementById("chat-background-video");
    if (existingVideo) {
        existingVideo.remove();
    }
    if (body) {
        body.classList.remove("chat-background-video-active");
    }
    root.style.removeProperty("--chat-background-media");
    delete root.dataset.backgroundMedia;

    if (!url || typeof url !== "string") {
        return;
    }
    const trimmed = url.trim();
    if (!trimmed || trimmed.toLowerCase() === "none") {
        return;
    }

    const lower = trimmed.toLowerCase();
    const videoExtensions = [".mp4", ".webm", ".mov", ".m4v"];
    if (videoExtensions.some(ext => lower.endsWith(ext))) {
        if (!body) {
            return;
        }
        const video = document.createElement("video");
        video.id = "chat-background-video";
        video.src = trimmed;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.setAttribute("aria-hidden", "true");
        Object.assign(video.style, {
            position: "fixed",
            top: "50%",
            left: "50%",
            width: "auto",
            height: "auto",
            minWidth: "100%",
            minHeight: "100%",
            transform: "translate(-50%, -50%)",
            objectFit: "cover",
            zIndex: "-2",
            opacity: "var(--background-media-opacity, 1)",
        });
        root.dataset.backgroundMedia = "video";
        body.classList.add("chat-background-video-active");
        body.prepend(video);
    } else {
        const escapedUrl = trimmed.replace(/"/g, '\\"');
        root.style.setProperty("--chat-background-media", `url("${escapedUrl}")`);
        root.dataset.backgroundMedia = "image";
    }
}

function applyOpacityPercent(urlParams, variableName, ...paramNames) {
    for (const name of paramNames) {
        const raw = urlParams.get(name);
        if (raw == null) continue;
        const cleaned = String(raw).trim().replace('%', '');
        const num = Number(cleaned);
        if (!Number.isFinite(num)) continue;
        const clamped = Math.max(0, Math.min(100, num));
        // 0 = opaque, 100 = fully transparent  →  alpha = 1 - (p / 100)
        const alpha = 1 - (clamped / 100);
        setCssVariable(variableName, String(alpha));
        return;
    }
}

function setLengthVar(urlParams, cssVar, ...names) {
    for (const n of names) {
        const raw = urlParams.get(n);
        if (!raw) continue;
        const v = String(raw).trim();
        const value = /^\d+(\.\d+)?$/.test(v) ? `${v}px` : v; // allow bare numbers as px
        setCssVariable(cssVar, value);
        return;
    }
}

function applyColorOption(urlParams, variableName, ...paramNames) {
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

function applyOpacityOption(urlParams, variableName, ...paramNames) {
    for (const name of paramNames) {
        const raw = urlParams.get(name);
        if (raw == null) continue;
        const num = Number(String(raw).trim());
        if (Number.isFinite(num) && num >= 0 && num <= 1) {
            setCssVariable(variableName, String(num));
            return;
        }
    }
}

export function applyVisualOptions(urlParams, embedOptions) {
    if (paramIsTrue(urlParams.get("transparent"))) {
        setCssVariable("--chat-background", "transparent");
    }
    applyColorOption(urlParams, "--chat-background", "background", "bg", "chat_bg");
    applyColorOption(urlParams, "--message-background", "message_background", "message_bg", "bubble_bg");
    applyColorOption(urlParams, "--message-color", "text_color", "message_color");
    applyColorOption(urlParams, "--username-color-default", "username_color", "name_color");
    applyColorOption(urlParams, "--author-color", "author_color");
    applyColorOption(urlParams, "--timestamp-color", "timestamp_color", "time_color");

    // --- New: single bubble padding knob ---
    // Accepts bare numbers (px) or any CSS length (e.g., 12px, 0.8rem).
    const setLengthPx = (cssVar, ...names) => {
        for (const n of names) {
            const raw = urlParams.get(n);
            if (!raw) {
                continue;
            }
            const v = String(raw).trim();
            const value = /^\d+(\.\d+)?$/.test(v) ? `${v}px` : v;
            setCssVariable(cssVar, value);
            break;
        }
    };
    setLengthPx("--bubble-padding", "bubble_padding", "bubble_pad", "padding_all");

    // --- New: line-height knob for message content ---
    // Accepts unitless (e.g., 1.15) or any CSS value (e.g., 120%, 18px).
    const setLineHeight = (...names) => {
        for (const n of names) {
            const raw = urlParams.get(n);
            if (!raw) {
                continue;
            }
            const v = String(raw).trim();
            const value = /^\d+(\.\d+)?$/.test(v) ? v : v;
            setCssVariable("--message-line-height", value);
            break;
        }
    };
    setLineHeight("line_height", "message_line_height", "lh");

    // Avatar & emoji sizing (allow bare numbers meaning px, or explicit units)
    setLengthPx("--avatar-size", "avatar_size");
    setLengthPx("--avatar-width", "avatar_width");
    setLengthPx("--avatar-height", "avatar_height");
    setLengthPx("--emoji-size", "emoji_size");
    setLengthPx("--message-line-gap", "line_gap");
    // Transparency sliders: 0=opaque, 100=fully transparent
    applyOpacityPercent(urlParams, "--background-media-opacity", "background_transparency", "bg_transparency", "background_opacity_percent");
    applyOpacityPercent(urlParams, "--message-background-opacity", "bubble_transparency", "message_bg_transparency", "bubble_opacity_percent", "message_bg_opacity_percent");

    // Text wrapping & inner width bounds for message bubbles
    const wrapParam = (urlParams.get("wrap") || urlParams.get("wrap_text") || "").toLowerCase();
    if (wrapParam) {
        let whiteSpace = "normal";
        if (["nowrap", "no", "off", "0"].includes(wrapParam)) whiteSpace = "nowrap";
        else if (wrapParam === "pre") whiteSpace = "pre";
        else if (wrapParam === "pre-wrap" || wrapParam === "prewrap") whiteSpace = "pre-wrap";
        setCssVariable("--message-white-space", whiteSpace);
    }
    const msgMaxW = urlParams.get("message_max_width") || urlParams.get("msg_max_w");
    if (msgMaxW) setCssVariable("--message-max-width", msgMaxW);
    const msgMinW = urlParams.get("message_min_width") || urlParams.get("msg_min_w");
    if (msgMinW) setCssVariable("--message-min-width", msgMinW);

    const fontParam = urlParams.get("font");
    const normalizedFont = normalizeFont(fontParam);
    if (normalizedFont) {
        setCssVariable("--chat-font-family", normalizedFont);
    }

    if (embedOptions.embedMode) {
        document.documentElement.classList.add("embed-mode");
        if (document.body) {
            document.body.classList.add("embed-mode");
        } else {
            window.addEventListener(
                "DOMContentLoaded",
                () => {
                    document.body.classList.add("embed-mode");
                },
                { once: true },
            );
        }
    }
}

export function createDomHelpers(embedOptions) {
    let lastReportedHeight = 0;

    function reportEmbedSize(chatElement) {
        if (!embedOptions.embedMode || !embedOptions.autoResize || window === window.parent) {
            return;
        }
        const element = chatElement || document.getElementById("chat");
        if (!element) {
            return;
        }
        const rect = element.getBoundingClientRect();
        const renderedHeight = Math.ceil((rect && rect.height) || element.clientHeight || element.scrollHeight);
        const frameHeight = typeof embedOptions.frameHeight === "number" ? embedOptions.frameHeight : null;
        const maxHeight = typeof embedOptions.maxHeight === "number" ? embedOptions.maxHeight : frameHeight;
        const targetHeight = maxHeight ? Math.min(renderedHeight, maxHeight) : renderedHeight;
        if (targetHeight !== lastReportedHeight) {
            lastReportedHeight = targetHeight;
            try {
                window.parent.postMessage(
                    {
                        source: "discord-chat-to-obs",
                        type: "size",
                        height: targetHeight,
                    },
                    "*",
                );
            } catch (error) {
                console.warn("Failed to post resize message", error);
            }
        }
    }

    function scrollChatToBottom() {
        const chatBox = document.getElementById("chat");
        if (!chatBox) {
            return;
        }
        const schedule = window.requestAnimationFrame || function (fn) {
            return setTimeout(fn, 16);
        };
        schedule(() => {
            try {
                chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
            } catch (error) {
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            reportEmbedSize(chatBox);
        });
    }

    return { scrollChatToBottom, reportEmbedSize };
}


