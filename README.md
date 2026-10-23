# base32_crockford_tools

Encodes and decodes integers and byte sequences using Douglas Crockford's Base32 variant, designed for human transcription.

## Usage

```python
from base32_crockford_tools import encode_int, decode_int, encode_bytes, decode_bytes, normalize_symbol

encoded = encode_int(65535)
value = decode_int(encoded)  # 65535

# Checksums
checked = encode_int(31, with_checksum=True)  # "ZZ"
assert decode_int(checked, verify_checksum=True) == 31

# Visual aliases are accepted on decode
assert decode_int("O0") == 0

# Bytes
b_enc = encode_bytes(b"hello")
b_dec = decode_bytes(b_enc)
assert b_dec == b"hello"

# Normalize before storage
canonical = normalize_symbol("ab-cd EF")  # "ABCDEF"
```

## Why this exists

Base32Crockford exists because Base64 and RFC 4648 Base32 both use character sets that are hostile to human transcription: `0` vs `O`, `1` vs `l` vs `I`, `8` vs `B`, `5` vs `S`. Crockford's alphabet drops `L`, `O`, and `U` and folds their lookalikes onto a single value during decoding, so a human typing a code from printout or screen cannot silently corrupt it.

The trade-off: this is not a drop-in RFC 4648 replacement. If you need a standard that interoperates with Base32-encoded data from other systems, use the `base64` module's `b32encode`. This library is for when the constraint is "a human will type this."

## Edge cases you will hit

- **Byte length is not perfectly recoverable.** `encode_bytes` and `decode_bytes` round-trip for data the library itself produced, but `decode_bytes` cannot recover the exact original byte length from an arbitrary symbol string because 5-bit groups don't align to 8-bit bytes. If you need exact lengths, store the length separately.
- **`U` is overloaded.** It maps to integer value 1 during decoding (as a visual alias of `V`/`1`), but it is also checksum symbol 36. The decoder resolves this by position: when `verify_checksum=True` is set, the final symbol is interpreted as a checksum; otherwise `U` decodes as value 1.
- **Negative integers are rejected.** Crockford's spec describes non-negative magnitudes only. If you need to encode signed values, split the sign out yourself.
- **Strict mode** (`strict=True`) accepts only uppercase canonical symbols with no separators or aliases. This is for validating machine-generated output, not human input.
