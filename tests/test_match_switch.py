import subprocess
import sys
from pathlib import Path

def test_match_multi_value_and_else(tmp_path):
    source = tmp_path / "test_match.vl"
    source.write_text("""
use sys.io

act classify(val: i32) -> string {
    match val {
        1 => {
            return "one"
        }
        2, 3 => {
            return "two_or_three"
        }
        4, 5, 6 => {
            return "four_to_six"
        }
        else => {
            return "other"
        }
    }
}

act main() -> i32 {
    let r1 = classify(1)
    let r2 = classify(2)
    let r3 = classify(3)
    let r5 = classify(5)
    let r9 = classify(9)
    io.println("r1={r1}, r2={r2}, r3={r3}, r5={r5}, r9={r9}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "r1=one, r2=two_or_three, r3=two_or_three, r5=four_to_six, r9=other" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "r1=one, r2=two_or_three, r3=two_or_three, r5=four_to_six, r9=other" in res_sh.stdout


def test_switch_c_style(tmp_path):
    source = tmp_path / "test_switch.vl"
    source.write_text("""
use sys.io

act get_speed(gear: i32) -> i32 {
    switch gear {
        case 1: {
            return 15
        }
        case 2: {
            return 30
        }
        case 3, 4: {
            return 65
        }
        default: {
            return 0
        }
    }
}

act main() -> i32 {
    let g1 = get_speed(1)
    let g3 = get_speed(3)
    let g4 = get_speed(4)
    let g9 = get_speed(9)
    io.println("g1={g1}, g3={g3}, g4={g4}, g9={g9}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "g1=15, g3=65, g4=65, g9=0" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "g1=15, g3=65, g4=65, g9=0" in res_sh.stdout


def test_match_single_statement_and_wildcard(tmp_path):
    source = tmp_path / "test_wildcard.vl"
    source.write_text("""
use sys.io

act main() -> i32 {
    mut score: i32 = 0
    loop i in 0..6 {
        match i {
            0 => score += 1
            1, 2 => score += 10
            3 => score += 100
            _ => score += 1000
        }
    }
    io.println("final_score={score}")
    return 0
}
""", encoding="utf-8")

    # Python stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    # i=0: +1, i=1: +10, i=2: +10, i=3: +100, i=4: +1000, i=5: +1000 => 2121
    assert "final_score=2121" in res_py.stdout

    # Self-hosted stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(source)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "final_score=2121" in res_sh.stdout


def test_example_19_execution():
    example_path = Path("examples/19_match_switch.vl")
    assert example_path.exists()

    # Stage 1
    res_py = subprocess.run([sys.executable, "velo.py", "run", str(example_path)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_py.returncode == 0
    assert "Status 200: OK" in res_py.stdout
    assert "Score 10: A+" in res_py.stdout
    assert "Total points across iterations 0..4 = 50" in res_py.stdout
    assert "Action for key 2 = attack" in res_py.stdout

    # Stage 2
    res_sh = subprocess.run(["bin/velo.exe", "run", str(example_path)], capture_output=True, text=True, encoding="utf-8", cwd=Path.cwd())
    assert res_sh.returncode == 0
    assert "Status 200: OK" in res_sh.stdout
    assert "Score 10: A+" in res_sh.stdout
    assert "Total points across iterations 0..4 = 50" in res_sh.stdout
    assert "Action for key 2 = attack" in res_sh.stdout
