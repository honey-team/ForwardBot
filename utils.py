import discord
from discord import app_commands
from os import getenv
import aiohttp
from bs4 import BeautifulSoup

image_types = {'image/jpeg', 'image/png', 'image/webp'}

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
        return
    
async def create_send_embeds(ctx: discord.Interaction, messages: list[discord.Message], show_original: bool=True, anonymous: bool=False) -> dict:
    embeds: list[discord.Embed] = []
    for i, message in enumerate(messages):
        tenor = message.embeds and message.embeds[0].url.startswith('https://tenor.com/view/') # kill tenor
        if i == 0:
            embeds.append(discord.Embed(title=f'{getenv("EMOJI") or ""} *Forwarded*', description=message.content if not (message.embeds and message.content == message.embeds[0].url) else None))
        else:
            embeds.append(discord.Embed(description=message.content))
        image = discord.utils.find(lambda a: a.content_type in image_types, message.attachments)
        if image is None:
            if tenor:
                async with aiohttp.ClientSession(headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}) as session:
                    async with session.get(message.embeds[0].url) as r:
                        data = await r.text()
                embeds[i].set_image(url=f"https://c.tenor.com/{BeautifulSoup(data, 'html.parser').find('meta', itemprop='contentUrl')['content'].split('/')[4]}/tenor.gif")
            elif message.embeds and message.embeds[0].type == 'image':
                embeds[i].set_image(url=message.embeds[0].url)
        else:
            embeds[i].set_image(url=image.url)
        for a in message.attachments:
            if a != image:
                embeds[i].add_field(name='', value=f'[{a.filename}]({a.url})')
        if show_original:
            embeds[i].add_field(name='', value=f'-# [{message.author.name}・<t:{int(message.created_at.timestamp())}:t>]({message.jump_url})', inline=False)
    if anonymous:
        return {'embeds': embeds}
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=f'Forwarded by {ctx.user.name}' if not ctx.locale is discord.Locale.russian else f'Переслано {ctx.user.name}', disabled=True))
    return {'embeds': embeds, 'view': view}