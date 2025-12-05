"""
Portfolio Export Module
=======================
Generates a comprehensive PowerPoint deck for a selected portfolio of sites.
Includes:
1. Portfolio Summary (Metrics, Charts, Rankings)
2. State Analysis (if applicable)
3. Individual Site Profiles (Site Profile, Capacity, Critical Path, etc.)
"""

import copy
import io
from typing import List, Dict, Any
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
except ImportError:
    Presentation = None

from .pptx_export import (
    JLL_COLORS, SiteProfileData, CapacityTrajectory, PhaseData, ScoreAnalysis,
    TEMPLATE_SLIDES, ExportConfig,
    generate_capacity_trajectory_chart, generate_critical_path_chart,
    generate_score_radar_chart, generate_score_summary_chart,
    generate_market_analysis_chart,
    populate_site_profile_table, update_overview_textbox,
    find_and_replace_text, build_replacements,
    add_header_bar, add_footer, set_slide_background_white,
    add_critical_path_text, add_score_breakdown_text, add_market_text
)
from .program_tracker import calculate_portfolio_summary, ProgramTrackerData


def copy_slide_from_external(source_slide, dest_prs):
    """
    Copy a slide from a source presentation to the destination presentation.
    Handles TextBoxes, AutoShapes, Pictures, and Tables.
    """
    # Create a blank slide
    blank_layout = dest_prs.slide_layouts[6] 
    dest_slide = dest_prs.slides.add_slide(blank_layout)
    
    # Copy shapes
    for shape in source_slide.shapes:
        # 1. Pictures
        if shape.shape_type == 13: # PICTURE
            try:
                blob = shape.image.blob
                dest_slide.shapes.add_picture(io.BytesIO(blob), shape.left, shape.top, shape.width, shape.height)
            except Exception as e:
                print(f"Failed to copy picture: {e}")
        
        # 2. Tables
        elif shape.shape_type == 19: # TABLE
            try:
                rows = len(shape.table.rows)
                cols = len(shape.table.columns)
                new_table = dest_slide.shapes.add_table(
                    rows, cols, shape.left, shape.top, shape.width, shape.height
                ).table
                
                for r in range(rows):
                    for c in range(cols):
                        source_cell = shape.table.cell(r, c)
                        dest_cell = new_table.cell(r, c)
                        
                        # Copy text and simple formatting
                        dest_cell.text = source_cell.text
                        
                        # Copy paragraph alignment/font from first paragraph if exists
                        if source_cell.text_frame.paragraphs:
                            p_source = source_cell.text_frame.paragraphs[0]
                            p_dest = dest_cell.text_frame.paragraphs[0]
                            p_dest.alignment = p_source.alignment
                            
                            if p_source.runs:
                                r_source = p_source.runs[0]
                                if p_dest.runs:
                                    r_dest = p_dest.runs[0]
                                    r_dest.font.size = r_source.font.size
                                    r_dest.font.bold = r_source.font.bold
                                    try:
                                        r_dest.font.color.rgb = r_source.font.color.rgb
                                    except:
                                        pass
            except Exception as e:
                print(f"Failed to copy table: {e}")

        # 3. TextBoxes and AutoShapes
        elif shape.shape_type == MSO_SHAPE.AUTO_SHAPE or shape.shape_type == MSO_SHAPE.TEXT_BOX:
            try:
                new_shape = dest_slide.shapes.add_shape(
                    shape.auto_shape_type,
                    shape.left, shape.top, shape.width, shape.height
                )
                
                # Copy fill (basic)
                if shape.fill.type == 1: # Solid
                    try:
                        new_shape.fill.solid()
                        new_shape.fill.fore_color.rgb = shape.fill.fore_color.rgb
                    except:
                        pass
                
                # Copy text
                if shape.has_text_frame:
                    new_shape.text_frame.clear()
                    for paragraph in shape.text_frame.paragraphs:
                        new_p = new_shape.text_frame.add_paragraph()
                        new_p.text = paragraph.text
                        new_p.alignment = paragraph.alignment
                        
                        # Copy runs
                        for run in paragraph.runs:
                            new_run = new_p.add_run()
                            new_run.text = run.text
                            new_run.font.name = run.font.name
                            new_run.font.size = run.font.size
                            new_run.font.bold = run.font.bold
                            new_run.font.italic = run.font.italic
                            try:
                                new_run.font.color.rgb = run.font.color.rgb
                            except:
                                pass
            except Exception as e:
                print(f"Failed to copy shape: {e}")


def generate_portfolio_export(
    sites: Dict[str, Dict],
    template_path: str,
    output_path: str,
    config: ExportConfig = None
) -> str:
    """
    Generate a comprehensive portfolio export by merging individual site decks.
    This ensures exact fidelity to the individual site exports.
    """
    if not Presentation:
        raise ImportError("python-pptx is required")
    
    print(f"[DEBUG] Generating Portfolio Export for {len(sites)} sites")
    
    # 1. Create Master Presentation
    master_prs = Presentation(template_path)
    
    # Clear existing slides to start fresh (but keep layouts)
    xml_slides = master_prs.slides._sldIdLst  
    slides = list(xml_slides)
    for s in slides:
        xml_slides.remove(s)
        
    # 2. Add Portfolio Summary Slides
    # -----------------------------
    # Title Slide
    layout = master_prs.slide_layouts[0] 
    slide = master_prs.slides.add_slide(layout)
    
    # Set Title
    if slide.shapes.title:
        slide.shapes.title.text = "Portfolio Overview"
    
    # Set Subtitle
    subtitle_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
    if len(slide.placeholders) > 1:
        try:
            slide.placeholders[1].text = subtitle_text
        except:
            pass
    else:
        # Fallback textbox
        left = Inches(1)
        top = Inches(4)
        width = Inches(8)
        height = Inches(1)
        txBox = slide.shapes.add_textbox(left, top, width, height)
        p = txBox.text_frame.paragraphs[0]
        p.text = subtitle_text
        p.font.size = Pt(24)
        p.font.color.rgb = RGBColor(128, 128, 128)
        p.alignment = PP_ALIGN.CENTER
    
    # Metrics Slide
    add_portfolio_metrics_slide(master_prs, sites)
    
    # Ranking Slide
    add_portfolio_ranking_slide(master_prs, sites)
    
    # 3. Generate and Merge Individual Site Decks
    # -------------------------------------------
    from .pptx_export import export_site_to_pptx
    import tempfile
    import os
    
    for site_id, site_data in sites.items():
        print(f"[DEBUG] Processing site: {site_data.get('name', site_id)}")
        
        # Create temp file for this site
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            # Generate individual deck (The "Source of Truth")
            export_site_to_pptx(site_data, template_path, tmp_path, config)
            
            # Merge into master
            source_prs = Presentation(tmp_path)
            
            # We skip the first slide (Title) and the last slide (Thank You)
            # Assuming standard structure: Title, Profile, ..., Thank You
            # If only 1 slide, copy it.
            if len(source_prs.slides) > 1:
                slides_to_copy = source_prs.slides[1:-1] # Skip first and last
            else:
                slides_to_copy = source_prs.slides
                
            for source_slide in slides_to_copy:
                copy_slide_from_external(source_slide, master_prs, source_prs)
                
        except Exception as e:
            print(f"[ERROR] Failed to process site {site_id}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    # 4. Save Master
    master_prs.save(output_path)
    return output_path


def copy_slide_from_external(source_slide, dest_prs, source_prs):
    """
    Copy a slide from a source presentation to a destination presentation.
    """
    # 1. Find matching layout
    # We assume source and dest use the same template, so layouts match by index
    layout_index = 6 # Default to blank
    try:
        # Try to find the index of the source layout in the source master
        # This is tricky because slide_layout doesn't store its index directly easily
        # But we can iterate source_prs.slide_layouts
        for i, layout in enumerate(source_prs.slide_layouts):
            if source_slide.slide_layout.name == layout.name: # Match by name
                layout_index = i
                break
    except:
        pass
        
    dest_layout = dest_prs.slide_layouts[layout_index]
    dest_slide = dest_prs.slides.add_slide(dest_layout)
    
    # 2. Copy Shapes
    for shape in source_slide.shapes:
        # 1. Pictures (Type 13)
        if shape.shape_type == 13: 
            try:
                blob = shape.image.blob
                dest_slide.shapes.add_picture(io.BytesIO(blob), shape.left, shape.top, shape.width, shape.height)
            except: pass
            
        # 2. Tables (Type 19)
        elif shape.shape_type == 19:
            try:
                rows = len(shape.table.rows)
                cols = len(shape.table.columns)
                new_table = dest_slide.shapes.add_table(rows, cols, shape.left, shape.top, shape.width, shape.height).table
                # Copy content
                for r in range(rows):
                    for c in range(cols):
                        source_cell = shape.table.cell(r, c)
                        dest_cell = new_table.cell(r, c)
                        dest_cell.text = source_cell.text
                        # Copy basic font props from first paragraph
                        if source_cell.text_frame.paragraphs:
                            p_src = source_cell.text_frame.paragraphs[0]
                            p_dst = dest_cell.text_frame.paragraphs[0]
                            if p_src.runs:
                                r_src = p_src.runs[0]
                                if p_dst.runs:
                                    r_dst = p_dst.runs[0]
                                    r_dst.font.size = r_src.font.size
                                    r_dst.font.bold = r_src.font.bold
                                    try:
                                        r_dst.font.color.rgb = r_src.font.color.rgb
                                    except: pass
                                    
                        # Copy cell fill if possible (basic solid fill)
                        try:
                            if source_cell.fill.type == 1: # Solid
                                dest_cell.fill.solid()
                                dest_cell.fill.fore_color.rgb = source_cell.fill.fore_color.rgb
                        except: pass
            except: pass
            
        # 3. AutoShapes (1) / TextBoxes (17) / Placeholders (14)
        elif shape.shape_type == 1 or shape.shape_type == 17 or shape.shape_type == 14:
            try:
                # For placeholders, we treat them as auto shapes to preserve content
                # We don't want to link them to the new layout's placeholders because that might reset them
                shape_type = shape.auto_shape_type if hasattr(shape, 'auto_shape_type') else 1 
                
                new_shape = dest_slide.shapes.add_shape(shape_type, shape.left, shape.top, shape.width, shape.height)
                
                # Copy text
                if shape.has_text_frame:
                    new_shape.text_frame.clear()
                    for p in shape.text_frame.paragraphs:
                        new_p = new_shape.text_frame.add_paragraph()
                        new_p.text = p.text
                        new_p.alignment = p.alignment
                        new_p.level = p.level
                        
                        # Copy runs
                        for r in p.runs:
                            new_r = new_p.add_run()
                            new_r.text = r.text
                            new_r.font.size = r.font.size
                            new_r.font.bold = r.font.bold
                            new_r.font.italic = r.font.italic
                            new_r.font.underline = r.font.underline
                            try:
                                new_r.font.color.rgb = r.font.color.rgb
                            except: pass
                            try:
                                if r.font.color.type == 2: # Theme color
                                    new_r.font.color.theme_color = r.font.color.theme_color
                            except: pass

                # Copy fill
                if shape.fill.type == 1:
                    new_shape.fill.solid()
                    try:
                        new_shape.fill.fore_color.rgb = shape.fill.fore_color.rgb
                    except: pass
                    
                # Copy line
                if shape.line.fill.type == 1: # Solid line
                    try:
                        new_shape.line.color.rgb = shape.line.color.rgb
                        new_shape.line.width = shape.line.width
                    except: pass
            except: pass
            
    return dest_slide


def add_portfolio_metrics_slide(prs, sites, index=None):
    """Add slide with portfolio metrics and charts."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    
    # Move slide if index is specified
    if index is not None:
        xml_slides = prs.slides._sldIdLst
        slides = list(xml_slides)
        xml_slides.remove(slides[-1])
        xml_slides.insert(index, slides[-1])
    
    # Header
    add_header_bar(slide, "Portfolio Summary", Inches, Pt, RGBColor)
    
    # Calculate metrics
    site_list = []
    for s in sites.values():
        site_list.append(s)
    summary = calculate_portfolio_summary(site_list)
    
    # Metrics Text
    left = Inches(0.5)
    top = Inches(1.5)
    width = Inches(3.0)
    height = Inches(5.0)
    
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    
    metrics = [
        ("Total Sites", f"{summary['site_count']}"),
        ("Total Fee Potential", f"${summary['total_potential']:,.0f}"),
        ("Weighted Pipeline", f"${summary['total_weighted']:,.0f}"),
        ("Avg Probability", f"{summary['avg_probability']:.1%}"),
    ]
    
    for label, value in metrics:
        p = tf.add_paragraph()
        p.text = label
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = RGBColor(26, 43, 74)
        
        p = tf.add_paragraph()
        p.text = value
        p.font.size = Pt(24)
        p.font.color.rgb = RGBColor(46, 125, 50) # Green
        p.space_after = Pt(20)

    # Charts (Generated via Matplotlib)
    # 1. Pipeline by Stage
    fig, ax = plt.subplots(figsize=(6, 4))
    stages = list(summary['by_stage'].keys())
    values = [sum(s['weighted'] for s in summary['by_stage'][stage]) for stage in stages]
    
    ax.bar(stages, values, color=[JLL_COLORS['teal'], JLL_COLORS['amber'], JLL_COLORS['light_blue'], JLL_COLORS['green']])
    ax.set_title('Weighted Value by Stage', fontsize=12, fontweight='bold', color=JLL_COLORS['dark_blue'])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.0f}M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png', dpi=150)
    img_stream.seek(0)
    plt.close()
    
    slide.shapes.add_picture(img_stream, Inches(4.0), Inches(1.5), Inches(5.0), Inches(3.5))
    

def add_portfolio_ranking_slide(prs, sites, index=None):
    """Add slide with ranking table."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    
    # Move slide if index is specified
    if index is not None:
        xml_slides = prs.slides._sldIdLst
        slides = list(xml_slides)
        xml_slides.remove(slides[-1])
        xml_slides.insert(index, slides[-1])
    
    add_header_bar(slide, "Portfolio Rankings", Inches, Pt, RGBColor)
    
    # Sort sites by score
    ranked_sites = []
    for sid, s in sites.items():
        score = 0
        if 'profile' in s and isinstance(s['profile'], SiteProfileData):
            score = s['profile'].ratings.get('overall_score', 0) # This might be wrong place
        # Try to get score from scoring engine output if available
        # For now, let's assume 'score' key exists or calculate it
        # Simplified:
        ranked_sites.append((s.get('name', sid), s.get('total_fee_potential', 0), s.get('probability', 0)))
        
    # Sort by Fee * Prob (Weighted)
    ranked_sites.sort(key=lambda x: x[1]*x[2], reverse=True)
    
    # Table
    rows = min(len(ranked_sites) + 1, 11) # Header + top 10
    cols = 4
    left = Inches(1.0)
    top = Inches(1.5)
    width = Inches(11.3)
    height = Inches(0.5 * rows)
    
    table = slide.shapes.add_table(rows, cols, left, top, width, height).table
    
    # Header
    headers = ["Site Name", "Fee Potential", "Probability", "Weighted Value"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(26, 43, 74)
        cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
        cell.text_frame.paragraphs[0].font.bold = True
        
    # Data
    for i, (name, fee, prob) in enumerate(ranked_sites[:10]):
        row = i + 1
        table.cell(row, 0).text = name
        table.cell(row, 1).text = f"${fee:,.0f}"
        table.cell(row, 2).text = f"{prob:.1%}"
        table.cell(row, 3).text = f"${fee*prob:,.0f}"


def add_capacity_slide(prs, site_data, replacements):
    """Add Capacity Trajectory slide."""
    from .pptx_export import generate_capacity_trajectory_chart, CapacityTrajectory, PhaseData, convert_phase_data
    import tempfile
    import os
    
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    add_header_bar(slide, "Capacity Trajectory", Inches, Pt, RGBColor)
    
    # Generate Chart
    traj_data = site_data.get('capacity_trajectory', site_data.get('schedule', {}))
    trajectory = (CapacityTrajectory.from_dict(traj_data) if traj_data else
                  CapacityTrajectory.generate_default(
                      site_data.get('target_mw', 600),
                      site_data.get('phase1_mw'),
                      site_data.get('start_year', 2028)))
    
    # Extract Phases
    phases = []
    phase_data = site_data.get('phases', [])
    if phase_data:
        for idx, pd in enumerate(phase_data, 1):
            if isinstance(pd, dict):
                converted_pd = convert_phase_data(pd)
                if 'phase_num' not in converted_pd:
                    converted_pd['phase_num'] = idx
                phases.append(PhaseData(**converted_pd))
            else:
                phases.append(pd)
                      
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        chart_path = tmp.name
        
    try:
        generate_capacity_trajectory_chart(
            trajectory, 
            site_data.get('name', 'Site'), 
            chart_path, 
            phases=phases
        )
        slide.shapes.add_picture(chart_path, Inches(0.5), Inches(1.5), Inches(12.33), Inches(5.5))
    except Exception as e:
        print(f"[ERROR] Failed to generate capacity chart: {e}")
    finally:
        if os.path.exists(chart_path):
            os.unlink(chart_path)


def add_infrastructure_slide(prs, site_data, replacements):
    """Add Infrastructure slide."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    add_header_bar(slide, "Infrastructure Analysis", Inches, Pt, RGBColor)
    
    # Placeholder content
    left = Inches(1)
    top = Inches(2)
    width = Inches(11)
    height = Inches(4)
    
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.text = "Infrastructure Details"
    p = tf.add_paragraph()
    p.text = f"Substation: {site_data.get('substation', 'TBD')}"
    p = tf.add_paragraph()
    p.text = f"Transmission Line: {site_data.get('transmission_line', 'TBD')}"


def add_market_slide(prs, site_data, replacements):
    """Add Market Analysis slide."""
    from .pptx_export import generate_market_analysis_chart, add_market_text
    import tempfile
    import os
    
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    add_header_bar(slide, "Market Analysis", Inches, Pt, RGBColor)
    
    # Chart
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        chart_path = tmp.name
        
    try:
        generate_market_analysis_chart(
            site_data, 
            site_data.get('name', 'Site'), 
            chart_path
        )
        slide.shapes.add_picture(chart_path, Inches(0.5), Inches(1.5), Inches(6.0), Inches(4.5))
    except Exception as e:
        print(f"[ERROR] Failed to generate market chart: {e}")
    finally:
        if os.path.exists(chart_path):
            os.unlink(chart_path)
        
    # Text
    add_market_text(slide, site_data)


def add_score_slide(prs, site_data, replacements):
    """Add Score Analysis slide."""
    from .pptx_export import generate_score_summary_chart, add_score_breakdown_text, ScoreAnalysis
    import tempfile
    import os
    
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)
    add_header_bar(slide, "Site Scoring Analysis", Inches, Pt, RGBColor)
    
    # Score Data
    score_data = None
    if 'profile' in site_data and hasattr(site_data['profile'], 'ratings'):
         score_data = ScoreAnalysis.from_dict(site_data['profile'].ratings)
    
    if score_data:
        # Chart
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            chart_path = tmp.name
            
        try:
            generate_score_summary_chart(
                score_data, 
                site_data.get('name', 'Site'), 
                chart_path
            )
            slide.shapes.add_picture(chart_path, Inches(0.5), Inches(1.5), Inches(6.0), Inches(4.5))
        except Exception as e:
            print(f"[ERROR] Failed to generate score chart: {e}")
        finally:
            if os.path.exists(chart_path):
                os.unlink(chart_path)
            
        # Text
        add_score_breakdown_text(slide, score_data)
    else:
        txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(10), Inches(1))
        txBox.text_frame.text = "No scoring data available for this site."
