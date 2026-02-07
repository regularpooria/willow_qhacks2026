import sys
import time
import threading
from pathlib import Path
import webview  # pywebview

# ==========================================
# Configuration
# ==========================================
sys.setrecursionlimit(5000)
APP_TITLE = "Willow"

COMPACT_SIZE = (420, 380)
FULL_SIZE = (900, 650)

# How often to re-assert topmost (some Windows setups can drop it)
TOPMOST_PULSE_SECONDS = 1.0


class AppState:
    def __init__(self):
        self.muted = True
        self.current_mode = "compact"
        self.transcript = ""
        self.window: webview.Window | None = None


state = AppState()


# ==========================================
# Window positioning helpers
# ==========================================
def get_bottom_right_position(window_size: tuple[int, int]) -> tuple[int, int]:
    """
    Place window near bottom-right. On Windows we can ask pywebview for screen size.
    On other platforms, fall back to 1920x1080.
    """
    w, h = int(window_size[0]), int(window_size[1])
    try:
        screen_w = webview.screens[0].width
        screen_h = webview.screens[0].height
    except Exception:
        screen_w, screen_h = 1920, 1080

    x = int(screen_w - w - 20)
    y = int(screen_h - h - 100)
    return x, y


def apply_mode(mode: str) -> dict:
    """
    Resize + reposition the single window. No recursion shenanigans:
    - JS calls this once (button click)
    - Python resizes/moves window
    - JS resize handler updates CSS only (no callback into Python)
    """
    mode = "full" if mode == "full" else "compact"
    state.current_mode = mode
    size = FULL_SIZE if mode == "full" else COMPACT_SIZE
    x, y = get_bottom_right_position(size)

    resized = False
    if state.window is not None:
        try:
            # Resize first, then move
            state.window.resize(int(size[0]), int(size[1]))
            state.window.move(int(x), int(y))
            resized = True
        except Exception as e:
            print(f"⚠️  Failed to apply mode={mode}: {e}")

    return {
        "ok": True,
        "mode": mode,
        "resized": resized,
        "size": list(size),
        "pos": [x, y],
    }


def maintain_on_top():
    """
    Keep the window on top. This is mostly redundant if on_top=True works,
    but on some Windows 10 renderer combos it can occasionally get dropped.
    """
    while True:
        time.sleep(TOPMOST_PULSE_SECONDS)
        w = state.window
        if not w:
            continue
        try:
            w.on_top = True
        except Exception:
            pass


# ==========================================
# JS API (window.pywebview.api.*)
# ==========================================
class Api:
    def set_mute(self, muted: bool):
        state.muted = bool(muted)
        print(f"🎙️  Microphone {'muted' if state.muted else 'LIVE'}")
        return {"ok": True, "muted": state.muted}

    def set_window_mode(self, mode: str):
        # mode is "compact" or "full"
        return apply_mode(mode)

    def update_transcript(self, text: str):
        state.transcript = text or ""
        return {"ok": True}

    def get_current_mode(self):
        return {"mode": state.current_mode}


# ==========================================
# App bootstrap
# ==========================================
def ensure_web_folder() -> Path:
    """
    Expect ./web/index.html and ./web/styles.css, matching your previous Eel layout.
    """
    root = Path(__file__).resolve().parent
    web_dir = root / "web"

    if not web_dir.exists():
        raise FileNotFoundError(
            "Missing ./web/ folder. Put index.html and styles.css in ./web/"
        )

    for name in ("index.html", "styles.css"):
        if not (web_dir / name).exists():
            raise FileNotFoundError(f"Missing {name} in ./web/")

    return web_dir


def on_loaded():
    # Called once after the GUI loop starts.
    if state.window is None:
        return

    # Ensure top-most
    try:
        state.window.on_top = True
    except Exception:
        pass

    # Apply initial size/position
    apply_mode(state.current_mode)

    # Re-assert topmost on Windows (belt & suspenders)
    if sys.platform == "win32":
        threading.Thread(target=maintain_on_top, daemon=True).start()


def main():
    try:
        web_dir = ensure_web_folder()
    except Exception as e:
        print(f"❌ {e}")
        input("Press Enter to exit...")
        return

    start_size = COMPACT_SIZE if state.current_mode == "compact" else FULL_SIZE
    x, y = get_bottom_right_position(start_size)
    url = (web_dir / "index.html").resolve().as_uri()

    api = Api()

    window = webview.create_window(
        APP_TITLE,
        url=url,
        js_api=api,
        width=int(start_size[0]),
        height=int(start_size[1]),
        x=int(x),
        y=int(y),
        on_top=True,
        resizable=True,
    )
    state.window = window

    webview.start(on_loaded, window, debug=False)


if __name__ == "__main__":
    main()
