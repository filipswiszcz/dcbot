from typing import List
from dataclasses import dataclass


@dataclass(frozen=True)
class Guideline:
    name: str
    instructions: str
    example_conversations: List[Conversation]