"""Bounded process-local state and private photo bytes for a short demo session."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.consultation.models import (ConsultationMessage, ConsultationState, FeatureId,
                                     PhotoReference, RecommendationSet, UpdateConsultation)


LIFETIME = timedelta(hours=1)


def now() -> datetime:
    return datetime.now(timezone.utc)


class StoreFullError(RuntimeError):
    pass


class StaleConsultationError(RuntimeError):
    pass


@dataclass
class _Entry:
    state: ConsultationState
    photo_bytes: bytes | None = None


class ConsultationStore:
    def __init__(self, max_sessions: int = 10):
        self._entries: dict[UUID, _Entry] = {}
        self._lock = RLock()
        self.max_sessions = max_sessions

    def _entry(self, consultation_id: UUID) -> _Entry:
        entry = self._entries.get(consultation_id)
        if entry is None:
            raise KeyError("Consultation not found or expired.")
        if entry.state.expires_at <= now():
            del self._entries[consultation_id]
            raise KeyError("Consultation not found or expired.")
        return entry

    def create(self, feature: FeatureId) -> ConsultationState:
        with self._lock:
            current = now()
            self._entries = {key: value for key, value in self._entries.items()
                             if value.state.expires_at > current}
            if len(self._entries) >= self.max_sessions:
                raise StoreFullError("Consultation capacity reached. Try again later.")
            state = ConsultationState(id=uuid4(), primary_service=feature,
                                      created_at=current, updated_at=current,
                                      expires_at=current + LIFETIME)
            self._entries[state.id] = _Entry(state)
            return state.model_copy(deep=True)

    def get(self, consultation_id: UUID) -> ConsultationState:
        with self._lock:
            return self._entry(consultation_id).state.model_copy(deep=True)

    def photo_bytes(self, consultation_id: UUID) -> bytes | None:
        """Internal reference for a later phase; never exposed by this API."""
        with self._lock:
            return self._entry(consultation_id).photo_bytes

    def attach_photo(self, consultation_id: UUID, content: bytes, content_type: str,
                     width: int, height: int) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            current = now()
            entry.state = entry.state.model_copy(update={
                "photo": PhotoReference(id=uuid4(), content_type=content_type, width=width, height=height),
                "stage": "collecting", "recommendations": None,
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            entry.photo_bytes = content
            return entry.state.model_copy(deep=True)

    def update(self, consultation_id: UUID, change: UpdateConsultation) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            preferences = entry.state.preferences
            if change.preferences is not None:
                fields = change.preferences.model_dump(exclude_unset=True)
                preferences = preferences.model_copy(update=fields)
            messages = list(entry.state.messages)
            current = now()
            if change.message is not None:
                if len(messages) >= 10:
                    raise ValueError("Consultation message limit reached.")
                messages.append(ConsultationMessage(content=change.message, created_at=current))
            entry.state = entry.state.model_copy(update={
                "preferences": preferences, "messages": messages, "stage": "collecting",
                "recommendations": None, "updated_at": current, "expires_at": current + LIFETIME,
            })
            return entry.state.model_copy(deep=True)

    def save_recommendations(self, consultation_id: UUID, expected_update: datetime,
                             recommendations: RecommendationSet) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            if entry.state.updated_at != expected_update:
                raise StaleConsultationError("Consultation changed while recommendations were prepared.")
            current = now()
            entry.state = entry.state.model_copy(update={
                "recommendations": recommendations, "stage": "recommended",
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            return entry.state.model_copy(deep=True)
