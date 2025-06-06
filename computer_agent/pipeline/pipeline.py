"""
Pipeline V1: Configuration Setup + YOLO/OCR Detection + Merging + Seraphine Grouping + Visualizations
Building the complete pipeline step by step - with intelligent ID tracking and JSON export
"""
import os
import time
import json
import cv2
import numpy as np
from functools import wraps
from PIL import Image
from datetime import datetime
from utils.yolo_detector import YOLODetector, YOLOConfig
from utils.ocr_detector import OCRDetector, OCRDetConfig
from utils.bbox_merger import BBoxMerger
from utils.beautiful_visualizer import BeautifulVisualizer
from utils.seraphine_processor import FinalSeraphineProcessor, convert_detections_to_seraphine_format
from utils.seraphine_generator import FinalGroupImageGenerator
import asyncio
from utils.gemini_integration import run_gemini_analysis, integrate_gemini_results
from utils.pipeline_exporter import save_enhanced_pipeline_json
from concurrent.futures import ThreadPoolExecutor
from utils.parallel_processor import ParallelProcessor
from utils.helpers import load_configuration, debug_print

# Import all the helper functions from pipeline_utils.py
from .pipeline_utils import (
    setup_detector_configs,
    load_image_opencv,
    convert_bgr_to_pil_for_ocr,
    assign_intelligent_ids,
    create_intelligent_merger,
    run_parallel_detection_and_merge,
    run_seraphine_grouping,
    convert_merged_to_seraphine_format,
    create_seraphine_id_mapping,
    create_visualizations,
    display_enhanced_pipeline_summary
)

async def run_pipeline(image_path, mode="debug", output_dir=None):
    """
    Run the complete pipeline on an image.
    
    Args:
        image_path (str): Path to the input image
        mode (str): "debug" for detailed output, "deploy_mcp" for production
        output_dir (str): Custom output directory path (optional)
    
    Returns:
        dict: Pipeline results including:
            - detection_results
            - seraphine_analysis
            - gemini_results
            - visualization_paths
            - json_path
    """
    pipeline_start = time.time()
    
    config = load_configuration()
    if not config:
        return None
    
    # Update output directory if provided
    if output_dir:
        config["output_dir"] = output_dir
    
    # Force disable ALL debug output in deploy mode
    if mode == "deploy_mcp":
        config.update({
            "yolo_enable_debug": False,
            "yolo_enable_timing": False,
            "ocr_enable_debug": False,
            "ocr_enable_timing": False,
            "seraphine_enable_debug": False,
            "seraphine_timing": False,
            "save_visualizations": False,
            "save_json": False,
            "save_gemini_visualization": False,
            "save_gemini_json": False,
        })
    
    debug_print("🚀 ENHANCED AI PIPELINE V1.2: Detection + Merging + Seraphine + Gemini + Export")
    debug_print("=" * 90)
    
    # Set up detector configs BEFORE using them
    yolo_config, ocr_config = setup_detector_configs(config)
    
    # Load and validate image
    img_bgr = load_image_opencv(image_path)
    if img_bgr is None:
        debug_print(f"❌ Error: Could not load image '{image_path}'")
        return None
    
    debug_print(f"📸 Image loaded: {img_bgr.shape[1]}x{img_bgr.shape[0]} pixels")
    
    try:
        # Step 1: Detection + Merging
        detection_results = run_parallel_detection_and_merge(img_bgr, yolo_config, ocr_config, config)
        
        # Step 2: Seraphine Grouping
        seraphine_analysis = run_seraphine_grouping(detection_results['merged_detections'], config)
        
        # Step 3: Generate Grouped Images
        grouped_image_paths = None
        if config.get("generate_grouped_images", True):
            debug_print("\n🖼️  Step 3: Generating Seraphine Grouped Images")
            
            output_dir = config.get("output_dir", "outputs")
            filename_base = os.path.splitext(os.path.basename(image_path))[0]
            
            final_group_generator = FinalGroupImageGenerator(
                output_dir=output_dir,
                save_mapping=False
            )
            
            grouped_image_paths = final_group_generator.create_grouped_images(
                image_path, 
                seraphine_analysis, 
                filename_base
            )
            
            debug_print(f"✅ Generated {len(grouped_image_paths)} grouped images")
        
        # Step 4: Gemini Analysis
        gemini_results = None
        if config.get("gemini_enabled", False):
            try:
                gemini_results = await run_gemini_analysis(
                    seraphine_analysis, grouped_image_paths, image_path, config
                )
                
                if gemini_results:
                    seraphine_analysis['original_merged_detections'] = detection_results['merged_detections']
                    seraphine_analysis = integrate_gemini_results(seraphine_analysis, gemini_results)
                    
            except Exception as e:
                debug_print(f"⚠️  Gemini analysis failed: {str(e)}")
        
        # Calculate total time
        total_time = time.time() - pipeline_start
        
        # Get icon count
        icon_count = gemini_results.get('total_icons_found', 0) if gemini_results else 0
        
        # MODE-SPECIFIC OUTPUTS
        if mode == "deploy_mcp":
            print(f"Pipeline completed in {total_time:.3f}s, found {icon_count} icons.")
            
            # Clean up output directory
            output_dir = config.get("output_dir", "outputs")
            if os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
                os.makedirs(output_dir, exist_ok=True)
            
            field_name = 'seraphine_gemini_groups' if gemini_results else 'seraphine_groups'
            
            # Create a copy of seraphine_analysis without the bbox_processor
            serializable_analysis = {k: v for k, v in seraphine_analysis.items() if k != 'bbox_processor'}
            
            return {
                'total_time': total_time,
                'total_icons_found': icon_count,
                field_name: serializable_analysis.get(field_name, serializable_analysis.get('analysis', {}))
            }
        
        else:  # DEBUG MODE
            # Step 5: Save JSON
            json_path = save_enhanced_pipeline_json(image_path, detection_results, seraphine_analysis, gemini_results, config)
            
            # Step 6: Create Visualizations
            visualization_paths = create_visualizations(image_path, detection_results, seraphine_analysis, config, gemini_results)
            
            # Summary
            display_enhanced_pipeline_summary(image_path, detection_results, seraphine_analysis, gemini_results, visualization_paths, json_path, config)
            
            # Create a copy of seraphine_analysis without the bbox_processor
            serializable_analysis = {k: v for k, v in seraphine_analysis.items() if k != 'bbox_processor'}
            
            return {
                'detection_results': detection_results,
                'seraphine_analysis': serializable_analysis,  # Use the serializable version
                'gemini_results': gemini_results,
                'grouped_image_paths': grouped_image_paths,
                'visualization_paths': visualization_paths,
                'json_path': json_path,
                'config': config,
                'total_time': total_time
            }
        
    except Exception as e:
        total_time = time.time() - pipeline_start
        
        if mode == "deploy_mcp":
            print(f"Pipeline failed after {total_time:.3f}s: {str(e)}")
        else:
            debug_print(f"❌ Error during pipeline execution: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return None

if __name__ == "__main__":
    # This allows the file to be run directly
    asyncio.run(run_pipeline("path/to/your/image.jpg"))
