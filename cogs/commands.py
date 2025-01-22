import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
from utils.helpers import fetch_overseerr_requests, handle_requests, approve_request, decline_request
from logging_conf import logger
from env import CONTENT_HEADERS, POLL_INTERVAL

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.DISCORD_CHANNEL_ID = self.config.get('DISCORD_CHANNEL_ID')
        self.CONTENT_HEADERS = CONTENT_HEADERS
        self.processed_requests = set()  # Set to keep track of processed request IDs
        self.bot_ready = False
        self.check_overseerr_requests.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot_ready = True

    # Load configuration
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    # Save configuration
    def save_config(self, config):
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)

    # Slash command to set the channel ID
    @app_commands.command(name="setchannel", description="Set the notification channel")
    async def setchannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.config['DISCORD_CHANNEL_ID'] = channel.id
        self.save_config(self.config)
        self.DISCORD_CHANNEL_ID = channel.id  # Update the attribute immediately
        await interaction.response.send_message(f"Notification channel set to {channel.mention}")

    # Task to check Overseerr for new requests
    @tasks.loop(seconds=POLL_INTERVAL)
    async def check_overseerr_requests(self):
        if not self.bot_ready:
            return

        logger.info("Checking Overseerr for new requests...")
        requests_data = await fetch_overseerr_requests(self.CONTENT_HEADERS)
        if requests_data and requests_data.get('results'):
            logger.info("Request(s) found! Processing...")
            await handle_requests(self.bot, self.CONTENT_HEADERS, self.DISCORD_CHANNEL_ID, requests_data, self.processed_requests)

    # Event listener for reactions
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.emoji == '✅':
            logger.info("Approving request...")
            await approve_request(self.CONTENT_HEADERS, reaction.message)
        elif reaction.emoji == '❌':
            await decline_request(self.CONTENT_HEADERS, reaction.message)

async def setup(bot):
    await bot.add_cog(Commands(bot))