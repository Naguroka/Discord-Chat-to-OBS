import { createConfig } from "./config.js";
import { applyBackgroundMedia, applyVisualOptions, createDomHelpers } from "./dom.js";
import { configureMedia } from "./media.js";
import { configureRenderer } from "./render.js";
import { startChatPolling } from "./api.js";
import { setCssVariable } from "./utils.js";

const config = createConfig();

document.documentElement.dataset.chatTarget = config.feedTarget;
if (config.embedMode) {
    document.documentElement.dataset.embedScrollbar = config.showEmbedScrollbar ? "visible" : "hidden";
} else {
    document.documentElement.dataset.embedScrollbar = "";
}

applyBackgroundMedia(config.backgroundMediaPreference);
applyVisualOptions(config.urlParams, config.embedOptions);

if (config.embedMode && typeof config.embedOptions.frameHeight === "number") {
    const height = config.embedOptions.frameHeight;
    const maxHeight = typeof config.embedOptions.maxHeight === "number" ? config.embedOptions.maxHeight : height;
    setCssVariable("--chat-frame-height", `${height}px`);
    setCssVariable("--chat-frame-max-height", `${maxHeight}px`);
} else {
    setCssVariable("--chat-frame-height", "auto");
    setCssVariable("--chat-frame-max-height", "none");
}

const domHelpers = createDomHelpers(config.embedOptions);

configureMedia({
    config,
    scrollToBottom: domHelpers.scrollChatToBottom,
});

const { renderChat } = configureRenderer({
    config,
    scrollToBottom: domHelpers.scrollChatToBottom,
});

startChatPolling(config, renderChat);
