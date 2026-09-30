"""Small text-only live Gemini check through the real Consultation API.

Run from backend/: python ../scripts/consultation03_live_probe.py
Reads backend/.env through app.main. Never prints a key, photo, or URL.
"""

import json
import logging
from io import BytesIO
from pathlib import Path
import sys
import argparse

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.main import app


CASES = {
    "hairstyle": [
        "For graduation I want a clean, classy look that is easy to maintain. "
        "I do not care about length and want to avoid anything flashy.",
        "Low maintenance matters most. I have no other preferences.",
    ],
    "makeup": [
        "For a casual daytime outing I prefer natural, subtle makeup. "
        "I like a soft finish and want to avoid heavy eye makeup.",
        "Keep it understated; I have no other preferences.",
    ],
    "nails": [
        "For an evening event I want a bold, glossy nail look. "
        "Please avoid black. I prefer red or a rich color.",
        "A polished design is fine; I have no other preferences.",
    ],
}


def check(response, stage):
    if response.status_code != 200:
        raise RuntimeError(f"{stage}: HTTP {response.status_code}: {response.json().get('detail')}")
    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", choices=CASES.keys())
    args = parser.parse_args()
    logging.getLogger("ai_transport").disabled = True
    client = TestClient(app)
    mode = check(client.get("/consultations/mode"), "mode")
    if mode["provider"] != "gemini":
        raise RuntimeError("Set CONSULTATION_PROVIDER=gemini in backend/.env first")
    image = BytesIO()
    Image.new("RGB", (128, 128), "#8b96a3").save(image, format="PNG")
    result = {"provider": mode["provider"], "model": mode["model"], "cases": {}}
    for feature, answers in CASES.items():
        if args.feature and feature != args.feature:
            continue
        created = client.post("/consultations", json={"primary_service": feature})
        if created.status_code != 201:
            raise RuntimeError(f"{feature} create: HTTP {created.status_code}")
        identity = created.json()["id"]
        check(client.put(f"/consultations/{identity}/photo", files={
            "image": ("synthetic.png", image.getvalue(), "image/png")}), f"{feature} photo")
        turns = []
        for message in [None, *answers]:
            body = {} if message is None else {"message": message}
            turn = check(client.post(f"/consultations/{identity}/turn", json=body),
                         f"{feature} turn")
            turns.append({"user": message, "assistant": turn["assistant_message"],
                          "status": turn["status"]})
            if turn["status"] == "ready_for_recommendation":
                break
        if turns[-1]["status"] != "ready_for_recommendation":
            raise RuntimeError(f"{feature}: Gemini still needs information after bounded probe")
        state = check(client.get(f"/consultations/{identity}"), f"{feature} state")
        rows = turn["recommendations"]["recommendations"]
        if len(rows) != 3 or any(row["primary"]["feature"] != feature for row in rows):
            raise RuntimeError(f"{feature}: validated set did not contain three correct choices")
        if any(row["status"] != "pending" for row in state["generations"]):
            raise RuntimeError(f"{feature}: generation unexpectedly started")
        result["cases"][feature] = {"turns": turns, "preferences": state["preferences"],
                                    "styles": [row["primary"]["style_id"] for row in rows],
                                    "reasons": [row["reason"] for row in rows],
                                    "validated": True, "generation_started": False}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
