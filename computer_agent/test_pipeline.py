"""
Test OCR detection and Gemini analysis functionality
"""
import os
import asyncio
import json
from datetime import datetime
from PIL import Image
from utils.output_manager import get_output_folder
from pipeline.screenshot import take_screenshot
from pipeline.pipeline_test import run_pipeline_test

async def run_pipeline():
    """
    Takes a screenshot and runs the full pipeline test
    """
    print("\n🧪 Starting Pipeline Test")
    print("=" * 50)
    
    # Generate session ID with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"pipeline_test_{timestamp}"
    
    # Create session-specific output folder
    output_folder = get_output_folder(session_id, base_dir="pipeline_test_outputs")
    print(f"📁 Using output folder: {output_folder}")
    
    # Take screenshot
    print("📸 Taking screenshot...")
    screenshot_path = take_screenshot(output_dir=str(output_folder))
    if screenshot_path is None:
        print("❌ Failed to take screenshot")
        return False
    
    try:
        # Run pipeline with screenshot
        print("\n🔄 Running pipeline...")
        results = await run_pipeline_test(screenshot_path, mode="debug", output_dir=str(output_folder))
        
        if results is None:
            print("❌ Pipeline returned None")
            return False
        
        # Print success summary
        print("\n✅ Pipeline Test Completed Successfully!")
        print("=" * 50)
        print(f"📊 Results Summary:")
        print(f"  - Session ID: {session_id}")
        print(f"  - Output Folder: {output_folder}")
        print(f"  - Screenshot saved: {screenshot_path}")
        print(f"  - YOLO Detections: {len(results['detection_results']['yolo_detections'])}")
        print(f"  - OCR Detections: {len(results['detection_results']['ocr_detections'])}")
        print(f"  - Merged Detections: {len(results['detection_results']['merged_detections'])}")
        print(f"  - Seraphine Groups: {results['seraphine_analysis']['analysis']['total_groups']}")
        print(f"  - Generated Files: {len(results['visualization_paths'])}")
        print(f"  - JSON Output: {results['json_path']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in pipeline test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(run_pipeline())
