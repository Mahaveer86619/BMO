from faster_whisper import WhisperModel
from app.core.config import settings

class WhisperProvider:
    _model: WhisperModel | None = None

    @classmethod
    def _get_model(cls) -> WhisperModel:
        if cls._model is None:
            cls._model = WhisperModel(
                settings.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",
                download_root=settings.WHISPER_MODEL_CACHE,
            )
        return cls._model

    @classmethod
    def transcribe(cls, audio_path: str) -> str:
        model = cls._get_model()
        segments, _ = model.transcribe(audio_path, beam_size=5)
        return " ".join(s.text for s in segments).strip()
