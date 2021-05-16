import random
import discord
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client  # this allows us to access the client within our cog

    @commands.command()
    async def gitconnect(self, ctx):
        await ctx.send("https://www.youtube.com/watch?v=lCcwn6bGUtU")

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"Pong! {round(self.client.latency * 1000)}ms")

    @commands.command()
    async def roll(self, ctx):
        await ctx.send(random.randint(1, 6))


# This function allows us to connect this cog to our bot
def setup(client):
    client.add_cog(Commands(client))
