"""
Gradio web interface for Research2Repo
Based on OmniShotCut's Gradio demo approach
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

# Add project root to path
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

try:
    import gradio as gr
    from providers import get_provider, ProviderRegistry
    from providers.base import ModelCapability
except ImportError:
    print("Gradio or required dependencies not installed")
    print("Install with: pip install gradio")
    sys.exit(1)

# Constants
BASE_TMP_DIR = os.path.abspath("./gradio_tmp")
os.makedirs(BASE_TMP_DIR, exist_ok=True)
os.environ["TMPDIR"] = BASE_TMP_DIR
os.environ["TEMP"] = BASE_TMP_DIR
os.environ["GRADIO_TEMP_DIR"] = BASE_TMP_DIR

# Global state
PIPELINE_STATE = {
    "current_stage": "",
    "progress": 0,
    "logs": [],
    "generated_files": {},
    "metadata": {}
}

def list_available_providers() -> Dict[str, List[str]]:
    """List available providers and their models."""
    try:
        available = ProviderRegistry.detect_available()
        provider_models = {}
        
        for provider_name in available:
            try:
                provider = ProviderRegistry.create(provider_name)
                models = [model.name for model in provider.available_models()]
                provider_models[provider_name] = models
            except Exception as e:
                provider_models[provider_name] = [f"Error: {str(e)}"]
        
        return provider_models
    except Exception as e:
        return {"error": [str(e)]}

def download_paper(url: str, progress: gr.Progress = gr.Progress()) -> str:
    """Download a research paper from URL."""
    try:
        import requests
        
        progress(0.1, desc="Downloading paper...")
        
        headers = {
            "User-Agent": "Research2Repo/3.0 (Academic Tool; +https://github.com/nellaivijay/Research2Repo)"
        }
        response = requests.get(url, stream=True, timeout=120, headers=headers)
        response.raise_for_status()
        
        # Save to temp file
        temp_path = os.path.join(BASE_TMP_DIR, "paper.pdf")
        total_size = 0
        max_bytes = 100 * 1024 * 1024  # 100MB limit
        
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                total_size += len(chunk)
                if total_size > max_bytes:
                    raise ValueError(f"PDF exceeds 100MB limit.")
                f.write(chunk)
        
        progress(1.0, desc="Paper downloaded successfully")
        
        size_mb = total_size / (1024 * 1024)
        return f"✅ Paper downloaded: {size_mb:.1f} MB\nSaved to: {temp_path}"
        
    except Exception as e:
        return f"❌ Error downloading paper: {str(e)}"

def analyze_paper(
    pdf_path: str,
    provider_name: str,
    model_name: str,
    progress: gr.Progress = gr.Progress()
) -> str:
    """Analyze a research paper."""
    try:
        progress(0.1, desc="Initializing provider...")
        
        # Get provider
        provider = get_provider(provider_name=provider_name, model_name=model_name)
        
        progress(0.3, desc="Loading paper...")
        
        # Simulate analysis (in real implementation, this would call the actual analyzer)
        # For demo purposes, we'll simulate the analysis process
        
        progress(0.5, desc="Extracting diagrams...")
        time.sleep(1)
        
        progress(0.7, desc="Analyzing content...")
        time.sleep(1)
        
        progress(0.9, desc="Processing equations...")
        time.sleep(1)
        
        progress(1.0, desc="Analysis complete")
        
        # Simulated analysis result
        result = f"""
**Paper Analysis Complete**

**Provider**: {provider_name}
**Model**: {model_name}
**Paper Path**: {pdf_path}

**Analysis Results**:
- Title: Simulated Paper Title
- Authors: Author 1, Author 2, Author 3
- Sections: 8
- Equations: 15
- Hyperparameters: 12
- Diagrams: 3

**Next Steps**:
1. Review the analysis above
2. Configure pipeline parameters
3. Run the full pipeline to generate code

*Note: This is a demo. In production, this would call the actual PaperAnalyzer.*
"""
        return result
        
    except Exception as e:
        return f"❌ Error analyzing paper: {str(e)}"

def run_pipeline(
    pdf_path: str,
    provider_name: str,
    model_name: str,
    mode: str,
    enable_refine: bool,
    enable_execution: bool,
    enable_tests: bool,
    enable_devops: bool,
    progress: gr.Progress = gr.Progress()
) -> str:
    """Run the Research2Repo pipeline."""
    try:
        global PIPELINE_STATE
        
        # Reset state
        PIPELINE_STATE = {
            "current_stage": "",
            "progress": 0,
            "logs": [],
            "generated_files": {},
            "metadata": {}
        }
        
        stages = []
        if mode == "classic":
            stages = [
                "Download PDF",
                "Analyze Paper",
                "Extract Equations",
                "Design Architecture",
                "Generate Config",
                "Synthesize Code",
                "Generate Tests",
                "Validate Code",
                "Auto-Fix Issues",
                "Save Repository"
            ]
        else:  # agent mode
            stages = [
                "Parse Paper",
                "Decomposed Planning",
                "Per-File Analysis",
                "Document Segmentation",
                "Self-Refine Loop",
                "CodeRAG Mining",
                "Context-Managed Coding",
                "Validation",
                "Execution Sandbox",
                "Auto-Debugging",
                "DevOps Generation",
                "Reference Evaluation"
            ]
        
        total_stages = len(stages)
        
        for i, stage in enumerate(stages):
            PIPELINE_STATE["current_stage"] = stage
            PIPELINE_STATE["progress"] = (i + 1) / total_stages * 100
            PIPELINE_STATE["logs"].append(f"[{i+1}/{total_stages}] {stage}")
            
            progress((i + 1) / total_stages, desc=f"Stage {i+1}/{total_stages}: {stage}")
            
            # Simulate stage execution
            time.sleep(0.5)
        
        # Generate simulated results
        result = f"""
**Pipeline Execution Complete**

**Configuration**:
- Mode: {mode}
- Provider: {provider_name}
- Model: {model_name}
- Self-Refine: {enable_refine}
- Execution: {enable_execution}
- Tests: {enable_tests}
- DevOps: {enable_devops}

**Pipeline Stages Completed**: {len(stages)}

**Generated Repository Structure**:
```
generated_repo/
├── README.md
├── requirements.txt
├── setup.py
├── config.yaml
├── src/
│   ├── __init__.py
│   ├── model.py
│   ├── data.py
│   └── train.py
├── tests/
│   ├── test_model.py
│   └── test_data.py
└── examples/
    └── basic_usage.py
```

**Files Generated**: 12
**Lines of Code**: ~1,500
**Test Coverage**: 85%

**Validation Score**: 92/100
- Equation Coverage: 95%
- Hyperparam Coverage: 88%
- Critical Issues: 0
- Warnings: 2

*Note: This is a demo. In production, this would execute the actual pipeline.*
"""
        return result
        
    except Exception as e:
        return f"❌ Error running pipeline: {str(e)}"

def estimate_cost(
    provider_name: str,
    model_name: str,
    mode: str,
    paper_length: str
) -> str:
    """Estimate cost for pipeline execution."""
    try:
        # Simulated cost estimation
        base_costs = {
            "gemini": {"gpt-4": 0.01, "gpt-3.5": 0.002},
            "openai": {"gpt-4": 0.03, "gpt-3.5": 0.002},
            "anthropic": {"claude-opus": 0.015, "claude-sonnet": 0.003}
        }
        
        mode_multiplier = {
            "classic": 1.0,
            "agent": 2.5
        }
        
        paper_multiplier = {
            "short": 0.5,
            "medium": 1.0,
            "long": 2.0
        }
        
        provider = provider_name.lower()
        model = model_name.lower()
        
        # Get base cost
        base_cost = base_costs.get(provider, {}).get(model, 0.01)
        
        # Apply multipliers
        total_cost = base_cost * mode_multiplier.get(mode, 1.0) * paper_multiplier.get(paper_length, 1.0)
        
        return f"""
**Cost Estimation**

**Configuration**:
- Provider: {provider_name}
- Model: {model_name}
- Mode: {mode}
- Paper Length: {paper_length}

**Estimated Cost**: ${total_cost:.4f}

**Cost Breakdown**:
- Paper Analysis: ${total_cost * 0.2:.4f}
- Architecture Design: ${total_cost * 0.15:.4f}
- Code Generation: ${total_cost * 0.4:.4f}
- Validation: ${total_cost * 0.15:.4f}
- Testing: ${total_cost * 0.1:.4f}

*Note: Actual costs may vary based on paper complexity and provider pricing.*
"""
        
    except Exception as e:
        return f"❌ Error estimating cost: {str(e)}"

def compare_providers(
    task: str,
    providers: str
) -> str:
    """Compare different providers for a specific task."""
    try:
        provider_list = [p.strip() for p in providers.split(",")]
        
        # Simulated comparison
        comparison = f"""
**Provider Comparison for: {task}**

"""
        for provider in provider_list:
            # Simulated metrics
            cost = 0.01 if "gemini" in provider.lower() else 0.02
            speed = "Fast" if "gemini" in provider.lower() or "gpt-3.5" in provider.lower() else "Medium"
            accuracy = 92 if "gpt-4" in provider.lower() or "claude-opus" in provider.lower() else 85
            
            comparison += f"""
**{provider}**
- Cost: ${cost:.4f}
- Speed: {speed}
- Accuracy: {accuracy}%
- Recommended: {"✅ Yes" if accuracy >= 90 else "⚠️ Maybe"}
"""
        
        return comparison
        
    except Exception as e:
        return f"❌ Error comparing providers: {str(e)}"

# Custom CSS (inspired by OmniShotCut)
custom_css = """
#main-container {
    max-width: 1400px !important;
}

.result-box {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
    background-color: #f9fafb;
    margin: 8px 0;
}

.result-box pre {
    white-space: pre-wrap;
    word-wrap: break-word;
}

.markdown-text {
    line-height: 1.6;
}

.gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.stage-indicator {
    padding: 8px 16px;
    border-radius: 4px;
    background-color: #e0e7ff;
    color: #3730a3;
    font-weight: 600;
}
"""

def create_demo():
    """Create the Gradio demo interface."""
    
    # Get available providers
    providers_info = list_available_providers()
    
    with gr.Blocks(
        title="Research2Repo - Interactive Demo",
        css=custom_css,
        theme=gr.themes.Soft()
    ) as demo:
        
        gr.Markdown("""
# Research2Repo - Interactive Demo

**Educational agentic framework for converting research papers into implementation repositories**

This interactive demo allows you to:
- Upload research papers and analyze them
- Run the full paper-to-code conversion pipeline
- Compare different AI providers and models
- Estimate costs before execution
- Visualize pipeline progress and results

**Supported Providers**: Google Gemini, OpenAI GPT-4o, Anthropic Claude, Ollama (local)
        """)
        
        with gr.Tabs():
            # Tab 1: Paper Upload and Analysis
            with gr.Tab("📄 Paper Analysis"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Upload Paper")
                        
                        paper_input = gr.Textbox(
                            label="Paper URL (arXiv, OpenReview, etc.)",
                            placeholder="https://arxiv.org/pdf/1706.03762.pdf",
                            value="https://arxiv.org/pdf/1706.03762.pdf"
                        )
                        
                        provider_dropdown = gr.Dropdown(
                            label="Provider",
                            choices=list(providers_info.keys()),
                            value="gemini" if "gemini" in providers_info else list(providers_info.keys())[0] if providers_info else "openai"
                        )
                        
                        model_dropdown = gr.Dropdown(
                            label="Model",
                            choices=providers_info.get("gemini", ["gemini-1.5-pro"]) if "gemini" in providers_info else ["gpt-4"],
                            value=providers_info.get("gemini", ["gemini-1.5-pro"])[0] if "gemini" in providers_info else "gpt-4"
                        )
                        
                        download_button = gr.Button("Download Paper", variant="secondary")
                        analyze_button = gr.Button("Analyze Paper", variant="primary")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Analysis Result")
                        analysis_output = gr.Markdown(label="Result")
            
            # Tab 2: Pipeline Execution
            with gr.Tab("🚀 Pipeline Execution"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Pipeline Configuration")
                        
                        pipeline_mode = gr.Radio(
                            label="Pipeline Mode",
                            choices=["classic", "agent"],
                            value="agent"
                        )
                        
                        with gr.Row():
                            refine_checkbox = gr.Checkbox(label="Enable Self-Refine", value=True)
                            execution_checkbox = gr.Checkbox(label="Enable Execution", value=False)
                        
                        with gr.Row():
                            tests_checkbox = gr.Checkbox(label="Enable Tests", value=True)
                            devops_checkbox = gr.Checkbox(label="Enable DevOps", value=True)
                        
                        pipeline_button = gr.Button("Run Pipeline", variant="primary", size="lg")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Pipeline Result")
                        pipeline_output = gr.Markdown(label="Result")
                        
                        progress_bar = gr.Progress()
            
            # Tab 3: Cost Estimation
            with gr.Tab("💰 Cost Estimation"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Cost Configuration")
                        
                        cost_provider = gr.Dropdown(
                            label="Provider",
                            choices=list(providers_info.keys()),
                            value="gemini" if "gemini" in providers_info else list(providers_info.keys())[0] if providers_info else "openai"
                        )
                        
                        cost_model = gr.Dropdown(
                            label="Model",
                            choices=providers_info.get("gemini", ["gemini-1.5-pro"]) if "gemini" in providers_info else ["gpt-4"],
                            value=providers_info.get("gemini", ["gemini-1.5-pro"])[0] if "gemini" in providers_info else "gpt-4"
                        )
                        
                        cost_mode = gr.Radio(
                            label="Pipeline Mode",
                            choices=["classic", "agent"],
                            value="agent"
                        )
                        
                        paper_length = gr.Radio(
                            label="Paper Length",
                            choices=["short", "medium", "long"],
                            value="medium"
                        )
                        
                        estimate_button = gr.Button("Estimate Cost", variant="secondary")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Cost Breakdown")
                        cost_output = gr.Markdown(label="Cost Result")
            
            # Tab 4: Provider Comparison
            with gr.Tab("🔄 Provider Comparison"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Comparison Setup")
                        
                        comparison_task = gr.Dropdown(
                            label="Task",
                            choices=["Paper Analysis", "Code Generation", "Validation", "Full Pipeline"],
                            value="Full Pipeline"
                        )
                        
                        providers_text = gr.Textbox(
                            label="Providers to Compare (comma-separated)",
                            value="gemini, openai, anthropic",
                            placeholder="gemini, openai, anthropic"
                        )
                        
                        compare_button = gr.Button("Compare Providers", variant="secondary")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Comparison Result")
                        comparison_output = gr.Markdown(label="Comparison Result")
        
        # Event handlers
        download_button.click(
            fn=download_paper,
            inputs=[paper_input],
            outputs=[analysis_output]
        )
        
        analyze_button.click(
            fn=analyze_paper,
            inputs=[paper_input, provider_dropdown, model_dropdown],
            outputs=[analysis_output]
        )
        
        pipeline_button.click(
            fn=run_pipeline,
            inputs=[paper_input, provider_dropdown, model_dropdown, pipeline_mode, 
                   refine_checkbox, execution_checkbox, tests_checkbox, devops_checkbox],
            outputs=[pipeline_output]
        )
        
        estimate_button.click(
            fn=estimate_cost,
            inputs=[cost_provider, cost_model, cost_mode, paper_length],
            outputs=[cost_output]
        )
        
        compare_button.click(
            fn=compare_providers,
            inputs=[comparison_task, providers_text],
            outputs=[comparison_output]
        )
    
    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(share=True)