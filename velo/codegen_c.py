import re
from typing import List, Optional, Tuple, Dict, Any
from velo.ast_nodes import (
    Program, Decl, UseStmt, FunctionDecl, ExternDecl, Param, BlockStmt, DataDecl, Field, KindDecl, VariantDecl,
    Stmt, ExprStmt, ReturnStmt, BreakStmt, ContinueStmt, VarDeclStmt, AssignStmt, IfStmt, LoopStmt, ZoneStmt, DeferStmt,
    MatchCase, MatchStmt,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral, VariantExpr,
    Identifier, MemberAccess, IndexExpr, DerefExpr, StructLiteral, CastExpr, CallExpr, AddressOf, BinaryExpr, UnaryExpr, AnonFuncExpr,
    TypeAliasDecl
)
from velo.monomorphize import Monomorphizer, parse_act_type, mangle_act_type

TYPE_MAP = {
    "i8": "i8",
    "i16": "i16",
    "i32": "i32",
    "i64": "i64",
    "u8": "u8",
    "u16": "u16",
    "u32": "u32",
    "u64": "u64",
    "f32": "f32",
    "f64": "f64",
    "bool": "bool",
    "usize": "usize",
    "isize": "isize",
    "string": "const char*",
    "void": "void",
    # §4.1 passable allocator handle: @Allocator in Velo → VeloZoneArena* in C
    "Allocator": "VeloZoneArena",
    # §4.2 thread surface: @Thread → VeloThreadCtx*, @Mutex → void*
    "Thread": "VeloThreadCtx",
    "Mutex": "void",
}

class CCodeGenerator:
    def __init__(self):
        self.output: List[str] = []
        self.indent_level = 0
        self.struct_defs: Dict[str, Dict[str, str]] = {}
        self.struct_field_decls: Dict[str, List[Field]] = {}
        self.type_aliases: Dict[str, str] = {}
        self.kind_defs: Dict[str, KindDecl] = {}
        self.variant_to_kind: Dict[str, str] = {}
        self.current_scope_types: Dict[str, str] = {}
        self.current_function: Optional[FunctionDecl] = None
        self.defer_stack: List[List[Stmt]] = []
        self.zone_counter = 0
        self.match_counter = 0

    def _indent(self) -> str:
        return "    " * self.indent_level

    def _emit_line(self, line: str = ""):
        if line:
            self.output.append(f"{self._indent()}{line}\n")
        else:
            self.output.append("\n")

    def _map_type(self, type_str: Optional[str]) -> str:
        if not type_str or type_str == "void":
            return "void"
        
        parsed = parse_act_type(type_str)
        if parsed:
            prefix, params, ret = parsed
            if hasattr(self, 'used_act_types'):
                self.used_act_types.add((tuple(params), ret))
            mangled = mangle_act_type(params, ret)
            return mangled + ("*" * len(prefix))

        pointer_count = 0
        while type_str.startswith("@"):
            pointer_count += 1
            type_str = type_str[1:]

        # Belt-and-braces: resolve a primitive type alias that escaped Pass 0 canonicalization
        if type_str in self.type_aliases:
            type_str = self.type_aliases[type_str]

        base_c_type = TYPE_MAP.get(type_str, type_str)
        return base_c_type + ("*" * pointer_count)

    def generate(self, program: Program) -> str:
        program = Monomorphizer().monomorphize(program)

        self.output = []
        self.struct_defs = {}
        self.current_scope_types = {}
        self.global_types: Dict[str, str] = {}
        self.func_return_types: Dict[str, str] = {}
        self.defer_stack = []
        self.zone_counter = 0

        self.func_decls: Dict[str, FunctionDecl] = {}
        self.used_act_types: Set[Tuple[Tuple[str, ...], str]] = set()
        self.anon_funcs: List[Tuple[str, AnonFuncExpr]] = []
        self.anon_func_set: Set[int] = set()
        self.anon_expr_to_name: Dict[int, str] = {}

        # Collect function return types and declarations for type inference
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                self.func_decls[decl.name] = decl
                self.func_return_types[decl.name] = decl.return_type or "void"
            elif isinstance(decl, ExternDecl):
                self.func_return_types[decl.name] = decl.return_type or "void"

        # Pre-scan for all act types and anonymous functions
        def collect_types(t: Optional[str]):
            if not t: return
            parsed = parse_act_type(t)
            if parsed:
                _, p_params, p_ret = parsed
                self.used_act_types.add((tuple(p_params), p_ret))
                for p in p_params: collect_types(p)
                collect_types(p_ret)

        def scan_expr(e: Optional[Expr]):
            if not e: return
            if isinstance(e, AnonFuncExpr):
                eid = id(e)
                if eid not in self.anon_func_set:
                    self.anon_func_set.add(eid)
                    anon_name = f"_velo_anon_act_{len(self.anon_funcs)}"
                    self.anon_funcs.append((anon_name, e))
                    self.anon_expr_to_name[eid] = anon_name
                param_types = [p.type_name for p in e.params]
                self.used_act_types.add((tuple(param_types), e.return_type))
                for pt in param_types: collect_types(pt)
                collect_types(e.return_type)
                scan_stmt(e.body)
            elif isinstance(e, CastExpr):
                collect_types(e.target_type)
                scan_expr(e.expr)
            elif isinstance(e, BinaryExpr):
                scan_expr(e.left); scan_expr(e.right)
            elif isinstance(e, UnaryExpr):
                scan_expr(e.operand)
            elif isinstance(e, CallExpr):
                scan_expr(e.callee)
                for a in e.args: scan_expr(a)
            elif isinstance(e, MemberAccess):
                scan_expr(e.target)
            elif isinstance(e, IndexExpr):
                scan_expr(e.target); scan_expr(e.index)
            elif isinstance(e, AddressOf):
                scan_expr(e.operand)
            elif isinstance(e, DerefExpr):
                scan_expr(e.operand)
            elif isinstance(e, StructLiteral):
                for _, fv in e.field_inits: scan_expr(fv)
            elif isinstance(e, VariantExpr):
                for a in e.args: scan_expr(a)

        def scan_stmt(s: Optional[Stmt]):
            if not s: return
            if isinstance(s, VarDeclStmt):
                collect_types(s.type_name)
                scan_expr(s.value)
            elif isinstance(s, ExprStmt):
                scan_expr(s.expr)
            elif isinstance(s, ReturnStmt):
                scan_expr(s.value)
            elif isinstance(s, AssignStmt):
                scan_expr(s.target); scan_expr(s.value)
            elif isinstance(s, IfStmt):
                scan_expr(s.condition); scan_stmt(s.then_branch)
                if s.else_branch: scan_stmt(s.else_branch)
            elif isinstance(s, LoopStmt):
                if s.expr: scan_expr(s.expr)
                if s.start_expr: scan_expr(s.start_expr)
                if s.end_expr: scan_expr(s.end_expr)
                if s.step_expr: scan_expr(s.step_expr)
                scan_stmt(s.body)
            elif isinstance(s, BlockStmt):
                for st in s.statements: scan_stmt(st)
            elif isinstance(s, ZoneStmt):
                scan_stmt(s.body)
            elif isinstance(s, DeferStmt):
                scan_stmt(s.statement)
            elif isinstance(s, MatchStmt):
                scan_expr(s.expr)
                for c in s.cases:
                    for v in c.values: scan_expr(v)
                    scan_stmt(c.body)

        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                for p in decl.params: collect_types(p.type_name)
                collect_types(decl.return_type)
                scan_stmt(decl.body)
            elif isinstance(decl, ExternDecl):
                for p in decl.params: collect_types(p.type_name)
                collect_types(decl.return_type)
            elif isinstance(decl, DataDecl):
                for f in decl.fields: collect_types(f.type_name)
            elif isinstance(decl, KindDecl):
                for v in decl.variants:
                    collect_types(v.payload_type)
                    if v.fields:
                        for f in v.fields: collect_types(f.type_name)
            elif isinstance(decl, VarDeclStmt):
                collect_types(decl.type_name)
                scan_expr(decl.value)

        self._emit_line("/* Generated by Velo Stage 1 Compiler */")
        self._emit_line('#include "velo_runtime.h"')
        self._emit_line()

        # Collect kind declarations
        self.kind_defs = {}
        self.variant_to_kind = {}
        self.match_counter = 0
        for decl in program.declarations:
            if isinstance(decl, KindDecl):
                self.kind_defs[decl.name] = decl
                for v in decl.variants:
                    self.variant_to_kind[v.name] = decl.name

        # 1. Forward-declare all structs and kinds
        seen_structs = set()
        for decl in program.declarations:
            if isinstance(decl, DataDecl):
                if decl.name not in seen_structs:
                    self._emit_line(f"typedef struct {decl.name} {decl.name};")
                    self.struct_defs[decl.name] = {f.name: f.type_name for f in decl.fields}
                    self.struct_field_decls[decl.name] = decl.fields
                    seen_structs.add(decl.name)
            elif isinstance(decl, KindDecl):
                if decl.name not in seen_structs:
                    if self._is_tagged_union(decl):
                        self._emit_line(f"typedef struct {decl.name} {decl.name};")
                    else:
                        self._emit_line(f"typedef int32_t {decl.name};")
                    seen_structs.add(decl.name)

        self._emit_line()

        # 1. Register and emit type aliases (`aka EntityId = u64`)
        for decl in program.declarations:
            if isinstance(decl, TypeAliasDecl):
                if decl.name not in self.type_aliases:
                    self.type_aliases[decl.name] = decl.target_type
        alias_decls = [d for d in program.declarations if isinstance(d, TypeAliasDecl)]
        if alias_decls:
            self._emit_line("/* Type aliases */")
            for decl in alias_decls:
                self._emit_line(f"typedef {self._map_type(decl.target_type)} {decl.name};")
            self._emit_line()

        # 1.5 Emit function pointer typedefs
        if self.used_act_types:
            self._emit_line("/* Function pointer typedefs */")
            for params, ret in sorted(self.used_act_types, key=lambda x: mangle_act_type(list(x[0]), x[1])):
                mangled_name = mangle_act_type(list(params), ret)
                ret_c = self._map_type(ret)
                param_c = ", ".join(self._map_type(p) for p in params) if params else "void"
                self._emit_line(f"typedef {ret_c} (*{mangled_name})({param_c});")
            self._emit_line()

        # 2. Emit kind and struct definitions
        for decl in program.declarations:
            if isinstance(decl, KindDecl):
                self._emit_kind_definition(decl)

        emitted_structs = set()
        for decl in program.declarations:
            if isinstance(decl, DataDecl):
                if decl.name not in emitted_structs:
                    self._emit_struct_definition(decl)
                    emitted_structs.add(decl.name)

        # 3. Emit global constants and variables
        seen_globals = set()
        for decl in program.declarations:
            if isinstance(decl, VarDeclStmt):
                if decl.name not in seen_globals:
                    type_str = self._infer_or_map_type(decl.type_name, decl.value)
                    raw_velo_type = decl.type_name or self._infer_raw_velo_type(decl.value)
                    self.global_types[decl.name] = raw_velo_type
                    const_prefix = "" if decl.is_mut else "const "
                    if decl.value:
                        val_code = self._emit_expression(decl.value)
                        self._emit_line(f"{const_prefix}{type_str} {decl.name} = {val_code};")
                    else:
                        self._emit_line(f"{type_str} {decl.name};")
                    seen_globals.add(decl.name)

        self._emit_line()

        # 4. Emit extern function declarations

        seen_externs = set()
        for decl in program.declarations:
            if isinstance(decl, ExternDecl):
                if decl.name not in seen_externs:
                    ret_type = self._map_type(decl.return_type)
                    param_strs = [f"{self._map_type(p.type_name)} {p.name}" for p in decl.params]
                    params_joined = ", ".join(param_strs) if param_strs else "void"
                    self._emit_line(f"extern {ret_type} {decl.name}({params_joined});")
                    seen_externs.add(decl.name)

        self._emit_line()

        # 4. Emit function forward declarations
        seen_funcs = set()
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl) and decl.name != "main":
                if decl.name not in seen_funcs:
                    ret_type = self._map_type(decl.return_type)
                    param_strs = [f"{self._map_type(p.type_name)} {p.name}" for p in decl.params]
                    params_joined = ", ".join(param_strs) if param_strs else "void"
                    self._emit_line(f"{ret_type} {decl.name}({params_joined});")
                    seen_funcs.add(decl.name)

        # Emit anonymous function forward declarations
        for anon_name, anon_expr in self.anon_funcs:
            ret_type = self._map_type(anon_expr.return_type)
            param_strs = [f"{self._map_type(p.type_name)} {p.name}" for p in anon_expr.params]
            params_joined = ", ".join(param_strs) if param_strs else "void"
            self._emit_line(f"static {ret_type} {anon_name}({params_joined});")

        self._emit_line()

        # Emit anonymous function bodies
        for anon_name, anon_expr in self.anon_funcs:
            self._emit_anon_func_def(anon_name, anon_expr)

        # 5. Emit function bodies
        emitted_funcs = set()
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                if decl.name not in emitted_funcs:
                    self._emit_function(decl)
                    emitted_funcs.add(decl.name)

        return "".join(self.output)

    def _emit_anon_func_def(self, name: str, expr: AnonFuncExpr):
        ret_type_c = self._map_type(expr.return_type)
        param_strs = []
        for p in expr.params:
            ptype_c = self._map_type(p.type_name)
            param_strs.append(f"{ptype_c} {p.name}")
        params_c = ", ".join(param_strs) if param_strs else "void"
        self._emit_line(f"static {ret_type_c} {name}({params_c}) {{")
        self.indent_level += 1
        old_scope = self.current_scope_types.copy()
        for p in expr.params:
            self.current_scope_types[p.name] = p.type_name
        self._emit_block_body(expr.body.statements)
        self.current_scope_types = old_scope
        self.indent_level -= 1
        self._emit_line("}")
        self._emit_line()

    def _emit_struct_definition(self, decl: DataDecl):
        attrs = ""
        attr_parts = []
        if decl.align:
            attr_parts.append(f"aligned({decl.align})")
        if decl.packed:
            attr_parts.append("packed")
        if attr_parts:
            attrs = f"__attribute__(({', '.join(attr_parts)})) "
        self._emit_line(f"struct {attrs}{decl.name} {{")
        self.indent_level += 1
        for field in decl.fields:
            c_type = self._map_type(field.type_name)
            self._emit_line(f"{c_type} {field.name};")
        self.indent_level -= 1
        self._emit_line("};")
        self._emit_line()

    def _is_tagged_union(self, decl: KindDecl) -> bool:
        for v in decl.variants:
            if v.payload_type is not None or (v.fields is not None and len(v.fields) > 0):
                return True
        return False

    def _emit_kind_definition(self, decl: KindDecl):
        if not self._is_tagged_union(decl):
            self._emit_line("enum {")
            self.indent_level += 1
            for i, v in enumerate(decl.variants):
                if v.discriminant is not None:
                    self._emit_line(f"{decl.name}_{v.name} = {v.discriminant},")
                else:
                    self._emit_line(f"{decl.name}_{v.name} = {i},")
            self.indent_level -= 1
            self._emit_line("};")
            self._emit_line()
        else:
            self._emit_line("enum {")
            self.indent_level += 1
            for i, v in enumerate(decl.variants):
                if v.discriminant is not None:
                    self._emit_line(f"{decl.name}_{v.name} = {v.discriminant},")
                else:
                    self._emit_line(f"{decl.name}_{v.name} = {i},")
            self.indent_level -= 1
            self._emit_line("};")
            self._emit_line()

            for v in decl.variants:
                if v.fields and len(v.fields) > 0:
                    self._emit_line(f"typedef struct {decl.name}_{v.name}_Payload {{")
                    self.indent_level += 1
                    for f in v.fields:
                        c_type = self._map_type(f.type_name)
                        self._emit_line(f"{c_type} {f.name};")
                    self.indent_level -= 1
                    self._emit_line(f"}} {decl.name}_{v.name}_Payload;")
                    self._emit_line()

            self._emit_line(f"struct {decl.name} {{")
            self.indent_level += 1
            self._emit_line("int32_t kind;")
            has_any_payload = any(v.payload_type is not None or (v.fields and len(v.fields) > 0) for v in decl.variants)
            if has_any_payload:
                self._emit_line("union {")
                self.indent_level += 1
                for v in decl.variants:
                    if v.fields and len(v.fields) > 0:
                        self._emit_line(f"{decl.name}_{v.name}_Payload {v.name};")
                    elif v.payload_type is not None:
                        c_type = self._map_type(v.payload_type)
                        self._emit_line(f"{c_type} {v.name};")
                self.indent_level -= 1
                self._emit_line("} as;")
            self.indent_level -= 1
            self._emit_line("};")
            self._emit_line()

    def _emit_function(self, func: FunctionDecl):
        self.current_function = func
        is_main = (func.name == "main")
        self.current_scope_types = dict(self.global_types)
        self.defer_stack = [[]]

        for p in func.params:
            self.current_scope_types[p.name] = p.type_name
        
        if is_main:
            self._emit_line("int main(int argc, char** argv) {")
        else:
            ret_type = self._map_type(func.return_type)
            param_strs = [f"{self._map_type(p.type_name)} {p.name}" for p in func.params]
            params_joined = ", ".join(param_strs) if param_strs else "void"
            self._emit_line(f"{ret_type} {func.name}({params_joined}) {{")

        self.indent_level += 1

        self._emit_block_body(func.body.statements)

        if is_main:
            self._emit_line("return 0;")

        self.indent_level -= 1
        self._emit_line("}")
        self._emit_line()
        self.current_function = None

    def _emit_block_body(self, statements: List[Stmt]):
        returned = False
        for stmt in statements:
            self._emit_statement(stmt)
            if isinstance(stmt, ReturnStmt):
                returned = True
                break

        if not returned and self.defer_stack:
            defers = self.defer_stack.pop()
            for d in reversed(defers):
                self._emit_statement(d)
        elif self.defer_stack:
            self.defer_stack.pop()

    def _emit_statement(self, stmt: Stmt):
        if isinstance(stmt, DeferStmt):
            if self.defer_stack:
                self.defer_stack[-1].append(stmt.statement)

        elif isinstance(stmt, ExprStmt):
            expr_code = self._emit_expression(stmt.expr)
            self._emit_line(f"{expr_code};")

        elif isinstance(stmt, ReturnStmt):
            ret_val_code = None
            if stmt.value:
                ret_val_code = self._emit_expression(stmt.value)

            for frame in reversed(self.defer_stack):
                for d in reversed(frame):
                    temp_stack = self.defer_stack
                    self.defer_stack = []
                    self._emit_statement(d)
                    self.defer_stack = temp_stack

            if ret_val_code:
                self._emit_line(f"return {ret_val_code};")
            elif self.current_function and self.current_function.name == "main":
                self._emit_line("return 0;")
            else:
                self._emit_line("return;")

        elif isinstance(stmt, BreakStmt):
            self._emit_line("break;")

        elif isinstance(stmt, ContinueStmt):
            self._emit_line("continue;")

        elif isinstance(stmt, VarDeclStmt):
            type_str = self._infer_or_map_type(stmt.type_name, stmt.value)
            raw_velo_type = stmt.type_name or self._infer_raw_velo_type(stmt.value)
            self.current_scope_types[stmt.name] = raw_velo_type

            if type_str.endswith("*"):
                const_prefix = ""
            else:
                const_prefix = "" if stmt.is_mut else "const "

            if stmt.value:
                val_code = self._emit_expression(stmt.value)
                self._emit_line(f"{const_prefix}{type_str} {stmt.name} = {val_code};")
            else:
                self._emit_line(f"{type_str} {stmt.name};")

        elif isinstance(stmt, AssignStmt):
            target_code = self._emit_expression(stmt.target)
            val_code = self._emit_expression(stmt.value)
            self._emit_line(f"{target_code} {stmt.op} {val_code};")

        elif isinstance(stmt, IfStmt):
            self._emit_if(stmt)

        elif isinstance(stmt, LoopStmt):
            it = stmt.iterator or "it"
            self.current_scope_types[it] = "i64"
            if stmt.start_expr is None and stmt.end_expr is None:
                if stmt.expr is not None:
                    is_count = getattr(stmt, 'is_count', False)
                    if not is_count:
                        if isinstance(stmt.expr, IntLiteral):
                            is_count = True
                        elif isinstance(stmt.expr, Identifier) and self.current_scope_types.get(stmt.expr.name) in ("i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize", "isize"):
                            is_count = True
                        elif isinstance(stmt.expr, BinaryExpr) and stmt.expr.op in ('+', '-', '*', '/', '%'):
                            is_count = True
                        elif isinstance(stmt.expr, CallExpr) and isinstance(stmt.expr.callee, Identifier) and self.func_return_types.get(stmt.expr.callee.name) in ("i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize", "isize"):
                            is_count = True

                    expr_code = self._emit_expression(stmt.expr)
                    if is_count:
                        self._emit_line(f"for (i64 {it} = 0; {it} < ({expr_code}); ++{it}) {{")
                    else:
                        self._emit_line(f"for (i64 {it} = 0; ({expr_code}); ++{it}) {{")
                else:
                    self._emit_line(f"for (i64 {it} = 0; ; ++{it}) {{")
            else:
                start_code = self._emit_expression(stmt.start_expr)
                end_code = self._emit_expression(stmt.end_expr)
                is_reverse = False
                if isinstance(stmt.start_expr, IntLiteral) and isinstance(stmt.end_expr, IntLiteral):
                    if stmt.start_expr.value > stmt.end_expr.value:
                        is_reverse = True

                if stmt.step_expr is not None:
                    step_code = self._emit_expression(stmt.step_expr)
                    if isinstance(stmt.step_expr, IntLiteral) and stmt.step_expr.value < 0:
                        cmp_op = ">=" if stmt.is_inclusive else ">"
                        update_clause = f"{it} += ({step_code})"
                    elif is_reverse:
                        cmp_op = ">=" if stmt.is_inclusive else ">"
                        update_clause = f"{it} -= ({step_code})"
                    else:
                        cmp_op = "<=" if stmt.is_inclusive else "<"
                        update_clause = f"{it} += ({step_code})"
                else:
                    if is_reverse:
                        cmp_op = ">=" if stmt.is_inclusive else ">"
                        update_clause = f"--{it}"
                    else:
                        cmp_op = "<=" if stmt.is_inclusive else "<"
                        update_clause = f"++{it}"

                self._emit_line(f"for (i64 {it} = ({start_code}); {it} {cmp_op} ({end_code}); {update_clause}) {{")

            self.indent_level += 1
            self.defer_stack.append([])
            self._emit_block_body(stmt.body.statements)
            self.indent_level -= 1
            self._emit_line("}")

        elif isinstance(stmt, ZoneStmt):
            self.zone_counter += 1
            wm = f"_zone_wm_{self.zone_counter}"
            self._emit_line("{")
            self.indent_level += 1
            if stmt.size is not None:  # §4.1: private pool-backed arena scoped to this block
                prev = f"_zone_prev_{self.zone_counter}"
                size_code = self._emit_expression(stmt.size)
                self._emit_line(f"VeloZoneArena* {prev} = velo_zone_enter((size_t)({size_code}));")
            self._emit_line(f"size_t {wm} = velo_zone_push();")
            self.defer_stack.append([])
            self._emit_block_body(stmt.body.statements)
            self._emit_line(f"velo_zone_pop({wm});")
            if stmt.size is not None:
                self._emit_line(f"velo_zone_leave(_zone_prev_{self.zone_counter});")
            self.indent_level -= 1
            self._emit_line("}")

        elif isinstance(stmt, MatchStmt):
            subj_type = self._resolve_expr_type(stmt.expr)
            kdecl = self.kind_defs.get(subj_type)
            if kdecl and self._is_tagged_union(kdecl):
                if isinstance(stmt.expr, Identifier):
                    subj_var = stmt.expr.name
                else:
                    self.match_counter += 1
                    subj_var = f"_match_subj_{self.match_counter}"
                    self._emit_line(f"{subj_type} {subj_var} = {self._emit_expression(stmt.expr)};")
                self._emit_line(f"switch ({subj_var}.kind) {{")
                for c in stmt.cases:
                    if c.is_default:
                        self._emit_line("default: {")
                    else:
                        for v in c.values:
                            vname = v.variant_name if isinstance(v, VariantExpr) else self._emit_expression(v)
                            self._emit_line(f"case {subj_type}_{vname}:")
                        self._emit_line("{")
                    self.indent_level += 1
                    self.defer_stack.append([])
                    if not c.is_default and len(c.values) > 0 and isinstance(c.values[0], VariantExpr):
                        v_expr = c.values[0]
                        v_decl = next((vd for vd in kdecl.variants if vd.name == v_expr.variant_name), None)
                        if v_decl and v_expr.args:
                            if v_decl.fields:
                                for f_decl, arg in zip(v_decl.fields, v_expr.args):
                                    if isinstance(arg, Identifier):
                                        c_type = self._map_type(f_decl.type_name)
                                        self._emit_line(f"{c_type} {arg.name} = {subj_var}.as.{v_expr.variant_name}.{f_decl.name};")
                                        self.current_scope_types[arg.name] = f_decl.type_name
                            elif v_decl.payload_type:
                                arg = v_expr.args[0]
                                if isinstance(arg, Identifier):
                                    c_type = self._map_type(v_decl.payload_type)
                                    self._emit_line(f"{c_type} {arg.name} = {subj_var}.as.{v_expr.variant_name};")
                                    self.current_scope_types[arg.name] = v_decl.payload_type
                    self._emit_block_body(c.body.statements)
                    if not (c.body.statements and isinstance(c.body.statements[-1], (ReturnStmt, BreakStmt))):
                        self._emit_line("break;")
                    self.indent_level -= 1
                    self._emit_line("}")
                self._emit_line("}")
            elif kdecl and not self._is_tagged_union(kdecl):
                expr_code = self._emit_expression(stmt.expr)
                self._emit_line(f"switch ({expr_code}) {{")
                for c in stmt.cases:
                    if c.is_default:
                        self._emit_line("default: {")
                    else:
                        for v in c.values:
                            if isinstance(v, VariantExpr):
                                self._emit_line(f"case {kdecl.name}_{v.variant_name}:")
                            else:
                                v_code = self._emit_expression(v)
                                self._emit_line(f"case {v_code}:")
                        self._emit_line("{")
                    self.indent_level += 1
                    self.defer_stack.append([])
                    self._emit_block_body(c.body.statements)
                    if not (c.body.statements and isinstance(c.body.statements[-1], (ReturnStmt, BreakStmt))):
                        self._emit_line("break;")
                    self.indent_level -= 1
                    self._emit_line("}")
                self._emit_line("}")
            else:
                expr_code = self._emit_expression(stmt.expr)
                self._emit_line(f"switch ({expr_code}) {{")
                for c in stmt.cases:
                    if c.is_default:
                        self._emit_line("default: {")
                    else:
                        for v in c.values:
                            if isinstance(v, VariantExpr):
                                kname = v.kind_name or self.variant_to_kind.get(v.variant_name, "")
                                prefix = f"{kname}_" if kname else ""
                                self._emit_line(f"case {prefix}{v.variant_name}:")
                            else:
                                v_code = self._emit_expression(v)
                                self._emit_line(f"case {v_code}:")
                        self._emit_line("{")
                    self.indent_level += 1
                    self.defer_stack.append([])
                    self._emit_block_body(c.body.statements)
                    if not (c.body.statements and isinstance(c.body.statements[-1], (ReturnStmt, BreakStmt))):
                        self._emit_line("break;")
                    self.indent_level -= 1
                    self._emit_line("}")
                self._emit_line("}")

    def _emit_if(self, stmt: IfStmt):
        cond_code = self._emit_expression(stmt.condition)
        self._emit_line(f"if ({cond_code}) {{")
        self.indent_level += 1
        self.defer_stack.append([])
        self._emit_block_body(stmt.then_branch.statements)
        self.indent_level -= 1

        if stmt.else_branch:
            if isinstance(stmt.else_branch, IfStmt):
                self._emit_line("} else ")
                self.output[-1] = self.output[-1].rstrip() + " "
                self._emit_if(stmt.else_branch)
                return
            elif isinstance(stmt.else_branch, BlockStmt):
                self._emit_line("} else {")
                self.indent_level += 1
                self.defer_stack.append([])
                self._emit_block_body(stmt.else_branch.statements)
                self.indent_level -= 1
                self._emit_line("}")
        else:
            self._emit_line("}")

    def _infer_raw_velo_type(self, value: Optional[Expr]) -> str:
        if isinstance(value, IntLiteral): return value.type_name if value.type_name else "i32"
        if isinstance(value, FloatLiteral): return value.type_name if value.type_name else "f32"
        if isinstance(value, StringLiteral): return "string"
        if isinstance(value, BoolLiteral): return "bool"
        if isinstance(value, NullLiteral): return "@void"
        if isinstance(value, VariantExpr):
            if value.kind_name: return value.kind_name
            return self.variant_to_kind.get(value.variant_name, "i32")
        if isinstance(value, StructLiteral): return value.struct_name
        if isinstance(value, CastExpr): return value.target_type
        if isinstance(value, AddressOf):
            operand_type = self._resolve_expr_type(value.operand)
            return f"@{operand_type}"
        if isinstance(value, AnonFuncExpr):
            return f"act({', '.join(p.type_name for p in value.params)}) -> {value.return_type}"
        if isinstance(value, Identifier):
            if value.name in self.func_decls:
                fdecl = self.func_decls[value.name]
                return f"act({', '.join(p.type_name for p in fdecl.params)}) -> {fdecl.return_type}"
            return self.current_scope_types.get(value.name, "i32")
        if isinstance(value, DerefExpr):
            return self._resolve_expr_type(value)
        if isinstance(value, MemberAccess):
            if isinstance(value.target, Identifier) and value.target.name in self.kind_defs:
                return value.target.name
            return self._resolve_expr_type(value)
        if isinstance(value, IndexExpr):
            target_type = self._resolve_expr_type(value.target)
            if target_type == "string":
                return "u8"
            if target_type.startswith("@"):
                return target_type[1:]
            return "i32"
        if isinstance(value, CallExpr):
            if isinstance(value.callee, MemberAccess) and isinstance(value.callee.target, Identifier) and value.callee.target.name in self.kind_defs:
                return value.callee.target.name
            if isinstance(value.callee, Identifier):
                if value.callee.name in self.func_return_types:
                    return self.func_return_types[value.callee.name]
            elif isinstance(value.callee, MemberAccess) and isinstance(value.callee.target, Identifier):
                if value.callee.target.name == "mem" and value.callee.member in ("alloc", "heap_alloc"):
                    if len(value.args) >= 1:
                        type_name = self._extract_type_name(value.args[0])
                        return f"@{type_name}"
                elif value.callee.target.name == "mem" and value.callee.member == "current":
                    return "@Allocator"  # §4.1: active arena as a passable handle
                elif value.callee.target.name == "mem" and value.callee.member == "alloc_with":
                    # §4.1: returns @T where T is the type arg (args[1])
                    if len(value.args) >= 2:
                        type_name = self._extract_type_name(value.args[1])
                        return f"@{type_name}"
                elif value.callee.target.name == "thread":
                    # §4.2: spawn/join zero-arg i32 acts; opaque @Mutex ops
                    if value.callee.member == "spawn":
                        return "@Thread"
                    if value.callee.member == "join":
                        return "i32"
                    if value.callee.member == "mutex":
                        return "@Mutex"
                    return "void"  # acquire / release / free
                elif value.callee.target.name == "fs":
                    if value.callee.member == "read_file":
                        return "string"
                    elif value.callee.member in ("write_file", "exists", "remove", "remove_file"):
                        return "bool"
                    elif value.callee.member == "size":
                        return "usize"
                elif value.callee.target.name == "str":
                    if value.callee.member == "len":
                        return "usize"
        return "i32"


    def _infer_or_map_type(self, type_name: Optional[str], value: Optional[Expr]) -> str:
        if type_name:
            return self._map_type(type_name)
        raw = self._infer_raw_velo_type(value)
        return self._map_type(raw)

    def _resolve_expr_type(self, expr: Expr) -> str:
        if isinstance(expr, IntLiteral): return expr.type_name if expr.type_name else "i32"
        if isinstance(expr, FloatLiteral): return expr.type_name if expr.type_name else "f32"
        if isinstance(expr, StringLiteral): return "string"
        if isinstance(expr, BoolLiteral): return "bool"
        if isinstance(expr, NullLiteral): return "@void"
        if isinstance(expr, StructLiteral): return expr.struct_name
        if isinstance(expr, Identifier):
            return self.current_scope_types.get(expr.name, "i32")
        elif isinstance(expr, VariantExpr):
            if expr.kind_name: return expr.kind_name
            return self.variant_to_kind.get(expr.variant_name, "i32")
        elif isinstance(expr, CastExpr):
            return expr.target_type
        elif isinstance(expr, AddressOf):
            sub_type = self._resolve_expr_type(expr.operand)
            return f"@{sub_type}"
        elif isinstance(expr, DerefExpr):
            sub_type = self._resolve_expr_type(expr.operand)
            if sub_type.startswith("@"):
                return sub_type[1:]
            return sub_type
        elif isinstance(expr, IndexExpr):
            target_type = self._resolve_expr_type(expr.target)
            if target_type == "string":
                return "u8"
            if target_type.startswith("@"):
                return target_type[1:]
            return target_type
        elif isinstance(expr, MemberAccess):
            if isinstance(expr.target, Identifier) and expr.target.name in self.kind_defs:
                return expr.target.name
            target_type = self._resolve_expr_type(expr.target)
            clean_type = target_type.lstrip("@")
            fields = self.struct_defs.get(clean_type, {})
            return fields.get(expr.member, "i32")
        elif isinstance(expr, AnonFuncExpr):
            return f"act({', '.join(p.type_name for p in expr.params)}) -> {expr.return_type}"
        elif isinstance(expr, CallExpr):
            if isinstance(expr.callee, MemberAccess) and isinstance(expr.callee.target, Identifier) and expr.callee.target.name in self.kind_defs:
                return expr.callee.target.name
            if isinstance(expr.callee, Identifier):
                if expr.callee.name in self.func_return_types:
                    return self.func_return_types[expr.callee.name]
                callee_type = self.current_scope_types.get(expr.callee.name)
                if callee_type:
                    parsed = parse_act_type(callee_type)
                    if parsed:
                        return parsed[2]
            elif isinstance(expr.callee, MemberAccess) and isinstance(expr.callee.target, Identifier):
                if expr.callee.target.name == "mem" and expr.callee.member in ("alloc", "heap_alloc"):
                    if len(expr.args) >= 1:
                        type_name = self._extract_type_name(expr.args[0])
                        return f"@{type_name}"
                elif expr.callee.target.name == "mem" and expr.callee.member == "current":
                    return "@Allocator"  # §4.1
                elif expr.callee.target.name == "mem" and expr.callee.member == "alloc_with":
                    # §4.1: type is @T where T is the type arg (args[1])
                    if len(expr.args) >= 2:
                        type_name = self._extract_type_name(expr.args[1])
                        return f"@{type_name}"
                elif expr.callee.target.name == "thread":
                    # §4.2: spawn/join zero-arg i32 acts; opaque @Mutex ops
                    if expr.callee.member == "spawn":
                        return "@Thread"
                    if expr.callee.member == "join":
                        return "i32"
                    if expr.callee.member == "mutex":
                        return "@Mutex"
                    return "void"  # acquire / release / free
                elif expr.callee.target.name == "fs":
                    if expr.callee.member == "read_file":
                        return "string"
                    elif expr.callee.member in ("write_file", "exists", "remove", "remove_file"):
                        return "bool"
                    elif expr.callee.member == "size":
                        return "usize"
                elif expr.callee.target.name == "str":
                    if expr.callee.member == "len":
                        return "usize"
                target_type = self._resolve_expr_type(expr.callee.target)
                clean_type = target_type.lstrip("@")
                fields = self.struct_defs.get(clean_type, {})
                if expr.callee.member in fields:
                    callee_type = fields[expr.callee.member]
                    parsed = parse_act_type(callee_type)
                    if parsed:
                        return parsed[2]
                elif expr.callee.member in self.func_return_types:
                    return self.func_return_types[expr.callee.member]
                callee_type = self._resolve_expr_type(expr.callee)
                parsed = parse_act_type(callee_type)
                if parsed:
                    return parsed[2]
            else:
                if isinstance(expr.callee, MemberAccess):
                    target_type = self._resolve_expr_type(expr.callee.target)
                    clean_type = target_type.lstrip("@")
                    fields = self.struct_defs.get(clean_type, {})
                    if expr.callee.member in fields:
                        callee_type = fields[expr.callee.member]
                        parsed = parse_act_type(callee_type)
                        if parsed:
                            return parsed[2]
                    elif expr.callee.member in self.func_return_types:
                        return self.func_return_types[expr.callee.member]
                callee_type = self._resolve_expr_type(expr.callee)
                parsed = parse_act_type(callee_type)
                if parsed:
                    return parsed[2]
        elif isinstance(expr, BinaryExpr):
            if expr.op in ("==", "!=", "<", "<=", ">", ">="):
                return "bool"
            return self._resolve_expr_type(expr.left)
        elif isinstance(expr, UnaryExpr):
            if expr.op in ("!", "not"):
                return "bool"
            return self._resolve_expr_type(expr.operand)
        return "i32"

    def _emit_expression(self, expr: Expr) -> str:
        if isinstance(expr, NullLiteral):
            return "NULL"
        elif isinstance(expr, IntLiteral):
            if expr.raw_str:
                clean = "".join(c for c in expr.raw_str if c != '_')
                if expr.type_name:
                    sfx = expr.type_name
                    digits = clean[:-len(sfx)]
                    if sfx in ("u64", "usize"):
                        return f"{digits}ULL"
                    elif sfx in ("i64", "isize"):
                        return f"{digits}LL"
                    elif sfx in ("u8", "u16", "u32"):
                        return f"{digits}U"
                    return digits
                elif clean.startswith("0b") or clean.startswith("0B") or clean.startswith("0o") or clean.startswith("0O"):
                    return str(expr.value)
                return clean
            return str(expr.value)
        elif isinstance(expr, FloatLiteral):
            if expr.raw_str:
                clean = "".join(c for c in expr.raw_str if c != '_')
                if expr.type_name:
                    sfx = expr.type_name
                    digits = clean[:-len(sfx)]
                    if sfx == "f64":
                        return digits
                    else:
                        return f"{digits}f" if not digits.endswith("f") else digits
                elif not clean.endswith("f") and not clean.endswith("F"):
                    return f"{clean}f"
                return clean
            return f"{expr.value}f"
        elif isinstance(expr, StringLiteral):
            escaped = (expr.value
                       .replace('\\', '\\\\')
                       .replace('"', '\\"')
                       .replace('\n', '\\n')
                       .replace('\r', '\\r')
                       .replace('\t', '\\t')
                       .replace('\0', '\\0'))
            return f'"{escaped}"'
        elif isinstance(expr, BoolLiteral):
            return "true" if expr.value else "false"
        elif isinstance(expr, Identifier):
            return expr.name
        elif isinstance(expr, AddressOf):
            sub = self._emit_expression(expr.operand)
            return f"(&{sub})"
        elif isinstance(expr, DerefExpr):
            sub = self._emit_expression(expr.operand)
            return f"(*{sub})"
        elif isinstance(expr, IndexExpr):
            target_code = self._emit_expression(expr.target)
            index_code = self._emit_expression(expr.index)
            return f"{target_code}[{index_code}]"
        elif isinstance(expr, CastExpr):
            sub = self._emit_expression(expr.expr)
            c_type = self._map_type(expr.target_type)
            return f"(({c_type})({sub}))"
        elif isinstance(expr, StructLiteral):
            inits = [f".{fname} = {self._emit_expression(fval)}" for fname, fval in expr.field_inits]
            field_decls = self.struct_field_decls.get(expr.struct_name)
            if field_decls:
                covered = {fname for fname, _ in expr.field_inits}
                for f in field_decls:
                    if f.name in covered:
                        continue
                    if f.default_expr is None:
                        raise ValueError(f"Struct literal '{expr.struct_name}' is missing field '{f.name}' and it has no default initializer")
                    inits.append(f".{f.name} = {self._emit_expression(f.default_expr)}")
            return f"({expr.struct_name}){{ {', '.join(inits)} }}"
        elif isinstance(expr, VariantExpr):
            kname = expr.kind_name or self.variant_to_kind.get(expr.variant_name)
            kdecl = self.kind_defs.get(kname) if kname else None
            if not kdecl or not self._is_tagged_union(kdecl):
                prefix = f"{kname}_" if kname else ""
                return f"{prefix}{expr.variant_name}"
            vdecl = next((v for v in kdecl.variants if v.name == expr.variant_name), None)
            if not expr.args:
                return f"({kname}){{ .kind = {kname}_{expr.variant_name} }}"
            if vdecl and vdecl.fields and len(vdecl.fields) > 0:
                inits = [f".{f.name} = {self._emit_expression(a)}" for f, a in zip(vdecl.fields, expr.args)]
                return f"({kname}){{ .kind = {kname}_{expr.variant_name}, .as = {{ .{expr.variant_name} = {{ {', '.join(inits)} }} }} }}"
            elif vdecl and vdecl.payload_type:
                arg_code = self._emit_expression(expr.args[0])
                return f"({kname}){{ .kind = {kname}_{expr.variant_name}, .as = {{ .{expr.variant_name} = {arg_code} }} }}"
            return f"({kname}){{ .kind = {kname}_{expr.variant_name} }}"
        elif isinstance(expr, MemberAccess):
            if isinstance(expr.target, Identifier) and expr.target.name in self.kind_defs:
                kdecl = self.kind_defs[expr.target.name]
                if not self._is_tagged_union(kdecl):
                    return f"{expr.target.name}_{expr.member}"
                return f"({expr.target.name}){{ .kind = {expr.target.name}_{expr.member} }}"
            target_code = self._emit_expression(expr.target)
            target_type = self._resolve_expr_type(expr.target)
            arrow = "->" if target_type.startswith("@") else "."
            return f"{target_code}{arrow}{expr.member}"
        elif isinstance(expr, BinaryExpr):
            left = self._emit_expression(expr.left)
            right = self._emit_expression(expr.right)
            op = expr.op

            # Smart string value comparison
            if op in ("==", "!=") and not isinstance(expr.left, NullLiteral) and not isinstance(expr.right, NullLiteral):
                l_type = self._resolve_expr_type(expr.left)
                r_type = self._resolve_expr_type(expr.right)
                if l_type == "string" and r_type == "string":
                    cmp_op = "==" if op == "==" else "!="
                    return f"(({left} != NULL && {right} != NULL) ? (strcmp({left}, {right}) {cmp_op} 0) : ({left} {op} {right}))"

            if op == "and": op = "&&"
            elif op == "or": op = "||"
            return f"({left} {op} {right})"
        elif isinstance(expr, UnaryExpr):
            sub = self._emit_expression(expr.operand)
            op = "!" if expr.op in ("!", "not") else expr.op
            return f"({op}{sub})"
        elif isinstance(expr, CallExpr):
            if isinstance(expr.callee, MemberAccess) and isinstance(expr.callee.target, Identifier) and expr.callee.target.name in self.kind_defs:
                kname = expr.callee.target.name
                vname = expr.callee.member
                kdecl = self.kind_defs[kname]
                vdecl = next((v for v in kdecl.variants if v.name == vname), None)
                if vdecl and vdecl.fields and len(vdecl.fields) > 0:
                    inits = [f".{f.name} = {self._emit_expression(a)}" for f, a in zip(vdecl.fields, expr.args)]
                    return f"({kname}){{ .kind = {kname}_{vname}, .as = {{ .{vname} = {{ {', '.join(inits)} }} }} }}"
                elif vdecl and vdecl.payload_type:
                    arg_code = self._emit_expression(expr.args[0])
                    return f"({kname}){{ .kind = {kname}_{vname}, .as = {{ .{vname} = {arg_code} }} }}"
                return f"({kname}){{ .kind = {kname}_{vname} }}"
            if isinstance(expr.callee, MemberAccess):
                if isinstance(expr.callee.target, Identifier):
                    if expr.callee.target.name == "io":
                        if expr.callee.member in ("println", "print"):
                            return self._lower_io_call(expr.callee.member, expr.args)
                        elif expr.callee.member == "print_char":
                            return f"velo_io_print_char((char)({self._emit_expression(expr.args[0])}))"
                    
                    elif expr.callee.target.name == "mem":
                        if expr.callee.member == "alloc":
                            return self._lower_mem_alloc(expr.args)
                        elif expr.callee.member == "heap_alloc":
                            return self._lower_heap_alloc(expr.args)
                        elif expr.callee.member == "free":
                            return self._lower_heap_free(expr.args)
                        elif expr.callee.member == "used":
                            return "velo_mem_used()"
                        elif expr.callee.member == "heap_used":
                            return "velo_heap_used()"
                        elif expr.callee.member == "current":
                            # §4.1: capture the active arena as a passable @Allocator handle
                            # §4.1/§4.2: per-thread active arena as a passable handle
                            return "velo_zone_active()"
                        elif expr.callee.member == "alloc_with":
                            # §4.1: allocate into an explicit @Allocator handle
                            return self._lower_mem_alloc_with(expr.args)

                    elif expr.callee.target.name == "thread":
                        # §4.2: spawn/join zero-arg i32 acts; opaque @Mutex ops
                        # Args are compile-checked — never blindly cast.
                        self._thread_expect(expr.callee.member, expr.args)
                        if expr.callee.member == "spawn":
                            arg_code = self._emit_expression(expr.args[0]) if expr.args else "0"
                            return f"velo_thread_spawn((VeloThreadFn)({arg_code}))"
                        elif expr.callee.member == "join":
                            arg_code = self._emit_expression(expr.args[0]) if expr.args else "0"
                            return f"velo_thread_join({arg_code})"
                        elif expr.callee.member == "mutex":
                            return "velo_mutex_create()"
                        elif expr.callee.member == "acquire":
                            arg_code = self._emit_expression(expr.args[0])
                            return f"velo_mutex_acquire((void*)({arg_code}))"
                        elif expr.callee.member == "release":
                            arg_code = self._emit_expression(expr.args[0])
                            return f"velo_mutex_release((void*)({arg_code}))"
                        elif expr.callee.member == "free":
                            arg_code = self._emit_expression(expr.args[0])
                            return f"velo_mutex_destroy((void*)({arg_code}))"

                    elif expr.callee.target.name == "fs":
                        if expr.callee.member == "read_file":
                            return self._lower_fs_read_file(expr.args)
                        elif expr.callee.member == "write_file":
                            return self._lower_fs_write_file(expr.args)
                        elif expr.callee.member == "exists":
                            return self._lower_fs_exists(expr.args)
                        elif expr.callee.member == "size":
                            return self._lower_fs_size(expr.args)
                        elif expr.callee.member in ("remove", "remove_file"):
                            return self._lower_fs_remove(expr.args)

                    elif expr.callee.target.name == "str":
                        if expr.callee.member == "len":
                            return f"((usize)strlen({self._emit_expression(expr.args[0])}))"

                target_type = self._resolve_expr_type(expr.callee.target)
                clean_type = target_type.lstrip("@")
                struct_fields = self.struct_defs.get(clean_type, {})
                if expr.callee.member not in struct_fields and expr.callee.member in self.func_decls:
                    fn = self.func_decls[expr.callee.member]
                    target_code = self._emit_expression(expr.callee.target)
                    p0_type = fn.params[0].type_name if fn.params else ""
                    if p0_type.startswith("@") and not target_type.startswith("@"):
                        first_arg_code = f"(&({target_code}))"
                    elif target_type.startswith("@") and not p0_type.startswith("@"):
                        first_arg_code = f"(*({target_code}))"
                    else:
                        first_arg_code = target_code
                    arg_codes = [first_arg_code] + [self._emit_expression(arg) for arg in expr.args]
                    return f"{expr.callee.member}({', '.join(arg_codes)})"

            callee_code = self._emit_expression(expr.callee)
            arg_codes = [self._emit_expression(arg) for arg in expr.args]
            return f"{callee_code}({', '.join(arg_codes)})"
        elif isinstance(expr, AnonFuncExpr):
            return self.anon_expr_to_name.get(id(expr), f"_velo_anon_act_{len(self.anon_funcs)}")

        raise ValueError(f"Unknown expression node: {type(expr)}")

    def _is_thread_entry(self, expr: Expr) -> bool:
        """§4.2: is `expr` a zero-arg, i32-returning act value? Accepts a
        named top-level act, an act-typed local/global, or an anonymous act.
        Anything else must fail loudly, never reach a C-level cast."""
        if isinstance(expr, AnonFuncExpr):
            return len(expr.params) == 0 and expr.return_type == "i32"
        if isinstance(expr, Identifier):
            sig = self.current_scope_types.get(expr.name)
            if sig and sig.replace(" ", "").replace("\t", "") == "act()->i32":
                return True
            decl = self.func_decls.get(expr.name)
            if decl is not None:
                return len(decl.params) == 0 and (decl.return_type or "void") == "i32"
        return False

    def _thread_arg_type(self, expr: Expr) -> str:
        if isinstance(expr, AnonFuncExpr):
            return f"act({', '.join(p.type_name for p in expr.params)}) -> {expr.return_type}"
        if isinstance(expr, Identifier):
            decl = self.func_decls.get(expr.name)
            if decl is not None:
                params = ", ".join(p.type_name for p in decl.params)
                return f"act({params}) -> {decl.return_type or 'void'}"
        return self._resolve_expr_type(expr)

    def _thread_expect(self, member: str, args: List[Expr]) -> None:
        """§4.2: compile-checks thread intrinsic arguments. Mirrored by the
        Stage 2 type checker — both stages must reject the same programs
        with the same messages."""
        counts = {"spawn": 1, "join": 1, "acquire": 1, "release": 1, "free": 1, "mutex": 0}
        if member not in counts:
            return  # unknown member: falls through to the generic error path
        if member == "mutex":
            if args:
                raise ValueError("thread.mutex takes no arguments")
            return
        if len(args) != counts[member]:
            raise ValueError(f"thread.{member} takes exactly 1 argument")
        if member == "mutex":
            return
        if member == "spawn" and self._is_thread_entry(args[0]):
            return
        got = self._thread_arg_type(args[0])
        want = {"spawn": "act() -> i32", "join": "@Thread", "acquire": "@Mutex",
                "release": "@Mutex", "free": "@Mutex"}[member]
        if got.replace(" ", "").replace("\t", "") != want.replace(" ", ""):
            raise ValueError(f"thread.{member} expects {want} (got {got})")

    def _lower_mem_alloc(self, args: List[Expr]) -> str:
        if len(args) != 2:
            raise ValueError("mem.alloc expects exactly 2 arguments: (@Type, count)")
        type_name = self._extract_type_name(args[0])
        c_type = self._map_type(type_name)
        count_code = self._emit_expression(args[1])
        return f"({c_type}*)velo_mem_alloc(sizeof({c_type}), (size_t)({count_code}))"

    def _lower_heap_alloc(self, args: List[Expr]) -> str:
        if len(args) != 2:
            raise ValueError("mem.heap_alloc expects exactly 2 arguments: (@Type, count)")
        type_name = self._extract_type_name(args[0])
        c_type = self._map_type(type_name)
        count_code = self._emit_expression(args[1])
        return f"({c_type}*)velo_heap_alloc(sizeof({c_type}), (size_t)({count_code}))"

    def _lower_heap_free(self, args: List[Expr]) -> str:
        if len(args) != 1:
            raise ValueError("mem.free expects exactly 1 argument: (ptr)")
        ptr_code = self._emit_expression(args[0])
        return f"velo_heap_free((void*)({ptr_code}))"

    def _lower_mem_alloc_with(self, args: List[Expr]) -> str:
        # §4.1: mem.alloc_with(allocator, @Type, count)
        if len(args) != 3:
            raise ValueError("mem.alloc_with expects exactly 3 arguments: (allocator, @Type, count)")
        alloc_code = self._emit_expression(args[0])
        type_name = self._extract_type_name(args[1])
        c_type = self._map_type(type_name)
        count_code = self._emit_expression(args[2])
        return f"({c_type}*)velo_alloc_with((VeloAllocator)({alloc_code}), sizeof({c_type}), (size_t)({count_code}))"

    def _lower_fs_read_file(self, args: List[Expr]) -> str:
        if len(args) != 1:
            raise ValueError("fs.read_file expects exactly 1 argument: (path)")
        path_code = self._emit_expression(args[0])
        return f"velo_fs_read_file({path_code})"

    def _lower_fs_write_file(self, args: List[Expr]) -> str:
        if len(args) != 2:
            raise ValueError("fs.write_file expects exactly 2 arguments: (path, content)")
        path_code = self._emit_expression(args[0])
        content_code = self._emit_expression(args[1])
        return f"velo_fs_write_file({path_code}, {content_code})"

    def _lower_fs_exists(self, args: List[Expr]) -> str:
        if len(args) != 1:
            raise ValueError("fs.exists expects exactly 1 argument: (path)")
        path_code = self._emit_expression(args[0])
        return f"velo_fs_exists({path_code})"

    def _lower_fs_size(self, args: List[Expr]) -> str:
        if len(args) != 1:
            raise ValueError("fs.size expects exactly 1 argument: (path)")
        path_code = self._emit_expression(args[0])
        return f"velo_fs_size({path_code})"

    def _lower_fs_remove(self, args: List[Expr]) -> str:
        if len(args) != 1:
            raise ValueError("fs.remove expects exactly 1 argument: (path)")
        path_code = self._emit_expression(args[0])
        return f"velo_fs_remove({path_code})"

    def _extract_type_name(self, expr: Expr) -> str:
        if isinstance(expr, AddressOf) and isinstance(expr.operand, Identifier):
            return expr.operand.name
        elif isinstance(expr, Identifier):
            return expr.name
        return "void"

    def _lower_io_call(self, member: str, args: List[Expr]) -> str:
        nl_char = "\n" if member == "println" else ""
        if len(args) == 0:
            return 'printf("\\n")'

        first_arg = args[0]
        if isinstance(first_arg, StringLiteral):
            text = first_arg.value
            pattern = re.compile(r'\{([a-zA-Z0-9_\.@\[\]]+)\}')
            matches = list(pattern.finditer(text))

            if matches:
                fmt_parts = []
                c_args = []
                last_idx = 0

                for m in matches:
                    fmt_parts.append(text[last_idx:m.start()])
                    var_path = m.group(1)

                    resolved_type = self._resolve_path_type(var_path)
                    c_expr = self._convert_path_to_c(var_path)

                    if resolved_type in ("f32", "f64"):
                        fmt_parts.append("%.2f")
                        c_args.append(f"(double)({c_expr})")
                    elif resolved_type == "string":
                        fmt_parts.append("%s")
                        c_args.append(f"(const char*)({c_expr})")
                    elif resolved_type == "bool":
                        fmt_parts.append("%s")
                        c_args.append(f"(({c_expr}) ? \"true\" : \"false\")")
                    else:
                        fmt_parts.append("%lld")
                        c_args.append(f"(long long)({c_expr})")

                    last_idx = m.end()

                fmt_parts.append(text[last_idx:])
                full_fmt = "".join(fmt_parts) + nl_char
                escaped_fmt = full_fmt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')

                return f'printf("{escaped_fmt}", {", ".join(c_args)})'
            else:
                escaped = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')
                if member == "println":
                    return f'velo_io_println("{escaped}")'
                else:
                    return f'velo_io_print("{escaped}")'

        arg_code = self._emit_expression(first_arg)
        resolved = self._resolve_expr_type(first_arg)
        if resolved in ("f32", "f64"):
            fmt_str = "%f\\n" if member == "println" else "%f"
            return f'printf("{fmt_str}", (double)({arg_code}))'
        elif resolved == "string":
            fmt_str = "%s\\n" if member == "println" else "%s"
            return f'printf("{fmt_str}", (const char*)({arg_code}))'
        elif resolved == "bool":
            fmt_str = "%s\\n" if member == "println" else "%s"
            return f'printf("{fmt_str}", ({arg_code}) ? "true" : "false")'
        else:
            fmt_str = "%lld\\n" if member == "println" else "%lld"
            return f'printf("{fmt_str}", (long long)({arg_code}))'

    def _resolve_path_type(self, path: str) -> str:
        if ".@" in path:
            base = path.replace(".@", "")
            base_type = self.current_scope_types.get(base, "i32")
            return base_type.lstrip("@")

        clean_path = re.sub(r'\[[a-zA-Z0-9_]+\]', '', path)

        parts = clean_path.split(".")
        if len(parts) == 1:
            return self.current_scope_types.get(parts[0], "i32")

        curr_type = self.current_scope_types.get(parts[0], "")
        for part in parts[1:]:
            clean_type = curr_type.lstrip("@")
            fields = self.struct_defs.get(clean_type, {})
            curr_type = fields.get(part, "f32")

        return curr_type

    def _convert_path_to_c(self, path: str) -> str:
        if ".@" in path:
            base = path.replace(".@", "")
            return f"(*{base})"

        parts = path.split(".")
        if len(parts) == 1:
            return parts[0]

        result = parts[0]
        has_bracket = "[" in parts[0]
        curr_type = self.current_scope_types.get(parts[0].split("[")[0], "")

        for part in parts[1:]:
            if has_bracket:
                arrow = "."
            else:
                arrow = "->" if curr_type.startswith("@") else "."
            result = f"{result}{arrow}{part}"
            has_bracket = "[" in part
            clean_type = curr_type.lstrip("@")
            fields = self.struct_defs.get(clean_type, {})
            curr_type = fields.get(part.split("[")[0], "f32")

        return result
