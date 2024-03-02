from typing import Optional, List
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    user: str
    text: Optional[str] = None

    def render(self):
        result = self.user + ":"
        if self.text is not None:
            result += " " + self.text
        return result


@dataclass
class Conversation:
    messages: List[Message]

    def prepare(self, message: Message):
        self.messages.insert(0, message)
        return self

    def render(self):
        return "<|endoftext|>".join(
            [message.render() for message in self.messages]
        )
        

@dataclass(frozen=True)
class Guideline:
    name: str
    instructions: str
    example_conversations: List[Conversation]