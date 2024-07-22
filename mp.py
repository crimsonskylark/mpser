from enum import Enum

INT_MAX_VALUE: int = (2**64) - 1
BIN_MAX_LENGTH: int = (2**32) - 1
STR_MAX_BYTE_LENGTH: int = (2**32) - 1
ARRAY_MAX_ELM_COUNT: int = (2**32) - 1
MAP_MAX_KV_ASSOC: int = (2**32) - 1


class MsgPackType(Enum):
    Integer = 0
    Nil = 1
    Boolean = 2
    Float = 3
    RawString = 4
    RawBinary = 5
    Array = 6
    Map = 7
    Ext = 8


class MsgPackMarker(Enum):
    PositiveFixInt = 0x00
    NegativeFixInt = 0xE0
    FixMap = 0x80
    FixArray = 0x90
    FixStr = 0xA0

    Nil = 0xC0

    UNUSED = 0xC1

    BoolFalse = 0xC2
    BoolTrue = 0xC3

    Bin8 = 0xC4
    Bin16 = 0xC5
    Bin32 = 0xC6

    Ext8 = 0xC7
    Ext16 = 0xC8
    Ext32 = 0xC9

    Float32 = 0xCA
    Float64 = 0xCB

    UInt8 = 0xCC
    UInt16 = 0xCD
    UInt32 = 0xCE
    UInt64 = 0xCF

    Int8 = 0xD0
    Int16 = 0xD1
    Int32 = 0xD2
    Int64 = 0xD3

    FixExt1 = 0xD4
    FixExt2 = 0xD5
    FixExt4 = 0xD6
    FixExt8 = 0xD7
    FixExt16 = 0xD8

    Str8 = 0xD9
    Str16 = 0xDA
    Str32 = 0xDB

    Array16 = 0xDC
    Array32 = 0xDD

    Map16 = 0xDE
    Map32 = 0xDF
