import unittest

from base32_crockford_tools import (
    encode_int,
    decode_int,
    encode_bytes,
    decode_bytes,
    normalize_symbol,
)


class TestEncodeInt(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(encode_int(0), "0")

    def test_single_digit(self):
        self.assertEqual(encode_int(10), "A")

    def test_round_trip_values(self):
        for v in (1, 31, 32, 1024, 65535, 2**40):
            self.assertEqual(decode_int(encode_int(v)), v, f"failed for {v}")

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            encode_int(-1)

    def test_bool_rejected(self):
        with self.assertRaises(TypeError):
            encode_int(True)

    def test_with_checksum(self):
        # 0 has checksum value 0, symbol "0"
        self.assertEqual(encode_int(0, with_checksum=True), "00")
        # Verify it decodes
        self.assertEqual(decode_int("00", verify_checksum=True), 0)

    def test_known_checksum_value(self):
        # Crockford's spec: checksum of 31 is 31 mod 37 = 31, symbol "Z".
        encoded = encode_int(31, with_checksum=True)
        self.assertEqual(encoded, "ZZ")
        self.assertEqual(decode_int("ZZ", verify_checksum=True), 31)


class TestDecodeInt(unittest.TestCase):
    def test_case_insensitive(self):
        self.assertEqual(decode_int("abcdef"), decode_int("ABCDEF"))

    def test_visual_alias_o(self):
        self.assertEqual(decode_int("O"), 0)
        self.assertEqual(decode_int("o"), 0)

    def test_visual_alias_i_l(self):
        self.assertEqual(decode_int("I"), 1)
        self.assertEqual(decode_int("l"), 1)
        self.assertEqual(decode_int("L"), 1)

    def test_separators_ignored(self):
        self.assertEqual(decode_int("AB-CD-EF"), decode_int("ABCDEF"))
        self.assertEqual(decode_int("AB CD EF"), decode_int("ABCDEF"))
        self.assertEqual(decode_int("AB_CD_EF"), decode_int("ABCDEF"))

    def test_strict_rejects_lowercase(self):
        with self.assertRaises(ValueError):
            decode_int("abc", strict=True)

    def test_strict_rejects_aliases(self):
        with self.assertRaises(ValueError):
            decode_int("O", strict=True)

    def test_strict_rejects_separators(self):
        with self.assertRaises(ValueError):
            decode_int("A-B", strict=True)

    def test_strict_accepts_canonical(self):
        self.assertEqual(decode_int("ABCDEF", strict=True), decode_int("ABCDEF"))

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            decode_int("")

    def test_invalid_symbol_rejected(self):
        with self.assertRaises(ValueError):
            decode_int("AB!CD")

    def test_checksum_mismatch_raises(self):
        # 0's checksum is 0 (symbol "0"); using a wrong checksum should fail.
        with self.assertRaises(ValueError):
            decode_int("0Z", verify_checksum=True)

    def test_checksum_symbol_u_value_36(self):
        # Checksum value 36 uses symbol U. 36 mod 37 = 36. We need an
        # integer whose mod-37 checksum is 36. 36 itself works.
        encoded = encode_int(36, with_checksum=True)
        # 36 in base32 is "10" (1*32 + 4). Checksum symbol for value 36
        # is index 36, which is in _CHECKSUM_SYMBOLS at [36-32]=[4]="U".
        self.assertTrue(encoded.endswith("U"), f"expected checksum U, got {encoded}")
        self.assertEqual(decode_int(encoded, verify_checksum=True), 36)

    def test_type_error(self):
        with self.assertRaises(TypeError):
            decode_int(123)


class TestNormalizeSymbol(unittest.TestCase):
    def test_uppercases(self):
        self.assertEqual(normalize_symbol("abcdef"), "ABCDEF")

    def test_replaces_o(self):
        self.assertEqual(normalize_symbol("OoOo"), "0000")

    def test_replaces_i_l(self):
        self.assertEqual(normalize_symbol("ILL"), "111")

    def test_removes_separators(self):
        self.assertEqual(normalize_symbol("AB-CD EF_GH"), "ABCDEFGH")

    def test_type_error(self):
        with self.assertRaises(TypeError):
            normalize_symbol(None)


class TestEncodeBytes(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(encode_bytes(b""), "")

    def test_single_zero_byte(self):
        self.assertEqual(encode_bytes(b"\x00"), "0")

    def test_single_byte_max(self):
        self.assertEqual(encode_bytes(b"\xff"), "7Z")

    def test_known_value(self):
        # 0x00FF = 255, which in base32 is 7 and 31 -> "7Z"
        self.assertEqual(encode_bytes(b"\x00\xff"), "07Z")

    def test_leading_zeros_preserved(self):
        encoded = encode_bytes(b"\x00\x00\x01")
        self.assertTrue(encoded.startswith("00"))

    def test_type_error(self):
        with self.assertRaises(TypeError):
            encode_bytes("not bytes")


class TestDecodeBytes(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(decode_bytes(""), b"")

    def test_zero(self):
        self.assertEqual(decode_bytes("0"), b"\x00")

    def test_round_trip(self):
        for data in (b"\x01", b"\xff", b"\x00\x01", b"hello"):
            self.assertEqual(decode_bytes(encode_bytes(data)), data)

    def test_case_insensitive(self):
        self.assertEqual(decode_bytes("7z"), decode_bytes("7Z"))

    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):
            decode_bytes("7!")

    def test_type_error(self):
        with self.assertRaises(TypeError):
            decode_bytes(123)


if __name__ == "__main__":
    unittest.main()
