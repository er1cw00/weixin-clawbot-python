"""
Utility functions
"""

import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


def markdown_to_plain_text(text: str) -> str:
    """
    Convert markdown to plain text

    - Code blocks: strip fences, keep content
    - Images: remove entirely
    - Links: keep display text only
    - Tables: convert pipes to spaces
    """
    result = text

    # Code blocks: ```lang\ncode\n``` -> code
    result = re.sub(r"```[^\n]*\n?([\s\S]*?)```", lambda m: m.group(1).strip(), result)

    # Images: ![alt](url) -> remove
    result = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", result)

    # Links: [text](url) -> text
    result = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", result)

    # Tables: remove separator rows
    result = re.sub(r"^\|[\s:|-]+\|$", "", result, flags=re.MULTILINE)

    # Tables: | a | b | -> "a  b"
    def replace_table_row(match):
        inner = match.group(1)
        cells = [cell.strip() for cell in inner.split("|")]
        return "  ".join(cells)

    result = re.sub(r"^\|(.+)\|$", replace_table_row, result, flags=re.MULTILINE)

    # Bold/italic: **text** or *text* -> text
    result = re.sub(r"\*\*([^*]+)\*\*", r"\1", result)
    result = re.sub(r"\*([^*]+)\*", r"\1", result)

    # Headers: ### text -> text
    result = re.sub(r"^#+\s*", "", result, flags=re.MULTILINE)

    return result.strip()


def aes_ecb_padded_size(raw_size: int) -> int:
    """
    Calculate AES-128-ECB padded size

    PKCS7 padding: pad to 16-byte boundary
    """
    block_size = 16
    remainder = raw_size % block_size
    if remainder == 0:
        return raw_size
    return raw_size + (block_size - remainder)


def aes_ecb_encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt with AES-128-ECB

    Args:
        plaintext: Plaintext bytes
        key: 16-byte AES key

    Returns:
        Ciphertext bytes
    """
    cipher = AES.new(key, AES.MODE_ECB)
    padded = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded)


def aes_ecb_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    """
    Decrypt with AES-128-ECB

    Args:
        ciphertext: Ciphertext bytes
        key: 16-byte AES key

    Returns:
        Plaintext bytes
    """
    from Crypto.Util.Padding import unpad

    cipher = AES.new(key, AES.MODE_ECB)
    padded = cipher.decrypt(ciphertext)
    return unpad(padded, AES.block_size)
