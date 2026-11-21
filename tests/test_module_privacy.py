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
def test_view_act_accessible_across_modules():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "math_lib.vl"
        mod_file.write_text(
            'view act add(a: i32, b: i32) -> i32 { return a + b }\n'
            'view act multiply(a: i32, b: i32) -> i32 { return a * b }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "math_lib.vl"\n'
            'act main() {\n'
            '    assert(add(3, 4) == 7, "add failed")\n'
            '    assert(multiply(3, 4) == 12, "multiply failed")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"Expected success, got stderr: {res.stderr}\nstdout: {res.stdout}"


@pytest.mark.fast
def test_private_act_blocked_from_other_modules():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "math_lib.vl"
        mod_file.write_text(
            'view act add(a: i32, b: i32) -> i32 { return a + b }\n'
            'act internal_secret() -> i32 { return 42 }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "math_lib.vl"\n'
            'act main() {\n'
            '    let x = add(1, 2)\n'
            '    let y = internal_secret()\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["check", str(main_file)], cwd=td)
        assert res.returncode != 0
        combined = res.stdout + res.stderr
        assert "'internal_secret' is private to 'math_lib.vl' and cannot be accessed from 'main.vl'" in combined


@pytest.mark.fast
def test_private_act_accessible_within_defining_file():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "math_lib.vl"
        mod_file.write_text(
            'act internal_secret() -> i32 { return 42 }\n'
            'view act compute() -> i32 { return internal_secret() + 1 }\n',
            encoding="utf-8"
        )
        main_file = Path(td) / "main.vl"
        main_file.write_text(
            'use "math_lib.vl"\n'
            'act main() {\n'
            '    assert(compute() == 43, "compute failed")\n'
            '}\n',
            encoding="utf-8"
        )
        res = run_velo(["run", str(main_file)], cwd=td)
        assert res.returncode == 0, f"Expected success, got stderr: {res.stderr}\nstdout: {res.stdout}"


@pytest.mark.fast
def test_view_data_struct_and_privacy():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "types.vl"
        mod_file.write_text(
            'view data PublicPoint { x: i32, y: i32 }\n'
            'data PrivateConfig { secret: i32 }\n',
            encoding="utf-8"
        )
        main_ok = Path(td) / "main_ok.vl"
        main_ok.write_text(
            'use "types.vl"\n'
            'act main() {\n'
            '    let p = PublicPoint { x: 10, y: 20 }\n'
            '    assert(p.x == 10 and p.y == 20, "point mismatch")\n'
            '}\n',
            encoding="utf-8"
        )
        res_ok = run_velo(["run", str(main_ok)], cwd=td)
        assert res_ok.returncode == 0, f"Expected success, got: {res_ok.stderr}"

        main_err = Path(td) / "main_err.vl"
        main_err.write_text(
            'use "types.vl"\n'
            'act main() {\n'
            '    let c = PrivateConfig { secret: 99 }\n'
            '}\n',
            encoding="utf-8"
        )
        res_err = run_velo(["check", str(main_err)], cwd=td)
        assert res_err.returncode != 0
        combined = res_err.stdout + res_err.stderr
        assert "'PrivateConfig' is private to 'types.vl' and cannot be accessed from 'main_err.vl'" in combined


@pytest.mark.fast
def test_view_kind_and_privacy():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "kinds.vl"
        mod_file.write_text(
            'view kind PublicColor { Red, Green, Blue }\n'
            'kind PrivateState { Active, Inactive }\n',
            encoding="utf-8"
        )
        main_ok = Path(td) / "main_ok.vl"
        main_ok.write_text(
            'use "kinds.vl"\n'
            'act is_red(c: PublicColor) -> bool {\n'
            '    on c {\n'
            '        .Red => { return true }\n'
            '        .Green, .Blue => { return false }\n'
            '    }\n'
            '}\n'
            'act main() {\n'
            '    let c = PublicColor.Red\n'
            '    assert(is_red(c), "expected red")\n'
            '}\n',
            encoding="utf-8"
        )
        res_ok = run_velo(["run", str(main_ok)], cwd=td)
        assert res_ok.returncode == 0, f"Expected success, got: {res_ok.stderr}"

        main_err = Path(td) / "main_err.vl"
        main_err.write_text(
            'use "kinds.vl"\n'
            'act main() {\n'
            '    let s = PrivateState.Active\n'
            '}\n',
            encoding="utf-8"
        )
        res_err = run_velo(["check", str(main_err)], cwd=td)
        assert res_err.returncode != 0
        combined = res_err.stdout + res_err.stderr
        assert "'PrivateState' is private to 'kinds.vl' and cannot be accessed from 'main_err.vl'" in combined


@pytest.mark.fast
def test_view_pact_and_privacy():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "contracts.vl"
        mod_file.write_text(
            'view pact PublicPact {\n'
            '    act val(self: @Self) -> i32\n'
            '}\n'
            'pact PrivatePact {\n'
            '    act secret(self: @Self) -> i32\n'
            '}\n',
            encoding="utf-8"
        )
        main_ok = Path(td) / "main_ok.vl"
        main_ok.write_text(
            'use "contracts.vl"\n'
            'data Item { v: i32 }\n'
            'act val(self: @Item) -> i32 { return self.v }\n'
            'act inspect_item[T: PublicPact](x: @T) -> i32 {\n'
            '    return x.val()\n'
            '}\n'
            'act main() {\n'
            '    let it = Item { v: 100 }\n'
            '    assert(inspect_item[Item](@it) == 100, "pact inspection failed")\n'
            '}\n',
            encoding="utf-8"
        )
        res_ok = run_velo(["run", str(main_ok)], cwd=td)
        assert res_ok.returncode == 0, f"Expected success, got: {res_ok.stderr}"

        main_err = Path(td) / "main_err.vl"
        main_err.write_text(
            'use "contracts.vl"\n'
            'data Item { v: i32 }\n'
            'act secret(self: @Item) -> i32 { return self.v }\n'
            'act inspect_item[T: PrivatePact](x: @T) -> i32 {\n'
            '    return x.secret()\n'
            '}\n'
            'act main() {\n'
            '    let it = Item { v: 100 }\n'
            '    inspect_item[Item](@it)\n'
            '}\n',
            encoding="utf-8"
        )
        res_err = run_velo(["check", str(main_err)], cwd=td)
        assert res_err.returncode != 0
        combined = res_err.stdout + res_err.stderr
        assert "'PrivatePact' is private to 'contracts.vl' and cannot be accessed from 'main_err.vl'" in combined


@pytest.mark.fast
def test_view_global_variable_and_privacy():
    with tempfile.TemporaryDirectory() as td:
        mod_file = Path(td) / "globals.vl"
        mod_file.write_text(
            'view let PUBLIC_MAGIC: i32 = 777\n'
            'let PRIVATE_MAGIC: i32 = 666\n',
            encoding="utf-8"
        )
        main_ok = Path(td) / "main_ok.vl"
        main_ok.write_text(
            'use "globals.vl"\n'
            'act main() {\n'
            '    assert(PUBLIC_MAGIC == 777, "magic failed")\n'
            '}\n',
            encoding="utf-8"
        )
        res_ok = run_velo(["run", str(main_ok)], cwd=td)
        assert res_ok.returncode == 0, f"Expected success, got: {res_ok.stderr}"

        main_err = Path(td) / "main_err.vl"
        main_err.write_text(
            'use "globals.vl"\n'
            'act main() {\n'
            '    let x = PRIVATE_MAGIC\n'
            '}\n',
            encoding="utf-8"
        )
        res_err = run_velo(["check", str(main_err)], cwd=td)
        assert res_err.returncode != 0
        combined = res_err.stdout + res_err.stderr
        assert "'PRIVATE_MAGIC' is private to 'globals.vl' and cannot be accessed from 'main_err.vl'" in combined


@pytest.mark.fast
def test_view_cannot_be_applied_to_use_or_test():
    with tempfile.TemporaryDirectory() as td:
        f_use = Path(td) / "bad_use.vl"
        f_use.write_text('view use "foo.vl"\nact main() {}\n', encoding="utf-8")
        res_use = run_velo(["check", str(f_use)], cwd=td)
        assert res_use.returncode != 0
        assert "'view' cannot be applied to 'use'" in (res_use.stdout + res_use.stderr)

        f_test = Path(td) / "bad_test.vl"
        f_test.write_text('view test "my test" {}\n', encoding="utf-8")
        res_test = run_velo(["check", str(f_test)], cwd=td)
        assert res_test.returncode != 0
        assert "'view' cannot be applied to 'test'" in (res_test.stdout + res_test.stderr)
