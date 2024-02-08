function fetchChat() {
    fetch('http://localhost:8080/chat')
        .then(response => response.json())
        .then(data => {
            const chatBox = document.getElementById('chat');
            chatBox.innerHTML = ''; // Clear previous messages
            
            data.forEach(msg => {
                const messageElement = document.createElement('div');
                messageElement.classList.add('chat-message');
                
                let contentHtml = msg.content;
                
                // Check if the message content contains an image URL
                if (msg.content.match(/\.(jpeg|jpg|gif|png|svg)$/)) {
                    contentHtml += `<img src="${msg.content}" class="chat-image">`; // Append image to the content
                }

                messageElement.innerHTML = `
                    <div class="message-content">
                        <span class="username" style="color: ${msg.role_color};">${msg.author}:</span>
                        <span class="message-text">${contentHtml}</span>
                    </div>
                `;
                chatBox.appendChild(messageElement);
            });

            // Scroll to the latest message
            chatBox.scrollTop = chatBox.scrollHeight;
        })
        .catch(error => console.error('Error fetching chat messages:', error));
}

// Initial fetch
fetchChat();

// Continuously fetch chat updates every second
setInterval(fetchChat, 1000);
