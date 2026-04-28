"""
Synthetic data generation for Research2Repo pipeline testing
"""

import json
import random
from typing import Dict, List, Any
from datetime import datetime


class SyntheticPaperGenerator:
    """Generate synthetic research paper data for testing."""
    
    def __init__(self):
        """Initialize the synthetic paper generator."""
        self.paper_templates = {
            "ml": {
                "titles": [
                    "Attention Is All You Need",
                    "BERT: Pre-training of Deep Bidirectional Transformers",
                    "GPT-4: A Large Multimodal Model",
                    "Diffusion Models Beat GANs on Image Synthesis",
                    "LoRA: Low-Rank Adaptation of Large Language Models"
                ],
                "authors": [
                    ["Vaswani et al."],
                    ["Devlin et al."],
                    ["OpenAI Team"],
                    ["Ho et al."],
                    ["Hu et al."]
                ],
                "sections": [
                    "Introduction",
                    "Related Work",
                    "Method",
                    "Experiments",
                    "Results",
                    "Discussion",
                    "Conclusion",
                    "References"
                ],
                "equations": [
                    "Attention(Q,K,V) = softmax(QK^T / sqrt(d_k))V",
                    "Loss = -sum(y_i * log(y_hat_i))",
                    "f(x) = sigma(Wx + b)",
                    "y = Wx + b",
                    "L = 1/N * sum(L_i)"
                ],
                "hyperparameters": {
                    "learning_rate": [0.001, 0.0001, 0.01],
                    "batch_size": [32, 64, 128],
                    "epochs": [10, 50, 100],
                    "hidden_dim": [256, 512, 1024],
                    "dropout": [0.1, 0.2, 0.5]
                }
            },
            "nlp": {
                "titles": [
                    "Word2Vec: Distributed Representations of Words",
                    "GloVe: Global Vectors for Word Representation",
                    "Transformer: Attention Is All You Need",
                    "BERT: Pre-training of Deep Bidirectional Transformers",
                    "T5: Text-to-Text Transfer Transformer"
                ],
                "authors": [
                    ["Mikolov et al."],
                    ["Pennington et al."],
                    ["Vaswani et al."],
                    ["Devlin et al."],
                    ["Raffel et al."]
                ],
                "sections": [
                    "Introduction",
                    "Background",
                    "Model Architecture",
                    "Training",
                    "Evaluation",
                    "Analysis",
                    "Conclusion",
                    "References"
                ],
                "equations": [
                    "J(θ) = -1/m * sum(log P(w_o | w_c))",
                    "cos_sim(u, v) = u · v / (||u|| * ||v||)",
                    "softmax(x_i) = exp(x_i) / sum(exp(x_j))",
                    "attention = softmax(QK^T / sqrt(d_k))V"
                ],
                "hyperparameters": {
                    "embedding_dim": [100, 200, 300],
                    "window_size": [5, 10, 15],
                    "min_count": [5, 10, 20],
                    "negative_samples": [5, 10, 20]
                }
            },
            "cv": {
                "titles": [
                    "ResNet: Deep Residual Learning for Image Recognition",
                    "YOLO: Real-Time Object Detection",
                    "U-Net: Convolutional Networks for Biomedical Image Segmentation",
                    "Vision Transformer (ViT)",
                    "Stable Diffusion: High-Resolution Image Synthesis"
                ],
                "authors": [
                    ["He et al."],
                    ["Redmon et al."],
                    ["Ronneberger et al."],
                    ["Dosovitskiy et al."],
                    ["Rombach et al."]
                ],
                "sections": [
                    "Introduction",
                    "Related Work",
                    "Network Architecture",
                    "Experiments",
                    "Results",
                    "Ablation Studies",
                    "Conclusion",
                    "References"
                ],
                "equations": [
                    "y = F(x, {W_i}) + x",
                    "IoU = Area_of_Overlap / Area_of_Union",
                    "loss = MSE(y_pred, y_true)",
                    "F(x) = max(0, x)"
                ],
                "hyperparameters": {
                    "input_size": [224, 256, 512],
                    "num_layers": [18, 34, 50],
                    "learning_rate": [0.001, 0.01, 0.1],
                    "momentum": [0.9, 0.95, 0.99]
                }
            }
        }
    
    def generate_paper(self, domain: str = "ml", complexity: str = "medium") -> Dict[str, Any]:
        """
        Generate a synthetic research paper.
        
        Args:
            domain: Domain of the paper (ml, nlp, cv)
            complexity: Complexity level (simple, medium, complex)
            
        Returns:
            Dictionary containing synthetic paper data
        """
        if domain not in self.paper_templates:
            raise ValueError(f"Unknown domain: {domain}")
        
        template = self.paper_templates[domain]
        
        # Select random title and authors
        title = random.choice(template["titles"])
        authors = random.choice(template["authors"])
        
        # Generate sections based on complexity
        if complexity == "simple":
            sections = template["sections"][:4]
        elif complexity == "medium":
            sections = template["sections"][:6]
        else:  # complex
            sections = template["sections"]
        
        # Generate random number of equations
        num_equations = random.randint(3, 8) if complexity == "simple" else random.randint(5, 15)
        equations = random.sample(template["equations"], min(num_equations, len(template["equations"])))
        
        # Generate hyperparameters
        hyperparameters = {}
        for param, values in template["hyperparameters"].items():
            hyperparameters[param] = random.choice(values)
        
        # Generate abstract
        abstract = self._generate_abstract(title, domain)
        
        # Generate full text (simplified)
        full_text = self._generate_full_text(title, abstract, sections)
        
        return {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "sections": sections,
            "equations": equations,
            "hyperparameters": hyperparameters,
            "full_text": full_text,
            "domain": domain,
            "complexity": complexity,
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_abstract(self, title: str, domain: str) -> str:
        """Generate a synthetic abstract."""
        abstract_templates = [
            f"We present {title.lower()}, a novel approach for {domain} tasks.",
            f"This paper introduces {title.lower()}, addressing key challenges in {domain}.",
            f"We propose {title.lower()}, achieving state-of-the-art results on {domain} benchmarks."
        ]
        
        base = random.choice(abstract_templates)
        additions = [
            "Our method demonstrates significant improvements over existing approaches.",
            "Experimental results show the effectiveness of our proposed method.",
            "We validate our approach on multiple datasets and tasks.",
            "The proposed architecture achieves better performance with fewer parameters."
        ]
        
        return base + " " + random.choice(additions)
    
    def _generate_full_text(self, title: str, abstract: str, sections: List[str]) -> str:
        """Generate synthetic full text."""
        text = f"# {title}\n\n"
        text += f"{abstract}\n\n"
        
        for section in sections:
            text += f"## {section}\n\n"
            text += f"This section describes {section.lower()}.\n"
            text += "Detailed analysis and methodology are presented here.\n\n"
        
        return text
    
    def generate_batch(self, num_papers: int, domain: str = "ml") -> List[Dict[str, Any]]:
        """
        Generate a batch of synthetic papers.
        
        Args:
            num_papers: Number of papers to generate
            domain: Domain of the papers
            
        Returns:
            List of synthetic paper dictionaries
        """
        return [self.generate_paper(domain) for _ in range(num_papers)]


class SyntheticCodeGenerator:
    """Generate synthetic code for testing."""
    
    def __init__(self):
        """Initialize the synthetic code generator."""
        self.code_templates = {
            "model": {
                "python": """
import torch
import torch.nn as nn

class {model_name}(nn.Module):
    def __init__(self, {params}):
        super({model_name}, self).__init__()
        # Model implementation
        pass
    
    def forward(self, x):
        # Forward pass
        return x
""",
                "description": "Neural network model implementation"
            },
            "data": {
                "python": """
import torch
from torch.utils.data import Dataset, DataLoader

class {dataset_name}(Dataset):
    def __init__(self, data_path):
        self.data = self._load_data(data_path)
    
    def _load_data(self, path):
        # Load data
        pass
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]
""",
                "description": "Data loading and preprocessing"
            },
            "train": {
                "python": """
import torch
import torch.optim as optim

def train_model(model, train_loader, epochs={epochs}):
    optimizer = optim.Adam(model.parameters(), lr={lr})
    criterion = nn.CrossEntropyLoss()
    
    for epoch in range(epochs):
        for batch in train_loader:
            # Training loop
            pass
    
    return model
""",
                "description": "Training loop implementation"
            }
        }
    
    def generate_code(self, code_type: str, **kwargs) -> str:
        """
        Generate synthetic code.
        
        Args:
            code_type: Type of code (model, data, train)
            **kwargs: Additional parameters for code generation
            
        Returns:
            Generated code string
        """
        if code_type not in self.code_templates:
            raise ValueError(f"Unknown code type: {code_type}")
        
        template = self.code_templates[code_type]["python"]
        
        # Fill in template with provided parameters
        params = {
            "model_name": kwargs.get("model_name", "MyModel"),
            "dataset_name": kwargs.get("dataset_name", "MyDataset"),
            "epochs": kwargs.get("epochs", 10),
            "lr": kwargs.get("lr", 0.001),
            "params": kwargs.get("params", "input_dim, hidden_dim, output_dim")
        }
        
        return template.format(**params)
    
    def generate_repository_structure(self, paper_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a complete repository structure based on paper data.
        
        Args:
            paper_data: Paper data dictionary
            
        Returns:
            Dictionary mapping file paths to file contents
        """
        files = {}
        
        # Generate README
        files["README.md"] = self._generate_readme(paper_data)
        
        # Generate model code
        model_name = paper_data["title"].replace(" ", "").replace("-", "_")
        files[f"src/model.py"] = self.generate_code("model", model_name=model_name)
        
        # Generate data loading code
        files[f"src/data.py"] = self.generate_code("data", dataset_name=f"{model_name}Dataset")
        
        # Generate training code
        files[f"src/train.py"] = self.generate_code(
            "train",
            epochs=paper_data["hyperparameters"].get("epochs", 10),
            lr=paper_data["hyperparameters"].get("learning_rate", 0.001)
        )
        
        # Generate requirements.txt
        files["requirements.txt"] = self._generate_requirements(paper_data)
        
        # Generate config file
        files["config.yaml"] = self._generate_config(paper_data)
        
        return files
    
    def _generate_readme(self, paper_data: Dict[str, Any]) -> str:
        """Generate README content."""
        return f"""# {paper_data['title']}

Implementation of {paper_data['title']} by {', '.join(paper_data['authors'])}

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from src.model import {paper_data['title'].replace(' ', '').replace('-', '_')}
from src.train import train_model

# Load and train model
model = {paper_data['title'].replace(' ', '').replace('-', '_')}()
train_model(model, train_loader)
```

## Hyperparameters

{self._format_hyperparameters(paper_data['hyperparameters'])}

## Results

Implementation of the paper with state-of-the-art performance.

## License

MIT License
"""
    
    def _format_hyperparameters(self, hyperparameters: Dict[str, Any]) -> str:
        """Format hyperparameters for README."""
        lines = []
        for key, value in hyperparameters.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    def _generate_requirements(self, paper_data: Dict[str, Any]) -> str:
        """Generate requirements.txt content."""
        return """torch>=2.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
scikit-learn>=1.3.0
"""
    
    def _generate_config(self, paper_data: Dict[str, Any]) -> str:
        """Generate config.yaml content."""
        import yaml
        return yaml.dump(paper_data["hyperparameters"], default_flow_style=False)


if __name__ == "__main__":
    # Test synthetic data generation
    print("Generating synthetic papers...")
    
    paper_generator = SyntheticPaperGenerator()
    
    # Generate a single paper
    paper = paper_generator.generate_paper(domain="ml", complexity="medium")
    print(f"\nGenerated paper: {paper['title']}")
    print(f"Authors: {paper['authors']}")
    print(f"Sections: {paper['sections']}")
    print(f"Equations: {paper['equations']}")
    print(f"Hyperparameters: {paper['hyperparameters']}")
    
    # Generate code
    code_generator = SyntheticCodeGenerator()
    repo_structure = code_generator.generate_repository_structure(paper)
    print(f"\nGenerated repository structure with {len(repo_structure)} files")
    for file_path in repo_structure.keys():
        print(f"  - {file_path}")
    
    # Save to JSON for testing
    with open("synthetic_paper.json", "w") as f:
        json.dump(paper, f, indent=2)
    print("\nSaved synthetic paper to synthetic_paper.json")