"""LLM layer that writes the root-cause investigation for each anomaly.

This replaces the deterministic template as the *primary* explanation source. The
model is given a JSON array of anomalies whose every figure has already been
computed by `analysis.py` from the billing data, and it returns a structured
investigation for each one: a headline naming the suspected cause, a severity, a
narrative explanation, ranked cause hypotheses with confidence and supporting
evidence, the checks that would confirm or eliminate them, and a recommended
action.

The split that makes this safe is between facts and hypotheses. Figures, names,
dates and features are quoted from the input and never recomputed - the pipeline
owns those. Causes are the model's own reasoning, are ranked rather than asserted,
and each one has to cite the field it rests on. So the report reads like an
analyst wrote it without the model ever being trusted with arithmetic.

Provider: Google Gemini (`gemini-3.5-flash-lite`) over the REST API, called with
`responseMimeType=application/json` and an explicit `responseSchema`, so the
reply is machine-parseable rather than prose that has to be scraped.

Credentials, in priority order:

    GEMINI_API_KEY / GOOGLE_API_KEY environment variable
    GEMINI_API_KEY=... line in a `.env` file at the project root

Enabled by default whenever a key is present. Set CARCI_LLM_REASONING=0 to force
the deterministic template instead. If the key is missing, the network call
fails, or the reply cannot be parsed, the caller silently keeps the template
text, so the app still runs offline and never breaks on an API outage.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

MODEL = "gemini-3.5-flash-lite"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
# A hypothesis-driven report runs several times longer than the single paragraph
# this layer used to return, and a truncated reply loses whole records.
MAX_OUTPUT_TOKENS = 32768
TIMEOUT_SECONDS = 90
ENABLE_FLAG = "CARCI_LLM_REASONING"
KEY_VARIABLES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")

# Batched into one request rather than one call per anomaly: 20 separate requests
# would cost 20x the latency for the same work.
MAX_RECORDS_PER_CALL = 20

# Surfaced by the UI when the layer is enabled but produced nothing, so a failed
# call is diagnosable instead of silently looking like "the feature is off".
_LAST_ERROR: Optional[str] = None

SYSTEM_PROMPT = """You are a senior AWS cost investigator writing the root-cause
section of a billing incident report.

You will receive a JSON array of detected cost anomalies. Every figure in each
entry has ALREADY been computed from the customer's billing data by a statistical
pipeline and a SHAP feature-attribution step.

Your output contains two different kinds of statement, and the rules differ.

FACTS - the numbers, names, dates, regions, resources and features you are given.

  * Use ONLY what is in the input. Never calculate, re-round, estimate or invent
    a figure. If a value is not in the input, do not state it.
  * Do not claim the model detected something when `model_flagged` is false, and
    never present a `reference_only` entry as a confirmed detection.
  * When `no_prior_baseline` is true there is no comparison to draw. Call it new
    spend; do not describe it as an increase.

HYPOTHESES - what plausibly caused the anomaly.

  * Here you are expected to reason past the data and propose specific engineering
    explanations. This is the part of the report a human analyst would write.
  * Ground every hypothesis in something you were given: the usage type, the
    resource, how concentrated the region share is, the tag, and which features
    the attribution step found most important.
  * Rank them, and say how confident you are. A hypothesis you cannot tie to
    anything in the input is not worth listing.
  * Never state a hypothesis as established fact. "Consistent with", "suggests"
    and "would explain" are correct. "Was caused by" is not.

Fields to return:

`headline` - under 70 characters. Name the suspected cause, not the symptom.
  Weak: "AmazonEC2 cost increase". Strong: "Crypto-mining traffic on an untagged
  research instance".

`severity` - one of critical, high, medium, low. Judge it from `impact_usd` and
  `increase_pct` together with how alarming the usage type and feature pattern
  are. A `reference_only` entry is never above low.

`explanation` - three or four short paragraphs of plain prose. No headings, no
  bullet points, no markdown.
    Paragraph 1: what changed, in money and in time.
    Paragraph 2: where the cost concentrated - region, resource, usage type, tag -
      and what that concentration implies.
    Paragraph 3: what the feature attribution says drove the score, in plain
      language rather than raw column names.
    Paragraph 4, only if it earns its place: what makes this case unusual, or why
      it should be escalated.
  Write for a finance manager who is technical enough to act but did not build
  the system.

`likely_causes` - two to four ranked hypotheses, most likely first. Each carries:
    `cause` - a specific mechanism, not a category. "An autoscaling group scaled
      out under load and never scaled back in" beats "increased usage".
    `confidence` - high, medium or low.
    `evidence` - the specific figure or field from the input that supports it.

`investigation_steps` - two to four concrete checks in the order you would run
  them. Name the AWS console page, CLI command or log to open, and the actual
  resource, region or tag to filter on. Each step should confirm or eliminate one
  of the hypotheses above.

`recommended_action` - one or two sentences on what to do once the cause is
  confirmed. Specific to this anomaly, never generic advice that would fit any of
  them.

Return one entry per input entry, matched by `index`."""

CONFIDENCE_LEVELS = ("high", "medium", "low")
SEVERITY_LEVELS = ("critical", "high", "medium", "low")

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "explanations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "index": {"type": "INTEGER"},
                    "headline": {"type": "STRING"},
                    "severity": {"type": "STRING", "enum": list(SEVERITY_LEVELS)},
                    "explanation": {"type": "STRING"},
                    "likely_causes": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "cause": {"type": "STRING"},
                                "confidence": {"type": "STRING", "enum": list(CONFIDENCE_LEVELS)},
                                "evidence": {"type": "STRING"},
                            },
                            "required": ["cause", "confidence", "evidence"],
                        },
                    },
                    "investigation_steps": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "recommended_action": {"type": "STRING"},
                },
                "required": [
                    "index",
                    "headline",
                    "severity",
                    "explanation",
                    "likely_causes",
                    "investigation_steps",
                    "recommended_action",
                ],
            },
        }
    },
    "required": ["explanations"],
}


def _load_env_file() -> None:
    """Read `.env` at the project root into os.environ, without overwriting it.

    Keeps the key out of the source tree. Deliberately minimal so the project
    does not need python-dotenv as a dependency.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name and name not in os.environ:
                os.environ[name] = value
    except OSError:
        return


def api_key() -> str:
    _load_env_file()
    for variable in KEY_VARIABLES:
        value = os.environ.get(variable, "").strip()
        if value:
            return value
    return ""


def is_enabled() -> bool:
    """On by default when a key exists; CARCI_LLM_REASONING=0 forces it off."""
    flag = os.environ.get(ENABLE_FLAG, "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    return bool(api_key())


def last_error() -> Optional[str]:
    return _LAST_ERROR


def _to_payload(record: Dict, index: int) -> Dict:
    """Reduce an anomaly record to the facts the model is allowed to talk about.

    Deliberately narrow: passing the whole record would hand the model fields it
    has no business repeating, and every extra key is a chance for it to state
    something the pipeline never computed. No suggested action is included, so
    the recommendation the model returns is its own reading of these facts rather
    than a rewrite of a keyword rule.
    """
    return {
        "index": index,
        "service": record["service_name"],
        "date": record["display_date"],
        "observed_cost_usd": record["anomaly_value"],
        "baseline_cost_usd": record["normal_value"],
        "increase_pct": record["percentage"],
        "impact_usd": record["impact_value"],
        "driver_line_item_cost_usd": record["driver_row_cost"],
        "region": record["region"],
        "region_share_pct": record["region_share_pct"],
        "resource": record["resource"],
        "usage_type": record["usage_type"],
        "tag": record["tag"],
        "top_features": record["top_ml_features"],
        "feature_attribution": [
            {
                "feature": item["feature"],
                "value": item["feature_value"],
                "shap_value": item["shap_value"],
            }
            for item in record.get("feature_contributions", [])[:3]
        ],
        "attribution_method": record["attribution_method"],
        "model_flagged": bool(record["model_flag"]),
        "reference_only": bool(record["is_fallback"]),
        "no_prior_baseline": bool(record["is_new_spend"]),
    }


def _post(url: str, body: Dict) -> Dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _call_gemini(payload: List[Dict], key: str) -> Optional[Dict]:
    """One request, with a single retry for transient 429/500/503 responses."""
    global _LAST_ERROR

    # Quoted rather than interpolated raw: the key goes into a query string, and a
    # stray character in it should produce an API error we can report, not an
    # unreadable InvalidURL from urllib before the request is even sent.
    url = f"{API_ROOT}/{MODEL}:generateContent?key={urllib.parse.quote(key, safe='')}"
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Write an explanation and a recommended action for each of "
                            "these detected cost anomalies:\n\n"
                            + json.dumps(payload, indent=2)
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            # Low temperature: this is a writing task over fixed facts, not a
            # creative one, and drift here reads as invented numbers.
            "temperature": 0.2,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }

    for attempt in range(2):
        try:
            return _post(url, body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            _LAST_ERROR = f"HTTP {exc.code}: {detail}"
            if exc.code in {429, 500, 503} and attempt == 0:
                time.sleep(2)
                continue
            return None
        except Exception as exc:
            # Network failure, DNS, timeout, TLS: all mean "no LLM text this run",
            # never "break the analysis".
            _LAST_ERROR = f"{type(exc).__name__}: {exc}"
            if attempt == 0:
                time.sleep(2)
                continue
            return None
    return None


def _clean_choice(value: object, allowed: tuple) -> str:
    """Return `value` if it is one of `allowed`, else "".

    The schema constrains these to an enum, but the enum is enforced by the API
    rather than by us, and the UI colours a badge from the result. An unexpected
    string is dropped instead of being rendered.
    """
    text = str(value or "").strip().lower()
    return text if text in allowed else ""


def _clean_causes(value: object) -> List[Dict[str, str]]:
    """Keep only hypotheses that carry both a mechanism and its evidence.

    A cause with no evidence is exactly the unsupported speculation the prompt
    forbids, so it is discarded here rather than shown to the user.
    """
    if not isinstance(value, list):
        return []
    causes = []
    for item in value[:4]:
        if not isinstance(item, dict):
            continue
        cause = str(item.get("cause", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not cause or not evidence:
            continue
        causes.append(
            {
                "cause": cause,
                "confidence": _clean_choice(item.get("confidence"), CONFIDENCE_LEVELS) or "low",
                "evidence": evidence,
            }
        )
    return causes


def _clean_steps(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(step).strip() for step in value[:4] if str(step).strip()]


def generate_explanations(records: List[Dict]) -> Optional[Dict[int, Dict]]:
    """Return {record index: investigation}, or None.

    Each investigation carries `explanation`, `headline`, `severity`,
    `likely_causes`, `investigation_steps` and `recommended_action`. Only
    `explanation` is required; the rest are cleaned to safe empty values so a
    partial reply degrades the card rather than breaking it.

    None is not an error condition. It is the normal signal that the caller should
    keep the deterministic template text, and it is what happens whenever the
    feature is switched off or the API is unreachable.
    """
    global _LAST_ERROR
    _LAST_ERROR = None

    if not records:
        return None
    if not is_enabled():
        _LAST_ERROR = "No API key found (set GEMINI_API_KEY in .env)." if not api_key() else None
        return None

    key = api_key()
    # A key pasted across a line break or with a stray space is a common setup
    # error, and it otherwise surfaces as an opaque URL or transport failure.
    if any(character.isspace() for character in key):
        _LAST_ERROR = (
            "GEMINI_API_KEY contains a space or line break. Check the .env line is "
            "a single unbroken value."
        )
        return None

    payload = [_to_payload(record, i) for i, record in enumerate(records[:MAX_RECORDS_PER_CALL])]
    response = _call_gemini(payload, key)
    if response is None:
        return None

    try:
        candidate = response["candidates"][0]
        # A safety block returns 200 with no parts, so the reason is checked first.
        if candidate.get("finishReason") not in {"STOP", None}:
            _LAST_ERROR = f"finishReason={candidate.get('finishReason')}"
            if candidate.get("finishReason") != "MAX_TOKENS":
                return None
        text = candidate["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except Exception as exc:
        _LAST_ERROR = f"Unparseable reply: {type(exc).__name__}: {exc}"
        return None

    explanations: Dict[int, Dict] = {}
    for item in parsed.get("explanations", []):
        try:
            index = int(item["index"])
        except (KeyError, TypeError, ValueError):
            continue
        explanation = str(item.get("explanation", "")).strip()
        if not explanation:
            # Without the narrative there is nothing to show, so this record keeps
            # its template text rather than appearing half-filled.
            continue
        explanations[index] = {
            "explanation": explanation,
            "headline": str(item.get("headline", "")).strip(),
            "severity": _clean_choice(item.get("severity"), SEVERITY_LEVELS),
            "likely_causes": _clean_causes(item.get("likely_causes")),
            "investigation_steps": _clean_steps(item.get("investigation_steps")),
            "recommended_action": str(item.get("recommended_action", "")).strip(),
        }

    if not explanations:
        _LAST_ERROR = "Reply contained no usable explanations."
        return None
    return explanations
