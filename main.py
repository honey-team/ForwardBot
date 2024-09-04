import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from os import getenv
load_dotenv()

bot = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(bot)
messages: dict[int, list[discord.Message]] = {}

@bot.event
async def on_ready():
    await tree.sync()

@tree.context_menu(name='Forward')
@app_commands.user_install()
async def forward(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in messages:
        messages[interaction.user.id] = [message]
        await interaction.followup.send('Message saved. Now, use the `/send` command to send it to another channel.')
        return
    class AskButton(discord.ui.Button):
        async def callback(self, ctx: discord.Interaction):
            if self.custom_id == 'yes':
                if len(messages[ctx.user.id]) < 10:
                    messages[ctx.user.id].append(message)
                    await ctx.response.edit_message(content='Message added to the list. Now, use the `/send` command to send all messages to another channel.',view=None)
                else:
                    await ctx.response.send_message(content='You have reached the maximum limit of 10 messages. Please send the messages you have saved using the `/send` command or overwrite.')
                return
            messages[ctx.user.id] = [message]
            await ctx.response.edit_message(content='Message saved. Now, use the `/send` command to send it to another channel.', view=None)
    view = discord.ui.View()
    view.add_item(AskButton(label='Yes', custom_id='yes', style=discord.ButtonStyle.green))
    view.add_item(AskButton(label='No, delete all other messages', custom_id='no', style=discord.ButtonStyle.red))
    if len(message.attachments) > 1 and discord.utils.find(lambda a: a.content_type.startswith('image'), message.attachments):
        await interaction.followup.send('You have already saved a message. Would you like to add it to the list?\n-# NOTE: You can save up to 10 messages. Only first image will be visible as image.', view=view)
        return
    await interaction.followup.send('You have already saved a message. Would you like to add it to the list?\n-# NOTE: You can save up to 10 messages.', view=view)

@tree.command(description='Send the saved message(s) to another channel')
@app_commands.describe(show_original='Whether to show the original message link. Might be needed to set to off on servers with strict automod.')
@app_commands.user_install()
async def send(ctx: discord.Interaction, show_original: bool=True):
    if ctx.user.id not in messages:
        await ctx.response.send_message('You have not saved any messages to send. Use context menu option `Forward`', ephemeral=True)
        return
    embeds: list[discord.Embed] = []
    for i, message in enumerate(messages[ctx.user.id]):
        if i == 0:
            embeds.append(discord.Embed(title=f'{getenv("EMOJI") or ""} *Forwarded*', description=message.content, timestamp=message.created_at))
        else:
            embeds.append(discord.Embed(description=message.content, timestamp=message.created_at))
        embeds[i].set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        image = discord.utils.find(lambda a: a.content_type.startswith('image'), message.attachments)
        if image is not None:
            embeds[i].set_image(url=image.url)
        for a in message.attachments:
            if a != image:
                embeds[i].add_field(name=a.filename, value=f'[Link to attachment]({a.url})')
        if show_original:
            embeds[i].add_field(name='Original Message', value=f'[Link to message]({message.jump_url})', inline=False)
        embeds[i].set_footer(text=f'Forwarded by {ctx.user.name}', icon_url=ctx.user.display_avatar.url)
    await ctx.response.send_message(embeds=embeds)
    del messages[ctx.user.id]

bot.run(getenv('TOKEN'))
