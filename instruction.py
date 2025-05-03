from __future__ import annotations
from typing import Optional

byte = int


def to_bytes(data: byte) -> bytes:
    byte_spec = (1, "little")
    data = 0b1111_1111 & data
    return data.to_bytes(*byte_spec)


class Encoder:
    content: bytearray

    def __init__(self):
        self.content = bytearray([])

    def _push(self, data: byte):
        self.content.extend(to_bytes(data))

    def extend(self, enc: Encoder):
        if isinstance(enc, Encoder):
            self.content.extend(enc.content)

    def encode(self):
        raise NotImplementedError


# region legacy prefix
class LegacyPrefix(Encoder):
    data_bytes: tuple

    def __init__(self):
        super().__init__()

    def encode(self):
        self.content = bytearray([])
        for data in self.data_bytes:
            self._push(data)


class LegacyPrefix1(LegacyPrefix):
    data_bytes: tuple[byte]

    def __init__(self, data0: byte):
        super().__init__()
        self.data_bytes = (data0,)


class LegacyPrefix2(LegacyPrefix):
    data_bytes: tuple[byte, byte]

    def __init__(self, data0: byte, data1: byte):
        super().__init__()
        self.data_bytes = (data0, data1)


class LegacyPrefix3(LegacyPrefix):
    data_bytes: tuple[byte, byte, byte]

    def __init__(self, data0: byte, data1: byte, data2: byte):
        super().__init__()
        self.data_bytes = (data0, data1, data2)


class LegacyPrefix4(LegacyPrefix):
    data_bytes: tuple[byte, byte, byte, byte]

    def __init__(self, data0: byte, data1: byte, data2: byte, data3: byte):
        super().__init__()
        self.data_bytes = (data0, data1, data2, data3)


# endregion


# region escape sequences
class EscapeSequence(Encoder):
    data_bytes: tuple

    def __init__(self):
        super().__init__()
        raise NotImplementedError

    def encode(self):
        self.content = bytearray([])
        for data in self.data_bytes:
            self._push(data)


class EscapeSequence0(EscapeSequence):
    data_bytes: tuple[byte]

    def __init__(
        self,
        data0: byte = 0x0F,
    ):
        super().__init__()
        self.data_bytes = (data0,)


class EscapeSequence1(EscapeSequence):
    data_bytes: tuple[byte, byte]

    def __init__(self, data0: byte = 0x0F, data1: byte = 0x0F):
        super().__init__()
        self.data_bytes = (data0, data1)


class EscapeSequence2(EscapeSequence):
    data_bytes: tuple[byte, byte]

    def __init__(self, data0: byte = 0x0F, data1: byte = 0x38):
        super().__init__()
        self.data_bytes = (data0, data1)


class EscapeSequence3(EscapeSequence):
    data_bytes: tuple[byte, byte]

    def __init__(self, data0: byte = 0x0F, data1: byte = 0x3A):
        super().__init__()
        self.data_bytes = (data0, data1)


# endregion


class Prefix(Encoder):
    legacy_prefixs: Optional[LegacyPrefix] = None
    prefix: Optional[byte] = None
    escape_sequence: Optional[EscapeSequence] = None

    def __init__(
        self,
        legacy_prefixs: Optional[LegacyPrefix] = None,
        prefix: Optional[byte] = None,
        escape_sequence: Optional[EscapeSequence] = None,
    ):
        super().__init__()
        self.legacy_prefixs = legacy_prefixs
        self.prefix = prefix
        self.escape_sequence = escape_sequence

    def encode(self):
        self.content = bytearray([])
        if self.legacy_prefixs is not None:
            self.legacy_prefixs.encode()
            self.extend(self.legacy_prefixs)
        if self.prefix is not None:
            self._push(self.prefix)
        if self.escape_sequence is not None:
            self.escape_sequence.encode()
            self.extend(self.escape_sequence)


# region rex,vex,xop prefix
class PrefixRex(Prefix):
    w: bool
    r: bool
    x: bool
    b: bool

    def __init__(self, w: bool, r: bool, x: bool, b: bool, **kwds):
        super().__init__(**kwds)
        self.w = w
        self.r = r
        self.x = x
        self.b = b

    def encode(self):
        self.content = bytearray([])
        super().encode()
        w = 0b1 if self.w else 0b0
        r = 0b1 if self.r else 0b0
        x = 0b1 if self.x else 0b0
        b = 0b1 if self.b else 0b0
        data = 0b0100 << 4 | w << 3 | r << 2 | x << 1 | b << 0
        self._push(data)


class RvvvvLpp(Encoder):
    r: byte
    vvvv: byte
    L: byte
    pp: byte

    def __init__(self, r: byte, vvvv: byte, L: byte, pp: byte):
        super().__init__()
        self.r = r
        self.vvvv = vvvv
        self.L = L
        self.pp = pp

    def encode(self):
        self.content = bytearray([])
        r = 0b1 & self.r
        vvvv = 0b1111 & self.vvvv
        L = 0b1 & self.L
        pp = 0b11 & self.pp
        data = r << 7 | vvvv << 3 | L << 2 | pp << 0
        self._push(data)


class WvvvvLpp(Encoder):
    w: byte
    vvvv: byte
    L: byte
    pp: byte

    def __init__(self, w: byte, vvvv: byte, L: byte, pp: byte):
        super().__init__()
        self.w = w
        self.vvvv = vvvv
        self.L = L
        self.pp = pp

    def encode(self):
        self.content = bytearray([])
        w = 0b1 & self.w
        vvvv = 0x1111 & self.vvvv
        L = 0b1 & self.L
        pp = 0b11 & self.pp
        data = w << 7 | vvvv << 3 | L << 2 | pp << 0
        self._push(data)


class RxbMapSelect(Encoder):
    r: byte
    x: byte
    b: byte
    map_select: byte

    def __init__(self, r: byte, x: byte, b: byte, map_select: byte):
        super().__init__()
        self.r = r
        self.x = x
        self.b = b
        self.map_select = map_select

    def encode(self):
        self.content = bytearray([])
        r = 0b1 & self.r
        x = 0b1 & self.x
        b = 0b1 & self.b
        map_select = 0b11111 & self.map_select
        data = r << 7 | x << 6 | b << 5 | map_select << 0
        self._push(data)


class PrefixVex1(Prefix):
    r_vvvv_l_pp: RvvvvLpp

    def __init__(self, r_vvvv_l_pp: RvvvvLpp, **kwds):
        super().__init__(prefix=0xC5, **kwds)
        self.r_vvvv_l_pp = r_vvvv_l_pp

    def encode(self):
        self.content = bytearray([])
        super().encode()
        self.r_vvvv_l_pp.encode()
        self.extend(self.r_vvvv_l_pp)


class PrefixVex2(Prefix):
    rxb_map_select: RxbMapSelect
    w_vvvv_l_pp: WvvvvLpp

    def __init__(self, rxb_map_select: RxbMapSelect, w_vvvv_l_pp: WvvvvLpp, **kwds):
        super().__init__(prefix=0xC4, **kwds)
        self.rxb_map_select = rxb_map_select
        self.w_vvvv_l_pp = w_vvvv_l_pp

    def encode(self):
        self.content = bytearray([])
        super().encode()
        self.rxb_map_select.encode()
        self.w_vvvv_l_pp.encode()
        self.extend(self.rxb_map_select)
        self.extend(self.w_vvvv_l_pp)


class PrefixXop(Prefix):
    rxb_map_select: RxbMapSelect
    w_vvvv_l_pp: WvvvvLpp

    def __init__(self, rxb_map_select: RxbMapSelect, w_vvvv_l_pp: WvvvvLpp, **kwds):
        super().__init__(prefix=0x8F, **kwds)
        self.rxb_map_select = rxb_map_select
        self.w_vvvv_l_pp = w_vvvv_l_pp

    def encode(self):
        self.content = bytearray([])
        super().encode()
        self.rxb_map_select.encode()
        self.w_vvvv_l_pp.encode()
        self.extend(self.rxb_map_select)
        self.extend(self.w_vvvv_l_pp)


# endregion


# region mod/rm sib
class ModRM(Encoder):
    mod: byte
    reg: byte
    rm: byte

    def __init__(self, mod: byte, reg: byte, rm: byte):
        super().__init__()
        self.mod = mod
        self.reg = reg
        self.rm = rm

    def encode(self):
        self.content = bytearray([])
        mod = 0b11 & self.mod
        reg = 0b111 & self.reg
        rm = 0b111 & self.rm
        data = mod << 6 | reg << 3 | rm << 0
        self._push(data)


class ScaleIndexBase(Encoder):
    scale: byte
    index: byte
    base: byte

    def __init__(self, scale: byte, index: byte, base: byte):
        super().__init__()
        self.scale = scale
        self.index = index
        self.base = base

    def encode(self):
        self.content = bytearray([])
        scale = 0b11 & self.scale
        index = 0b111 & self.index
        base = 0b111 & self.base
        data = scale << 6 | index << 3 | base << 0
        self._push(data)


# endregion


class Infix(Encoder):
    opcode: byte

    def __init__(self, opcode: byte):
        super().__init__()
        self.opcode = opcode

    def encode(self):
        self.content = bytearray([])
        self._push(self.opcode)


# region displacement, immediate
class Displacement(Encoder):
    data_bytes: tuple

    def __init__(self):
        super().__init__()

    def encode(self):
        self.content = bytearray([])
        for data in self.data_bytes:
            self._push(data)


class Displacement1(Displacement):
    data_bytes: tuple[byte]

    def __init__(self, data0: byte):
        super().__init__()
        self.data_bytes = (data0,)


class Displacement2(Displacement):
    data_bytes: tuple[byte, byte]

    def __init__(self, data0: byte, data1: byte):
        super().__init__()
        self.data_bytes = (data0, data1)


class Displacement4(Displacement):
    data_bytes: tuple[byte, byte, byte, byte]

    def __init__(self, data0: byte, data1: byte, data2: byte, data3: byte):
        super().__init__()
        self.data_bytes = (data0, data1, data2, data3)


class Displacement8(Displacement):
    data_bytes: tuple[byte, byte, byte, byte, byte, byte, byte, byte]

    def __init__(
        self,
        data0: byte,
        data1: byte,
        data2: byte,
        data3: byte,
        data4: byte,
        data5: byte,
        data6: byte,
        data7: byte,
    ):
        super().__init__()
        self.data_bytes = (data0, data1, data2, data3, data4, data5, data6, data7)


class Immediate(Encoder):
    data_bytes: tuple

    def __init__(self):
        super().__init__()

    def encode(self):
        self.content = bytearray([])
        for data in self.data_bytes:
            self._push(data)


class Immediate1(Immediate):
    data_bytes: tuple[byte]

    def __init__(
        self,
        data0: byte,
    ):
        super().__init__()
        self.data_bytes = (data0,)


class Immediate2(Immediate):
    data_bytes: tuple[byte, byte]

    def __init__(
        self,
        data0: byte,
        data1: byte,
    ):
        super().__init__()
        self.data_bytes = (data0, data1)


class Immediate4(Immediate):
    data_bytes: tuple[byte, byte, byte, byte]

    def __init__(
        self,
        data0: byte,
        data1: byte,
        data2: byte,
        data3: byte,
    ):
        super().__init__()
        self.data_bytes = (data0, data1, data2, data3)


class Immediate8(Immediate):
    data_bytes: tuple[byte, byte, byte, byte, byte, byte, byte, byte]

    def __init__(
        self,
        data0: byte,
        data1: byte,
        data2: byte,
        data3: byte,
        data4: byte,
        data5: byte,
        data6: byte,
        data7: byte,
    ):
        super().__init__()
        self.data_bytes = (data0, data1, data2, data3, data4, data5, data6, data7)


# endregion


class Suffix(Encoder):
    modrm: Optional[ModRM]
    sib: Optional[ScaleIndexBase]
    reg: Optional[byte]
    displacement: Optional[Displacement]
    immediate: Optional[Immediate]
    _3dnow_opcode: Optional[byte]

    def __init__(
        self,
        modrm: Optional[ModRM] = None,
        sib: Optional[ScaleIndexBase] = None,
        displacement: Optional[Displacement] = None,
        immediate: Optional[Immediate] = None,
        _3dnow_opcode: Optional[byte] = None,
    ):
        super().__init__()
        self.modrm = modrm
        self.sib = sib
        self.displacement = displacement
        self.immediate = immediate
        self._3dnow_opcode = _3dnow_opcode

    def encode(self):
        self.content = bytearray([])
        if self.modrm is not None:
            self.modrm.encode()
            self.extend(self.modrm)
        if self.sib is not None:
            self.sib.encode()
            self.extend(self.sib)
        if self.displacement is not None:
            self.displacement.encode()
            self.extend(self.displacement)
        if self.immediate is not None:
            self.immediate.encode()
            self.extend(self.immediate)
        if self._3dnow_opcode is not None:
            self._push(self._3dnow_opcode)


class Instruction(Encoder):
    infix: Infix
    prefix: Optional[Prefix]
    suffix: Optional[Suffix]

    def __init__(
        self,
        infix: Infix,
        prefix: Optional[Prefix] = None,
        suffix: Optional[Suffix] = None,
    ):
        super().__init__()
        self.prefix = prefix
        self.infix = infix
        self.suffix = suffix

    def encode(self):
        self.content = bytearray([])
        if self.prefix is not None:
            self.prefix.encode()
            self.extend(self.prefix)
        self.infix.encode()
        self.extend(self.infix)
        if self.suffix is not None:
            self.suffix.encode()
            self.extend(self.suffix)

    def code(self) -> bytearray:
        self.encode()
        return self.content

    def __repr__(self) -> str:
        return " ".join(["{:02X}".format(i) for i in self.content])
