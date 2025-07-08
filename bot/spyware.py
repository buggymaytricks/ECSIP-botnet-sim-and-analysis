import os
import pyperclip
from PIL import ImageGrab
from io import BytesIO
import tempfile
import time
import platform

def utc_now():
    """Returns timestamp safe for filenames on both Windows and Linux"""
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S_UTC", time.gmtime())
    return timestamp

def log_clipboard():
    try:
        content = pyperclip.paste()
        if content:
            return f"[✓] Clipboard captured: {content[:100]}"  # First 100 chars
        return "[x] Clipboard is empty"
    except Exception as e:
        return f"[!] Clipboard error: {e}"
    
def take_screenshot():
    try:
        screenshot = ImageGrab.grab()
        timestamp = utc_now()
        
        # Handle temp directory paths cross-platform
        temp_dir = tempfile.gettempdir()
        
        # Create filename safe for both OSes
        filename = f"screenshot_{timestamp}.png"
        if platform.system() == "Windows":
            filename = filename.replace(":", "-")  # Extra safety for Windows
            
        file_path = os.path.join(temp_dir, filename)
        
        # Save the screenshot
        screenshot.save(file_path)
        
        # Optional: Convert to base64 (if needed)
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        
        return f"[✓] Screenshot saved at: {file_path}"
    except Exception as e:
        return f"[!] Screenshot error: {e}"

def main():
    cb = log_clipboard()
    ss = take_screenshot()
    return f"{cb}\n{ss}"
