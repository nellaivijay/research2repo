"""
Anthropic Claude provider — Claude 3.5/4 Sonnet/Opus with vision and extended thinking.
"""

import base64
import json
import os
from typing import Optional

from providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResult,
    ModelCapability,
    ModelInfo,
)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider with vision and structured output."""

    MODELS = [
        ModelInfo(
            name="claude-sonnet-4-20250514",
            provider="anthropic",
            max_context_tokens=200_000,
            max_output_tokens=64_000,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STREAMING,
            ],
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
        ModelInfo(
            name="claude-opus-4-20250514",
            provider="anthropic",
            max_context_tokens=200_000,
            max_output_tokens=32_000,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STREAMING,
            ],
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
        ),
        ModelInfo(
            name="claude-3-5-sonnet-20241022",
            provider="anthropic",
            max_context_tokens=200_000,
            max_output_tokens=8_192,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.STREAMING,
            ],
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set.")
        super().__init__(api_key=key, model_name=model_name)

        import anthropic
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    def available_models(self) -> list[ModelInfo]:
        return self.MODELS

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        images: Optional[list[bytes]] = None,
    ) -> GenerationResult:
        cfg = config or GenerationConfig()
        content = []

        if images and self.supports(ModelCapability.VISION):
            for img_bytes in images:
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                })
        content.append({"type": "text", "text": prompt})

        kwargs = {
            "model": self.model_name,
            "max_tokens": cfg.max_output_tokens,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "messages": [{"role": "user", "content": content}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if cfg.stop_sequences:
            kwargs["stop_sequences"] = cfg.stop_sequences

        response = self._client.messages.create(**kwargs)

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        return GenerationResult(
            text=text,
            model=self.model_name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "stop",
            raw_response=response,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        schema_instruction = (
            f"Respond ONLY with valid JSON (no markdown, no explanation) "
            f"conforming to this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
        )
        full_prompt = schema_instruction + prompt
        sys_prompt = system_prompt or "You are a structured data extraction assistant. Respond only with valid JSON."
        result = self.generate(full_prompt, system_prompt=sys_prompt, config=config)
        # Strip markdown fences if present
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
