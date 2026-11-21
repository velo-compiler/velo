"""
Phase 77 / Task 77.3: Static Contracts and Generic Constraints (`pact`).

Tests the static contract system:
- `pact Name { act method(self: @Self, ...) -> Ret }` declaration
- Generic type parameter constraints: `[T: PactName]`
- Multi-parameter generic constraints: `[T: PactName, U]`
- Compile-time static dispatch via monomorphization (zero vtables, zero runtime overhead)
- Clear compiler diagnostics when a concrete type fails to satisfy a pact:
  `Type '<ConcreteType>' does not satisfy pact '<PactName>': missing method '<method>'`
"""

import subprocess
import pytest
from conftest import velo_exe, REPO_ROOT

pytestmark = pytest.mark.fast

VELO_EXE = velo_exe()


def run_velo_source(tmp_path, code: str):
    src_file = tmp_path / "test_prog.vl"
    src_file.write_text(code, encoding="utf-8")
    res = subprocess.run(
        [str(VELO_EXE), "run", str(src_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res


def build_velo_source(tmp_path, code: str):
    src_file = tmp_path / "test_prog.vl"
    src_file.write_text(code, encoding="utf-8")
    bin_file = tmp_path / "test_prog.exe"
    res = subprocess.run(
        [str(VELO_EXE), "build", str(src_file), "-o", str(bin_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res


def test_basic_pact_declaration_and_call(tmp_path):
    code = """
pact Printable {
    act print(self: @Self) -> void
}

data User {
    name: string
}

act print(u: @User) {
    io.println(u.name)
}

act display[T: Printable](item: @T) {
    item.print()
}

act main() -> i32 {
    mut u = User{ name: "Alice" }
    display(@u)
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "Alice" in res.stdout


def test_multi_method_pact(tmp_path):
    code = """
use std.io

pact Measurable {
    act area(self: @Self) -> i32
    act perimeter(self: @Self) -> i32
}

data Rectangle {
    width: i32
    height: i32
}

act area(r: @Rectangle) -> i32 {
    return r.width * r.height
}

act perimeter(r: @Rectangle) -> i32 {
    return 2 * (r.width + r.height)
}

act inspect_shape[S: Measurable](s: @S) {
    let a = s.area()
    let p = s.perimeter()
    io.println("area={a}, perim={p}")
}

act main() -> i32 {
    mut rect = Rectangle{ width: 5, height: 10 }
    inspect_shape(@rect)
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "area=50, perim=30" in res.stdout


def test_multi_type_params_with_pact(tmp_path):
    code = """
use std.io

pact Greeter {
    act greet(self: @Self) -> void
}

data Robot {
    model: string
}

act greet(r: @Robot) {
    io.println("Beep Boop: {r.model}")
}

act pair_inspect[T: Greeter, U](item: @T, code: U) {
    item.greet()
    io.println("Code: {code}")
}

act main() -> i32 {
    mut bot = Robot{ model: "RX-78" }
    pair_inspect(@bot, 42)
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "Beep Boop: RX-78" in res.stdout
    assert "Code: 42" in res.stdout


def test_pact_missing_method_compile_error(tmp_path):
    code = """
pact Printable {
    act print(self: @Self) -> void
}

data NonPrintable {
    val: i32
}

act display[T: Printable](item: @T) {
    item.print()
}

act main() -> i32 {
    mut x = NonPrintable{ val: 42 }
    display(@x)
    return 0
}
"""
    res = build_velo_source(tmp_path, code)
    assert res.returncode != 0
    combined_output = res.stdout + res.stderr
    assert "Type 'NonPrintable' does not satisfy pact 'Printable': missing method 'print'" in combined_output


def test_unknown_pact_compile_error(tmp_path):
    code = """
data Widget {
    id: i32
}

act show[T: NonExistentPact](item: @T) {
}

act main() -> i32 {
    mut w = Widget{ id: 1 }
    show(@w)
    return 0
}
"""
    res = build_velo_source(tmp_path, code)
    assert res.returncode != 0
    combined_output = res.stdout + res.stderr
    assert "Unknown pact 'NonExistentPact'" in combined_output


def test_pact_method_with_parameters_and_return_value(tmp_path):
    code = """
pact Serializer {
    act serialize_field(self: @Self, prefix: string, code: i32) -> string
}

data Payload {
    tag: string
}

act serialize_field(p: @Payload, prefix: string, code: i32) -> string {
    return "{prefix}:{p.tag}:{code}"
}

act dump[T: Serializer](item: @T) -> string {
    return item.serialize_field("ITEM", 999)
}

act main() -> i32 {
    mut p = Payload{ tag: "SENSOR" }
    let s = dump(@p)
    io.println(s)
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "ITEM:SENSOR:999" in res.stdout


def test_pact_satisfied_by_value_receiver(tmp_path):
    code = """
pact Numeric {
    act to_number(self: Self) -> i32
}

data ValueHolder {
    num: i32
}

act to_number(vh: ValueHolder) -> i32 {
    return vh.num * 2
}

act extract[T: Numeric](item: T) -> i32 {
    return item.to_number()
}

act main() -> i32 {
    mut v = ValueHolder{ num: 21 }
    let res = extract(v)
    io.println("res={res}")
    return 0
}
"""
    res = run_velo_source(tmp_path, code)
    assert res.returncode == 0, f"Error: {res.stderr}\n{res.stdout}"
    assert "res=42" in res.stdout

