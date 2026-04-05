"""
classifier.py — Enterprise-Grade Subject Classifier using Google Gemini

Architecture:
    GeminiClient → InputSanitizer → CacheLayer → PromptBuilder
    → RetryEngine → ResponseValidator → FallbackHandler → ObservabilityLayer
    → ClassificationResult

Author  : Senior Review Pass
Version : 2.0.0 (Updated to new google.genai SDK)
"""

import hashlib
import json
import logging
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import threading

# ✅ Naya SDK Imports
from google import genai
from google.genai import types, errors

# ---------------------------------------------------------------------------
# Logger (library-safe: no basicConfig here)
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

KNOWN_SUBJECTS: set[str] = {
    "Mathematics", "Physics", "Chemistry", "Biology", "Computer Science",
    "English", "History", "Geography", "Economics", "Political Science",
    "Philosophy", "Psychology", "Sociology", "Statistics", "Accounting",
    "Business Studies", "Environmental Science", "General Studies",
}

KEYWORD_FALLBACK_MAP: dict[str, list[str]] = {
    "Mathematics":       ["algebra", "calculus", "trigonometry", "matrix", "derivative", "integral", "equation", "theorem", "proof", "polynomial"],
    "Physics":           ["newton", "force", "velocity", "momentum", "energy", "wave", "quantum", "thermodynamics", "optics", "relativity"],
    "Chemistry":         ["molecule", "atom", "bond", "reaction", "element", "compound", "periodic", "acid", "base", "oxidation"],
    "Biology":           ["cell", "dna", "rna", "protein", "evolution", "photosynthesis", "mitosis", "meiosis", "ecosystem", "organism"],
    "Computer Science":  ["algorithm", "recursion", "array", "stack", "queue", "binary", "sorting", "complexity", "pointer", "class"],
    "English":           ["grammar", "verb", "noun", "adjective", "prose", "poetry", "syntax", "paragraph", "essay", "literature"],
    "Economics":         ["demand", "supply", "gdp", "inflation", "market", "elasticity", "monopoly", "fiscal", "monetary", "price"],
    "History":           ["war", "empire", "revolution", "dynasty", "civilization", "colonialism", "treaty", "independence", "medieval", "ancient"],
    "Geography":         ["latitude", "longitude", "climate", "erosion", "tectonic", "river", "mountain", "continent", "ocean", "population"],
    "Statistics":        ["mean", "median", "variance", "probability", "distribution", "regression", "hypothesis", "sampling", "correlation", "standard deviation"],
}

MAX_RETRIES        = 3
BASE_BACKOFF_SEC   = 1.5 
MAX_BACKOFF_SEC    = 20.0
PER_CALL_TIMEOUT   = 15.0

CB_FAILURE_THRESHOLD = 5 
CB_RECOVERY_SEC      = 60

PROMPT_TEXT_CHAR_LIMIT = 3000

CACHE_TTL_SECONDS = 86_400 * 30


# ---------------------------------------------------------------------------
# Enums & Result Dataclass
# ---------------------------------------------------------------------------

class ClassificationSource(str, Enum):
    CACHE          = "cache"
    GEMINI_FLASH   = "gemini_flash"
    GEMINI_LITE    = "gemini_lite"      # Naya add kiya
    GEMMA_SURVIVAL = "gemma_survival"   # Naya add kiya (Tumhara Gemma)
    KEYWORD        = "keyword_fallback"
    DEFAULT        = "default_fallback"


@dataclass
class ClassificationResult:
    subject:     str
    confidence:  float 
    source:      ClassificationSource
    latency_ms:  int
    reasoning:   str  = ""
    attempts:    int  = 1
    cache_hit:   bool = False
    warnings:    list[str] = field(default_factory=list)

    @property
    def safe_filename_subject(self) -> str:
        name = unicodedata.normalize("NFKD", self.subject)
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)
        name = name.strip(". ")
        return name[:100] or "Unknown_Subject"

    def __str__(self) -> str:
        return (
            f"ClassificationResult(subject='{self.subject}', confidence={self.confidence:.0%}, "
            f"source={self.source.value}, latency={self.latency_ms}ms, cache_hit={self.cache_hit})"
        )


# ---------------------------------------------------------------------------
# Cache & Circuit Breaker (Same as before)
# ---------------------------------------------------------------------------

class _SubjectCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[ClassificationResult, float]] = {}
        self._lock  = threading.Lock()

    @staticmethod
    def _make_key(text: str) -> str:
        return hashlib.sha256(text[:500].encode("utf-8", errors="replace")).hexdigest()

    def get(self, text: str) -> Optional[ClassificationResult]:
        key = self._make_key(text)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            result, stored_at = entry
            if time.time() - stored_at > CACHE_TTL_SECONDS:
                del self._store[key]
                return None
            return result

    def set(self, text: str, result: ClassificationResult) -> None:
        key = self._make_key(text)
        with self._lock:
            self._store[key] = (result, time.time())

_cache = _SubjectCache()


class _CircuitBreaker:
    def __init__(self, threshold: int, recovery_sec: float) -> None:
        self._threshold    = threshold
        self._recovery_sec = recovery_sec
        self._failures     = 0
        self._opened_at: Optional[float] = None
        self._lock         = threading.Lock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None: return False
            if time.time() - self._opened_at >= self._recovery_sec: return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failures   = 0
            self._opened_at  = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._opened_at = time.time()
                logger.error("Circuit breaker OPEN. Gemini calls paused for %ds.", self._recovery_sec)

_circuit_breaker = _CircuitBreaker(CB_FAILURE_THRESHOLD, CB_RECOVERY_SEC)


# ---------------------------------------------------------------------------
# Gemini Client (Updated to new SDK)
# ---------------------------------------------------------------------------

class GeminiClient:
    _instance: Optional["GeminiClient"] = None
    _init_lock = threading.Lock()

    def __init__(self, api_key: str) -> None:
        # ✅ Naya Client Initialization
        self.client = genai.Client(api_key=api_key)
        
        # ✅ Configurations ko alag se store karte hain
        self.flash_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=256,
        )
        self.pro_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=256,
        )
        logger.info("GeminiClient initialised via new SDK.")

    @classmethod
    def instance(cls) -> "GeminiClient":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    api_key = os.getenv("GEMINI_API_KEY", "").strip()
                    if not api_key:
                        raise EnvironmentError("GEMINI_API_KEY not found in env.")
                    cls._instance = cls(api_key)
        return cls._instance


# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------

def _sanitize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text[:PROMPT_TEXT_CHAR_LIMIT].strip()

_FEW_SHOT_EXAMPLES = """
Examples (input → output):
{"text": "Newton's laws of motion, F=ma, velocity, acceleration, free body diagrams"}
→ {"subject": "Physics", "confidence": 0.98, "reasoning": "Classical mechanics terminology"}
{"text": "mitochondria, ATP synthesis, photosynthesis, cell membrane, DNA replication"}
→ {"subject": "Biology", "confidence": 0.97, "reasoning": "Cell biology and biochemistry terms"}
"""

def _build_prompt(sanitized_text: str) -> str:
    return f"""You are an expert academic classifier. Your job is to identify the EXACT, SPECIFIC subject of these notes.

RULES:
1. Return ONLY valid JSON.
2. "subject" MUST be the specific topic (e.g., "Compiler Design", "Organic Chemistry", "Linear Algebra", "Ancient History").
3. DO NOT use broad categories like "Computer Science" or "Mathematics" unless the notes are very generic.
4. "subject" format: Title Case, Max 3 words, no special characters (e.g., use "Operating Systems" not "intro to OS").
5. "confidence" is a float between 0.0 and 1.0.
6. "reasoning" is one short sentence.

[NOTES_START]
{sanitized_text}
[NOTES_END]
"""

# ✅ Naya Exception Handling
_RETRYABLE = (errors.APIError,)

def _call_with_retry(
    client: genai.Client,
    model_name: str,
    config: types.GenerateContentConfig,
    prompt: str,
    model_label: str,
) -> Optional[dict]:
    last_exc: Optional[Exception] = None
    backoff = BASE_BACKOFF_SEC

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug("Calling %s (attempt %d/%d)", model_label, attempt, MAX_RETRIES)

            # ✅ Naya API Call Syntax
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )

            if not response.candidates:
                logger.warning("%s response blocked by safety filters.", model_label)
                return None

            raw_text = response.text.strip() if response.text else ""
            raw_text = re.sub(r"^```json\s*|^```\s*|```$", "", raw_text, flags=re.MULTILINE).strip()

            parsed = json.loads(raw_text)
            _circuit_breaker.record_success()
            return parsed

        except _RETRYABLE as exc:
            last_exc = exc
            _circuit_breaker.record_failure()
            wait = min(backoff, MAX_BACKOFF_SEC)
            logger.warning("%s error on attempt %d: %s. Retrying in %.1fs.", model_label, attempt, exc, wait)
            time.sleep(wait)
            backoff *= 2

        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("%s returned unparseable JSON: %s", model_label, exc)
            return None
        except Exception as exc:
            logger.error("%s non-retryable error: %s", model_label, exc)
            _circuit_breaker.record_failure()
            return None

    logger.error("%s failed. Last error: %s", model_label, last_exc)
    return None


def _validate_and_normalise(parsed: dict, source_label: str) -> Optional[tuple[str, float, str]]:
    subject    = str(parsed.get("subject", "")).strip().title() # Title Case (Operating Systems)
    confidence = float(parsed.get("confidence", 0.0))
    reasoning  = str(parsed.get("reasoning", "")).strip()

    # Clean the subject name (Remove any weird symbols if AI hallucinated)
    import re
    subject = re.sub(r'[^A-Za-z0-9 ]+', '', subject).strip()
    
    if not subject:
        return "General Studies", confidence, reasoning
        
    return subject, max(0.0, min(1.0, confidence)), reasoning


def _keyword_classify(text: str) -> tuple[str, float]:
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for subject, keywords in KEYWORD_FALLBACK_MAP.items():
        hit = sum(1 for kw in keywords if kw in text_lower)
        if hit: scores[subject] = hit

    if not scores: return "General Studies", 0.3
    best = max(scores, key=lambda s: scores[s])
    total_hits = sum(scores.values())
    confidence = min(scores[best] / max(total_hits, 1), 0.75)
    return best, round(confidence, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_subject_from_text(text: str, correlation_id: Optional[str] = None) -> ClassificationResult:
    log_prefix = f"[{correlation_id}] " if correlation_id else ""
    start_time = time.perf_counter()
    warnings: list[str] = []

    if not text or not text.strip():
        return ClassificationResult(subject="Unreadable_Document", confidence=0.0, source=ClassificationSource.DEFAULT, latency_ms=0)

    cached = _cache.get(text)
    if cached is not None:
        cached.latency_ms = int((time.perf_counter() - start_time) * 1000)
        return cached

    clean_text = _sanitize_text(text)
    prompt = _build_prompt(clean_text)

    subject: Optional[str] = None
    confidence, reasoning = 0.0, ""
    source = ClassificationSource.DEFAULT
    attempts = 0

    try:
        g_client = GeminiClient.instance()
    except EnvironmentError as exc:
        warnings.append(str(exc))
        g_client = None

    # ── Layer 4: Gemini 2.5 Flash (First Choice) ──
    if g_client and not _circuit_breaker.is_open:
        parsed = _call_with_retry(g_client.client, "gemini-2.5-flash", g_client.flash_config, prompt, "gemini-flash")
        attempts += MAX_RETRIES if parsed is None else 1
        if parsed:
            validated = _validate_and_normalise(parsed, "gemini-flash")
            if validated:
                subject, confidence, reasoning = validated
                source = ClassificationSource.GEMINI_FLASH

    # ── Layer 5: Gemini 3.1 Flash Lite (The Heavy Lifter) ──
    if subject is None and g_client and not _circuit_breaker.is_open:
        parsed = _call_with_retry(g_client.client, "gemini-3.1-flash-lite-preview", g_client.pro_config, prompt, "gemini-lite")
        attempts += MAX_RETRIES if parsed is None else 1
        if parsed:
            validated = _validate_and_normalise(parsed, "gemini-lite")
            if validated:
                subject, confidence, reasoning = validated
                source = ClassificationSource.GEMINI_LITE

    # ── Layer 6: GEMMA 2B (The Ultimate AI Survival Mode) ──
    if subject is None and g_client and not _circuit_breaker.is_open:
        logger.info("%sGemma 2B Survival Mode Activated!", log_prefix)
        # Tumhari list se exact 2B string li hai: "gemma-3n-e2b-it"
        parsed = _call_with_retry(g_client.client, "gemma-3n-e2b-it", g_client.pro_config, prompt, "gemma-survival")
        attempts += MAX_RETRIES if parsed is None else 1
        if parsed:
            validated = _validate_and_normalise(parsed, "gemma-survival")
            if validated:
                subject, confidence, reasoning = validated
                source = ClassificationSource.GEMMA_SURVIVAL

    # ── Layer 7: Keyword Fallback (Dumb Backup - Only if internet/API is fully down) ──
    if subject is None:
        subject, confidence = _keyword_classify(clean_text)
        source = ClassificationSource.KEYWORD
        reasoning = "Classified via keyword fallback."

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    result = ClassificationResult(subject=subject, confidence=round(confidence, 4), source=source, latency_ms=elapsed_ms, reasoning=reasoning, attempts=attempts, warnings=warnings)

    if confidence >= 0.6 and source != ClassificationSource.DEFAULT:
        _cache.set(text, result)

    return result