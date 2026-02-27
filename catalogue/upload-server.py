#!/usr/bin/env python3
"""Micro-serveur d'upload d'images pour le catalogue Hotwav.

Usage:
    pip install flask pillow
    UPLOAD_TOKEN=secret python3 upload-server.py

Options (variables d'environnement):
    UPLOAD_TOKEN  — token d'auth (obligatoire)
    UPLOAD_PORT   — port d'ecoute (defaut: 8090)
"""

import os
import re
import unicodedata
from pathlib import Path

from flask import Flask, request, jsonify
from PIL import Image

app = Flask(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
IMGS_DIR = SCRIPT_DIR / "imgs"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_DIMENSION = 1200
PORT = int(os.environ.get("UPLOAD_PORT", 8090))
TOKEN = os.environ.get("UPLOAD_TOKEN", "")


def _slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "X-Upload-Token, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


@app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        return "", 204

    if not TOKEN:
        return jsonify({"error": "UPLOAD_TOKEN not configured on server"}), 500
    if request.headers.get("X-Upload-Token") != TOKEN:
        return jsonify({"error": "Invalid or missing token"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    product_id = request.form.get("product_id", "").strip()
    color_name = request.form.get("color_name", "").strip()
    if not product_id or not color_name:
        return jsonify({"error": "product_id and color_name are required"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        exts = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return jsonify({"error": f"Format not allowed. Accepted: {exts}"}), 400

    file.seek(0, os.SEEK_END)
    if file.tell() > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large (max {MAX_FILE_SIZE // (1024 * 1024)} Mo)"}), 400
    file.seek(0)

    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
        img = Image.open(file)
    except Exception:
        return jsonify({"error": "Invalid image file"}), 400

    if img.mode not in ("RGB", "RGBA", "LA", "PA"):
        img = img.convert("RGBA")

    w, h = img.size
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        ratio = min(MAX_DIMENSION / w, MAX_DIMENSION / h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    filename = f"{_slugify(product_id)}-{_slugify(color_name)}.png"
    IMGS_DIR.mkdir(exist_ok=True)
    img.save(IMGS_DIR / filename, "PNG", optimize=True)

    return jsonify({"path": f"imgs/{filename}"}), 200


if __name__ == "__main__":
    if not TOKEN:
        print("\033[33m⚠  UPLOAD_TOKEN not set — all uploads will be rejected\033[0m")
    print(f"📁 Images dir: {IMGS_DIR}")
    print(f"🚀 Upload server on http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
