import discord
from discord.ext.commands import Bot
from discord.ext import commands
from random import randint
from time import sleep,time

Client = discord.Client()
client = commands.Bot(command_prefix='!')
cec = False
allow_roulette = True
cooldown = []

@client.event
async def on_ready():
    print("Bot Ready")
    print(client.user.name)
    print(client.user.id)

@client.event
async def on_message(message):
    if message.author.bot == False and( message.content != '' or message.attachments != []):
        channel = discord.utils.get(message.server.channels, name='logs-general',type=discord.ChannelType.text)
        embed = discord.Embed(title='Message créé',color=0x2ecc71,description=str(message.timestamp)+' UTC')
        embed.set_author(name=str(message.author),icon_url=message.author.avatar_url)
        embed.add_field(name='Channel',value=str(message.channel),inline=False)
        embed.set_footer(text='id : '+str(message.id))
        if message.content != '' :
            embed.add_field(name='Contenu',value=str(message.clean_content),inline=False)
        if message.attachments != []:
            attachement = message.attachments[0]
            embed.add_field(name='URL fichier',value=attachement['url'],inline=False)
        await client.send_message(channel,embed = embed)
        await client.process_commands(message)

@client.event
async def on_message_delete(message):
    if message.author.bot == False :
        channel = discord.utils.get(message.server.channels, name='logs-general',type=discord.ChannelType.text)
        embed = discord.Embed(title='Message suprimé',color=0xe74c3c,description=str(message.timestamp)+' UTC')
        embed.set_author(name=str(message.author),icon_url=message.author.avatar_url)
        embed.add_field(name='Channel',value=str(message.channel),inline=False)
        embed.set_footer(text='id : '+str(message.id))
        if message.content != '' :
            embed.add_field(name='Contenu',value=str(message.clean_content),inline=False)
        if message.attachments != []:
            attachement = message.attachments[0]
            embed.add_field(name='URL fichier',value=attachement['url'],inline=False)
        await client.send_message(channel,embed = embed)

@client.event
async def on_message_edit(before,after):
    if after.author.bot == False and before.content != after.content:
        channel = discord.utils.get(after.server.channels, name='logs-general',type=discord.ChannelType.text)
        embed = discord.Embed(title='Message édité',color=0x3498db,description=str(after.timestamp)+' UTC')
        embed.set_author(name=str(after.author),icon_url=after.author.avatar_url)
        embed.add_field(name='Channel',value=str(after.channel),inline=False)
        embed.set_footer(text='id : '+str(after.id))
        if after.content != '' :
            embed.add_field(name='Contenu avant modification',value=str(before.clean_content),inline=False)
            embed.add_field(name='Contenu après modification',value=str(after.clean_content),inline=False)
        if after.attachments != []:
            attachement = after.attachments[0]
            embed.add_field(name='URL fichier',value=attachement['url'],inline=False)
        await client.send_message(channel,embed = embed)
            
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
async def roulette(ctx,chiffre,member: discord.Member =None):
    global cec,allow_roulette
    if cec == False and allow_roulette == True:
        cec = True
        if member == None:
            role_names = [role.name for role in ctx.message.author.roles]
        else:
            role_names = [role.name for role in member.roles]
            role_namesuser = [role.name for role in ctx.message.author.roles]
            if not("grosfdp" in role_namesuser):
                member = None
                role_names = role_namesuser
        chiffre = int(chiffre)
        if(1<chiffre)&(chiffre<7):
            val = randint(1,6)
            if chiffre == val:
                await client.send_message(ctx.message.channel,'Tu as gagné')
            else:
                await client.send_message(ctx.message.channel,'Tu as perdu, mon chiffre était '+str(val))
                if not("grosfdp" in role_names):
                    await client.send_message(ctx.message.channel,'Au revoir')
                    if member == None:
                        await client.kick(ctx.message.author)
                    else:
                        await client.kick(member)
        else:
            await client.send_message(ctx.message.channel,'Gros fdp met un chiffre entre 1 et 6')
    elif allow_roulette == False :
        await client.send_message(ctx.message.channel,'La roulette est désactivé')
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
        if await test_role():
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
    await client.purge_from(channel, limit=nbmessage, check=None, before=None, after=None, around=None)

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

@client.command(pass_context=True)
async def aide(ctx):
    await client.send_message(ctx.message.channel,"```!loto : Mettez un chiffre entre 1 et 500, si vous gagner vous avez le droit d'utiliser une fois une autre commande\n\n!kick mention : Kick la personne mentionné\n\n!punir mention n :Déplace la personne mentionné n fois dans l'afk avec un temps aleatoire entre chaque déplacement\n\n!bdsm mention x : Déplace la personne mentionner pendant x secondes dans l'afk```")

@client.command(pass_context=True)
async def config_roulette(ctx):
    global allow_roulette
    if await test_role(ctx.message.author):
        if allow_roulette == True:
            allow_roulette = False
            await client.send_message(ctx.message.channel,'La roulette est désactivé')
        elif allow_roulette == False:
            allow_roulette = True
            await client.send_message(ctx.message.channel,'La roulette est activé')

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
                
client.run("Mzk3MDE1NDc2MjA4NjY0NTc5.DSp1HA.uzMjC5itib65fYEpVKh4ooOXsp4")
