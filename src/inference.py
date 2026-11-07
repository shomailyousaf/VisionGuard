import os
from pathlib import Path

import mlflow
import tensorflow as tf
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
MODEL_URI = os.getenv(
    "MODEL_URI",
    "models:/VisionGuardClassifier@champion"
)
THRESHOLD = float(os.getenv("PREDICTION_THRESHOLD", "0.5"))

if not TRACKING_URI:
    raise ValueError("MLFLOW_TRACKING_URI is missing from .env")

mlflow.set_tracking_uri(TRACKING_URI)
mlflow.set_registry_uri(TRACKING_URI)

MODEL = mlflow.keras.load_model(MODEL_URI)

IMAGE_SIZE = (224, 224)

def preprocess_image(image_bytes):
    image = tf.io.decode_image(
        image_bytes,
        channels=3,
        expand_animations=False
    )

    image.set_shape([None, None, 3])

    image = tf.image.resize_with_pad(
        image,
        IMAGE_SIZE[0],
        IMAGE_SIZE[1]
    )

    image = tf.cast(image, tf.float32) / 255.0

    return tf.expand_dims(image, axis=0)

def predict_image(image_bytes):
    image = preprocess_image(image_bytes)

    probability = float(
        MODEL.predict(image, verbose=0)[0][0]
    )

    label = "AI-generated" if probability >= THRESHOLD else "Real"

    confidence = (
        probability if label == "AI-generated"
        else 1.0 - probability
    )

    return {
        "label": label,
        "confidence": confidence,
        "ai_probability": probability
    }