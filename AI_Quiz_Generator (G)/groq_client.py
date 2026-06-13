import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)


def generate_questions(topic: str) -> list[dict]:
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a quiz generator. Generate exactly 5 multiple choice questions. "
                    "Each question must match the user's topic, have exactly 4 options, and only one correct answer. "
                    "Questions should be easy difficulty and short. "
                    "Return JSON only in this exact format with no markdown, no explanation, and no extra text: "
                    '[{"question":"...","options":["A","B","C","D"],"answer":"..."}]'
                ),
            },
            {
                "role": "user",
                "content": f"Topic: {topic}",
            },
        ],
    )
    raw_text = completion.choices[0].message.content.strip()
    quiz = json.loads(raw_text)

    if not isinstance(quiz, list):
        raise ValueError("Response is not a JSON list.")
    if len(quiz) != 5:
        raise ValueError(f"Expected exactly 5 questions, got {len(quiz)}.")

    for i, q in enumerate(quiz):
        for key in ("question", "options", "answer"):
            if key not in q:
                raise ValueError(f"Question {i + 1} missing key: {key}")
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            raise ValueError(f"Question {i + 1} must have exactly 4 options.")

    return quiz


#if __name__ == "__main__":
    #response = generate_questions("BIBLE")
    #print(json.dumps(response, indent=2))
