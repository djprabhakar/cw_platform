from __future__ import annotations

from pydantic import BaseModel


class Instruction(BaseModel):
    field_name: str
    instruction_text: str
    transformation: str
    confidence: float


class InstructionSet(BaseModel):
    instructions: list[Instruction]

    def for_field(self, field_name: str) -> Instruction | None:
        for instruction in self.instructions:
            if instruction.field_name == field_name:
                return instruction
        return None
