# Discord Chat Display

## What This Does
This project shows the messages from one Discord channel in a web page that looks like Discord chat. Image attachments and Tenor GIFs play automatically so you don't just see a link. You can point OBS (or any browser source) at that page so people watching your stream see the live conversation.

![Discord Chat Display](https://raw.githubusercontent.com/Naguroka/Discord-Chat-to-OBS/main/2024-02-08%2000_11_02-Discord%20Chat%20Display.png)

## Before You Start
You will need:
- A Windows PC with [Python 3.10 or newer](https://www.python.org/downloads/) installed. When you install Python, **check the box that says “Add Python to PATH.”**
- A Discord bot token and permission to add the bot to the server/channel you want to mirror. Turn on the **MESSAGE CONTENT INTENT** for that bot.

## One-Time Setup (do these steps in order)
1. **Download the project**
   - Click the green “Code” button on GitHub and choose “Download ZIP”.
   - Right-click the ZIP you downloaded and choose **Extract All…**. Put it somewhere easy, like your Desktop. You should end up with a folder called `Discord-Chat-to-OBS-main`.

2. **Open a Command Prompt inside the folder**
   - In File Explorer, open the `Discord-Chat-to-OBS-main` folder.
   - Click the address bar, type `cmd`, and press Enter. A black window opens pointing at the folder.

3. **Install the required Python packages** (this uses your normal/global Python install)
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   If Windows says “pip is not recognized,” close the command prompt, reopen it, and try again.

4. **Make your personal settings file**
   - In File Explorer, find the file called `settings.ini.example`.
   - Right-click it, choose **Copy**.
   - Right-click an empty space in the same folder, choose **Paste**.
   - You will now have a file named `settings.ini.example - Copy`. Right-click that file, choose **Rename**, and type exactly `settings.ini`.
   - Double-click the new `settings.ini` file to open it (Notepad is fine). Replace the placeholder values:
     * `DISCORD_BOT_TOKEN` → paste your real bot token here.
     * `DISCORD_CHANNEL_ID` → put the channel ID number you want to display (right-click the channel in Discord with Developer Mode on and choose “Copy ID”).
   - Save the file and close Notepad.

You only need to do the steps above once.

## How to Run It (every time you stream)
1. Open the `Discord-Chat-to-OBS-main` folder.
2. Double-click `start_everything.bat`.
   - A window will say the web page is running on `http://localhost:8000`.
   - Another window will say the Discord bot is running on `http://127.0.0.1:8080`.
3. In OBS (or a browser), add a browser source pointing to either address:
   - `http://localhost:8000/` if you want the static files served separately (same as before).
   - `http://127.0.0.1:8080/` if you want the bot to serve everything (one program instead of two).
4. As messages arrive in the Discord channel, they appear in the overlay automatically.

To stop everything, close the two command windows that opened.

## Changing the Look
- `styles.css` controls colours and spacing.
- `script.js` controls how messages appear (for example, adding image previews).
- In `settings.ini` you can tweak:
  - `CHAT_API_HOST` and `CHAT_API_PORT` if you need different network addresses.
  - `CHAT_HISTORY_SIZE` if you want to show more or fewer messages.

## Having Trouble?
- **It says the bot token is required:** Re-open `settings.ini` and make sure you saved your token and channel ID.
- **The bot can’t log in:** Double-check the token in the Developer Portal; regenerate it if needed.
- **No messages show up:** Make sure the bot is inside the server, has access to that channel, and the channel ID is correct.
- **Pip errors:** Confirm Python is installed and added to PATH, then rerun the `pip install` commands.

## License
MIT License – see `LICENSE` if you’re curious.
