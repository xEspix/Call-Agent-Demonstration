from elevenlabs.client import ElevenLabs
from elevenlabs import play
import os
from dotenv import load_dotenv
load_dotenv()


ElevenLabs_API_KEY=os.getenv("ElevenLabs_API_KEY")

client= ElevenLabs(api_key=ElevenLabs_API_KEY)
audio=client.text_to_speech.convert(
    voice_id="bperRlax6jQ6TbJctq3b",
    text="Hello how are you doing today? I am your friendly assistant from Riverwood Estate."
)

with open("output.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)

print("Audio saved as output.mp3")