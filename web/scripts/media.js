let runtimeConfig = null;
let scrollToBottom = () => {};
let lottieLoaderPromise = null;
const lottieDataCache = new Map();
const lottieDataPromises = new Map();

export function configureMedia(context) {
    runtimeConfig = context.config;
    scrollToBottom = context.scrollToBottom || (() => {});
}

function ensureConfig() {
    if (!runtimeConfig) {
        throw new Error("Media module not configured." );
    }
}

function collectFallbackSources(media) {
    const sources = [];
    if (media && typeof media === "object") {
        if (typeof media.fallback_url === "string") {
            sources.push(media.fallback_url);
        }
        if (Array.isArray(media.fallback_urls)) {
            media.fallback_urls.forEach(url => {
                if (typeof url === "string") {
                    sources.push(url);
                }
            });
        }
        if (typeof media.url === "string") {
            sources.push(media.url);
        }
        if (typeof media.source_url === "string") {
            sources.push(media.source_url);
        }
        if (Array.isArray(media.lottie_urls)) {
            media.lottie_urls.forEach(url => {
                if (typeof url === "string") {
                    sources.push(url);
                }
            });
        }
    }
    return [...new Set(sources)];
}

function collectLottieSources(media) {
    if (!media || typeof media !== "object") {
        return [];
    }
    const sources = [];
    if (Array.isArray(media.lottie_urls)) {
        media.lottie_urls.forEach(url => {
            if (typeof url === "string") {
                sources.push(url);
            }
        });
    }
    if (typeof media.url === "string" && media.url.endsWith('.json')) {
        sources.push(media.url);
    }
    return [...new Set(sources)];
}

function loadLottieLibrary() {
    ensureConfig();
    if (lottieLoaderPromise) {
        return lottieLoaderPromise;
    }
    const existing = window.lottie || window.bodymovin;
    if (existing) {
        lottieLoaderPromise = Promise.resolve(existing);
        return lottieLoaderPromise;
    }
    const script = document.createElement("script");
    script.src = runtimeConfig.lottieCdnUrl;
    script.async = true;
    script.crossOrigin = "anonymous";

    lottieLoaderPromise = new Promise((resolve, reject) => {
        script.addEventListener("load", () => {
            if (window.lottie || window.bodymovin) {
                resolve(window.lottie || window.bodymovin);
            } else {
                reject(new Error("Lottie library failed to initialize."));
            }
        });
        script.addEventListener("error", () => {
            reject(new Error("Failed to load Lottie library."));
        });
    });

    document.head.appendChild(script);
    return lottieLoaderPromise;
}

function fetchLottieData(url) {
    if (!url || typeof url !== "string") {
        return Promise.reject(new Error("Invalid Lottie URL."));
    }
    if (lottieDataCache.has(url)) {
        return Promise.resolve(lottieDataCache.get(url));
    }
    if (lottieDataPromises.has(url)) {
        return lottieDataPromises.get(url);
    }

    const request = fetch(url, {
        mode: "cors",
        credentials: "omit",
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
    const uniqueUrls = Array.isArray(urls) ? urls.filter(url => typeof url === "string" && url) : [];
    if (uniqueUrls.length === 0) {
        return Promise.reject(new Error("No Lottie sources available."));
    }

    let attemptIndex = 0;
    const attempt = lastError => {
        if (attemptIndex >= uniqueUrls.length) {
            return Promise.reject(lastError || new Error("All Lottie sources failed."));
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

    const img = document.createElement("img");
    img.classList.add("chat-image");
    img.alt = "";
    img.loading = "lazy";
    let index = 0;

    const applySource = () => {
        if (index >= sources.length) {
            img.remove();
            return;
        }
        img.src = sources[index];
    };

    img.addEventListener("load", scrollToBottom);
    img.addEventListener("error", () => {
        index += 1;
        applySource();
    });

    applySource();
    return img;
}

function createLottieElement(media) {
    ensureConfig();
    if (!media || typeof media !== "object") {
        return createFallbackImage(media);
    }

    const lottieSources = collectLottieSources(media);
    if (lottieSources.length === 0) {
        return createFallbackImage(media);
    }

    const container = document.createElement("div");
    container.classList.add("chat-lottie");

    Promise.all([loadLottieLibrary(), fetchLottieAnimationData(lottieSources)])
        .then(([lottie, payload]) => {
            if (!container.isConnected) {
                return;
            }
            const animation = lottie.loadAnimation({
                container,
                renderer: "svg",
                loop: media.loop !== false,
                autoplay: media.autoplay !== false,
                animationData: payload.data,
                rendererSettings: {
                    preserveAspectRatio: "xMidYMid meet",
                },
            });
            container.dataset.lottieUrl = payload.url;
            container._lottieAnimation = animation;
            animation.addEventListener("DOMLoaded", scrollToBottom);
        })
        .catch(error => {
            if (!container.isConnected) {
                return;
            }
            console.warn("Failed to load Lottie animation.", error);
            const fallback = createFallbackImage(media);
            if (fallback) {
                container.replaceWith(fallback);
                scrollToBottom();
            } else {
                container.remove();
            }
        });

    return container;
}

function createCustomEmojiElement(name, id, animated) {
    ensureConfig();
    if (!id) {
        return document.createTextNode(`:${name}:`);
    }

    const img = document.createElement("img");
    img.classList.add("custom-emoji");
    img.alt = `:${name}:`;
    img.decoding = "async";
    img.loading = "lazy";
    img.addEventListener("load", scrollToBottom);

    const extensions = animated ? ["gif", "webp", "png"] : ["webp", "png", "gif"];
    let index = 0;

    const buildUrl = (ext, bust = false) => {
        const queryParts = ext === "gif" ? ["size=96"] : ["size=96", "quality=lossless"];
        if (bust) {
            queryParts.push(`retry=${Date.now()}`);
        }
        const query = queryParts.length ? `?${queryParts.join("&")}` : "";
        return `${runtimeConfig.customEmojiCdnBase}/${id}.${ext}${query}`;
    };

    const applySource = (bust = false) => {
        const ext = extensions[index];
        img.src = buildUrl(ext, bust);
    };

    img.addEventListener("error", () => {
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

export function renderContentSegments(segments) {
    const fragment = document.createDocumentFragment();
    if (!Array.isArray(segments) || segments.length === 0) {
        return fragment;
    }

    segments.forEach(segment => {
        if (!segment || typeof segment !== "object") {
            return;
        }
        if (segment.type === "emoji" && segment.id) {
            fragment.appendChild(
                createCustomEmojiElement(segment.name, segment.id, Boolean(segment.animated))
            );
            return;
        }
        if (segment.type === "text" && typeof segment.content === "string") {
            const parts = segment.content.split(/\n/);
            parts.forEach((part, index) => {
                if (part) {
                    fragment.appendChild(document.createTextNode(part));
                }
                if (index < parts.length - 1) {
                    fragment.appendChild(document.createElement("br"));
                }
            });
        }
    });

    return fragment;
}

export function renderTextWithCustomEmojis(text) {
    ensureConfig();
    const fragment = document.createDocumentFragment();
    if (!text) {
        return fragment;
    }

    const pattern = new RegExp(runtimeConfig.customEmojiPattern.source, runtimeConfig.customEmojiPattern.flags);
    pattern.lastIndex = 0;
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(text)) !== null) {
        const before = text.slice(lastIndex, match.index);
        if (before) {
            fragment.appendChild(document.createTextNode(before));
        }
        const name = match[1];
        const id = match[2] || "";
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

export function createMediaElement(media) {
    if (!media) {
        return null;
    }

    const type = (media.type || "").toLowerCase();

    if (type === "lottie") {
        const element = createLottieElement(media);
        if (element) {
            return element;
        }
        return null;
    }

    if (!media.url) {
        return createFallbackImage(media);
    }

    if (type === "video") {
        const video = document.createElement("video");
        video.src = media.url;
        video.autoplay = true;
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.preload = "auto";
        video.classList.add("chat-video");
        video.addEventListener("loadeddata", scrollToBottom);
        return video;
    }

    const img = document.createElement("img");
    img.alt = "";
    img.loading = "lazy";
    img.classList.add("chat-image");
    img.addEventListener("load", scrollToBottom);

    const fallbackSources = collectFallbackSources(media);
    let fallbackIndex = 0;

    if (fallbackSources.length > 0) {
        img.addEventListener("error", () => {
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

