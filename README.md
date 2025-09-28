# Discord Chat Display

## Overview
Discord Chat Display lets you mirror a Discord channel inside browser sources such as OBS. A lightweight Discord bot listens for new messages, relays them over a tiny web API, and the bundled front-end renders them in a Discord-inspired theme.

![Discord Chat Display](https://raw.githubusercontent.com/Naguroka/Discord-Chat-to-OBS/main/2024-02-08%2000_11_02-Discord%20Chat%20Display.png)

## Requirements
- Python 3.10 or newer (3.12 recommended)
- A Discord bot token with the **MESSAGE CONTENT INTENT** enabled
- Permissions to invite the bot to the guild/channel you want to mirror

## Setup

1. **Clone the repository**
   ```sh
   git clone https://github.com/Naguroka/Discord-Chat-to-OBS.git
   cd Discord-Chat-to-OBS
   ```

2. **Install dependencies** (virtual environments are encouraged)
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS / Linux
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Create your configuration**
   ```sh
   copy settings.ini.example settings.ini  # Windows
   # cp settings.ini.example settings.ini   # macOS / Linux
   ```
   Fill in the required secrets inside `settings.ini`:
   - `DISCORD_BOT_TOKEN` - your bot token from the Discord Developer Portal.
   - `DISCORD_CHANNEL_ID` - the numeric ID of the channel to mirror (right-click the channel in Discord with developer mode enabled).

## Optional configuration
Tune runtime behaviour by editing the corresponding values in `settings.ini`:
- `CHAT_API_HOST` (default `127.0.0.1`) - interface for the JSON endpoint.
- `CHAT_API_PORT` (default `8080`) - port for the JSON endpoint that the web page polls.
- `CHAT_HISTORY_SIZE` (default `200`) - number of recent messages kept in memory.
- `LOG_LEVEL` (default `INFO`) - standard Python logging level (e.g. `DEBUG`).

The bot also honours environment variables with the same names, which can override the values in `settings.ini` when needed for deployments.

## Running
### Quick start (Windows)
Double-click `start_everything.bat`. It launches the static file server on `http://localhost:8000` and the Discord relay on `http://localhost:8080`.

### Manual start (all platforms)
Open two terminals:
1. Serve the static assets so OBS/browser sources can load them:
   ```sh
   python -m http.server 8000
   ```
2. Start the Discord relay bot:
   ```sh
   python bot.py
   ```

Visit `http://localhost:8000` in a browser (or add it as an OBS browser source) to see the chat update in real time.

## Customisation
- **Styling:** Adjust colours and layout in `styles.css`.
- **Front-end behaviour:** Extend `script.js` if you want richer message formatting.
- **Message retention:** Change `CHAT_HISTORY_SIZE` in `settings.ini` to tune how many messages are exposed to the front-end.

## Troubleshooting
- `RuntimeError: Configuration value 'DISCORD_BOT_TOKEN' is required.` - ensure `settings.ini` exists and is filled in, or set the variables in your shell before launching.
- `discord.errors.LoginFailure` - double-check that the bot token is correct and has not been regenerated.
- No messages appearing - confirm the bot has access to the target channel and that `DISCORD_CHANNEL_ID` uses the correct snowflake.

## Contributing
Contributions and feature suggestions are welcome! Please open an issue or submit a pull request if you have improvements.

## License
Distributed under the MIT License. See `LICENSE` for details.
