import discord
from discord import app_commands
from dotenv import load_dotenv
from os import getenv
from utils import *
load_dotenv()

bot = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(bot)
messages: dict[int, list[discord.Message]] = {}

@bot.event
async def on_ready():
    await tree.set_translator(MyTranslator())
    await tree.sync()

@tree.context_menu(name=app_commands.locale_str('Forward'))
@app_commands.user_install()
async def forward(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in messages:
        messages[interaction.user.id] = [message]
        if interaction.locale is discord.Locale.russian:
            await interaction.followup.send('Сообщение сохранено. Теперь используйте команду `/отправить`, чтобы отправить его в другой канал.')
        else:
            await interaction.followup.send('Message saved. Now, use the `/send` command to send it to another channel.')
        return
    class AskButton(discord.ui.Button):
        async def callback(self, ctx: discord.Interaction):
            if self.custom_id == 'yes':
                if len(messages[ctx.user.id]) < 10:
                    messages[ctx.user.id].append(message)
                    if ctx.locale is discord.Locale.russian:
                        await ctx.response.edit_message(content='Сообщение добавлено в список. Теперь используйте команду `/отправить`, чтобы отправить все сообщения в другой канал.',view=None)
                    else:
                        await ctx.response.edit_message(content='Message added to the list. Now, use the `/send` command to send all messages to another channel.',view=None)
                else:
                    if ctx.locale is discord.Locale.russian:
                        await ctx.response.send_message(content='Вы достигли максимального лимита в 10 сообщений. Пожалуйста, отправьте сохраненные сообщения с помощью команды `/отправить` или перезапишите их.')
                    else:
                        await ctx.response.send_message(content='You have reached the maximum limit of 10 messages. Please send the messages you have saved using the `/send` command or overwrite them.')
                return
            messages[ctx.user.id] = [message]
            if ctx.locale is discord.Locale.russian:
                await ctx.response.edit_message(content='Сообщение сохранено. Теперь используйте команду `/отправить`, чтобы отправить его в другой канал.', view=None)
            else:
                await ctx.response.edit_message(content='Message saved. Now, use the `/send` command to send it to another channel.', view=None)
    view = discord.ui.View()
    if interaction.locale is discord.Locale.russian:
        view.add_item(AskButton(label='Да', custom_id='yes', style=discord.ButtonStyle.green))
        view.add_item(AskButton(label='Нет, удалить все остальные сообщения', custom_id='no', style=discord.ButtonStyle.red))
    else:
        view.add_item(AskButton(label='Yes', custom_id='yes', style=discord.ButtonStyle.green))
        view.add_item(AskButton(label='No, delete all other messages', custom_id='no', style=discord.ButtonStyle.red))
    if len(message.attachments) > 1 and discord.utils.find(lambda a: a.content_type.startswith('image'), message.attachments):
        if interaction.locale is discord.Locale.russian:
            await interaction.followup.send('У вас уже сохранено сообщение. Хотите добавить его в список?\n-# ПРИМЕЧАНИЕ: Вы можете сохранить до 10 сообщений. Только первое изображение будет видно как изображение.', view=view)
        else:
            await interaction.followup.send('You have already saved a message. Would you like to add it to the list?\n-# NOTE: You can save up to 10 messages. Only first image will be visible as image.', view=view)
        return
    if interaction.locale is discord.Locale.russian:
        await interaction.followup.send('У вас уже сохранено сообщение. Хотите добавить его в список?\n-# ПРИМЕЧАНИЕ: Вы можете сохранить до 10 сообщений.', view=view)
    else:
        await interaction.followup.send('You have already saved a message. Would you like to add it to the list?\n-# NOTE: You can save up to 10 messages.', view=view)

@tree.command(name=app_commands.locale_str('send'), description=app_commands.locale_str('Send the saved message(s) to another channel'))
@app_commands.describe(show_original=app_commands.locale_str('Whether to show the original message link. Might be needed to set to off on some servers.'), anonymous=app_commands.locale_str('Whether to send the message anonymously.'))
@app_commands.user_install()
async def send(ctx: discord.Interaction, show_original: bool=True, anonymous: bool=False):
    if ctx.user.id not in messages:
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Вы не сохранили никаких сообщений для отправки. Используйте контекстное меню `Переслать`', ephemeral=True)
        else:
            await ctx.response.send_message('You have not saved any messages to send. Use context menu option `Forward`', ephemeral=True)
        return
    if anonymous:
        await ctx.response.send_message(':shushing_face:', ephemeral=True)
    else:
        await ctx.response.defer()
    await ctx.followup.send(**await create_send_embeds(ctx, messages[ctx.user.id], show_original, anonymous))
    del messages[ctx.user.id]

@tree.command(name=app_commands.locale_str('preview'), description=app_commands.locale_str('Preview the saved message(s)'))
@app_commands.user_install()
async def preview(ctx: discord.Interaction):
    if ctx.user.id not in messages:
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Вы не сохранили никаких сообщений для перессылки. Используйте контекстное меню `Переслать`', ephemeral=True)
        else:
            await ctx.response.send_message('You have not saved any messages to forward. Use context menu option `Forward`', ephemeral=True)
        return
    await ctx.response.send_message('That\'s how your message will look like:' if not ctx.locale is discord.Locale.russian else 'Так выглядит ваше сообщение:', **await create_send_embeds(ctx, messages[ctx.user.id], anonymous=True, show_ids=True), ephemeral=True)

@tree.command(name=app_commands.locale_str('delete'), description=app_commands.locale_str('Delete the saved message(s)'))
@app_commands.describe(id=app_commands.locale_str('ID of the message to delete (leave blank to delete all)'))
@app_commands.user_install()
async def delete(ctx: discord.Interaction, id: app_commands.Range[int, 1, 10]=None):
    if ctx.user.id not in messages:
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Вы не сохранили никаких сообщений для перессылки. Используйте контекстное меню `Переслать`', ephemeral=True)
        else:
            await ctx.response.send_message('You have not saved any messages to forward. Use context menu option `Forward`', ephemeral=True)
        return
    if id is None or (id == 1 and len(messages[ctx.user.id]) == 1):
        del messages[ctx.user.id]
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Все сообщения были удалены.', ephemeral=True)
        else:
            await ctx.response.send_message('All messages were deleted.', ephemeral=True)
        return
    if id > len(messages[ctx.user.id]):
        if ctx.locale is discord.Locale.russian:
            await ctx.response.send_message('Такого сообщения нет.', ephemeral=True)
        else:
            await ctx.response.send_message('There is no such message.', ephemeral=True)
        return
    messages[ctx.user.id].pop(id-1)
    if ctx.locale is discord.Locale.russian:
        await ctx.response.send_message('Сообщение было удалено.', ephemeral=True)
    else:
        await ctx.response.send_message('Message was deleted.', ephemeral=True)
    
bot.run(getenv('TOKEN'))