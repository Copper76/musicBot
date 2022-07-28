import random
import discord
from discord.ext import commands
import youtube_dl
import pafy
import asyncio
import os

client = commands.Bot(command_prefix="-")

song_queue = {}
loops = {}
current_urls = {}


async def check_queue(ctx):
    ctx.voice_client.stop()
    if loops[ctx.guild.id]:
        await play_song(ctx, current_urls[ctx.guild.id])
        return
    if len(song_queue[ctx.guild.id]) > 0:
        await play_song(ctx, song_queue[ctx.guild.id][0].split('  ')[0])
        current_urls[ctx.guild.id] = song_queue[ctx.guild.id][0].split('  ')[0]
        song_queue[ctx.guild.id].pop(0)
    else:
        await ctx.send("That was the last song, the bot lies waiting for your next command.")


async def search_song(amount, song, get_url=False):
    info = await client.loop.run_in_executor(None, lambda: youtube_dl.YoutubeDL(
        {"format": "bestaudio/best",
         'postprocessors': [{
             'key': 'FFmpegExtractAudio',
             'preferredcodec': 'mp3',
             'preferredquality': '192',
         }],
         "quiet": True}
    ).extract_info(f"ytsearch{amount}:{song}", download=False, ie_key="YoutubeSearch"))
    if len(info["entries"]) == 0: return None
    return [entry["webpage_url"] for entry in info["entries"]] if get_url else info['entries']


async def play_song(ctx, song):
    url = pafy.new(song).getbestaudio().url
    ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url)),
                          after=lambda error: client.loop.create_task(check_queue(ctx)))
    ctx.voice_client.source.volume = 0.5


@client.command()
async def join(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        song_queue[ctx.guild.id] = []
        loops[ctx.guild.id] = False
        voiceChannel = ctx.author.voice.channel
        if ctx.voice_client != None:
            await ctx.voice_client.disconnect()
        await voiceChannel.connect()
    else:
        await ctx.send("You are not connected to a voice channel")


@client.command()
async def leave(ctx):
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("The bot is already in the void")


@client.command()
async def pause(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        else:
            await ctx.send("The bot is not playing anything")
    else:
        await ctx.send("The bot is still in the void")


@client.command(aliases=["r"])
async def resume(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
        else:
            await ctx.send("The bot is already playing")
    else:
        await ctx.send("The bot is still in the void")


@client.command()
async def clear(ctx):
    if ctx.author.voice and ctx.voice_client and ctx.author.voice.channel.id == ctx.voice_client.channel.id:
        song_queue[ctx.guild.id].clear()
        ctx.voice_client.stop()


@client.command(aliases=["p"])
async def play(ctx, *, song=None):
    if ctx.author.voice and ctx.author.voice.channel:
        voiceChannel = ctx.author.voice.channel
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        if voice == None or voice.channel != voiceChannel:
            await join(ctx)
        if song == None:
            return await ctx.send("Please specify a song to play.")

        name = False

        if "youtube.com/playlist?" in song:
            pass
            # result = await get_playlist(song, get_url=True)
            # i = 1
            # for r in result:
            #     if ctx.voice_client.source:
            #         song_queue.append(f"{r}  {song}  {i}")
            #         await ctx.send(f"OK, {r} has been queued at position {len(song_queue) + 1}")
            #     else:
            #         await play_song(ctx, r)
            #         await ctx.send(f"playing {r}")
            #     i += 1
            #
            # await play_song(ctx, song)
            # await ctx.send(f"playing {song}")
        else:
            if not "youtube.com/watch?" in song or "https://youtu.be/" in song:
                await ctx.send("searching for your song")

                result = await search_song(1, song)

                if not result:
                    return await ctx.send("There is no such song")

                song = result[0]
                name = True

            if name:
                if ctx.voice_client.source:
                    song_queue[ctx.guild.id].append(f"{song['webpage_url']}  {song['title']}")
                    await ctx.send(f"OK, {song['webpage_url']} has been queued at position {len(song_queue[ctx.guild.id]) + 1}")
                else:
                    await play_song(ctx, song['webpage_url'])
                    await ctx.send(f"playing {song['webpage_url']}")
                    current_urls[ctx.guild.id] = song['webpage_url']
            else:
                if ctx.voice_client.source:
                    song_queue[ctx.guild.id].append(f"{song}")
                    await ctx.send(f"OK, {song} has been queued at position {len(song_queue[ctx.guild.id]) + 1}")
                else:
                    await play_song(ctx, song)
                    await ctx.send(f"playing {song}")
                    current_urls[ctx.guild.id] = song

    else:
        await ctx.send("You are not connected to a voice channel")


@client.command(aliases=["q"])
async def queue(ctx):
    if len(song_queue[ctx.guild.id]) == 0:
        return await ctx.send("There is currently no song in the queue.")

    embed = discord.Embed(title="Song Queue", description="", colour=discord.Colour.dark_gold())
    i = 1
    for url in song_queue[ctx.guild.id]:
        embed.description += f"{i} {url}\n"
        i += 1
    await ctx.send(embed=embed)

@client.command()
async def skip(ctx):
    if ctx.author.voice and ctx.voice_client and ctx.author.voice.channel.id == ctx.voice_client.channel.id:
        ctx.voice_client.stop()
        await ctx.send("Song skipped")

@client.command()
async def shuffle(ctx):
    if ctx.author.voice and ctx.voice_client and ctx.author.voice.channel.id == ctx.voice_client.channel.id:
        if len(song_queue[ctx.guild.id]) == 0:
            await ctx.send("There is no song in the queue")
        else:
            random.shuffle(song_queue[ctx.guild.id])
            await ctx.send("Songs shuffled")
            embed = discord.Embed(title="New Song Queue", description="", colour=discord.Colour.dark_gold())
            i = 1
            for url in song_queue[ctx.guild.id]:
                embed.description += f"{i} {url}\n"
                i += 1
            await ctx.send(embed=embed)

@client.command()
async def loop(ctx):
    loops[ctx.guild.id] = not loops[ctx.guild.id]


client.run('Nzg1MjczMzUzNzQwNjE1NzM0.GcjwF3.E1c0s-BR6Lp81-GbJ85oJJ2Jz1VUhtG4LJ9jVc')
