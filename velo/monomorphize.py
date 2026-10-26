"""
Monomorphizer for the Velo Programming Language.
Expands generic templates (data, kind, act) into concrete, zero-overhead C specializations.
"""

from typing import List, Optional, Tuple, Dict, Set, Any
from copy import deepcopy
from velo.ast_nodes import (
    Program, Decl, UseStmt, FunctionDecl, ExternDecl, Param, BlockStmt, DataDecl, Field, KindDecl, VariantDecl,
    Stmt, ExprStmt, ReturnStmt, BreakStmt, ContinueStmt, VarDeclStmt, AssignStmt, IfStmt, LoopStmt, ZoneStmt, DeferStmt,
    MatchCase, MatchStmt,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral, VariantExpr,
    Identifier, MemberAccess, IndexExpr, DerefExpr, StructLiteral, CastExpr, CallExpr, AddressOf, BinaryExpr, UnaryExpr, AnonFuncExpr,
    ShelfLiteral, MapLiteral, RingLiteral, BitsetLiteral,
    TypeAliasDecl, TestDecl,
    mangle_op_name, OP_SYMBOL_TO_NAME
)


def parse_type_signature(t: str) -> Tuple[str, str, List[str]]:
    """
    Parses a type string into (pointer_prefix, base_name, type_arguments).
    E.g. '@Box[Option[i32], string]' -> ('@', 'Box', ['Option[i32]', 'string'])
    """
    if not t:
        return "", "", []
    prefix = ""
    while t.startswith("@"):
        prefix += "@"
        t = t[1:]
    if "[" in t and t.endswith("]"):
        bracket_idx = t.index("[")
        base = t[:bracket_idx]
        inner = t[bracket_idx + 1:-1]
        args: List[str] = []
        depth = 0
        cur: List[str] = []
        for ch in inner:
            if ch == "[":
                depth += 1
                cur.append(ch)
            elif ch == "]":
                depth -= 1
                cur.append(ch)
            elif ch == "," and depth == 0:
                args.append("".join(cur).strip())
                cur = []
            else:
                cur.append(ch)
        if cur:
            args.append("".join(cur).strip())
        return prefix, base, args
    return prefix, t, []


def mangle_type_name(t: str) -> str:
    """
    Produces a valid C identifier representation of a type.
    E.g. 'Box[i32]' -> 'Box_i32', '@i32' -> 'ptr_i32', 'Pair[string, @i32]' -> 'Pair_string_ptr_i32'.
    """
    if not t:
        return t
    prefix, base, args = parse_type_signature(t)
    if not args:
        clean_base = base
    else:
        mangled_args = [mangle_type_name(a) for a in args]
        clean_base = f"{base}_{'_'.join(mangled_args)}"
    clean_prefix = prefix.replace("@", "ptr_")
    clean_base = clean_base.replace("[", "_").replace("]", "").replace(", ", "_").replace(",", "_").replace("@", "ptr_")
    return clean_prefix + clean_base


def _shelf_elem_of(t: Optional[str]) -> Optional[str]:
    """5.2: extracts the element type from 'shelf[T]' / '@shelf[T]', or None.
    Slice 10: 'heap shelf[T]' strips the modifier first."""
    if not t:
        return None
    raw = t.lstrip("@").strip()
    if raw.startswith("heap shelf[") and raw.endswith("]"):
        raw = raw[5:]
    if raw.startswith("shelf[") and raw.endswith("]"):
        inner = raw[6:-1].strip()
        return inner or None
    return None


def _map_kv_of(t: Optional[str]) -> Optional[Tuple[str, str]]:
    """5.2 slice 6: extracts (key, value) from 'Map[K, V]' / '@Map[K, V]',
    or None. Bracket-depth aware — value slots may themselves be maps."""
    if not t:
        return None
    raw = t.lstrip("@").strip()
    if raw.startswith("Map[") and raw.endswith("]"):
        inner = raw[4:-1].strip()
        depth = 0
        for i, ch in enumerate(inner):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            elif ch == "," and depth == 0:
                key = inner[:i].strip()
                val = inner[i + 1:].strip()
                if key and val:
                    return key, val
    return None


# 5.2 slice 2 (shelf[dyn]): the numeric families of the inference ladder. The
# widen rule is int+float → f64; any other mix lowers to shelf[dyn] (tagged
# boxes). Shared with codegen_c — one spelling of the ladder policy per stage.
DYN_INT_TYPES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize", "isize"}
DYN_FLOAT_TYPES = {"f32", "f64"}


def normalize_type_name(t: Optional[str]) -> Optional[str]:
    """
    Normalizes a generic type signature in AST to its mangled concrete name, preserving leading '@'.
    E.g. '@Box[i32]' -> '@Box_i32', 'Option[string]' -> 'Option_string', 'i32' -> 'i32'.
    5.2: `shelf[T]` passes through UNCHANGED — the codegen extracts the element
    type from the kept bracket form (`_shelf_elem_type`), never from a mangled name.
    """
    if not t:
        return t
    # 5.2 slice 10: `heap shelf[...]` passes through UNCHANGED like shelf — the
    # heap prefix must reach the emit tier (the src sentinel) intact. Checked
    # before parse_type_signature (the space splits oddly there).
    if t.lstrip("@").startswith("heap shelf"):
        return t
    prefix, base, args = parse_type_signature(t)
    if base == "shelf":
        return t  # 5.2: keep the bracket form; elem extraction needs it
    if base == "Map":
        return t  # 5.2 slice 6: keep `Map[K, V]`; the two-slot extraction needs it
    if base == "ring":
        return t  # 5.2 slice 9: keep `ring[T]`; elem extraction needs it
    # 5.2 slice 9: `bitset` is bare (no bracket args) and passes through below.
    if not args:
        return prefix + base
    mangled_args = [mangle_type_name(a) for a in args]
    return f"{prefix}{base}_{'_'.join(mangled_args)}"


def parse_act_type(type_str: str) -> Optional[Tuple[str, List[str], str]]:
    if not type_str:
        return None
    prefix = ""
    while type_str.startswith("@"):
        prefix += "@"
        type_str = type_str[1:]
    if not type_str.startswith("act("):
        return None
    arrow_idx = type_str.rfind("->")
    if arrow_idx != -1:
        ret_type = type_str[arrow_idx + 2:].strip()
        params_str = type_str[4:arrow_idx].strip()
    else:
        ret_type = "void"
        params_str = type_str[4:].strip()
    if params_str.endswith(")"):
        params_str = params_str[:-1].strip()
    params = []
    if params_str:
        depth = 0
        cur = []
        for ch in params_str:
            if ch in "([":
                depth += 1
                cur.append(ch)
            elif ch in ")]":
                depth -= 1
                cur.append(ch)
            elif ch == "," and depth == 0:
                params.append("".join(cur).strip())
                cur = []
            else:
                cur.append(ch)
        if cur:
            params.append("".join(cur).strip())
    return prefix, params, ret_type


def mangle_act_type(params: List[str], ret_type: str) -> str:
    def clean(t: str) -> str:
        parsed = parse_act_type(t)
        if parsed:
            _, sub_params, sub_ret = parsed
            return mangle_act_type(sub_params, sub_ret)
        return t.replace("@", "ptr_").replace("[", "_").replace("]", "").replace(" ", "").replace(",", "_")
    p_str = "_".join(clean(p) for p in params) if params else "void"
    r_str = clean(ret_type)
    return f"velo_act_{p_str}_to_{r_str}"


def subst_type(t: Optional[str], subst: Dict[str, str]) -> Optional[str]:
    """
    Replaces type parameters with concrete types.
    E.g. 'Box[T]' with {'T': 'i32'} -> 'Box[i32]'.
    """
    if not t:
        return t
    parsed_act = parse_act_type(t)
    if parsed_act:
        p_prefix, p_params, p_ret = parsed_act
        new_params = [subst_type(p, subst) or p for p in p_params]
        new_ret = subst_type(p_ret, subst) or p_ret
        return f"{p_prefix}act({', '.join(new_params)}) -> {new_ret}"

    prefix, base, args = parse_type_signature(t)
    if base in subst:
        replacement = subst[base]
        return prefix + replacement
    if args:
        new_args = [subst_type(a, subst) or a for a in args]
        return f"{prefix}{base}[{', '.join(new_args)}]"
    return prefix + base


class Monomorphizer:
    def __init__(self):
        self.generic_structs: Dict[str, DataDecl] = {}
        self.generic_kinds: Dict[str, KindDecl] = {}
        self.generic_funcs: Dict[str, FunctionDecl] = {}

        self.instantiated_structs: Dict[str, DataDecl] = {}
        self.instantiated_kinds: Dict[str, KindDecl] = {}
        self.instantiated_funcs: Dict[str, FunctionDecl] = {}

        self.worklist: List[Tuple[str, str, Tuple[str, ...]]] = []
        self.seen_instantiations: Set[Tuple[str, str, Tuple[str, ...]]] = set()

        self.func_return_types: Dict[str, str] = {}
        self.func_param_types: Dict[str, List[str]] = {}
        self.struct_fields: Dict[str, Set[str]] = {}
        self.struct_field_types: Dict[str, Dict[str, str]] = {}
        self.kind_names: Set[str] = set()
        self.op_overloads: Dict[Tuple[str, int, Tuple[str, ...]], str] = {}
        self.generic_op_overloads: Dict[Tuple[str, int], FunctionDecl] = {}

    def request_instantiation(self, kind: str, template_name: str, args: Tuple[str, ...]):
        key = (kind, template_name, args)
        if key not in self.seen_instantiations:
            self.seen_instantiations.add(key)
            self.worklist.append(key)

    def monomorphize(self, program: Program) -> Program:
        # Pass 0: Canonicalize primitive type aliases (`aka Foo = u64`) in place,
        # so every downstream stage sees the concrete target type everywhere.
        self.type_aliases: Dict[str, str] = {}
        for decl in program.declarations:
            if isinstance(decl, TypeAliasDecl):
                if decl.name in self.type_aliases:
                    raise ValueError(f"Duplicate type alias '{decl.name}'")
                self.type_aliases[decl.name] = decl.target_type
        self._canonicalize_program_types(program)

        # Pass 1: Collect generic templates and regular declarations
        regular_decls: List[Decl] = []
        for decl in program.declarations:
            if isinstance(decl, DataDecl):
                if decl.type_params:
                    self.generic_structs[decl.name] = decl
                else:
                    regular_decls.append(decl)
                f_map = {f.name: (normalize_type_name(f.type_name) or f.type_name) for f in decl.fields}
                self.struct_fields[decl.name] = set(f_map.keys())
                self.struct_field_types[decl.name] = f_map
            elif isinstance(decl, KindDecl):
                if decl.type_params:
                    self.generic_kinds[decl.name] = decl
                else:
                    regular_decls.append(decl)
                self.kind_names.add(decl.name)
            elif isinstance(decl, FunctionDecl) and decl.type_params:
                self.generic_funcs[decl.name] = decl
                if getattr(decl, 'is_operator', False):
                    self.generic_op_overloads[(decl.operator_symbol, len(decl.params))] = decl
            else:
                regular_decls.append(decl)
                if isinstance(decl, FunctionDecl) and getattr(decl, 'is_operator', False):
                    param_types = tuple(normalize_type_name(p.type_name) or "i32" for p in decl.params)
                    self.op_overloads[(decl.operator_symbol, len(param_types), param_types)] = decl.name

        # Collect return and parameter types for all known non-generic functions and externs
        for decl in regular_decls:
            if isinstance(decl, FunctionDecl):
                self.func_return_types[decl.name] = normalize_type_name(decl.return_type) or "void"
                self.func_param_types[decl.name] = [normalize_type_name(p.type_name) or "i32" for p in decl.params]
            elif isinstance(decl, ExternDecl):
                self.func_return_types[decl.name] = normalize_type_name(decl.return_type) or "void"
                self.func_param_types[decl.name] = [normalize_type_name(p.type_name) or "i32" for p in decl.params]

        # Pass 2: Normalize and specialize regular declarations
        transformed_regular_decls: List[Decl] = []
        for decl in regular_decls:
            if isinstance(decl, FunctionDecl):
                transformed_decl = self._transform_function(decl, {})
                transformed_regular_decls.append(transformed_decl)
            elif isinstance(decl, DataDecl):
                # Check field types
                new_fields: List[Field] = []
                for f in decl.fields:
                    self._check_type_usage(f.type_name)
                    new_fields.append(Field(name=f.name, type_name=normalize_type_name(f.type_name) or "i32", line=f.line, col=f.col, default_expr=f.default_expr))
                transformed_regular_decls.append(DataDecl(name=decl.name, fields=new_fields, line=decl.line, col=decl.col,
                                                          type_params=decl.type_params, align=decl.align, packed=decl.packed))
            elif isinstance(decl, KindDecl):
                new_variants: List[VariantDecl] = []
                for v in decl.variants:
                    ptype = v.payload_type
                    if ptype:
                        self._check_type_usage(ptype)
                        ptype = normalize_type_name(ptype)
                    vf = None
                    if v.fields:
                        vf = []
                        for f in v.fields:
                            self._check_type_usage(f.type_name)
                            vf.append(Field(name=f.name, type_name=normalize_type_name(f.type_name) or "i32", line=f.line, col=f.col, default_expr=f.default_expr))
                    new_variants.append(VariantDecl(name=v.name, line=v.line, col=v.col, discriminant=v.discriminant, payload_type=ptype, fields=vf))
                transformed_regular_decls.append(KindDecl(name=decl.name, variants=new_variants, line=decl.line, col=decl.col))
            elif isinstance(decl, VarDeclStmt):
                if decl.type_name:
                    self._check_type_usage(decl.type_name)
                scope: Dict[str, str] = {}
                new_val = self._transform_expr(decl.value, scope, {}, decl.type_name) if decl.value else None
                transformed_regular_decls.append(VarDeclStmt(
                    name=decl.name,
                    type_name=normalize_type_name(decl.type_name),
                    value=new_val,
                    is_mut=decl.is_mut,
                    line=decl.line,
                    col=decl.col
                ))
            elif isinstance(decl, TestDecl):
                new_body = self._transform_block(decl.body, {}, {}, "void")
                transformed_regular_decls.append(TestDecl(name=decl.name, body=new_body, line=decl.line, col=decl.col))
            else:
                transformed_regular_decls.append(decl)

        # Pass 3: Process worklist until all dependencies are instantiated
        while self.worklist:
            kind, tname, args = self.worklist.pop(0)
            if kind == "struct":
                self._instantiate_struct(tname, args)
            elif kind == "kind":
                self._instantiate_kind(tname, args)
            elif kind == "func":
                self._instantiate_func(tname, args)

        # Pass 4: Assemble final declarations list
        final_decls: List[Decl] = []
        # Emit instantiated kinds
        for kd in self.instantiated_kinds.values():
            final_decls.append(kd)
        # Emit instantiated structs
        for sd in self.instantiated_structs.values():
            final_decls.append(sd)
        # Emit regular declarations
        for rd in transformed_regular_decls:
            final_decls.append(rd)
        # Emit instantiated functions
        for fd in self.instantiated_funcs.values():
            final_decls.append(fd)

        return Program(declarations=final_decls)

    def _canon_type(self, t: Optional[str]) -> Optional[str]:
        if not t:
            return t
        ptr = 0
        base = t
        while base.startswith("@"):
            ptr += 1
            base = base[1:]
        if base not in self.type_aliases:
            return t
        return ("@" * ptr) + self.type_aliases[base]

    def _canonicalize_program_types(self, program: Program):
        for decl in program.declarations:
            if isinstance(decl, DataDecl):
                for f in decl.fields:
                    f.type_name = self._canon_type(f.type_name)
            elif isinstance(decl, KindDecl):
                for v in decl.variants:
                    if v.payload_type:
                        v.payload_type = self._canon_type(v.payload_type)
                    if v.fields:
                        for f in v.fields:
                            f.type_name = self._canon_type(f.type_name)
            elif isinstance(decl, FunctionDecl):
                for p in decl.params:
                    p.type_name = self._canon_type(p.type_name)
                decl.return_type = self._canon_type(decl.return_type)
                self._canonicalize_stmt_types(decl.body)
            elif isinstance(decl, ExternDecl):
                for p in decl.params:
                    p.type_name = self._canon_type(p.type_name)
                decl.return_type = self._canon_type(decl.return_type)
            elif isinstance(decl, VarDeclStmt):
                decl.type_name = self._canon_type(decl.type_name)
                self._canonicalize_expr_types(decl.value)

    def _canonicalize_stmt_types(self, stmt: Optional[Stmt]):
        if stmt is None:
            return
        if isinstance(stmt, BlockStmt):
            for s in stmt.statements:
                self._canonicalize_stmt_types(s)
        elif isinstance(stmt, VarDeclStmt):
            stmt.type_name = self._canon_type(stmt.type_name)
            self._canonicalize_expr_types(stmt.value)
        elif isinstance(stmt, AssignStmt):
            self._canonicalize_expr_types(stmt.target)
            self._canonicalize_expr_types(stmt.value)
        elif isinstance(stmt, IfStmt):
            self._canonicalize_expr_types(stmt.condition)
            self._canonicalize_stmt_types(stmt.then_branch)
            self._canonicalize_stmt_types(stmt.else_branch)
        elif isinstance(stmt, LoopStmt):
            self._canonicalize_expr_types(stmt.start_expr)
            self._canonicalize_expr_types(stmt.end_expr)
            self._canonicalize_expr_types(stmt.step_expr)
            self._canonicalize_expr_types(stmt.expr)
            self._canonicalize_stmt_types(stmt.body)
        elif isinstance(stmt, ZoneStmt):
            self._canonicalize_stmt_types(stmt.body)
        elif isinstance(stmt, DeferStmt):
            self._canonicalize_stmt_types(stmt.statement)
        elif isinstance(stmt, MatchStmt):
            self._canonicalize_expr_types(stmt.expr)
            for c in stmt.cases:
                for v in c.values:
                    self._canonicalize_expr_types(v)
                self._canonicalize_stmt_types(c.body)
        elif isinstance(stmt, ExprStmt):
            self._canonicalize_expr_types(stmt.expr)
        elif isinstance(stmt, ReturnStmt):
            self._canonicalize_expr_types(stmt.value)

    def _canonicalize_expr_types(self, expr: Optional[Expr]):
        if expr is None:
            return
        if isinstance(expr, CastExpr):
            expr.target_type = self._canon_type(expr.target_type)
            self._canonicalize_expr_types(expr.expr)
        elif isinstance(expr, UnaryExpr):
            self._canonicalize_expr_types(expr.operand)
        elif isinstance(expr, AddressOf):
            self._canonicalize_expr_types(expr.operand)
        elif isinstance(expr, DerefExpr):
            self._canonicalize_expr_types(expr.operand)
        elif isinstance(expr, BinaryExpr):
            self._canonicalize_expr_types(expr.left)
            self._canonicalize_expr_types(expr.right)
        elif isinstance(expr, MemberAccess):
            self._canonicalize_expr_types(expr.target)
        elif isinstance(expr, IndexExpr):
            self._canonicalize_expr_types(expr.target)
            self._canonicalize_expr_types(expr.index)
        elif isinstance(expr, StructLiteral):
            for _, val in expr.field_inits:
                self._canonicalize_expr_types(val)
        elif isinstance(expr, ShelfLiteral):
            for a in expr.args:
                self._canonicalize_expr_types(a)
        elif isinstance(expr, MapLiteral):
            for a in expr.keys:
                self._canonicalize_expr_types(a)
            for a in expr.vals:
                self._canonicalize_expr_types(a)
        elif isinstance(expr, CallExpr):
            self._canonicalize_expr_types(expr.callee)
            for a in expr.args:
                self._canonicalize_expr_types(a)
        elif isinstance(expr, VariantExpr):
            for a in expr.args:
                self._canonicalize_expr_types(a)
        elif isinstance(expr, AnonFuncExpr):
            for p in expr.params:
                p.type_name = self._canon_type(p.type_name)
            expr.return_type = self._canon_type(expr.return_type)
            self._canonicalize_stmt_types(expr.body)

    def _check_type_usage(self, type_str: Optional[str]):
        if not type_str:
            return
        prefix, base, args = parse_type_signature(type_str)
        if args:
            # Check nested arguments first
            for a in args:
                self._check_type_usage(a)
            # Normalize args before requesting
            norm_args = tuple(normalize_type_name(a) or a for a in args)
            if base in self.generic_structs:
                self.request_instantiation("struct", base, norm_args)
            elif base in self.generic_kinds:
                self.request_instantiation("kind", base, norm_args)

    def _instantiate_struct(self, name: str, args: Tuple[str, ...]):
        template = self.generic_structs[name]
        mangled_name = f"{name}_{'_'.join(mangle_type_name(a) for a in args)}"
        if mangled_name in self.instantiated_structs:
            return

        subst = dict(zip(template.type_params or [], args))
        new_fields: List[Field] = []
        for f in template.fields:
            ftype = subst_type(f.type_name, subst)
            self._check_type_usage(ftype)
            norm_ftype = normalize_type_name(ftype) or "i32"
            new_fields.append(Field(name=f.name, type_name=norm_ftype, line=f.line, col=f.col, default_expr=f.default_expr))

        decl = DataDecl(name=mangled_name, fields=new_fields, line=template.line, col=template.col)
        decl.align = template.align
        decl.packed = template.packed
        self.instantiated_structs[mangled_name] = decl
        f_map = {f.name: f.type_name for f in new_fields}
        self.struct_fields[mangled_name] = set(f_map.keys())
        self.struct_field_types[mangled_name] = f_map

    def _instantiate_kind(self, name: str, args: Tuple[str, ...]):
        template = self.generic_kinds[name]
        mangled_name = f"{name}_{'_'.join(mangle_type_name(a) for a in args)}"
        if mangled_name in self.instantiated_kinds:
            return

        subst = dict(zip(template.type_params or [], args))
        new_variants: List[VariantDecl] = []
        for v in template.variants:
            ptype = subst_type(v.payload_type, subst) if v.payload_type else None
            if ptype:
                self._check_type_usage(ptype)
                ptype = normalize_type_name(ptype)
            vf = None
            if v.fields:
                vf = []
                for f in v.fields:
                    ftype = subst_type(f.type_name, subst)
                    self._check_type_usage(ftype)
                    vf.append(Field(name=f.name, type_name=normalize_type_name(ftype) or "i32", line=f.line, col=f.col, default_expr=f.default_expr))
            new_variants.append(VariantDecl(
                name=v.name,
                line=v.line,
                col=v.col,
                discriminant=v.discriminant,
                payload_type=ptype,
                fields=vf
            ))

        decl = KindDecl(name=mangled_name, variants=new_variants, line=template.line, col=template.col)
        self.instantiated_kinds[mangled_name] = decl

    def _instantiate_func(self, name: str, args: Tuple[str, ...]):
        template = self.generic_funcs[name]
        mangled_name = f"{name}_{'_'.join(mangle_type_name(a) for a in args)}"
        if mangled_name in self.instantiated_funcs:
            return

        subst = dict(zip(template.type_params or [], args))
        new_params: List[Param] = []
        for p in template.params:
            ptype = subst_type(p.type_name, subst)
            self._check_type_usage(ptype)
            new_params.append(Param(name=p.name, type_name=normalize_type_name(ptype) or "i32", line=p.line, col=p.col))

        ret_type = subst_type(template.return_type, subst)
        if ret_type:
            self._check_type_usage(ret_type)
            ret_type = normalize_type_name(ret_type)

        self.func_return_types[mangled_name] = ret_type or "void"
        self.func_param_types[mangled_name] = [p.type_name for p in new_params]

        scope: Dict[str, str] = {p.name: p.type_name for p in new_params}
        new_body = self._transform_block(template.body, scope, subst, ret_type)

        decl = FunctionDecl(
            name=mangled_name,
            params=new_params,
            return_type=ret_type,
            body=new_body,
            line=template.line,
            col=template.col,
            is_operator=getattr(template, 'is_operator', False),
            operator_symbol=getattr(template, 'operator_symbol', None)
        )
        if decl.is_operator:
            param_types = tuple(p.type_name for p in new_params)
            self.op_overloads[(decl.operator_symbol, len(param_types), param_types)] = mangled_name
        self.instantiated_funcs[mangled_name] = decl

    def _transform_function(self, fn: FunctionDecl, subst: Dict[str, str]) -> FunctionDecl:
        new_params: List[Param] = []
        for p in fn.params:
            ptype = subst_type(p.type_name, subst)
            self._check_type_usage(ptype)
            new_params.append(Param(name=p.name, type_name=normalize_type_name(ptype) or "i32", line=p.line, col=p.col))

        ret_type = subst_type(fn.return_type, subst)
        if ret_type:
            self._check_type_usage(ret_type)
            ret_type = normalize_type_name(ret_type)

        scope: Dict[str, str] = {p.name: p.type_name for p in new_params}
        new_body = self._transform_block(fn.body, scope, subst, ret_type)

        return FunctionDecl(
            name=fn.name,
            params=new_params,
            return_type=ret_type,
            body=new_body,
            line=fn.line,
            col=fn.col,
            is_operator=getattr(fn, 'is_operator', False),
            operator_symbol=getattr(fn, 'operator_symbol', None)
        )

    def _transform_block(self, block: BlockStmt, scope: Dict[str, str], subst: Dict[str, str], current_ret_type: Optional[str]) -> BlockStmt:
        inner_scope = dict(scope)
        new_stmts: List[Stmt] = []
        for stmt in block.statements:
            new_stmts.append(self._transform_stmt(stmt, inner_scope, subst, current_ret_type))
        return BlockStmt(statements=new_stmts, line=block.line, col=block.col)

    def _transform_stmt(self, stmt: Stmt, scope: Dict[str, str], subst: Dict[str, str], current_ret_type: Optional[str]) -> Stmt:
        if isinstance(stmt, VarDeclStmt):
            vtype = subst_type(stmt.type_name, subst)
            if vtype:
                self._check_type_usage(vtype)
                vtype = normalize_type_name(vtype)
            new_val = self._transform_expr(stmt.value, scope, subst, vtype) if stmt.value else None
            inferred_type = vtype or (self._infer_expr_type(new_val, scope) if new_val else "i32")
            scope[stmt.name] = inferred_type
            return VarDeclStmt(
                name=stmt.name,
                type_name=vtype,
                value=new_val,
                is_mut=stmt.is_mut,
                line=stmt.line,
                col=stmt.col
            )
        elif isinstance(stmt, AssignStmt):
            new_target = self._transform_expr(stmt.target, scope, subst, None)
            target_type = self._infer_expr_type(new_target, scope)
            new_val = self._transform_expr(stmt.value, scope, subst, target_type)
            if stmt.op in ("+=", "-=", "*=", "/=", "%="):
                base_op = stmt.op[:-1]
                val_type = self._infer_expr_type(new_val, scope)
                match_fn, arg0, arg1 = self._find_binary_op_overload(base_op, new_target, target_type, new_val, val_type)
                if match_fn:
                    call_node = CallExpr(callee=Identifier(name=match_fn, line=stmt.line, col=stmt.col), args=[arg0, arg1], line=stmt.line, col=stmt.col)
                    return AssignStmt(target=new_target, op="=", value=call_node, line=stmt.line, col=stmt.col)
            return AssignStmt(target=new_target, op=stmt.op, value=new_val, line=stmt.line, col=stmt.col)
        elif isinstance(stmt, ReturnStmt):
            new_val = self._transform_expr(stmt.value, scope, subst, current_ret_type) if stmt.value else None
            return ReturnStmt(value=new_val, line=stmt.line, col=stmt.col)
        elif isinstance(stmt, ExprStmt):
            return ExprStmt(expr=self._transform_expr(stmt.expr, scope, subst, None), line=stmt.line, col=stmt.col)
        elif isinstance(stmt, IfStmt):
            new_cond = self._transform_expr(stmt.condition, scope, subst, "bool")
            new_then = self._transform_block(stmt.then_branch, scope, subst, current_ret_type)
            new_else = None
            if stmt.else_branch:
                if isinstance(stmt.else_branch, BlockStmt):
                    new_else = self._transform_block(stmt.else_branch, scope, subst, current_ret_type)
                else:
                    new_else = self._transform_stmt(stmt.else_branch, scope, subst, current_ret_type)
            return IfStmt(condition=new_cond, then_branch=new_then, else_branch=new_else, line=stmt.line, col=stmt.col)
        elif isinstance(stmt, LoopStmt):
            if stmt.of_expr is not None:
                # 5.2: `loop v of coll` — transform the source, then register the
                # iterator with the shelf's ELEMENT type in the loop scope.
                # Slice 4: the optional index binding is a usize scope entry.
                new_of = self._transform_expr(stmt.of_expr, scope, subst, None)
                of_t = self._infer_expr_type(new_of, scope)
                loop_scope = dict(scope)
                if stmt.iterator:
                    loop_scope[stmt.iterator] = _shelf_elem_of(of_t) or "i32"
                if stmt.of_index:
                    loop_scope[stmt.of_index] = "usize"
                new_body = self._transform_block(stmt.body, loop_scope, subst, current_ret_type)
                return LoopStmt(
                    iterator=stmt.iterator,
                    start_expr=None,
                    end_expr=None,
                    of_expr=new_of,
                    of_index=stmt.of_index,
                    body=new_body,
                    line=stmt.line,
                    col=stmt.col
                )
            new_start = self._transform_expr(stmt.start_expr, scope, subst, "i32") if stmt.start_expr else None
            new_end = self._transform_expr(stmt.end_expr, scope, subst, "i32") if stmt.end_expr else None
            new_step = self._transform_expr(stmt.step_expr, scope, subst, "i32") if stmt.step_expr else None
            new_expr = self._transform_expr(stmt.expr, scope, subst, None) if stmt.expr else None
            loop_scope = dict(scope)
            if stmt.iterator:
                loop_scope[stmt.iterator] = "i32"
            new_body = self._transform_block(stmt.body, loop_scope, subst, current_ret_type)
            return LoopStmt(
                iterator=stmt.iterator,
                start_expr=new_start,
                end_expr=new_end,
                step_expr=new_step,
                body=new_body,
                is_inclusive=stmt.is_inclusive,
                expr=new_expr,
                is_count=stmt.is_count,
                line=stmt.line,
                col=stmt.col
            )
        elif isinstance(stmt, ZoneStmt):
            new_size = self._transform_expr(stmt.size, scope, subst, "usize") if stmt.size else None
            return ZoneStmt(
                body=self._transform_block(stmt.body, scope, subst, current_ret_type),
                size=new_size,
                line=stmt.line,
                col=stmt.col
            )
        elif isinstance(stmt, DeferStmt):
            return DeferStmt(statement=self._transform_stmt(stmt.statement, scope, subst, current_ret_type), line=stmt.line, col=stmt.col)
        elif isinstance(stmt, BlockStmt):
            return self._transform_block(stmt, scope, subst, current_ret_type)
        elif isinstance(stmt, MatchStmt):
            new_subj = self._transform_expr(stmt.expr, scope, subst, None)
            subj_type = self._infer_expr_type(new_subj, scope)
            new_cases: List[MatchCase] = []
            for c in stmt.cases:
                case_scope = dict(scope)
                new_vals = [self._transform_expr(v, scope, subst, subj_type) for v in c.values]
                # If variant binding is present, register variable in case scope
                if not c.is_default and new_vals and isinstance(new_vals[0], VariantExpr):
                    v_expr = new_vals[0]
                    # Locate variant payload type
                    kname = v_expr.kind_name or subj_type
                    kdecl = self.instantiated_kinds.get(kname)
                    if kdecl and v_expr.args:
                        vdecl = next((vd for vd in kdecl.variants if vd.name == v_expr.variant_name), None)
                        if vdecl:
                            if vdecl.payload_type and len(v_expr.args) == 1 and isinstance(v_expr.args[0], Identifier):
                                case_scope[v_expr.args[0].name] = vdecl.payload_type
                            elif vdecl.fields and len(v_expr.args) == len(vdecl.fields):
                                for f_decl, arg in zip(vdecl.fields, v_expr.args):
                                    if isinstance(arg, Identifier):
                                        case_scope[arg.name] = f_decl.type_name
                new_body = self._transform_block(c.body, case_scope, subst, current_ret_type)
                new_cases.append(MatchCase(values=new_vals, is_default=c.is_default, body=new_body, line=c.line, col=c.col))
            return MatchStmt(expr=new_subj, cases=new_cases, line=stmt.line, col=stmt.col)
        return stmt

    def _transform_expr(self, expr: Expr, scope: Dict[str, str], subst: Dict[str, str], expected_type: Optional[str]) -> Expr:
        if isinstance(expr, VariantExpr):
            kname = expr.kind_name
            if not kname and expected_type:
                kname = expected_type.lstrip("@")
            if kname:
                kname = subst_type(kname, subst)
                self._check_type_usage(kname)
                kname = normalize_type_name(kname)
            new_args = [self._transform_expr(a, scope, subst, None) for a in expr.args]
            return VariantExpr(kind_name=kname, variant_name=expr.variant_name, args=new_args, line=expr.line, col=expr.col)
        elif isinstance(expr, StructLiteral):
            sname = subst_type(expr.struct_name, subst) or expr.struct_name
            if sname in self.generic_structs and expected_type:
                # Type was inferred from expected_type (e.g. let b: Box[i32] = Box{ value: 42 })
                sname = expected_type.lstrip("@")
            self._check_type_usage(sname)
            sname = normalize_type_name(sname) or sname
            new_inits = [(fname, self._transform_expr(fval, scope, subst, None)) for fname, fval in expr.field_inits]
            return StructLiteral(struct_name=sname, field_inits=new_inits, line=expr.line, col=expr.col)
        elif isinstance(expr, CastExpr):
            ttype = subst_type(expr.target_type, subst)
            self._check_type_usage(ttype)
            ttype = normalize_type_name(ttype) or "i32"
            return CastExpr(expr=self._transform_expr(expr.expr, scope, subst, ttype), target_type=ttype, line=expr.line, col=expr.col)
        elif isinstance(expr, CallExpr):
            is_ufcs = False
            first_arg = None
            fn_name = None

            if isinstance(expr.callee, MemberAccess):
                member = expr.callee.member
                target = expr.callee.target
                is_module = isinstance(target, Identifier) and target.name in {"io", "mem", "fs", "str", "sys", "math", "time", "os", "simd"}
                is_kind = isinstance(target, Identifier) and (target.name in self.kind_names or target.name in self.generic_kinds)
                if not is_module and not is_kind:
                    # Check if target struct has this field
                    t_type_raw = self._infer_expr_type(target, scope)
                    clean_t = t_type_raw.lstrip("@")
                    prefix, base, _ = parse_type_signature(clean_t)
                    fields = self.struct_fields.get(clean_t) or self.struct_fields.get(base) or self.struct_fields.get(clean_t.split('_')[0], set())
                    if member not in fields:
                        # Check if member is a known function
                        if member in self.func_param_types or member in self.generic_funcs:
                            is_ufcs = True
                            fn_name = member
                            # Transform target
                            new_target = self._transform_expr(target, scope, subst, None)
                            target_type = self._infer_expr_type(new_target, scope)
                            p0_type = None
                            if member in self.func_param_types and self.func_param_types[member]:
                                p0_type = self.func_param_types[member][0]
                            elif member in self.generic_funcs and self.generic_funcs[member].params:
                                p0_type = self.generic_funcs[member].params[0].type_name

                            # Auto-reference or auto-dereference
                            if p0_type and p0_type.startswith("@") and not target_type.startswith("@"):
                                first_arg = AddressOf(operand=new_target, line=new_target.line, col=new_target.col)
                            elif p0_type and not p0_type.startswith("@") and target_type.startswith("@"):
                                first_arg = DerefExpr(operand=new_target, line=new_target.line, col=new_target.col)
                            else:
                                first_arg = new_target

            if is_ufcs:
                new_args = [first_arg] + [self._transform_expr(a, scope, subst, None) for a in expr.args]
                new_callee = Identifier(name=fn_name, line=expr.callee.line, col=expr.callee.col)
            else:
                new_args = [self._transform_expr(a, scope, subst, None) for a in expr.args]
                new_callee = self._transform_expr(expr.callee, scope, subst, None)

            # mem.alloc / mem.heap_alloc's first argument is a type symbol
            # (`@T`), not a value: it must be substituted through the same
            # generic map as every other type name (gaps §4.1 adjacency).
            if (isinstance(expr.callee, MemberAccess)
                    and isinstance(expr.callee.target, Identifier)
                    and expr.callee.target.name == "mem"
                    and expr.callee.member in ("alloc", "heap_alloc")
                    and expr.args and isinstance(expr.args[0], AddressOf)
                    and isinstance(expr.args[0].operand, Identifier)):
                raw_type = expr.args[0].operand.name
                concrete_type = subst_type(raw_type, subst) or raw_type
                self._check_type_usage(concrete_type)
                concrete_type = normalize_type_name(concrete_type) or concrete_type
                new_args[0] = AddressOf(
                    operand=Identifier(name=concrete_type, line=expr.args[0].operand.line, col=expr.args[0].operand.col),
                    line=expr.args[0].line, col=expr.args[0].col)

            if isinstance(new_callee, Identifier) and new_callee.name in self.generic_funcs:
                template_name = new_callee.name
                template = self.generic_funcs[template_name]
                concrete_args: List[str] = []

                if expr.type_args:
                    for ta in expr.type_args:
                        substed = subst_type(ta, subst) or ta
                        self._check_type_usage(substed)
                        concrete_args.append(normalize_type_name(substed) or substed)
                else:
                    # Infer from argument types!
                    inferred: Dict[str, str] = {}
                    for param, arg in zip(template.params, new_args):
                        arg_type = self._infer_expr_type(arg, scope)
                        self._unify_types(param.type_name, arg_type, template.type_params or [], inferred)
                    for tp in (template.type_params or []):
                        if tp in inferred:
                            self._check_type_usage(inferred[tp])
                            concrete_args.append(normalize_type_name(inferred[tp]) or inferred[tp])
                        else:
                            raise Exception(f"Could not infer generic type parameter '{tp}' in call to '{template_name}' at line {expr.line}")

                norm_args_tuple = tuple(concrete_args)
                mangled_name = f"{template_name}_{'_'.join(mangle_type_name(a) for a in concrete_args)}"
                self.request_instantiation("func", template_name, norm_args_tuple)
                new_callee = Identifier(name=mangled_name, line=new_callee.line, col=new_callee.col)

            return CallExpr(callee=new_callee, args=new_args, line=expr.line, col=expr.col)
        elif isinstance(expr, MemberAccess):
            return MemberAccess(target=self._transform_expr(expr.target, scope, subst, None), member=expr.member, line=expr.line, col=expr.col)
        elif isinstance(expr, ShelfLiteral):
            new_args = [self._transform_expr(a, scope, subst, None) for a in expr.args]
            new_lit = ShelfLiteral(args=new_args, line=expr.line, col=expr.col)
            new_lit.elem_type = expr.elem_type
            new_lit.is_heap = expr.is_heap   # slice 10: the storage modifier rides the clone
            return new_lit
        elif isinstance(expr, MapLiteral):
            new_keys = [self._transform_expr(a, scope, subst, None) for a in expr.keys]
            new_vals = [self._transform_expr(a, scope, subst, None) for a in expr.vals]
            new_lit = MapLiteral(keys=new_keys, vals=new_vals, line=expr.line, col=expr.col)
            new_lit.kv_type = expr.kv_type
            return new_lit
        elif isinstance(expr, RingLiteral):
            new_args = [self._transform_expr(a, scope, subst, None) for a in expr.args]
            new_lit = RingLiteral(args=new_args, line=expr.line, col=expr.col)
            new_lit.elem_type = expr.elem_type
            return new_lit
        elif isinstance(expr, BitsetLiteral):
            new_args = [self._transform_expr(a, scope, subst, None) for a in expr.args]
            return BitsetLiteral(args=new_args, line=expr.line, col=expr.col)
        elif isinstance(expr, IndexExpr):
            return IndexExpr(target=self._transform_expr(expr.target, scope, subst, None), index=self._transform_expr(expr.index, scope, subst, "usize"), line=expr.line, col=expr.col)
        elif isinstance(expr, DerefExpr):
            return DerefExpr(operand=self._transform_expr(expr.operand, scope, subst, None), line=expr.line, col=expr.col)
        elif isinstance(expr, AddressOf):
            return AddressOf(operand=self._transform_expr(expr.operand, scope, subst, None), line=expr.line, col=expr.col)
        elif isinstance(expr, BinaryExpr):
            new_left = self._transform_expr(expr.left, scope, subst, None)
            new_right = self._transform_expr(expr.right, scope, subst, None)
            l_type = self._infer_expr_type(new_left, scope)
            r_type = self._infer_expr_type(new_right, scope)
            match_fn, arg0, arg1 = self._find_binary_op_overload(expr.op, new_left, l_type, new_right, r_type)
            if match_fn:
                return CallExpr(callee=Identifier(name=match_fn, line=expr.line, col=expr.col), args=[arg0, arg1], line=expr.line, col=expr.col)
            return BinaryExpr(left=new_left, op=expr.op, right=new_right, line=expr.line, col=expr.col)
        elif isinstance(expr, UnaryExpr):
            new_operand = self._transform_expr(expr.operand, scope, subst, None)
            op_type = self._infer_expr_type(new_operand, scope)
            match_fn, arg0 = self._find_unary_op_overload(expr.op, new_operand, op_type)
            if match_fn:
                return CallExpr(callee=Identifier(name=match_fn, line=expr.line, col=expr.col), args=[arg0], line=expr.line, col=expr.col)
            return UnaryExpr(op=expr.op, operand=new_operand, line=expr.line, col=expr.col)
        elif isinstance(expr, AnonFuncExpr):
            new_params = [Param(name=p.name, type_name=subst_type(p.type_name, subst) or p.type_name, line=p.line, col=p.col) for p in expr.params]
            new_ret = subst_type(expr.return_type, subst) or expr.return_type
            inner_scope = scope.copy()
            for p in new_params:
                inner_scope[p.name] = p.type_name
            new_body = self._transform_stmt(expr.body, inner_scope, subst, new_ret)
            return AnonFuncExpr(params=new_params, return_type=new_ret, body=new_body, line=expr.line, col=expr.col)
        return expr

    def _infer_expr_type(self, expr: Optional[Expr], scope: Dict[str, str]) -> str:
        if not expr:
            return "i32"
        if isinstance(expr, AnonFuncExpr):
            return f"act({', '.join(p.type_name for p in expr.params)}) -> {expr.return_type}"
        if isinstance(expr, IntLiteral):
            return expr.type_name if expr.type_name else "i32"
        if isinstance(expr, FloatLiteral):
            return expr.type_name if expr.type_name else "f32"
        if isinstance(expr, StringLiteral):
            return "string"
        if isinstance(expr, BoolLiteral):
            return "bool"
        if isinstance(expr, NullLiteral):
            return "@void"
        if isinstance(expr, Identifier):
            return scope.get(expr.name, "i32")
        if isinstance(expr, StructLiteral):
            return expr.struct_name
        if isinstance(expr, VariantExpr):
            return expr.kind_name or "i32"
        if isinstance(expr, CastExpr):
            return expr.target_type
        if isinstance(expr, AddressOf):
            sub = self._infer_expr_type(expr.operand, scope)
            return f"@{sub}"
        if isinstance(expr, DerefExpr):
            sub = self._infer_expr_type(expr.operand, scope)
            return sub[1:] if sub.startswith("@") else sub
        if isinstance(expr, MemberAccess):
            target_type = self._infer_expr_type(expr.target, scope)
            clean_type = target_type.lstrip("@")
            if clean_type in ("f32x4", "i32x4"):
                if expr.member in ("x", "y", "z", "w"):
                    return "f32" if clean_type == "f32x4" else "i32"
                raise ValueError(f"unknown SIMD vector member '{expr.member}' (available: x, y, z, w)")
            prefix, base, _ = parse_type_signature(clean_type)
            f_types = self.struct_field_types.get(clean_type) or self.struct_field_types.get(base) or self.struct_field_types.get(clean_type.split('_')[0], {})
            if expr.member in f_types:
                return f_types[expr.member]
            # 5.2: shelf property reads (len = usize); others are downstream errors
            if _shelf_elem_of(target_type) is not None and expr.member == "len":
                return "usize"
            # 5.2 slice 6: map reads mirror the shelf surface best-effort
            map_kv = _map_kv_of(target_type)
            if map_kv is not None and expr.member == "len":
                return "usize"
            return "i32"
        if isinstance(expr, MapLiteral):
            # 5.2 slice 6: best-effort only (the strict key/value ladders run
            # in the checker/codegen); generic T unification needs the type
            if expr.kv_type:
                return expr.kv_type
            if not expr.keys:
                return "i32"
            key_types = [self._infer_expr_type(a, scope) for a in expr.keys]
            val_types = [self._infer_expr_type(a, scope) for a in expr.vals]
            k0 = key_types[0]
            if all(t == k0 for t in key_types):
                if all(t == val_types[0] for t in val_types):
                    return f"Map[{k0}, {val_types[0]}]"
                if all(t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES for t in val_types) and any(t in DYN_FLOAT_TYPES for t in val_types):
                    return f"Map[{k0}, f64]"
                return f"Map[{k0}, dyn]"
            return "Map[dyn, dyn]"  # best-effort for heterogeneous keys (checker rejects)
        if isinstance(expr, ShelfLiteral):
            # 5.2: homogeneous best-effort inference (generic T unification);
            # the strict check runs in the checker/codegen. Slice 10: a heap
            # literal's inferred spelling carries the `heap ` prefix.
            heap_pfx = "heap " if expr.is_heap else ""
            if expr.elem_type:
                return f"{heap_pfx}shelf[{expr.elem_type}]"
            if not expr.args:
                return "i32"
            # 5.2 slice 2: the ladder runs over ALL args (a heterogeneous
            # literal inside a generic must not infer from the first element)
            types = [self._infer_expr_type(a, scope) for a in expr.args]
            first = types[0]
            if all(t == first for t in types):
                return f"{heap_pfx}shelf[{first}]"
            if all(t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES for t in types) and any(t in DYN_FLOAT_TYPES for t in types):
                return f"{heap_pfx}shelf[f64]"
            return f"{heap_pfx}shelf[dyn]"
        if isinstance(expr, RingLiteral):
            # 5.2 slice 9: best-effort ring ladder (no dyn arm — a mixed
            # non-numeric generic literal is a checker-rejected corner)
            if expr.elem_type:
                return f"ring[{expr.elem_type}]"
            if not expr.args:
                return "i32"
            types = [self._infer_expr_type(a, scope) for a in expr.args]
            first = types[0]
            if all(t == first for t in types):
                return f"ring[{first}]"
            if all(t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES for t in types) and any(t in DYN_FLOAT_TYPES for t in types):
                return "ring[f64]"
            second = next((t for t in types if t != first), first)
            return f"ring[{first}]"  # checker rejects the mix upstream
        if isinstance(expr, BitsetLiteral):
            return "bitset"
        if isinstance(expr, IndexExpr):
            # 5.2: shelf element reads; slice 6: map value reads
            target_type = self._infer_expr_type(expr.target, scope)
            clean_type = target_type.lstrip("@")
            if clean_type in ("f32x4", "i32x4"):
                return "f32" if clean_type == "f32x4" else "i32"
            elem = _shelf_elem_of(target_type)
            if elem is not None:
                return elem
            map_kv = _map_kv_of(target_type)
            if map_kv is not None:
                return map_kv[1]
            return "i32"
        if isinstance(expr, CallExpr):
            if isinstance(expr.callee, Identifier):
                if expr.callee.name in ("f32x4", "f32x4_splat"):
                    return "f32x4"
                if expr.callee.name in ("i32x4", "i32x4_splat"):
                    return "i32x4"
                if expr.callee.name in self.func_return_types:
                    return self.func_return_types[expr.callee.name]
                if expr.callee.name in self.generic_funcs:
                    return self.generic_funcs[expr.callee.name].return_type or "void"
            elif isinstance(expr.callee, MemberAccess):
                # 5.2: shelf receiver calls — put/insert are void, take/
                # remove_at yield the element, sorted() a new shelf[elem]
                recv = self._infer_expr_type(expr.callee.target, scope)
                elem = _shelf_elem_of(recv)
                if elem is not None:
                    if expr.callee.member in ("put", "insert"):
                        return "void"
                    if expr.callee.member in ("take", "remove_at"):
                        return elem
                    if expr.callee.member == "sorted":
                        return f"shelf[{elem}]"
                # 5.2 slice 6/7: map receiver calls — put void / get, get_or,
                # take value / has bool
                map_kv = _map_kv_of(recv)
                if map_kv is not None:
                    if expr.callee.member == "put":
                        return "void"
                    if expr.callee.member in ("get", "get_or", "take"):
                        return map_kv[1]
                    if expr.callee.member == "has":
                        return "bool"
                if isinstance(expr.callee.target, Identifier) and expr.callee.target.name == "simd":
                    if expr.callee.member == "dot":
                        return "f32"
                    if expr.callee.member == "sqrt":
                        return "f32x4"
                    if expr.callee.member in ("min", "max"):
                        if expr.args:
                            return self._infer_expr_type(expr.args[0], scope)
                        return "f32x4"
                if expr.callee.member in self.func_return_types:
                    return self.func_return_types[expr.callee.member]
                if expr.callee.member in self.generic_funcs:
                    return self.generic_funcs[expr.callee.member].return_type or "void"
        if isinstance(expr, BinaryExpr):
            if expr.op in ("==", "!=", "<", "<=", ">", ">="):
                return "bool"
            l_t = self._infer_expr_type(expr.left, scope)
            r_t = self._infer_expr_type(expr.right, scope)
            if l_t in ("f32x4", "i32x4") or r_t in ("f32x4", "i32x4"):
                return l_t
            match_fn, _, _ = self._find_binary_op_overload(expr.op, expr.left, l_t, expr.right, r_t)
            if match_fn and match_fn in self.func_return_types:
                return self.func_return_types[match_fn]
            return l_t
        if isinstance(expr, UnaryExpr):
            if expr.op in ("!", "not"):
                return "bool"
            op_t = self._infer_expr_type(expr.operand, scope)
            if op_t in ("f32x4", "i32x4"):
                return op_t
            match_fn, _ = self._find_unary_op_overload(expr.op, expr.operand, op_t)
            if match_fn and match_fn in self.func_return_types:
                return self.func_return_types[match_fn]
            return op_t
        return "i32"

    def _find_binary_op_overload(self, op: str, left: Expr, l_type: str, right: Expr, r_type: str) -> Tuple[Optional[str], Optional[Expr], Optional[Expr]]:
        key = (op, 2, (l_type, r_type))
        if key in self.op_overloads:
            return self.op_overloads[key], left, right

        for (cand_op, cand_len, cand_params), fn_name in self.op_overloads.items():
            if cand_op == op and cand_len == 2:
                p0_t, p1_t = cand_params
                a0 = self._adapt_arg(left, l_type, p0_t)
                a1 = self._adapt_arg(right, r_type, p1_t)
                if a0 is not None and a1 is not None:
                    return fn_name, a0, a1

        if (op, 2) in self.generic_op_overloads:
            template = self.generic_op_overloads[(op, 2)]
            try:
                inferred: Dict[str, str] = {}
                self._unify_types(template.params[0].type_name, l_type, template.type_params or [], inferred)
                self._unify_types(template.params[1].type_name, r_type, template.type_params or [], inferred)
                concrete_args = []
                for tp in (template.type_params or []):
                    if tp in inferred:
                        self._check_type_usage(inferred[tp])
                        concrete_args.append(normalize_type_name(inferred[tp]) or inferred[tp])
                    else:
                        return None, None, None
                norm_args_tuple = tuple(concrete_args)
                mangled_name = f"{template.name}_{'_'.join(mangle_type_name(a) for a in concrete_args)}"
                self.request_instantiation("func", template.name, norm_args_tuple)
                p0_t = normalize_type_name(subst_type(template.params[0].type_name, inferred))
                p1_t = normalize_type_name(subst_type(template.params[1].type_name, inferred))
                a0 = self._adapt_arg(left, l_type, p0_t)
                a1 = self._adapt_arg(right, r_type, p1_t)
                if a0 is not None and a1 is not None:
                    return mangled_name, a0, a1
            except Exception:
                pass

        return None, None, None

    def _find_unary_op_overload(self, op: str, operand: Expr, op_type: str) -> Tuple[Optional[str], Optional[Expr]]:
        key = (op, 1, (op_type,))
        if key in self.op_overloads:
            return self.op_overloads[key], operand

        for (cand_op, cand_len, cand_params), fn_name in self.op_overloads.items():
            if cand_op == op and cand_len == 1:
                p0_t = cand_params[0]
                a0 = self._adapt_arg(operand, op_type, p0_t)
                if a0 is not None:
                    return fn_name, a0

        if (op, 1) in self.generic_op_overloads:
            template = self.generic_op_overloads[(op, 1)]
            try:
                inferred: Dict[str, str] = {}
                self._unify_types(template.params[0].type_name, op_type, template.type_params or [], inferred)
                concrete_args = []
                for tp in (template.type_params or []):
                    if tp in inferred:
                        self._check_type_usage(inferred[tp])
                        concrete_args.append(normalize_type_name(inferred[tp]) or inferred[tp])
                    else:
                        return None, None
                norm_args_tuple = tuple(concrete_args)
                mangled_name = f"{template.name}_{'_'.join(mangle_type_name(a) for a in concrete_args)}"
                self.request_instantiation("func", template.name, norm_args_tuple)
                p0_t = normalize_type_name(subst_type(template.params[0].type_name, inferred))
                a0 = self._adapt_arg(operand, op_type, p0_t)
                if a0 is not None:
                    return mangled_name, a0
            except Exception:
                pass

        return None, None

    def _adapt_arg(self, expr: Expr, actual_t: str, formal_t: str) -> Optional[Expr]:
        if actual_t == formal_t:
            return expr
        if formal_t == f"@{actual_t}":
            return AddressOf(operand=expr, line=expr.line, col=expr.col)
        if actual_t == f"@{formal_t}":
            return DerefExpr(operand=expr, line=expr.line, col=expr.col)
        return None

    def _unify_types(self, formal: str, actual: str, type_params: List[str], inferred: Dict[str, str]):
        if formal in type_params:
            inferred[formal] = actual
            return
        if formal.startswith("@") and actual.startswith("@"):
            self._unify_types(formal[1:], actual[1:], type_params, inferred)
            return
        p_prefix, p_base, p_args = parse_type_signature(formal)
        a_prefix, a_base, a_args = parse_type_signature(actual)
        if p_base == a_base and len(p_args) == len(a_args):
            for pa, aa in zip(p_args, a_args):
                self._unify_types(pa, aa, type_params, inferred)
        elif not a_args and a_base.startswith(p_base + "_"):
            suffix = a_base[len(p_base) + 1:]
            actual_args = suffix.split("_")
            if len(p_args) == len(actual_args):
                for pa, aa in zip(p_args, actual_args):
                    self._unify_types(pa, aa, type_params, inferred)
