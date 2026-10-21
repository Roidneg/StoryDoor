import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise SystemExit("GROQ_API_KEY is missing from .env.")

with Groq(api_key=api_key, timeout=30.0, max_retries=0) as client:
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: StoryDoor is connected.",
            }
        ],
        reasoning_effort="low",
        max_completion_tokens=256,
    )

    print("Model:", response.model)
    print("Reply:", response.choices[0].message.content)
    print("Finish reason:", response.choices[0].finish_reason)