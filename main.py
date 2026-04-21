import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f'✅ Módulo cargado: {filename}')

@bot.event
async def on_ready():
    print(f'🚀 Astra Bot conectado como {bot.user}')
    # Sincronización de comandos
    try:
        guild = discord.Object(id=1495565448601927821)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    except Exception as e:
        print(f"Error sincronizando: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv('TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
#jeje