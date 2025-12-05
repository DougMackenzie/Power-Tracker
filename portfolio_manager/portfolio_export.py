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
    Generate a comprehensive portfolio export by iterating through sites and 
    generating slides directly in the master presentation.
    This ensures exact fidelity to the individual site exports while keeping everything in one file.
    """
    if not Presentation:
        raise ImportError("python-pptx is required")
    
    print(f"[DEBUG] Generating Portfolio Export for {len(sites)} sites")
    
    # 1. Load Master Presentation
    prs = Presentation(template_path)
    
    # 2. Add Portfolio Summary Slides (At the beginning)
    # -------------------------------------------------
    # The template likely starts with Title (0), Profile (1), Boundary (2), Topo (3), Thank You (4)
    # We want to insert our summary slides after the Title (0).
    
    # Update Title Slide (Index 0)
    title_slide = prs.slides[0]
    if title_slide.shapes.title:
        title_slide.shapes.title.text = "Portfolio Overview"
    
    # Subtitle
    subtitle_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
    if len(title_slide.placeholders) > 1:
        try:
            title_slide.placeholders[1].text = subtitle_text
        except:
            pass
            
    # Add Metrics Slide (Index 1)
    add_portfolio_metrics_slide(prs, sites, index=1)
    
    # Add Ranking Slide (Index 2)
    add_portfolio_ranking_slide(prs, sites, index=2)
    
    # Now the original template slides are shifted:
    # Title: 0
    # Metrics: 1
    # Ranking: 2
    # Profile: 3 (was 1)
    # Boundary: 4 (was 2)
    # Topo: 5 (was 3)
    # Thank You: 6 (was 4)
    
    template_indices = {
        'profile': 3,
        'boundary': 4,
        'topo': 5
    }
    
    # 3. Generate Slides for Each Site
    # --------------------------------
    from .pptx_export import (
        populate_slide, build_replacements, SiteProfileData,
        generate_capacity_trajectory_chart, generate_critical_path_chart,
        generate_score_summary_chart, generate_market_analysis_chart,
        add_critical_path_text, add_score_breakdown_text, add_market_text,
        convert_phase_data, PhaseData, CapacityTrajectory, ScoreAnalysis
    )
    
    # We append new slides to the end
    for site_id, site_data in sites.items():
        print(f"[DEBUG] Processing site: {site_data.get('name', site_id)}")
        
        # Prepare Data
        replacements = build_replacements(site_data, config)
        
        # Get Profile Data
        profile_data = None
        if 'profile' in site_data:
            p = site_data['profile']
            if hasattr(p, 'overview') and hasattr(p, 'to_description_dict'):
                profile_data = p
            elif isinstance(p, dict):
                profile_data = SiteProfileData.from_dict(p)
        
        # --- 1. Site Profile Slide ---
        # Clone the template profile slide
        source_profile_idx = template_indices['profile']
        profile_slide = duplicate_slide_in_place(prs, source_profile_idx)
        
        # Populate Profile Slide using SHARED LOGIC
        populate_slide(profile_slide, site_data, profile_data, replacements, config, slide_type='site_profile')

        # --- 2. Site Boundary Slide ---
        if config.include_site_boundary:
            source_boundary_idx = template_indices['boundary']
            boundary_slide = duplicate_slide_in_place(prs, source_boundary_idx)
            # Populate Boundary Slide using SHARED LOGIC
            populate_slide(boundary_slide, site_data, profile_data, replacements, config, slide_type='site_boundary')

        # --- 3. Topography Slide ---
        if config.include_topography:
            source_topo_idx = template_indices['topo']
            topo_slide = duplicate_slide_in_place(prs, source_topo_idx)
            # Populate Topography Slide using SHARED LOGIC
            populate_slide(topo_slide, site_data, profile_data, replacements, config, slide_type='topography')
            
        # --- 4. Capacity Trajectory (New Slide) ---
        if config.include_capacity_trajectory:
            add_capacity_slide(prs, site_data, replacements)

        # --- 5. Infrastructure (New Slide) ---
        if config.include_infrastructure:
            add_infrastructure_slide(prs, site_data, replacements)
            
        # --- 6. Market Analysis (New Slide) ---
        if config.include_market_analysis:
            add_market_slide(prs, site_data, replacements)
            
        # --- 7. Score Analysis (New Slide) ---
        if config.include_score_analysis:
            add_score_slide(prs, site_data, replacements)

    # 4. Cleanup
    # ----------
    # Delete the original template slides (which are now in the middle)
    # We must delete from highest index to lowest to avoid shifting issues
    indices_to_delete = sorted(template_indices.values(), reverse=True)
    xml_slides = prs.slides._sldIdLst
    for idx in indices_to_delete:
        if idx < len(prs.slides):
            xml_slides.remove(xml_slides[idx])
            
    # Move Thank You slide to end (it was at index 6, but indices shifted after deletion)
    # Actually, if we deleted 3, 4, 5, the Thank You slide (was 6) is now at 3.
    # We want it at the very end.
    # Let's just find the Thank You slide by content or assume it's the one after the deleted block.
    # Easier: Just move the last slide (if it's Thank You) to the end?
    # Or, we can just let it be. If we deleted the templates, the Thank You slide is likely in the middle now if we appended new slides.
    # Wait, we appended new slides to the END.
    # So the order was: [Title, Metrics, Ranking, Profile, Boundary, Topo, ThankYou, Site1Slides..., Site2Slides...]
    # We deleted Profile, Boundary, Topo.
    # Order is now: [Title, Metrics, Ranking, ThankYou, Site1Slides..., Site2Slides...]
    # We want ThankYou at the end.
    
    # Find Thank You slide (it should be at index 3 now)
    thank_you_idx = 3
    if thank_you_idx < len(prs.slides):
        # Move it to end
        xml_slides = prs.slides._sldIdLst
        slides = list(xml_slides)
        thank_you_slide = slides[thank_you_idx]
        xml_slides.remove(thank_you_slide)
        xml_slides.append(thank_you_slide)
            
    # 5. Save
    prs.save(output_path)
    return output_path


def duplicate_slide_in_place(prs, index):
    """
    Duplicate a slide within the same presentation using XML cloning for maximum fidelity.
    """
    import copy
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    
    source = prs.slides[index]
    layout = source.slide_layout
    dest = prs.slides.add_slide(layout)
    
    # CRITICAL: Clear existing shapes from the new slide!
    for shape in list(dest.shapes):
        sp = shape._element
        sp.getparent().remove(sp)
    
    # Copy shapes
    for shape in source.shapes:
        # 1. Pictures (Type 13) - Must use API to handle relationships (rId)
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE: 
            try:
                blob = shape.image.blob
                dest.shapes.add_picture(io.BytesIO(blob), shape.left, shape.top, shape.width, shape.height)
            except Exception as e:
                print(f"[WARNING] Failed to copy picture: {e}")
                
        # 2. Everything else (Tables, TextBoxes, AutoShapes, Groups) - Use XML Clone
        # This preserves EXACT formatting (borders, shading, fonts, etc.)
        else:
            try:
                new_el = copy.deepcopy(shape.element)
                dest.shapes._spTree.append(new_el)
            except Exception as e:
                print(f"[WARNING] Failed to clone shape XML: {e}")
            
    return dest


def replace_images_with_placeholders(slide, site_data, label="Map Placeholder"):
    """Replace images with gray placeholders."""
    
    shapes_to_replace = []
    for shape in slide.shapes:
        # Identify images to replace
        # Type 13 = Picture
        if shape.shape_type == 13:
            # Heuristic: 
            # 1. If label is "Map Placeholder" (Profile Slide), replace images on right (>4 inches)
            # 2. If label is "Site Boundary" or "Topography", replace ANY large image (>4 inches width)
            
            if label == "Map Placeholder":
                if shape.left > Inches(4):
                    shapes_to_replace.append(shape)
            else:
                # For boundary/topo, replace main images
                if shape.width > Inches(4):
                    shapes_to_replace.append(shape)
                
    for shape in shapes_to_replace:
        left, top, width, height = shape.left, shape.top, shape.width, shape.height
        # Remove
        sp = shape._element
        sp.getparent().remove(sp)
        
        # Add Placeholder
        rect = slide.shapes.add_shape(1, left, top, width, height) # 1 = Rectangle
        rect.fill.solid()
        rect.fill.fore_color.rgb = RGBColor(240, 240, 240)
        rect.line.color.rgb = RGBColor(200, 200, 200)
        
        tf = rect.text_frame
        tf.text = label
        tf.paragraphs[0].font.color.rgb = RGBColor(100, 100, 100)
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER


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
