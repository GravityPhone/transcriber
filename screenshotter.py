import os
import time
import platform
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from mss import mss

def create_session_folder():
    base_folder = "screenshot_sessions"
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    
    session_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_folder = os.path.join(base_folder, f"session_{session_timestamp}")
    os.makedirs(session_folder)
    return session_folder

def select_monitors():
    with mss() as sct:
        monitors = sct.monitors[1:]  # Exclude the "all in one" monitor
        print("Available monitors:")
        for i, m in enumerate(monitors, 1):
            print(f"{i}. Monitor {i}: {m['width']}x{m['height']}")
        
        while True:
            selection = input("Enter the numbers of the monitors you want to capture (comma-separated), or 'all': ").lower()
            if selection == 'all':
                return list(range(len(monitors)))
            try:
                selected = [int(x.strip()) - 1 for x in selection.split(',')]
                if all(0 <= s < len(monitors) for s in selected):
                    return selected
                else:
                    print("Invalid monitor number(s). Please try again.")
            except ValueError:
                print("Invalid input. Please enter numbers separated by commas or 'all'.")

def get_system_font():
    system = platform.system()
    if system == "Windows":
        return "arial.ttf"
    elif system == "Darwin":  # macOS
        return "/System/Library/Fonts/Helvetica.ttc"
    else:  # Linux and others
        return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def take_screenshot(save_folder, monitor_indices):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        with mss() as sct:
            for idx in monitor_indices:
                monitor = sct.monitors[idx + 1]  # +1 because mss.monitors[0] is the "all in one" monitor
                screenshot = sct.grab(monitor)
                filename = os.path.join(save_folder, f"screenshot_monitor{idx+1}_{timestamp}.png")
                
                Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX").save(filename)
                print(f"Screenshot saved as {filename}")
                
                # Add timestamp to the image
                image = Image.open(filename)
                draw = ImageDraw.Draw(image)
                try:
                    font = ImageFont.truetype(get_system_font(), 36)
                except IOError:
                    font = ImageFont.load_default()
                draw.text((10, 10), timestamp, font=font, fill=(255, 0, 0))
                image.save(filename)
                print(f"Screenshot processed and saved as {filename}")
    except Exception as e:
        print(f"Error capturing/processing screenshot: {e}")

def main():
    session_folder = create_session_folder()
    print(f"Saving screenshots to: {session_folder}")
    
    selected_monitors = select_monitors()
    print(f"Selected monitors: {[i+1 for i in selected_monitors]}")
    
    try:
        while True:
            take_screenshot(session_folder, selected_monitors)
            time.sleep(40)
    except KeyboardInterrupt:
        print("\nScreenshot capture stopped.")

if __name__ == "__main__":
    main()