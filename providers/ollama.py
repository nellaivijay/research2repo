"""
Ollama provider — local/self-hosted models (Llama, CodeLlama, Mistral, DeepSeek, etc.).
"""

import json
import os
from typing import Optional

import requests

from providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResult,
    ModelCapability,
    ModelInfo,
)


class OllamaProvider(BaseProvider):
    """Ollama local model provider. Requires Ollama running at the configured host."""

    # Common models — actual availability depends on what's pulled locally.
    KNOWN_MODELS = [
        ModelInfo(
            name="deepseek-coder-v2:latest",
            provider="ollama",
            max_context_tokens=128_000,
            max_output_tokens=8_192,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
                ModelCapability.LONG_CONTEXT,
            ],
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
        ModelInfo(
            name="llama3.1:70b",
            provider="ollama",
            max_context_tokens=128_000,
            max_output_tokens=8_192,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.CODE_GENERATION,
            ],
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
        ModelInfo(
            name="codellama:34b",
            provider="ollama",
            max_context_tokens=16_384,
            max_output_tokens=4_096,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
            ],
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
        ModelInfo(
            name="llava:13b",
            provider="ollama",
            max_context_tokens=4_096,
            max_output_tokens=2_048,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
            ],
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
        ModelInfo(
            name="mistral:latest",
            provider="ollama",
            max_context_tokens=32_768,
            max_output_tokens=4_096,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.CODE_GENERATION,
            ],
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,  # unused, kept for interface consistency
        model_name: Optional[str] = None,
        host: Optional[str] = None,
    ):
        super().__init__(api_key=api_key, model_name=model_name)
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    def default_model(self) -> str:
        return "deepseek-coder-v2:latest"

    def available_models(self) -> list[ModelInfo]:
        # Merge known models with what's actually available locally
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            local_models = [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            local_models = []

        models = list(self.KNOWN_MODELS)
        known_names = {m.name for m in models}
        for name in local_models:
            if name not in known_names:
                models.append(ModelInfo(
                    name=name,
                    provider="ollama",
                    max_context_tokens=4_096,
                    max_output_tokens=2_048,
                    capabilities=[ModelCapability.TEXT_GENERATION],
                ))
        return models

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        images: Optional[list[bytes]] = None,
    ) -> GenerationResult:
        import base64

        cfg = config or GenerationConfig()
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "num_predict": cfg.max_output_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if images:
            payload["images"] = [base64.b64encode(img).decode() for img in images]
        if cfg.response_format == "json":
            payload["format"] = "json"

        response = requests.post(
            f"{self.host}/api/generate",
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
        data = response.json()

        return GenerationResult(
            text=data.get("response", ""),
            model=self.model_name,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            finish_reason="stop" if data.get("done") else "length",
            raw_response=data,
        )

    def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> dict:
        cfg = config or GenerationConfig()
        cfg.response_format = "json"
        schema_instruction = (
            f"Respond ONLY with valid JSON conforming to this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
        )
        full_prompt = schema_instruction + prompt
        result = self.generate(full_prompt, system_prompt=system_prompt, config=cfg)
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
