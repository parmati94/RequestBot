import requests
import discord
from logging_conf import logger
from env import OVERSEERR_BASE_URL
from utils.config_utils import load_config

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

async def send_embed(bot, embed_data):
    logger.info('Creating embed...')
    config = load_config()
    channel_id = config.get('DISCORD_CHANNEL_ID')
    channel = bot.get_channel(channel_id)
    if channel:
        embed = discord.Embed(
            title=f"{embed_data['title']}",
            description=embed_data['description'],
            color=PLEX_ORANGE
        )
        if embed_data['poster_url']:
            embed.set_thumbnail(url=embed_data['poster_url'])
        embed.set_footer(text=f'Request ID: {embed_data["request_id"]}')

        embed.add_field(name="Requested By", value=embed_data['username'], inline=True)
        embed.add_field(name="Type", value=embed_data['content_type'].capitalize(), inline=True)

        if embed_data['content_type'].lower() == 'tv':
            embed.add_field(name="Seasons", value=embed_data['seasons'], inline=True)

        logger.info(f"Sending embed for request ID: {embed_data['request_id']}")
        message = await channel.send(embed=embed)
        await message.add_reaction('✅')
        await message.add_reaction('❌')

async def handle_requests(bot, request):
    logger.info('Processing request...')
    request_id = request.get('request', {}).get('request_id')
    content_type = request.get('media', {}).get('media_type')
    username = request.get('request', {}).get('requestedBy_username')
    title = request.get('subject', 'Unknown Title')
    description = request.get('message', 'No description available.')
    poster_path = request.get('image', '')
    seasons = next((item['value'] for item in request.get('extra', []) if item.get('name') == 'Requested Seasons'), '')

    embed_data = {
        'request_id': request_id,
        'title': title,
        'description': description,
        'poster_url': f"{poster_path}" if poster_path else '',
        'username': username,
        'content_type': content_type,
        'seasons': seasons
    }
    logger.debug(embed_data)

    await send_embed(bot, embed_data)

async def approve_request(headers, message):
    request_id = get_request_id_from_message(message)
    if request_id:
        try:
            response = requests.post(f'{OVERSEERR_BASE_URL}/api/v1/request/{request_id}/approve', headers=headers)
            response.raise_for_status()
            
            logger.info(f"Request {request_id} successfully approved.")
            
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
            
            logger.info(f"Request {request_id} successfully declined.")
            
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