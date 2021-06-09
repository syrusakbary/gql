from gql.compiler.utils_codegen import CodeChunk

from .conftest import load_module


def test_codegen_write_simple_strings():
    gen = CodeChunk()
    gen.write("def sum(a, b):")
    gen.indent()
    gen.write("return a + b")

    code = str(gen)

    m = load_module(code)
    assert m.sum(2, 3) == 5


def test_codegen_write_template_strings_args():
    gen = CodeChunk()
    gen.write("def {0}(a, b):", "sum")
    gen.indent()
    gen.write("return a + b")

    code = str(gen)

    m = load_module(code)
    assert m.sum(2, 3) == 5


def test_codegen_write_template_strings_kwargs():
    gen = CodeChunk()
    gen.write("def {method}(a, b):", method="sum")
    gen.indent()
    gen.write("return a + b")

    code = str(gen)

    m = load_module(code)
    assert m.sum(2, 3) == 5


def test_codegen_block():
    gen = CodeChunk()
    gen.write("def sum(a, b):")
    with gen.block():
        gen.write("return a + b")

    code = str(gen)

    m = load_module(code)
    assert m.sum(2, 3) == 5


def test_codegen_write_block():
    gen = CodeChunk()
    with gen.write_block("def {name}(a, b):", name="sum"):
        gen.write("return a + b")

    code = str(gen)

    m = load_module(code)
    assert m.sum(2, 3) == 5


def test_codegen_write_lines():
    lines = ["@staticmethod", "def sum(a, b):" "    return a + b"]
    gen = CodeChunk()
    gen.write("class Math:")
    gen.indent()
    gen.write_lines(lines)

    code = str(gen)

    m = load_module(code)
    assert m.Math.sum(2, 3) == 5
