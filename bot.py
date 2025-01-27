import os
import sys
import discord
from discord.ext import commands
import asyncio
from logging_conf import logger
import textwrap
from flask import Flask, request, jsonify
from env import DISCORD_BOT_TOKEN, CONTENT_HEADERS
from utils.helpers import handle_requests

# Check if env.py exists
if not os.path.exists('env.py'):
    sample_env_content = textwrap.dedent("""
        import os

        DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', 'your-discord-bot-token')
        OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY', 'your-overseerr-api-key')
        OVERSEERR_BASE_URL = os.getenv('OVERSEERR_BASE_URL', 'https://sampleurl.com')
        POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '60')) # Interval to poll overseerr for new requests

        CONTENT_HEADERS = {
            'X-Api-Key': OVERSEERR_API_KEY
        }
    """)
    with open('env.py', 'w') as f:
        f.write(sample_env_content)
    logger.error("env.py file is missing. A sample env.py file has been created. Please update it with your values.")
    sys.exit(1)

# Import environment variables from env.py
try:
    from env import DISCORD_BOT_TOKEN, CONTENT_HEADERS
except ImportError as e:
    logger.error(f"Error importing environment variables: {e}")
    sys.exit(1)

# Check if required environment variables are set
if not DISCORD_BOT_TOKEN or not CONTENT_HEADERS:
    logger.error("Required environment variables are missing in env.py. Please set DISCORD_BOT_TOKEN and CONTENT_HEADERS.")
    sys.exit(1)

# Initialize the bot with a command prefix and intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent if needed
bot = commands.Bot(command_prefix='!', intents=intents)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
async def webhook():
    data = request.json
    logger.info(f"Received webhook data: {data}")
    asyncio.run_coroutine_threadsafe(handle_webhook(data), bot.loop)
    return jsonify({"status": "success"}), 200

async def handle_webhook(data):
    # Process the webhook data and handle the event
    await handle_requests(bot, data)

@bot.event
async def on_ready():
    try:
        s = await bot.tree.sync()
        logger.info(f'S:  {s}')
        logger.info(f'Synced {len(s)} commands')
    except Exception as e:
        logger.info(f'Error syncing commands: {e}')
    logger.info(f'Logged in as {bot.user.name}')

async def main():
    try:
        async with bot:
            logger.info("Loading extension 'cogs.commands'...")
            await bot.load_extension('cogs.commands')
            logger.info("Extension 'cogs.commands' loaded successfully.")
            logger.info("Starting bot...")
            await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.info(f'Failed to start bot: {e}')

if __name__ == "__main__":
    # Run the Flask app in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5000, use_reloader=False))
    flask_thread.start()

    # Run the Discord bot
    asyncio.run(main())