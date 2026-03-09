"""Prompt Injection Guard — Detects and sanitizes malicious LLM input.

Protects agents from prompt injection attacks where user-controlled fields
(complaint descriptions, dispute reasons, campaign goals) contain instructions
that attempt to override the agent's system prompt.

Detection Strategy:
  1. Pattern matching — regex-based detection of common injection patterns
  2. Structural analysis — detects role-switching, delimiter abuse, encoding tricks
  3. Length limiting — truncates excessively long inputs

Usage:
    from shared.security import sanitize_input, PromptInjectionError

    # Quick sanitize (returns cleaned string, raises on high-risk)
    clean_description = sanitize_input(description, field_name="description")

    # Detailed check (returns ScanResult with risk_level and matched patterns)
    guard = PromptInjectionGuard()
    result = guard.scan(description)
    if result.is_blocked:
        logger.warning("Prompt injection detected: %s", result.matched_patterns)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)

# Maximum input length before truncation (characters)
MAX_INPUT_LENGTH = 2000


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ScanResult:
    """Result of a prompt injection scan."""

    risk_level: RiskLevel
    matched_patterns: tuple[str, ...] = ()
    sanitized_text: str = ""

    @property
    def is_blocked(self) -> bool:
        return self.risk_level == RiskLevel.HIGH


class PromptInjectionError(ValueError):
    """Raised when high-risk prompt injection is detected."""

    def __init__(self, matched_patterns: tuple[str, ...]) -> None:
        self.matched_patterns = matched_patterns
        super().__init__(
            f"Prompt injection detected. Matched patterns: {', '.join(matched_patterns)}"
        )


# ── Detection Patterns ──────────────────────────────────────────
# Each pattern: (name, regex, risk_level)
# HIGH = block the input entirely
# MEDIUM = sanitize (strip the injection part) + log warning

_PATTERNS: list[tuple[str, re.Pattern[str], RiskLevel]] = [
    # Role hijacking — attempts to override system prompt
    (
        "role_override",
        re.compile(
            r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are)|"
            r"from\s+now\s+on\s+you|your\s+new\s+(role|instructions?)|"
            r"sen\s+artık|rolün\s+değişti|yeni\s+görevin)",
            re.IGNORECASE,
        ),
        RiskLevel.HIGH,
    ),
    # System prompt extraction
    (
        "prompt_extraction",
        re.compile(
            r"(ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)|"
            r"(reveal|show|print|output|repeat)\s+(your\s+)?(system\s+prompt|instructions?|rules?)|"
            r"what\s+(are|were)\s+your\s+(instructions?|rules?|prompts?)|"
            r"önceki\s+talimatları\s+(unut|yoksay)|"
            r"sistem\s+promptunu\s+(göster|yaz))",
            re.IGNORECASE,
        ),
        RiskLevel.HIGH,
    ),
    # Delimiter injection — tries to break out of user input context
    (
        "delimiter_injection",
        re.compile(
            r"(```system|<\|system\|>|<system>|<<SYS>>|\[SYSTEM\]|"
            r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|endoftext\|>)",
            re.IGNORECASE,
        ),
        RiskLevel.HIGH,
    ),
    # Tool/function manipulation
    (
        "tool_manipulation",
        re.compile(
            r"(call\s+the\s+function|execute\s+(this\s+)?(command|code|script)|"
            r"run\s+(this\s+)?(python|bash|shell|sql)|"
            r"import\s+os|subprocess|eval\(|exec\(|"
            r"__import__|rm\s+-rf)",
            re.IGNORECASE,
        ),
        RiskLevel.HIGH,
    ),
    # Output manipulation — tries to control agent's response format
    (
        "output_manipulation",
        re.compile(
            r"(respond\s+only\s+with|your\s+response\s+must\s+be|"
            r"do\s+not\s+use\s+(any\s+)?tools?|"
            r"skip\s+(all\s+)?(steps?|tools?|analysis)|"
            r"just\s+(say|respond|output|return)\s+\")",
            re.IGNORECASE,
        ),
        RiskLevel.MEDIUM,
    ),
    # Data exfiltration attempts
    (
        "data_exfiltration",
        re.compile(
            r"(send\s+(this|data|info)\s+to|"
            r"(http|https|ftp)://[^\s]+|"
            r"webhook\s*[:\.]|"
            r"curl\s+|wget\s+)",
            re.IGNORECASE,
        ),
        RiskLevel.MEDIUM,
    ),
    # Encoding tricks (base64, hex instructions)
    (
        "encoding_tricks",
        re.compile(
            r"(base64\s*(decode|encode)|"
            r"decode\s+this|"
            r"\\x[0-9a-fA-F]{2}\\x[0-9a-fA-F]{2}|"
            r"&#\d{2,4};)",
            re.IGNORECASE,
        ),
        RiskLevel.MEDIUM,
    ),
]


class PromptInjectionGuard:
    """Scans user input for prompt injection patterns.

    Thread-safe: no mutable state after init.
    """

    def __init__(self, max_length: int = MAX_INPUT_LENGTH) -> None:
        self._max_length = max_length
        self._patterns = _PATTERNS

    def scan(self, text: str) -> ScanResult:
        """Scan text for prompt injection patterns.

        Returns ScanResult with risk_level, matched patterns, and sanitized text.
        """
        if not text or not text.strip():
            return ScanResult(risk_level=RiskLevel.LOW, sanitized_text="")

        # Truncate overly long inputs
        truncated = text[: self._max_length] if len(text) > self._max_length else text

        matched_high: list[str] = []
        matched_medium: list[str] = []

        for name, pattern, risk in self._patterns:
            if pattern.search(truncated):
                if risk == RiskLevel.HIGH:
                    matched_high.append(name)
                else:
                    matched_medium.append(name)

        # Determine overall risk
        if matched_high:
            return ScanResult(
                risk_level=RiskLevel.HIGH,
                matched_patterns=tuple(matched_high + matched_medium),
                sanitized_text="",
            )

        if matched_medium:
            # For medium risk: sanitize by removing matched patterns
            sanitized = truncated
            for name, pattern, risk in self._patterns:
                if name in matched_medium:
                    sanitized = pattern.sub("[REDACTED]", sanitized)

            logger.warning(
                "Medium-risk prompt injection patterns detected: %s",
                matched_medium,
            )
            return ScanResult(
                risk_level=RiskLevel.MEDIUM,
                matched_patterns=tuple(matched_medium),
                sanitized_text=sanitized.strip(),
            )

        return ScanResult(risk_level=RiskLevel.LOW, sanitized_text=truncated.strip())


# ── Module-level singleton ──────────────────────────────────────
_guard = PromptInjectionGuard()


def sanitize_input(text: str, field_name: str = "input") -> str:
    """Sanitize user input, raising PromptInjectionError on HIGH risk.

    For MEDIUM risk, returns sanitized text with patterns redacted.
    For LOW risk, returns the original text (trimmed + length-limited).

    This is the primary API for agent code:
        clean = sanitize_input(description, field_name="description")
    """
    result = _guard.scan(text)

    if result.is_blocked:
        logger.error(
            "Prompt injection BLOCKED in field '%s': patterns=%s, input_preview='%s'",
            field_name,
            result.matched_patterns,
            text[:100],
        )
        raise PromptInjectionError(result.matched_patterns)

    if result.risk_level == RiskLevel.MEDIUM:
        logger.warning(
            "Prompt injection sanitized in field '%s': patterns=%s",
            field_name,
            result.matched_patterns,
        )

    return result.sanitized_text
