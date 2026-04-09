# Prompt Engineering Guide

This guide documents every prompt used in the Research2Repo pipeline, explains the design patterns behind them, and provides practical advice for customization.

---

## Table of Contents

1. [Prompt Architecture](#prompt-architecture)
2. [Prompt Categories](#prompt-categories)
   - [Analysis Prompts](#analysis-prompts-3)
   - [Planning Prompts](#planning-prompts-3)
   - [Generation Prompts](#generation-prompts-3)
   - [Validation Prompts](#validation-prompts-3)
   - [Specialized Prompts](#specialized-prompts-2)
   - [Evaluation Prompts](#evaluation-prompts-1)
3. [Prompt Design Patterns](#prompt-design-patterns)
4. [Template Variables Reference](#template-variables-reference)
5. [Prompt-to-Module Mapping Table](#prompt-to-module-mapping-table)
6. [Customizing Prompts](#customizing-prompts)
7. [Tips for Better Results](#tips-for-better-results)

---

## Prompt Architecture

### File Organization

All prompts live in the `prompts/` directory at the project root as plain `.txt` files:

```
prompts/
  analyzer.txt              (29 lines)
  architect.txt             (47 lines)
  architecture_design.txt   (56 lines)
  auto_debug.txt            (40 lines)
  coder.txt                 (36 lines)
  devops.txt                (22 lines)
  diagram_extractor.txt     (30 lines)
  equation_extractor.txt    (31 lines)
  file_analysis.txt         (44 lines)
  logic_design.txt          (36 lines)
  overall_plan.txt          (19 lines)
  reference_eval.txt        (39 lines)
  self_refine_refine.txt    (30 lines)
  self_refine_verify.txt    (47 lines)
  test_generator.txt        (38 lines)
  validator.txt             (52 lines)
```

Total: **16 prompt files**, 555 lines combined.

Note: `architect.txt` is used only in Classic mode. The three planning prompts (`overall_plan.txt`, `architecture_design.txt`, `logic_design.txt`) are used only in Agent mode.

### Loading Mechanism

Every module that uses prompts follows the same loading pattern via a `_load_prompt()` helper:

```python
def _load_prompt(self, path: str, **kwargs) -> str:
    if os.path.exists(path):
        with open(path) as f:
            template = f.read()
        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        return template
    return ""
```

Key behaviors:

1. **Path resolution:** Prompt file paths are computed at class level using `os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "filename.txt")`. This ensures prompts are found regardless of the working directory.

2. **Template variable substitution:** Uses `{{placeholder}}` syntax (double curly braces). When `_load_prompt()` is called with keyword arguments, each `{{key}}` in the template is replaced with the corresponding value. Most prompts do NOT use template variables -- they are system-level instructions. Template variables are primarily used by `devops.txt`, `auto_debug.txt`, `self_refine_verify.txt`, `self_refine_refine.txt`, and `reference_eval.txt`.

3. **Fallback mechanism:** If the prompt file does not exist, `_load_prompt()` returns an empty string. Each module then checks for this and calls a `_default_prompt()` (or similar) method that returns a hardcoded inline string. This makes the system resilient to missing prompt files but means that removing a prompt file silently falls back to a less-optimized default.

### Prompt vs System Prompt

Most prompts in Research2Repo serve as the **user prompt** (the main instruction). Each module also defines a **system prompt** inline in the code, typically a short role assignment:

```python
system_prompt="You are an expert ML researcher. Analyze this paper thoroughly."
```

The user prompt contains the detailed instructions, the paper context, and the output format specification. The system prompt sets the role and high-level behavior.

---

## Prompt Categories

### Analysis Prompts (3)

These prompts handle paper ingestion and information extraction.

#### `analyzer.txt` (29 lines)

**Used by:** `PaperAnalyzer.analyze()` in `core/analyzer.py`

**Purpose:** Analyze a research paper and extract structured information into a JSON object with 13 fields.

**Structure:**
- Opens with role assignment: "You are an expert ML researcher performing a thorough analysis of a research paper."
- Lists 10 extraction targets with specific format instructions for each (LaTeX strings for equations, dict for hyperparameters, etc.)
- Includes format examples for equations and hyperparameters
- Ends with an exhaustiveness directive and output format constraint

**Key excerpt:**
```
5. "equations": A list of ALL mathematical equations in LaTeX format. Include:
   - Loss functions
   - Forward pass computations
   - Attention formulas
   - Normalization equations
   - Any equation numbered in the paper
```

**Output format:** Raw JSON object (no markdown fences).

---

#### `diagram_extractor.txt` (30 lines)

**Used by:** `PaperAnalyzer.extract_diagrams_to_mermaid()` in `core/analyzer.py`

**Purpose:** Convert architecture diagrams from PDF page images into Mermaid.js code.

**Structure:**
- Instructions for identifying diagram types (architecture, pipeline, data flow, attention)
- Mermaid formatting guidelines (`graph TD` for top-down, `graph LR` for left-to-right)
- A complete example Mermaid diagram showing an encoder block
- Separation instructions (use `---` between diagrams)
- Sentinel value: respond with `NO_DIAGRAMS` if none found

**Paired system prompt:** "You are an expert at reading ML paper diagrams and converting them to Mermaid.js."

**Input:** Page images (sent as vision content alongside the text prompt).

---

#### `equation_extractor.txt` (31 lines)

**Used by:** `EquationExtractor.extract_from_text()` and `extract_from_images()` in `advanced/equation_extractor.py`

**Purpose:** Extract ALL mathematical equations with full metadata.

**Structure:**
- Specifies 3 conversion targets per equation: LaTeX, PyTorch pseudocode, plain-English description
- Specifies 4 metadata fields: equation number, section, variable definitions, category
- Includes a complete JSON example for the scaled dot-product attention equation
- Categories: `forward_pass`, `loss`, `initialization`, `optimization`, `metric`

**Key excerpt:**
```json
{
  "equation_number": "Eq. 1",
  "section": "3.2 Scaled Dot-Product Attention",
  "latex": "\\text{Attention}(Q,K,V) = ...",
  "pytorch": "attn_weights = F.softmax(torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(d_k), dim=-1)\noutput = torch.matmul(attn_weights, V)",
  "variables": {"Q": "Query matrix, shape (batch, heads, seq_len, d_k)", ...},
  "category": "forward_pass"
}
```

**Output format:** JSON array.

---

### Planning Prompts (3)

Used exclusively in Agent mode by the `DecomposedPlanner`.

#### `overall_plan.txt` (19 lines)

**Used by:** `DecomposedPlanner._step1_overall_plan()` in `core/planner.py`

**Purpose:** Extract a high-level implementation roadmap from the paper.

**Structure:**
- Concise prompt specifying 6 JSON fields: `core_components`, `methods_to_implement`, `training_objectives`, `data_processing_steps`, `evaluation_protocols`, `summary`
- Each field includes concrete examples (e.g., "BPE tokenization with 37000 merge operations")
- Exhaustiveness directive: "Every algorithm, loss function, data step, and evaluation metric mentioned in the paper should be captured."

**Output format:** JSON object.

---

#### `architecture_design.txt` (56 lines)

**Used by:** `DecomposedPlanner._step2_architecture_design()` in `core/planner.py`

**Purpose:** Design the repository file structure with Mermaid class and sequence diagrams.

**Structure:**
- 4 JSON output fields with detailed format specifications
- Complete Mermaid classDiagram example showing inheritance, composition, and attributes
- Complete Mermaid sequenceDiagram example showing the training flow (DataLoader, Model, Loss, Optimizer)
- Module relationship format: `{from, to, relationship, description}`

This is the longest planning prompt and produces the most structured output of the planning sub-stages.

**Output format:** JSON object.

---

#### `logic_design.txt` (36 lines)

**Used by:** `DecomposedPlanner._step3_logic_design()` in `core/planner.py`

**Purpose:** Determine dependency graph, execution order, and per-file implementation logic.

**Structure:**
- Specifies generation ordering rules: config/utils first, base classes before derived, data before training, model bottom-up, tests last
- Dependency graph format with example
- Per-file specifications with function signatures, equation references, and complexity levels

**Output format:** JSON object.

---

### Generation Prompts (3)

These prompts produce actual code and infrastructure files.

#### `coder.txt` (36 lines)

**Used by:** `CodeSynthesizer._generate_single_file()` in `core/coder.py`

**Purpose:** Generate production-quality Python code for a single file, faithful to the paper.

**Structure:** Seven strict requirements, each with sub-rules and examples:

1. **Equation Fidelity** -- Embed LaTeX as comments above implementations. Use EXACT operations (e.g., pre-norm vs post-norm).
2. **Dimension Correctness** -- Add shape comments (e.g., `# (batch, seq_len, d_model) -> (batch, num_heads, seq_len, d_k)`). Use assert statements. Document shapes in docstrings.
3. **Hyperparameter Injection** -- NO hardcoded values. All come from config or constructor args. Defaults match paper values.
4. **Code Quality** -- Type hints, docstrings with Args/Returns, proper `__init__.py` exports, naming conventions.
5. **PyTorch Conventions** -- `nn.Module` subclasses, standard layers (`nn.Linear`, `nn.LayerNorm`), register buffers, `F.scaled_dot_product_attention`.
6. **Imports** -- Explicit imports from the repo's own modules (not relative imports).
7. **Output Format** -- ONLY file content. No markdown fences, no explanations.

**Paired system prompt:** "You are an expert ML engineer writing production-quality Python code. You implement research papers faithfully, with exact equations, correct tensor dimensions, and proper loss functions. Output ONLY the file content -- no explanations, no markdown fences."

---

#### `test_generator.txt` (38 lines)

**Used by:** `TestGenerator._generate_test_file()` in `advanced/test_generator.py`

**Purpose:** Generate comprehensive pytest test suites.

**Structure:** Five test category specifications:

1. **Dimension Tests** -- Input/output shapes, intermediate shapes, batch dimension, variable lengths
2. **Equation Tests** -- Known input/output pairs, numerical stability, gradient flow
3. **Configuration Tests** -- Different configs, paper defaults, invalid config detection
4. **Loss Function Tests** -- Known loss values, gradient computation, label smoothing
5. **Integration Tests** -- Full forward pass, backward pass, training step reduces loss

Plus pytest convention guidelines: naming, `@pytest.mark.parametrize`, `torch.testing.assert_close`.

**Output format:** Complete test file content.

---

#### `devops.txt` (22 lines)

**Used by:** `DevOpsGenerator` (available as a template, though the current implementation uses hardcoded templates in `advanced/devops.py`)

**Purpose:** Generate deployment and CI/CD files.

**Template variables used:** `{repo_name}`, `{description}`, `{python_version}`, `{training_entrypoint}`, `{inference_entrypoint}`, `{requirements}`, `{file_list}`

Note: This prompt uses single curly brace `{placeholder}` syntax (not `{{placeholder}}`), since it was designed to be used with Python's `str.format()` or manual replacement. The current `DevOpsGenerator` implementation uses deterministic templates rather than LLM generation, but this prompt serves as the specification for what LLM-enhanced generation should produce.

**Output format:** Files separated by `===FILE: path/to/file===` markers.

---

### Validation Prompts (3)

#### `validator.txt` (52 lines)

**Used by:** `CodeValidator.validate()` in `core/validator.py`

**Purpose:** Review generated code against the paper and score fidelity.

**Structure:** The most detailed prompt in the system, organized as a review checklist:

1. **Equation Fidelity** -- Every numbered equation implemented; operations correct (softmax dimension, reduction axis, normalization constants, scaling factors); matrix multiply order, transpose operations, broadcasting
2. **Dimension Consistency** -- Tensor shapes match paper; reshape/view correct; attention masks correct shape; batch dimension consistent
3. **Hyperparameter Completeness** -- Every hyperparameter configurable; defaults match paper; no undocumented hyperparameters
4. **Loss Function Accuracy** -- Exact formulation; label smoothing, weight terms, regularization; correct reduction
5. **Architecture Correctness** -- Layer ordering (pre-norm vs post-norm); skip connections; activation functions; dropout placement
6. **Code Quality** -- Missing imports, undefined variables, type errors, missing return statements

Severity definitions with examples:
- **critical:** Wrong equation, wrong dimensions, missing loss terms
- **warning:** Missing dropout, hardcoded hyperparameter, missing docstring
- **info:** Style issues, minor suggestions

Pass criteria: `score >= 80 AND critical_count == 0`

**Output format:** JSON object with `score`, `equation_coverage`, `hyperparam_coverage`, `summary`, `passed`, `issues`.

---

#### `self_refine_verify.txt` (47 lines)

**Used by:** `SelfRefiner.verify()` in `core/refiner.py`

**Purpose:** Critique any pipeline artifact against the paper context.

**Template variables:** `{artifact_type}` (substituted via `{{artifact_type}}` in the actual template)

**Structure:** A unified verification prompt with artifact-type-specific checklists:

- **overall_plan:** All core components identified? All training objectives? All evaluation metrics? Complete data pipeline?
- **architecture_design:** File list covers all components? Class diagrams accurate? Sequence diagram correct? Module relationships complete?
- **logic_design:** Execution order consistent with dependencies? Circular dependencies (CRITICAL)? Every file specified? Function signatures complete?
- **config:** All hyperparameters included? Values correct? YAML valid and organized?
- **file_analysis:** All classes/functions specified? Imports correct? Algorithms accurate? Input/output shapes correct?
- **code:** All algorithms implemented? Equations correct? Imports valid? Syntax errors?

**Output format:** JSON with `critique`, `issues` (array with severity), `score` (1-5), `needs_refinement` (boolean).

---

#### `self_refine_refine.txt` (30 lines)

**Used by:** `SelfRefiner.refine_artifact()` in `core/refiner.py`

**Purpose:** Produce a refined version of an artifact that addresses all issues from verification.

**Template variables:** `{artifact_type}`, `{critique}`, `{issues}`, `{artifact}`, `{context}`

**Structure:**
- Presents the original artifact, the critique, and the paper context
- Four specific tasks: fix critical issues, fix warnings, preserve correct content, add missing components
- Format rules: maintain same schema, output valid JSON/YAML/code as appropriate
- Strict output constraint: ONLY the refined artifact, no explanations

**Output format:** Same format as the input artifact (JSON, YAML, or code).

---

### Specialized Prompts (2)

#### `file_analysis.txt` (44 lines)

**Used by:** `FileAnalyzer.analyze_file()` in `core/file_analyzer.py`

**Purpose:** Generate a detailed implementation blueprint for a single file before code generation.

**Structure:** Specifies 8 JSON output fields with detailed sub-schemas:

1. `file_path` -- The target file
2. `classes` -- PascalCase names, base classes, attributes (with types and defaults), methods (with signatures and equation references)
3. `functions` -- snake_case names, typed args with defaults, return types, descriptions
4. `imports` -- Exact import statements (e.g., `"from model.attention import MultiHeadAttention"`)
5. `dependencies` -- Other repo files this file imports from
6. `algorithms` -- Ordered algorithmic steps with equation references and tensor shapes
7. `input_output_spec` -- Input/output descriptions with exact shapes and dtypes
8. `test_criteria` -- What should be verified (shapes, attention weight sums, gradient flow)

Ends with a specificity directive: "Be SPECIFIC. Use exact tensor shapes, exact equation references, exact hyperparameter names. This specification will be handed directly to a code generator -- ambiguity causes bugs."

**Output format:** JSON object.

---

#### `auto_debug.txt` (40 lines)

**Used by:** `AutoDebugger._build_debug_prompt()` in `advanced/debugger.py`

**Purpose:** Analyze a runtime error and generate targeted fixes.

**Template variables:** `{error_message}`, `{error_type}`, `{source_files}`

**Structure:**
- Presents the error message, error type, and relevant source files
- Three-step task: identify root cause, determine affected files, generate minimal fix
- Common error patterns reference table (7 error types with fix strategies):
  - `ImportError/ModuleNotFoundError` -- Fix import paths, add `__init__.py`, install packages
  - `TypeError` -- Fix argument types, check signatures
  - `ValueError` -- Fix data shapes, check tensor dimensions
  - `RuntimeError` -- Fix CUDA issues, memory, device mismatches
  - `FileNotFoundError` -- Fix paths, create missing configs
  - `SyntaxError` -- Fix Python syntax
  - `AttributeError` -- Fix class attribute access, check API changes
- Conservative constraint: "make the MINIMAL change needed. Do not refactor or improve code beyond fixing the error."

**Output format:** JSON with `root_cause`, `fixes` (array of `{file_path, description, original_snippet, fixed_snippet}`), `additional_files_needed`, `packages_needed`.

Note: The `AutoDebugger` code actually expects a different schema (`fixes` with `file_path` and `fixed_content` for complete file replacements). The prompt's `original_snippet`/`fixed_snippet` format is the conceptual intent; the code's structured generation schema enforces complete file content.

---

### Evaluation Prompts (1)

#### `reference_eval.txt` (39 lines)

**Used by:** `ReferenceEvaluator._build_eval_prompt()` in `advanced/evaluator.py`

**Purpose:** Score generated code against a reference implementation and/or the paper.

**Template variables:** `{paper_text}`, `{generated_files}`, `{reference_files}`

**Structure:**
- Presents paper text, generated code, and reference code
- 4-step evaluation protocol:
  1. Identify ALL key paper components
  2. Categorize by severity (HIGH: core algorithm; MEDIUM: data/metrics; LOW: logging/utils)
  3. Check implementation fidelity for each component
  4. Compare against reference for structural and functional similarity
- Component scores across 6 dimensions: model_architecture, loss_functions, data_processing, training_loop, evaluation, configuration
- Scoring directive: "Score generously if the implementation is functionally correct even if style/naming differs from reference."

**Output format:** JSON with `overall_score` (1-5), `component_scores`, `coverage` (0-100), `missing_components`, `extra_components`, `severity_breakdown`, `summary`.

---

## Prompt Design Patterns

The prompts across Research2Repo follow six consistent design patterns.

### Pattern 1: Role Assignment

Every prompt opens with a role assignment that primes the LLM for the specific task:

| Prompt | Role |
|---|---|
| `analyzer.txt` | "You are an expert ML researcher performing a thorough analysis" |
| `coder.txt` | "You are an expert ML engineer writing production-quality Python code" |
| `validator.txt` | "You are a meticulous ML code reviewer" |
| `auto_debug.txt` | "You are an expert Python debugger" |
| `self_refine_verify.txt` | "You are a rigorous reviewer" |
| `self_refine_refine.txt` | "You are an expert who refines and improves artifacts" |
| `reference_eval.txt` | "You are an expert evaluator" |
| `file_analysis.txt` | "You are an expert ML engineer performing detailed per-file analysis" |
| `architecture_design.txt` | "You are an expert software architect" |
| `logic_design.txt` | "You are an expert software engineer" |
| `devops.txt` | "You are a DevOps engineer" |
| `overall_plan.txt` | "You are an expert ML researcher" |
| `diagram_extractor.txt` | (system prompt: "expert at reading ML paper diagrams") |
| `equation_extractor.txt` | (system prompt: "expert at extracting mathematical equations") |
| `test_generator.txt` | (system prompt: "expert at writing pytest tests for ML code") |

System prompts (set in code, not in the .txt files) reinforce the role.

### Pattern 2: Structured JSON Output

Most prompts explicitly define the expected JSON schema within the prompt text itself. This redundancy (the schema is also passed programmatically via `generate_structured()`) significantly improves compliance:

```
Return a JSON object with:
- "score": 0-100 fidelity score
- "equation_coverage": 0-100 percentage of paper equations found in code
- "issues": array of {severity, file_path, line_hint, description, suggestion, category}
```

Prompts that use this pattern: `analyzer.txt`, `overall_plan.txt`, `architecture_design.txt`, `logic_design.txt`, `file_analysis.txt`, `validator.txt`, `self_refine_verify.txt`, `auto_debug.txt`, `reference_eval.txt`.

### Pattern 3: Exhaustiveness Directives

To counter LLMs' tendency to summarize or omit details, prompts include explicit exhaustiveness instructions:

- `analyzer.txt`: "CRITICAL: Be exhaustive. Missing a single equation or hyperparameter will cause the generated code to be incorrect."
- `equation_extractor.txt`: "IMPORTANT: Capture EVERY equation, including those in appendices and supplementary material."
- `overall_plan.txt`: "Be exhaustive. Every algorithm, loss function, data step, and evaluation metric mentioned in the paper should be captured."
- `validator.txt`: "Be thorough. A missed critical issue means the model will train incorrectly."
- `coder.txt`: Uses "EXACT" and "ALL" in every requirement section.

### Pattern 4: Negative Constraints

Prompts use explicit negative constraints to prevent common LLM misbehaviors:

- **No markdown fences:** `analyzer.txt`: "Respond with ONLY the JSON object. No markdown fences, no explanations." / `coder.txt`: "Output ONLY the file content. No markdown fences, no explanations before or after."
- **No explanations:** `self_refine_refine.txt`: "Output ONLY the refined artifact. No explanations, no markdown fences."
- **No hardcoded values:** `coder.txt`: "HYPERPARAMETER INJECTION: NO hardcoded values."
- **No refactoring:** `auto_debug.txt`: "Be conservative -- make the MINIMAL change needed. Do not refactor or improve code beyond fixing the error."

Despite these constraints, the code defensively strips markdown fences from all LLM outputs via `_clean_output()` methods.

### Pattern 5: Quality Checklists

The `validator.txt` and `self_refine_verify.txt` prompts structure their instructions as numbered checklists, each with concrete sub-items:

```
1. EQUATION FIDELITY (category: "equation")
   - Is every numbered equation from the paper implemented in code?
   - Are the operations correct? (e.g., softmax dimension, reduction axis, normalization constants)
   - Are scaling factors correct? (e.g., 1/sqrt(d_k), temperature parameters)
   - Check: matrix multiply order, transpose operations, broadcasting
```

This pattern forces the LLM to evaluate each dimension systematically rather than giving a gestalt assessment.

### Pattern 6: Concrete Examples

Several prompts include worked examples to anchor the LLM's output format:

- `equation_extractor.txt`: Complete JSON example for scaled dot-product attention
- `architecture_design.txt`: Complete Mermaid classDiagram and sequenceDiagram examples
- `diagram_extractor.txt`: Complete Mermaid graph example with subgraphs
- `coder.txt`: Inline code examples (`# Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V`)
- `analyzer.txt`: Format examples for equations and hyperparameters

---

## Template Variables Reference

Most prompts are static system-level instructions. The following prompts use template variables that are substituted at runtime:

### `devops.txt`

| Variable | Source | Description |
|---|---|---|
| `{repo_name}` | `ArchitecturePlan.repo_name` | Repository name |
| `{description}` | `ArchitecturePlan.description` | One-line description |
| `{python_version}` | `ArchitecturePlan.python_version` | Python version |
| `{training_entrypoint}` | `ArchitecturePlan.training_entrypoint` | Training script path |
| `{inference_entrypoint}` | `ArchitecturePlan.inference_entrypoint` | Inference script path |
| `{requirements}` | `ArchitecturePlan.requirements` | pip package list |
| `{file_list}` | Generated files | List of generated file paths |

### `auto_debug.txt`

| Variable | Source | Description |
|---|---|---|
| `{{error_message}}` | `ExecutionResult.stderr` | Full traceback (truncated to 4,000 chars) |
| `{{error_type}}` | `ExecutionResult.error_type` | Classified error category |
| `{{source_files}}` | Relevant source files | Python files referenced in traceback |

### `self_refine_verify.txt`

| Variable | Source | Description |
|---|---|---|
| `{artifact_type}` | Caller | One of: overall_plan, architecture_design, logic_design, config, file_analysis, code |

### `self_refine_refine.txt`

| Variable | Source | Description |
|---|---|---|
| `{artifact_type}` | Caller | Artifact type identifier |
| `{critique}` | Verification step | Critique text from verify() |
| `{issues}` | Verification step | List of issues found |
| `{artifact}` | Pipeline | The original artifact content |
| `{context}` | Pipeline | Paper context string |

### `reference_eval.txt`

| Variable | Source | Description |
|---|---|---|
| `{paper_text}` | `PaperAnalysis.full_text` | Full paper text (truncated to 30,000 chars) |
| `{generated_files}` | Pipeline | Generated code files |
| `{reference_files}` | `--reference-dir` | Ground-truth reference code |

---

## Prompt-to-Module Mapping Table

| Prompt File | Used By Module | Used By Class/Function | Output Format | Temperature | Key Constraints |
|---|---|---|---|---|---|
| `analyzer.txt` | `core/analyzer.py` | `PaperAnalyzer.analyze()` | JSON (13 fields) | 0.1 | Must capture ALL equations and hyperparameters |
| `diagram_extractor.txt` | `core/analyzer.py` | `PaperAnalyzer.extract_diagrams_to_mermaid()` | Mermaid code blocks | 0.1 | `---` separators; `NO_DIAGRAMS` sentinel |
| `equation_extractor.txt` | `advanced/equation_extractor.py` | `EquationExtractor.extract_from_text()` | JSON array | 0.1 | LaTeX + PyTorch + variables for each equation |
| `overall_plan.txt` | `core/planner.py` | `DecomposedPlanner._step1_overall_plan()` | JSON (6 fields) | 0.1 | Exhaustive component identification |
| `architecture_design.txt` | `core/planner.py` | `DecomposedPlanner._step2_architecture_design()` | JSON (4 fields) | 0.1 | Mermaid class and sequence diagrams required |
| `logic_design.txt` | `core/planner.py` | `DecomposedPlanner._step3_logic_design()` | JSON (3 fields) | 0.1 | Topological sort consistency |
| `architect.txt` | `core/architect.py` | `SystemArchitect.design_system()` | JSON (ArchitecturePlan) | 0.1 | Essential files guaranteed post-hoc |
| `coder.txt` | `core/coder.py` | `CodeSynthesizer._generate_single_file()` | Raw Python/YAML/Markdown | 0.15 | No markdown fences; equations as comments |
| `test_generator.txt` | `advanced/test_generator.py` | `TestGenerator._generate_test_file()` | Raw Python (pytest) | 0.15 | pytest conventions; parametrize |
| `devops.txt` | `advanced/devops.py` | `DevOpsGenerator` (template spec) | Multi-file with markers | 0.1 | GPU-aware; production-quality |
| `validator.txt` | `core/validator.py` | `CodeValidator.validate()` | JSON (ValidationReport) | 0.1 | Pass: score >= 80 AND 0 critical issues |
| `self_refine_verify.txt` | `core/refiner.py` | `SelfRefiner.verify()` | JSON (critique + issues) | 0.2 | Artifact-type-specific checklists |
| `self_refine_refine.txt` | `core/refiner.py` | `SelfRefiner.refine_artifact()` | Same as input artifact | 0.15 | Preserve correct content; fix all critical issues |
| `file_analysis.txt` | `core/file_analyzer.py` | `FileAnalyzer.analyze_file()` | JSON (FileAnalysis) | 0.1 | Exact shapes, exact equations, exact names |
| `auto_debug.txt` | `advanced/debugger.py` | `AutoDebugger._build_debug_prompt()` | JSON (fixes array) | 0.1 | Minimal changes only; complete file content |
| `reference_eval.txt` | `advanced/evaluator.py` | `ReferenceEvaluator._build_eval_prompt()` | JSON (EvaluationScore) | 0.3 | Score generously for functional correctness |

---

## Customizing Prompts

### How to Modify Prompts

1. **Edit directly:** All prompts are plain text files in the `prompts/` directory. Edit them with any text editor.

2. **Backup first:** Before modifying, create a backup:
   ```bash
   cp prompts/coder.txt prompts/coder.txt.bak
   ```

3. **Test with verbose mode:** Use `--verbose` (or `-v`) to see LLM responses and verify your changes produce the expected output format.

4. **Respect the output schema:** This is the most important constraint. The parsing code in each module expects a specific JSON structure. If you change the output format requested by the prompt, you must also update the corresponding parsing code.

### What You Can Safely Change

- **Role descriptions** -- Change "expert ML researcher" to a more specific role.
- **Emphasis and directives** -- Add domain-specific instructions (e.g., "Pay special attention to attention mask handling").
- **Examples** -- Add or modify examples to match your use case.
- **Checklist items** -- Add new validation checks or analysis fields (but you must also update the parsing code to handle them).

### What You Should NOT Change

- **JSON field names** -- The parsing code uses exact key names like `"score"`, `"equations"`, `"issues"`. Changing these breaks parsing.
- **Output format instructions** -- "Respond with ONLY the JSON object" is critical. Removing it causes the LLM to add explanations that break JSON parsing.
- **Template variable placeholders** -- `{{error_type}}`, `{{artifact_type}}`, etc. must remain exactly as written for substitution to work.

### Adding a New Prompt

To add a new prompt:

1. Create `prompts/my_new_prompt.txt`.
2. In your module, define the path:
   ```python
   PROMPT_FILE = os.path.join(
       os.path.dirname(os.path.dirname(__file__)), "prompts", "my_new_prompt.txt"
   )
   ```
3. Load it with the standard pattern:
   ```python
   prompt = self._load_prompt(self.PROMPT_FILE)
   if not prompt:
       prompt = self._default_prompt()  # fallback
   ```

---

## Tips for Better Results

### Temperature Settings

Temperature controls randomness. Research2Repo uses different temperatures for different tasks:

| Temperature | Used For | Rationale |
|---|---|---|
| 0.1 | Analysis, planning, validation, debugging | Maximum determinism for structured extraction and evaluation |
| 0.15 | Code generation, refinement | Slight creativity for implementation choices while staying faithful |
| 0.2 | Self-refine verification | Allows diverse critique perspectives |
| 0.3 | Reference evaluation (multi-sample) | Intentional variance across evaluation samples for robust aggregation |

If you find code generation is too rigid (e.g., identical patterns across files), try increasing the coder temperature to 0.2. If validation is too lenient, try decreasing it to 0.05.

### Provider Selection for Long Papers

For papers over 50 pages, prefer Gemini as the primary provider. Gemini's File Upload API processes the PDF natively without text extraction, preserving:
- Table formatting and structure
- Figure references and positioning
- Mathematical notation fidelity
- Appendix content that PyPDF2 may garble

Other providers receive extracted text, which loses formatting for very long documents.

### Self-Refine Trade-offs

Enabling `--refine` adds approximately 2x LLM calls per stage where it is applied (one verify call + one refine call per iteration, with default `max_iterations=2`). This is most valuable for:

- **Planning stages:** Catches missing components and dependency errors early, before they propagate to code generation.
- **File analysis:** Ensures tensor shapes and function signatures are consistent across files.

It is less critical for code validation, which already has its own auto-fix loop.

### Per-File Analysis is the Biggest Quality Lever

According to the PaperCoder ablation study, per-file analysis (Agent Stage 3) contributes a +0.23 improvement in repository quality scores. This stage is the single most impactful addition in agent mode because:

1. It forces the LLM to think through each file's implementation before generating code.
2. The accumulated context ensures cross-file consistency (import paths, class names, tensor shapes).
3. It creates a contract that the code generator can follow, reducing hallucination.

### Prompt Length and Context Window

The effective prompt for code generation can be very long (paper context + plan + dependency files + instructions). If you hit context window limits:

1. The dependency context truncates files to 3,000 characters (direct deps) or 1,500 characters (rolling window).
2. The validation context truncates files to 5,000 characters.
3. The evaluation context truncates files to 6,000 characters and paper text to 30,000 characters.
4. Equation lists are capped at 15--30 entries in various prompts.

If you need more context, use a provider with a larger context window (Gemini supports up to 2M tokens).

### Debugging Prompt Issues

If the pipeline produces unexpected results:

1. **Check the JSON parsing:** Add `print(result.text)` before the `json.loads()` call to see what the LLM actually returned.
2. **Look for markdown fences:** Despite negative constraints, LLMs sometimes wrap output in `` ```json ``` ``. The code handles this, but custom parsing may not.
3. **Check fallback activation:** If you see "[Module] Structured generation failed, retrying as text...", the structured output mode failed and the fallback may produce different results.
4. **Inspect the cache:** Cached results in `.r2r_cache/` may use old prompt versions. Use `--no-cache` or `--clear-cache` when testing prompt changes.
