from pydub import AudioSegment
import io


def normalize_audio(audio_bytes: bytes) -> bytes:
    """Normalize audio to 16kHz, 16-bit mono PCM WAV."""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    return buf.getvalue()


def pad_wav(audio_bytes: bytes, pre_ms: int = 0, post_ms: int = 0) -> bytes:
    """Prepend and/or append silence to a WAV, preserving its sample rate and format."""
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
    if pre_ms:
        audio = AudioSegment.silent(duration=pre_ms, frame_rate=audio.frame_rate).set_channels(audio.channels).set_sample_width(audio.sample_width) + audio
    if post_ms:
        audio = audio + AudioSegment.silent(duration=post_ms, frame_rate=audio.frame_rate).set_channels(audio.channels).set_sample_width(audio.sample_width)
    buf = io.BytesIO()
    audio.export(buf, format="wav")
    return buf.getvalue()


def silence_wav(duration_ms: int, sample_rate: int = 16000) -> bytes:
    """Generate a pure-silence WAV of the given duration."""
    silence = AudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)
    silence = silence.set_channels(1).set_sample_width(2)
    buf = io.BytesIO()
    silence.export(buf, format="wav")
    return buf.getvalue()
