
(function () {
    const targetSelector = '#chat-target';
    const themeButtons = Array.from(document.querySelectorAll('button[data-theme]'));
    const toggleUsersBtn = document.getElementById('toggleUsers');
    const apiOriginInput = document.getElementById('apiOrigin');

    let hideUsernames = false;
    let currentTheme = 'default';
    let mountedIframe = null;

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
    toggleUsersBtn.classList.toggle('active', hideUsernames);

    function mountChat() {
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
            mountedIframe.remove();
            mountedIframe = null;
        }

        target.innerHTML = '';

        const theme = THEMES[currentTheme] || THEMES.default;

        mountedIframe = DiscordChatEmbed.mount(target, {
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
        button.addEventListener('click', () => {
            themeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            currentTheme = button.dataset.theme;
            mountChat();
        });
    });

    toggleUsersBtn.addEventListener('click', () => {
        hideUsernames = !hideUsernames;
        toggleUsersBtn.classList.toggle('active', hideUsernames);
        toggleUsersBtn.textContent = hideUsernames ? 'Show usernames' : 'Hide usernames';
        mountChat();
    });

    apiOriginInput.addEventListener('change', mountChat);

    window.addEventListener('DOMContentLoaded', mountChat);
})();
