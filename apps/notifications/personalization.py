"""
apps/notifications/personalization.py

Renders per-user personalized message subject/body by substituting tokens.

Supported tokens (case-insensitive), written as {{token}}:
    {{first_name}}   → user's first name        (fallback: "there")
    {{last_name}}    → user's last name          (fallback: "")
    {{full_name}}    → user's full name          (fallback: "there")
    {{email}}        → user's email / recipient
    {{role}}         → user's role               (fallback: "")

If no user can be resolved, name tokens fall back to friendly defaults so the
message still reads naturally (e.g. "Hi there,").
"""
import re
import logging

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z_]+)\s*\}\}")


def resolve_user_for_message(message):
    """
    Find the User a scheduled message is for.

    Priority:
        1. The explicit `user` FK on the message.
        2. A user whose email matches `recipient` (case-insensitive).

    Returns:
        User instance or None.
    """
    if getattr(message, "user_id", None):
        return message.user

    # Lazy import to avoid circular imports at module load
    from apps.users.models import User

    try:
        return User.objects.filter(email__iexact=message.recipient).first()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not resolve user for recipient='%s': %s", message.recipient, exc
        )
        return None


def build_token_map(user, recipient_email):
    """
    Build the token → value mapping for substitution.
    Works even when `user` is None (uses friendly fallbacks).
    """
    first = (getattr(user, "first_name", "") or "").strip() if user else ""
    last = (getattr(user, "last_name", "") or "").strip() if user else ""
    full = (getattr(user, "full_name", "") or "").strip() if user else ""
    email = (getattr(user, "email", "") if user else "") or recipient_email or ""
    role = (getattr(user, "role", "") or "") if user else ""

    return {
        "first_name": first or "there",
        "last_name": last,
        "full_name": full or first or "there",
        "email": email,
        "role": role,
    }


def apply_tokens(text, token_map):
    """
    Replace every {{token}} in `text` using token_map.
    Unknown tokens are left untouched so nothing is silently dropped.
    """
    if not text:
        return text

    def _sub(match):
        key = match.group(1).lower()
        if key in token_map:
            return str(token_map[key])
        return match.group(0)  # leave unknown tokens as-is

    return _TOKEN_RE.sub(_sub, text)


def personalize_message(message):
    """
    Produce personalized (subject, body) for a ScheduledMessage.

    Resolves the target user, builds the token map, and substitutes tokens
    in both subject and body. If the body contains no name token at all,
    a friendly greeting line is prepended so every message feels personal.

    Returns:
        (subject: str, body: str)
    """
    user = resolve_user_for_message(message)
    token_map = build_token_map(user, message.recipient)

    subject = apply_tokens(message.subject, token_map)
    body = apply_tokens(message.body, token_map)

    # If the author didn't include any name token, add a greeting so the
    # message still opens personally.
    if not _TOKEN_RE.search(message.body or "") and "first_name" in token_map:
        greeting = f"Hi {token_map['first_name']},\n\n"
        body = greeting + body

    return subject, body
