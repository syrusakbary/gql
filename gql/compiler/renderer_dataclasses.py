import importlib.util
from dataclasses import dataclass
from importlib.abc import Loader
from typing import Any, Callable, Dict, List, Optional, Type

from graphql import GraphQLSchema
from marshmallow.fields import Field as MarshmallowField

from .query_parser import (
    ParsedField,
    ParsedObject,
    ParsedOperation,
    ParsedQuery,
    ParsedVariableDefinition,
)
from .utils_codegen import CodeChunk, camel_case_to_lower_case

DEFAULT_MAPPING = {
    "ID": "str",
    "String": "str",
    "Int": "int",
    "Float": "Number",
    "Boolean": "bool",
}


@dataclass
class CustomScalar:
    name: str
    type: Type[Any]
    encoder: Optional[Callable[..., Any]] = None
    decoder: Optional[Callable[..., Any]] = None
    mm_field: Optional[MarshmallowField] = None


class DataclassesRenderer:
    def __init__(
        self, schema: GraphQLSchema, config_path: Optional[str] = None
    ) -> None:
        self.schema = schema
        self.config_path = config_path
        self.custom_scalars = {}
        if config_path is not None:
            spec = importlib.util.spec_from_file_location("config", config_path)
            config = importlib.util.module_from_spec(spec)
            assert isinstance(spec.loader, Loader)
            spec.loader.exec_module(config)
            assert hasattr(config, "custom_scalars"), "Custom scalars is not in config"
            self.custom_scalars = getattr(config, "custom_scalars")

    def render(
        self,
        parsed_query: ParsedQuery,
        fragment_name_to_importpath: Dict[str, str],
        enum_name_to_importpath: Dict[str, str],
        input_name_to_importpath: Dict[str, str],
        config_importpath: Optional[str],
    ) -> str:
        buffer = CodeChunk()
        self.__write_file_header(buffer)
        buffer.write("from dataclasses import dataclass, field as _field")
        self.__render_customer_scalars_imports(buffer, config_importpath)
        buffer.write("from gql.compiler.runtime.variables import encode_variables")
        buffer.write("from gql import gql, Client")
        buffer.write("from gql.transport.exceptions import TransportQueryError")
        buffer.write("from functools import partial")
        buffer.write("from numbers import Number")
        buffer.write(
            "from typing import Any, AsyncGenerator, Dict, List, Generator, Optional"
        )
        buffer.write("from dataclasses_json import DataClassJsonMixin, config")
        buffer.write("")
        for fragment_name in sorted(set(parsed_query.used_fragments)):
            importpath = fragment_name_to_importpath[fragment_name]
            buffer.write(
                f"from {importpath} import {fragment_name}, "
                f"QUERY as {fragment_name}Query"
            )
            buffer.write("")
        enum_names = set()
        for enum in parsed_query.enums:
            enum_names.add(enum.name)
        if enum_names:
            buffer.write(
                "from gql.compiler.runtime.enum_utils import enum_field_metadata"
            )
            for enum_name in sorted(enum_names):
                importpath = enum_name_to_importpath[enum_name]
                buffer.write(f"from {importpath} import {enum_name}")
            buffer.write("")
        input_object_names = set()
        for input_object in parsed_query.input_objects:
            input_object_names.add(input_object.name)
        if input_object_names:
            for input_object_name in sorted(input_object_names):
                importpath = input_name_to_importpath[input_object_name]
                buffer.write(f"from {importpath} import {input_object_name}")
            buffer.write("")

        sorted_objects = sorted(
            parsed_query.objects,
            key=lambda obj: 1 if isinstance(obj, ParsedOperation) else 0,
        )
        for obj in sorted_objects:
            buffer.write("")
            self.__render_operation(parsed_query, buffer, obj, config_importpath)

        if parsed_query.fragment_objects:
            buffer.write("# fmt: off")
            if parsed_query.used_fragments:
                queries = [
                    f"{fragment_name}Query"
                    for fragment_name in sorted(set(parsed_query.used_fragments))
                ]
                buffer.write(f'QUERY: List[str] = {" + ".join(queries)} + ["""')
            else:
                buffer.write('QUERY: List[str] = ["""')
            buffer.write(parsed_query.query)
            buffer.write('"""]')
            buffer.write("")

        for fragment_obj in parsed_query.fragment_objects:
            self.__render_fragment(parsed_query, buffer, fragment_obj)

        return str(buffer)

    def render_enums(self, parsed_query: ParsedQuery) -> Dict[str, str]:
        result = {}

        for enum in parsed_query.enums + parsed_query.internal_enums:
            buffer = CodeChunk()
            self.__write_file_header(buffer)
            buffer.write("from enum import Enum")
            buffer.write("")
            buffer.write("")
            with buffer.write_block(f"class {enum.name}(Enum):"):
                for value_name, value in enum.values.items():
                    if isinstance(value, str):
                        value = f'"{value}"'

                    buffer.write(f"{value_name} = {value}")
                buffer.write('MISSING_ENUM = ""')
                buffer.write("")
                buffer.write("@classmethod")
                with buffer.write_block(
                    f'def _missing_(cls, value: object) -> "{enum.name}":'
                ):
                    buffer.write("return cls.MISSING_ENUM")
            buffer.write("")
            result[enum.name] = str(buffer)

        return result

    def render_input_objects(
        self, parsed_query: ParsedQuery, config_importpath: Optional[str]
    ) -> Dict[str, str]:
        result = {}

        for input_object in parsed_query.input_objects + parsed_query.internal_inputs:
            buffer = CodeChunk()
            self.__write_file_header(buffer)
            buffer.write("from dataclasses import dataclass, field as _field")
            buffer.write("from functools import partial")
            self.__render_customer_scalars_imports(buffer, config_importpath)
            buffer.write("from numbers import Number")
            buffer.write(
                "from typing import Any, AsyncGenerator, Dict, List, Generator,"
                " Optional"
            )
            buffer.write("")
            buffer.write("from dataclasses_json import DataClassJsonMixin, config")
            buffer.write("")
            enum_names = set()
            for enum in input_object.input_enums:
                enum_names.add(enum.name)
            if enum_names:
                buffer.write(
                    "from gql.compiler.runtime.enum_utils import enum_field_metadata"
                )
                for enum_name in sorted(enum_names):
                    buffer.write(
                        f"from ..enum.{camel_case_to_lower_case(enum_name)}"
                        f" import {enum_name}"
                    )
                buffer.write("")
            input_object_names = set()
            for input_dep in input_object.inputs:
                input_object_names.add(input_dep.name)
            if input_object_names:
                for input_object_name in sorted(input_object_names):
                    buffer.write(
                        f"from ..input.{camel_case_to_lower_case(input_object_name)} "
                        f"import {input_object_name}"
                    )
                buffer.write("")

            buffer.write("")
            self.__render_object(parsed_query, buffer, input_object, True)
            result[input_object.name] = str(buffer)

        return result

    def __render_object(
        self,
        parsed_query: ParsedQuery,
        buffer: CodeChunk,
        obj: ParsedObject,
        is_input: bool = False,
    ) -> None:
        class_parents = (
            "(DataClassJsonMixin)" if not obj.parents else f'({", ".join(obj.parents)})'
        )

        buffer.write("@dataclass(frozen=True)")
        with buffer.write_block(f"class {obj.name}{class_parents}:"):
            # render child objects
            children_names = set()
            for child_object in obj.children:
                if child_object.name not in children_names:
                    self.__render_object(parsed_query, buffer, child_object, is_input)
                children_names.add(child_object.name)

            # render fields
            fields = obj.fields
            if is_input:
                fields = self.__sort_fields(parsed_query, obj.fields)

            for field in fields:
                self.__render_field(parsed_query, buffer, field, is_input)

            # pass if not children or fields
            if not (obj.children or obj.fields):
                buffer.write("pass")

        buffer.write("")

    def __render_fragment(
        self, parsed_query: ParsedQuery, buffer: CodeChunk, obj: ParsedObject
    ) -> None:
        class_parents = (
            "(DataClassJsonMixin)" if not obj.parents else f'({", ".join(obj.parents)})'
        )

        buffer.write("@dataclass(frozen=True)")
        with buffer.write_block(f"class {obj.name}{class_parents}:"):

            # render child objects
            children_names = set()
            for child_object in obj.children:
                if child_object.name not in children_names:
                    self.__render_object(parsed_query, buffer, child_object)
                children_names.add(child_object.name)

            # render fields
            for field in obj.fields:
                self.__render_field(parsed_query, buffer, field)

        buffer.write("")

    def __render_operation(
        self,
        parsed_query: ParsedQuery,
        buffer: CodeChunk,
        parsed_op: ParsedOperation,
        config_importpath: Optional[str],
    ) -> None:
        buffer.write("# fmt: off")
        if len(parsed_query.used_fragments):
            queries = [
                f"{fragment_name}Query"
                for fragment_name in sorted(set(parsed_query.used_fragments))
            ]
            buffer.write(f'QUERY: List[str] = {" + ".join(queries)} + ["""')
        else:
            buffer.write('QUERY: List[str] = ["""')
        buffer.write(parsed_query.query)
        buffer.write('"""')
        buffer.write("]")
        buffer.write("")
        buffer.write("")
        with buffer.write_block(f"class {parsed_op.name}:"):
            # Render children
            for child_object in parsed_op.children:
                self.__render_object(parsed_query, buffer, child_object)

            # Execution functions
            if parsed_op.variables:
                vars_args = ", " + ", ".join(
                    [
                        self.__render_variable_definition(var)
                        for var in parsed_op.variables
                    ]
                )
                variables_dict = (
                    "{"
                    + ", ".join(
                        f'"{var.name}": {var.name}' for var in parsed_op.variables
                    )
                    + "}"
                )
            else:
                vars_args = ""
                variables_dict = "{}"

            assert len(parsed_op.children) == 1
            child = parsed_op.children[0]
            assert len(child.fields) == 1
            query = child.fields[0]
            query_name = query.name
            query_result_type = f"{query.type}"
            if query_result_type in DEFAULT_MAPPING.keys():
                query_result_type = DEFAULT_MAPPING.get(
                    query_result_type, query_result_type
                )
            elif query_result_type in self.custom_scalars.keys():
                query_result_type = self.custom_scalars.get(
                    query_result_type, query_result_type
                ).type.__name__
            else:
                query_result_type = f"{parsed_op.name}Data.{query_result_type}"
            if query.nullable:
                query_result_type = f"Optional[{query_result_type}]"
            if query.is_list:
                query_result_type = f"List[{query_result_type}]"
            if parsed_op.type in ["query", "mutation"]:
                self.__write_execute_method(
                    buffer,
                    vars_args,
                    query_result_type,
                    variables_dict,
                    parsed_op.name,
                    query_name,
                    config_importpath,
                )
                self.__write_async_execute_method(
                    buffer,
                    vars_args,
                    query_result_type,
                    variables_dict,
                    parsed_op.name,
                    query_name,
                    config_importpath,
                )
            else:
                self.__write_subscribe_method(
                    buffer,
                    vars_args,
                    query_result_type,
                    variables_dict,
                    parsed_op.name,
                    query_name,
                    config_importpath,
                )
                self.__write_async_subscribe_method(
                    buffer,
                    vars_args,
                    query_result_type,
                    variables_dict,
                    parsed_op.name,
                    query_name,
                    config_importpath,
                )

    def __render_customer_scalars_imports(
        self, buffer: CodeChunk, config_importpath: Optional[str]
    ) -> None:
        if not config_importpath:
            return
        scalar_types = set()
        for _, custom_scalar in self.custom_scalars.items():
            if custom_scalar.type.__module__ != "builtins":
                scalar_types.add(custom_scalar.type.__name__)
        types_import_line = ", " + ", ".join(scalar_types) if scalar_types else ""
        buffer.write(
            f"from {config_importpath} import custom_scalars{types_import_line}"
        )

    @staticmethod
    def __write_execute_method(
        buffer: CodeChunk,
        vars_args: str,
        query_result_type: str,
        variables_dict: str,
        operation_name: str,
        query_name: str,
        config_importpath: Optional[str],
    ) -> None:
        buffer.write("# fmt: off")
        buffer.write("@classmethod")
        with buffer.write_block(
            f"def execute(cls, client: Client{vars_args})" f" -> {query_result_type}:"
        ):
            buffer.write(f"variables: Dict[str, Any] = {variables_dict}")
            scalars = ", custom_scalars" if config_importpath else ""
            buffer.write(f"new_variables = encode_variables(variables{scalars})")
            buffer.write("response_text = client.execute(")
            buffer.write('    gql("".join(set(QUERY))), variable_values=new_variables')
            buffer.write(")")
            buffer.write(f"res = cls.{operation_name}Data.from_dict(response_text)")
            buffer.write(f"return res.{query_name}")
        buffer.write("")

    @staticmethod
    def __write_async_execute_method(
        buffer: CodeChunk,
        vars_args: str,
        query_result_type: str,
        variables_dict: str,
        operation_name: str,
        query_name: str,
        config_importpath: Optional[str],
    ) -> None:
        buffer.write("# fmt: off")
        buffer.write("@classmethod")
        with buffer.write_block(
            f"async def execute_async(cls, client: Client{vars_args})"
            f" -> {query_result_type}:"
        ):
            buffer.write(f"variables: Dict[str, Any] = {variables_dict}")
            scalars = ", custom_scalars" if config_importpath else ""
            buffer.write(f"new_variables = encode_variables(variables{scalars})")
            buffer.write("response_text = await client.execute_async(")
            buffer.write('    gql("".join(set(QUERY))), variable_values=new_variables')
            buffer.write(")")
            buffer.write(f"res = cls.{operation_name}Data.from_dict(response_text)")
            buffer.write(f"return res.{query_name}")
        buffer.write("")

    @staticmethod
    def __write_subscribe_method(
        buffer: CodeChunk,
        vars_args: str,
        query_result_type: str,
        variables_dict: str,
        operation_name: str,
        query_name: str,
        config_importpath: Optional[str],
    ) -> None:
        buffer.write("# fmt: off")
        buffer.write("@classmethod")
        with buffer.write_block(
            f"def subscribe(cls, client: Client{vars_args})"
            f" -> Generator[{query_result_type}, None, None]:"
        ):
            buffer.write(f"variables: Dict[str, Any] = {variables_dict}")
            scalars = ", custom_scalars" if config_importpath else ""
            buffer.write(f"new_variables = encode_variables(variables{scalars})")
            buffer.write("subscription = client.subscribe(")
            buffer.write('    gql("".join(set(QUERY))), variable_values=new_variables')
            buffer.write(")")
            with buffer.write_block("for response_text in subscription:"):
                buffer.write(f"res = cls.{operation_name}Data.from_dict(response_text)")
                buffer.write(f"yield res.{query_name}")
        buffer.write("")

    @staticmethod
    def __write_async_subscribe_method(
        buffer: CodeChunk,
        vars_args: str,
        query_result_type: str,
        variables_dict: str,
        operation_name: str,
        query_name: str,
        config_importpath: Optional[str],
    ) -> None:
        buffer.write("# fmt: off")
        buffer.write("@classmethod")
        with buffer.write_block(
            f"async def subscribe_async(cls, client: Client{vars_args})"
            f" -> AsyncGenerator[{query_result_type}, None]:"
        ):
            buffer.write(f"variables: Dict[str, Any] = {variables_dict}")
            scalars = ", custom_scalars" if config_importpath else ""
            buffer.write(f"new_variables = encode_variables(variables{scalars})")
            buffer.write("subscription = client.subscribe_async(")
            buffer.write('    gql("".join(set(QUERY))), variable_values=new_variables')
            buffer.write(")")
            with buffer.write_block("async for response_text in subscription:"):
                buffer.write(f"res = cls.{operation_name}Data.from_dict(response_text)")
                buffer.write(f"yield res.{query_name}")
        buffer.write("")

    @staticmethod
    def __sort_fields(
        parsed_query: ParsedQuery, fields: List[ParsedField]
    ) -> List[ParsedField]:
        def sort_key(field) -> int:
            if field.nullable:
                return 2
            return 0

        return sorted(fields, key=sort_key)

    def __render_variable_definition(self, var: ParsedVariableDefinition):
        var_type = DEFAULT_MAPPING.get(var.type, var.type)

        if var.type in self.custom_scalars.keys():
            var_type = self.custom_scalars[var.type].type.__name__

        if var.is_list:
            return f"{var.name}: List[{var_type}] = []"

        if not var.nullable:
            return f"{var.name}: {var_type}"

        return f'{var.name}: Optional[{var_type}] = {var.default_value or "None"}'

    def __render_field(
        self,
        parsed_query: ParsedQuery,
        buffer: CodeChunk,
        field: ParsedField,
        is_input: bool = False,
    ) -> None:
        enum_names = [e.name for e in parsed_query.enums + parsed_query.internal_enums]
        is_enum = field.type in enum_names
        suffix = ""
        field_type = DEFAULT_MAPPING.get(field.type, field.type)
        if field.is_list:
            field_type = f"List[{field_type}]"

        if is_enum:
            suffix = f" = _field(metadata=enum_field_metadata({field_type}))"

        if field_type in self.custom_scalars.keys():
            if (
                self.custom_scalars[field_type].encoder
                or self.custom_scalars[field_type].decoder
                or self.custom_scalars[field_type].mm_field
            ):
                suffix = (
                    " = _field(metadata=config("
                    f'encoder=custom_scalars["{field_type}"].encoder, '
                    f'decoder=custom_scalars["{field_type}"].decoder, '
                    f'mm_field=custom_scalars["{field_type}"].mm_field))'
                )
            field_type = self.custom_scalars[field_type].type.__name__

        if field.nullable:
            if is_input:
                suffix = f" = {field.default_value}"
            buffer.write(f"{field.name}: Optional[{field_type}]{suffix}")
        else:
            buffer.write(f"{field.name}: {field_type}{suffix}")

    @staticmethod
    def __write_file_header(buffer: CodeChunk) -> None:
        buffer.write("#!/usr/bin/env python3")
        buffer.write("# @" + "generated AUTOGENERATED file. Do not Change!")
        buffer.write("")
