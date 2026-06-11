"""
apps/core/utils.py

Shared utility helpers used across the project.
"""


def mask_email(email: str) -> str:
    """
    Partially obscure an email address to protect user privacy in API responses.

    Strategy
    --------
    For the local part (everything before '@'):
      - Keep the first 2 characters visible.
      - Keep the last 2 characters visible (only if the local part is long
        enough — i.e. more than 4 characters total).
      - Replace everything in between with '****'.

    Examples
    --------
    >>> mask_email("rusht1093@gmail.com")
    'ru****93@gmail.com'

    >>> mask_email("ab@example.com")   # exactly 2 chars — nothing to mask
    'ab****@example.com'

    >>> mask_email("abc@example.com")  # 3 chars — only first 2 + mask
    'ab****@example.com'

    >>> mask_email("abcd@example.com") # 4 chars — first 2 + last 2 overlap; just mask middle
    'ab****cd@example.com'
    """
    if "@" not in email:
        return email  # Not a valid email — return as-is

    local, domain = email.rsplit("@", 1)

    if len(local) <= 2:
        # Too short to split meaningfully; mask everything after the first 2 chars
        masked_local = local[:2] + "****"
    else:
        # Show first 2 and last 2, mask everything in between
        masked_local = local[:2] + "****" + local[-2:]

    return f"{masked_local}@{domain}"
