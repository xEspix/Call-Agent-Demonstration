import os
import uuid
from gtts import gTTS

LANG_MAP={
    "English": "en",
    "Hindi": "hi"
}

SPEED=1.2


def _speed_up(path: str) -> None:
    from pydub import AudioSegment
    audio=AudioSegment.from_mp3(path)
    fast=audio._spawn(
        audio.raw_data,
        overrides={"frame_rate": int(audio.frame_rate * SPEED)}
    ).set_frame_rate(audio.frame_rate)
    fast.export(path, format="mp3")


def generate_voice(text: str, language: str="English", audio_dir: str=None) -> str:
    if audio_dir is None:
        raise ValueError("audio_dir must be provided as an absolute path")

    os.makedirs(audio_dir, exist_ok=True)

    lang_code=LANG_MAP.get(language, "en")
    filename=f"{uuid.uuid4().hex}.mp3"
    path=os.path.join(audio_dir, filename)

    tts=gTTS(text=text, lang=lang_code, slow=False)
    tts.save(path)

    try:
        _speed_up(path)
    except Exception as e:
        print(f"[tts] Speed-up skipped: {e}")

    return filename