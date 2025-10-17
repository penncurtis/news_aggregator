import os, re
from openai import OpenAI

def extractive_summary(text: str, max_sent=3) -> str:
    # naive top-sentence selection by position & length
    sents = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sents[:max_sent])

def llm_summary(text: str) -> str:
    api = os.getenv("OPENAI_API_KEY")
    if not api: return extractive_summary(text)
    client = OpenAI(api_key=api)
    prompt = f"Summarize in 3 concise bullets:\n\n{text[:8000]}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()
