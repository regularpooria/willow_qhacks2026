# example.py
import os
from dotenv import load_dotenv
from io import BytesIO
import requests
from elevenlabs.client import ElevenLabs
import wave


def aud_to_trans():
    elevenlabs = ElevenLabs(
        api_key="sk_47f593889414d07d36c0fe14ad44b9d3c7ceae65b30aaaf0"
    )

    with open("records/0.wav", "rb") as fd:
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
