"""Text-only Gemini consultation. The backend owns state, catalog and validation."""

import asyncio
import json
import logging
import os
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.consultation.models import (CatalogStyle, ConsultationState,
                                     ConversationProposal, FeatureId)

LOGGER = logging.getLogger(__name__)
SYSTEM = (
    "You are a concise beauty consultant inside an application with a fixed style catalog. "
    "Ask only useful, nonrepetitive questions; usually a few answers are enough. "
    "The photo is not visible to you. Never infer appearance or claim a look will be perfect. "
    "Extract only preferences the user states or clearly implies. Respect 'no preference'. "
    "If enough is known, choose exactly three different primary style IDs for the selected "
    "service from the supplied candidates. Complementary styles, if any, must come from "
    "the other supplied services. Give a brief reason grounded in the user's words. "
    "If information is still useful, ask one concise next question instead. "
    "Do not invent style IDs, prices, appointment availability, visual observations, or "
    "implementation details. Return only the requested structured response."
)


class ProviderFailure(RuntimeError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


class ConversationProvider(Protocol):
    async def turn(self, state: ConsultationState, message: str | None,
                   candidates: dict[FeatureId, list[CatalogStyle]]) -> ConversationProposal: ...


class GeminiProvider:
    def __init__(self, *, model: str | None = None, api_key: str | None = None,
                 transport=None):
        self.model = model or os.getenv("CONSULTATION_GEMINI_MODEL", "gemini-3.8-flash")
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.transport = transport

    async def turn(self, state: ConsultationState, message: str | None,
                   candidates: dict[FeatureId, list[CatalogStyle]]) -> ConversationProposal:
        if not self.api_key:
            raise ProviderFailure("missing_key")
        context = {
            "primary_service": state.primary_service,
            "preferences": state.preferences.model_dump(exclude_none=True),
            "conversation": [{"role": row.role, "text": row.content} for row in state.messages],
            "latest_user_message": message,
            "eligible_styles": {
                feature: [{"feature": feature, "style_id": row.style_id,
                           "name": row.name, "tags": row.tags, "description": row.description}
                          for row in styles]
                for feature, styles in candidates.items()
            },
        }
        try:
            if self.transport is not None:
                raw = await self.transport(context)
            else:
                raw = await self._request(context)
            if isinstance(raw, str):
                return ConversationProposal.model_validate_json(raw)
            return ConversationProposal.model_validate(raw)
        except ProviderFailure:
            raise
        except (ValidationError, ValueError, TypeError):
            LOGGER.warning("Gemini response failed structured validation")
            raise ProviderFailure("malformed_response") from None

    async def _request(self, context: dict):
        # Import only in Gemini mode. The installed SDK's retry default can make
        # multiple attempts; attempts=1 makes this one bounded request.
        from google import genai
        from google.genai import errors, types

        # The SDK otherwise prefers aiohttp when installed. An explicit HTTPX
        # client honors the same proxy configuration used by this application.
        async with httpx.AsyncClient(trust_env=True) as http_client:
            client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(
                api_version="v1", timeout=30000, httpx_async_client=http_client,
                retry_options=types.HttpRetryOptions(attempts=1)))
            try:
                response = await asyncio.wait_for(client.aio.models.generate_content(
                    model=self.model,
                    contents=json.dumps(context, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM,
                        response_mime_type="application/json",
                        # This full JSON Schema field accepts the strict
                        # Pydantic model's additionalProperties constraints.
                        response_json_schema=ConversationProposal.model_json_schema(),
                    )), timeout=35)
                return response.parsed if response.parsed is not None else response.text
            except asyncio.TimeoutError:
                LOGGER.warning("Gemini consultation timeout")
                raise ProviderFailure("timeout") from None
            except errors.APIError as exc:
                code = getattr(exc, "code", None)
                category = ("rate_limit" if code == 429 else "model_unavailable"
                            if code == 404 else "provider_error")
                LOGGER.warning("Gemini consultation failure category=%s status=%s", category, code)
                raise ProviderFailure(category) from None
            except (OSError, httpx.HTTPError) as exc:
                LOGGER.warning("Gemini consultation connection failure exception=%s", type(exc).__name__)
                raise ProviderFailure("network_error") from None
            finally:
                await client.aio.aclose()
