import os
import re
import sqlite3
import discord
from github import Github
from discord.ext import commands

# Our SQL Variables to create and connect the DB.
DIR = os.path.dirname(__file__)
DB_NAME = "GitInfo.db"
DB = sqlite3.connect(os.path.join(DIR, DB_NAME))
SQL = DB.cursor()


class Gitconnect(commands.Cog):
    def __init__(self, client):
        self.client = client  # this allows us to access the client within our cog

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
        # regex to locate everything between the "" that the branch_list variable returns
        find_branch = re.search('"(.+?)"', str(branch_list))
        master = repo.get_branch(find_branch.group(1))
        sha_commit = master.commit.sha
        commit = repo.get_commit(sha=sha_commit)

        # Getting author username and profile picture for the embed
        # author = commit.author.login
        # author_pfp = commit.author.avatar_url

        embed = discord.Embed(title=f"{repo.name}", description=repo.description, url=repo.url,
                              color=discord.Colour.blue())
        embed.set_thumbnail(url=repo.owner.avatar_url)
        embed.add_field(name="__Latest Commit__", value=f"{commit.commit.message}", inline=True)
        embed.set_footer(icon_url=commit.author.avatar_url,
                         text=f"By {commit.author.login} on {commit.commit.committer.date}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["connect", "add"])
    async def link(self, ctx, git_user):
        # Getting token from environment for the Github API
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        SQL.execute(f'create table if not exists "{server_name}"('
                    '"Server_ID" integer secon, '
                    '"Server_Name" text, '
                    '"Username" text not null primary key'
                    ')')

        # This tests to see if the user already exists on the table, if they do it fails and sends a failure messsage
        try:
            SQL.execute(f'insert into "{server_name}"(Server_ID, Server_Name, Username) values(?, ?, ?)',
                        (server_id, server_name, git_user))
        except Exception as e:
            print(e)
            await ctx.send(
                f"The user **{git_user}** has already been added to the watch list for this server...")
            return

        # Commits changes to the DB if the user does not already exist
        DB.commit()
        await ctx.send(f"The user **{git_user}** has been successfully added to our watch list, their Github activity "
                       f"will be monitored starting after the next sync.")

    @commands.command(aliases=["remove", "disconnect"])
    async def unlink(self, ctx, git_user):
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        # We are searching the DB for an occurrence of the user that needs to be removed, if they exist it continues
        # if they do not exists it stops and returns that the user is not on the DB.
        SQL_Search = SQL.execute(
            f'select rowid from "{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Username = "{git_user}"')
        if SQL_Search.fetchone() is not None:
            try:
                SQL.execute(
                    f'delete from "{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Username = "{git_user}"')
            except Exception as e:
                print(e)
                await ctx.send(
                    f"The user **{git_user}** does not exist on the watch list...")
                return
        else:
            await ctx.send(
                f"The user **{git_user}** does not exist on the watch list...")
            return

        # If the user does exist, it commits the deletion to the DB.
        DB.commit()
        await ctx.send(f"The user **{git_user}** has been successfully been removed from the watch list.")

    @commands.command(aliases=["list"])
    async def watchlist(self, ctx):
        server_name = str(ctx.guild)
        server_id = ctx.guild.id
        SQL.execute(
            f'select Username from "{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}"')
        remove_items = ["'", "(", ")", ","]
        watch_list = []

        # Sorts through our SQL data to remove unneeded items based off of the remove_items list.
        for entry in SQL.fetchall():
            for item in remove_items:
                entry = str(entry)
                entry = entry.replace(item, "")
            watch_list.append(entry)
            watch_list = sorted(watch_list, key=str.casefold)

        embed = discord.Embed(title=f"{server_name}'s Github Watchlist", color=discord.Colour.blue())
        embed.add_field(name="**__Github Users__**", value=f"\n".join(watch_list), inline=True)
        embed.set_footer(icon_url=ctx.author.avatar_url, text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)


# This function allows us to connect this cog to our bot
def setup(client):
    client.add_cog(Gitconnect(client))
