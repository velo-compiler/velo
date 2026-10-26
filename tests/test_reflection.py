import json
import os
import subprocess
import sys
import pytest

def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)

def _run_stage1(args):
    return subprocess.run(
        [sys.executable, "velo.py"] + args,
        capture_output=True,
        text=True
    )

def _run_stage2(args):
    if not os.path.exists("bin/velo.exe"):
        pytest.skip("bin/velo.exe not built; skipping native stage 2 test")
    return subprocess.run(
        ["bin/velo.exe"] + args,
        capture_output=True,
        text=True
    )

POSITIVE_REFLECTION_SRC = """use sys.io

data Point {
    x: f32
    y: f32
}

data Empty {
}

data Person {
    name: string
    age: i32
    active: bool
}

act inspect_struct[T](target: @T) {
    let count = field_count(T)
    assert(count == 2, "Point has 2 fields in generic inspector")
    assert(field_name(T, 0) == "x", "Field 0 is x")
    assert(field_name(T, 1) == "y", "Field 1 is y")
    assert(field_type(T, 0) == "f32", "Field 0 type is f32")
    assert(field_type(T, 1) == "f32", "Field 1 type is f32")
}

act main() -> i32 {
    // 1. Direct compile-time constants
    assert(field_count(Point) == 2, "field_count(Point) == 2")
    assert(field_name(Point, 0) == "x", "field_name(Point, 0) == x")
    assert(field_name(Point, 1) == "y", "field_name(Point, 1) == y")
    assert(field_type(Point, 0) == "f32", "field_type(Point, 0) == f32")
    assert(field_type(Point, 1) == "f32", "field_type(Point, 1) == f32")

    // 2. Pointer syntax reflection
    assert(field_count(@Point) == 2, "field_count(@Point) == 2")

    // 3. Empty struct reflection
    assert(field_count(Empty) == 0, "field_count(Empty) == 0")

    // 4. Multi-field struct and dynamic indexing loop
    assert(field_count(Person) == 3, "field_count(Person) == 3")
    mut i: i32 = 0
    loop i < field_count(Person) {
        let fn = field_name(Person, i)
        let ft = field_type(Person, i)
        if i == 0 {
            assert(fn == "name" and ft == "string", "Person[0] == name: string")
        } else if i == 1 {
            assert(fn == "age" and ft == "i32", "Person[1] == age: i32")
        } else if i == 2 {
            assert(fn == "active" and ft == "bool", "Person[2] == active: bool")
        }
        i += 1
    }

    // 5. Generic inspection
    mut pt = Point{ x: 1.0, y: 2.0 }
    inspect_struct[Point](@pt)

    io.println("REFLECTION_TEST_SUCCESS")
    return 0
}
"""

def test_reflection_positive_execution(tmp_path):
    src = _write(tmp_path, "reflect_pos.vl", POSITIVE_REFLECTION_SRC)

    p1 = _run_stage1(["run", src])
    assert p1.returncode == 0, f"Stage 1 failed:\n{p1.stderr}\n{p1.stdout}"
    assert "REFLECTION_TEST_SUCCESS" in p1.stdout

    p2 = _run_stage2(["run", src])
    assert p2.returncode == 0, f"Stage 2 failed:\n{p2.stderr}\n{p2.stdout}"
    assert "REFLECTION_TEST_SUCCESS" in p2.stdout

NEGATIVE_CASES = [
    (
        "field_count_arity",
        "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let c = field_count(Point, 1) }",
        "field_count expects exactly 1 argument: (Type)"
    ),
    (
        "field_name_arity",
        "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let n = field_name(Point) }",
        "field_name expects exactly 2 arguments: (Type, index)"
    ),
    (
        "field_type_arity",
        "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let t = field_type(Point) }",
        "field_type expects exactly 2 arguments: (Type, index)"
    ),
    (
        "first_arg_expr",
        "use sys.io\nact main() { let c = field_count(123) }",
        "reflection intrinsic expects a struct type as first argument"
    ),
    (
        "first_arg_primitive",
        "use sys.io\nact main() { let c = field_count(i32) }",
        "'i32' is not a struct"
    ),
    (
        "unknown_struct",
        "use sys.io\nact main() { let c = field_count(NonExistent) }",
        "unknown struct 'NonExistent'"
    ),
    (
        "index_non_int",
        'use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let n = field_name(Point, "zero") }',
        "field index must be an integer (got string)"
    ),
    (
        "index_oob_positive",
        "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let n = field_name(Point, 5) }",
        "field index out of bounds: 5 (struct 'Point' has 2 fields)"
    ),
    (
        "index_oob_negative",
        "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let t = field_type(Point, -1) }",
        "field index out of bounds: -1 (struct 'Point' has 2 fields)"
    ),
    (
        "bare_field_count",
        "use sys.io\nact main() { let x = field_count }",
        "reflection intrinsic 'field_count' must be called with parentheses: field_count(...)"
    ),
    (
        "bare_field_name",
        "use sys.io\nact main() { let x = field_name }",
        "reflection intrinsic 'field_name' must be called with parentheses: field_name(...)"
    ),
    (
        "bare_field_type",
        "use sys.io\nact main() { let x = field_type }",
        "reflection intrinsic 'field_type' must be called with parentheses: field_type(...)"
    ),
]

@pytest.mark.parametrize("name,code,expected_error", NEGATIVE_CASES)
def test_reflection_negative_diagnostics_parity(tmp_path, name, code, expected_error):
    src = _write(tmp_path, f"{name}.vl", code)

    p1 = _run_stage1(["check", src])
    assert p1.returncode != 0, f"Stage 1 unexpectedly succeeded for {name}"
    s1_out = p1.stdout + p1.stderr
    assert expected_error in s1_out, f"Stage 1 missing expected error: '{expected_error}' in:\n{s1_out}"

    p2 = _run_stage2(["check", src])
    assert p2.returncode != 0, f"Stage 2 unexpectedly succeeded for {name}"
    s2_out = p2.stdout + p2.stderr
    assert expected_error in s2_out, f"Stage 2 missing expected error: '{expected_error}' in:\n{s2_out}"

def test_reflection_json_diagnostics(tmp_path):
    code = "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let n = field_name(Point, 10) }"
    src = _write(tmp_path, "reflect_json.vl", code)

    p1 = _run_stage1(["check", "--json", src])
    assert p1.returncode != 0
    data1 = json.loads(p1.stdout)
    assert "diagnostics" in data1
    assert len(data1["diagnostics"]) >= 1
    assert "field index out of bounds: 10" in data1["diagnostics"][0]["message"]

    p2 = _run_stage2(["check", "--json", src])
    assert p2.returncode != 0
    data2 = json.loads(p2.stdout)
    assert "diagnostics" in data2
    assert len(data2["diagnostics"]) >= 1
    assert "field index out of bounds: 10" in data2["diagnostics"][0]["message"]

def test_reflection_lsp_hover_and_completions(tmp_path):
    from pathlib import Path
    from velo.analysis import VeloAnalysis, _path_to_uri

    src_file = tmp_path / "reflect_lsp.vl"
    code = "use sys.io\ndata Point { x: f32, y: f32 }\nact main() { let c = field_count(Point) }"
    src_file.write_text(code, encoding="utf-8")
    uri = _path_to_uri(str(src_file))

    repo_root = Path(__file__).resolve().parent.parent
    analysis = VeloAnalysis(str(repo_root))
    analysis.open(uri, str(src_file), code, 1)

    hover = analysis.hover(uri, 2, 23)
    assert hover is not None
    assert "field_count" in hover["contents"]["value"]
    assert "builtin" in hover["contents"]["value"]

    comps = analysis.completions(uri, 2, 10)
    labels = [c["label"] for c in comps]
    assert "field_count" in labels
    assert "field_name" in labels
    assert "field_type" in labels
