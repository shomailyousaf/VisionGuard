
import os
import sqlite3
from pathlib import Path

import psycopg
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from psycopg.rows import dict_row
from werkzeug.utils import secure_filename

from src.inference import predict_image

ROOT = Path(__file__).resolve().parent

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    str(ROOT / "visionguard_history.db")
)

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "5242880"))

MODEL_NAME = "VisionGuardClassifier"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "visionguard-local-key")
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


def get_db_connection():
    if DATABASE_URL:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db_connection() as connection:
        if DATABASE_URL:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS prediction_history (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    label TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_name TEXT
                )
            """)
        else:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS prediction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    label TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_name TEXT
                )
            """)


def execute_query(connection, query, parameters=()):
    if DATABASE_URL:
        query = query.replace("?", "%s")

    return connection.execute(query, parameters)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        flash("Please select an image to upload.")
        return redirect(url_for("index"))

    file = request.files["image"]

    if not file.filename:
        flash("No file was selected.")
        return redirect(url_for("index"))

    safe_filename = secure_filename(file.filename)

    if not safe_filename:
        flash("Invalid filename.")
        return redirect(url_for("index"))

    if not allowed_file(safe_filename):
        flash("Unsupported file type. Please upload JPG, JPEG or PNG.")
        return redirect(url_for("index"))

    image_bytes = file.read()

    if not image_bytes:
        flash("The uploaded file is empty.")
        return redirect(url_for("index"))

    try:
        result = predict_image(image_bytes)
    except Exception:
        flash("The uploaded file is not a valid or supported image.")
        return redirect(url_for("index"))

    with get_db_connection() as connection:
        execute_query(
            connection,
            """
            INSERT INTO prediction_history
            (filename, label, confidence, model_name)
            VALUES (?, ?, ?, ?)
            """,
            (
                safe_filename,
                result["label"],
                result["confidence"],
                MODEL_NAME
            )
        )

    return render_template(
        "result.html",
        filename=safe_filename,
        result=result
    )


@app.route("/history")
def history():
    with get_db_connection() as connection:
        records = execute_query(
            connection,
            """
            SELECT * FROM prediction_history
            ORDER BY created_at DESC
            """
        ).fetchall()

    return render_template("history.html", records=records)


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "model": MODEL_NAME,
        "alias": "champion"
    })


@app.errorhandler(413)
def file_too_large(error):
    return render_template(
        "error.html",
        message="File is too large. Maximum upload size is 5 MB."
    ), 413


@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "error.html",
        message="The requested page could not be found."
    ), 404


initialize_database()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
