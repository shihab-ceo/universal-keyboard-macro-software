"""MacroKeys: a small Windows global keyboard macro prototype."""

from __future__ import annotations

import ctypes
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
import winreg
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk


APP_NAME = "MacroKeys"
if getattr(sys, "frozen", False):
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    CONFIG_PATH = local_app_data / APP_NAME / "profiles.json"
else:
    CONFIG_PATH = Path(__file__).with_name("profiles.json")
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_SIZE = 0x0005
WM_USER = 0x0400
WM_TRAY_CALLBACK = WM_USER + 0x513
STARTUP_REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "MacroKeys"
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
SIZE_MINIMIZED = 1
GWLP_WNDPROC = -4
LLKHF_INJECTED = 0x10
LLMHF_INJECTED = 0x01
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT), ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON), ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256), ("uTimeoutOrVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                 wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadIconW.restype = wintypes.HICON
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.CallWindowProcW.argtypes = [ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                                   wintypes.WPARAM, wintypes.LPARAM]
user32.CallWindowProcW.restype = ctypes.c_ssize_t
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL


VK_NAMES = {
    **{f"F{i}": 0x6F + i for i in range(1, 25)},
    **{chr(i): i for i in range(ord("A"), ord("Z") + 1)},
    **{str(i): ord(str(i)) for i in range(10)},
    "SPACE": 0x20, "ENTER": 0x0D, "TAB": 0x09, "ESC": 0x1B,
    "BACKSPACE": 0x08, "DELETE": 0x2E, "INSERT": 0x2D,
    "HOME": 0x24, "END": 0x23, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    "CAPSLOCK": 0x14, "NUMLOCK": 0x90, "PRINTSCREEN": 0x2C,
    "PAUSE": 0x13, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
    "\\": 0xDC, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE,
    "/": 0xBF, "`": 0xC0,
}
MODIFIERS = {"CTRL": 0x11, "CONTROL": 0x11, "ALT": 0x12, "SHIFT": 0x10,
             "WIN": 0x5B, "LWIN": 0x5B, "RWIN": 0x5C}
VK_DISPLAY = {value: key for key, value in VK_NAMES.items() if len(key) > 1}
VK_DISPLAY.update({value: chr(value) for value in range(0x41, 0x5B)})
VK_DISPLAY.update({value: str(value - 0x30) for value in range(0x30, 0x3A)})
VK_DISPLAY.update({0x10: "SHIFT", 0x11: "CTRL", 0x12: "ALT", 0x5B: "WIN"})


def key_name(vk: int) -> str:
    return VK_DISPLAY.get(vk, f"VK_{vk:02X}")


def load_profiles() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data.get("profiles"), list) and data["profiles"]:
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {"version": 1, "profiles": [{"name": "Default", "mappings": []}]}


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --startup'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{runner.resolve()}" "{Path(__file__).resolve()}" --startup'


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REGISTRY_KEY,
                            0, winreg.KEY_READ) as key:
            command, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
        return bool(command)
    except (FileNotFoundError, OSError):
        return False


def set_startup_enabled(enabled: bool) -> None:
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STARTUP_REGISTRY_KEY) as key:
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REGISTRY_KEY,
                            0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, STARTUP_VALUE_NAME)
    except FileNotFoundError:
        pass


def send_key(vk: int, key_up: bool = False) -> None:
    flags = KEYEVENTF_KEYUP if key_up else 0
    inp = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk, dwFlags=flags))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_text(text: str) -> None:
    inputs = []
    for char in text:
        code = ord(char)
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wScan=code, dwFlags=KEYEVENTF_UNICODE))
        up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
        inputs.extend((down, up))
    if inputs:
        array_type = INPUT * len(inputs)
        user32.SendInput(len(inputs), array_type(*inputs), ctypes.sizeof(INPUT))


def play_actions(lines: list[str], stop_event: threading.Event) -> None:
    actions = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    repeats = 1
    if actions and actions[0].upper().startswith("REPEAT:"):
        repeats = max(1, min(1000, int(actions.pop(0).split(":", 1)[1])))
    for _ in range(repeats):
        for action in actions:
            if stop_event.is_set():
                return
            kind, separator, value = action.partition(":")
            if not separator:
                if action.upper() == "DISABLE":
                    continue
                raise ValueError(f"Invalid action: {action}")
            kind, value = kind.strip().upper(), value.strip()
            if kind == "DISABLE":
                continue
            elif kind == "TEXT":
                send_text(value)
            elif kind in ("KEYDOWN", "KEYUP"):
                token = value.strip().upper()
                if token in VK_NAMES:
                    vk = VK_NAMES[token]
                elif token.startswith("VK_") and len(token) == 5:
                    vk = int(token[3:], 16)
                else:
                    raise ValueError(f"Unknown key in {action}")
                send_key(vk, key_up=(kind == "KEYUP"))
            elif kind == "KEY":
                parts = [part.strip().upper() for part in value.split("+") if part.strip()]
                if not parts:
                    raise ValueError(f"Unknown key in {action}. Use names like CTRL+SHIFT+S or ENTER.")
                modifiers = []
                for part in parts[:-1]:
                    if part not in MODIFIERS:
                        raise ValueError(f"Unknown modifier '{part}' in {action}")
                    modifiers.append(MODIFIERS[part])
                key_name_part = parts[-1]
                if key_name_part in VK_NAMES:
                    key = VK_NAMES[key_name_part]
                elif key_name_part.startswith("VK_") and len(key_name_part) == 5:
                    try:
                        key = int(key_name_part[3:], 16)
                    except ValueError as exc:
                        raise ValueError(f"Unknown key in {action}") from exc
                else:
                    raise ValueError(f"Unknown key in {action}. Use names like CTRL+SHIFT+S or ENTER.")
                for vk in modifiers:
                    send_key(vk)
                send_key(key)
                send_key(key, True)
                for vk in reversed(modifiers):
                    send_key(vk, True)
            elif kind == "WAIT":
                delay = max(0, min(60000, int(value))) / 1000
                if stop_event.wait(delay):
                    return
            elif kind == "CLICK":
                button = value.upper()
                flags = {"LEFT": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
                         "RIGHT": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
                         "MIDDLE": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)}.get(button)
                if not flags:
                    raise ValueError("CLICK must be LEFT, RIGHT, or MIDDLE")
                user32.mouse_event(flags[0], 0, 0, 0, 0)
                user32.mouse_event(flags[1], 0, 0, 0, 0)
            elif kind in ("MOUSEDOWN", "MOUSEUP"):
                button = value.upper()
                flags = {"LEFT": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
                         "RIGHT": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
                         "MIDDLE": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)}.get(button)
                if not flags:
                    raise ValueError("MOUSEDOWN/MOUSEUP must be LEFT, RIGHT, or MIDDLE")
                user32.mouse_event(flags[0] if kind == "MOUSEDOWN" else flags[1], 0, 0, 0, 0)
            elif kind == "MOVE":
                x, y = (int(v.strip()) for v in value.split(",", 1))
                user32.SetCursorPos(x, y)
            elif kind == "SCROLL":
                direction = value.upper()
                if direction not in ("UP", "DOWN"):
                    raise ValueError("SCROLL must be UP or DOWN")
                user32.mouse_event(0x0800, 0, 0, 120 if direction == "UP" else -120, 0)
            elif kind == "OPEN":
                if not value:
                    raise ValueError("OPEN needs an application path, file, or URL")
                os.startfile(value)
            else:
                raise ValueError(f"Unknown action type '{kind}'")


class KeyboardHook:
    def __init__(self, on_key, on_mouse):
        self.on_key = on_key
        self.on_mouse = on_mouse
        self.thread = None
        self.ready = threading.Event()
        self.thread_id = 0
        self.hook = None
        self.mouse_hook = None
        self.callback = None
        self.mouse_callback = None
        self.error = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.ready.clear()
        self.error = None
        self.thread = threading.Thread(target=self._run, daemon=True, name="MacroKeysHook")
        self.thread.start()
        self.ready.wait(3)
        if self.error:
            raise RuntimeError(self.error)
        if not self.hook:
            raise RuntimeError("Windows keyboard hook did not start")

    def stop(self):
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)
        self.thread = None

    def _run(self):
        self.thread_id = kernel32.GetCurrentThreadId()

        @HOOKPROC
        def hook_proc(code, wparam, lparam):
            if code >= 0:
                info = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                event = int(wparam)
                down = event in (WM_KEYDOWN, WM_SYSKEYDOWN)
                up = event in (WM_KEYUP, WM_SYSKEYUP)
                if (down or up) and not (info.flags & LLKHF_INJECTED):
                    if self.on_key(int(info.vkCode), down, up):
                        return 1
            return user32.CallNextHookEx(self.hook, code, wparam, lparam)

        @HOOKPROC
        def mouse_proc(code, wparam, lparam):
            if code >= 0:
                info = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                if not (info.flags & LLMHF_INJECTED):
                    self.on_mouse(int(wparam), int(info.mouseData))
            return user32.CallNextHookEx(self.mouse_hook, code, wparam, lparam)

        self.callback = hook_proc
        self.mouse_callback = mouse_proc
        self.hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.callback,
                                             kernel32.GetModuleHandleW(None), 0)
        if not self.hook:
            self.error = f"SetWindowsHookEx failed: {ctypes.get_last_error()}"
            self.ready.set()
            return
        self.mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self.mouse_callback,
                                                   kernel32.GetModuleHandleW(None), 0)
        if not self.mouse_hook:
            self.error = f"Mouse hook failed: {ctypes.get_last_error()}"
            user32.UnhookWindowsHookEx(self.hook)
            self.hook = None
            self.ready.set()
            return
        self.ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(self.mouse_hook)
        user32.UnhookWindowsHookEx(self.hook)
        self.mouse_hook = None
        self.hook = None


class NativeTrayIcon:
    def __init__(self, root, is_active, on_show, on_toggle, on_exit):
        self.root = root
        self.is_active = is_active
        self.on_show = on_show
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.hwnd = user32.GetAncestor(root.winfo_id(), 2)
        self.icon = user32.LoadIconW(None, ctypes.c_void_p(32512))
        self.menu = tk.Menu(root, tearoff=False)
        self.menu.add_command(label="Open MacroKeys", command=on_show)
        self.menu.add_command(label="Pause macros", command=on_toggle)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=on_exit)

        @WNDPROC
        def window_proc(hwnd, message, wparam, lparam):
            if message == WM_TRAY_CALLBACK:
                mouse_message = int(lparam) & 0xFFFF
                if mouse_message == WM_LBUTTONUP:
                    self.root.after(0, self.on_show)
                    return 0
                if mouse_message in (WM_RBUTTONUP, 0x020B):
                    self.root.after(0, self.show_menu)
                    return 0
            if message == WM_SIZE and int(wparam) == SIZE_MINIMIZED:
                self.root.after(0, self.root.withdraw)
            return user32.CallWindowProcW(self.previous_proc, hwnd, message, wparam, lparam)

        self.window_proc = window_proc
        self.previous_proc = user32.SetWindowLongPtrW(
            self.hwnd, GWLP_WNDPROC, ctypes.cast(self.window_proc, ctypes.c_void_p).value
        )
        if not self.previous_proc:
            raise ctypes.WinError(ctypes.get_last_error())
        self.data = NOTIFYICONDATAW()
        self.data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.data.hWnd = self.hwnd
        self.data.uID = 1
        self.data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.data.uCallbackMessage = WM_TRAY_CALLBACK
        self.data.hIcon = self.icon
        self.data.szTip = "MacroKeys — Universal Keyboard Macro"
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.data)):
            user32.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, self.previous_proc)
            raise ctypes.WinError(ctypes.get_last_error())
        self.visible = True

    def show_menu(self):
        self.menu.entryconfigure(1, label="Pause macros" if self.is_active() else "Resume macros")
        point = POINT()
        user32.GetCursorPos(ctypes.byref(point))
        self.menu.tk_popup(point.x, point.y)

    def destroy(self):
        if getattr(self, "visible", False):
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.data))
            self.visible = False
        if getattr(self, "previous_proc", 0):
            user32.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, self.previous_proc)
            self.previous_proc = 0


class MacroKeysApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.launched_at_startup = "--startup" in sys.argv[1:]
        self.root.title("MacroKeys — Universal Keyboard Macro")
        self.root.geometry("1440x850")
        self.root.minsize(800, 560)
        self.root.state("zoomed")
        self.root.configure(bg="#111827")
        self.data = load_profiles()
        self.active_profile = self.data["profiles"][0]
        self.selected_index = None
        self.capture_key = False
        self.capture_target_index = None
        self.keyboard_view = None
        self.recording = False
        self.wizard_recording = False
        self.wizard_recorded_keys = []
        self.wizard_record_down = set()
        self.wizard_record_lock = threading.Lock()
        self.wizard_record_summary_var = None
        self.last_record_time = None
        self.active = False
        self.consumed = set()
        self.stop_playback = threading.Event()
        self.events = queue.Queue()
        self.playback_lock = threading.Lock()
        self.hook = KeyboardHook(self._on_key_event, self._on_mouse_event)
        self._style()
        self._build_ui()
        self.refresh_mappings()
        self.root.after(60, self._drain_events)
        self.root.after(1000, self._poll_foreground_profile)
        if any((m.get("triggers") or m.get("trigger")) and m.get("actions")
               for m in self.active_profile.get("mappings", [])):
            self.root.after(350, self.toggle_active)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.tray = None
        try:
            self.tray = NativeTrayIcon(self.root, lambda: self.active, self.show_window,
                                       self.toggle_active, self.exit_app)
        except Exception as exc:
            self.status_var.set("System tray unavailable")
            messagebox.showerror("System tray", f"Could not create tray icon:\n{exc}", parent=self.root)
        if self.launched_at_startup and self.tray is not None:
            self.root.after(700, self.minimize_to_tray)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#111827")
        style.configure("TLabel", background="#111827", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground="#f9fafb")
        style.configure("Muted.TLabel", foreground="#9ca3af")
        style.configure("MacroOff.TLabel", foreground="#fca5a5", font=("Segoe UI", 9, "bold"))
        style.configure("MacroOn.TLabel", foreground="#86efac", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", padding=(12, 7), font=("Segoe UI", 9, "bold"))
        style.configure("Accent.TButton", background="#2563eb", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        style.configure("Treeview", background="#1f2937", fieldbackground="#1f2937",
                        foreground="#e5e7eb", rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background="#374151", foreground="#f9fafb",
                        font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        pages = ttk.Notebook(self.root)
        pages.pack(fill="both", expand=True)
        home = ttk.Frame(pages, padding=22)
        pages.add(home, text="ম্যাক্রো")
        outer = ttk.Frame(pages, padding=20)
        pages.add(outer, text="অ্যাডভান্সড")
        self.pages = pages

        home_header = ttk.Frame(home)
        home_header.pack(fill="x")
        ttk.Label(home_header, text="MacroKeys", style="Title.TLabel").pack(side="left")
        ttk.Label(home_header, text="ম্যাক্রো তৈরি করুন, তারপর চালানোর কীবোর্ড কী বেছে নিন।",
                  style="Muted.TLabel").pack(side="left", padx=14, pady=(8, 0))
        ttk.Button(home_header, text="＋ নতুন ম্যাক্রো তৈরি", style="Accent.TButton",
                   command=self.open_macro_wizard).pack(side="right")
        self.home_toggle_button = ttk.Button(home_header, text="▶ ম্যাক্রো চালু করুন",
                                             style="Accent.TButton", command=self.toggle_active)
        self.home_toggle_button.pack(side="right", padx=(0, 8))
        self.home_active_status_var = tk.StringVar(value="বন্ধ — trigger key কাজ করবে না")
        self.home_active_status = ttk.Label(home_header, textvariable=self.home_active_status_var,
                                            style="MacroOff.TLabel")
        self.home_active_status.pack(side="right", padx=(0, 12))

        home_profile = ttk.Frame(home)
        home_profile.pack(fill="x", pady=(18, 8))
        ttk.Label(home_profile, text="প্রোফাইল").pack(side="left")
        self.profile_var = tk.StringVar(value=self.active_profile["name"])
        self.profile_combo = ttk.Combobox(home_profile, textvariable=self.profile_var,
                                          state="readonly", width=20,
                                          values=[p["name"] for p in self.data["profiles"]])
        self.profile_combo.pack(side="left", padx=(8, 10))
        self.profile_combo.bind("<<ComboboxSelected>>", self._change_profile)
        ttk.Button(home_profile, text="＋ নতুন প্রোফাইল", command=self.add_profile).pack(side="left")
        ttk.Label(home_profile, text="নিচের তালিকা থেকে ম্যাক্রো বেছে কী সেট করুন অথবা মুছে ফেলুন।",
                  style="Muted.TLabel").pack(side="left", padx=14)
        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        ttk.Checkbutton(home_profile, text="কম্পিউটার চালুর সাথে চালু",
                        variable=self.startup_var, command=self._toggle_startup).pack(side="right")

        work = ttk.Frame(home)
        work.pack(fill="both", expand=True, pady=(12, 0))
        sidebar = ttk.Frame(work, padding=(0, 0, 16, 0), width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        ttk.Label(sidebar, text="সেভ করা ম্যাক্রো", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self.keyboard_macro_list = tk.Listbox(
            sidebar, exportselection=False, bg="#1f2937", fg="#f9fafb",
            selectbackground="#2563eb", selectforeground="white", relief="flat",
            font=("Segoe UI", 10), activestyle="none",
        )
        self.keyboard_macro_list.pack(fill="both", expand=True)
        self.empty_macros_label = ttk.Label(
            sidebar, text="এখনো কোনো ম্যাক্রো নেই।\n\nনতুন ম্যাক্রো তৈরি করতে\nনিচের বোতাম চাপুন।",
            style="Muted.TLabel", justify="center", anchor="center",
        )
        self.empty_macros_label.place(relx=0.47, rely=0.42, anchor="center")
        self.keyboard_macro_list.bind("<<ListboxSelect>>", self._select_keyboard_macro)
        self.keyboard_macro_list.bind("<ButtonPress-1>", self._keyboard_macro_press, add="+")
        self.keyboard_macro_list.bind("<Double-Button-1>", self._edit_keyboard_macro)
        ttk.Button(sidebar, text="＋ নতুন ম্যাক্রো তৈরি", style="Accent.TButton",
                   command=self.open_macro_wizard).pack(fill="x", pady=(9, 0))
        ttk.Button(sidebar, text="নির্বাচিত ম্যাক্রো মুছুন", command=self.delete_mapping).pack(fill="x", pady=(6, 0))
        ttk.Button(sidebar, text="আসল কীবোর্ডের কী চাপুন", command=self.begin_capture).pack(fill="x", pady=(6, 0))
        self.home_status_var = tk.StringVar(value="বাম দিক থেকে ম্যাক্রো বাছুন, তারপর কীবোর্ডের কীতে ছেড়ে দিন বা কী নির্বাচন করে সেট করুন।")

        board = ttk.Frame(work)
        board.pack(side="left", fill="both", expand=True)
        ttk.Label(board, text="কীবোর্ডে ম্যাক্রো সেট করুন", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.keyboard_target_var = tk.StringVar(value="")
        self.keyboard_selection_var = tk.StringVar(value="একটি ম্যাক্রো বেছে একাধিক key-তে click করুন—সব key একই sequence চালাবে।")
        ttk.Label(board, textvariable=self.keyboard_selection_var, style="Muted.TLabel").pack(anchor="w", pady=(4, 8))
        self.keyboard_canvas = tk.Canvas(board, height=400, bg="#111827", highlightthickness=0,
                                         scrollregion=(0, 0, 1270, 390))
        self.keyboard_canvas.pack(fill="both", expand=True)
        keyboard_scroll = ttk.Scrollbar(board, orient="horizontal", command=self.keyboard_canvas.xview)
        keyboard_scroll.pack(fill="x")
        self.keyboard_canvas.configure(xscrollcommand=keyboard_scroll.set)
        actions = ttk.Frame(board)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Label(actions, textvariable=self.home_status_var, style="Muted.TLabel").pack(side="left")
        ttk.Button(actions, text="নির্বাচিত key-তে সেট করুন", style="Accent.TButton",
                   command=self._apply_keyboard_target).pack(side="right")
        self.keyboard_view = self.root
        self.keyboard_list_refreshing = False
        self.root.bind_all("<ButtonRelease-1>", self._keyboard_drag_release, add="+")
        self.root.bind_all("<B1-Motion>", self._keyboard_drag_motion, add="+")

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="MacroKeys", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Turn any keyboard key into a shortcut or macro",
                  style="Muted.TLabel").pack(side="left", padx=15, pady=(8, 0))
        ttk.Button(header, text="Keyboard assignment", style="Accent.TButton",
                   command=self.open_keyboard_view).pack(side="left", padx=(8, 0))
        ttk.Label(header, text="Advanced tools · import/export and action editing",
                  style="Muted.TLabel").pack(side="right")
        ttk.Button(header, text="Import", command=self.import_profile).pack(side="right", padx=(0, 8))
        ttk.Button(header, text="Export", command=self.export_profile).pack(side="right", padx=(0, 8))

        auto_row = ttk.Frame(outer)
        auto_row.pack(fill="x", pady=(12, 0))
        ttk.Label(auto_row, text="Auto-switch executable").pack(side="left")
        self.auto_exe_var = tk.StringVar(value=self.active_profile.get("process", ""))
        ttk.Entry(auto_row, textvariable=self.auto_exe_var, width=28).pack(side="left", padx=8)
        ttk.Label(auto_row, text="e.g. photoshop.exe · blank means manual profile",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(auto_row, text="Save profile", command=self.save_profile).pack(side="right")

        body = ttk.Frame(outer, padding=(0, 20, 0, 12))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 16))
        ttk.Label(left, text="KEY MAPPINGS", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 8))
        cols = ("trigger", "name")
        self.mapping_tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        self.mapping_tree.heading("trigger", text="TRIGGER KEY")
        self.mapping_tree.heading("name", text="MACRO NAME")
        self.mapping_tree.column("trigger", width=130, anchor="center")
        self.mapping_tree.column("name", width=240)
        self.mapping_tree.pack(fill="both", expand=True)
        self.mapping_tree.bind("<<TreeviewSelect>>", self._select_mapping)
        list_actions = ttk.Frame(left)
        list_actions.pack(fill="x", pady=(10, 0))
        ttk.Button(list_actions, text="+ New mapping", style="Accent.TButton",
                   command=self.new_mapping).pack(side="left")
        ttk.Button(list_actions, text="Delete", command=self.delete_mapping).pack(side="left", padx=8)

        right = ttk.Frame(body, padding=16)
        right.pack(side="right", fill="both", expand=True)
        ttk.Label(right, text="MAPPING EDITOR", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        fields = ttk.Frame(right)
        fields.pack(fill="x", pady=(12, 8))
        ttk.Label(fields, text="Macro name").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(fields, textvariable=self.name_var)
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12), padx=(0, 10))
        ttk.Label(fields, text="Trigger key").grid(row=0, column=1, sticky="w")
        self.trigger_var = tk.StringVar()
        self.trigger_entry = ttk.Entry(fields, textvariable=self.trigger_var, state="readonly")
        self.trigger_entry.grid(row=1, column=1, sticky="ew", pady=(4, 12))
        ttk.Button(fields, text="Capture key", command=self.begin_capture).grid(row=1, column=2, padx=(8, 0), sticky="ew")
        fields.columnconfigure(0, weight=1)
        fields.columnconfigure(1, weight=1)
        action_header = ttk.Frame(right)
        action_header.pack(fill="x")
        ttk.Label(action_header, text="Actions — one per line", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(action_header, text="Select keys", command=self.open_key_picker).pack(side="right", padx=(8, 0))
        self.record_button = ttk.Button(action_header, text="Record input", command=self.toggle_recording)
        self.record_button.pack(side="right")
        ttk.Label(right, text="TEXT: hello   ·   KEY: CTRL+SHIFT+S   ·   WAIT: 250   ·   CLICK: LEFT",
                  style="Muted.TLabel", wraplength=430).pack(anchor="w", pady=(3, 7))
        self.actions_text = tk.Text(right, height=12, wrap="word", bg="#1f2937", fg="#f9fafb",
                                    insertbackground="white", relief="flat", padx=10, pady=10,
                                    font=("Cascadia Code", 10), undo=True)
        self.actions_text.pack(fill="both", expand=True)
        ttk.Label(right, text="Optional: REPEAT:3 on the first line. MOVE:x,y moves the mouse.",
                  style="Muted.TLabel").pack(anchor="w", pady=(7, 10))
        ttk.Button(right, text="Save mapping", style="Accent.TButton", command=self.save_mapping).pack(anchor="e")

        footer = ttk.Frame(outer)
        footer.pack(fill="x")
        self.status_var = tk.StringVar(value="Ready · global shortcuts are off")
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")
        self.toggle_button = ttk.Button(footer, text="Start macros", style="Accent.TButton", command=self.toggle_active)
        self.toggle_button.pack(side="right")
        ttk.Label(outer, text="Tip: Start macros to enable mappings. Press Stop macros to pass every key through normally.",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

    def _change_profile(self, _event=None):
        self._commit_editor(quiet=True)
        self.active_profile["process"] = self.auto_exe_var.get().strip()
        name = self.profile_var.get()
        self.active_profile = next(p for p in self.data["profiles"] if p["name"] == name)
        self.auto_exe_var.set(self.active_profile.get("process", ""))
        self.selected_index = None
        self.refresh_mappings()

    def add_profile(self):
        name = simpledialog.askstring("New profile", "Profile name:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name or any(p["name"].casefold() == name.casefold() for p in self.data["profiles"]):
            messagebox.showerror("Profile", "Enter a unique profile name.", parent=self.root)
            return
        self._commit_editor(quiet=True)
        profile = {"name": name, "process": "", "mappings": []}
        self.data["profiles"].append(profile)
        self.active_profile = profile
        self.profile_combo.configure(values=[p["name"] for p in self.data["profiles"]])
        self.profile_var.set(name)
        self.auto_exe_var.set("")
        self.selected_index = None
        self.refresh_mappings()
        self.persist()

    def save_profile(self):
        self._commit_editor(quiet=True)
        self.active_profile["process"] = self.auto_exe_var.get().strip()
        self.persist()
        self.status_var.set(f"Saved profile · {self.active_profile['name']}")

    def export_profile(self):
        self._commit_editor(quiet=True)
        self.active_profile["process"] = self.auto_exe_var.get().strip()
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export profile", defaultextension=".json",
            initialfile=f"{self.active_profile['name']}.json",
            filetypes=[("MacroKeys profile", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.active_profile, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_var.set(f"Exported profile · {Path(path).name}")
        except OSError as exc:
            messagebox.showerror("Export profile", str(exc), parent=self.root)

    def import_profile(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Import profile",
            filetypes=[("MacroKeys profile", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            profile = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(profile, dict) or not isinstance(profile.get("name"), str) or not isinstance(profile.get("mappings"), list):
                raise ValueError("This file is not a valid MacroKeys profile.")
            profile.setdefault("process", "")
            for mapping in profile["mappings"]:
                if not isinstance(mapping, dict) or not isinstance(mapping.get("actions"), list):
                    raise ValueError("A mapping in this profile is malformed.")
            existing = {p["name"].casefold() for p in self.data["profiles"]}
            if profile["name"].casefold() in existing:
                profile["name"] = f"{profile['name']} (imported)"
            self._commit_editor(quiet=True)
            self.data["profiles"].append(profile)
            self.active_profile = profile
            self.profile_combo.configure(values=[p["name"] for p in self.data["profiles"]])
            self.profile_var.set(profile["name"])
            self.auto_exe_var.set(profile.get("process", ""))
            self.selected_index = None
            self.refresh_mappings()
            self.persist()
            self.status_var.set(f"Imported profile · {profile['name']}")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Import profile", str(exc), parent=self.root)

    def _foreground_executable(self):
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        handle = kernel32.OpenProcess(0x1000, False, process_id.value)
        if not handle:
            return ""
        try:
            size = wintypes.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return Path(buffer.value).name.casefold()
        finally:
            kernel32.CloseHandle(handle)
        return ""

    def _poll_foreground_profile(self):
        if not self.root.winfo_exists():
            return
        exe = self._foreground_executable()
        target = next((p for p in self.data["profiles"]
                       if p.get("process", "").strip().casefold() == exe and exe), None)
        if target and target is not self.active_profile:
            self._commit_editor(quiet=True)
            self.active_profile["process"] = self.auto_exe_var.get().strip()
            self.active_profile = target
            self.profile_var.set(target["name"])
            self.auto_exe_var.set(target.get("process", ""))
            self.selected_index = None
            self.refresh_mappings()
            self.persist()
            self.status_var.set(f"Auto profile · {target['name']}")
        self.root.after(1000, self._poll_foreground_profile)

    def refresh_mappings(self):
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)
        for index, mapping in enumerate(self.active_profile.get("mappings", [])):
            triggers = mapping.get("triggers") or ([mapping.get("trigger")] if mapping.get("trigger") else [])
            trigger_label = ", ".join(triggers) if triggers else "(unset)"
            self.mapping_tree.insert("", "end", iid=str(index),
                                     values=(trigger_label, mapping.get("name", "Untitled macro")))
        if self.selected_index is not None and self.selected_index < len(self.active_profile["mappings"]):
            self.mapping_tree.selection_set(str(self.selected_index))
        if self.keyboard_view is not None and self.keyboard_view.winfo_exists():
            self._refresh_keyboard_view()

    def _refresh_library(self):
        self._refresh_keyboard_macros()

    def _select_library_macro(self, _event=None):
        self._select_keyboard_macro(_event)

    def open_macro_wizard(self):
        wizard = tk.Toplevel(self.root)
        wizard.title("নতুন ম্যাক্রো · ধাপ ১/২")
        wizard.geometry("950x680")
        wizard.minsize(850, 600)
        wizard.configure(bg="#111827")
        wizard.transient(self.root)
        wizard.grab_set()

        frame = ttk.Frame(wizard, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="ধাপ ১/২ · ম্যাক্রো তৈরি", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="নাম দিন, ম্যাক্রো চালালে যে key-গুলো চাপবে সেগুলো বাছুন, তারপর key-গুলোর মাঝের delay দিন।",
                  style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(5, 18))
        ttk.Label(frame, text="ম্যাক্রোর নাম").pack(anchor="w")
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var, font=("Segoe UI", 12))
        name_entry.pack(fill="x", pady=(4, 14))
        name_entry.focus_set()

        record_row = ttk.Frame(frame)
        record_row.pack(fill="x", pady=(0, 8))
        ttk.Label(record_row, text="কীবোর্ড থেকে sequence রেকর্ড করুন:").pack(side="left")
        self.wizard_recorded_keys = []
        self.wizard_record_summary_var = tk.StringVar(value="রেকর্ড করা key: —")
        self.wizard_record_status_var = tk.StringVar(value="রেকর্ড বন্ধ")
        ttk.Label(record_row, textvariable=self.wizard_record_status_var,
                  style="Muted.TLabel").pack(side="left", padx=10)
        start_record_button = ttk.Button(record_row, text="● রেকর্ড শুরু", style="Accent.TButton")
        start_record_button.pack(side="right", padx=(6, 0))
        stop_record_button = ttk.Button(record_row, text="■ রেকর্ড বন্ধ", state="disabled")
        stop_record_button.pack(side="right")
        ttk.Label(frame, textvariable=self.wizard_record_summary_var, style="Muted.TLabel",
                  wraplength=880).pack(anchor="w", pady=(0, 8))

        ttk.Label(frame, text="আউটপুট key বাছুন (এই ক্রমে কাজ করবে)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 7))
        key_rows = [
            ["ESC", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACE"],
            ["TAB", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]"],
            ["CAPSLOCK", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "ENTER"],
            ["SHIFT", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "UP"],
            ["CTRL", "WIN", "ALT", "SPACE", "LEFT", "DOWN", "RIGHT", "DELETE", "HOME", "END", "PAGEUP", "PAGEDOWN", "INSERT"],
            ["NUMLOCK", "KP7", "KP8", "KP9", "KPSUBTRACT"],
            ["KP4", "KP5", "KP6", "KPADD", "KP1"],
            ["KP2", "KP3", "KPMULTIPLY", "KP0", "KPDECIMAL", "KPDIVIDE"],
        ]
        selected = {}
        grid = ttk.Frame(frame)
        grid.pack(fill="x")
        output_keys = [key for row in key_rows for key in row]
        for position, key in enumerate(output_keys):
            var = tk.BooleanVar(value=False)
            selected[key] = var
            ttk.Checkbutton(grid, text=key, variable=var)\
                .grid(row=position // 10, column=position % 10, padx=3, pady=1, sticky="w")

        ttk.Label(frame, text="রেকর্ড করা sequence থাকলে সেটিই ব্যবহার হবে; না থাকলে উপরের checkbox-এ বাছা key-গুলো ব্যবহার হবে।",
                  style="Muted.TLabel", wraplength=880).pack(anchor="w", pady=(3, 0))

        delay_row = ttk.Frame(frame)
        delay_row.pack(fill="x", pady=(18, 8))
        ttk.Label(delay_row, text="প্রতিটি key-এর মাঝের delay (মিলিসেকেন্ড)").pack(side="left")
        delay_var = tk.StringVar(value="50")
        ttk.Spinbox(delay_row, from_=0, to=60000, increment=10, textvariable=delay_var,
                    width=10).pack(side="left", padx=10)
        ttk.Label(frame, text="বাছা key-গুলো একটির পর একটি পাঠানো হবে। ০ ms দিলে মাঝখানে বিরতি থাকবে না।",
                  style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(3, 16))

        def stop_wizard_recording():
            if not self.wizard_recording:
                return
            self.wizard_recording = False
            with self.wizard_record_lock:
                for vk in tuple(self.wizard_record_down):
                    self.wizard_recorded_keys.append(("KEYUP", key_name(vk)))
                self.wizard_record_down.clear()
            if not self.active:
                self.hook.stop()
            start_record_button.configure(state="normal")
            stop_record_button.configure(state="disabled")
            self.wizard_record_status_var.set("রেকর্ড বন্ধ")
            self._refresh_wizard_record_summary()

        def start_wizard_recording():
            with self.wizard_record_lock:
                self.wizard_recorded_keys.clear()
                self.wizard_record_down.clear()
            self._refresh_wizard_record_summary()
            try:
                if not self.hook.thread or not self.hook.thread.is_alive():
                    self.hook.start()
            except Exception as exc:
                messagebox.showerror("কীবোর্ড রেকর্ড", str(exc), parent=wizard)
                return
            self.wizard_recording = True
            start_record_button.configure(state="disabled")
            stop_record_button.configure(state="normal")
            self.wizard_record_status_var.set("রেকর্ড চলছে — শেষ হলে ‘রেকর্ড বন্ধ’ চাপুন")

        start_record_button.configure(command=start_wizard_recording)
        stop_record_button.configure(command=stop_wizard_recording)

        def cancel_wizard():
            stop_wizard_recording()
            wizard.grab_release()
            wizard.destroy()

        wizard.protocol("WM_DELETE_WINDOW", cancel_wizard)

        def continue_to_assignment():
            stop_wizard_recording()
            name = name_var.get().strip()
            with self.wizard_record_lock:
                recorded_events = list(self.wizard_recorded_keys)
            keys = [key for row in key_rows for key in row if selected[key].get()]
            if not name:
                messagebox.showinfo("ম্যাক্রোর নাম", "ম্যাক্রোর একটি নাম লিখুন।", parent=wizard)
                name_entry.focus_set()
                return
            if not recorded_events and not keys:
                messagebox.showinfo("আউটপুট key", "কমপক্ষে একটি key বাছুন।", parent=wizard)
                return
            if any(m.get("name", "").casefold() == name.casefold()
                   for m in self.active_profile.get("mappings", [])):
                messagebox.showerror("ম্যাক্রোর নাম", "এই প্রোফাইলে এই নামের ম্যাক্রো আগে থেকেই আছে।", parent=wizard)
                return
            try:
                delay = int(delay_var.get())
                if not 0 <= delay <= 60000:
                    raise ValueError
            except ValueError:
                messagebox.showerror("ডিলে", "০ থেকে ৬০০০০ মিলিসেকেন্ডের পূর্ণসংখ্যা লিখুন।", parent=wizard)
                return
            modifiers = {"CTRL": "VK_11", "ALT": "VK_12", "SHIFT": "VK_10", "WIN": "VK_5B"}
            numpad = {f"KP{i}": f"VK_{0x60 + i:02X}" for i in range(10)}
            numpad.update({"KPADD": "VK_6B", "KPMULTIPLY": "VK_6A", "KPSUBTRACT": "VK_6D",
                           "KPDIVIDE": "VK_6F", "KPDECIMAL": "VK_6E"})
            actions = []
            if recorded_events:
                held = set()
                for position, (event_kind, key) in enumerate(recorded_events):
                    token = modifiers.get(key, numpad.get(key, key))
                    actions.append(f"{event_kind}:{token}")
                    if event_kind == "KEYDOWN":
                        held.add(token)
                    else:
                        held.discard(token)
                        more_keys = any(kind == "KEYDOWN" for kind, _ in recorded_events[position + 1:])
                        if delay and not held and more_keys:
                            actions.append(f"WAIT:{delay}")
            else:
                modifier_keys = [key for key in keys if key in modifiers]
                normal_keys = [key for key in keys if key not in modifiers]
                if modifier_keys and normal_keys:
                    for position, key in enumerate(normal_keys):
                        chord = "+".join([*modifier_keys, numpad.get(key, key)])
                        actions.append(f"KEY:{chord}")
                        if delay and position < len(normal_keys) - 1:
                            actions.append(f"WAIT:{delay}")
                else:
                    for position, key in enumerate(keys):
                        actions.append(f"KEY:{modifiers.get(key, numpad.get(key, key))}")
                        if delay and position < len(keys) - 1:
                            actions.append(f"WAIT:{delay}")
            self._commit_editor(quiet=True)
            self.active_profile["mappings"].append({"name": name, "trigger": "", "actions": actions})
            self.selected_index = len(self.active_profile["mappings"]) - 1
            self._load_mapping(self.selected_index)
            self.persist()
            self.refresh_mappings()
            wizard.grab_release()
            wizard.destroy()
            self.pages.select(0)
            self.open_keyboard_view()

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", side="bottom", pady=(12, 0))
        ttk.Button(buttons, text="বাতিল", command=cancel_wizard).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="সেভ করে চালানোর key বাছুন →", style="Accent.TButton",
                   command=continue_to_assignment).pack(side="right")

    def _refresh_wizard_record_summary(self):
        variable = self.wizard_record_summary_var
        if variable is None:
            return
        with self.wizard_record_lock:
            keys = list(self.wizard_recorded_keys)
        label = " → ".join(f"{key} {'↓' if kind == 'KEYDOWN' else '↑'}" for kind, key in keys) if keys else "—"
        variable.set(f"রেকর্ড করা key: {label}")

    def _select_mapping(self, _event=None):
        selection = self.mapping_tree.selection()
        if not selection:
            return
        self._commit_editor(quiet=True)
        self.selected_index = int(selection[0])
        self._load_mapping(self.selected_index)

    def _load_mapping(self, index):
        self.selected_index = index
        mapping = self.active_profile["mappings"][self.selected_index]
        self.name_var.set(mapping.get("name", ""))
        triggers = mapping.get("triggers") or ([mapping.get("trigger")] if mapping.get("trigger") else [])
        self.trigger_var.set(", ".join(triggers))
        self.actions_text.delete("1.0", "end")
        self.actions_text.insert("1.0", "\n".join(mapping.get("actions", [])))

    def _assign_mapping_trigger(self, index, trigger):
        if not (0 <= index < len(self.active_profile["mappings"])):
            return False
        self._commit_editor(quiet=True)
        mapping = self.active_profile["mappings"][index]
        trigger = trigger.upper()
        duplicates = [m for i, m in enumerate(self.active_profile["mappings"])
                      if i != index and trigger in [t.upper() for t in
                          (m.get("triggers") or ([m.get("trigger")] if m.get("trigger") else []))]]
        if duplicates:
            names = ", ".join(m.get("name", "Untitled macro") for m in duplicates)
            if not messagebox.askyesno(
                "Reassign key", f"{trigger} is already assigned to {names}. Move it to this macro?",
                parent=self.root,
            ):
                return False
            for other in duplicates:
                other_triggers = other.get("triggers") or ([other.get("trigger")] if other.get("trigger") else [])
                other["triggers"] = [t for t in other_triggers if t.upper() != trigger]
                other["trigger"] = other["triggers"][0] if other["triggers"] else ""
        triggers = mapping.get("triggers") or ([mapping.get("trigger")] if mapping.get("trigger") else [])
        if trigger not in [t.upper() for t in triggers]:
            triggers.append(trigger)
        mapping["triggers"] = triggers
        mapping["trigger"] = triggers[0]
        self.selected_index = index
        self._load_mapping(index)
        self.persist()
        self.refresh_mappings()
        self.status_var.set(f"Assigned {trigger} · {mapping.get('name', 'Macro')}")
        if self.keyboard_view is not None and self.keyboard_view.winfo_exists():
            self._refresh_keyboard_view()
        if not self.active:
            self.toggle_active()
        return True

    def open_keyboard_view(self):
        if self.selected_index is None or self.selected_index >= len(self.active_profile.get("mappings", [])):
            messagebox.showinfo("ম্যাক্রো বাছুন", "আগে একটি সেভ করা ম্যাক্রো বাছুন, অথবা ‘নতুন ম্যাক্রো তৈরি’ চাপুন।", parent=self.root)
            return
        self.pages.select(0)
        self._refresh_keyboard_macros()
        self.keyboard_macro_list.selection_clear(0, "end")
        self.keyboard_macro_list.selection_set(self.selected_index)
        self._load_keyboard_macro(self.selected_index)
        self.keyboard_canvas.focus_set()

    def _keyboard_macro_press(self, event):
        if not hasattr(self, "keyboard_macro_list"):
            return
        index = self.keyboard_macro_list.nearest(event.y)
        if 0 <= index < len(self.active_profile["mappings"]):
            self.keyboard_macro_list.selection_clear(0, "end")
            self.keyboard_macro_list.selection_set(index)
            self.keyboard_macro_list.activate(index)
            self._load_keyboard_macro(index)
            self.keyboard_drag_index = index

    def _keyboard_drag_motion(self, event):
        if getattr(self, "keyboard_drag_index", None) is not None and self.keyboard_view is not None:
            self.keyboard_view.configure(cursor="hand2")

    def _keyboard_drag_release(self, event):
        index = getattr(self, "keyboard_drag_index", None)
        self.keyboard_drag_index = None
        if self.keyboard_view is not None and self.keyboard_view.winfo_exists():
            self.keyboard_view.configure(cursor="")
        if index is None or not hasattr(self, "keyboard_canvas"):
            return
        canvas = self.keyboard_canvas
        x0, y0 = canvas.winfo_rootx(), canvas.winfo_rooty()
        x, y = event.x_root - x0, event.y_root - y0
        if not (0 <= x < canvas.winfo_width() and 0 <= y < canvas.winfo_height()):
            return
        # Convert viewport coordinates to canvas coordinates so drag-and-drop
        # still targets the correct key after horizontal scrolling.
        x = canvas.canvasx(x)
        y = canvas.canvasy(y)
        for item in reversed(canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1)):
            for tag in canvas.gettags(item):
                if tag.startswith("assign-key-"):
                    trigger = self.keyboard_key_tags.get(tag)
                    if trigger:
                        self._assign_mapping_trigger(index, trigger)
                    return

    def _select_keyboard_macro(self, _event=None):
        if getattr(self, "keyboard_list_refreshing", False):
            return
        selection = self.keyboard_macro_list.curselection()
        if selection:
            self._load_keyboard_macro(selection[0])

    def _load_keyboard_macro(self, index):
        if not (0 <= index < len(self.active_profile["mappings"])):
            return
        self._commit_editor(quiet=True)
        self.mapping_tree.selection_set(str(index))
        self._load_mapping(index)
        mapping = self.active_profile["mappings"][index]
        if hasattr(self, "keyboard_target_var"):
            self.keyboard_target_var.set("")
        triggers = mapping.get("triggers") or ([mapping.get("trigger")] if mapping.get("trigger") else [])
        trigger_label = ", ".join(triggers) if triggers else "সেট হয়নি"
        self.keyboard_selection_var.set(f"নির্বাচিত ম্যাক্রো: {mapping.get('name', 'ম্যাক্রো')}  ·  চালানোর key: {trigger_label}")
        self.home_status_var.set(f"নির্বাচিত: {mapping.get('name', 'ম্যাক্রো')} · key: {trigger_label}")
        if hasattr(self, "keyboard_canvas") and self.keyboard_canvas.winfo_exists():
            self._draw_keyboard()

    def _edit_keyboard_macro(self, _event=None):
        self._select_keyboard_macro()
        self.show_window()
        self.name_entry.focus_set()

    def _refresh_keyboard_macros(self):
        if not hasattr(self, "keyboard_macro_list") or not self.keyboard_macro_list.winfo_exists():
            return
        self.keyboard_list_refreshing = True
        try:
            self.keyboard_macro_list.delete(0, "end")
            mappings = self.active_profile.get("mappings", [])
            for mapping in mappings:
                triggers = mapping.get("triggers") or ([mapping.get("trigger")] if mapping.get("trigger") else [])
                trigger = ", ".join(triggers) if triggers else "এখনো সেট হয়নি"
                self.keyboard_macro_list.insert("end", f"{mapping.get('name', 'ম্যাক্রো')}  ·  {trigger}")
            if mappings:
                self.empty_macros_label.place_forget()
            else:
                self.empty_macros_label.place(relx=0.47, rely=0.42, anchor="center")
            if self.selected_index is not None and self.selected_index < self.keyboard_macro_list.size():
                self.keyboard_macro_list.selection_set(self.selected_index)
            if not mappings:
                self.home_status_var.set("ম্যাক্রো তৈরি করতে ‘নতুন ম্যাক্রো তৈরি’ চাপুন।")
        finally:
            self.keyboard_list_refreshing = False

    def _refresh_keyboard_view(self):
        self._refresh_keyboard_macros()
        if hasattr(self, "keyboard_canvas") and self.keyboard_canvas.winfo_exists():
            self._draw_keyboard()

    def _draw_keyboard(self):
        canvas = self.keyboard_canvas
        canvas.delete("all")
        self.keyboard_key_tags = {}
        assigned = {trigger.upper(): m for m in self.active_profile.get("mappings", [])
                    for trigger in (m.get("triggers") or ([m.get("trigger")] if m.get("trigger") else []))}
        unit, gap, key_height, row_gap = 42, 4, 38, 8
        key_rows = [
            [("Esc", "ESC", 1), None, ("F1", "F1", 1), ("F2", "F2", 1), ("F3", "F3", 1), ("F4", "F4", 1), None,
             ("F5", "F5", 1), ("F6", "F6", 1), ("F7", "F7", 1), ("F8", "F8", 1), None,
             ("F9", "F9", 1), ("F10", "F10", 1), ("F11", "F11", 1), ("F12", "F12", 1), None,
             ("PrtSc", "VK_2C", 1), ("ScrLk", "VK_91", 1), ("Pause", "PAUSE", 1)],
            [("`", "VK_C0", 1), ("1", "1", 1), ("2", "2", 1), ("3", "3", 1), ("4", "4", 1), ("5", "5", 1),
             ("6", "6", 1), ("7", "7", 1), ("8", "8", 1), ("9", "9", 1), ("0", "0", 1), ("-", "VK_BD", 1),
             ("=", "VK_BB", 1), ("Backspace", "BACKSPACE", 2)],
            [("Tab", "TAB", 1.5), ("Q", "Q", 1), ("W", "W", 1), ("E", "E", 1), ("R", "R", 1), ("T", "T", 1),
             ("Y", "Y", 1), ("U", "U", 1), ("I", "I", 1), ("O", "O", 1), ("P", "P", 1), ("[", "VK_DB", 1),
             ("]", "VK_DD", 1), ("\\", "VK_DC", 1.5)],
            [("Caps", "CAPSLOCK", 1.8), ("A", "A", 1), ("S", "S", 1), ("D", "D", 1), ("F", "F", 1), ("G", "G", 1),
             ("H", "H", 1), ("J", "J", 1), ("K", "K", 1), ("L", "L", 1), (";", "VK_BA", 1),
             ("'", "VK_DE", 1), ("Enter", "ENTER", 2.2)],
            [("Shift", "VK_10", 2.4), ("Z", "Z", 1), ("X", "X", 1), ("C", "C", 1), ("V", "V", 1), ("B", "B", 1),
             ("N", "N", 1), ("M", "M", 1), (",", "VK_BC", 1), (".", "VK_BE", 1), ("/", "VK_BF", 1),
             ("Shift", "VK_10", 2.6), None, ("↑", "UP", 1)],
            [("Ctrl", "VK_11", 1.4), ("Win", "VK_5B", 1.2), ("Alt", "VK_12", 1.4), ("Space", "SPACE", 5.8),
             ("Alt", "VK_12", 1.4), ("Menu", "VK_5D", 1.2), ("Ctrl", "VK_11", 1.4), None,
             ("←", "LEFT", 1), ("↓", "DOWN", 1), ("→", "RIGHT", 1)],
        ]

        def draw_key(x, y, label, trigger, units):
            width = int(unit * units + gap * max(0, units - 1))
            tag = f"assign-key-{len(self.keyboard_key_tags)}"
            self.keyboard_key_tags[tag] = trigger
            macro = assigned.get(trigger.upper())
            fill = "#2563eb" if macro else "#253246"
            selected_target = getattr(self, "keyboard_target_var", None)
            is_target = selected_target is not None and selected_target.get().upper() == trigger.upper()
            outline = "#fbbf24" if is_target else ("#60a5fa" if macro else "#52647a")
            canvas.create_rectangle(x, y, x + width, y + key_height, fill=fill,
                                    outline=outline, width=3 if is_target else 1, tags=(tag,))
            caption = label
            if macro and units >= 1.8:
                caption += "\n" + macro.get("name", "Macro")[:10]
            canvas.create_text(x + width / 2, y + key_height / 2, text=caption,
                               fill="white", font=("Segoe UI", 8 if macro else 9, "bold"),
                               justify="center", tags=(tag,))
            canvas.tag_bind(tag, "<Button-1>", lambda _event, t=trigger: self._assign_selected_keyboard_key(t))
            return width

        for row_index, row in enumerate(key_rows):
            x, y = 12, 12 + row_index * (key_height + row_gap)
            for key in row:
                if key is None:
                    x += 10
                    continue
                label, trigger, units = key
                x += draw_key(x, y, label, trigger, units) + gap

        navigation_rows = [
            [("Ins", "INSERT", 1), ("Home", "HOME", 1), ("PgUp", "PAGEUP", 1)],
            [("Del", "DELETE", 1), ("End", "END", 1), ("PgDn", "PAGEDOWN", 1)],
        ]
        nav_x = 850
        for row_index, row in enumerate(navigation_rows):
            x, y = nav_x, 12 + (row_index + 1) * (key_height + row_gap)
            for label, trigger, units in row:
                x += draw_key(x, y, label, trigger, units) + gap

        numpad_x = 1050
        numpad_rows = [
            [("Num", "NUMLOCK", 1), ("/", "VK_6F", 1), ("*", "VK_6A", 1), ("-", "VK_6D", 1)],
            [("7", "VK_67", 1), ("8", "VK_68", 1), ("9", "VK_69", 1), ("+", "VK_6B", 1)],
            [("4", "VK_64", 1), ("5", "VK_65", 1), ("6", "VK_66", 1), ("+", "VK_6B", 1)],
            [("1", "VK_61", 1), ("2", "VK_62", 1), ("3", "VK_63", 1), ("Enter", "VK_0D", 1)],
            [("0", "VK_60", 2), (".", "VK_6E", 1), ("Enter", "VK_0D", 1)],
        ]
        for row_index, row in enumerate(numpad_rows):
            x, y = numpad_x, 12 + (row_index + 1) * (key_height + row_gap)
            for label, trigger, units in row:
                x += draw_key(x, y, label, trigger, units) + gap
        canvas.create_text(numpad_x, 12, text="NUMPAD", anchor="nw", fill="#9ca3af",
                           font=("Segoe UI", 8, "bold"))
        canvas.configure(scrollregion=(0, 0, 1270, 390))

    def _assign_selected_keyboard_key(self, trigger):
        if self.keyboard_macro_list.curselection():
            index = self.keyboard_macro_list.curselection()[0]
        else:
            index = self.selected_index
        if index is None:
            messagebox.showinfo("Assign key", "Select a macro from the list first.", parent=self.keyboard_view)
            return
        self.keyboard_target_var.set(trigger.upper())
        self._assign_mapping_trigger(index, trigger)

    def _apply_keyboard_target(self):
        trigger = self.keyboard_target_var.get().strip()
        if not trigger:
            messagebox.showinfo("কী বাছুন", "আগে কীবোর্ডের যে key-তে সেট করতে চান সেটিতে ক্লিক করুন।", parent=self.keyboard_view)
            return
        if self.keyboard_macro_list.curselection():
            index = self.keyboard_macro_list.curselection()[0]
        else:
            index = self.selected_index
        if index is not None:
            self._assign_mapping_trigger(index, trigger)

    def _new_macro_from_keyboard_view(self):
        self.new_mapping()
        if self.keyboard_view is not None and self.keyboard_view.winfo_exists():
            self._refresh_keyboard_view()
            index = len(self.active_profile["mappings"]) - 1
            self.keyboard_macro_list.selection_clear(0, "end")
            self.keyboard_macro_list.selection_set(index)
            self.keyboard_macro_list.activate(index)
            self._load_keyboard_macro(index)

    def new_mapping(self):
        self._commit_editor(quiet=True)
        self.active_profile["mappings"].append({"name": "New macro", "trigger": "", "actions": []})
        self.selected_index = len(self.active_profile["mappings"]) - 1
        self.refresh_mappings()
        self.mapping_tree.selection_set(str(self.selected_index))
        self.name_var.set("New macro")
        self.trigger_var.set("")
        self.actions_text.delete("1.0", "end")
        self.name_entry.focus_set()

    def begin_capture(self):
        if self.selected_index is None:
            messagebox.showinfo("Capture key", "Create or select a macro first.", parent=self.root)
            return
        self.capture_target_index = self.selected_index
        try:
            if not self.hook.thread or not self.hook.thread.is_alive():
                self.hook.start()
        except Exception as exc:
            messagebox.showerror("Capture key", str(exc), parent=self.root)
            return
        self.capture_key = True
        self.status_var.set("ম্যাক্রো চালানোর key হিসেবে সেট করতে কীবোর্ডে একটি key চাপুন…")

    def _on_capture_key(self, vk):
        self.events.put(("capture", vk, self.capture_target_index))

    def open_key_picker(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select output keys")
        dialog.configure(bg="#111827")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        container = ttk.Frame(dialog, padding=16)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Choose the keys this trigger should send, in order.",
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(container, text="The delay is inserted between selected key taps. For a simultaneous shortcut, use KEY:CTRL+SHIFT+S.",
                  style="Muted.TLabel", wraplength=760).pack(anchor="w", pady=(4, 12))

        key_rows = [
            ["ESC", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"],
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACE"],
            ["TAB", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]"],
            ["CAPSLOCK", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'", "ENTER"],
            ["SHIFT", "Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "UP"],
            ["CTRL", "WIN", "ALT", "SPACE", "LEFT", "DOWN", "RIGHT", "DELETE", "HOME", "END", "PAGEUP", "PAGEDOWN", "INSERT"],
            ["NUMLOCK", "KP7", "KP8", "KP9", "KPSUBTRACT", "KP4", "KP5", "KP6",
             "KPADD", "KP1", "KP2", "KP3", "KPMULTIPLY", "KP0", "KPDECIMAL", "KPDIVIDE"],
        ]
        selected = {}
        grid = ttk.Frame(container)
        grid.pack(fill="x")
        for row_index, row in enumerate(key_rows):
            for col_index, key in enumerate(row):
                var = tk.BooleanVar(value=False)
                selected[key] = var
                ttk.Checkbutton(grid, text=key, variable=var, width=max(4, min(10, len(key) + 1)))\
                    .grid(row=row_index, column=col_index, padx=2, pady=3, sticky="ew")

        delay_row = ttk.Frame(container)
        delay_row.pack(fill="x", pady=(14, 4))
        ttk.Label(delay_row, text="Delay between keys (ms)").pack(side="left")
        delay_var = tk.StringVar(value="0")
        ttk.Spinbox(delay_row, from_=0, to=60000, increment=10, textvariable=delay_var, width=10).pack(side="left", padx=8)
        ttk.Label(delay_row, text="0 = no delay", style="Muted.TLabel").pack(side="left")

        def add_selected():
            keys = [key for row in key_rows for key in row if selected[key].get()]
            if not keys:
                messagebox.showinfo("Select keys", "Choose at least one output key.", parent=dialog)
                return
            try:
                delay = max(0, min(60000, int(delay_var.get())))
            except ValueError:
                messagebox.showerror("Select keys", "Delay must be a whole number from 0 to 60000 ms.", parent=dialog)
                return
            modifiers = {"CTRL": "VK_11", "ALT": "VK_12", "SHIFT": "VK_10"}
            numpad = {f"KP{i}": f"VK_{0x60 + i:02X}" for i in range(10)}
            numpad.update({"KPADD": "VK_6B", "KPMULTIPLY": "VK_6A", "KPSUBTRACT": "VK_6D",
                           "KPDIVIDE": "VK_6F", "KPDECIMAL": "VK_6E"})
            lines = []
            for index, key in enumerate(keys):
                output_key = modifiers.get(key, numpad.get(key, key))
                lines.append(f"KEY:{output_key}")
                if delay and index < len(keys) - 1:
                    lines.append(f"WAIT:{delay}")
            if self.actions_text.get("1.0", "end-1c").strip():
                self.actions_text.insert("end", "\n")
            self.actions_text.insert("end", "\n".join(lines) + "\n")
            self.actions_text.see("end")
            dialog.destroy()

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Add selected keys", style="Accent.TButton", command=add_selected).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=8)

    def _on_mouse_event(self, event, mouse_data):
        if not self.active or not self.recording:
            return
        names = {
            WM_LBUTTONDOWN: ("MOUSEDOWN", "LEFT"), WM_LBUTTONUP: ("MOUSEUP", "LEFT"),
            WM_RBUTTONDOWN: ("MOUSEDOWN", "RIGHT"), WM_RBUTTONUP: ("MOUSEUP", "RIGHT"),
            WM_MBUTTONDOWN: ("MOUSEDOWN", "MIDDLE"), WM_MBUTTONUP: ("MOUSEUP", "MIDDLE"),
        }
        if event in names:
            kind, value = names[event]
            self.events.put(("record", f"{kind}:{value}", time.perf_counter()))
        elif event == WM_MOUSEWHEEL:
            delta = (mouse_data >> 16) & 0xFFFF
            if delta >= 0x8000:
                delta -= 0x10000
            direction = "UP" if delta > 0 else "DOWN"
            self.events.put(("record", f"SCROLL:{direction}", time.perf_counter()))

    def toggle_recording(self):
        if not self.active:
            messagebox.showinfo("Record input", "Start macros before recording.", parent=self.root)
            return
        self.recording = not self.recording
        if self.recording:
            self.last_record_time = None
            self.record_button.configure(text="Stop recording")
            self.status_var.set("Recording physical keyboard and mouse events…")
        else:
            self.record_button.configure(text="Record input")
            self.status_var.set("Recording stopped · save the mapping to keep these actions")

    def _append_recorded_action(self, action, timestamp):
        if self.last_record_time is not None:
            delay_ms = round((timestamp - self.last_record_time) * 1000)
            if delay_ms >= 1:
                self.actions_text.insert("end", f"WAIT:{delay_ms}\n")
        self.actions_text.insert("end", f"{action}\n")
        self.actions_text.see("end")
        self.last_record_time = timestamp

    def _on_key_event(self, vk, down, up):
        if self.capture_key and down:
            self.capture_key = False
            self.consumed.add(vk)
            self._on_capture_key(vk)
            return True
        if self.wizard_recording and (down or up):
            key = key_name(vk)
            with self.wizard_record_lock:
                if down and vk not in self.wizard_record_down:
                    self.wizard_recorded_keys.append(("KEYDOWN", key))
                    self.wizard_record_down.add(vk)
                elif up and vk in self.wizard_record_down:
                    self.wizard_recorded_keys.append(("KEYUP", key))
                    self.wizard_record_down.discard(vk)
            if up:
                self.consumed.discard(vk)
            else:
                self.consumed.add(vk)
            self.events.put(("wizard_record_update",))
            return True
        if up and vk in self.consumed:
            self.consumed.discard(vk)
            return True
        if not self.active:
            return False
        if self.recording:
            if down or up:
                action = "KEYDOWN" if down else "KEYUP"
                self.events.put(("record", f"{action}:{key_name(vk)}", time.perf_counter()))
            return False
        if down:
            mapping = next((m for m in self.active_profile.get("mappings", [])
                            if key_name(vk).upper() in [trigger.upper() for trigger in
                                (m.get("triggers") or ([m.get("trigger")] if m.get("trigger") else []))]
                            and m.get("actions")), None)
            if mapping:
                if self.playback_lock.locked():
                    return False
                self.consumed.add(vk)
                self.events.put(("run", mapping.get("name", "Macro"), list(mapping["actions"])))
                return True
        if up and vk in self.consumed:
            self.consumed.discard(vk)
            return True
        return False

    def _drain_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "capture":
                    trigger = key_name(event[1])
                    target_index = event[2] if len(event) > 2 else self.selected_index
                    if target_index is not None:
                        self._assign_mapping_trigger(target_index, trigger)
                    else:
                        self.trigger_var.set(trigger)
                    self.status_var.set(f"Captured {trigger} · assigned to the selected macro")
                    if not self.active:
                        self.hook.stop()
                elif event[0] == "record":
                    self._append_recorded_action(event[1], event[2])
                elif event[0] == "wizard_record_update":
                    self._refresh_wizard_record_summary()
                elif event[0] == "run":
                    _, name, actions = event
                    threading.Thread(target=self._play, args=(name, actions), daemon=True).start()
                elif event[0] == "error":
                    self.status_var.set("Macro error · see details")
                    messagebox.showerror("Macro error", event[1], parent=self.root)
                elif event[0] == "done":
                    self.status_var.set(f"Running · completed {event[1]}")
        except queue.Empty:
            pass
        self.root.after(60, self._drain_events)

    def _play(self, name, actions):
        if not self.playback_lock.acquire(blocking=False):
            return
        try:
            self.stop_playback.clear()
            play_actions(actions, self.stop_playback)
            self.events.put(("done", name))
        except Exception as exc:
            self.events.put(("error", f"{name}: {exc}"))
        finally:
            self.playback_lock.release()

    def _commit_editor(self, quiet=False):
        if self.selected_index is None or self.selected_index >= len(self.active_profile["mappings"]):
            return True
        name = self.name_var.get().strip()
        trigger = self.trigger_var.get().strip().upper()
        actions = self.actions_text.get("1.0", "end-1c").splitlines()
        if not quiet and (not name or not trigger or not any(line.strip() and not line.strip().startswith("#") for line in actions)):
            messagebox.showerror("Save mapping", "Enter a name, capture a trigger key, and add at least one action.", parent=self.root)
            return False
        trigger_list = [item.strip() for item in trigger.split(",") if item.strip()]
        self.active_profile["mappings"][self.selected_index] = {
            "name": name or "Untitled macro", "trigger": trigger_list[0] if trigger_list else "",
            "triggers": trigger_list, "actions": actions,
        }
        return True

    def save_mapping(self):
        if self.selected_index is None:
            messagebox.showinfo("Save mapping", "Create or select a mapping first.", parent=self.root)
            return
        if not self._commit_editor():
            return
        triggers = [item.strip().upper() for item in self.trigger_var.get().split(",") if item.strip()]
        duplicates = [m for i, m in enumerate(self.active_profile["mappings"])
                      if i != self.selected_index and set(triggers) & set(
                          item.upper() for item in (m.get("triggers") or
                              ([m.get("trigger")] if m.get("trigger") else [])))]
        if duplicates:
            messagebox.showerror("Save mapping", "One or more trigger keys already belong to another macro.", parent=self.root)
            return
        self.persist()
        self.refresh_mappings()
        self.mapping_tree.selection_set(str(self.selected_index))
        self.status_var.set(f"Saved · {self.active_profile['name']} profile")

    def delete_mapping(self):
        if self.selected_index is None:
            selection = self.keyboard_macro_list.curselection() if hasattr(self, "keyboard_macro_list") else ()
            if selection:
                self.selected_index = selection[0]
        if self.selected_index is None or self.selected_index >= len(self.active_profile.get("mappings", [])):
            messagebox.showinfo("ম্যাক্রো মুছুন", "আগে তালিকা থেকে একটি ম্যাক্রো বাছুন।", parent=self.root)
            return
        mapping_name = self.active_profile["mappings"][self.selected_index].get("name", "Untitled macro")
        if not messagebox.askyesno("ম্যাক্রো মুছুন", f"এই প্রোফাইল থেকে ‘{mapping_name}’ মুছে ফেলবেন?", parent=self.root):
            return
        del self.active_profile["mappings"][self.selected_index]
        self.selected_index = None
        self.name_var.set("")
        self.trigger_var.set("")
        self.actions_text.delete("1.0", "end")
        self.refresh_mappings()
        self.persist()

    def persist(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save configuration", str(exc), parent=self.root)

    def toggle_active(self):
        if self.active:
            self.deactivate()
            return
        self._commit_editor(quiet=True)
        ready = [m for m in self.active_profile.get("mappings", [])
                 if (m.get("triggers") or m.get("trigger")) and m.get("actions")]
        if not ready:
            messagebox.showinfo("ম্যাক্রো চালু করুন", "আগে অন্তত একটি ম্যাক্রো তৈরি করে কীবোর্ডের key-তে সেট করুন।", parent=self.root)
            return
        try:
            self.hook.start()
        except Exception as exc:
            messagebox.showerror("Keyboard hook", str(exc), parent=self.root)
            return
        self.active = True
        self._sync_macro_controls()
        self.status_var.set("Running · press Stop macros to pass keys through")

    def _toggle_startup(self):
        enabled = bool(self.startup_var.get())
        try:
            set_startup_enabled(enabled)
        except OSError as exc:
            self.startup_var.set(not enabled)
            messagebox.showerror(
                "Windows startup", f"Startup setting could not be changed:\n{exc}", parent=self.root,
            )
            return
        self.home_status_var.set(
            "Windows চালুর সাথে MacroKeys চালু হবে।" if enabled
            else "Windows চালুর সময় MacroKeys অটো-রান বন্ধ করা হয়েছে।"
        )

    def deactivate(self):
        self.active = False
        self.capture_key = False
        self.recording = False
        self.record_button.configure(text="Record input")
        self.consumed.clear()
        self.stop_playback.set()
        self.hook.stop()
        self._sync_macro_controls()
        self.status_var.set("Ready · global shortcuts are off")

    def _sync_macro_controls(self):
        if self.active:
            label = "■ ম্যাক্রো বন্ধ করুন"
            self.home_active_status_var.set("চালু — trigger key চাপুন")
            self.home_active_status.configure(style="MacroOn.TLabel")
            self.toggle_button.configure(text="Stop macros")
        else:
            label = "▶ ম্যাক্রো চালু করুন"
            self.home_active_status_var.set("বন্ধ — trigger key কাজ করবে না")
            self.home_active_status.configure(style="MacroOff.TLabel")
            self.toggle_button.configure(text="Start macros")
        self.home_toggle_button.configure(text=label)

    def minimize_to_tray(self):
        self.root.withdraw()
        self.status_var.set("Minimized to tray · macros " + ("running" if self.active else "paused"))

    def show_window(self):
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def exit_app(self):
        if self.active:
            self.deactivate()
        self._commit_editor(quiet=True)
        self.persist()
        if self.tray:
            self.tray.destroy()
        self.root.destroy()


def main():
    if os.name != "nt":
        raise SystemExit("MacroKeys currently requires Windows.")
    root = tk.Tk()
    MacroKeysApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
