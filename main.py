from discord.ext import commands
import os

client = commands.Bot(command_prefix=">")


# Loads our cogs library
@client.command()
@commands.has_permissions(administrator=True)
async def load(ctx, extension):
    client.load_extension(f"cogs.{extension}")


# Unloads our cogs library
@client.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, extension):
    client.unload_extension(f"cogs.{extension}")


for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")

client.run(os.environ['TOKEN'])
