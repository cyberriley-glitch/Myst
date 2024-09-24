# Myst

## Installation
Install dependency packages by running `pip3 install -r requirements.txt`

Create a File called `.env` and place it in the root of this folder. Enter the following for its contents. Replace where necessary:
```
BOT_TOKEN=<your discord token>
```

## Running it
Run the bot by running it with `python3 main.py`

## Run as Service
Install the Service File on the Server by running the following commands. Prior, you should check the file for changes you might need to apply
```
cp discord-bot.service /etc/systemd/system/discord-bot.service
systemctl daemon-reload
systemctl enable discord-bot
systemctl start discord-bot
```