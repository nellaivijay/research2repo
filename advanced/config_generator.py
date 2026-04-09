"""
ConfigGenerator — Extracts ALL hyperparameters from the paper analysis
and generates a structured YAML config file with proper organization,
types, and documentation comments.
"""

import os
from typing import Optional

import yaml

from providers.base import BaseProvider, GenerationConfig, ModelCapability
from providers import get_provider
from core.analyzer import PaperAnalysis


class ConfigGenerator:
    """
    Generates a comprehensive config.yaml from paper hyperparameters.

    Groups hyperparameters into logical sections:
      - model: architecture params (d_model, num_heads, etc.)
      - training: optimization params (lr, batch_size, epochs, etc.)
      - data: dataset params (max_seq_len, vocab_size, etc.)
      - regularization: dropout, weight_decay, label_smoothing
      - infrastructure: device, seed, logging, checkpointing
    """

    def __init__(self, provider: Optional[BaseProvider] = None):
        self.provider = provider or get_provider()

    def generate(self, analysis: PaperAnalysis) -> str:
        """
        Generate a structured YAML config from paper analysis.

        Returns:
            YAML string content for config.yaml.
        """
        print("  [ConfigGenerator] Generating config.yaml...")

        # Use LLM to organize hyperparameters into structured sections
        prompt = self._build_prompt(analysis)

        result = self.provider.generate(
            prompt=prompt,
            system_prompt=(
                "You are an ML config expert. Generate a well-organized YAML config file. "
                "Output ONLY valid YAML content with comments. No markdown fences."
            ),
            config=GenerationConfig(temperature=0.1, max_output_tokens=4096),
        )

        yaml_content = result.text.strip()
        if yaml_content.startswith("```"):
            yaml_content = yaml_content.split("\n", 1)[1] if "\n" in yaml_content else yaml_content[3:]
        if yaml_content.endswith("```"):
            yaml_content = yaml_content[:-3].rstrip()

        # Validate YAML
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            print("  [ConfigGenerator] Warning: LLM output is not valid YAML, using fallback.")
            yaml_content = self._fallback_config(analysis)

        return yaml_content

    def generate_schema(self, analysis: PaperAnalysis) -> dict:
        """Generate a JSON schema for the config file."""
        schema = {
            "type": "object",
            "properties": {
                "model": {
                    "type": "object",
                    "description": "Model architecture parameters",
                    "properties": {},
                },
                "training": {
                    "type": "object",
                    "description": "Training hyperparameters",
                    "properties": {},
                },
                "data": {
                    "type": "object",
                    "description": "Data processing parameters",
                    "properties": {},
                },
                "regularization": {
                    "type": "object",
                    "description": "Regularization parameters",
                    "properties": {},
                },
            },
        }

        # Categorize hyperparameters
        model_keys = {"d_model", "d_ff", "d_k", "d_v", "num_heads", "num_layers",
                       "vocab_size", "max_seq_len", "hidden_size", "num_encoder_layers",
                       "num_decoder_layers", "intermediate_size"}
        train_keys = {"learning_rate", "lr", "batch_size", "epochs", "warmup_steps",
                       "warmup_ratio", "max_steps", "gradient_clip", "weight_decay",
                       "adam_beta1", "adam_beta2", "adam_epsilon"}
        reg_keys = {"dropout", "attention_dropout", "label_smoothing",
                     "weight_decay", "gradient_clip_norm"}

        for key, value in analysis.hyperparameters.items():
            key_lower = key.lower().replace(" ", "_")
            prop = {"type": "string", "default": value, "description": f"From paper: {key}={value}"}

            if any(k in key_lower for k in model_keys):
                schema["properties"]["model"]["properties"][key_lower] = prop
            elif any(k in key_lower for k in train_keys):
                schema["properties"]["training"]["properties"][key_lower] = prop
            elif any(k in key_lower for k in reg_keys):
                schema["properties"]["regularization"]["properties"][key_lower] = prop
            else:
                schema["properties"]["model"]["properties"][key_lower] = prop

        return schema

    def _build_prompt(self, analysis: PaperAnalysis) -> str:
        parts = [
            f"Generate a comprehensive YAML config file for the paper: {analysis.title}\n",
            "## ALL Hyperparameters from the paper:",
        ]
        for k, v in analysis.hyperparameters.items():
            parts.append(f"  - {k}: {v}")

        if analysis.equations:
            parts.append("\n## Key equations (for understanding parameter roles):")
            for eq in analysis.equations[:10]:
                parts.append(f"  - {eq}")

        parts.append("""
## YAML Structure Required:
# Paper: {title}
# {description}

model:
  # Architecture parameters
  ...

training:
  # Optimization parameters
  ...

data:
  # Data loading parameters
  ...

regularization:
  # Regularization parameters
  ...

infrastructure:
  seed: 42
  device: "cuda"
  num_workers: 4
  log_interval: 100
  checkpoint_dir: "./checkpoints"
  use_wandb: false
  use_tensorboard: true

Include YAML comments explaining each parameter and referencing the paper section.
Use appropriate types (int, float, string, list).
Output ONLY valid YAML. No markdown fences.""")

        return "\n".join(parts)

    def _fallback_config(self, analysis: PaperAnalysis) -> str:
        """Generate a basic YAML config when LLM output is invalid."""
        config = {
            "model": {},
            "training": {},
            "data": {"max_seq_len": 512},
            "regularization": {},
            "infrastructure": {
                "seed": 42,
                "device": "cuda",
                "num_workers": 4,
                "log_interval": 100,
                "checkpoint_dir": "./checkpoints",
            },
        }

        for key, value in analysis.hyperparameters.items():
            key_clean = key.lower().replace(" ", "_").replace("-", "_")
            # Try to parse numeric values
            try:
                parsed = float(value.split()[0]) if value else value
                if parsed == int(parsed):
                    parsed = int(parsed)
            except (ValueError, AttributeError):
                parsed = value

            if any(k in key_clean for k in ("lr", "learning", "batch", "epoch", "warmup", "step", "grad")):
                config["training"][key_clean] = parsed
            elif any(k in key_clean for k in ("dropout", "decay", "smooth", "clip")):
                config["regularization"][key_clean] = parsed
            else:
                config["model"][key_clean] = parsed

        header = f"# Config for: {analysis.title}\n# Auto-generated by Research2Repo\n\n"
        return header + yaml.dump(config, default_flow_style=False, sort_keys=False)
