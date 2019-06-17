import discord
import config
import sys
import db
import jmutil
import wrcheck
import operator
from discord.ext import commands

firstRun = True
client = commands.Bot(command_prefix=config.COMMAND_PREFIX)
database = db.Database(config.JM_DB_PATH)

class Jumpmaze(commands.Cog):
    """Jumpmaze Discord bot commands"""

    async def populate_solo_embed(self, embed, map):
        maptype = database.get_map_type(map)
        rec = database.get_solo_map_record(map) if maptype == "solo" else database.get_jmrun_map_record(map)
        l = database.get_map_records(map)

        embed.add_field(name="Record Time", value=jmutil.ticstime(rec['time']), inline=False)
        embed.add_field(name="Record Date", value=jmutil.format_date(rec['date']), inline=False)
        embed.add_field(name="Record Set By", value=jmutil.strip_colours(rec['author']), inline=False)

        for i in range(min(10, len(l))):    
            user, time = l[i]
            rank = database.get_entry_rank(map + '_pbs', user, False)

            embed.add_field(name=str(rank) + ". " + user, value=jmutil.ticstime(time), inline=True)

    async def populate_team_embed(self, embed, map):
        recs = database.get_team_map_record(map)

        embed.add_field(name="Record Time", value=jmutil.ticstime(recs['time']), inline=False)
        embed.add_field(name="Record Date", value=jmutil.format_date(recs['date']), inline=False)

        for player, points in recs['helpers'].items():
            plural = "s"
            if points == 1:
                plural = ""

            embed.add_field(name=jmutil.strip_colours(player), value=str(points) + " point" + plural, inline=True)

    @commands.command(help="Returns the records for a specified map.", usage="<lump>")
    async def map(self, ctx, map):
        map = map.upper()
        maptype = database.get_map_type(map)

        url = "%s/maps/%s" % (config.SITE_URL, map)
        embed = discord.Embed(title="Records for " + map, colour=discord.Colour.blue(), url=url)
        embed.set_thumbnail(url="%s/img/maps/%s.png" % (config.SITE_URL, map))

        if maptype == "solo" or maptype == "jmrun":
            await self.populate_solo_embed(embed, map)

        elif maptype == "team":
            await self.populate_team_embed(embed, map)

        else:
            await ctx.send("Error - No map named %s exists, or it has no set records." % (map,))
            return
            
        await ctx.send(embed=embed)

    @commands.command(help="Returns the records for a specified route-based map.", usage="<lump> <route>")
    async def maproute(self, ctx, map, route):
        map = map.upper()
        routens = '%s (Route %s)' % (map, route)
        maptype = database.get_map_type(map)

        if maptype != "solo" or not database.entry_exists(routens, 'jrs_hs_time'):
            await ctx.send("Error - No map named %s exists, it has no set records, or it is not a route-based map." % (map,))
            return

        embed = discord.Embed(title="Records for %s (route %s)" % (map, route), colour=discord.Colour.blue())
        self.populate_solo_embed(embed, routens)
            
        await ctx.send(embed=embed)
        

    @commands.command(help="Returns the top 10 players")
    async def top(self, ctx):
        players = database.get_all_players()
        solomaps = database.get_solo_map_names()
        scores = {}

        numsolomaps = len(solomaps)

        for player in players:
            scores[player] = 0

            maps = database.get_player_maps(player)

            for map in maps:
                rank = database.get_entry_rank(map + '_pbs', player, True)
                scores[player] += rank

            scores[player] /= numsolomaps

        sortedscores = sorted(scores.items(), key=operator.itemgetter(1), reverse=True)

        embed = discord.Embed(title="Top Players", colour=discord.Colour.blue())
        for i in range(min(15, len(sortedscores))):
            player, score = sortedscores[i]

            embed.add_field(name="%d. %s" % (i + 1, player), value="Score: %0.3f" % (score,), inline=True)

        await ctx.send(embed=embed)


@client.command()
async def exit(ctx):
    print(ctx.author.id)
    if ctx.author.id in config.ADMINS:
        await client.close()
        sys.exit()
    else:
        await ctx.send("No")

@client.event
async def on_ready():
    game = discord.Game("Jumpmaze")
    await client.change_presence(status=discord.Status.online, activity=game)

client.loop.create_task(wrcheck.poll_thread_target(client, database))
client.add_cog(Jumpmaze())
client.run(config.BOT_TOKEN)