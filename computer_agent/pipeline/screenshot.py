"""
Simple screenshot functionality that saves to output folder
"""
import os
import cv2
import numpy as np
from PIL import ImageGrab
from datetime import datetime

def take_screenshot(output_dir="outputs", suffix="none"):
    """
    Take a screenshot of the entire screen and save it to output folder.
    
    Args:
        output_dir (str): Directory to save screenshots (default: "outputs")
    
    Returns:
        str: Relative path to the saved screenshot
    """
    try:
        # Take screenshot using PIL
        screenshot = ImageGrab.grab()
        
        # Convert PIL Image to OpenCV format (BGR)
        screenshot = np.array(screenshot)
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix == "none":    
            filename = f"screenshot_{timestamp}.jpg"
        else:
            filename = f"screenshot_{timestamp}_{suffix}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        # Save screenshot
        cv2.imwrite(filepath, screenshot)
        print(f"📸 Screenshot saved: {filepath}")
        
        # Return relative path
        return filepath
        
    except Exception as e:
        print(f"❌ Error taking screenshot: {str(e)}")
        return None
