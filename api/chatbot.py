"""
VANYA focused disease Q&A assistant.
Uses local guidance.json knowledge base + word-boundary regex + rapidfuzz matching.
Single implementation used directly by FastAPI POST /chat.
"""
import re
try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    class _FuzzFallback:
        @staticmethod
        def token_sort_ratio(s1: str, s2: str) -> float:
            w1 = " ".join(sorted(s1.split()))
            w2 = " ".join(sorted(s2.split()))
            return difflib.SequenceMatcher(None, w1, w2).ratio() * 100.0
    fuzz = _FuzzFallback()

from . import guidance

INTENT_KEYWORDS = {
    "greeting": [
        r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgreetings\b",
        r"\bgood\s+morning\b", r"\bgood\s+afternoon\b", r"\bgood\s+evening\b", r"\bnamaste\b"
    ],
    "about": [
        r"\babout\s+(this\s+)?(disease|infection|problem|crop|condition)\b",
        r"\bwhat\s+is\s+this\s+(disease|infection|problem|condition)\b",
        r"\btell\s+me\s+about\b",
        r"\bexplain\s+(this\s+)?(disease|infection|problem)\b",
        r"\b(disease\s+)?overview\b",
        r"\bwhat\s+does\s+this\s+mean\b",
        r"^(about|explain|overview|details|what is it)\b"
    ],
    "causes": [
        r"\bcause\b", r"\bcauses\b", r"\bcaused\b", r"\bcausative\b",
        r"\bwhy\s+does\b", r"\bwhy\s+is\b", r"\bpathogen\b", r"\bfungus\b",
        r"\bbacteria\b", r"\bvirus\b", r"\breason\b", r"\borigin\b"
    ],
    "symptoms": [
        r"\bsymptom\b", r"\bsymptoms\b", r"\bsign\b", r"\bsigns\b",
        r"\blook\s+like\b", r"\blooks\s+like\b", r"\bidentify\b",
        r"\bappearance\b", r"\bhow\s+to\s+identify\b", r"\blesion\b", r"\bspots\b"
    ],
    "prevention": [
        r"\bprevent\b", r"\bprevention\b", r"\bpreventative\b", r"\bpreventive\b",
        r"\bavoid\b", r"\bprotect\b", r"\bprotection\b", r"\bsafeguard\b",
        r"\bstop\s+from\s+occurring\b"
    ],
    "treatment": [
        r"\btreat\b", r"\btreatment\b", r"\bcure\b", r"\bcurative\b",
        r"\bremedy\b", r"\bspray\b", r"\bfungicide\b", r"\bbactericide\b",
        r"\bmedicine\b", r"\bhow\s+to\s+treat\b", r"\bcontrol\b", r"\bmanage\b",
        r"\bchemical\b", r"\borganic\s+control\b"
    ],
    "spread": [
        r"\bspread\b", r"\bspreads\b", r"\bspreading\b", r"\btransmit\b",
        r"\btransmits\b", r"\btransmitted\b", r"\btransmission\b",
        r"\bcontagious\b", r"\bhow\s+does\s+it\s+spread\b", r"\bhow\s+it\s+spreads\b",
        r"\bvector\b", r"\bairborne\b", r"\bwaterborne\b"
    ]
}

FUZZY_TARGETS = {
    "greeting": ["hello", "hi", "hey there", "good morning", "namaste"],
    "about": ["what is this disease", "tell me about this disease", "explain this disease", "about disease"],
    "causes": ["what causes this", "causes of this disease", "why did this occur", "pathogen causing this"],
    "symptoms": ["what are the symptoms", "signs of disease", "how to identify this", "what does it look like"],
    "prevention": ["how to prevent this", "disease prevention", "how to avoid this disease", "prevent infection"],
    "treatment": ["how to treat this", "treatment options", "cure for disease", "fungicide spray medicine"],
    "spread": ["how does it spread", "how is this transmitted", "disease spread mechanism", "is it contagious"]
}

DECLINE_MESSAGE = (
    "Sorry, I can only answer questions about the detected disease: "
    "causes, symptoms, prevention and treatment. "
    "For anything else, please consult a local agricultural expert."
)


def detect_intent(message: str) -> str | None:
    text = message.lower().strip()
    if not text:
        return None

    # 1. Exact regex word-boundary matching (prevents "this" matching "hi")
    for intent, patterns in INTENT_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, text):
                return intent

    # 2. Fuzzy matching fallback with rapidfuzz
    best_intent = None
    best_score = 0.0

    for intent, targets in FUZZY_TARGETS.items():
        for target in targets:
            score = fuzz.token_sort_ratio(text, target)
            if score > 78 and score > best_score:
                best_score = score
                best_intent = intent

    return best_intent


def answer_query(user_question: str, disease_name: str | None = None) -> dict:
    intent = detect_intent(user_question)

    # Greeting check
    if intent == "greeting":
        return {
            "reply": (
                "Hello! I am VANYA's Disease Assistant. "
                "I can answer questions about the detected disease: its causes, "
                "symptoms, prevention, treatment, and how it spreads."
            ),
            "disclaimer": "General information only - not a substitute for advice from an agricultural expert."
        }

    # Healthy plant check
    if disease_name and "healthy" in disease_name.lower():
        return {
            "reply": (
                "No disease was detected on this plant; the leaf appears healthy. "
                "General care tips: Ensure balanced irrigation, avoid waterlogging, "
                "maintain good weed control, scout regularly for pests, and practice balanced fertilization."
            ),
            "disclaimer": "General information only - not a substitute for advice from an agricultural expert."
        }

    # If no disease provided yet
    if not disease_name:
        return {
            "reply": (
                "Please upload or analyze a leaf image first. Once a disease is detected, "
                "I can provide specific causes, symptoms, prevention, and treatment guidance."
            ),
            "disclaimer": "General information only."
        }

    # If question intent not recognized: politely decline, NEVER fall back to management
    if not intent or intent not in ("about", "causes", "symptoms", "prevention", "treatment", "spread"):
        return {
            "reply": DECLINE_MESSAGE,
            "disclaimer": "General information only - not a substitute for advice from an agricultural expert."
        }

    info = guidance.get(disease_name)
    crop_disease_readable = disease_name.replace("___", " - ").replace("_", " ")

    reply_text = ""
    if intent == "about":
        reply_text = info.get("about") or info.get("chatbot_response")
    elif intent == "causes":
        reply_text = info.get("causes")
    elif intent == "symptoms":
        reply_text = info.get("symptoms")
    elif intent == "prevention":
        reply_text = info.get("prevention")
    elif intent == "treatment":
        reply_text = info.get("treatment")
    elif intent == "spread":
        reply_text = info.get("spread")

    if not reply_text:
        reply_text = f"Detailed {intent} guidance for {crop_disease_readable} is being updated in our knowledge base."

    # Include source reference if verified
    source_url = info.get("source")
    if source_url and source_url.startswith("http"):
        reply_text += f"\n\nSource: {source_url}"

    return {
        "intent": intent,
        "reply": reply_text,
        "source": source_url,
        "disclaimer": info.get("disclaimer", "General information only - not a substitute for advice from an agricultural expert.")
    }
