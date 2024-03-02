import os

from dotenv import load_dotenv

from openai import OpenAI, completions, api_key


load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def test_completion():
    response = client.chat.completions.create(
        messages = [
            {'role': 'user', 'content': 'what is the first rule of fight club?'}
        ],
        model="gpt-3.5-turbo",
        max_tokens=1
    )

    assert len(response.choices) == 1
    assert response.choices[0].finish_reason == "length"
    assert len(response.choices[0].message.content) > 0