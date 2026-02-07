from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

import os


def trans_to_aud(transcript):
    load_dotenv()

    elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
    )

    audio = elevenlabs.text_to_speech.convert(
        text=transcript,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    play(audio)
