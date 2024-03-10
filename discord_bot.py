#!/bin/python3
import yt_dlp
from mcstatus import JavaServer
from mctools import RCONClient
import discord
from urllib.parse import urlparse
from discord import app_commands
import asyncio
import dotenv
intentsAll = discord.Intents.all()
client = discord.Client(intents=intentsAll)
tree = app_commands.CommandTree(client)

dotenv.load_dotenv()

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key':'FFmpegExtractAudio',
        'preferredcodec':'mp3',
        'preferredquality':'192'
    }]
}

def check_url(url):
    approved_urls = ['www.youtube.com']
    watch_path = '/watch'
    url2 = urlparse(url)
    if url2.netloc in approved_urls and url2.path == watch_path and url2.query and url2.query not in ('v','v=') and url2.query.startswith('v='):
        return True
    else:
        return False

def get_first_audio_format(info):
    for format in info:
        if 'acodec' in format and 'vcodec' in format:
            if  format['acodec'] != 'none' and format['vcodec'] == 'none':
                return format

def get_youtube_link(url):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_format = get_first_audio_format(info['formats'])
            if audio_format:
                return audio_format['url']
            else:
                return None
    except Exception as e:
        return None



def send_server_command(command):
    rcon = RCONClient(SERVER_ADDRESS, SERVER_PORT)

    if rcon.login(RCON_PASS):
        resp = rcon.command(command)
        return resp

def get_server_info():
    try:
        server = JavaServer(SERVER_ADDRESS)

        status = server.status()

        message = f"""
Server is online, currently {status.players.online} players are connected.
Server version: {status.version.name}
Server MOTD: {status.description}
        """
        return message
    except ConnectionError:
        return "Server is unreachable or offline."



is_playing = False
voice_client = None


def after_audio(error, voice_channel):
    global is_playing
    is_playing = False
    asyncio.run_coroutine_threadsafe(voice_channel.disconnect(), client.loop)

@tree.command(name = "play", description = "Play moosic", guilds=[discord.Object(GUILD_ID)])
async def play(interaction, url:str):
    global is_playing
    global voice_client
    voice = interaction.user.voice
    if not voice:
        await interaction.response.send_message("You need to be in a voice channel!")
        return False
    channel = voice.channel
    if not channel:
        await interaction.response.send_message("You need to be in a voice channel!")
        return False
    if not check_url(url):
         await interaction.response.send_message("That is not a valid youtube link goober")
         return False
    audio_url = get_youtube_link(url)
    if not audio_url:
        await interaction.response.send_message("Cant find suitable format for video")
        return False
    if not is_playing:
        await interaction.response.send_message("Got it chief")
        is_playing = True
        voice_channel = await channel.connect()
        voice_client = voice_channel
        voice_channel.play(source=discord.FFmpegPCMAudio(audio_url), after=lambda error:after_audio(error, voice_channel))
    else:
        await interaction.response.send_message("Sorry, already playin")


@tree.command(name = "stop", description = "Stop moosic", guilds=[discord.Object(GUILD_ID)])
async def stop(interaction):
    global is_playing
    global voice_client
    if is_playing:
        voice = interaction.user.voice
        if not voice:
            await interaction.response.send_message("You need to be in a voice channel!")
            return False
        channel = voice.channel
        if not channel:
            await interaction.response.send_message("You need to be in a voice channel!")
            return False
        if not voice_client:
            await interaction.response.send_message("Failed to aquire client handle, this goober behaviour should not be happening and if you ever see this i am restarted")
            return False
        await interaction.response.send_message("Stopppiiing audio!")
        await voice_client.disconnect()
    else:
        await interaction.response.send_message("I am not playing anything you goober")

@tree.command(name = "info", description = "Get server info", guilds=[discord.Object(GUILD_ID)])
async def info(interaction):
    await interaction.response.send_message(get_server_info())

@tree.command(name = "exec", description = "Run a command", guilds=[discord.Object(GUILD_ID)])
@app_commands.checks.has_any_role(APPROVED_MINECRAFT_ROLE_ID)
async def exec(interaction, command:str):
    resp = send_server_command(command)
    if len(resp) <= 2000:
        await interaction.response.send_message(resp, ephemeral=True)
    else:
        await interaction.response.send_message("Command output was longer than 2000 characters and could not be sent", ephemeral=True)

@exec.error
async def exec_error(ctx, error):
    if isinstance(error, discord.app_commands.errors.MissingAnyRole):
        await ctx.response.send_message("Sorry, you dont have permissions for this command.", ephemeral=True)
    else:
        await ctx.response.send_message("Sorry, an error occured.", ephemeral=True)

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name="goobers"))
    await tree.sync(guild=discord.Object(GUILD_ID))
    print(f"We have logged in as {client.user}")


client.run(DISCORD_ID)

