import os
import asyncio
import discord
from discord.ext.commands import Bot
from discord.ext import commands
from random import randint
from time import sleep,time

if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '**{0.title}**'
        return fmt.format(self.player)

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def clear(self):
        if not self.songs.empty():
            del self.songs
            self.songs = asyncio.Queue()

    async def get_queue(self):
        lsongs = list(self.songs._queue)
        return lsongs

              
    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()

class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        self.is_pause = False

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.join)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.6
            entry = VoiceEntry(ctx.message, player)
            if state.is_playing():
                await self.bot.say('Enqueued ' + str(entry))
            await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value : int):
        """Sets the volume of the currently playing song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing() and not self.is_pause:
            player = state.player
            player.pause()
            self.is_pause = True
            await self.bot.say('Music is paused')
        elif not state.is_playing():
            await self.bot.say('Not playing any music right now...')
        elif self.is_pause:
            await self.bot.say('Music is alredy paused')

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing() and self.is_pause:
            player = state.player
            player.resume()
            self.is_pause = False
            await self.bot.say('Music is resume')
        elif not state.is_playing():
            await self.bot.say('Not playing any music right now...')
        elif not self.is_pause:
            await self.bot.say('Music is not paused')
        

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)
        if state.is_playing():
            player = state.player
            player.stop()
        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester and member with 'DJ' role can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            
        else:
            role_names = [role.name for role in ctx.message.author.roles]
            voter = ctx.message.author
            if voter == state.current.requester or "DJ" in role_names:
                await self.bot.say('Skipping song...')
                state.skip()
            elif voter.id not in state.skip_votes:
                state.skip_votes.add(voter.id)
                total_votes = len(state.skip_votes)
                if total_votes >= 3:
                    await self.bot.say('Skip vote passed, skipping song...')
                    state.skip()
                else:
                    await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
            else:
                await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    async def clear(self, ctx):
        """Clears songs in the queue"""
        state = self.get_voice_state(ctx.message.server)
        if state.songs.empty():
            await self.bot.say('Queue is already empty')
        else:
            state.clear()
            await self.bot.say('Queue cleared')
        

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything.')
        elif self.is_pause :
            await self.bot.say('I am actually paused')
        else:
            embed = discord.Embed(title=state.current.player.title,url=state.current.player.url)
            embed.set_author(name='Now playing', icon_url=state.current.requester.avatar_url)
            duration = state.current.player.duration
            if duration:
                duration='{0[0]}m {0[1]}s'.format(divmod(duration, 60))
                embed.add_field(name='Duration',value=duration,inline=True)          
            embed.add_field(name='Uploader',value=state.current.player.uploader,inline=True)
            embed.add_field(name='Requester',value=state.current.requester,inline=True)
            await self.bot.say(embed=embed)

    @commands.command(pass_context=True, no_pm=True)
    async def queue(self, ctx):
        """Shows songs in the queue"""
        state = self.get_voice_state(ctx.message.server)
        songs = await state.get_queue()
        if len(songs) == 0:
            await self.bot.say('Queue is empty')
        else:
            embed = discord.Embed(title='Queue')
            for i in range(1,len(songs)+1):
                print(len(songs))
                song = songs[i-1]
                duration = song.player.duration
                if duration:
                    duration='  {0[0]}m {0[1]}s'.format(divmod(duration, 60))
                else:
                    duration = ''
                embed.add_field(name=str(i)+'. '+song.player.title+duration,value="Requester : {}".format(song.requester))
            await self.bot.say(embed=embed)

Client = discord.Client()
client = commands.Bot(command_prefix=commands.when_mentioned_or('!'))
client.add_cog(Music(client))
cec = False
cooldown = []

@client.event
async def on_ready():
    print("Bot Ready")
    print(client.user.name)
    print(client.user.id)
            
@client.command(pass_context=True)
async def kick(ctx,member: discord.Member):
    global cec
    if cec == False:
        cec = True
        if (await test_role(ctx.message.author)) and (member.voice_channel != None):
            server = ctx.message.server
            channel = await client.create_channel(server,'Poubelle',type=discord.ChannelType.voice)
            await client.move_member(member,channel)
            await client.delete_channel(channel)
        cec = False        

@client.command(pass_context=True)
async def loto(ctx,chiffre):
    chiffre = int(chiffre)
    if(0<chiffre)&(chiffre<501):
        if await test_cooldown(ctx,str(ctx.message.author)):
            val = randint(1,500)
            if chiffre == val:
                await client.send_message(ctx.message.channel,'Tu as gagné')
                roles = ctx.message.server.roles
                role = discord.utils.get(roles, name='petitfdp')
                await client.add_roles(ctx.message.author, role)
            else:
                await client.send_message(ctx.message.channel,'Tu as perdu, mon chiffre était '+str(val))
            cooldown.append([str(ctx.message.author),time()])
    else:
        await client.send_message(ctx.message.channel,'Gros fdp met un chiffre entre 1 et 500')

@client.command(pass_context=True)
async def punir(ctx,member: discord.Member,time):
    global cec
    if cec == False:
        cec = True
        if await test_role(ctx.message.author):
            channel = ctx.message.server.afk_channel
            for i in range(0,int(time)):
                await client.move_member(member,channel)
                temps=randint(1,30)
                if (i != int(time)-1):
                    print(temps)
                    sleep(temps)
            await client.send_message(ctx.message.channel,'Punition terminé')
    cec = False

@client.command(pass_context=True)
async def bdsm(ctx,member: discord.Member,time):
    global cec
    if cec == False:
        cec = True
        if await test_role(ctx.message.author):
            channel = ctx.message.server.afk_channel
            for i in range(0,int(time)):
                await client.move_member(member,channel)
                sleep(1)
            await client.send_message(ctx.message.channel,'BDSM terminé')
    cec = False

@client.command(pass_context=True)
async def purge(ctx,nbmessage):
    nbmessage = int(nbmessage)
    channel = ctx.message.channel
    await client.purge_from(channel, limit=nbmessage+1, check=None, before=None, after=None, around=None)

@client.command(pass_context=True)
async def rip(ctx,member: discord.Member):
    if await test_role(ctx.message.author):
        roles = ctx.message.server.roles
        role = discord.utils.get(roles, name='Victime')
        if not role in member.roles:
            await client.add_roles(member, role)
            print("Role ajouté à",str(member))
            channel = ctx.message.server.afk_channel
            await client.move_member(member,channel)

@client.command(pass_context=True)
async def srip(ctx,member: discord.Member):
    roles = ctx.message.server.roles
    role = discord.utils.get(roles, name='Victime')
    if role in member.roles:
        await client.remove_roles(member, role)
        print("Role enlevé à",str(member))

async def test_role(member):
    role_names = [role.name for role in member.roles]
    test = False
    if ("grosfdp" in role_names) or ("petitfdp" in role_names):
        test = True
        if ("petitfdp" in role_names):
            role = discord.utils.get(member.roles, name='petitfdp')
            if role in member.roles:
                await client.remove_roles(member, role)
    return test

async def test_cooldown(ctx,nom):
    test = True
    for member in cooldown:
        if member[0] == nom:
            if (time()-member[1])>60:
                cooldown.remove(member)
                test = True
            else:
                await client.send_message(ctx.message.channel,'Le cooldown est pas fini, il reste '+str(60-int((time()-member[1])))+' s')
                test = False
            break
    return test
                
client.run(os.environ['BOT_ID'])
