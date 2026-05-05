"""
Unified LLM interface with robust error handling and async streaming.
"""
import os
import json
import httpx
from typing import List, Dict, Any, Type, AsyncGenerator
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMClient:
    """Unified interface for interacting with LLMs."""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        
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
        
        api_key = os.getenv("OPENAI_API_KEY") if self.provider == "openai" else os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise EnvironmentError(f"[LLMClient] {self.provider.upper()}_API_KEY is not configured. Set it in .env before running.")
            
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

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
        if self.provider == "openai":
            response = self.client.chat.completions.create(
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
            response = self.client.messages.create(
                model=self.model,
                messages=msgs,
                system=system_msg,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self._update_usage(response.usage.input_tokens, response.usage.output_tokens)
            return response.content[0].text

    async def stream_completion_async(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 4000) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient() as client:
            if self.provider == "openai":
                headers = {
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True
                }
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=data) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            content = line[6:]
                            if content == "[DONE]":
                                break
                            try:
                                chunk = json.loads(content)
                                if chunk["choices"][0]["delta"].get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                pass
            elif self.provider == "anthropic":
                system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
                msgs = [m for m in messages if m["role"] != "system"]
                headers = {
                    "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
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
                                if chunk.get("type") == "content_block_delta" and "delta" in chunk:
                                    yield chunk["delta"]["text"]
                            except json.JSONDecodeError:
                                pass

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
