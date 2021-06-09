from enum import Enum
from typing import Any, Dict, Union

from dataclasses_json import DataClassJsonMixin

from ..renderer_dataclasses import CustomScalar
from .enum_utils import MissingEnumException


def encode_value(
    value: Union[DataClassJsonMixin, Any, Enum],
    custom_scalars: Dict[str, CustomScalar] = {},
) -> Union[Dict[str, Any], str]:
    if isinstance(value, DataClassJsonMixin):
        return encode_variables(value.to_dict(), custom_scalars)
    elif isinstance(value, Enum):
        if value.value == "":
            raise MissingEnumException(value)
        return value.value
    for _, custom_scalar in custom_scalars.items():
        if custom_scalar.encoder and isinstance(value, custom_scalar.type):
            return custom_scalar.encoder(value)
    return value


def encode_variables(
    variables: Dict[str, Any], custom_scalars: Dict[str, CustomScalar] = {}
) -> Dict[str, Any]:
    new_variables: Dict[str, Any] = {}
    for key, value in variables.items():
        if isinstance(value, list):
            new_list = [encode_value(val, custom_scalars) for val in value]
            new_variables[key] = new_list
        else:
            new_variables[key] = encode_value(value, custom_scalars)
    return new_variables
