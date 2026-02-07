# example.py
import os
import sys
from dotenv import load_dotenv
from io import BytesIO
import requests
from elevenlabs.client import ElevenLabs
import wave

load_dotenv()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def aud_to_trans():
    elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    with open(resource_path("records/0.wav"), "rb") as fd:
        audio_data = BytesIO(fd.read())

    transcription = elevenlabs.speech_to_text.convert(
        file=audio_data,
        model_id="scribe_v2",  # Model to use
        tag_audio_events=False,  # Tag audio events like laughter, applause, etc.
        language_code="eng",  # Language of the audio file. If set to None, the model will detect the language automatically.
        diarize=False,  # Whether to annotate who is speaking
    )

    print(transcription.text)
    return transcription.text


if __name__ == "__main__":
    aud_to_trans()
