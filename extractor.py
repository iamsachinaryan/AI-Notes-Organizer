"""
extractor.py — Enterprise-Grade PDF OCR (ZOMBIE-KILLER EDITION)
"""
import io
import logging
import os
import time
import threading
import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import cv2
import numpy as np
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("SmartExtractor")

RENDER_DPI = 150  
OCR_PROMPT = """Extract ALL text from this image EXACTLY as written. Return ONLY the raw extracted text."""

@dataclass
class ExtractionResult:
    text: str
    pages_scanned: int
    pages_failed: int
    total_pages: int
    pages_sampled: List[int]
    models_used: dict[int, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

class GenAIClientManager:
    _client: Optional[genai.Client] = None
    _lock = threading.Lock()

    @classmethod
    def get_client(cls) -> genai.Client:
        with cls._lock:
            if cls._client is None:
                api_key = os.getenv("GEMINI_API_KEY", "").strip()
                cls._client = genai.Client() if not api_key else genai.Client(api_key=api_key)
            return cls._client

class ImageProcessor:
    @staticmethod
    def enhance_for_ocr(pil_img: Image.Image) -> bytes:
        w, h = pil_img.size
        scale = min(1.0, 1800 / max(w, h))
        if scale < 1.0:
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)

        cv_img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.GaussianBlur(gray, (5, 5), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        equalized = clahe.apply(denoised)
        binary = cv2.adaptiveThreshold(equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10)
        if np.sum(binary == 0) > np.sum(binary == 255): binary = cv2.bitwise_not(binary)

        buf = io.BytesIO()
        Image.fromarray(cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)).save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()

class EnterprisePDFExtractor:
    @classmethod
    def _process_single_page(cls, pdf_path: str, page_num: int, client: genai.Client) -> dict:
        try:
            images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=RENDER_DPI, fmt="ppm")
            if not images: return {"page": page_num, "status": "failed", "error": "Blank"}

            jpeg_bytes = ImageProcessor.enhance_for_ocr(images[0])
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Part.from_text(text=OCR_PROMPT), types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")],
                config=types.GenerateContentConfig(temperature=0.0)
            )
            if not response.candidates: return {"page": page_num, "status": "failed", "error": "Blocked"}
            return {"page": page_num, "status": "success", "text": response.text.strip(), "model": "gemini-2.5-flash"}
        except Exception as e:
            return {"page": page_num, "status": "failed", "error": str(e)}

    @classmethod
    def extract(cls, pdf_path: Union[str, Path]) -> ExtractionResult:
        pdf_path = Path(pdf_path)
        info = pdfinfo_from_path(str(pdf_path))
        total_pages = info.get("Pages", 0)
        if total_pages == 0: raise ValueError("PDF has 0 pages.")

        pages_to_scan = list(range(1, total_pages + 1)) if total_pages <= 3 else sorted(list(set([1, total_pages // 2, total_pages])))
        logger.info(f"📄 Target: '{pdf_path.name}' | Scanning: {pages_to_scan} | Mode: 🚀 STRICT PARALLEL")

        client = GenAIClientManager.get_client()
        texts_dict, models_used, pages_failed, warnings = {}, {}, 0, []

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(pages_to_scan))
        future_to_page = {executor.submit(cls._process_single_page, str(pdf_path), p, client): p for p in pages_to_scan}
        
        try:
            for future in concurrent.futures.as_completed(future_to_page, timeout=15.0): # 15 SECONDS MAX
                page_num = future_to_page[future]
                res = future.result()
                if res["status"] == "success" and res.get("text"):
                    texts_dict[page_num] = res["text"]
                    models_used[page_num] = res["model"]
                    logger.info(f"✅ Success on Page {page_num}")
                else:
                    pages_failed += 1
        except concurrent.futures.TimeoutError:
            logger.error("🚨 CRITICAL: Google Server Hang Detected! Abandoning Zombie Threads.")
            warnings.append("API timed out.")

        executor.shutdown(wait=False, cancel_futures=True) # ZOMBIE KILLER
        final_text = "\n\n".join([texts_dict[p] for p in sorted(texts_dict.keys())])

        return ExtractionResult(final_text, len(pages_to_scan) - pages_failed, pages_failed, total_pages, pages_to_scan, models_used, warnings)

def extract_smart_text_with_google_vision(pdf_path: Union[str, Path]) -> ExtractionResult:
    return EnterprisePDFExtractor.extract(pdf_path)