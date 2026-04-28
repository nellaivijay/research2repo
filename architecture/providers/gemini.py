"""
Google Gemini provider — leverages long-context and native vision.
"""

import json
import os
from typing import Optional

import google.generativeai as genai

from providers.base import (
    BaseProvider,
    GenerationConfig,
    GenerationResult,
    ModelCapability,
    ModelInfo,
)


class GeminiProvider(BaseProvider):
    """Google Gemini provider with File API and vision support."""

    MODELS = [
        ModelInfo(
            name="gemini-2.5-pro-preview-05-06",
            provider="gemini",
            max_context_tokens=1_048_576,
            max_output_tokens=65_536,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.FILE_UPLOAD,
                ModelCapability.STREAMING,
            ],
            cost_per_1k_input=0.00125,
            cost_per_1k_output=0.01,
        ),
        ModelInfo(
            name="gemini-2.0-flash",
            provider="gemini",
            max_context_tokens=1_048_576,
            max_output_tokens=8_192,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.FILE_UPLOAD,
                ModelCapability.STREAMING,
            ],
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0004,
        ),
        ModelInfo(
            name="gemini-1.5-pro",
            provider="gemini",
            max_context_tokens=2_097_152,
            max_output_tokens=8_192,
            capabilities=[
                ModelCapability.TEXT_GENERATION,
                ModelCapability.VISION,
                ModelCapability.LONG_CONTEXT,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODE_GENERATION,
                ModelCapability.FILE_UPLOAD,
                ModelCapability.STREAMING,
            ],
            cost_per_1k_input=0.00125,
            cost_per_1k_output=0.005,
        ),
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not set.")
        super().__init__(api_key=key, model_name=model_name)
        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(self.model_name)

    def default_model(self) -> str:
        return "gemini-2.5-pro-preview-05-06"

    def available_models(self) -> list[ModelInfo]:
        return self.MODELS

    def _build_config(self, config: Optional[GenerationConfig] = None) -> dict:
        cfg = config or GenerationConfig()
        gen_config = {
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "max_output_tokens": cfg.max_output_tokens,
        }
        if cfg.stop_sequences:
            gen_config["stop_sequences"] = cfg.stop_sequences
        if cfg.response_format == "json":
            gen_config["response_mime_type"] = "application/json"
        return gen_config

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        images: Optional[list[bytes]] = None,
    ) -> GenerationResult:
        parts = []
        if system_prompt:
            parts.append(f"System: {system_prompt}\n\n")
        if images:
            import PIL.Image
            import io
            for img_bytes in images:
                img = PIL.Image.open(io.BytesIO(img_bytes))
                parts.append(img)
        parts.append(prompt)

        gen_config = self._build_config(config)
        response = self._model.generate_content(parts, generation_config=gen_config)

        usage = getattr(response, "usage_metadata", None)
        return GenerationResult(
            text=response.text,
            model=self.model_name,
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            finish_reason=str(getattr(response.candidates[0], "finish_reason", "stop")),
            raw_response=response,
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
            f"You MUST respond with valid JSON conforming to this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
        )
        full_prompt = schema_instruction + prompt
        result = self.generate(full_prompt, system_prompt=system_prompt, config=cfg)
        return json.loads(result.text)

    def upload_file(self, file_path: str) -> object:
        """Upload a file via Gemini File API for long-context processing."""
        print(f"  [Gemini] Uploading {file_path} via File API...")
        uploaded = genai.upload_file(file_path)
        print(f"  [Gemini] Upload complete: {uploaded.name}")
        return uploaded

    def generate_with_file(
        self,
        uploaded_file: object,
        prompt: str,
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ) -> GenerationResult:
        """Generate using an uploaded file as context (zero-RAG long-context)."""
        parts = []
        if system_prompt:
            parts.append(f"System: {system_prompt}\n\n")
        parts.append(uploaded_file)
        parts.append(prompt)

        gen_config = self._build_config(config)
        response = self._model.generate_content(parts, generation_config=gen_config)

        usage = getattr(response, "usage_metadata", None)
        return GenerationResult(
            text=response.text,
            model=self.model_name,
            input_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            finish_reason=str(getattr(response.candidates[0], "finish_reason", "stop")),
            raw_response=response,
        )
