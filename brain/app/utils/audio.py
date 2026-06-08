from pydub import AudioSegment
import io

def normalize_audio(audio_bytes: bytes) -> bytes:
    """Normalize audio to 16kHz, 16-bit mono PCM WAV."""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    return buf.getvalue()
