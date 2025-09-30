# Discord Chat Display

![Discord Chat Display](https://raw.githubusercontent.com/Naguroka/Discord-Chat-to-OBS/main/2024-02-08%2000_11_02-Discord%20Chat%20Display.png)

## Highlights
- Mirrors a Discord channel in real time for OBS or any browser source.
- Plays images, videos, animated emojis, and Lottie stickers inline.
- Ships with an embeddable widget (`embed.js`) so any website can host the chat without extra styling.
- Lets you target different Discord channels for OBS and the web embed (`DISCORD_CHANNEL_ID_OBS` vs `DISCORD_CHANNEL_ID_EMBED`).
- Smooth scrolling and message entrance animations keep the feed readable.

## Requirements
- Windows PC (tested) with [Python 3.10+](https://www.python.org/downloads/). During install, **check "Add Python to PATH."**
- A Discord bot with **MESSAGE CONTENT INTENT** enabled and permission to read the target channel(s).

## Quick Start
1. **Download the project.** Click the green **Code** button on GitHub and choose **Download ZIP**. Extract it somewhere easy, e.g. Desktop.
2. **Install dependencies.** In the extracted folder, open PowerShell/Command Prompt and run:
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Configure `settings.ini`.** Copy `settings.ini.example` to `settings.ini`, open it in a text editor, and fill in:
   - `DISCORD_BOT_TOKEN` - your bot token.
   - `DISCORD_CHANNEL_ID_OBS` - the channel you want to show inside OBS.
   - `DISCORD_CHANNEL_ID_EMBED` - the channel to expose via the embeddable widget. Use the OBS channel ID again if you only need one feed.
   Optional keys:
   - `CHAT_API_HOST` / `CHAT_API_PORT` - override the HTTP server bind address (default `127.0.0.1:8080`).
   - `CHAT_HISTORY_SIZE` - how many recent messages to retain (default `200`).
   Legacy `DISCORD_CHANNEL_ID` is still read as a fallback, but the two explicit keys above are preferred.
4. **Run the bot and web server.** Either double-click `start_everything.bat` or run `python bot.py`. The log will confirm the OBS + embed channel IDs and the REST endpoints.
5. **Add to OBS.** Create a Browser Source in OBS pointing at `http://127.0.0.1:8080/` and set the width/height you prefer. The page auto-scrolls and animates new messages.

## Embedding on Another Site
The embed widget consumes the `/embed.js` helper and talks to the `/embed-chat` endpoint automatically.

### Copy-paste script helper
```html
<div id="discord-chat"></div>
<script
  src="https://your-host.example.com:8080/embed.js"
  data-origin="https://your-host.example.com:8080"
  data-target="#discord-chat"
  data-width="100%"
  data-height="480px"
  data-chat-target="embed">
</script>
```
Supported `data-` attributes:
- `data-width`, `data-height`, `data-min-height`, `data-max-height`
- `data-background` (`bg`), `data-message-background`, `data-text-color`, `data-username-color`
- `data-font` (`system`, `serif`, `mono`, or any CSS font stack)
- `data-transparent` (`true`/`false`)
- `data-hide-usernames` (`true` hides the `Name:` prefix)
- `data-auto-resize` (`false` by default; set `true` to allow the iframe to grow with content)
- `data-chat-target` (`embed` or `obs`; defaults to `embed`)
- `data-api-origin` if your JSON API lives on another host

### Manual mount with JavaScript
```html
<script src="https://your-host.example.com:8080/embed.js"></script>
<script>
  DiscordChatEmbed.mount('#discord-chat', {
    origin: 'https://your-host.example.com:8080',
    chatTarget: 'embed',
    background: '#000000',
    messageBackground: '#202225',
    textColor: '#ffffff',
    hideUsernames: false,
    autoResize: false,
    height: '480px',
    maxHeight: '480px',
  });
</script>
```

### Plain `<iframe>`
```html
<iframe
  src="https://your-host.example.com:8080/?embed=1&chat_target=embed&transparent=1&bg=%23000000&message_bg=%23313131"
  style="border: 0; width: 100%; height: 480px;"
  loading="lazy"
  allow="autoplay">
</iframe>
```
Query parameters mirror the helper options (`bg`, `message_bg`, `text_color`, `username_color`, `font`, `hide_usernames`, `auto_resize`, `chat_target`).

> **Tip:** The iframe posts `postMessage` events like `{ source: 'discord-chat-to-obs', type: 'size', height }`. Listen for those if you turn on auto-resize.

## Demo Page
A ready-made playground lives in `demo-embed/index.html`. Start the bot (`python bot.py`), then open that file in your browser to try theme switches, username toggles, and alternate origins.

![Embed Demo](embed%20demo.png)

## Troubleshooting
- **"DISCORD_BOT_TOKEN is required."** Double-check `settings.ini` and ensure the file is in the project root.
- **Bot fails to log in.** Regenerate the token in the Developer Portal and update `settings.ini`.
- **Feed is empty.** Confirm the bot has access to the channel(s) and the IDs in `settings.ini` are correct.
- **Pip errors.** Make sure Python is installed, added to PATH, and retry the `pip install` commands.

## License
MIT License. See `LICENSE` for details.
