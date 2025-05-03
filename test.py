from typing import Literal
from instruction import *
import registers as regs


def dump2hex(data: bytearray) -> str:
    return " ".join(["{:02X}".format(i) for i in data])


def pack(data: int, n_bytes: int = 1) -> list[int]:
    return list(data.to_bytes(n_bytes, "little"))


class Assembler:
    instructions: list[Instruction]

    def __init__(self, instructions: list[Instruction] = []) -> None:
        self.instructions = instructions

    def _push(self, inst: Instruction):
        self.instructions.append(inst)

    def emit(self):
        content = bytearray([])
        for inst in self.instructions:
            content.extend(inst.code())
        return content


Factor = Literal[1] | Literal[2] | Literal[4] | Literal[8]


class Argument:

    def __init__(
        self,
        reg: Optional[byte] = None,
        modrm: Optional[ModRM] = None,
        sib: Optional[ScaleIndexBase] = None,
        imm: Optional[int] = None,
        n_of_imm: Optional[Factor] = None,
        disp: Optional[int] = None,
        n_of_disp: Optional[Factor] = None,
        _3dnow_opcode: Optional[byte] = None,
    ) -> None:
        self.reg = reg
        self.modrm = modrm
        self.sib = sib
        self.imm = imm
        self.n_of_imm = n_of_imm
        self.disp = disp
        self.n_of_disp = n_of_disp
        self._3dnow_opcode = _3dnow_opcode

    def build_immediate(self) -> Immediate:
        assert self.imm is not None and self.n_of_imm is not None
        Imm = {1: Immediate1, 2: Immediate2, 4: Immediate4, 8: Immediate8}
        return Imm[self.n_of_imm](*pack(self.imm))

    def build_displacement(self) -> Displacement:
        assert self.imm is not None and self.n_of_imm is not None
        Disp = {1: Displacement1, 2: Displacement2, 4: Displacement4, 8: Displacement8}
        return Disp[self.n_of_imm](*pack(self.imm))

    def build(self):
        suffix = Suffix(
            modrm=self.modrm,
            sib=self.sib,
            displacement=self.build_displacement(),
            immediate=self.build_immediate(),
            _3dnow_opcode=self._3dnow_opcode,
        )
        return suffix


class ReturnAssembler(Assembler):

    def near_ret(self):
        inst = Instruction(Infix(0xC3))
        self._push(inst)

    def far_ret(self):
        inst = Instruction(Infix(0xCB))
        self._push(inst)

    def near_ret_imm16(self, imm: int):
        imm2 = Immediate2(*pack(imm, 2))
        inst = Instruction(Infix(0xC2), suffix=Suffix(immediate=imm2))
        self._push(inst)

    def far_ret_imm16(self, imm: int):
        imm2 = Immediate2(*pack(imm, 2))
        inst = Instruction(Infix(0xCA), suffix=Suffix(immediate=imm2))
        self._push(inst)


class NopAssembler(Assembler):
    def nop(self):
        inst = Instruction(Infix(0x90))
        self._push(inst)

    def nop_reg16(self):
        raise NotImplementedError

    def nop_mem16(self):
        raise NotImplementedError

    def nop_reg32(self):
        raise NotImplementedError

    def nop_mem32(self):
        raise NotImplementedError


class MovAssembler(Assembler):
    def mov_mem32_indirect_imm32(
        self, rm: int, imm: int, sib: Optional[ScaleIndexBase] = None
    ):
        x = False
        b = bool((rm & 0b1000) >> 3)
        if rm == 0b0100 and sib is not None:
            x = bool((sib.index & 0b1000) >> 3)
            b = bool((sib.base & 0b1000) >> 3)
        print(x, b)
        prefix = PrefixRex(
            w=False,
            r=False,
            x=x,
            b=b,
        )
        infix = Infix(0xC7)
        modrm = ModRM(0b00, 0b000, rm)
        imm4 = Immediate4(*pack(imm, n_bytes=4))
        suffix = Suffix(modrm=modrm, sib=sib if rm == 0b0100 else None, immediate=imm4)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_mem16_indirect_imm16(
        self, rm: int, imm: int, sib: Optional[ScaleIndexBase] = None
    ):
        x = False
        b = bool((rm & 0b1000) >> 3)
        if rm == 0b0100 and sib is not None:
            x = bool((sib.index & 0b1000) >> 3)
            b = bool((sib.base & 0b1000) >> 3)
        print(x, b)
        prefix = PrefixRex(
            w=False,
            r=False,
            x=x,
            b=b,
            legacy_prefixs=LegacyPrefix2(0x67, 0x66),
        )
        infix = Infix(0xC7)
        modrm = ModRM(0b00, 0b000, rm)
        imm2 = Immediate2(*pack(imm, n_bytes=2))
        suffix = Suffix(modrm=modrm, sib=sib if rm == 0b0100 else None, immediate=imm2)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_mem8_indirect_imm8(
        self, rm: int, imm: int, sib: Optional[ScaleIndexBase] = None
    ):
        x = False
        b = bool((rm & 0b1000) >> 3)
        if rm == 0b0100 and sib is not None:
            x = bool((sib.index & 0b1000) >> 3)
            b = bool((sib.base & 0b1000) >> 3)
        prefix = PrefixRex(w=False, r=False, x=x, b=b)
        infix = Infix(0xC6)
        modrm = ModRM(0b00, 0b000, rm)
        imm1 = Immediate1(*pack(imm, n_bytes=1))
        suffix = Suffix(modrm=modrm, sib=sib if rm == 0b0100 else None, immediate=imm1)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_mem8_rel_imm8(self, disp: int, imm: int):
        # prefix = PrefixRex(w=False, r=False, x=False, b=False)
        infix = Infix(0xC6)
        modrm = ModRM(0b00, 0b000, 0b0101)
        disp4 = Displacement4(*pack(disp, n_bytes=4))
        imm1 = Immediate1(*pack(imm, n_bytes=1))
        suffix = Suffix(modrm=modrm, displacement=disp4, immediate=imm1)
        inst = Instruction(infix=infix, suffix=suffix)
        self._push(inst)

    def mov_mem8_disp1_imm8(
        self, rm: int, imm: int, disp: int, sib: Optional[ScaleIndexBase] = None
    ):
        x = False
        b = bool((rm & 0b1000) >> 3)
        if rm == 0b0100 and sib is not None:
            x = bool((sib.index & 0b1000) >> 3)
            b = bool((sib.base & 0b1000) >> 3)

        prefix = PrefixRex(w=False, r=False, x=x, b=b)
        infix = Infix(0xC6)
        modrm = ModRM(0b01, 0b000, rm)
        disp1 = Displacement1(*pack(disp, n_bytes=1))
        imm1 = Immediate1(*pack(imm, n_bytes=1))
        suffix = Suffix(
            modrm=modrm,
            sib=sib if rm == 0b0100 else None,
            immediate=imm1,
            displacement=disp1,
        )
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_mem8_disp4_imm8(
        self, rm: int, imm: int, disp: int, sib: Optional[ScaleIndexBase] = None
    ):
        x = False
        b = bool((rm & 0b1000) >> 3)
        if rm == 0b0100 and sib is not None:
            x = bool((sib.index & 0b1000) >> 3)
            b = bool((sib.base & 0b1000) >> 3)

        prefix = PrefixRex(w=False, r=False, x=x, b=b)
        infix = Infix(0xC6)
        modrm = ModRM(0b10, 0b000, rm)
        disp4 = Displacement4(*pack(disp, n_bytes=4))
        imm1 = Immediate1(*pack(imm, n_bytes=1))
        suffix = Suffix(
            modrm=modrm,
            sib=sib if rm == 0b0100 else None,
            immediate=imm1,
            displacement=disp4,
        )
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg8_mem8_disp32(
        self,
        src: int,
        tgt: int,
        disp: int,
        sib: Optional[ScaleIndexBase] = None,
    ):
        r = bool((0b1000 & tgt) >> 3)
        if src == 0b100 and sib is not None:
            b = bool((0b1000 & sib.base) >> 3)
            x = bool((0b1000 & sib.index) >> 3)
        else:
            x = False
            b = bool((0b1000 & src) >> 3)

        prefix = PrefixRex(w=False, r=r, x=x, b=b)
        infix = Infix(0x8A)
        modrm = ModRM(0b10, reg=tgt, rm=src)
        suffix = Suffix(
            modrm=modrm,
            sib=sib if src == 0b100 else None,
            displacement=Displacement4(*pack(disp, 4)),
        )
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg8_mem8_disp8(
        self, src: int, tgt: int, disp: int, sib: Optional[ScaleIndexBase] = None
    ):
        r = bool((0b1000 & tgt) >> 3)
        if src == 0b100 and sib is not None:
            b = bool((0b1000 & sib.base) >> 3)
            x = bool((0b1000 & sib.index) >> 3)
        else:
            x = False
            b = bool((0b1000 & src) >> 3)

        prefix = PrefixRex(w=False, r=r, x=x, b=b)
        infix = Infix(0x8A)
        modrm = ModRM(0b01, reg=tgt, rm=src)
        suffix = Suffix(
            modrm=modrm,
            sib=sib if src == 0b100 else None,
            displacement=Displacement1(*pack(disp, 1)),
        )
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg8_mem8(
        self,
        rm: int,
        reg: int,
        disp: Optional[int] = None,
        sib: Optional[ScaleIndexBase] = None,
    ):
        r = bool((0b1000 & reg) >> 3)
        if rm == 0b100 and sib is not None:
            b = bool((0b1000 & sib.base) >> 3)
            x = bool((0b1000 & sib.index) >> 3)
        else:
            x = False
            b = bool((0b1000 & rm) >> 3)

        prefix = PrefixRex(w=False, r=r, x=x, b=b)
        infix = Infix(0x8A)
        modrm = ModRM(0b00, reg=reg, rm=rm)
        suffix = Suffix(
            modrm=modrm,
            sib=sib if rm == 0b100 else None,
            displacement=(
                Displacement4(*pack(disp, 4))
                if rm == 0b101 and disp is not None
                else None
            ),
        )
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg8_reg8(self, src: int, tgt: int):
        r = bool((0b1000 & tgt) >> 3)
        b = bool((0b1000 & src) >> 3)
        prefix = PrefixRex(w=False, r=r, x=False, b=b)
        infix = Infix(0x8A)
        modrm = ModRM(0b11, reg=tgt, rm=src)
        suffix = Suffix(
            modrm=modrm,
        )
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg8_imm8(self, reg: int, imm: int):
        lflag = bool((0b0001_0000 & reg) >> 4)
        flag = bool((0b0000_1000 & reg) >> 3)
        prefix = None
        if lflag or flag:
            prefix = PrefixRex(w=False, r=False, x=False, b=flag)
        infix = Infix(0xB0 | (0b0000_0111 & reg))
        imm1 = Immediate1(*pack(imm, n_bytes=1))
        suffix = Suffix(immediate=imm1)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg16_imm16(self, reg: int, imm: int):
        flag = bool((0b0000_1000 & reg) >> 3)
        prefix = PrefixRex(
            w=False,
            r=False,
            x=False,
            b=flag,
            legacy_prefixs=LegacyPrefix1(0x66),
        )
        infix = Infix(0xB8 | (0b0000_0111 & reg))
        imm2 = Immediate2(*pack(imm, n_bytes=2))
        suffix = Suffix(immediate=imm2)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg32_imm32(self, reg: int, imm: int):
        flag = bool((0b0000_1000 & reg) >> 3)
        prefix = PrefixRex(
            w=False,
            r=False,
            x=False,
            b=flag,
        )
        infix = Infix(0xB8 | (0b0000_0111 & reg))
        imm4 = Immediate4(*pack(imm, n_bytes=4))
        suffix = Suffix(immediate=imm4)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)

    def mov_reg64_imm64(self, reg: int, imm: int):
        flag = bool((0b0000_1000 & reg) >> 3)
        prefix = PrefixRex(w=True, r=False, x=False, b=flag)
        # print(prefix.encode(), prefix.content)
        infix = Infix(0xB8 | (0b0000_0111 & reg))
        imm8 = Immediate8(*pack(imm, n_bytes=8))
        suffix = Suffix(immediate=imm8)
        inst = Instruction(prefix=prefix, infix=infix, suffix=suffix)
        self._push(inst)


"""
ret_assembler = ReturnAssembler()
ret_assembler.far_ret()
ret_assembler.near_ret()
ret_assembler.near_ret_imm16(0x1122)
ret_assembler.far_ret_imm16(0x1122)
code = ret_assembler.emit()

mov_assembler.mov_reg8_imm8(regs.R10B, 0x22)
mov_assembler.mov_reg16_imm16(regs.R10W, 0x0022)
mov_assembler.mov_reg32_imm32(regs.R10D, 0x1122_3344)
mov_assembler.mov_reg64_imm64(regs.R10, 0x11223344_55667788)

mov_assembler.mov_reg8_reg8(tgt=regs.AX, src=regs.R8)
mov_assembler.mov_reg8_mem8(tgt=regs.AX, src=regs.R8)
mov_assembler.mov_reg8_mem8(
    tgt=regs.AX, src=0b100, sib=ScaleIndexBase(scale=0b11, index=regs.R9, base=regs.R10)
)
mov_assembler.mov_reg8_mem8(
    tgt=regs.AX,
    src=0b101,
    sib=ScaleIndexBase(scale=0b11, index=regs.R9, base=regs.R10),
    disp=0x2333_2333,
)
mov_assembler.mov_reg8_mem8_disp8(
    tgt=regs.AX,
    src=0b100,
    sib=ScaleIndexBase(scale=0b11, index=regs.R9, base=regs.R10),
    disp=0x22,
)
mov_assembler.mov_reg8_mem8_disp32(
    tgt=regs.AX,
    src=0b100,
    sib=ScaleIndexBase(scale=0b11, index=regs.R9, base=regs.R10),
    disp=0x2233_4455,
)

mov_assembler.mov_mem8_indirect_imm8(regs.R8, 0xFF)
mov_assembler.mov_mem8_indirect_imm8(
    0b0100, 0xFF, sib=ScaleIndexBase(0b01, regs.R9, regs.R10)
)
mov_assembler.mov_mem8_rel_imm8(0x11223344, 0xFF)
mov_assembler.mov_mem8_disp1_imm8(regs.R8, imm=0xFF, disp=0x22)
mov_assembler.mov_mem8_disp1_imm8(
    0b0100, imm=0xFF, disp=0x22, sib=ScaleIndexBase(0b11, regs.R9, regs.R10)
)
mov_assembler.mov_mem8_disp4_imm8(regs.R8, imm=0xFF, disp=0x11223344)
mov_assembler.mov_mem8_disp4_imm8(
    0b0100, imm=0xFF, disp=0x11223344, sib=ScaleIndexBase(0b11, regs.R9, regs.R10)
)
mov_assembler.mov_mem16_indirect_imm16(regs.R8D, 0x1122)
mov_assembler.mov_mem16_indirect_imm16(
    0b0100, 0x1122, sib=ScaleIndexBase(0b11, regs.R9, regs.R10)
)
mov_assembler.mov_mem32_indirect_imm32(regs.R8W, 0x11223344)
mov_assembler.mov_mem32_indirect_imm32(
    0b0100, 0x11223344, sib=ScaleIndexBase(0b11, regs.R9W, regs.R10W)
)
"""


mov_assembler = MovAssembler()

mov_assembler.mov_reg8_imm8(regs.AL, 0x22)
mov_assembler.mov_reg8_imm8(regs.AH, 0x22)
mov_assembler.mov_reg8_imm8(regs.SPL, 0x22)
mov_assembler.mov_reg8_imm8(regs.R8B, 0x22)
mov_assembler.mov_reg8_imm8(regs.R12B, 0x22)
code = mov_assembler.emit()
print(dump2hex(code))
with open("test.bin", "wb") as f:
    f.write(code)
