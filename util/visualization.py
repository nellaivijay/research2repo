"""
Visualization utilities for Research2Repo pipeline stages
Based on OmniShotCut's visualization approach
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from typing import Dict, List, Any, Optional
import json
from pathlib import Path


class PipelineVisualizer:
    """Visualize Research2Repo pipeline stages and progress."""
    
    def __init__(self, style: str = "modern"):
        """
        Initialize the visualizer.
        
        Args:
            style: Visualization style ('modern', 'classic', 'minimal')
        """
        self.style = style
        self.colors = {
            'modern': {
                'background': '#f8fafc',
                'stage_box': '#3b82f6',
                'stage_text': '#ffffff',
                'arrow': '#64748b',
                'completed': '#10b981',
                'in_progress': '#f59e0b',
                'pending': '#94a3b8',
                'error': '#ef4444'
            },
            'classic': {
                'background': '#ffffff',
                'stage_box': '#4a90e2',
                'stage_text': '#ffffff',
                'arrow': '#333333',
                'completed': '#2ecc71',
                'in_progress': '#f39c12',
                'pending': '#95a5a6',
                'error': '#e74c3c'
            },
            'minimal': {
                'background': '#ffffff',
                'stage_box': '#000000',
                'stage_text': '#ffffff',
                'arrow': '#666666',
                'completed': '#000000',
                'in_progress': '#666666',
                'pending': '#cccccc',
                'error': '#ff0000'
            }
        }
    
    def visualize_pipeline_flow(
        self,
        mode: str = "agent",
        completed_stages: List[str] = None,
        current_stage: str = None,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize the pipeline flow diagram.
        
        Args:
            mode: Pipeline mode ('classic' or 'agent')
            completed_stages: List of completed stage names
            current_stage: Currently executing stage name
            save_path: Path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        if completed_stages is None:
            completed_stages = []
        
        colors = self.colors[self.style]
        
        # Define stages based on mode
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
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.set_xlim(0, 12)
        ax.set_ylim(0, len(stages) + 2)
        ax.axis('off')
        
        # Background
        ax.set_facecolor(colors['background'])
        
        # Title
        ax.text(6, len(stages) + 1, f"Research2Repo Pipeline - {mode.title()} Mode",
                ha='center', va='center', fontsize=16, fontweight='bold')
        
        # Draw stages
        for i, stage in enumerate(stages):
            y_pos = len(stages) - i - 0.5
            
            # Determine color based on status
            if stage in completed_stages:
                box_color = colors['completed']
            elif stage == current_stage:
                box_color = colors['in_progress']
            else:
                box_color = colors['pending']
            
            # Draw stage box
            box = FancyBboxPatch((1, y_pos - 0.4), 10, 0.8,
                                boxstyle="round,pad=0.1",
                                facecolor=box_color,
                                edgecolor='black',
                                linewidth=1)
            ax.add_patch(box)
            
            # Add stage text
            ax.text(6, y_pos, f"{i+1}. {stage}",
                   ha='center', va='center',
                   fontsize=10, color=colors['stage_text'],
                   fontweight='bold')
            
            # Draw arrow to next stage
            if i < len(stages) - 1:
                arrow = FancyArrowPatch((6, y_pos - 0.4), (6, y_pos - 1.2),
                                       arrowstyle='->',
                                       mutation_scale=20,
                                       color=colors['arrow'],
                                       linewidth=2)
                ax.add_patch(arrow)
        
        # Add legend
        legend_elements = [
            mpatches.Patch(color=colors['completed'], label='Completed'),
            mpatches.Patch(color=colors['in_progress'], label='In Progress'),
            mpatches.Patch(color=colors['pending'], label='Pending')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_progress_chart(
        self,
        stage_times: Dict[str, float],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize progress chart with time spent per stage.
        
        Args:
            stage_times: Dictionary mapping stage names to time spent
            save_path: Path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        colors = self.colors[self.style]
        
        stages = list(stage_times.keys())
        times = list(stage_times.values())
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create bar chart
        bars = ax.barh(stages, times, color=colors['stage_box'])
        
        # Customize
        ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Pipeline Stage', fontsize=12, fontweight='bold')
        ax.set_title('Pipeline Execution Time per Stage', fontsize=14, fontweight='bold')
        
        # Add value labels
        for bar, time in zip(bars, times):
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                   f'{time:.1f}s',
                   ha='left', va='center', fontsize=9)
        
        # Grid
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        # Background
        ax.set_facecolor(colors['background'])
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_cost_breakdown(
        self,
        cost_breakdown: Dict[str, float],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize cost breakdown by pipeline stage.
        
        Args:
            cost_breakdown: Dictionary mapping stage names to costs
            save_path: Path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        colors = self.colors[self.style]
        
        stages = list(cost_breakdown.keys())
        costs = list(cost_breakdown.values())
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create pie chart
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(stages)))
        wedges, texts, autotexts = ax.pie(costs, labels=stages, autopct='%1.1f%%',
                                           startangle=90, colors=colors_pie)
        
        # Customize text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('Pipeline Cost Breakdown', fontsize=14, fontweight='bold')
        
        # Add total cost as text
        total_cost = sum(costs)
        ax.text(0, -1.3, f'Total Cost: ${total_cost:.4f}',
               ha='center', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_validation_scores(
        self,
        validation_scores: Dict[str, float],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize validation scores across different metrics.
        
        Args:
            validation_scores: Dictionary mapping metric names to scores (0-100)
            save_path: Path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        colors = self.colors[self.style]
        
        metrics = list(validation_scores.keys())
        scores = list(validation_scores.values())
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create bar chart
        bars = ax.bar(metrics, scores, color=colors['stage_box'])
        
        # Add threshold line
        ax.axhline(y=80, color=colors['completed'], linestyle='--', 
                  linewidth=2, label='Pass Threshold (80)')
        
        # Customize
        ax.set_ylabel('Score', fontsize=12, fontweight='bold')
        ax.set_xlabel('Validation Metric', fontsize=12, fontweight='bold')
        ax.set_title('Validation Scores', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Add value labels
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{score:.1f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Grid
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Background
        ax.set_facecolor(colors['background'])
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_provider_comparison(
        self,
        provider_data: Dict[str, Dict[str, float]],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize comparison across different providers.
        
        Args:
            provider_data: Dictionary mapping provider names to their metrics
            save_path: Path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        colors = self.colors[self.style]
        
        providers = list(provider_data.keys())
        metrics = list(next(iter(provider_data.values())).keys())
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Create grouped bar chart
        x = np.arange(len(metrics))
        width = 0.8 / len(providers)
        
        for i, provider in enumerate(providers):
            values = [provider_data[provider].get(metric, 0) for metric in metrics]
            offset = (i - len(providers)/2 + 0.5) * width
            bars = ax.bar(x + offset, values, width, label=provider)
        
        # Customize
        ax.set_ylabel('Score / Cost', fontsize=12, fontweight='bold')
        ax.set_xlabel('Metric', fontsize=12, fontweight='bold')
        ax.set_title('Provider Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(metrics)
        ax.legend()
        
        # Grid
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Background
        ax.set_facecolor(colors['background'])
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_dashboard(
        self,
        pipeline_state: Dict[str, Any],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Create a comprehensive dashboard showing pipeline status.
        
        Args:
            pipeline_state: Dictionary containing pipeline state information
            save_path: Path to save the figure
            
        Returns:
            matplotlib Figure object
        """
        colors = self.colors[self.style]
        
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Pipeline Flow (top, spanning all columns)
        ax1 = fig.add_subplot(gs[0, :])
        self._add_pipeline_summary(ax1, pipeline_state)
        
        # 2. Progress Chart (middle left)
        ax2 = fig.add_subplot(gs[1, 0])
        if 'stage_times' in pipeline_state:
            self._add_progress_chart(ax2, pipeline_state['stage_times'])
        else:
            ax2.text(0.5, 0.5, 'No timing data available',
                    ha='center', va='center', transform=ax2.transAxes)
        
        # 3. Cost Breakdown (middle center)
        ax3 = fig.add_subplot(gs[1, 1])
        if 'cost_breakdown' in pipeline_state:
            self._add_cost_breakdown(ax3, pipeline_state['cost_breakdown'])
        else:
            ax3.text(0.5, 0.5, 'No cost data available',
                    ha='center', va='center', transform=ax3.transAxes)
        
        # 4. Validation Scores (middle right)
        ax4 = fig.add_subplot(gs[1, 2])
        if 'validation_scores' in pipeline_state:
            self._add_validation_scores(ax4, pipeline_state['validation_scores'])
        else:
            ax4.text(0.5, 0.5, 'No validation data available',
                    ha='center', va='center', transform=ax4.transAxes)
        
        # 5. Statistics (bottom, spanning all columns)
        ax5 = fig.add_subplot(gs[2, :])
        self._add_statistics(ax5, pipeline_state)
        
        fig.suptitle('Research2Repo Pipeline Dashboard', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def _add_pipeline_summary(self, ax, pipeline_state: Dict[str, Any]):
        """Add pipeline summary to axis."""
        colors = self.colors[self.style]
        ax.set_facecolor(colors['background'])
        ax.axis('off')
        
        # Summary text
        summary = f"""
Pipeline Status: {pipeline_state.get('status', 'Unknown')}
Current Stage: {pipeline_state.get('current_stage', 'None')}
Progress: {pipeline_state.get('progress', 0):.1f}%
Files Generated: {pipeline_state.get('files_generated', 0)}
Total Time: {pipeline_state.get('elapsed_time', 0):.1f}s
        """
        
        ax.text(0.1, 0.5, summary, transform=ax.transAxes,
               fontsize=12, verticalalignment='center',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def _add_progress_chart(self, ax, stage_times: Dict[str, float]):
        """Add progress chart to axis."""
        colors = self.colors[self.style]
        stages = list(stage_times.keys())
        times = list(stage_times.values())
        
        bars = ax.barh(stages, times, color=colors['stage_box'])
        ax.set_xlabel('Time (s)', fontsize=10)
        ax.tick_params(axis='both', which='major', labelsize=8)
        ax.set_facecolor(colors['background'])
    
    def _add_cost_breakdown(self, ax, cost_breakdown: Dict[str, float]):
        """Add cost breakdown to axis."""
        stages = list(cost_breakdown.keys())
        costs = list(cost_breakdown.values())
        
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(stages)))
        ax.pie(costs, labels=stages, autopct='%1.1f%%', startangle=90,
              colors=colors_pie, textprops={'fontsize': 8})
        ax.set_title('Cost Breakdown', fontsize=10)
    
    def _add_validation_scores(self, ax, validation_scores: Dict[str, float]):
        """Add validation scores to axis."""
        colors = self.colors[self.style]
        metrics = list(validation_scores.keys())
        scores = list(validation_scores.values())
        
        bars = ax.bar(metrics, scores, color=colors['stage_box'])
        ax.axhline(y=80, color=colors['completed'], linestyle='--', linewidth=1)
        ax.set_ylim(0, 100)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_facecolor(colors['background'])
    
    def _add_statistics(self, ax, pipeline_state: Dict[str, Any]):
        """Add statistics to axis."""
        colors = self.colors[self.style]
        ax.set_facecolor(colors['background'])
        ax.axis('off')
        
        stats_text = f"""
Provider: {pipeline_state.get('provider', 'N/A')}
Model: {pipeline_state.get('model', 'N/A')}
Mode: {pipeline_state.get('mode', 'N/A')}
Validation Score: {pipeline_state.get('validation_score', 0)}/100
Total Cost: ${pipeline_state.get('total_cost', 0):.4f}
        """
        
        ax.text(0.1, 0.5, stats_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='center',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))


def generate_pipeline_report(
    pipeline_state: Dict[str, Any],
    output_dir: str
) -> str:
    """
    Generate a comprehensive pipeline report with visualizations.
    
    Args:
        pipeline_state: Dictionary containing pipeline state information
        output_dir: Directory to save the report
        
    Returns:
        Path to the generated report file
    """
    visualizer = PipelineVisualizer(style="modern")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual visualizations
    report_files = []
    
    # Pipeline flow
    if 'completed_stages' in pipeline_state or 'current_stage' in pipeline_state:
        fig = visualizer.visualize_pipeline_flow(
            mode=pipeline_state.get('mode', 'agent'),
            completed_stages=pipeline_state.get('completed_stages', []),
            current_stage=pipeline_state.get('current_stage'),
            save_path=os.path.join(output_dir, 'pipeline_flow.png')
        )
        plt.close(fig)
        report_files.append('pipeline_flow.png')
    
    # Progress chart
    if 'stage_times' in pipeline_state:
        fig = visualizer.visualize_progress_chart(
            pipeline_state['stage_times'],
            save_path=os.path.join(output_dir, 'progress_chart.png')
        )
        plt.close(fig)
        report_files.append('progress_chart.png')
    
    # Cost breakdown
    if 'cost_breakdown' in pipeline_state:
        fig = visualizer.visualize_cost_breakdown(
            pipeline_state['cost_breakdown'],
            save_path=os.path.join(output_dir, 'cost_breakdown.png')
        )
        plt.close(fig)
        report_files.append('cost_breakdown.png')
    
    # Validation scores
    if 'validation_scores' in pipeline_state:
        fig = visualizer.visualize_validation_scores(
            pipeline_state['validation_scores'],
            save_path=os.path.join(output_dir, 'validation_scores.png')
        )
        plt.close(fig)
        report_files.append('validation_scores.png')
    
    # Dashboard
    fig = visualizer.create_dashboard(
        pipeline_state,
        save_path=os.path.join(output_dir, 'dashboard.png')
    )
    plt.close(fig)
    report_files.append('dashboard.png')
    
    # Save pipeline state as JSON
    state_file = os.path.join(output_dir, 'pipeline_state.json')
    with open(state_file, 'w') as f:
        json.dump(pipeline_state, f, indent=2)
    report_files.append('pipeline_state.json')
    
    return output_dir


if __name__ == "__main__":
    # Example usage
    example_state = {
        "status": "completed",
        "current_stage": "Reference Evaluation",
        "progress": 100,
        "mode": "agent",
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "files_generated": 12,
        "validation_score": 92,
        "elapsed_time": 245.5,
        "total_cost": 0.025,
        "completed_stages": [
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
        ],
        "stage_times": {
            "Parse Paper": 15.2,
            "Decomposed Planning": 25.5,
            "Per-File Analysis": 45.8,
            "Document Segmentation": 12.3,
            "Self-Refine Loop": 35.7,
            "CodeRAG Mining": 28.4,
            "Context-Managed Coding": 52.1,
            "Validation": 18.9,
            "Execution Sandbox": 22.3,
            "Auto-Debugging": 15.6,
            "DevOps Generation": 12.4,
            "Reference Evaluation": 8.2
        },
        "cost_breakdown": {
            "Paper Analysis": 0.005,
            "Architecture Design": 0.00375,
            "Code Generation": 0.01,
            "Validation": 0.00375,
            "Testing": 0.0025
        },
        "validation_scores": {
            "Equation Coverage": 95,
            "Hyperparam Coverage": 88,
            "Code Quality": 92,
            "Test Coverage": 85
        }
    }
    
    # Generate report
    report_dir = generate_pipeline_report(example_state, "./example_report")
    print(f"Pipeline report generated in: {report_dir}")