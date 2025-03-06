import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

completion = client.completions.create(
    model = "gpt-3.5-turbo-instruct",
    prompt = "Say this is a test",
    max_tokens = 7,
    temperature = 0
)

print(completion.choices[0].text.strip())