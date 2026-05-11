"""
Unified LLM interface with robust error handling and async streaming.
"""
import os
import json
import httpx
from typing import List, Dict, Any, Type, AsyncGenerator, Optional
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMClient:
    """Unified interface for interacting with LLMs."""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self.client: Optional[Any] = None
        
        self.usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_estimate": 0.0
        }
        
        self.pricing = {
            "gpt-4o": [0.005, 0.015],
            "gpt-3.5-turbo": [0.0005, 0.0015],
            "claude-3-opus-20240229": [0.015, 0.075],
            "claude-3-sonnet-20240229": [0.003, 0.015],
            "claude-3-haiku-20240307": [0.00025, 0.00125],
            "claude-opus-4-7": [0.015, 0.075],
            "claude-opus-4-6": [0.015, 0.075],
            "claude-sonnet-4-6": [0.003, 0.015]
        }
        
        if self.provider not in {"openai", "anthropic"}:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _get_api_key(self) -> str:
        env_var = "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"
        api_key = os.getenv(env_var, "").strip()
        if not api_key or api_key.startswith("your_"):
            raise EnvironmentError(
                f"[LLMClient] {env_var} is not configured. Copy .env.example to .env "
                "and set a real key before running agent calls."
            )
        return api_key

    def _ensure_client(self) -> Any:
        """Create provider SDK clients lazily so imports/tests do not need real keys."""
        if self.client is not None:
            return self.client

        api_key = self._get_api_key()
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        return self.client

    def _update_usage(self, prompt_tokens: int, completion_tokens: int):
        self.usage["prompt_tokens"] += prompt_tokens
        self.usage["completion_tokens"] += completion_tokens
        rates = self.pricing.get(self.model)
        if not rates:
            import logging
            logging.warning(f"Unknown model pricing for {self.model}. Using default conservative rates.")
            rates = [0.01, 0.03]
        self.usage["cost_estimate"] += (prompt_tokens * rates[0] / 1000) + (completion_tokens * rates[1] / 1000)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 4000) -> str:
        client = self._ensure_client()
        if self.provider == "openai":
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self._update_usage(response.usage.prompt_tokens, response.usage.completion_tokens)
            return response.choices[0].message.content
        elif self.provider == "anthropic":
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            msgs = [m for m in messages if m["role"] != "system"]
            response = client.messages.create(
                model=self.model,
                messages=msgs,
                system=system_msg,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self._update_usage(response.usage.input_tokens, response.usage.output_tokens)
            return response.content[0].text

    async def stream_completion_async(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 4000) -> AsyncGenerator[str, None]:
        collected_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        api_key = self._get_api_key()

        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
            if self.provider == "openai":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True,
                    "stream_options": {"include_usage": True}
                }
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=data) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            content = line[6:]
                            if content == "[DONE]":
                                break
                            try:
                                chunk = json.loads(content)
                                # OpenAI includes usage in the final chunk when stream_options.include_usage is set
                                if chunk.get("usage"):
                                    prompt_tokens = chunk["usage"].get("prompt_tokens", 0)
                                    completion_tokens = chunk["usage"].get("completion_tokens", 0)
                                if chunk.get("choices") and chunk["choices"][0]["delta"].get("content"):
                                    delta = chunk["choices"][0]["delta"]["content"]
                                    collected_text += delta
                                    yield delta
                            except json.JSONDecodeError:
                                pass
            elif self.provider == "anthropic":
                system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
                msgs = [m for m in messages if m["role"] != "system"]
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                data = {
                    "model": self.model,
                    "system": system_msg,
                    "messages": msgs,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True
                }
                async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=data) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            content = line[6:]
                            try:
                                chunk = json.loads(content)
                                # Anthropic sends input token count in message_start
                                if chunk.get("type") == "message_start" and "message" in chunk:
                                    usage = chunk["message"].get("usage", {})
                                    prompt_tokens = usage.get("input_tokens", 0)
                                # Anthropic sends output token count in message_delta
                                elif chunk.get("type") == "message_delta" and "usage" in chunk:
                                    completion_tokens = chunk["usage"].get("output_tokens", 0)
                                elif chunk.get("type") == "content_block_delta" and "delta" in chunk:
                                    delta = chunk["delta"]["text"]
                                    collected_text += delta
                                    yield delta
                            except json.JSONDecodeError:
                                pass

        # ── Token accounting (was previously missing for streaming) ────────
        if prompt_tokens == 0 and completion_tokens == 0:
            # Fallback: estimate from text lengths if API didn't provide usage
            prompt_text = " ".join(m.get("content", "") for m in messages)
            prompt_tokens = len(prompt_text) // 4
            completion_tokens = len(collected_text) // 4
        self._update_usage(prompt_tokens, completion_tokens)

    def structured_output(self, messages: List[Dict[str, str]], schema: Type[BaseModel]) -> BaseModel:
        schema_json = json.dumps(schema.model_json_schema())
        instruction = f"\n\nYou MUST return a raw JSON object that conforms exactly to this JSON schema. Do not include markdown formatting.\nSchema:\n{schema_json}"
        
        msgs = list(messages)
        if msgs and msgs[0]["role"] == "system":
            msgs[0]["content"] += instruction
        else:
            msgs.append({"role": "system", "content": instruction})

        for attempt in range(2):
            raw_output = self.chat_completion(msgs, temperature=0.1, max_tokens=4000)
            clean_output = raw_output.strip()
            if clean_output.startswith("```json"):
                clean_output = clean_output[7:]
            if clean_output.startswith("```"):
                clean_output = clean_output[3:]
            if clean_output.endswith("```"):
                clean_output = clean_output[:-3]
            clean_output = clean_output.strip()

            try:
                data = json.loads(clean_output)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == 0:
                    error_msg = f"Failed to parse or validate JSON. Error: {str(e)}\nPlease return a valid JSON object matching the schema without markdown."
                    msgs.append({"role": "assistant", "content": raw_output})
                    msgs.append({"role": "user", "content": error_msg})
                else:
                    raise Exception(f"Failed structured output validation after 2 attempts: {str(e)}")
