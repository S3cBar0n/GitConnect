import discord
import random
from discord.ext import commands


class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client  # this allows us to access the client within our cog

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f"Pong! {round(self.client.latency * 1000)}ms")

    @commands.command()
    async def roll(self, ctx):
        await ctx.send(random.randint(1, 6))

    @commands.command(aliases=["user", "info"])
    # @commands.has_permissions(kick_members=True)
    async def whois(self, ctx, member: discord.Member):
        embed = discord.Embed(title=member.name, description=member.mention, color=discord.Colour.green())
        embed.add_field(name='ID', value=member.id, inline=True)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(icon_url=ctx.author.avatar_url, text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)


# This function allows us to connect this cog to our bot
def setup(client):
    client.add_cog(Commands(client))
