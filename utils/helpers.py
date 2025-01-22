import requests
import discord
from logging_conf import logger
from env import OVERSEERR_BASE_URL

PLEX_ORANGE = discord.Color.from_rgb(229, 160, 13)

async def fetch_overseerr_requests(headers):
    try:
        response = requests.get(f'{OVERSEERR_BASE_URL}/api/v1/request?take=20&skip=0&filter=pending', headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching Overseerr requests: {e}")
        return None

async def fetch_targeted_data(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching TMDB data: {e}")
        return None

async def send_embed(bot, channel_id, request_id, content_data, content_type, username):
    channel = bot.get_channel(channel_id)
    if channel:
        title = content_data.get('name', 'Unknown Title')
        year = content_data.get('firstAirDate', 'Unknown Year')[:4]
        description = content_data.get('overview', 'No description available.')
        poster_path = content_data.get('posterPath', '')

        embed = discord.Embed(
            title=f"{title} ({year})",
            description=description,
            color=PLEX_ORANGE
        )
        if poster_path:
            poster_url = f"https://image.tmdb.org/t/p/w600_and_h900_bestv2/{poster_path}"
            embed.set_thumbnail(url=poster_url)
        embed.set_footer(text=f'Request ID: {request_id}')

        embed.add_field(name="Requested By", value=username, inline=True)
        embed.add_field(name="Type", value=content_type.capitalize(), inline=True)

        if content_type == 'tv':
            seasons = content_data.get('seasons', [])
            season_numbers = [str(season['seasonNumber']) for season in seasons]
            embed.add_field(name="Seasons", value=", ".join(season_numbers), inline=True)

        message = await channel.send(embed=embed)
        await message.add_reaction('✅')
        await message.add_reaction('❌')

async def handle_requests(bot, headers, channel_id, requests_data, processed_requests):
    for request in requests_data.get('results', []):
        if request.get('status') == 1:  # Status 1 means pending
            request_id = request.get('id')
            if request_id in processed_requests:
                logger.info(f"Skipping embed for request {request_id} - already processed.")
                continue  # Skip already processed requests

            tmdb_id = request.get('media', {}).get('tmdbId')
            content_type = request.get('media', {}).get('mediaType')
            username = request.get('requestedBy', {}).get('displayName')
            
            if tmdb_id and content_type:
                url = f'{OVERSEERR_BASE_URL}/api/v1/{content_type}/{tmdb_id}'
                content_data = await fetch_targeted_data(url, headers)
                if content_data:
                    await send_embed(bot, channel_id, request_id, content_data, content_type, username)
                    processed_requests.add(request_id)  # Mark the request as processed

async def approve_request(headers, message):
    request_id = get_request_id_from_message(message)
    if request_id:
        try:
            response = requests.post(f'{OVERSEERR_BASE_URL}/api/v1/request/{request_id}/approve', headers=headers)
            response.raise_for_status()
            await update_embed_status(message, 'Request approved!', discord.Color.green())
            await clear_reactions(message)
        except requests.RequestException as e:
            await message.channel.send(f'Error approving request: {e}')

async def decline_request(headers, message):
    request_id = get_request_id_from_message(message)
    if request_id:
        try:
            response = requests.post(f'{OVERSEERR_BASE_URL}/api/v1/request/{request_id}/decline', headers=headers)
            response.raise_for_status()
            await update_embed_status(message, 'Request declined!', discord.Color.red())
            await clear_reactions(message)
        except requests.RequestException as e:
            await message.channel.send(f'Error declining request: {e}')
            
async def update_embed_status(message, status, color):
    embed = message.embeds[0]
    embed.color = color
    embed.add_field(name="Status", value=status, inline=True)
    await message.edit(embed=embed)
    
async def clear_reactions(message):
    await message.clear_reactions()

def get_request_id_from_message(message):
    # Extract the request ID from the message content or embed
    for embed in message.embeds:
        if embed.footer.text.startswith("Request ID: "):
            return embed.footer.text.split("Request ID: ")[1]
    return None