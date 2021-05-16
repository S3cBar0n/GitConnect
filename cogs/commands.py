import os
import re

import discord
from github import Github
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

    @commands.command(aliases=["project", "status"])
    async def repo(self, ctx, repo_link):
        # Getting token from environment for the Github API
        token = os.getenv("GITTOKEN")
        git = Github(token)

        # Checks to see if the repo provided by the user is a link, if its a link it processes it for use with the API.
        if "://github.com/" in repo_link:
            repo_link = repo_link.split("/", 3)[3]
            repo = git.get_repo(repo_link)
        else:
            repo = git.get_repo(repo_link)

        # Getting our repo information for the embed
        branch_list = list(repo.get_branches())
        # Trying to locate the main/master if they do not match standard conventions
        find_branch = re.search('"(.+?)"', str(branch_list))
        master = repo.get_branch(find_branch.group(1))
        sha_commit = master.commit.sha
        commit = repo.get_commit(sha=sha_commit)

        # Getting author username and profile picture for the embed
        author = commit.author.login
        author_pfp = commit.author.avatar_url

        embed = discord.Embed(title=f"{repo.name}", description=repo.description, url=repo.url,
                              color=discord.Colour.blue())
        embed.set_thumbnail(url=repo.owner.avatar_url)
        embed.add_field(name="__Latest Commit__", value=f"{commit.commit.message}", inline=True)
        embed.set_footer(icon_url=author_pfp, text=f"By {author} on {commit.commit.committer.date}")
        await ctx.send(embed=embed)


# This function allows us to connect this cog to our bot
def setup(client):
    client.add_cog(Commands(client))
