from pathlib import Path
from settings import settings


class WhisperClient:
    def __init__(self) -> None:
        self.mode = settings.whisper_mode

    def transcribe(self, wav_path: Path) -> str:
        if self.mode == "mock":
            return "[mock transcription] Conversation chunk captured for interview completeness analysis."
        if self.mode == "local":
            # Placeholder: wire local whisper model invocation here.
            return "[local whisper placeholder transcription]"
        if self.mode == "api":
            # Placeholder: wire optional external API transcription here.
            return "[api whisper placeholder transcription]"
        return "[unknown whisper mode; fallback mock transcription]"
