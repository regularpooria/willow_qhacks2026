import sys
import time
import threading
from pathlib import Path
import webview  # pywebview
import pyaudio
import math
import struct
import wave
import os
from audio_to_transcript import aud_to_trans
from public.tools.LLM_behaviour import LLM_call
from transcript_to_audio import trans_to_aud
from playsound3 import playsound
import random

# ==========================================
# Configuration
# ==========================================
sys.setrecursionlimit(5000)
APP_TITLE = "Willow"

COMPACT_SIZE = (420, 380)
FULL_SIZE = (900, 650)

# How often to re-assert topmost (some Windows setups can drop it)
TOPMOST_PULSE_SECONDS = 1.0

# Get base path for resources (works both in dev and bundled exe)
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Audio recording settings
Threshold = 15
SHORT_NORMALIZE = 1.0 / 32768.0
chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
swidth = 2
TIMEOUT_LENGTH = 2
f_name_directory = resource_path("records")

waiting_audios_paths = [
    resource_path("public/audios/ill_take_care_of_it.mp3"),
    resource_path("public/audios/let_me_see_what_i_can_do.mp3"),
    resource_path("public/audios/on_it_chief.mp3"),
    resource_path("public/audios/processing_your_request.mp3"),
    resource_path("public/audios/working_on_it.mp3"),
]


class AppState:
    def __init__(self):
        self.muted = True
        self.current_mode = "compact"
        self.transcript = ""
        self.window: webview.Window | None = None
        self.recorder = None


state = AppState()


# ==========================================
# Audio Recorder
# ==========================================
class Recorder:
    @staticmethod
    def rms(frame):
        count = len(frame) / swidth
        format = "%dh" % (count)
        shorts = struct.unpack(format, frame)

        sum_squares = 0.0
        for sample in shorts:
            n = sample * SHORT_NORMALIZE
            sum_squares += n * n
        rms = math.pow(sum_squares / count, 0.5)

        return rms * 1000

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            output=True,
            frames_per_buffer=chunk,
        )
        self.running = False

    def record(self):
        print("Noise detected, recording beginning")
        rec = []
        current = time.time()
        end = time.time() + TIMEOUT_LENGTH

        while current <= end and self.running:
            if state.muted:
                print("Muted during recording, stopping")
                break

            data = self.stream.read(chunk)
            if self.rms(data) >= Threshold:
                end = time.time() + TIMEOUT_LENGTH

            current = time.time()
            rec.append(data)

        if not state.muted and rec:
            self.write(b"".join(rec))

    def write(self, recording):
        n_files = 0
        filename = os.path.join(f_name_directory, "{}.wav".format(n_files))

        wf = wave.open(filename, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(recording)
        wf.close()
        print("Written to file: {}".format(filename))
        print("Returning to listening")

    def listen(self):
        print("Listening beginning")
        self.running = True
        while self.running:
            if state.muted:
                time.sleep(0.1)
                continue

            input_data = self.stream.read(chunk)
            rms_val = self.rms(input_data)
            if rms_val > Threshold:
                self.record()
                transcript_text = aud_to_trans()
                if transcript_text:
                    state.transcript = transcript_text
                    playsound(random.choice(waiting_audios_paths), block=False)
                    response = LLM_call(state.transcript)
                    trans_to_aud(response)

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()


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

    def get_transcript(self):
        return {"transcript": state.transcript}


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


def start_audio_recording():
    """Start audio recording in a background thread"""

    def run_recorder():
        state.recorder = Recorder()
        state.recorder.listen()

    threading.Thread(target=run_recorder, daemon=True).start()


def on_loaded(window):
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

    # Start audio recording
    start_audio_recording()

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
