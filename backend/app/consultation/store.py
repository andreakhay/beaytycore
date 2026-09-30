"""Bounded process-local state and private photo bytes for a short demo session."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.consultation.models import (ConsultationMessage, ConsultationState, FeatureId,
                                     GenerationDetail, PhotoReference, Preferences,
                                     RecommendationGeneration, RecommendationSet,
                                     UpdateConsultation)


LIFETIME = timedelta(hours=1)


def now() -> datetime:
    return datetime.now(timezone.utc)


class StoreFullError(RuntimeError):
    pass


class StaleConsultationError(RuntimeError):
    pass


class GenerationConflict(RuntimeError):
    pass


@dataclass
class _Entry:
    state: ConsultationState
    photo_bytes: bytes | None = None
    results: dict[str, dict] | None = None
    turn_in_progress: bool = False


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
            self._assert_idle(entry)
            current = now()
            entry.state = entry.state.model_copy(update={
                "photo": PhotoReference(id=uuid4(), content_type=content_type, width=width, height=height),
                "stage": "collecting", "recommendations": None, "generations": [],
                "conversation_status": "not_started", "messages": [],
                "selected_recommendation_id": None,
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            entry.photo_bytes = content
            entry.results = None
            return entry.state.model_copy(deep=True)

    def update(self, consultation_id: UUID, change: UpdateConsultation) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            self._assert_idle(entry)
            preferences = entry.state.preferences
            if change.preferences is not None:
                fields = change.preferences.model_dump(exclude_unset=True)
                preferences = preferences.model_copy(update=fields)
            messages = list(entry.state.messages)
            current = now()
            if change.message is not None:
                if len(messages) >= 12:
                    raise ValueError("Consultation message limit reached.")
                messages.append(ConsultationMessage(content=change.message, created_at=current))
            entry.state = entry.state.model_copy(update={
                "preferences": preferences, "messages": messages, "stage": "collecting",
                "conversation_status": "more_information" if messages else "not_started",
                "recommendations": None, "generations": [], "selected_recommendation_id": None,
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            entry.results = None
            return entry.state.model_copy(deep=True)

    def save_recommendations(self, consultation_id: UUID, expected_update: datetime,
                             recommendations: RecommendationSet) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            self._assert_idle(entry)
            if entry.state.updated_at != expected_update:
                raise StaleConsultationError("Consultation changed while recommendations were prepared.")
            current = now()
            entry.state = entry.state.model_copy(update={
                "recommendations": recommendations, "stage": "recommended",
                "generations": [RecommendationGeneration(recommendation_id=row.id)
                                for row in recommendations.recommendations],
                "selected_recommendation_id": None,
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            entry.results = {}
            return entry.state.model_copy(deep=True)

    def begin_turn(self, consultation_id: UUID, message: str | None) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            self._assert_idle(entry)
            if entry.state.photo is None:
                raise GenerationConflict("Upload a photo before starting the conversation.")
            if entry.state.recommendations is not None:
                raise GenerationConflict("This consultation already has recommendations.")
            if len(entry.state.messages) + (1 if message else 0) + 1 > 12:
                raise GenerationConflict("Consultation message limit reached.")
            entry.turn_in_progress = True
            return entry.state.model_copy(deep=True)

    def finish_turn(self, consultation_id: UUID, expected_update: datetime,
                    message: str | None, assistant_message: str, status: str,
                    preferences: Preferences, recommendations: RecommendationSet | None) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            if not entry.turn_in_progress or entry.state.updated_at != expected_update:
                raise StaleConsultationError("Consultation changed while the assistant responded.")
            current = now()
            messages = list(entry.state.messages)
            if message:
                messages.append(ConsultationMessage(role="user", content=message, created_at=current))
            messages.append(ConsultationMessage(role="assistant", content=assistant_message, created_at=current))
            entry.state = entry.state.model_copy(update={
                "preferences": preferences, "messages": messages,
                "conversation_status": status,
                "stage": "recommended" if recommendations else "collecting",
                "recommendations": recommendations,
                "generations": [RecommendationGeneration(recommendation_id=row.id)
                                for row in recommendations.recommendations] if recommendations else [],
                "selected_recommendation_id": None,
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            entry.results = {} if recommendations else None
            entry.turn_in_progress = False
            return entry.state.model_copy(deep=True)

    def abort_turn(self, consultation_id: UUID) -> None:
        with self._lock:
            try:
                self._entry(consultation_id).turn_in_progress = False
            except KeyError:
                pass

    @staticmethod
    def _assert_idle(entry: _Entry) -> None:
        if entry.turn_in_progress or any(row.status == "generating" for row in entry.state.generations):
            raise GenerationConflict("A recommendation is still generating. Wait for it to finish.")

    @staticmethod
    def _generation(entry: _Entry, recommendation_id: str) -> RecommendationGeneration:
        for row in entry.state.generations:
            if row.recommendation_id == recommendation_id:
                return row
        raise KeyError("Recommendation not found.")

    def detail(self, consultation_id: UUID, recommendation_id: str) -> GenerationDetail:
        with self._lock:
            entry = self._entry(consultation_id)
            result = (entry.results or {}).get(recommendation_id)
            return GenerationDetail(generation=self._generation(entry, recommendation_id), result=result)

    def begin_generation(self, consultation_id: UUID, recommendation_id: str,
                         expected_update: datetime) -> tuple[bytes, str]:
        with self._lock:
            entry = self._entry(consultation_id)
            if entry.state.updated_at != expected_update:
                raise StaleConsultationError("Consultation changed before generation started.")
            self._assert_idle(entry)
            row = self._generation(entry, recommendation_id)
            if row.status == "completed":
                raise GenerationConflict("This recommendation is already complete.")
            if entry.state.photo is None or entry.photo_bytes is None:
                raise GenerationConflict("Consultation photo is unavailable.")
            changed = row.model_copy(update={"status": "generating", "attempts": row.attempts + 1,
                                             "error": None, "result_available": False})
            current = now()
            entry.state = entry.state.model_copy(update={
                "generations": [changed if item.recommendation_id == recommendation_id else item
                                for item in entry.state.generations],
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            return entry.photo_bytes, entry.state.photo.content_type

    def finish_generation(self, consultation_id: UUID, recommendation_id: str,
                          result: dict | None, error: str | None = None) -> GenerationDetail:
        with self._lock:
            entry = self._entry(consultation_id)
            row = self._generation(entry, recommendation_id)
            if row.status != "generating":
                raise GenerationConflict("Recommendation is not generating.")
            changed = row.model_copy(update={"status": "completed" if result is not None else "failed",
                                             "error": error, "result_available": result is not None})
            if result is not None:
                assert entry.results is not None
                entry.results[recommendation_id] = result
            current = now()
            entry.state = entry.state.model_copy(update={
                "generations": [changed if item.recommendation_id == recommendation_id else item
                                for item in entry.state.generations],
                "updated_at": current, "expires_at": current + LIFETIME,
            })
            return GenerationDetail(generation=changed, result=result)

    def select(self, consultation_id: UUID, recommendation_id: str) -> ConsultationState:
        with self._lock:
            entry = self._entry(consultation_id)
            if self._generation(entry, recommendation_id).status != "completed":
                raise GenerationConflict("Generate this recommendation before selecting it.")
            entry.state = entry.state.model_copy(update={
                "selected_recommendation_id": recommendation_id, "updated_at": now(),
            })
            return entry.state.model_copy(deep=True)
