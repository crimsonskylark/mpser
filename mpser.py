import struct
from io import BytesIO
from typing import Dict, Hashable, List, TypeVar, Union

from mp import MsgPackMarker, MsgPackType

T = TypeVar("T")
MappingType = Union[int, str, bool, float]


class MPWrite:
    def __init__(self, buffer: BytesIO):
        self.buffer: BytesIO = buffer

    def _write_pair(self, marker: MsgPackMarker, value: bytes):
        self._write_marker(marker)
        self._write_single(value)

    def _write_marker(self, marker: MsgPackMarker):
        self.buffer.write(struct.pack("<B", marker.value))

    def _write_single(self, value: bytes):
        self.buffer.write(value)

    def _write_any(self, value: MappingType):
        if isinstance(value, int):
            assert (
                value <= 0xFFFFFFFFFFFFFFFF
            ), f"integer value cannot be encoded, {hex(value)} > 0xffffffffffffffff"

            if value <= 0x7F:
                self.write_integer(value, MsgPackMarker.PositiveFixInt)
            elif value > 0x7F and value <= 0xFFFF:
                self.write_integer(value, MsgPackMarker.UInt16)
            elif value > 0xFFFF and value <= 0xFFFFFFFF:
                self.write_integer(value, MsgPackMarker.UInt32)
            else:
                self.write_integer(value, MsgPackMarker.UInt64)
        elif isinstance(value, str):
            length: int = len(value)

            assert (
                length < 0xFFFFFFFF
            ), f"string value cannot be encoded, length {hex(length)} > 0xFFFFFFFF"

            if length <= 0xFF:
                self.write_str(value, MsgPackMarker.Str8)
            elif length > 0xFF and length <= 0xFFFF:
                self.write_str(value, MsgPackMarker.Str16)
            elif length > 0xFFFF and length <= 0xFFFFFFFF:
                self.write_str(value, MsgPackMarker.FixStr)
            else:
                self.write_str(value, MsgPackMarker.Str32)
        elif isinstance(value, float):
            self.write_float(value, MsgPackMarker.Float32)
        elif isinstance(value, bool):
            self.write_bool(value)
        elif isinstance(value, list):
            arr_len: int = len(value)
            arr_type = MsgPackMarker.FixArray

            if arr_len > 0xF and arr_len <= 0xFFFF:
                arr_type = MsgPackMarker.Array16
            elif arr_len > 0xFFFF:
                arr_type = MsgPackMarker.Array32
            self.write_array(value, arr_type)
        elif isinstance(value, dict):
            self.write_map(value)
        elif value is None:
            self.write_nil()
        else:
            raise ValueError(f'"{type(value)}" cannot be encoded')

    def write_integer(self, value: int, t: MsgPackType):
        assert t not in MsgPackType, "invalid msgpack type in `write_integer'"

        match t:
            case MsgPackMarker.PositiveFixInt:
                self._write_single(struct.pack("B", t.value | (value & 0x7F)))
            case MsgPackMarker.NegativeFixInt:
                self._write_single(struct.pack("B", t.value | (value & 0x1F)))
            case MsgPackMarker.UInt8 | MsgPackMarker.Int8:
                self._write_pair(t, struct.pack("b", value & 0xFF))
            case MsgPackMarker.UInt16 | MsgPackMarker.Int16:
                self._write_pair(t, struct.pack(">H", value & 0xFFFF))
            case MsgPackMarker.UInt32 | MsgPackMarker.Int32:
                self._write_pair(t, struct.pack(">I", value & 0xFFFFFFFF))
            case MsgPackMarker.UInt64 | MsgPackMarker.Int64:
                self._write_pair(t, struct.pack(">Q", value & 0xFFFFFFFFFFFFFFFF))

    def write_float(self, value: float, t: MsgPackType):
        assert t not in MsgPackType, "invalid msgpack type in `write_float'"

        match t:
            case MsgPackMarker.Float32:
                self._write_pair(t, struct.pack(">f", value))
            case MsgPackMarker.Float64:
                self._write_pair(t, struct.pack(">d", value))

    def write_str(self, value: str | bytearray, t: MsgPackType):
        assert t not in MsgPackType, "invalid msgpack type in `write_str'"

        length: int = len(value)
        match t:
            case MsgPackMarker.FixStr:
                self._write_single(struct.pack(">B", t.value | (length & 0x1F)))
                self._write_single(value[: length & 0xFFFFFFFF].encode("utf8"))
            case MsgPackMarker.Str8 | MsgPackMarker.Bin8:
                self._write_marker(t)
                self._write_single(struct.pack(">B", length & 0xFF))
                if isinstance(value, str):
                    self._write_single(value[: length & 0xFF].encode("utf8"))
                else:
                    self._write_single(value[: length & 0xFF])
            case MsgPackMarker.Str16 | MsgPackMarker.Bin16:
                self._write_marker(t)
                self._write_single(struct.pack(">H", length & 0xFFFF))
                if isinstance(value, str):
                    self._write_single(value[: length & 0xFFFF].encode("utf8"))
                else:
                    self._write_single(value[: length & 0xFFFF])
            case MsgPackMarker.Str32 | MsgPackMarker.Bin32:
                self._write_marker(t)
                self._write_single(struct.pack(">I", length & 0xFFFFFFFF))
                if isinstance(value, str):
                    self._write_single(value[: length & 0xFFFFFFFF].encode("utf8"))
                else:
                    self._write_single(value[: length & 0xFFFFFFFF])

    def write_bin(self, value: bytearray, t: MsgPackType):
        return self.write_str(value, t)

    def write_bool(self, value: bool):
        self._write_marker(MsgPackMarker.BoolTrue if value else MsgPackMarker.BoolFalse)

    def write_nil(self):
        self._write_marker(MsgPackMarker.Nil)

    def write_array(self, arr: List[T], t: MsgPackType):
        length: int = len(arr)
        match t:
            case MsgPackMarker.FixArray:
                length &= 0xF
                self._write_single(struct.pack(">B", t.value | length))
            case MsgPackMarker.Array16:
                length &= 0xFFFF
                self._write_marker(t)
                self._write_single(struct.pack(">H", length))
            case MsgPackMarker.Array32:
                length &= 0xFFFFFFFF
                self._write_marker(t)
                self._write_single(struct.pack(">I", length))

        for elm in arr:
            self._write_any(elm)

    def write_map(self, value: Dict[Hashable, MappingType]):
        length: int = len(value)

        assert (
            length <= 0xFFFFFFFF
        ), f"dictionary/mapping cannot be encoded, length {hex(length)} > 0xFFFFFFFF"

        if length <= 0xF:
            length &= 0xF
            self._write_single(struct.pack(">B", MsgPackMarker.FixMap.value | length))
        elif length > 0xF and length <= 0xFFFF:
            length &= 0xFFFF
            self._write_marker(MsgPackMarker.Map16)
            self._write_single(struct.pack(">H", length))
        else:
            length &= 0xFFFFFFFF
            self._write_marker(MsgPackMarker.Map32)
            self._write_single(struct.pack(">I", length))

        for k, v in value.items():
            self._write_any(k)
            self._write_any(v)


class MPRead:
    def __init__(self, buffer: BytesIO):
        self.buffer = buffer

    def _read_and_advance(self, size: int = 1) -> bytes:
        return self.buffer.read(size)

    def read_int(self) -> int:
        byte = self._read_and_advance()
        value = int.from_bytes(byte, "little")

        print(byte, self.buffer.getvalue().hex())

        if (value & 0x80) == 0:
            return struct.unpack("B", byte)[0] & 0x7F
        elif (value & 0xE0) == 0xE0:
            return struct.unpack("b", byte)[0]

        match MsgPackMarker(value):
            case MsgPackMarker.UInt8:
                return struct.unpack("B", self._read_and_advance())
            case MsgPackMarker.Int8:
                return struct.unpack("b", self._read_and_advance())
            case MsgPackMarker.UInt16:
                return struct.unpack(">H", self._read_and_advance(2))[0]
            case MsgPackMarker.Int16:
                return struct.unpack(">h", self._read_and_advance(2))[0]
            case MsgPackMarker.UInt32:
                return struct.unpack(">I", self._read_and_advance(4))[0]
            case MsgPackMarker.Int32:
                return struct.unpack(">i", self._read_and_advance(4))[0]
            case MsgPackMarker.UInt64:
                return struct.unpack(">Q", self._read_and_advance(8))[0]
            case MsgPackMarker.Int64:
                return struct.unpack(">q", self._read_and_advance(8))[0]

    def read_float(self) -> float:
        match MsgPackMarker(struct.unpack("B", self._read_and_advance())[0]):
            case MsgPackMarker.Float32:
                return struct.unpack(">f", self._read_and_advance(4))[0]
            case MsgPackMarker.Float64:
                return struct.unpack(">d", self._read_and_advance(8))[0]


def test_int():
    m = MPWrite(BytesIO())

    m.write_integer(45, MsgPackMarker.PositiveFixInt)
    assert m.buffer.getvalue().hex() == "2d"

    m.write_integer(-12, MsgPackMarker.NegativeFixInt)
    assert m.buffer.getvalue().hex() == "2df4"

    m.write_integer(65538, MsgPackMarker.UInt16)
    assert m.buffer.getvalue().hex() == "2df4cd0002"

    m.write_integer(4294967295, MsgPackMarker.UInt32)
    assert m.buffer.getvalue().hex() == "2df4cd0002ceffffffff"

    m.write_integer(4294967297, MsgPackMarker.UInt32)
    assert m.buffer.getvalue().hex() == "2df4cd0002ceffffffffce00000001"

    m.write_integer(2147483645, MsgPackMarker.Int32)
    assert m.buffer.getvalue().hex() == "2df4cd0002ceffffffffce00000001d27ffffffd"

    m.write_integer(2147483649, MsgPackMarker.Int32)
    assert (
        m.buffer.getvalue().hex()
        == "2df4cd0002ceffffffffce00000001d27ffffffdd280000001"
    )

    mr = MPRead(m.buffer)

    m.buffer.seek(0)

    assert mr.read_int() == 45
    assert mr.read_int() == -12
    assert mr.read_int() == 2
    assert mr.read_int() == 4294967295
    assert mr.read_int() == 1


def test_float():
    m = MPWrite(BytesIO())

    m.write_float(3.14, MsgPackMarker.Float32)
    assert m.buffer.getvalue().hex() == "ca4048f5c3"

    m.write_float(5.99998, MsgPackMarker.Float32)
    assert m.buffer.getvalue().hex() == "ca4048f5c3ca40bfffd6"

    m.write_float(987.981, MsgPackMarker.Float32)
    assert m.buffer.getvalue().hex() == "ca4048f5c3ca40bfffd6ca4476fec9"

    mr = MPRead(m.buffer)

    m.buffer.seek(0)

    assert mr.read_float() == 3.140000104904175
    assert mr.read_float() == 5.9999799728393555
    assert mr.read_float() == 987.9810180664062


def test_str():
    m = MPWrite(BytesIO())

    m.write_str("Hello world", MsgPackMarker.FixStr)
    assert m.buffer.getvalue().hex() == "ab48656c6c6f20776f726c64"

    LI: str = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
        "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
    )

    m.write_str(LI, MsgPackMarker.Str16)
    assert (
        m.buffer.getvalue().hex()
        == "ab48656c6c6f20776f726c64da01ba4c6f72656d20697073756d20646f6c6f722073697420616d65742c20636f6e73656374657475722061646970697363696e6720656c69742c2073656420646f20656975736d6f642074656d706f7220696e6369646964756e74207574206c61626f726520657420646f6c6f7265206d61676e6120616c697175612e557420656e696d206164206d696e696d2076656e69616d2c2071756973206e6f737472756420657865726369746174696f6e20756c6c616d636f206c61626f726973206e69736920757420616c697175697020657820656120636f6d6d6f646f20636f6e7365717561742e44756973206175746520697275726520646f6c6f7220696e20726570726568656e646572697420696e20766f6c7570746174652076656c697420657373652063696c6c756d20646f6c6f726520657520667567696174206e756c6c612070617269617475722e4578636570746575722073696e74206f6363616563617420637570696461746174206e6f6e2070726f6964656e742c2073756e7420696e2063756c706120717569206f666669636961206465736572756e74206d6f6c6c697420616e696d20696420657374206c61626f72756d2e"
    )

    LI_ru: str = (
        "Давно выяснено, что при оценке дизайна и композиции читаемый текст мешает сосредоточиться."
        "Lorem Ipsum используют потому, что тот обеспечивает более или менее стандартное заполнение шаблона"
    )

    m.write_str(LI_ru, MsgPackMarker.Str16)
    assert (
        m.buffer.getvalue().hex()
        == "ab48656c6c6f20776f726c64da01ba4c6f72656d20697073756d20646f6c6f722073697420616d65742c20636f6e73656374657475722061646970697363696e6720656c69742c2073656420646f20656975736d6f642074656d706f7220696e6369646964756e74207574206c61626f726520657420646f6c6f7265206d61676e6120616c697175612e557420656e696d206164206d696e696d2076656e69616d2c2071756973206e6f737472756420657865726369746174696f6e20756c6c616d636f206c61626f726973206e69736920757420616c697175697020657820656120636f6d6d6f646f20636f6e7365717561742e44756973206175746520697275726520646f6c6f7220696e20726570726568656e646572697420696e20766f6c7570746174652076656c697420657373652063696c6c756d20646f6c6f726520657520667567696174206e756c6c612070617269617475722e4578636570746575722073696e74206f6363616563617420637570696461746174206e6f6e2070726f6964656e742c2073756e7420696e2063756c706120717569206f666669636961206465736572756e74206d6f6c6c697420616e696d20696420657374206c61626f72756d2eda00bcd094d0b0d0b2d0bdd0be20d0b2d18bd18fd181d0bdd0b5d0bdd0be2c20d187d182d0be20d0bfd180d0b820d0bed186d0b5d0bdd0bad0b520d0b4d0b8d0b7d0b0d0b9d0bdd0b020d0b820d0bad0bed0bcd0bfd0bed0b7d0b8d186d0b8d0b820d187d0b8d182d0b0d0b5d0bcd18bd0b920d182d0b5d0bad181d18220d0bcd0b5d188d0b0d0b5d18220d181d0bed181d180d0b5d0b4d0bed182d0bed187d0b8d182d18cd181d18f2e4c6f72656d20497073756d20d0b8d181d0bfd0bed0bbd18cd0b7d183d18ed18220d0bfd0bed182d0bed0bcd1832c20d187d182d0be20d182d0bed18220d0bed0b1d0b5d181d0bfd0b5d187d0b8d0b2d0b0d0b5d18220d0b1d0bed0bbd0b5d0b520d0b8d0bbd0b820d0bcd0b5d0bdd0b5d0b520d181d182d0b0d0bdd0b4d0b0d180d182d0bdd0bed0b520d0b7d0b0d0bfd0bed0bbd0bdd0b5d0bdd0b8d0b520d188d0b0d0b1d0bbd0bed0bdd0b0"
    )


def test_bin():
    m = MPWrite(BytesIO())

    m.write_bin(bytearray(range(32)), MsgPackMarker.Bin8)
    assert (
        m.buffer.getvalue().hex()
        == "c420000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )

    m.write_bin(b"\x41\x41\x41\x41\x41", MsgPackMarker.Bin16)
    assert (
        m.buffer.getvalue().hex()
        == "c420000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1fc500054141414141"
    )


def test_array():
    m = MPWrite(BytesIO())

    values: List[object] = [
        0xCA,
        0xFE,
        0xBA,
        0xBE,
        "Hello world",
        "45",
        None,
        None,
        1.618,
        3.14,
        {"hello": "world"},
    ]

    m.write_array(values, MsgPackMarker.Array16)
    assert (
        m.buffer.getvalue().hex()
        == "dc000bcd00cacd00fecd00bacd00bed90b48656c6c6f20776f726c64d9023435c0c0ca3fcf1aa0ca4048f5c381d90568656c6c6fd905776f726c64"
    )


def test_mapping():
    m = MPWrite(BytesIO())

    values: Dict[Hashable, MappingType] = {
        "Hello": "World",
        "A": ["B", "C", "D"],
        "user": {"abc": "cba"},
        "connected": False,
        "authenticated": True,
        "password": None,
    }

    m.write_map(values)
    assert (
        m.buffer.getvalue().hex()
        == "86d90548656c6c6fd905576f726c64d9014193d90142d90143d90144d9047573657281d903616263d903636261d909636f6e6e656374656400d90d61757468656e7469636174656401d90870617373776f7264c0"
    )
