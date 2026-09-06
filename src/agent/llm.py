"""LLM adapter with multi-provider support.

Providers: gemini, anthropic, openai, heuristic.
Modes: live, replay, record, mock.
"""
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ValidationError

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
        self.cache_dir = Path("eval/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.provider = provider or os.environ.get("AGENT_LLM_PROVIDER", "heuristic")
        self.model_small = os.environ.get("AGENT_MODEL_SMALL", "heuristic")
        self.model_main = os.environ.get("AGENT_MODEL_MAIN", "heuristic")

        # Lazy-init clients only when needed
        self._gemini_client = None
        self._anthropic_client = None
        self._openai_client = None

    # ---- provider clients (lazy) ----

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

    # ---- cache ----

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
    ):
        cache_file = self.cache_dir / f"{req_hash}.json"
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "provider": self.provider,
                    "model": model_name,
                    "mode": self.mode,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_ms": latency_ms,
                    "prompt_hash": req_hash,
                    "response": validated.model_dump(),
                },
                f,
                indent=2,
            )

    # ---- provider call implementations ----

    def _call_gemini(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> T:
        from google.genai import types

        client = self._get_gemini()
        current_prompt = prompt

        for attempt in range(5):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=current_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=response_model,
                        temperature=0,
                    ),
                )
                if response.parsed:
                    return response.parsed
                if response.text:
                    return response_model.model_validate_json(response.text)
                raise LLMError("Empty response from Gemini")
            except ValidationError as e:
                if attempt > 0 and "Validation failed previously" in current_prompt:
                    raise LLMError(f"Validation failed twice: {e}")
                current_prompt += f"\n\nValidation failed previously with: {e}. Please fix."
                continue
            except LLMError:
                raise
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "503" in err_str or "Quota" in err_str:
                    if attempt == 4:
                        raise LLMError(f"Gemini call failed after 5 retries: {e}")
                    time.sleep(2**attempt)
                    continue
                raise LLMError(f"Gemini call failed: {e}")

        raise LLMError("Exhausted retries in Gemini provider")

    def _call_anthropic(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> T:
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
            return response_model.model_validate(tool_use.input)
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Anthropic call failed: {e}")

    def _call_openai(self, model_name: str, system: str, prompt: str, response_model: type[T]) -> T:
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
            return parsed
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"OpenAI call failed: {e}")

    def _call_heuristic(self, system: str, prompt: str, response_model: type[T]) -> T:
        from src.agent.heuristic import heuristic_generate
        return heuristic_generate(system, prompt, response_model)

    # ---- public API ----

    def generate_structured(
        self,
        system: str,
        prompt: str,
        response_model: type[T],
        model: str | None = None,
    ) -> T:
        """Generate structured output. Raises LLMError on any failure; never returns a default."""
        if self.provider == "heuristic":
            return self._call_heuristic(system, prompt, response_model)

        model_name = model or self.model_main
        schema = response_model.model_json_schema()
        req_hash = self._hash_request(self.provider, model_name, system, prompt, schema)

        # Mock mode
        if self.mode == "mock":
            for matcher, resp in self.mock_responses.items():
                if matcher in prompt or matcher in system:
                    return response_model.model_validate(resp)
            raise LLMError(f"No mock response found for prompt: {prompt[:100]}")

        # Check cache for replay/record/live
        cached = self._read_cache(req_hash, response_model)
        if cached is not None:
            return cached

        # replay mode: cache miss is fatal
        if self.mode == "replay":
            raise CacheMiss(f"CacheMiss: {req_hash}")

        # live or record: call provider
        t0 = time.time()
        if self.provider == "gemini":
            validated = self._call_gemini(model_name, system, prompt, response_model)
        elif self.provider == "anthropic":
            validated = self._call_anthropic(model_name, system, prompt, response_model)
        elif self.provider == "openai":
            validated = self._call_openai(model_name, system, prompt, response_model)
        else:
            raise LLMError(f"Unknown provider: {self.provider}")
        latency_ms = (time.time() - t0) * 1000

        # Save to cache
        if self.mode in ("record", "live"):
            self._write_cache(req_hash, model_name, validated, latency_ms)

        return validated
