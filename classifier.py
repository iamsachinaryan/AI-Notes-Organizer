"""
classifier.py — AI-First Subject Classifier
Uses Gemini AI as PRIMARY classifier. No filename guessing.
"""
import json
import logging
import os
import time
import threading
import io
from dataclasses import dataclass
from typing import Optional, Union
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    subject: str
    confidence: float
    source: str
    latency_ms: int


class GeminiClient:
    _instance = None
    _init_lock = threading.Lock()

    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.json_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=256,
        )

    @classmethod
    def instance(cls) -> "GeminiClient":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    api_key = os.getenv("GEMINI_API_KEY", "").strip()
                    if not api_key:
                        raise EnvironmentError("GEMINI_API_KEY missing in .env")
                    cls._instance = cls(api_key)
        return cls._instance


# ─── PRIMARY: Classify from extracted OCR text ───────────────────────────────

def classify_from_text(text: str) -> Optional[str]:
    """Send OCR text to Gemini and get subject. Returns None on failure."""
    if not text or len(text.strip()) < 20:
        return None

    prompt = f"""You are an expert academic subject classifier.
Read the following notes and identify the EXACT academic subject.

Rules:
- Return ONLY valid JSON: {{"subject": "Subject Name"}}
- Subject must be a real academic course name (e.g., "Mathematics", "Operating Systems", "Data Structures", "Physics", "Chemistry", "History")
- Be specific. Don't say "General Studies" if you can identify it.
- Title Case only.

[NOTES START]
{text[:4000]}
[NOTES END]
"""
    try:
        g = GeminiClient.instance()
        response = g.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=g.json_config
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        subject = str(parsed.get("subject", "")).strip()
        if subject and len(subject) > 2:
            logger.info(f"✅ Classified from text: {subject}")
            return subject
    except Exception as e:
        logger.warning(f"Text classification failed: {e}")
    return None


# ─── SECONDARY: Classify by sending PDF page IMAGE to Gemini ─────────────────

def classify_from_pdf_image(pdf_path: Union[str, Path]) -> Optional[str]:
    """Convert first page of PDF to image and ask Gemini to classify it visually."""
    try:
        from pdf2image import convert_from_path
        import cv2
        import numpy as np
        from PIL import Image

        pdf_path = Path(pdf_path)
        logger.info("🖼️ OCR text insufficient — sending page image to Gemini for visual classification...")

        images = convert_from_path(str(pdf_path), first_page=1, last_page=1, dpi=120, fmt="ppm")
        if not images:
            return None

        # Convert to JPEG bytes
        pil_img = images[0]
        w, h = pil_img.size
        scale = min(1.0, 1200 / max(w, h))
        if scale < 1.0:
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=80)
        jpeg_bytes = buf.getvalue()

        prompt = """You are an expert academic subject classifier.
Look at this page from a student's notes or textbook.
Identify the EXACT academic subject.

Return ONLY valid JSON: {"subject": "Subject Name"}

Subject must be a real academic course (e.g., "Mathematics", "Trigonometry", "Operating Systems", "Data Structures & Algorithms", "Physics", "Chemistry", "Biology", "History", "Computer Networks", "Java Programming", "Database Management System").
Be specific. Title Case only.
"""
        g = GeminiClient.instance()
        response = g.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=prompt)
            ],
            config=g.json_config
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        subject = str(parsed.get("subject", "")).strip()
        if subject and len(subject) > 2:
            logger.info(f"✅ Classified from image: {subject}")
            return subject
    except Exception as e:
        logger.warning(f"Image classification failed: {e}")
    return None


# ─── LAST RESORT: Ask Gemini to guess from filename only ─────────────────────

def classify_from_filename(filename: str) -> str:
    """Ask Gemini to guess subject from filename — last resort only."""
    try:
        clean_name = filename.replace("temp_", "").replace(".pdf", "").replace("_", " ").replace("-", " ")
        prompt = f"""A student's file is named: "{clean_name}"
Based on this filename, what academic subject do these notes most likely belong to?

Return ONLY valid JSON: {{"subject": "Subject Name"}}
Subject must be a real academic course name. Title Case only.
If truly unclear, return {{"subject": "General Studies"}}
"""
        g = GeminiClient.instance()
        response = g.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=g.json_config
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        subject = str(parsed.get("subject", "General Studies")).strip()
        logger.info(f"✅ Classified from filename via AI: {subject}")
        return subject if subject else "General Studies"
    except Exception as e:
        logger.warning(f"Filename classification failed: {e}")
        return "General Studies"


# ─── MAIN ENTRY POINT ────────────────────────────────────────────────────────

def get_subject_from_text(
    text: str,
    correlation_id: Optional[str] = None,
    pdf_path: Optional[Union[str, Path]] = None
) -> ClassificationResult:
    """
    Classify subject using 3-tier AI approach:
    1. From OCR text (best)
    2. From PDF page image (if text is empty/poor)
    3. From filename via Gemini AI (last resort — NOT keyword matching)
    """
    start_time = time.perf_counter()
    fname = str(correlation_id or "")

    # Tier 1: Classify from extracted OCR text
    subject = classify_from_text(text)
    if subject:
        return ClassificationResult(subject, 0.97, "gemini_text", int((time.perf_counter() - start_time) * 1000))

    # Tier 2: Classify by sending PDF page image to Gemini
    if pdf_path:
        subject = classify_from_pdf_image(pdf_path)
        if subject:
            return ClassificationResult(subject, 0.95, "gemini_vision", int((time.perf_counter() - start_time) * 1000))

    # Tier 3: Ask Gemini to guess from filename (AI-based, not keyword matching)
    subject = classify_from_filename(fname)
    return ClassificationResult(subject, 0.80, "gemini_filename", int((time.perf_counter() - start_time) * 1000))