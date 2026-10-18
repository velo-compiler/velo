"""
API Documentation Generator for Velo modules (Stage 1).
"""
from pathlib import Path
from typing import List, Optional
from velo.lexer import Lexer
from velo.parser import Parser
from velo.ast_nodes import Program, DataDecl, FunctionDecl, ExternDecl

def extract_doc_comment(source_lines: List[str], target_line: int) -> str:
    """
    Extracts preceding doc comments (/// or /** */) for a declaration at target_line (1-indexed).
    """
    if target_line <= 1:
        return ""

    prev_idx = target_line - 2
    if prev_idx < 0:
        return ""

    # Check for block comment ending on previous line
    if "*/" in source_lines[prev_idx]:
        block_lines = []
        cur = prev_idx
        found_start = False
        while cur >= 0:
            line_str = source_lines[cur]
            block_lines.append(line_str)
            if "/**" in line_str:
                found_start = True
                break
            cur -= 1
        if found_start:
            block_lines.reverse()
            full_block = "\n".join(block_lines)
            start_pos = full_block.find("/**") + 3
            end_pos = full_block.rfind("*/")
            content = full_block[start_pos:end_pos]
            cleaned_lines = []
            for l in content.splitlines():
                stripped = l.strip()
                if stripped.startswith("*"):
                    stripped = stripped[1:].strip()
                if stripped:
                    cleaned_lines.append(stripped)
            return "\n> ".join(cleaned_lines)

    # Check single-line doc comments (/// or //)
    doc_lines = []
    cur = prev_idx
    while cur >= 0:
        stripped = source_lines[cur].strip()
        if stripped.startswith("///"):
            doc_lines.append(stripped[3:].strip())
        elif stripped.startswith("//"):
            doc_lines.append(stripped[2:].strip())
        else:
            break
        cur -= 1

    if doc_lines:
        doc_lines.reverse()
        return "\n> ".join(doc_lines)

    return ""

def generate_markdown_docs(source_path: str) -> str:
    path = Path(source_path).resolve()
    source_text = path.read_text(encoding="utf-8")
    source_lines = source_text.splitlines()

    lexer = Lexer(source_text, filename=str(path))
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    prog = parser.parse()

    output: List[str] = []
    output.append(f"# API Reference: `{path.name}`\n")

    # 1. Structs / Data types
    structs = [d for d in prog.declarations if isinstance(d, DataDecl)]
    if structs:
        output.append("## Data Structures\n")
        for s in structs:
            output.append(f"### `data {s.name}`\n")
            doc = extract_doc_comment(source_lines, s.line)
            if doc:
                output.append(f"> {doc}\n")
            output.append("| Field | Type |")
            output.append("| :--- | :--- |")
            for f in s.fields:
                output.append(f"| `{f.name}` | `{f.type_name}` |")
            output.append("")

    # 2. Functions
    functions = [d for d in prog.declarations if isinstance(d, FunctionDecl) and d.name != "main"]
    if functions:
        output.append("## Functions\n")
        for fn in functions:
            params_str = ", ".join(f"{p.name}: {p.type_name}" for p in fn.params)
            ret_str = fn.return_type if fn.return_type else "void"
            output.append(f"### `act {fn.name}({params_str}) -> {ret_str}`\n")
            doc = extract_doc_comment(source_lines, fn.line)
            if doc:
                output.append(f"> {doc}\n")

    # 3. Extern Declarations
    externs = [d for d in prog.declarations if isinstance(d, ExternDecl)]
    if externs:
        output.append("## External C Interfaces\n")
        for ext in externs:
            params_str = ", ".join(f"{p.name}: {p.type_name}" for p in ext.params)
            ret_str = ext.return_type if ext.return_type else "void"
            output.append(f"* `extern act {ext.name}({params_str}) -> {ret_str}`")
        output.append("")

    return "\n".join(output) + "\n"
