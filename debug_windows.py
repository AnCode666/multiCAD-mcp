import win32gui

def enum_windows_callback(hwnd, result):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if "ZWCAD" in title:
            rect = win32gui.GetWindowRect(hwnd)
            print(f"Handle: {hwnd}, Title: '{title}', Rect: {rect}")

print("Searching for ZWCAD windows...")
win32gui.EnumWindows(enum_windows_callback, None)
print("Done.")
