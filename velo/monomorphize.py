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
    Identifier, MemberAccess, IndexExpr, DerefExpr, StructLiteral, CastExpr, CallExpr, AddressOf, BinaryExpr, UnaryExpr, AnonFuncExpr
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


def normalize_type_name(t: Optional[str]) -> Optional[str]:
    """
    Normalizes a generic type signature in AST to its mangled concrete name, preserving leading '@'.
    E.g. '@Box[i32]' -> '@Box_i32', 'Option[string]' -> 'Option_string', 'i32' -> 'i32'.
    """
    if not t:
        return t
    prefix, base, args = parse_type_signature(t)
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

    def request_instantiation(self, kind: str, template_name: str, args: Tuple[str, ...]):
        key = (kind, template_name, args)
        if key not in self.seen_instantiations:
            self.seen_instantiations.add(key)
            self.worklist.append(key)

    def monomorphize(self, program: Program) -> Program:
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
            else:
                regular_decls.append(decl)

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
                    new_fields.append(Field(name=f.name, type_name=normalize_type_name(f.type_name) or "i32", line=f.line, col=f.col))
                transformed_regular_decls.append(DataDecl(name=decl.name, fields=new_fields, line=decl.line, col=decl.col))
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
                            vf.append(Field(name=f.name, type_name=normalize_type_name(f.type_name) or "i32", line=f.line, col=f.col))
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
            new_fields.append(Field(name=f.name, type_name=norm_ftype, line=f.line, col=f.col))

        decl = DataDecl(name=mangled_name, fields=new_fields, line=template.line, col=template.col)
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
                    vf.append(Field(name=f.name, type_name=normalize_type_name(ftype) or "i32", line=f.line, col=f.col))
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
            col=template.col
        )
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
            col=fn.col
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
            target_type = self._infer_expr_type(stmt.target, scope)
            new_target = self._transform_expr(stmt.target, scope, subst, None)
            new_val = self._transform_expr(stmt.value, scope, subst, target_type)
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
            return ZoneStmt(body=self._transform_block(stmt.body, scope, subst, current_ret_type), line=stmt.line, col=stmt.col)
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
                is_module = isinstance(target, Identifier) and target.name in {"io", "mem", "fs", "str", "sys"}
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
        elif isinstance(expr, IndexExpr):
            return IndexExpr(target=self._transform_expr(expr.target, scope, subst, None), index=self._transform_expr(expr.index, scope, subst, "usize"), line=expr.line, col=expr.col)
        elif isinstance(expr, DerefExpr):
            return DerefExpr(operand=self._transform_expr(expr.operand, scope, subst, None), line=expr.line, col=expr.col)
        elif isinstance(expr, AddressOf):
            return AddressOf(operand=self._transform_expr(expr.operand, scope, subst, None), line=expr.line, col=expr.col)
        elif isinstance(expr, BinaryExpr):
            return BinaryExpr(left=self._transform_expr(expr.left, scope, subst, None), op=expr.op, right=self._transform_expr(expr.right, scope, subst, None), line=expr.line, col=expr.col)
        elif isinstance(expr, UnaryExpr):
            return UnaryExpr(op=expr.op, operand=self._transform_expr(expr.operand, scope, subst, None), line=expr.line, col=expr.col)
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
            prefix, base, _ = parse_type_signature(clean_type)
            f_types = self.struct_field_types.get(clean_type) or self.struct_field_types.get(base) or self.struct_field_types.get(clean_type.split('_')[0], {})
            if expr.member in f_types:
                return f_types[expr.member]
            return "i32"
        if isinstance(expr, CallExpr):
            if isinstance(expr.callee, Identifier):
                if expr.callee.name in self.func_return_types:
                    return self.func_return_types[expr.callee.name]
                if expr.callee.name in self.generic_funcs:
                    return self.generic_funcs[expr.callee.name].return_type or "void"
            elif isinstance(expr.callee, MemberAccess):
                if expr.callee.member in self.func_return_types:
                    return self.func_return_types[expr.callee.member]
                if expr.callee.member in self.generic_funcs:
                    return self.generic_funcs[expr.callee.member].return_type or "void"
        if isinstance(expr, BinaryExpr):
            return self._infer_expr_type(expr.left, scope)
        return "i32"

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
