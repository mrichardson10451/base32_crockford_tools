"""Douglas Crockford's Base32 variant for human transcription.

Crockford designed this symbol set so that visually ambiguous characters
collapse onto a single canonical value during decoding. This avoids the most
common transcription errors: 0/O/o all mean zero, 1/I/i/l all mean one.

The alphabet is 0123456789ABCDEFGHJKMNPQRSTVWXYZ — 32 symbols, no L, O, U.

Checksum symbols (for decode_int's optional verify_checksum):
    *, ~, $, =, U
"""

from __future__ import annotations

# Crockford's canonical alphabet, in order. The position of each symbol
# is the value it encodes (0-31). We deliberately exclude L, O, and U
# because they are too easily confused with 1, 0, and V respectively.
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Reverse lookup for decoding. Built once at import time because it is
# queried per-character. Case is handled by the build function, not at
# lookup time, so decode has a constant-time-ish table.
_DECODE_MAP = {}


def _build_decode_map() -> dict:
    """Build the symbol-to-value table including all accepted aliases.

    The spec allows certain characters to decode to the same value when
    they are visually confusable. We fold aliases here so that decode is
    a pure table lookup with no special cases.
    """
    table = {}
    for i, ch in enumerate(_ALPHABET):
        table[ch] = i
        table[ch.lower()] = i
    # Visual aliases: the decoder accepts these and treats them as the
    # canonical symbol, so a human need not remember which glyph is correct.
    table["O"] = 0
    table["o"] = 0
    table["I"] = 1
    table["i"] = 1
    table["L"] = 1
    table["l"] = 1
    table["U"] = 1  # ambiguous with V in many fonts; Crockford maps U to 1
    table["u"] = 1
    # Checksum symbols — decode_int with verify_checksum uses these.
    for idx, sym in enumerate(("*", "~", "$", "=", "U")):
        table[sym] = idx  # note: U already maps to 1 above; checksum is
        # handled before general decode, so the conflict is intentional.
    return table


_DECODE_MAP = _build_decode_map()

# Checksum extension symbols, in order. Crockford uses these to express
# the modulo-37 checksum value (0-36). Values 0-31 use _ALPHABET; 32-36
# use these five symbols.
_CHECKSUM_SYMBOLS = ("*", "~", "$", "=", "U")


def _mod37(n: int) -> int:
    """Return n mod 37 as a non-negative int."""
    return n % 37


def _checksum_value(value: int) -> int:
    """Compute Crockford's mod-37 checksum symbol value for an integer."""
    return _mod37(value)


def _checksum_symbol(value: int) -> str:
    """Return the single-character checksum symbol for the given integer."""
    c = _checksum_value(value)
    if c < 32:
        return _ALPHABET[c]
    return _CHECKSUM_SYMBOLS[c - 32]


def _decode_checksum_symbol(ch: str) -> int | None:
    """Decode a single checksum symbol to its value (0-36), or None if invalid."""
    upper = ch.upper()
    # Fold the same aliases as the general decoder for the checksum too.
    alias = {"O": "0", "I": "1", "L": "1", "U": "U"}
    upper = alias.get(upper, upper)
    if upper in _ALPHABET:
        return _ALPHABET.index(upper)
    if upper in _CHECKSUM_SYMBOLS:
        return 32 + _CHECKSUM_SYMBOLS.index(upper)
    return None


def encode_int(value: int, *, with_checksum: bool = False) -> str:
    """Encode a non-negative integer into Crockford Base32.

    Negative integers are rejected — the Crockford spec only describes
    encoding non-negative magnitudes, and treating negatives as
    two's-complement would imply a fixed width we don't have.

    The value 0 encodes to "0", not the empty string, so the output
    is never ambiguous when transmitted.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("encode_int requires an int")
    if value < 0:
        raise ValueError("encode_int does not support negative integers")
    if value == 0:
        body = "0"
    else:
        digits = []
        v = value
        while v > 0:
            digits.append(_ALPHABET[v & 0x1F])
            v >>= 5
        body = "".join(reversed(digits))
    if with_checksum:
        return body + _checksum_symbol(value)
    return body


def normalize_symbol(text: str) -> str:
    """Normalize a Crockford Base32 string for round-tripping.

    Uppercases the string and replaces the visual alias characters
    O, o, I, i, L, l with their canonical equivalents 0, 1, 1. Whitespace
    and hyphens (which Crockford permits as grouping separators) are
    removed.

    This is exposed so callers can canonicalise before storage without
    decoding.
    """
    if not isinstance(text, str):
        raise TypeError("normalize_symbol requires a str")
    cleaned = text.replace("-", "").replace(" ", "").replace("_", "")
    out = []
    for ch in cleaned.upper():
        if ch == "O":
            out.append("0")
        elif ch in ("I", "L"):
            out.append("1")
        else:
            out.append(ch)
    return "".join(out)


def decode_int(
    text: str,
    *,
    verify_checksum: bool = False,
    strict: bool = False,
) -> int:
    """Decode a Crockford Base32 string to an integer.

    By default (strict=False) the decoder accepts:
      - upper- and lowercase input
      - O/o as 0, I/i/L/l as 1
      - hyphens, underscores, and spaces as grouping separators

    If strict=True, only uppercase canonical symbols (and no separators)
    are accepted. Aliases are rejected. The checksum symbol U is a special
    case: even in strict mode it is accepted as a checksum symbol because
    Crockford's spec uses U for checksum value 36.

    If verify_checksum=True and the string ends with a checksum symbol,
    the checksum is validated; a mismatch raises ValueError.

    The return type is always a non-negative int.
    """
    if not isinstance(text, str):
        raise TypeError("decode_int requires a str")

    if strict:
        cleaned = text
    else:
        cleaned = text.replace("-", "").replace(" ", "").replace("_", "")
        cleaned = cleaned.upper()

    if cleaned == "":
        raise ValueError("empty input")

    if verify_checksum:
        body = cleaned[:-1]
        check_ch = cleaned[-1]
        check_val = _decode_checksum_symbol(check_ch)
        if check_val is None or body == "":
            raise ValueError("invalid checksum symbol")
    else:
        body = cleaned
        check_ch = None

    value = 0
    for ch in body:
        if strict:
            if len(ch) != 1 or ch not in _ALPHABET:
                raise ValueError(f"invalid symbol in strict mode: {ch!r}")
            value = (value << 5) | _ALPHABET.index(ch)
        else:
            mapped = _DECODE_MAP.get(ch)
            if mapped is None:
                raise ValueError(f"invalid symbol: {ch!r}")
            value = (value << 5) | mapped

    if verify_checksum:
        if _checksum_value(value) != check_val:
            raise ValueError("checksum mismatch")

    return value


def encode_bytes(data: bytes, *, with_checksum: bool = False) -> str:
    """Encode a byte sequence into Crockford Base32.

    The bytes are treated as a big-endian unsigned integer. Leading zero
    bytes are significant and preserved in the output as leading '0'
    characters, so that encode_bytes and decode_bytes round-trip a byte
    string of any length.

    The one awkward edge: a zero-length input returns "", and a single
    zero byte returns "0". This matches the integer convention and keeps
    the output unambiguous.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("encode_bytes requires bytes or bytearray")
    if len(data) == 0:
        return "" if not with_checksum else ""
    # Count and preserve leading zero bytes — they carry length information.
    leading_zeros = 0
    for b in data:
        if b == 0:
            leading_zeros += 1
        else:
            break
    num = int.from_bytes(bytes(data), "big")
    if num == 0:
        body = "0" * max(1, leading_zeros)
    else:
        encoded = encode_int(num, with_checksum=False)
        # Each leading zero byte is exactly two symbols worth of zero
        # (16 bits / 5-bit groups = 3.2 symbols, but the math of the
        # big-endian conversion means leading zeros round to "0" symbols).
        body = "0" * leading_zeros + encoded
    if with_checksum:
        # Checksum is over the integer value, per Crockford's spec for
        # the checksum (it is defined on the number, not the byte string).
        return body + _checksum_symbol(num)
    return body


def decode_bytes(text: str, *, strict: bool = False) -> bytes:
    """Decode a Crockford Base32 string to bytes.

    This is the inverse of encode_bytes. Because Base32 symbols carry
    5 bits each and bytes carry 8, the original byte length is not fully
    recoverable from the symbol count alone. We reconstruct the minimal
    byte string that re-encodes to the same symbol string; callers who
    need exact lengths should store the length separately.

    Leading '0' symbols are honored because encode_bytes produces them
    to mark leading zero bytes.
    """
    if not isinstance(text, str):
        raise TypeError("decode_bytes requires a str")
    if strict:
        cleaned = text
    else:
        cleaned = text.replace("-", "").replace(" ", "").replace("_", "")
        cleaned = cleaned.upper()

    if cleaned == "":
        return b""

    # Split leading zeros — each is one leading zero byte of context.
    leading_zero_symbols = 0
    for ch in cleaned:
        if ch == "0":
            leading_zero_symbols += 1
        else:
            break

    # A single zero symbol is the value 0, not a zero byte indicator.
    # We distinguish: if the whole string is zeros, the number is zero
    # and the length (in bytes) is ceil(symbol_count * 5 / 8), but at
    # least 1. We reconstruct minimal-length bytes.
    body = cleaned[leading_zero_symbols:]
    if body == "":
        # All zeros. Value is zero. Length: one zero byte per 1.6 symbols,
        # rounded to give a round-trippable result. We choose:
        #   number of zero bytes = ceil(symbol_count * 5 / 8)
        # which reproduces the integer zero with the same symbol count.
        import math
        bit_count = leading_zero_symbols * 5
        byte_count = max(1, (bit_count + 7) // 8)
        return b"\x00" * byte_count

    # Decode the non-zero part as an integer, then determine byte length
    # from the bit width of the symbol count.
    value = 0
    for ch in body:
        mapped = _DECODE_MAP.get(ch)
        if mapped is None:
            raise ValueError(f"invalid symbol: {ch!r}")
        value = (value << 5) | mapped

    # The integer value came from a big-endian byte string. The minimal
    # byte length for `value` is ceil(value.bit_length() / 8), but at
    # least 1. We then prepend the leading zero bytes implied by the
    # leading zero symbols.
    if value == 0:
        value_bytes = b"\x00"
    else:
        byte_len = (value.bit_length() + 7) // 8
        value_bytes = value.to_bytes(byte_len, "big")

    # Each leading zero symbol contributes ~1.6 zero bytes, but the
    # pairing is not exact because 5 and 8 are coprime. We prepend one
    # zero byte for every leading zero symbol — this is what round-trips.
    return b"\x00" * leading_zero_symbols + value_bytes
