# Discord Chat Display

![Discord Chat Display](https://raw.githubusercontent.com/Naguroka/Discord-Chat-to-OBS/main/2024-02-08%2000_11_02-Discord%20Chat%20Display.png)

This project mirrors one Discord channel to a browser page so stream viewers or website visitors can watch the conversation live. Animated emojis, images, videos, and Discord GIF/PNG stickers play inline, and the layout copies the look and feel of Discord.

---

## 1. Install The Prerequisites (Windows)
1. Download [Python 3.10 or newer](https://www.python.org/downloads/).
2. Run the installer. When you see **“Add Python to PATH”**, tick that box before you click **Install**.
3. Finish the installer and close it.

## 2. Create Your Discord Bot And Invite It
1. Open <https://discord.com/developers/applications> and log in.
2. Click **New Application**, give it a name (for example, “Stream Chat Relay”), and click **Create**.
3. In the left sidebar select **Bot** → click **Add Bot** → confirm with **Yes, do it!**
4. Still on the Bot page:
   - Turn on **PRESENCE INTENT** (optional) and **MESSAGE CONTENT INTENT** (required).
   - Click **Reset Token**, confirm, and copy the token to a safe place – you will put it in `settings.ini` later.
5. In the sidebar pick **OAuth2 → URL Generator**.
   - Under **Scopes**, tick **`applications.commands`** and **`bot`** (do **not** use the **Install** tab).
   - Under **Bot Permissions**, tick **View Channels**, **Read Message History**, and **Send Messages**.
   - Scroll to the bottom, copy the generated URL, paste it into your browser, choose the server you stream from, and authorise the bot.

## 3. Download This Project
1. Go to the GitHub repository page.
2. Click the green **Code** button → **Download ZIP**.
3. Right‑click the downloaded ZIP → **Extract All…** → pick an easy location such as your Desktop. You should now have a folder named `Discord-Chat-to-OBS-main` (or similar).

## 4. Install The Python Packages
1. Open the extracted folder in File Explorer.
2. Click in the address bar, type `cmd`, and press Enter – a Command Prompt will open in that folder.
3. Run:
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   Let the commands finish (they may take a minute on the first run).

## 5. Configure `settings.ini`
1. In File Explorer copy `settings.ini.example`, then rename the copy to `settings.ini`.
2. Open `settings.ini` in Notepad and fill in:
   - `DISCORD_BOT_TOKEN` – paste the token you copied from the Developer Portal.
   - `DISCORD_CHANNEL_ID_OBS` – the channel you want to show inside OBS. In Discord, right‑click the channel name (Developer Mode enabled) → **Copy ID**.
   - `DISCORD_CHANNEL_ID_EMBED` – the channel you want to expose on websites. Use the OBS ID again if you only need one feed.
   Optional ideas:
   - `CHAT_API_HOST` / `CHAT_API_PORT` to bind the web server somewhere other than `127.0.0.1:8080`.
   - `CHAT_HISTORY_SIZE` to keep more or fewer messages (default 200).
   - Legacy `DISCORD_CHANNEL_ID` is still accepted, but the two explicit keys above are preferred.
3. Save the file and close Notepad.

## 6. Start The Relay
1. From a Command Prompt inside the project folder run `python bot.py` (or double‑click `start_everything.bat`).
2. The console will print the channels it is watching and confirm that the web server is listening on `http://127.0.0.1:8080`.
3. Leave this window open while you stream – it runs the Discord client and the local API.

## 7. Add The Chat To OBS
1. In OBS add a **Browser Source**.
2. Set the URL to `http://127.0.0.1:8080/` (or whatever host/port you configured).
3. Choose a width/height (for example 700 × 900). The overlay will auto‑scroll and animate new messages.

---

## Embedding The Chat On A Website
Everything a site owner needs lives in this repository – no extra CSS or scripts required.

### Quick Script Helper
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
Supported attributes include:
- `data-width`, `data-height`, `data-min-height`, `data-max-height`
- `data-background` (`bg`), `data-message-background`, `data-text-color`, `data-username-color`
- `data-font` (`system`, `serif`, `mono`, or any CSS font stack)
- `data-transparent` (`true`/`false`)
- `data-hide-usernames` (`true` hides the “Name:” prefix)
- `data-auto-resize` (`false` by default; set `true` to let the iframe grow with content)
- `data-chat-target` (`embed` or `obs`; defaults to `embed`)
- `data-api-origin` if the JSON API lives elsewhere

### Manual Mount With JavaScript
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

> **Tip:** The iframe posts `postMessage` events like `{ source: 'discord-chat-to-obs', type: 'size', height }`. Listen for those if you enable auto‑resize.

---

## Demo Playground
The `demo-embed/index.html` page lets you try theme buttons, username toggles, and custom origins locally.

![Embed Demo](embed%20demo.png)

---

## Troubleshooting
- **“DISCORD_BOT_TOKEN is required.”** Make sure `settings.ini` exists beside `bot.py` and the token field is filled in.
- **Bot fails to log in.** Regenerate the token in the Developer Portal and update `settings.ini`.
- **No messages appear.** Confirm the bot joined the server, can read the selected channels, and the channel IDs in `settings.ini` are correct.
- **pip errors.** Check that Python is installed and on PATH, then re-run the commands in Step 4.

## License
MIT License. See `LICENSE` for details.
