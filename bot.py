import os
import textwrap
from logging_conf import logger

# Check if env.py exists and create it if missing
if not os.path.exists('env.py'):
    sample_env_content = textwrap.dedent("""
        import os

        DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', 'your-discord-bot-token')
        OVERSEERR_API_KEY = os.getenv('OVERSEERR_API_KEY', 'your-overseerr-api-key')
        OVERSEERR_BASE_URL = os.getenv('OVERSEERR_BASE_URL', 'https://sampleurl.com')

        CONTENT_HEADERS = {
            'X-Api-Key': OVERSEERR_API_KEY
        }
    """)
    with open('env.py', 'w') as f:
        f.write(sample_env_content)
    logger.warning("env.py file is missing. A sample env.py file has been created. Update it if needed or pass environment variables via docker-compose.")

# Import environment variables from env.py
try:
    from env import DISCORD_BOT_TOKEN, CONTENT_HEADERS
except ImportError as e:
    logger.error(f"Error importing environment variables: {e}")
    sys.exit(1)

import sys
import discord
from discord.ext import commands
import asyncio
from flask import Flask, request, jsonify
from utils.helpers import handle_requests

# Check if required environment variables are set and not using default placeholder values
if DISCORD_BOT_TOKEN == 'your-discord-bot-token' or \
   os.getenv('OVERSEERR_API_KEY') == 'your-overseerr-api-key' or \
   os.getenv('OVERSEERR_BASE_URL') == 'https://sampleurl.com':
    logger.error("Required environment variables are missing or using default placeholder values in env.py. "
                 "Please set DISCORD_BOT_TOKEN, OVERSEERR_API_KEY, and OVERSEERR_BASE_URL.")
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
    
@bot.event
async def on_disconnect():
    logger.warning("Bot disconnected from Discord. Attempting to reconnect...")

@bot.event
async def on_resumed():
    logger.info("Bot successfully resumed session.")  

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