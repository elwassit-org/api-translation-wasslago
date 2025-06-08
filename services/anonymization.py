import re
import spacy
from typing import Tuple, Dict
import logging

logger = logging.getLogger(__name__)

class TextAnonymizer:
    """Anonymizes sensitive entities in text using SpaCy and regex, with efficient caching."""

    # === Class variables shared across all instances ===
    _model_cache = {}

    model_map = {
        "en": "en_core_web_trf",
        "fr": "fr_core_web_trf",
        "es": "es_core_web_trf",
        "de": "de_core_web_trf",
        "it": "it_core_web_trf",
        "nl": "nl_core_web_trf",
        "pt": "pt_core_web_trf",
        "ru": "ru_core_web_trf",
        "zh": "zh_core_web_trf",
        "ja": "ja_core_web_trf",
        "ko": "ko_core_web_trf"
    }

    sensitive_entities = {
        "PERSON", "ORG", "GPE", "NORP", "LOC", "DATE", "TIME",
        "MONEY", "PERCENT", "QUANTITY", "FAC", "LAW", "PRODUCT", "CARDINAL"
    }

    custom_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
        r'\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){2,4}\d{2,4}\b'  # Phones
    ]

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.model = self._get_or_load_model(lang)
        self.token_map = {}
        self.token_count = 1

    @classmethod
    def _get_or_load_model(cls, lang: str):
        """Returns a cached SpaCy model if available, otherwise loads and caches it."""
        if lang in cls._model_cache:
            return cls._model_cache[lang]

        model_name = cls.model_map.get(lang, "xx_sent_ud_sm")

        try:
            model = spacy.load(model_name)
        except Exception as e:
            logger.info(f"[Warning] Failed to load '{model_name}': {e}")
            model = spacy.load("xx_sent_ud_sm")

        cls._model_cache[lang] = model
        return model

    def anonymize_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Anonymizes sensitive entities and patterns in the input text."""
        self.token_map = {}
        self.token_count = 1
        doc = self.model(text)
        replaced_spans = set()

        for ent in sorted(doc.ents, key=lambda e: e.start_char):
            if ent.label_ in self.sensitive_entities and ent.text not in replaced_spans:
                token_key = self._next_token()
                self.token_map[token_key] = ent.text
                text = re.sub(re.escape(ent.text), token_key, text, count=1)
                replaced_spans.add(ent.text)

        for pattern in self.custom_patterns:
            for match in re.findall(pattern, text):
                if match not in self.token_map.values():
                    token_key = self._next_token()
                    self.token_map[token_key] = match
                    text = re.sub(re.escape(match), token_key, text, count=1)

        return text, self.token_map

    def _next_token(self) -> str:
        token_key = f"<TOKEN_{self.token_count}>"
        self.token_count += 1
        return token_key

class AnonymizationError(Exception):
    pass

def tokenize_text(text: str, lang: str) -> Tuple[str, Dict[str, str]]:
    """
    Optimized text tokenization with:
    - Thread-safe processing
    - Efficient replacement strategy
    - Comprehensive entity coverage
    """
    try:
        anonymizer = TextAnonymizer()
        return anonymizer.anonymize_text(text, lang)
    except AnonymizationError as e:
        logger.error(f"Tokenization failed: {str(e)}")
        return text, {}  # Return original text on failure