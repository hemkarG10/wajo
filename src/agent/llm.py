"""LLM adapter with multi-provider support.

Providers: openai_compat, gemini, anthropic, openai, heuristic.
Modes: live, replay, record, mock.
"""
import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeVar
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


class CacheMiss(LLMError):
    pass


class LlmAdapter:
    def __init__(
        self,
        mode: Literal["live", "replay", "record", "mock"] = "live",
        mock_responses: dict | None = None,
        provider: str | None = None,
    ):
        self.mode = mode
        self.mock_responses = mock_responses or {}
        self.cache_dir = Path(os.environ.get("AGENT_CACHE_DIR", "eval/cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.provider = provider or os.environ.get("AGENT_LLM_PROVIDER", "heuristic")
        assert self.provider in {"openai_compat", "gemini", "anthropic", "openai", "heuristic"}, f"Unknown provider {self.provider}"
        
        self.model_small = os.environ.get("AGENT_MODEL_SMALL", "heuristic")
        self.model_main = os.environ.get("AGENT_MODEL_MAIN", "heuristic")

        # Lazy-init clients
        self._gemini_client = None
        self._anthropic_client = None
        self._openai_client = None
        self._openai_compat_client = None

    def _get_gemini(self):
        if self._gemini_client is None:
            from google import genai
            key = os.environ.get("GEMINI_API_KEY", "")
            if not key:
                raise LLMError("GEMINI_API_KEY not set")
            self._gemini_client = genai.Client(api_key=key)
        return self._gemini_client

    def _get_anthropic(self):
        if self._anthropic_client is None:
            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not key:
                raise LLMError("ANTHROPIC_API_KEY not set")
            self._anthropic_client = anthropic.Anthropic(api_key=key)
        return self._anthropic_client

    def _get_openai(self):
        if self._openai_client is None:
            import openai
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                raise LLMError("OPENAI_API_KEY not set")
            self._openai_client = openai.OpenAI(api_key=key)
        return self._openai_client
        
    def _get_openai_compat(self):
        if self._openai_compat_client is None:
            import openai
            key = os.environ.get("OPENAI_API_KEY", "lm-studio")
            base_url = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
            self._openai_compat_client = openai.OpenAI(api_key=key, base_url=base_url)
        return self._openai_compat_client

    @staticmethod
    def _hash_request(provider: str, model: str, system: str, prompt: str, schema: dict) -> str:
        data = {
            "provider": provider,
            "model": model,
            "system": system,
            "prompt": prompt,
            "schema": schema,
        }
        raw = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _read_cache(self, req_hash: str, response_model: type[T]) -> T | None:
        cache_file = self.cache_dir / f"{req_hash}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                cached = json.load(f)
            return response_model.model_validate(cached["response"])
        return None

    def _write_cache(
        self,
        req_hash: str,
        model_name: str,
        validated: BaseModel,
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        base_url_host = "local"
        if self.provider == "openai_compat":
            base_url = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
            base_url_host = urlparse(base_url).netloc

        cache_file = self.cache_dir / f"{req_hash}.json"
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "provider": self.provider,
                    "model": model_name,
                    "base_url_host": base_url_host,
                    "mode": self.mode,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": latency_ms,
                    "prompt_hash": req_hash,
                    "response": validated.model_dump(),
                },
                f,
                indent=2,
            )

    def _strip_think(self, text: str) -> str:
        """Strip <think>...</think> blocks from output."""
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    def _call_openai_compat(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        client = self._get_openai_compat()
        schema_def = response_model.model_json_schema()
        
        current_prompt = prompt
        
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system + "\n/no_think"},
                        {"role": "user", "content": current_prompt},
                    ],
                    temperature=0,
                    max_tokens=600,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": response_model.__name__,
                            "strict": True,
                            "schema": schema_def
                        }
                    }
                )
                
                raw_text = response.choices[0].message.content or ""
                clean_text = self._strip_think(raw_text)
                
                in_tokens = response.usage.prompt_tokens if response.usage else 0
                out_tokens = response.usage.completion_tokens if response.usage else 0
                
                return response_model.model_validate_json(clean_text), in_tokens, out_tokens
                
            except ValidationError as e:
                if attempt == 1:
                    raise LLMError(f"Validation failed twice: {e}")
                current_prompt += f"\n\nValidation failed previously with: {e}. Please fix."
                continue
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "503" in err_str or "Quota" in err_str:
                    raise  # let the record script handle backoff
                raise LLMError(f"OpenAI compat call failed: {e}")
                
        raise LLMError("Exhausted retries in OpenAI compat provider")

    def _call_gemini(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        from google.genai import types
        client = self._get_gemini()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=response_model,
                    temperature=0,
                ),
            )
            if response.parsed:
                return response.parsed, 0, 0
            if response.text:
                return response_model.model_validate_json(response.text), 0, 0
            raise LLMError("Empty response from Gemini")
        except Exception as e:
            raise LLMError(f"Gemini call failed: {e}")

    def _call_anthropic(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        client = self._get_anthropic()
        schema = response_model.model_json_schema()
        tool_name = "extract_" + response_model.__name__.lower()
        tool = {
            "name": tool_name,
            "description": "Extract structured data",
            "input_schema": schema,
        }
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
            )
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if not tool_use:
                raise LLMError("Model did not return the requested tool call.")
            return response_model.model_validate(tool_use.input), response.usage.input_tokens, response.usage.output_tokens
        except Exception as e:
            raise LLMError(f"Anthropic call failed: {e}")

    def _call_openai(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        client = self._get_openai()
        try:
            completion = client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_model,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise LLMError("OpenAI returned no parsed output")
            return parsed, completion.usage.prompt_tokens, completion.usage.completion_tokens
        except Exception as e:
            raise LLMError(f"OpenAI call failed: {e}")

    def _call_heuristic(self, system: str, prompt: str, response_model: type[T]) -> tuple[T, int, int]:
        from src.agent.heuristic import heuristic_generate
        return heuristic_generate(system, prompt, response_model), 0, 0

    def generate_structured(
        self,
        system: str,
        prompt: str,
        response_model: type[T],
        model: str | None = None,
    ) -> T:
        """Generate structured output. Raises LLMError on any failure; never returns a default."""
        if self.provider == "heuristic":
            if self.mode == "record":
                raise LLMError("nothing to record")
            val, _, _ = self._call_heuristic(system, prompt, response_model)
            return val

        model_name = model or self.model_main
        schema = response_model.model_json_schema()
        req_hash = self._hash_request(self.provider, model_name, system, prompt, schema)

        if self.mode == "mock":
            for matcher, resp in self.mock_responses.items():
                if matcher in prompt or matcher in system:
                    val = response_model.model_validate(resp)
                    return val
            raise LLMError(f"No mock response found for prompt: {prompt[:100]}")

        cached = self._read_cache(req_hash, response_model)
        if cached is not None:
            return cached

        if self.mode == "replay":
            print(f"CACHE MISS INFO: hash={req_hash} provider={self.provider} model={model_name}")
            print(f"CACHE MISS SYSTEM:\n{system}")
            print(f"CACHE MISS PROMPT:\n{prompt}")
            print(f"CACHE MISS SCHEMA:\n{json.dumps(schema, sort_keys=True)}")
            raise CacheMiss(f"CacheMiss: {req_hash}")

        t0 = time.time()
        in_tok, out_tok = 0, 0
        if self.provider == "openai_compat":
            validated, in_tok, out_tok = self._call_openai_compat(model_name, system, prompt, response_model)
        elif self.provider == "gemini":
            validated, in_tok, out_tok = self._call_gemini(model_name, system, prompt, response_model)
        elif self.provider == "anthropic":
            validated, in_tok, out_tok = self._call_anthropic(model_name, system, prompt, response_model)
        elif self.provider == "openai":
            validated, in_tok, out_tok = self._call_openai(model_name, system, prompt, response_model)
        else:
            raise LLMError(f"Unknown provider: {self.provider}")
        latency_ms = (time.time() - t0) * 1000

        if self.mode in ("record", "live"):
            self._write_cache(req_hash, model_name, validated, latency_ms, in_tok, out_tok)

        return validated
