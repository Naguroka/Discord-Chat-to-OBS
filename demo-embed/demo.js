// Interactive playground for testing DiscordChatEmbed options.

(function () {
    const targetSelector = '#chat-target';
    const themeButtons = Array.from(document.querySelectorAll('button[data-theme]'));
    const toggleUsersBtn = document.getElementById('toggleUsers');
    const apiOriginInput = document.getElementById('apiOrigin');

    let hideUsernames = false;
    let currentTheme = 'default';
    let mountedIframe = null;

    // Theme presets to showcase quick styling tweaks.
const THEMES = {

        default: {
            background: '#1e2230',
            messageBackground: '#313543',
            textColor: '#ffffff',
            usernameColor: '#99aab5',
            font: 'system'
        },
        neon: {
            background: '#05070c',
            messageBackground: '#191d2f',
            textColor: '#50d6ff',
            usernameColor: '#ff83f5',
            font: '"Space Grotesk", "Segoe UI", sans-serif'
        },
        mono: {
            background: '#111111',
            messageBackground: '#1c1c1c',
            textColor: '#ededed',
            usernameColor: '#bbbbbb',
            font: 'monospace'
        }
    };

    toggleUsersBtn.textContent = hideUsernames ? 'Show usernames' : 'Hide usernames';
    // Keep the UI toggles in sync when we re-render the iframe.
    toggleUsersBtn.classList.toggle('active', hideUsernames);

    function mountChat() {
        // Refresh the iframe with the latest controls from the demo UI.
        const origin = apiOriginInput.value.trim();
        if (!origin) {
            alert('Please enter the bot origin (e.g. http://127.0.0.1:8080).');
            return;
        }

        const target = document.querySelector(targetSelector);
        if (!target) {
            console.error('Chat target not found.');
            return;
        }

        if (mountedIframe && mountedIframe.parentNode) {
            // Tear down the previous iframe so we do not leak listeners.
            mountedIframe.remove();
            mountedIframe = null;
        }

        target.innerHTML = '';

        const theme = THEMES[currentTheme] || THEMES.default;

        mountedIframe = DiscordChatEmbed.mount(target, {
            // Feed the helper the same options the README demonstrates.
            origin,
            background: theme.background,
            messageBackground: theme.messageBackground,
            textColor: theme.textColor,
            usernameColor: theme.usernameColor,
            font: theme.font,
            hideUsernames,
            transparent: false,
            autoResize: false,
            height: '480px',
            maxHeight: '480px',
            chatTarget: 'embed',
            className: 'chat-frame'
        });
    }

    themeButtons.forEach(button => {
        // Toggle the active theme button and rebuild the iframe.
        button.addEventListener('click', () => {
            themeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            currentTheme = button.dataset.theme;
            mountChat();
        });
    });

    toggleUsersBtn.addEventListener('click', () => {
        // Flip between showing and hiding usernames without reloading.
        hideUsernames = !hideUsernames;
        toggleUsersBtn.classList.toggle('active', hideUsernames);
        toggleUsersBtn.textContent = hideUsernames ? 'Show usernames' : 'Hide usernames';
        mountChat();
    });

    apiOriginInput.addEventListener('change', mountChat);
    // Remount when the origin changes so we always hit the new server.

    window.addEventListener('DOMContentLoaded', mountChat);
    // Kick things off once the controls are ready.
})();
