from paolo_tg_bot import awake_paolo
from os import getenv


if __name__ == "__main__":
    with open("token.json") as f:
        token = getenv("TELEGRAM_TOKEN")
        if token is None:
            raise Exception("Missing TELEGRAM_TOKEN environment variable. It needs to contain a valid telegram bot token.")

        awake_paolo(token)
