import os
import openai

client = openai.OpenAI(api_key="lm-studio", base_url="http://127.0.0.1:1234/v1")
response = client.chat.completions.create(
    model="qwen/qwen3.6-35b-a3b",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=600,
)
print(response)
