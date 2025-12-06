# Enhanced Portfolio PDF Generation - Helper Functions
"""
This module contains helper functions for generating charts and visualizations
for the comprehensive portfolio PDF export using matplotlib.
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
from io import BytesIO
from typing import Dict, List, Tuple
import tempfile
import os


def create_pie_chart(data: Dict[str, float], title: str, colors: List[str] = None) -> str:
    """Create a pie chart and return the temporary file path."""
    fig, ax = plt.subplots(figsize=(6, 6), facecolor='white')
    
    labels = list(data.keys())
    values = list(data.values())
    
    if colors is None:
        colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))
    
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct='%1.1f%%',
        startangle=90, colors=colors,
        textprops={'fontsize': 10, 'weight': 'bold'}
    )
    
    # Make percentage text white for better visibility
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
    
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    plt.tight_layout()
    
    # Save to temporary file
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return tmp_file.name


def create_bar_chart(categories: List[str], values: List[float], title: str, 
                      ylabel: str = "Value", color: str = '#3498db') -> str:
    """Create a bar chart and return the temporary file path."""
    fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
    
    x_pos = np.arange(len(categories))
    bars = ax.bar(x_pos, values, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}',
                ha='center', va='bottom', fontsize=9, weight='bold')
    
    ax.set_xlabel('', fontsize=11, weight='bold')
    ax.set_ylabel(ylabel, fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return tmp_file.name


def create_horizontal_bar_chart(labels: List[str], values: List[float], title: str,
                                  max_value: float = 100, color: str = '#2ecc71') -> str:
    """Create horizontal bar chart for rankings."""
    fig, ax = plt.subplots(figsize=(7, len(labels) * 0.5 + 1), facecolor='white')
    
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, values)):
        ax.text(val + max_value * 0.02, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}',
                va='center', fontsize=9, weight='bold')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Score', fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    ax.set_xlim(0, max_value)
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.invert_yaxis()  # Top score at top
    
    plt.tight_layout()
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return tmp_file.name


def create_stacked_area_chart(years: List[int], ic_data: List[float], gen_data: List[float], 
                                title: str = "Capacity Trajectory") -> str:
    """Create stacked area chart for capacity over time."""
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
    
    ax.fill_between(years, 0, ic_data, alpha=0.6, color='#3498db', label='Interconnection MW')
    ax.fill_between(years, 0, gen_data, alpha=0.6, color='#e74c3c', label='Generation MW')
    
    ax.plot(years, ic_data, color='#2980b9', linewidth=2, marker='o', markersize=4)
    ax.plot(years, gen_data, color='#c0392b', linewidth=2, marker='s', markersize=4)
    
    ax.set_xlabel('Year', fontsize=11, weight='bold')
    ax.set_ylabel('MW', fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    ax.legend(loc='upper left', frameon=True, shadow=True)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return tmp_file.name


def create_timeline_heatmap(years: List[int], mw_by_year: List[float], title: str = "Capacity Coming Online") -> str:
    """Create a timeline heatmap showing capacity additions by year."""
    fig, ax = plt.subplots(figsize=(12, 2), facecolor='white')
    
    # Normalize values for color mapping
    max_val = max(mw_by_year) if mw_by_year else 1
    normalized = [v / max_val if max_val > 0 else 0 for v in mw_by_year]
    
    # Create colormap
    cmap = plt.cm.RdYlGn_r  # Red (high) to Green (low)
    
    # Draw rectangles for each year
    for i, (year, val, norm_val) in enumerate(zip(years, mw_by_year, normalized)):
        color = cmap(norm_val)
        rect = Rectangle((i, 0), 1, 1, facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        
        # Add text
        ax.text(i + 0.5, 0.5, f'{int(val)}\nMW', 
                ha='center', va='center', fontsize=8, weight='bold',
                color='white' if norm_val > 0.5 else 'black')
        ax.text(i + 0.5, -0.3, str(year), 
                ha='center', va='top', fontsize=9, weight='bold')
    
    ax.set_xlim(0, len(years))
    ax.set_ylim(-0.5, 1)
    ax.set_title(title, fontsize=14, weight='bold', pad=30)
    ax.axis('off')
    
    plt.tight_layout()
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return tmp_file.name


def create_progress_bars(categories: List[str], values: List[float], max_val: float = 100,
                          title: str = "Progress") -> str:
    """Create visual progress bars for program tracker stages."""
    fig, ax = plt.subplots(figsize=(8, len(categories) * 0.6 + 1), facecolor='white')
    
    y_pos = np.arange(len(categories))
    
    # Background bars
    ax.barh(y_pos, [max_val] * len(categories), color='#ecf0f1', alpha=0.5, height=0.6)
    
    # Progress bars with color coding
    colors = []
    for val in values:
        if val >= 75:
            colors.append('#27ae60')  # Green
        elif val >= 50:
            colors.append('#f39c12')  # Orange
        else:
            colors.append('#e74c3c')  # Red
    
    bars = ax.barh(y_pos, values, color=colors, alpha=0.8, height=0.6, edgecolor='black', linewidth=0.5)
    
    # Add percentage labels
    for i, (bar, val) in enumerate(zip(bars, values)):
        ax.text(val + 2, bar.get_y() + bar.get_height()/2,
                f'{val:.0f}%',
                va='center', fontsize=9, weight='bold')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=10)
    ax.set_xlabel('Progress (%)', fontsize=11, weight='bold')
    ax.set_title(title, fontsize=14, weight='bold', pad=20)
    ax.set_xlim(0, max_val + 10)
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return tmp_file.name


def cleanup_temp_file(filepath: str):
    """Remove temporary chart file."""
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except Exception:
        pass  # Ignore cleanup errors
