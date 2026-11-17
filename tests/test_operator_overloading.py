import subprocess
import sys
import pytest
from conftest import velo_exe

def test_operator_overloading_execution():
    result = subprocess.run(
        [sys.executable, "velo.py", "run", "examples/25_operator_overloading.vl"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Error: {result.stderr}"
    output = result.stdout
    assert "=== Testing Operator Overloading for Game Math ===" in output
    assert "next_pos: x=11.00, y=18.50" in output
    assert "scaled_pos: x=20.00, y=40.00" in output
    assert "diff: x=1.00, y=-1.50" in output
    assert "neg_vel: x=-2.00, y=3.00" in output
    assert "pos == v_copy: true" in output
    assert "pos != vel: true" in output
    assert "after +=: x=5.00, y=10.00" in output
    assert "after *=: x=10.00, y=20.00" in output
    assert "=== Operator Overloading Verification Complete ===" in output

def test_operator_overloading_emit_c():
    result = subprocess.run(
        [sys.executable, "velo.py", "emit-c", "examples/25_operator_overloading.vl"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Error: {result.stderr}"
    c_code = result.stdout
    assert "velo_op_add_Vector2_Vector2" in c_code
    assert "velo_op_sub_Vector2_Vector2" in c_code
    assert "velo_op_mul_Vector2_f32" in c_code
    assert "velo_op_mul_f32_Vector2" in c_code
    assert "velo_op_neg_Vector2" in c_code
    assert "velo_op_eq_Vector2_Vector2" in c_code
    assert "velo_op_ne_Vector2_Vector2" in c_code

def test_operator_overloading_native():
    import os
    exe = str(velo_exe())
    if not os.path.exists(exe):
        pytest.skip("bin/velo.exe not built")
    result = subprocess.run([exe, "run", "examples/25_operator_overloading.vl"], capture_output=True, text=True)
    assert result.returncode == 0, f"Error: {result.stderr}"
    assert "=== Operator Overloading Verification Complete ===" in result.stdout
    assert "next_pos: x=11.00, y=18.50" in result.stdout
    assert "after *=: x=10.00, y=20.00" in result.stdout
