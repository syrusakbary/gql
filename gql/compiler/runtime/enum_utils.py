from enum import Enum
from functools import partial
from typing import Dict, Type

from dataclasses_json import config


class MissingEnumException(Exception):
    def __init__(self, variable: Enum) -> None:
        self.enum_type = type(variable).__name__

    def __str__(self) -> str:
        return f"Try to encode missing value of enum {self.enum_type}"


def enum_field_metadata(enum_type: Type[Enum]) -> Dict[str, dict]:
    def encode_enum(value: Enum) -> str:
        if value.value == "":
            raise MissingEnumException(value)
        return value.value

    def decode_enum(t: Type[Enum], value: str) -> Enum:
        return t(value)

    return config(encoder=encode_enum, decoder=partial(decode_enum, enum_type))
