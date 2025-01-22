import os
import sys
import discord
from discord.ext import commands
import asyncio
from logging_conf import logger
import textwrap

# Check if env.py exists
if not os.path.exists('env.py'):
    sample_env_content = textwrap.dedent("""
        # Sample env.py

        DISCORD_BOT_TOKEN = 'your-discord-bot-token'
        OVERSEERR_API_KEY = 'your-overseerr-api-key'

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
    asyncio.run(main())