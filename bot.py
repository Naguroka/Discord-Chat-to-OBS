import discord
from aiohttp import web
import asyncio

token = 'token'  # Replace with your actual token
channelid = channelID # Replace with your actual token
messages = []  # Store messages here

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True


class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.channel.id == channelid:
            content = message.content or ""
            avatar_url = str(message.author.avatar.url) if message.author.avatar else 'default_avatar.png'
            nickname = message.author.display_name  # Use display name to get the effective name in the server
            role_color = str(message.author.top_role.color)
            messages.append({
                'content': content,
                'author': nickname,
                'avatar_url': avatar_url,
                'role_color': role_color
            })
            print(f"Processed message from {message.author}: '{content}'")

client = MyClient(intents=intents)

async def chat(request):
    return web.json_response(messages, headers={
        "Access-Control-Allow-Origin": "*",  # Allows access from any origin
        "Access-Control-Allow-Methods": "GET",  # Allows only GET method
        "Access-Control-Allow-Headers": "*",  # Allows all headers
    })

app = web.Application()
app.router.add_get('/chat', chat)

async def start_bot():
    await client.start(token)

async def start_web_app():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    loop.create_task(start_web_app())
    print("Bot and server are running...")
    loop.run_forever()
