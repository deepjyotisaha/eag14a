import os
from datetime import datetime
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image

def take_screenshot():
    # Ensure temp_media directory exists
    temp_media_dir = os.path.join(os.path.dirname(__file__), 'temp_media')
    os.makedirs(temp_media_dir, exist_ok=True)

    # Get screen dimensions
    width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

    # Create device context and bitmap
    hdesktop = win32gui.GetDesktopWindow()
    hdc = win32gui.GetWindowDC(hdesktop)
    srcdc = win32ui.CreateDCFromHandle(hdc)
    memdc = srcdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(srcdc, width, height)
    memdc.SelectObject(bmp)
    memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)

    # Convert to PIL Image
    bmpinfo = bmp.GetInfo()
    bmpstr = bmp.GetBitmapBits(True)
    img = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1)

    # Save with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'screenshot_{timestamp}.png'
    filepath = os.path.join(temp_media_dir, filename)
    img.save(filepath)

    # Cleanup
    memdc.DeleteDC()
    win32gui.DeleteObject(bmp.GetHandle())
    win32gui.ReleaseDC(hdesktop, hdc)

    return filepath
