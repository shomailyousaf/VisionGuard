import sys
import types

mock_inference = types.ModuleType("src.inference")
mock_inference.predict_image = lambda image_bytes: {
    "label": "Real",
    "confidence": 0.9,
    "ai_probability": 0.1
}
sys.modules["src.inference"] = mock_inference

import app as visionguard


def test_health_endpoint():
    client = visionguard.app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"
    assert response.json["model"] == "VisionGuardClassifier"


def test_allowed_file():
    assert visionguard.allowed_file("photo.jpg")
    assert visionguard.allowed_file("photo.PNG")
    assert not visionguard.allowed_file("document.pdf")
    assert not visionguard.allowed_file("photo")


def test_homepage():
    client = visionguard.app.test_client()
    response = client.get("/")

    assert response.status_code == 200
