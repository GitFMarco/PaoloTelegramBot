from paolo_tg_bot import awake_paolo
import json


if __name__ == "__main__":
    with open("token.json") as f:
        try:
            token = json.load(f)["token"]

        except Exception:
            raise "Something went wrong with the token fetch. Make sure you have a token.json file in this project."

        else:
            awake_paolo(token)
