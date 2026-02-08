from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from playsound3 import playsound
import os
import sys

load_dotenv()

client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def trans_to_aud(transcript):

    audio_stream = client.text_to_speech.convert(
        text=transcript,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_flash_v2",
        output_format="mp3_44100_128",
    )

    # Write to a real file (PyInstaller-safe)
    output_path = resource_path("output.mp3")

    with open(output_path, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)

    playsound(output_path)
