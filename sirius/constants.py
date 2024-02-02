import os

from dotenv import load_dotenv
from typing import Dict, List, Literal

from dacite import from_dict
from yaml import safe_load

from sirius.base import Guideline

load_dotenv()


GUIDELINE: Guideline = from_dict(Guideline, safe_load(open("sirius/pre_prompt_sirius.yml", "r")))

NAME = GUIDELINE.name
INSTRUCTIONS = GUIDELINE.instructions
EXAMPLES = GUIDELINE.example_conversations


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

BOT_INVITE_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=328565073920&scope=bot"