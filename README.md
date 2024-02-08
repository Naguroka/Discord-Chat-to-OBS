```
# Discord Chat Display

## Overview
Discord Chat Display is a web application designed to embed a live Discord chat stream into your Twitch or other streaming platforms. It captures messages from a specified Discord channel and displays them in real-time on a custom web page, styled to resemble Discord's theme. This project enables streamers to visually integrate their Discord interactions directly into their streams.

## Features
- **Real-Time Chat Updates:** Automatically fetches and displays new messages from a designated Discord channel.
- **Discord-Like Styling:** Utilizes a color scheme and font similar to Discord for a cohesive look and feel.
- **Auto-Scrolling:** Keeps the chat view scrolled to the latest message, ensuring active conversations are always visible.
- **Customizable Layout:** Easy to customize CSS for personalizing the chat display to match your streaming overlay.

## Setup Instructions

### Prerequisites
- Python 3.6 or higher
- A Discord Bot Token

### Installation

1. **Clone the Repository**
   ```sh
   git clone https://github.com/Naguroka/discord-chat-to-obs.git
   cd discord-chat-display
   ```

2. **Install Dependencies**
   - The project uses standard libraries (`discord.py`, `aiohttp`).

3. **Configure Your Bot**
   - Create a Discord bot and obtain your token from the Discord Developer Portal.
   - Enable `MESSAGE CONTENT INTENT` for your bot.

4. **Set Up Environment Variables**
   - It's recommended to store your Discord Bot Token and channel ID as environment variables.
   ```sh
   DISCORD_BOT_TOKEN=your_bot_token
   DISCORD_CHANNEL_ID=your_channel_id
   ```

### Running the Application

1. **Start the "start_everything.bat" file**

## Usage

Once both the backend and frontend are running, navigate to `http://localhost:8000` in your web browser to view the chat display. The page will automatically update with new messages from your Discord channel.

## Customization

- **Styling:** Modify `styles.css` to change the appearance of the chat display.
- **Functionality:** Adjust `script.js` and `bot.py` for additional features or changes in message handling.

## Contributing

I welcome contributions! Please feel free to fork the repository, make your changes, and submit a pull request.

## Notes

- This was made to be used with OBS's browser module to show your discord chat on stream with a high level of customizability

## License

Distributed under the MIT License. See `LICENSE` for more information.
```
