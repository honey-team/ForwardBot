import discord
from discord import app_commands
from os import getenv
import aiohttp
from bs4 import BeautifulSoup
from copy import deepcopy
import aiosqlite

image_types = {'image/jpeg', 'image/png', 'image/webp'}
data_file = 'messages.db'

class MyTranslator(app_commands.Translator):
    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ) -> str | None:
        message = str(string)
        if locale is discord.Locale.russian:
            if message == 'Forward':
                return 'Переслать'
            if message == 'Send the saved message(s) to another channel':
                return 'Отправить сохраненное сообщение(я) в другой канал'
            if message == 'Whether to show the original message link. Might be needed to set to off on some servers.':
                return 'Показывать ли ссылку на оригинальное сообщение. Может понадобиться выключить на некоторых серверах.'
            if message == 'Whether to send the message anonymously.':
                return 'Отправлять ли сообщение анонимно.'
            if message == 'send':
                return 'отправить'
            if message == 'preview':
                return 'предпросмотр'
            if message == 'Preview the saved message(s)':
                return 'Предпросмотр сохраненных сообщений'
            if message == 'delete':
                return 'удалить'
            if message == 'Delete the saved message(s)':
                return 'Удалить сохраненное сообщение(я)'
        return
    
async def create_send_embeds(ctx: discord.Interaction, show_original: bool=True, anonymous: bool=False, show_ids: bool=False) -> dict:
    embeds: list[discord.Embed] = []
    conn = await aiosqlite.connect(data_file)
    cursor = await conn.execute('SELECT * FROM Messages WHERE user_id = ? ORDER BY id', (ctx.user.id,))
    messages = await cursor.fetchall()
    for i, message in enumerate(messages):
        await cursor.execute('SELECT filename, url, image, tenor FROM Attachments WHERE message_id = ? AND user_id = ?', (message[0], message[1]))
        attachments = await cursor.fetchall()
        image = discord.utils.find(lambda a: a[2] == 1, attachments)
        if i == 0:
            embeds.append(discord.Embed(title=f'{getenv("EMOJI") or ""} *Forwarded*' if not ctx.locale is discord.Locale.russian else f'{getenv("EMOJI") or ""} *Переслано*', description=message[3] if image and image[3] == 0 else None))
        else:
            embeds.append(discord.Embed(description=message[3] if image and image[3] != 1 else None))
        if image is not None:
            embeds[i].set_image(url=image[1])
        for a in attachments:
            if a[2] != 1:
                embeds[i].add_field(name='', value=f'[{a[0]}]({a[1]})')
        if show_original:
            embeds[i].add_field(name='', value=message[2], inline=False)
        if show_ids:
            embeds[i].set_author(name='ID: ' + str(i+1))
    await cursor.close()
    await conn.close()
    if anonymous:
        return {'embeds': embeds}
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=f'Forwarded by {ctx.user.name}' if not ctx.locale is discord.Locale.russian else f'Переслано {ctx.user.name}', disabled=True))
    return {'embeds': embeds, 'view': view}

# database shit

async def initiate_db(filename: str):
    conn = await aiosqlite.connect(filename)
    cursor = await conn.cursor()
    await cursor.executescript('''
                               CREATE TABLE IF NOT EXISTS Messages (
                               id INTEGER,
                               user_id INTEGER,
                               footer TEXT,
                               message TEXT
                               );
                               CREATE TABLE IF NOT EXISTS Attachments (
                               message_id INTEGER,
                               user_id INTEGER,
                               filename TEXT,
                               url TEXT,
                               image INTEGER,
                               tenor INTEGER
                               )''')
    await conn.commit()
    await conn.close()

async def add_message(ctx: discord.Interaction, message: discord.Message):
    conn = await aiosqlite.connect('messages.db')
    cursor = await conn.cursor()
    await cursor.execute('SELECT id FROM Messages WHERE user_id = ? ORDER BY id DESC', (ctx.user.id,))
    id = await cursor.fetchone()
    if id is None:
        id = 1
    else:
        id = id[0] + 1
    if message.author.id == ctx.client.user.id:
        for embed in message.embeds:
            await cursor.execute('INSERT INTO Messages VALUES (?, ?, ?, ?)', (id, ctx.user.id, embed.fields[-1].value if embed.fields and not embed.fields[-1].inline else None, embed.description))
            if embed.image:
                await cursor.execute('INSERT INTO Attachments (message_id, user_id, url, image) VALUES (?, ?, ?, 1)', (id, ctx.user.id, embed.image.url))
            for a in embed.fields:
                if not a.inline:
                    continue
                await cursor.execute('INSERT INTO Attachments VALUES (?, ?, ?, ?, 0, 0)', (id, ctx.user.id, a.name, a.value))
            id += 1
    else:
        await cursor.execute('INSERT INTO Messages VALUES (?, ?, ?, ?)', (id, ctx.user.id, f'-# [{message.author.name}・<t:{int(message.created_at.timestamp())}:t>]({message.jump_url})', message.content))
        tenor = message.embeds and message.embeds[0].url is not None and message.embeds[0].url.startswith('https://tenor.com/view/')
        image = discord.utils.find(lambda a: a.content_type in image_types, message.attachments)
        if image is None:
            if tenor:
                async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}) as session:
                    async with session.get(message.embeds[0].url) as r:
                        data = await r.text()
                image = f"https://c.tenor.com/{BeautifulSoup(data, 'html.parser').find('meta', itemprop='contentUrl')['content'].split('/')[4]}/tenor.gif"
            elif message.embeds and message.embeds[0].type == 'image':
                image = message.embeds[0].url
        else:
            image = image.url
        if image is not None:
            await cursor.execute('INSERT INTO Attachments (message_id, user_id, url, image, tenor) VALUES (?, ?, ?, 1, ?)', (id, ctx.user.id, image, 1 if message.embeds and tenor and message.embeds[0].url == message.content else 0))
        for attachment in message.attachments:
            if attachment.url == image:
                continue
            await cursor.execute('INSERT INTO Attachments VALUES (?, ?, ?, ?, 0, 0)', (id, ctx.user.id, attachment.filename, attachment.url))
    await conn.commit()
    await conn.close()

async def delete_messages(user_id: int, message_id: int=None):
    async with aiosqlite.connect(data_file) as conn:
        if message_id is None:
            await conn.execute('DELETE FROM Messages WHERE user_id = ?', (user_id,))
            await conn.execute('DELETE FROM Attachments WHERE user_id = ?', (user_id,))
            await conn.commit()
            return
        true_id = (await (await conn.execute('SELECT id FROM Messages WHERE user_id = ?', (user_id,))).fetchall())[message_id - 1][0]
        await conn.execute('DELETE FROM Messages WHERE id = ? AND user_id = ?', (true_id, user_id))
        await conn.execute('DELETE FROM Attachments WHERE message_id = ? AND user_id = ?', (true_id, user_id))
        await conn.commit()