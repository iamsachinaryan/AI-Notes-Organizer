"""
extractor.py — Enterprise-Grade PDF OCR with Smart Tiered Routing
====================================================================
Architecture: ImageProcessor → SmartRouter → FallbackEngine → Gemini/Gemma

Routing Strategy:
    - Page 1    : Gemini 3 Flash (High Accuracy, Low Quota)
    - Page 2-3  : Gemini 3.1 Flash Lite (High Volume, Heavy Lifter)
    - Page 4+   : Gemini 2.5 Flash (Load Balancing)
    - Fallback  : Gemma 3 4B (Ultimate Survival Mode for Zero Downtime)

Author: Next-Level Engineering
"""

import io
import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image, ImageFilter

# ✅ Naya SDK (Future-Proof)
from google import genai
from google.genai import types, errors

# ── Logger Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SmartExtractor")

# ── Constants & Configuration ────────────────────────────────────────────────
RENDER_DPI         = 300
MAX_PAYLOAD_BYTES  = 4 * 1024 * 1024  # 4MB safe limit
PER_CALL_TIMEOUT   = 30.0

OCR_PROMPT = """You are an expert OCR engine.
Your ONLY job: extract ALL text from this image EXACTLY as written.
- Extract every single word, number, and symbol.
- Preserve line breaks.
- Support both Hindi (Devanagari) and English seamlessly.
- Do NOT translate, summarize, or explain.
- Return ONLY the raw extracted text."""

# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class ExtractionResult:
    """Structured output tracking the entire extraction journey."""
    text:            str
    pages_scanned:   int
    pages_failed:    int
    total_pages:     int
    pages_sampled:   List[int]
    models_used:     dict[int, str] = field(default_factory=dict)  # PageNum -> Model Name
    warnings:        List[str]      = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"ExtractionResult(total_pages={self.total_pages}, "
            f"scanned={self.pages_scanned}, failed={self.pages_failed}, "
            f"chars_extracted={len(self.text)})"
        )


# ── The "Master Plan" Router ─────────────────────────────────────────────────

class SmartRouter:
    """
    Decides the Waterfall Strategy for each page.
    Returns a list of models to try in order (Primary -> Fallback 1 -> Fallback 2).
    """
    
    # ✅ Exact API Strings from Google API
    MODEL_VIP      = "gemini-3-flash-preview"           # VIP Treatment (Page 1)
    MODEL_LITE     = "gemini-3.1-flash-lite-preview"    # Heavy Lifter (Page 2, 3)
    MODEL_BALANCER = "gemini-2.5-flash"                 # Load Balancer (Remaining Pages)
    MODEL_SURVIVAL = "gemma-3-4b-it"                    # Ultimate Survival (Zero Downtime)

    @classmethod
    def get_routing_chain(cls, page_num: int) -> List[str]:
        """Returns the fallback chain for a specific page."""
        if page_num == 1:
            # VIP Treatment for Page 1
            return [cls.MODEL_VIP, cls.MODEL_LITE, cls.MODEL_SURVIVAL]
        
        elif page_num in [2, 3]:
            # Heavy Lifting for Index/Middle pages
            return [cls.MODEL_LITE, cls.MODEL_BALANCER, cls.MODEL_SURVIVAL]
        
        else:
            # Load Balancing for random remaining pages
            return [cls.MODEL_BALANCER, cls.MODEL_LITE, cls.MODEL_SURVIVAL]


# ── Thread-Safe API Client ───────────────────────────────────────────────────

class GenAIClientManager:
    _client: Optional[genai.Client] = None
    _lock = threading.Lock()

    @classmethod
    def get_client(cls) -> genai.Client:
        with cls._lock:
            if cls._client is None:
                api_key = os.getenv("GEMINI_API_KEY", "").strip()
                if not api_key:
                    raise EnvironmentError("GEMINI_API_KEY not found in environment.")
                cls._client = genai.Client(api_key=api_key)
                logger.info("✅ Google GenAI Client Initialized.")
            return cls._client


# ── Enterprise Image Processor Pipeline ──────────────────────────────────────

class ImageProcessor:
    """Encapsulates all OpenCV and PIL magic for image enhancement."""
    
    @staticmethod
    def enhance_for_ocr(pil_img: Image.Image, page_num: int) -> Image.Image:
        # 1. Upscale
        w, h = pil_img.size
        long_edge = max(w, h)
        if long_edge < 1800:
            scale = 1800 / long_edge
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # 2. Convert to OpenCV
        cv_img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 3. Deskew (Tilt Correction)
        gray = ImageProcessor._deskew(gray, page_num)

        # 4. Denoise & CLAHE (Fixing phone lighting)
        denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        equalized = clahe.apply(denoised)

        # 5. Adaptive Threshold
        binary = cv2.adaptiveThreshold(
            equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=31, C=10
        )

        # 6. Dark Background Invert
        if np.sum(binary == 0) > np.sum(binary == 255):
            binary = cv2.bitwise_not(binary)

        # 7. Final Output & Sharpen
        rgb = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
        pil_out = Image.fromarray(rgb).filter(ImageFilter.SHARPEN)
        return pil_out

    @staticmethod
    def _deskew(gray: np.ndarray, page_num: int) -> np.ndarray:
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
            if lines is None or len(lines) < 5: return gray
            angles = [np.degrees(line[0][1]) - 90 for line in lines[:20] if -45 < np.degrees(line[0][1]) - 90 < 45]
            if not angles: return gray
            median_angle = float(np.median(angles))
            if abs(median_angle) < 0.5 or abs(median_angle) > 15: return gray
            
            h, w = gray.shape
            M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
            return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            return gray

    @staticmethod
    def encode_to_jpeg(pil_img: Image.Image) -> bytes:
        for quality in [95, 85, 75, 60]:
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
            content = buf.getvalue()
            if len(content) <= MAX_PAYLOAD_BYTES:
                return content
        # Last resort
        w, h = pil_img.size
        pil_img = pil_img.resize((w // 2, h // 2), Image.LANCZOS)
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=60, optimize=True)
        return buf.getvalue()


# ── The Core Extractor Engine ────────────────────────────────────────────────

class EnterprisePDFExtractor:
    
    @staticmethod
    def _get_pages_to_sample(total_pages: int) -> List[int]:
        if total_pages <= 5: return list(range(1, total_pages + 1))
        pages = [1, 2, 3]
        remaining = list(range(4, total_pages + 1))
        pages.extend(random.sample(remaining, min(2, len(remaining))))
        return sorted(pages)

    @staticmethod
    def _execute_waterfall_ocr(client: genai.Client, jpeg_bytes: bytes, page_num: int) -> Tuple[str, str]:
        """
        Executes the Smart Routing. Tries models in sequence until one succeeds.
        Returns Tuple[Extracted_Text, Model_Used_Name]
        """
        routing_chain = SmartRouter.get_routing_chain(page_num)
        logger.info(f"Page {page_num} Routing Chain: {' ➔ '.join(routing_chain)}")

        for attempt, model_name in enumerate(routing_chain, 1):
            try:
                logger.debug(f"Attempt {attempt}/{len(routing_chain)} using model: {model_name}")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_text(text=OCR_PROMPT),
                        types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                    ],
                    config=types.GenerateContentConfig(temperature=0.0)
                )

                if not response.candidates:
                    logger.warning(f"[{model_name}] Blocked by safety filters.")
                    continue # Try next model in fallback chain

                text = response.text.strip() if response.text else ""
                logger.info(f"✅ Success on Page {page_num} using '{model_name}' ({len(text)} chars)")
                return text, model_name

            except errors.APIError as e:
                # Catch API limits (429) or Not Found (404) and trigger fallback
                error_code = getattr(e, 'code', 'Unknown')
                logger.warning(f"❌ [{model_name}] API Error ({error_code}): {e.message}. Triggering Fallback...")
                time.sleep(1) # Tiny pause before hitting the next model
                continue

            except Exception as e:
                logger.error(f"❌ [{model_name}] Unexpected Error: {e}. Triggering Fallback...")
                continue

        # If all fallbacks fail
        raise RuntimeError(f"All models in the routing chain failed for page {page_num}.")

    @classmethod
    def extract(cls, pdf_path: Union[str, Path]) -> ExtractionResult:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF missing: {pdf_path}")

        try:
            info = pdfinfo_from_path(str(pdf_path))
            total_pages = info.get("Pages", 0)
            if total_pages == 0: raise ValueError("PDF has 0 pages.")
        except Exception as exc:
            raise ValueError(f"Corrupted PDF: {pdf_path}") from exc

        pages_to_scan = cls._get_pages_to_sample(total_pages)
        logger.info(f"📄 Processing '{pdf_path.name}' | Total: {total_pages} | Scanning: {pages_to_scan}")

        client = GenAIClientManager.get_client()
        texts = []
        models_used = {}
        pages_failed = 0
        warnings = []

        for page_num in pages_to_scan:
            try:
                # 1. Render Page
                images = convert_from_path(str(pdf_path), first_page=page_num, last_page=page_num, dpi=RENDER_DPI, fmt="ppm", thread_count=2)
                if not images:
                    warnings.append(f"Page {page_num}: pdf2image returned nothing.")
                    pages_failed += 1
                    continue

                # 2. Enhance & Encode
                enhanced = ImageProcessor.enhance_for_ocr(images[0], page_num)
                jpeg_bytes = ImageProcessor.encode_to_jpeg(enhanced)

                # 3. Smart Waterfall OCR
                text, successful_model = cls._execute_waterfall_ocr(client, jpeg_bytes, page_num)
                
                if text:
                    texts.append(text)
                    models_used[page_num] = successful_model
                else:
                    warnings.append(f"Page {page_num}: Processed but returned zero text.")
                    models_used[page_num] = successful_model # It succeeded technically, but found no text
                    
            except Exception as e:
                logger.error(f"Page {page_num} completely failed after all fallbacks: {e}")
                warnings.append(f"Page {page_num} failed: {e}")
                pages_failed += 1

        final_text = "\n\n".join(texts)
        if not final_text.strip():
            warnings.append("Critical: Zero text extracted from entire document.")

        result = ExtractionResult(
            text=final_text,
            pages_scanned=len(pages_to_scan) - pages_failed,
            pages_failed=pages_failed,
            total_pages=total_pages,
            pages_sampled=pages_to_scan,
            models_used=models_used,
            warnings=warnings
        )
        logger.info(f"🏁 Extraction Complete: {result}")
        return result

# ── Entry Point (For Testing) ────────────────────────────────────────────────
if __name__ == "__main__":
    # Test karne ke liye is block ko use karein
    try:
        # result = EnterprisePDFExtractor.extract("Notessss.pdf")
        # print("\nExtracted Output Preview:\n", result.text[:500])
        pass
    except Exception as e:
        logger.error(f"Execution Failed: {e}")
# ── Backward Compatibility Wrapper (For app.py) ──────────────────────────────
def extract_smart_text_with_google_vision(pdf_path: Union[str, Path]) -> ExtractionResult:
    """
    Purani app.py ko bina change kiye naye Enterprise Engine se connect karne ke liye.
    """
    return EnterprisePDFExtractor.extract(pdf_path)