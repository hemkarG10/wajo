from src.agent.llm import LlmAdapter
from src.agent.models import InjectionJudgement
llm = LlmAdapter(provider="openai_compat")
try:
    res, i, o = llm._call_openai_compat("qwen/qwen3.6-35b-a3b", "System", "Prompt", InjectionJudgement)
    print("Success:", res)
except Exception as e:
    print("Error:", e)
