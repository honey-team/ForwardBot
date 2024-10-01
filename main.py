import discord
from discord import app_commands
from dotenv import load_dotenv
from os import getenv, path
from utils import *
import aiosqlite
load_dotenv()

bot = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(bot)
initialized = False

@bot.event
async def on_ready():
    global SEND, DELETE, initialized
    if initialized:
        return
    if not path.isfile(data_file):
        await initiate_db(data_file)
    await tree.set_translator(MyTranslator())
    for command in await tree.sync():
        if command.name == 'send':
            SEND = f'</send:{command.id}>'
        elif command.name == 'delete':
            DELETE = f'</delete:{command.id}>'
    initialized = True

@tree.context_menu(name=app_commands.locale_str('Forward'))
@app_commands.allowed_installs(True, True)
@app_commands.allowed_contexts(True, True, True)
async def forward(ctx: discord.Interaction, message: discord.Message):
    await ctx.response.defer(ephemeral=True)
    async with aiosqlite.connect(data_file) as conn:
        messages = (await (await conn.execute('SELECT COUNT(*) FROM Messages WHERE user_id = ?', (ctx.user.id,))).fetchone())[0]
    if message.author.id == bot.user.id:
        if messages + len(message.embeds) > 10:
            if ctx.locale is discord.Locale.russian:
                await ctx.followup.send(f'Вы достигли максимального лимита в 10 сообщений. Пожалуйста, отправьте сохраненные сообщения с помощью команды {SEND} или удалите их с помощью команды {DELETE}.')
            else:
                await ctx.followup.send(f'You have reached the maximum limit of 10 messages. Please send the messages you have saved using the {SEND} command or delete them using the {DELETE} command.')
            return
        await add_message(ctx, message)
        if ctx.locale is discord.Locale.russian:
            await ctx.followup.send(f'Сообщения добавлены в список. Теперь используйте команду {SEND}, чтобы отправить все сообщения в другой канал.')
        else:
            await ctx.followup.send(f'Messages added to the list. Now, use the {SEND} command to send all messages to another channel.')
        return
    if messages < 10:
        await add_message(ctx, message)
        if ctx.locale is discord.Locale.russian:
            await ctx.followup.send(f'Сообщение добавлено в список. Теперь используйте команду {SEND}, чтобы отправить все сообщения в другой канал.')
        else:
            await ctx.followup.send(f'Message added to the list. Now, use the {SEND} command to send all messages to another channel.')
    else:
        if ctx.locale is discord.Locale.russian:
            await ctx.followup.send(f'Вы достигли максимального лимита в 10 сообщений. Пожалуйста, отправьте сохраненные сообщения с помощью команды {SEND} или удалите их с помощью команды {DELETE}.')
        else:
            await ctx.followup.send(f'You have reached the maximum limit of 10 messages. Please send the messages you have saved using the {SEND} command or delete them using the {DELETE} command.')

@tree.context_menu(name=app_commands.locale_str('Instant forward'))
@app_commands.allowed_installs(True, True)
@app_commands.allowed_contexts(True, True, True)
async def instant(ctx: discord.Interaction, message: discord.Message):
    await ctx.response.defer()
    embeds: list[discord.Embed] = []
    if message.author.id == bot.user.id:
        for i, m in enumerate(message.embeds):
            embeds.append(deepcopy(m))
            if i == 0:
                embeds[i].title = f'{getenv("EMOJI") or ""} *Forwarded*' if not ctx.locale is discord.Locale.russian else f'{getenv("EMOJI") or ""} *Переслано*'
            else:
                embeds[i].title = None
    else:
        tenor = message.embeds and message.embeds[0].type == 'gifv' and message.embeds[0].url.startswith('https://tenor.com/view/') # kill tenor
        image = discord.utils.find(lambda a: a.content_type in image_types, message.attachments)
        embeds.append(discord.Embed(title=f'{getenv("EMOJI") or ""} *Forwarded*' if not ctx.locale is discord.Locale.russian else f'{getenv("EMOJI") or ""} *Переслано*', description=message.content if not ((tenor or (message.embeds and message.embeds[0].type == 'image')) and message.content == message.embeds[0].url) else None))
        if image is None:
            if tenor:
                async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}) as session:
                    async with session.get(message.embeds[0].url) as r:
                        data = await r.text()
                embeds[0].set_image(url=f"https://c.tenor.com/{BeautifulSoup(data, 'html.parser').find('meta', itemprop='contentUrl')['content'].split('/')[4]}/tenor.gif")
            elif message.embeds and message.embeds[0].type == 'image':
                embeds[0].set_image(url=message.embeds[0].url)
        else:
            embeds[0].set_image(url=image.url)
        for a in message.attachments:
            if a != image:
                embeds[0].add_field(name='', value=f'[{a.filename}]({a.url})')
        embeds[0].add_field(name='', value=f'-# [{message.author.name}・<t:{int(message.created_at.timestamp())}:t>]({message.jump_url})', inline=False)
    await ctx.followup.send(embeds=embeds)

@tree.command(name=app_commands.locale_str('send'), description=app_commands.locale_str('Send the saved message(s) to another channel'))
@app_commands.describe(show_original=app_commands.locale_str('Whether to show the original message link. Might be needed to set to off on some servers.'), anonymous=app_commands.locale_str('Whether to send the message anonymously.'))
@app_commands.allowed_installs(True, True)
@app_commands.allowed_contexts(True, True, True)
async def send(ctx: discord.Interaction, show_original: bool=True, anonymous: bool=False):
    if not await message_check(ctx.user.id):
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Вы не сохранили никаких сообщений для отправки. Используйте контекстное меню `Переслать`', ephemeral=True)
        else:
            await ctx.response.send_message('You have not saved any messages to send. Use context menu option `Forward`', ephemeral=True)
        return
    if anonymous:
        await ctx.response.send_message(':shushing_face:', ephemeral=True)
    else:
        await ctx.response.defer()
    await ctx.followup.send(embeds=await create_send_embeds(ctx, show_original))
    await delete_messages(ctx.user.id)

@tree.command(name=app_commands.locale_str('preview'), description=app_commands.locale_str('Preview the saved message(s)'))
@app_commands.allowed_installs(True, True)
@app_commands.allowed_contexts(True, True, True)
async def preview(ctx: discord.Interaction):
    if not await message_check(ctx.user.id):
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Вы не сохранили никаких сообщений для перессылки. Используйте контекстное меню `Переслать`', ephemeral=True)
        else:
            await ctx.response.send_message('You have not saved any messages to forward. Use context menu option `Forward`', ephemeral=True)
        return
    await ctx.response.send_message('That\'s how your message will look like:' if not ctx.locale is discord.Locale.russian else 'Так выглядит ваше сообщение:', embeds=await create_send_embeds(ctx, show_ids=True), ephemeral=True)

@tree.command(name=app_commands.locale_str('delete'), description=app_commands.locale_str('Delete the saved message(s)'))
@app_commands.describe(id=app_commands.locale_str('ID of the message to delete (leave blank to delete all)'))
@app_commands.allowed_installs(True, True)
@app_commands.allowed_contexts(True, True, True)
async def delete(ctx: discord.Interaction, id: app_commands.Range[int, 1, 10]=None):
    async with aiosqlite.connect(data_file) as conn:
        messages = await (await conn.execute('SELECT id FROM messages WHERE user_id = ? ORDER BY id', (ctx.user.id,))).fetchall()
    if not messages:
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Вы не сохранили никаких сообщений для перессылки. Используйте контекстное меню `Переслать`', ephemeral=True)
        else:
            await ctx.response.send_message('You have not saved any messages to forward. Use context menu option `Forward`', ephemeral=True)
        return
    if id is None or (id == 1 and len(messages) == 1):
        await delete_messages(ctx.user.id)
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Все сообщения были удалены.', ephemeral=True)
        else:
            await ctx.response.send_message('All messages were deleted.', ephemeral=True)
        return
    if id > len(messages):
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Такого сообщения нет.', ephemeral=True)
        else:
            await ctx.response.send_message('There is no such message.', ephemeral=True)
        return
    await delete_messages(ctx.user.id, id)
    if ctx.locale is discord.Locale.russian:
        await ctx.response.send_message('Сообщение было удалено.', ephemeral=True)
    else:
        await ctx.response.send_message('Message was deleted.', ephemeral=True)
    
bot.run(getenv('TOKEN'))
