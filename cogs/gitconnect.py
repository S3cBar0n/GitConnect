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

    # THIS COMMAND CREATES AN EMBED THAT LISTS A DISCORD MEMBERS NAME AND LISTS IF THEY HAVE A CONNECTED GITHUB ACCOUNT.
    @commands.command(aliases=["user", "info"])
    async def whois(self, ctx, member: discord.Member):
        """Lists information about a specific discord user.

        Use this command to see the users Github Username and latest activity.
        """
        event_types = {
            "WatchEvent": "Starred",
            "ForkEvent": "Forked",
            "PushEvent": "Pushed to",
            "CreateEvent": "Created",
            "PullRequestEvent": "PR submitted to",
            "IssueCommentEvent": "Commented on",
            "MemberEvent": "Modified settings for"
        }

        server_name = str(ctx.guild)
        server_id = ctx.guild.id
        git = Github()
        git_username = None
        git_userlink = None
        activity = []
        try:
            SQL.execute(
                f'select Git_Username from "UserAcc_{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Discord_ID = "{ctx.author.id}"')
            remove_items = ["'", "(", ")", ","]
            for entry in SQL.fetchall():
                for item in remove_items:
                    entry = str(entry)
                    entry = entry.replace(item, "")
                git_username = entry
                git_userlink = f"[{git_username}]({git.get_user(git_username).html_url})"
        except Exception as e:
            print(e)

        if git_username is not None:
            events = git.get_user(git_username).get_public_events()
            for item in range(3):
                print(
                    f"Recent Activity:\n {event_types[events[item].type]} the following repo {events[item].repo.name}")
                activity.append(f"{events[item].created_at.strftime('%m-%d')} - {event_types[events[item].type]} the repo {events[item].repo.name}")
        else:
            events = 0

        embed = discord.Embed(title=member.name, description=member.mention, color=discord.Colour.red())
        if git_userlink is not None:
            embed.add_field(name='Github Username', value=git_userlink, inline=False)
        else:
            embed.add_field(name='Link Your Github!', value="Use >link to add your account.", inline=False)
        if len(activity) >= 1:
            embed.add_field(name='Recent Activity', value=f"\n".join(activity), inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(icon_url=ctx.author.avatar_url, text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)

    # THIS ADDS A GITHUB ACCOUNT TO THE USER WHO CALLED THE COMMAND
    @commands.command(aliases=["addgit", "connecthub"])
    async def link(self, ctx, git_user):
        """This command attaches a Github Account to your discord account for this server.
        """
        # Getting token from environment for the Github API
        git = Github()
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        # Tests to see if the account is a real account on Github
        try:
            user = git.get_user(git_user)
        except Exception as e:
            print(e)
            await ctx.send(f"The github account {git_user} is not a valid Github User, try again...")
            return

        # Creates our DB to connect user accounts to discord users
        SQL.execute(f'create table if not exists "UserAcc_{server_name}"('
                    '"Server_ID" integer, '
                    '"Server_Name" text, '
                    '"Git_Username" text,'
                    '"Discord_ID" text not null primary key'
                    ')')

        # This tests to see if the user already exists on the table, if they do it fails and sends a failure message
        try:
            SQL.execute(
                f'insert into "UserAcc_{server_name}"(Server_ID, Server_Name, Git_Username, Discord_ID) values(?, ?, ?, ?)',
                (server_id, server_name, git_user, ctx.author.id))
        except Exception as e:
            print(e)
            await ctx.send(
                f"There is already an account connected to **{ctx.author.name}**...")
            return

        # Commits changes to the DB if the user does not already exist
        DB.commit()
        await ctx.send(f"The github account **{user.login}** has been attached to **{ctx.author.name}**.")

    # THIS COMMAND REMOVES THE GITHUB ACCOUNT ATTACHED TO WHOEVER CALLED THE COMMAND.
    @commands.command(aliases=["delgit", "removegit", "disconnecthub"])
    async def unlink(self, ctx):
        """This command removes a Github Account from your discord account for this server.
        """
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        # We are searching the DB for an occurrence of the user that needs to be removed, if they exist it continues
        # if they do not exists it stops and returns that the user is not on the DB.
        SQL_Search = SQL.execute(
            f'select rowid from "UserAcc_{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Discord_ID = "{ctx.author.id}"')
        if SQL_Search.fetchone() is not None:
            try:
                SQL.execute(
                    f'delete from "UserAcc_{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Discord_ID = "{ctx.author.id}"')
            except Exception as e:
                print(e)
                await ctx.send(
                    f"The user **{ctx.author.name}** does not have a Github Account attached...")
                return
        else:
            await ctx.send(
                f"The user **{ctx.author.name}** does not have a Github Account attached...")
            return

        # If the user does exist, it commits the deletion to the DB.
        DB.commit()
        await ctx.send(f"The Github account attached to **{ctx.author.name}** has been removed.")

    # GETS THE LATEST STATUS FOR A REPO, LISTS LATEST COMMIT AND ADDS A CLICKABLE LINK TO THE EMBED
    @commands.command(aliases=["project", "status"])
    async def repo(self, ctx, repo_link):
        """Pulls information on a Github Repo and provides the lastest commit.
        """
        # Getting token from environment for the Github API
        git = Github()

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

    # ADDS A GITHUB USER TO THE WATCH LIST TO ANNOUNCE ANY CHANGES TO REPOS OR NEW PROJECTS THEY CREATE
    @commands.command(aliases=["watch", "useradd", "userlink"])
    # @commands.has_permissions(kick_members=True)
    async def watchuser(self, ctx, git_user):
        """Adds a user to the watch list.

        Adds a user to the watchlist, this user's latest activity will be announced to the server.
        """
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        SQL.execute(f'create table if not exists "{server_name}"('
                    '"Server_ID" integer, '
                    '"Server_Name" text, '
                    '"Username" text not null primary key'
                    ')')

        # This tests to see if the user already exists on the table, if they do it fails and sends a failure message
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

    # REMOVES A USER FROM THE WATCH LIST
    @commands.command(aliases=["delwatch", "stopwatching"])
    # @commands.has_permissions(kick_members=True)
    async def unwatchuser(self, ctx, git_user):
        """Removes a user to the watch list.

        Removes a user from the watchlist, this user's activity will no longer be announced to the server.
        """
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

    # LISTS ALL CURRENT USERS ON THE WATCH LIST
    @commands.command(aliases=["watchlist"])
    async def list(self, ctx):
        """Lists all members currently on the watch list
        """
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

        embed = discord.Embed(title=f"{server_name}'s Github User Watchlist", color=discord.Colour.blue())
        embed.add_field(name="**__Github Users__**", value=f"\n".join(watch_list), inline=True)
        embed.set_footer(icon_url=ctx.author.avatar_url, text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)

    # ADDS A GITHUB REPO TO THE WATCH LIST TO ANNOUNCE ANY CHANGES TO THE REPO
    @commands.command(aliases=["repoconnect", "repoadd", "repolink"])
    # @commands.has_permissions(kick_members=True)
    async def watchrepo(self, ctx, repo_link):
        """Adds a repo to the watch list.

        Adds a repo to the watchlist, the latest commits and activity on this repo will be announced to the server.
        """
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        SQL.execute(f'create table if not exists "Repo_{server_name}"('
                    '"Server_ID" integer, '
                    '"Server_Name" text, '
                    '"Repo" text not null primary key, '
                    '"Last_Update" text'
                    ')')

        if "://github.com/" in repo_link:
            repo_link = repo_link.split("/", 3)[3]
        else:
            print("Unable to add repo...")

        # This tests to see if the user already exists on the table, if they do it fails and sends a failure message
        try:
            SQL.execute(f'insert into "Repo_{server_name}"(Server_ID, Server_Name, Repo) values(?, ?, ?)',
                        (server_id, server_name, repo_link))
        except Exception as e:
            print(e)
            await ctx.send(
                f"The Repo **{repo_link}** has already been added to the watch list for this server...")
            return

        # Commits changes to the DB if the user does not already exist
        DB.commit()
        await ctx.send(f"The Repo **{repo_link}** has been successfully added to our watch list, Github activity "
                       f"will be monitored starting after the next sync.")

    # REMOVES THE REPO FROM THE WATCHLIST
    @commands.command(aliases=["reporemove", "repodisconnect", "repodel", "unwatchrepo"])
    # @commands.has_permissions(kick_members=True)
    async def repounlink(self, ctx, repo_link):
        """Removes a repo from the watch list.

        Removes a repo from the watchlist, this repo's activity will no longer be announced to the server.
        """
        server_name = str(ctx.guild)
        server_id = ctx.guild.id

        if "://github.com/" in repo_link:
            repo_link = repo_link.split("/", 3)[3]
        else:
            print("Unable to add repo...")

        # We are searching the DB for an occurrence of the user that needs to be removed, if they exist it continues
        # if they do not exists it stops and returns that the user is not on the DB.
        SQL_Search = SQL.execute(
            f'select rowid from "Repo_{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Repo = "{repo_link}"')
        if SQL_Search.fetchone() is not None:
            try:
                SQL.execute(
                    f'delete from "Repo_{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}" and Repo = "{repo_link}"')
            except Exception as e:
                print(e)
                await ctx.send(
                    f"The repo **{repo_link}** does not exist on the watch list...")
                return
        else:
            await ctx.send(
                f"The repo **{repo_link}** does not exist on the watch list...")
            return

        # If the user does exist, it commits the deletion to the DB.
        DB.commit()
        await ctx.send(f"The repo **{repo_link}** has been successfully been removed from the watch list.")

    # LISTS ALL REPOS ON THE CURRENT WATCH LIST
    @commands.command(aliases=["repowatchlist", "rlist"])
    async def repolist(self, ctx):
        """Lists all repos currently on the watch list.
        """
        server_name = str(ctx.guild)
        server_id = ctx.guild.id
        SQL.execute(
            f'select Repo from "Repo_{server_name}" where Server_ID = "{server_id}" and Server_Name = "{server_name}"')
        remove_items = ["'", "(", ")", ","]
        watch_list = []

        # Sorts through our SQL data to remove unneeded items based off of the remove_items list.
        for entry in SQL.fetchall():
            for item in remove_items:
                entry = str(entry)
                entry = entry.replace(item, "")
            watch_list.append(entry)
            watch_list = sorted(watch_list, key=str.casefold)

        embed = discord.Embed(title=f"{server_name}'s Github Repo Watchlist", color=discord.Colour.blue())
        embed.add_field(name="**__Github Repositories__**", value=f"\n".join(watch_list), inline=True)
        embed.set_footer(icon_url=ctx.author.avatar_url, text=f"Requested by {ctx.author.name}")
        await ctx.send(embed=embed)


# This function allows us to connect this cog to our bot
def setup(client):
    client.add_cog(Gitconnect(client))
