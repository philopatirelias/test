from pathlib import Path
from settings import settings


class WhisperClient:
    def __init__(self) -> None:
        self.mode = settings.whisper_mode
        self._model = None

    def _get_local_model(self):
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "WHISPER_MODE=local requires faster-whisper. "
                "Install it with: python -m pip install faster-whisper"
            ) from exc

        model_name = getattr(settings, "whisper_local_model", "tiny")
        device = getattr(settings, "whisper_device", "cpu")
        compute_type = getattr(settings, "whisper_compute_type", "int8")

        self._model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )

        return self._model

    def transcribe(self, wav_path: Path) -> str:
        if self.mode == "mock":
            return "[mock transcription] Conversation chunk captured for interview completeness analysis."

        if self.mode == "local":
            model = self._get_local_model()

            segments, info = model.transcribe(
                str(wav_path),
                beam_size=1,
                vad_filter=True,
            )

            text_parts = []
            for segment in segments:
                if segment.text:
                    text_parts.append(segment.text.strip())

            text = " ".join(text_parts).strip()

            if not text:
                return "[no speech detected]"

            return text

        if self.mode == "api":
            return "[api whisper placeholder transcription]"

        return "[unknown whisper mode; fallback mock transcription]"