"""
Test file for the pipeline module
"""
import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import pipeline and screenshot functionality
from pipeline import run_pipeline
from screenshot import take_screenshot
from utils.output_manager import get_output_folder

async def test_pipeline():
    """Test the pipeline functionality"""
    print("\n🧪 Starting Pipeline Test")
    print("=" * 50)
    
    # Test 1: With image path
    image_path = "images/edge_canvas.png"
    print(f"📸 Testing with image path: {image_path}")
    
    try:
        # Create session-specific output folder for image test
        image_session_id = f"image_test_{datetime.now().strftime('%H%M%S')}"
        image_output_folder = get_output_folder(image_session_id)
        print(f"📁 Using output folder for image test: {image_output_folder}")
        
        # Run pipeline with image path and custom output folder
        results = await run_pipeline(image_path, mode="debug", output_dir=str(image_output_folder))
        
        # Basic validation
        if results is None:
            print("❌ Test Failed: Pipeline returned None")
            return False
            
        # Check required components
        required_keys = ['detection_results', 'seraphine_analysis', 'visualization_paths', 'json_path']
        for key in required_keys:
            if key not in results:
                print(f"❌ Test Failed: Missing {key} in results")
                return False
        
        # Check output files
        if not os.path.exists(results['json_path']):
            print(f"❌ Test Failed: JSON file not created at {results['json_path']}")
            return False
            
        for name, path in results['visualization_paths'].items():
            if not os.path.exists(path):
                print(f"❌ Test Failed: Visualization file not created: {name} at {path}")
                return False
        
        # Test 2: With screenshot
        print("\n📸 Testing with screenshot")
        
        # Create new session-specific output folder for screenshot test
        screenshot_session_id = f"screenshot_test_{datetime.now().strftime('%H%M%S')}"
        screenshot_output_folder = get_output_folder(screenshot_session_id)
        print(f"📁 Using output folder for screenshot test: {screenshot_output_folder}")
        
        # Take screenshot in the new output folder
        screenshot_path = take_screenshot(output_dir=str(screenshot_output_folder))
        if screenshot_path is None:
            print("❌ Test Failed: Could not take screenshot")
            return False
            
        # Run pipeline with screenshot using its own output folder
        screenshot_results = await run_pipeline(screenshot_path, mode="debug", output_dir=str(screenshot_output_folder))
        
        if screenshot_results is None:
            print("❌ Test Failed: Pipeline returned None for screenshot")
            return False
            
        # Print success summary
        print("\n✅ Test Passed Successfully!")
        print("=" * 50)
        print(f"📊 Results Summary:")
        print(f"  - YOLO Detections: {len(results['detection_results']['yolo_detections'])}")
        print(f"  - OCR Detections: {len(results['detection_results']['ocr_detections'])}")
        print(f"  - Merged Detections: {len(results['detection_results']['merged_detections'])}")
        print(f"  - Seraphine Groups: {results['seraphine_analysis']['analysis']['total_groups']}")
        print(f"  - Generated Files: {len(results['visualization_paths'])}")
        print(f"  - JSON Output: {results['json_path']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test Failed with error: {str(e)}")
        return False

async def test_invalid_image():
    """Test pipeline with invalid image"""
    print("\n🧪 Testing Invalid Image Handling")
    print("=" * 50)
    
    try:
        results = await run_pipeline("nonexistent_image.jpg")
        if results is None:
            print("✅ Test Passed: Pipeline correctly handled invalid image")
            return True
        else:
            print("❌ Test Failed: Pipeline should return None for invalid image")
            return False
    except Exception as e:
        print(f"❌ Test Failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    # Run tests
    print("🚀 Starting Pipeline Tests")
    print("=" * 50)
    
    # Run main test
    main_test_result = asyncio.run(test_pipeline())
    
    # Run invalid image test
    #invalid_test_result = asyncio.run(test_invalid_image())
    
    # Print final summary
    print("\n Test Summary")
    print("=" * 50)
    print(f"Main Pipeline Test: {'✅ Passed' if main_test_result else '❌ Failed'}")
    #print(f"Invalid Image Test: {'✅ Passed' if invalid_test_result else '❌ Failed'}")
    
    if main_test_result:
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n⚠️ Some tests failed. Please check the output above.")
