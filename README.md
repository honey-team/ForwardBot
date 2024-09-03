<p align=center>
    <img src="logo.png" width="250" />
</p>

A little discord bot for forwarding messages from one channel to another.

Add it! https://discord.com/oauth2/authorize?client_id=1279742984912375819

## Installation / Selfhosting

1. Clone the repository

```bash
git clone https://github.com/honey-team/ForwardBot.git
```

2. Install the dependencies

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory and add the following variables:

```bash
TOKEN=your-token-here
EMOJI=your-emoji-here
```

Create a new application on the [Discord Developer Portal](https://discord.com/developers/applications) and copy the token, then add forward.png as emoji to the application. (bot is intended to support user install)

4. Run the bot

```bash
python main.py
```