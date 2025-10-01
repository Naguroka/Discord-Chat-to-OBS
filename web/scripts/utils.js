export function paramIsTrue(value) {
    if (value == null) {
        return false;
    }
    const normalized = String(value).toLowerCase();
    return normalized === "1" || normalized === "true" || normalized === "yes";
}

export function paramIsFalse(value) {
    if (value == null) {
        return false;
    }
    const normalized = String(value).toLowerCase();
    return normalized === "0" || normalized === "false" || normalized === "no";
}

export function parsePositiveNumber(value, fallback) {
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

export function decodeTemplate(value) {
    if (typeof value !== "string") {
        return "";
    }
    try {
        const escapedBackslashes = value.split("\\").join("\\\\");
        const escapedQuotes = escapedBackslashes.split('"').join('\"');
        return JSON.parse(`"${escapedQuotes}"`);
    } catch (error) {
        return value;
    }
}

export function normalizeTemplate(value, fallback) {
    const decoded = decodeTemplate(value);
    if (!decoded || !decoded.trim()) {
        return fallback;
    }
    return decoded;
}

export function escapeHtml(value) {
    if (value == null) {
        return "";
    }
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

export function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
}

export function formatTimestamp(timestamp, showMessageTimestamps) {
    if (!showMessageTimestamps || !timestamp) {
        return "";
    }
    try {
        const date = new Date(timestamp);
        if (Number.isNaN(date.getTime())) {
            return "";
        }
        const hours = date.getHours();
        const hour12 = ((hours + 11) % 12) + 1;
        const minutes = date.getMinutes().toString().padStart(2, "0");
        const hourString = hour12.toString().padStart(2, "0");
        return `${hourString}:${minutes}`;
    } catch (error) {
        console.warn("Failed to format timestamp", error);
        return "";
    }
}

export function setCssVariable(name, value) {
    if (!name) {
        return;
    }
    document.documentElement.style.setProperty(name, value);
}

export function normalizeFont(value) {
    if (!value) {
        return null;
    }
    const trimmed = String(value).trim();
    if (!trimmed) {
        return null;
    }
    switch (trimmed.toLowerCase()) {
        case "system":
            return 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
        case "serif":
            return 'Georgia, "Times New Roman", serif';
        case "mono":
        case "monospace":
            return 'Menlo, Monaco, Consolas, "Courier New", monospace';
        default:
            return trimmed;
    }
}
