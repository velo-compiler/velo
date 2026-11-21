import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
from conftest import velo_exe

VELO_EXE = velo_exe()


def run_velo(args, cwd=None):
    res = subprocess.run(
        [str(VELO_EXE)] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res


@pytest.mark.fast
def test_module_aliasing_qualified_call():
    """`use "math.vl" :> m` allows calling `m.add()`."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "math.vl"
        mod_file.write_text(
            'view act add(a: i32, b: i32) -> i32 { return a + b }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "math.vl" :> m\n'
            'act main() {\n'
            '    let r = m.add(3, 4)\n'
            '    assert(r == 7, "add failed")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_module_aliasing_blocks_bare_call():
    """`use "math.vl" :> m` blocks calling `add()` bare."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "math.vl"
        mod_file.write_text(
            'view act add(a: i32, b: i32) -> i32 { return a + b }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "math.vl" :> m\n'
            'act main() {\n'
            '    let r = add(3, 4)\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode != 0
        combined = res.stdout + res.stderr
        assert "'add' is not imported into" in combined
        assert "use 'm.add'" in combined


@pytest.mark.fast
def test_selective_import_allowed_and_blocked():
    """`use "calc.vl" :> { add }` allows `add()` and blocks unlisted `sub()`."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "calc.vl"
        mod_file.write_text(
            'view act add(a: i32, b: i32) -> i32 { return a + b }\n'
            'view act sub(a: i32, b: i32) -> i32 { return a - b }\n',
            encoding="utf-8"
        )
        # 1. Allowed selective import
        main_file = Path(td) / "main_ok.vl"
        main_file.write_text(
            'use "calc.vl" :> { add }\n'
            'act main() {\n'
            '    assert(add(10, 5) == 15, "add ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # 2. Blocked unlisted function
        main_bad = Path(td) / "main_bad.vl"
        main_bad.write_text(
            'use "calc.vl" :> { add }\n'
            'act main() {\n'
            '    let r = sub(10, 5)\n'
            '}\n',
            encoding="utf-8"
        )
        res_bad = run_velo(["run", str(main_bad)], cwd=td)
        assert res_bad.returncode != 0
        combined = res_bad.stdout + res_bad.stderr
        assert "'sub' is not imported from 'calc.vl'" in combined


@pytest.mark.fast
def test_selective_import_with_renaming():
    """`use "calc.vl" :> { add :> calc_add }` renames `add` to `calc_add`."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "calc.vl"
        mod_file.write_text(
            'view act add(a: i32, b: i32) -> i32 { return a + b }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "calc.vl" :> { add :> calc_add }\n'
            'act main() {\n'
            '    assert(calc_add(20, 22) == 42, "renamed add ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Original name 'add' should not be imported
        main_bad = Path(td) / "main_bad.vl"
        main_bad.write_text(
            'use "calc.vl" :> { add :> calc_add }\n'
            'act main() {\n'
            '    let r = add(1, 2)\n'
            '}\n',
            encoding="utf-8"
        )
        res_bad = run_velo(["run", str(main_bad)], cwd=td)
        assert res_bad.returncode != 0


@pytest.mark.fast
def test_selective_import_struct():
    """`use "types.vl" :> { Point }` selectively imports struct `Point`."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "types.vl"
        mod_file.write_text(
            'view data Point { x: i32, y: i32 }\n'
            'view data Color { r: i32, g: i32, b: i32 }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "types.vl" :> { Point }\n'
            'act main() {\n'
            '    let p = Point{ x: 10, y: 20 }\n'
            '    assert(p.x == 10 and p.y == 20, "point ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Color is unlisted and blocked
        main_bad = Path(td) / "main_bad.vl"
        main_bad.write_text(
            'use "types.vl" :> { Point }\n'
            'act main() {\n'
            '    let c = Color{ r: 255, g: 0, b: 0 }\n'
            '}\n',
            encoding="utf-8"
        )
        res_bad = run_velo(["run", str(main_bad)], cwd=td)
        assert res_bad.returncode != 0
        combined = res_bad.stdout + res_bad.stderr
        assert "'Color' is not imported from 'types.vl'" in combined


@pytest.mark.fast
def test_selective_import_struct_with_rename():
    """`use "types.vl" :> { Point :> Coord }` renames `Point` to `Coord`."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "types.vl"
        mod_file.write_text(
            'view data Point { x: i32, y: i32 }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "types.vl" :> { Point :> Coord }\n'
            'act main() {\n'
            '    let c = Coord{ x: 5, y: 15 }\n'
            '    assert(c.x == 5 and c.y == 15, "coord ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_module_aliasing_global_variable():
    """`use "config.vl" :> cfg` allows accessing `cfg.MAX_SIZE`."""
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "config.vl"
        mod_file.write_text(
            'view let MAX_SIZE: i32 = 1024\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "config.vl" :> cfg\n'
            'act main() {\n'
            '    let limit = cfg.MAX_SIZE\n'
            '    assert(limit == 1024, "global ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

        # Bare access to MAX_SIZE should be blocked
        main_bad = Path(td) / "main_bad.vl"
        main_bad.write_text(
            'use "config.vl" :> cfg\n'
            'act main() {\n'
            '    let limit = MAX_SIZE\n'
            '}\n',
            encoding="utf-8"
        )
        res_bad = run_velo(["run", str(main_bad)], cwd=td)
        assert res_bad.returncode != 0
        combined = res_bad.stdout + res_bad.stderr
        assert "'MAX_SIZE' is not imported into" in combined


@pytest.mark.fast
def test_invalid_colon_gt_syntax_rejected():
    """Invalid token after `:>` is rejected with syntax error."""
    with tempfile.TemporaryDirectory() as td:
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "math.vl" :> 12345\n'
            'act main() {}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode != 0
        combined = res.stdout + res.stderr
        assert "Expected alias identifier or '{' after ':>'" in combined


@pytest.mark.fast
def test_multiple_module_aliases():
    """Multiple modules can be imported under distinct aliases."""
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "mod1.vl").write_text(
            'view act get_one() -> i32 { return 1 }\n',
            encoding="utf-8"
        )
        (Path(td) / "mod2.vl").write_text(
            'view act get_two() -> i32 { return 2 }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "mod1.vl" :> m1\n'
            'use "mod2.vl" :> m2\n'
            'act main() {\n'
            '    let a = m1.get_one()\n'
            '    let b = m2.get_two()\n'
            '    assert(a + b == 3, "multiple aliases ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_selective_import_multiple_renames():
    """Multiple items in selective import list can each be renamed."""
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "ops.vl").write_text(
            'view act op_add(a: i32, b: i32) -> i32 { return a + b }\n'
            'view act op_sub(a: i32, b: i32) -> i32 { return a - b }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "ops.vl" :> { op_add :> plus, op_sub :> minus }\n'
            'act main() {\n'
            '    assert(plus(10, 2) == 12, "plus ok")\n'
            '    assert(minus(10, 2) == 8, "minus ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


@pytest.mark.fast
def test_selective_import_struct_annotation_and_param():
    """Renamed struct type used in variable annotation and function parameter."""
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "types.vl").write_text(
            'view data Point { x: i32, y: i32 }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "types.vl" :> { Point :> Coord }\n'
            'act sum_coord(c: Coord) -> i32 {\n'
            '    return c.x + c.y\n'
            '}\n'
            'act main() {\n'
            '    let c: Coord = Coord{ x: 5, y: 15 }\n'
            '    assert(sum_coord(c) == 20, "coord annotation ok")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


