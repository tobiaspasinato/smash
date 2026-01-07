import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix=',', intents=intents)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

bot.run(TOKEN)