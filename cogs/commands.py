import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
from utils.helpers import fetch_overseerr_requests, handle_requests, approve_request, decline_request
from utils.config_utils import load_config, save_config
from logging_conf import logger
from env import CONTENT_HEADERS, POLL_INTERVAL

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.DISCORD_CHANNEL_ID = self.config.get('DISCORD_CHANNEL_ID')
        self.CONTENT_HEADERS = CONTENT_HEADERS
        self.bot_ready = False
        # self.check_overseerr_requests.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot_ready = True

    # Slash command to set the channel ID
    @app_commands.command(name="setchannel", description="Set the notification channel")
    async def setchannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.config['DISCORD_CHANNEL_ID'] = channel.id
        save_config(self.config)
        self.DISCORD_CHANNEL_ID = channel.id  # Update the attribute immediately
        
        logger.info(f"Notification channel set to {channel.id}")
        
        await interaction.response.send_message(f"Notification channel set to {channel.mention}")
        
    @app_commands.command(name="ping", description="Sends the bot's latency.")
    async def ping_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! Latency is {self.bot.latency}")
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        
        if reaction.message.channel.id != self.DISCORD_CHANNEL_ID:
            logger.info("Ignoring reaction - added on unwatched channel.")
            return
        
        if not reaction.message.embeds or not reaction.message.embeds[0].footer or not reaction.message.embeds[0].footer.text.startswith("Request ID: "):
            logger.info("Ignoring reaction - not a request embed.")
            return

        if reaction.emoji == '✅':
            logger.info("Approving request...")
            await approve_request(self.CONTENT_HEADERS, reaction.message)
        elif reaction.emoji == '❌':
            await decline_request(self.CONTENT_HEADERS, reaction.message)

async def setup(bot):
    await bot.add_cog(Commands(bot))