import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal, Type, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


class LlmAdapter:
    def __init__(self, mode: Literal["live", "replay", "record"] = "live"):
        self.mode = mode
        self.cache_dir = Path("eval/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # In replay mode, we don't need a real key.
        api_key = os.environ.get("ANTHROPIC_API_KEY", "dummy_key_for_replay")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.default_model = os.environ.get("AGENT_MODEL_MAIN", "claude-3-5-haiku-latest")

    def _hash_request(self, model: str, system: str, prompt: str, schema: dict) -> str:
        data = {
            "model": model,
            "system": system,
            "prompt": prompt,
            "schema": schema,
        }
        raw = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def generate_structured(
        self,
        system: str,
        prompt: str,
        response_model: Type[T],
        model: str | None = None,
    ) -> T:
        model_name = model or self.default_model
        schema = response_model.model_json_schema()
        
        req_hash = self._hash_request(model_name, system, prompt, schema)
        cache_file = self.cache_dir / f"{req_hash}.json"

        # Check cache if in replay or live mode
        if self.mode in ("replay", "live") and cache_file.exists():
            with open(cache_file, "r") as f:
                cached_data = json.load(f)
                return response_model.model_validate(cached_data["response"])

        if self.mode == "replay":
            raise LLMError(f"Cache miss in replay mode for hash {req_hash}")

        # Call Anthropic with tools to force structured output
        tool_name = "extract_" + response_model.__name__.lower()
        tool = {
            "name": tool_name,
            "description": "Extract structured data",
            "input_schema": schema,
        }

        try:
            response = self.client.messages.create(
                model=model_name,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
            )
            
            # Find the tool use block
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if not tool_use:
                raise LLMError("Model did not return the requested tool call.")
                
            result_data = tool_use.input
            
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}")
            
        # Validate with Pydantic
        validated = response_model.model_validate(result_data)
        
        # Save to cache if recording or live
        if self.mode in ("record", "live"):
            with open(cache_file, "w") as f:
                json.dump({
                    "request_hash": req_hash,
                    "model": model_name,
                    "response": result_data,
                }, f, indent=2)
                
        return validated
