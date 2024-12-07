import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class AudioEntry:
    """Represents a single audio message entry in the buffer."""

    message_id: int
    chat_id: int
    user_id: int
    filepath: str
    timestamp: datetime
    transcription: Optional[str] = None
    duration: Optional[float] = None


class AudioBuffer:
    def __init__(self, max_size: int = 100):
        """Initialize the audio buffer with a maximum size."""
        self.max_size = max_size
        self.buffer: Dict[str, AudioEntry] = {}

    def add_entry(
        self,
        message_id: int,
        chat_id: int,
        user_id: int,
        filepath: str,
        duration: Optional[float] = None,
    ) -> str:
        """
        Add a new audio entry to the buffer.
        Returns the unique key for the entry.
        """
        # Generate unique key
        key = f"{chat_id}_{message_id}"

        # Create new entry
        entry = AudioEntry(
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
            filepath=filepath,
            timestamp=datetime.now(),
            duration=duration,
        )

        # Add to buffer, removing oldest if at capacity
        if len(self.buffer) >= self.max_size:
            oldest_key = min(self.buffer.keys(), key=lambda k: self.buffer[k].timestamp)
            del self.buffer[oldest_key]

        self.buffer[key] = entry
        return key

    def get_entry(self, key: str) -> Optional[AudioEntry]:
        """Retrieve an entry from the buffer by its key."""
        return self.buffer.get(key)

    def update_transcription(self, key: str, transcription: str) -> bool:
        """Update the transcription for a specific entry."""
        if key in self.buffer:
            entry = self.buffer[key]
            entry.transcription = transcription
            return True
        return False

    def get_chat_history(self, chat_id: int, limit: int = 10) -> List[AudioEntry]:
        """Get recent audio entries for a specific chat."""
        chat_entries = [
            entry for entry in self.buffer.values() if entry.chat_id == chat_id
        ]
        return sorted(chat_entries, key=lambda x: x.timestamp, reverse=True)[:limit]

    def cleanup_old_entries(self, max_age_hours: int = 24) -> int:
        """Remove entries older than specified hours. Returns number of entries removed."""
        current_time = datetime.now()
        keys_to_remove = [
            key
            for key, entry in self.buffer.items()
            if (current_time - entry.timestamp).total_seconds() > max_age_hours * 3600
        ]

        for key in keys_to_remove:
            del self.buffer[key]

        return len(keys_to_remove)
