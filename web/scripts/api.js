export function startChatPolling(config, renderChat) {
    if (!config || typeof renderChat !== "function") {
        throw new Error("Invalid polling configuration.");
    }

    function fetchChat() {
        fetch(config.chatEndpoint, {
            headers: {
                Accept: "application/json",
            },
        })
            .then(response => response.json())
            .then(renderChat)
            .catch(error => console.error("Error fetching chat messages:", error));
    }

    fetchChat();
    const intervalId = setInterval(fetchChat, config.chatPollIntervalMs);
    return () => clearInterval(intervalId);
}
