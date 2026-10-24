import re
from typing import List, Optional, Tuple, Dict, Any
from velo.ast_nodes import (
    Program, Decl, UseStmt, FunctionDecl, ExternDecl, Param, BlockStmt, DataDecl, Field, KindDecl, VariantDecl,
    Stmt, ExprStmt, ReturnStmt, BreakStmt, ContinueStmt, VarDeclStmt, AssignStmt, IfStmt, LoopStmt, ZoneStmt, DeferStmt,
    MatchCase, MatchStmt,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral, VariantExpr,
    Identifier, MemberAccess, IndexExpr, DerefExpr, StructLiteral, CastExpr, CallExpr, AddressOf, BinaryExpr, UnaryExpr, AnonFuncExpr,
    ShelfLiteral, MapLiteral, RingLiteral, BitsetLiteral,
    TypeAliasDecl
)
from velo.monomorphize import Monomorphizer, parse_act_type, mangle_act_type, DYN_INT_TYPES, DYN_FLOAT_TYPES

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
    # 5.2 slice 2: the shelf[dyn] tagged box (VeloDyn lives in velo_runtime.h)
    "dyn": "VeloDyn",
}

# 5.1 String Processing Library: sys.str intrinsics backed by velo_str_*
# runtime helpers (velo_runtime.h). Legacy str.len keeps its inline strlen
# lowering; every other member is compile-checked by _str_expect (mirrored
# by Stage 2's src/analysis/str_checks.vl — identical wording) and emits a
# single runtime helper call so each argument is evaluated exactly once.
STR_RUNTIME_MEMBERS = {
    "contains": 2,
    "starts_with": 2,
    "ends_with": 2,
    "index_of": 2,
    "trim": 1,
    "replace": 3,
    "to_upper": 1,
    "to_lower": 1,
    "concat": 2,
    "split": 2,
}

_STR_SIGS = {
    "contains": ": (string s, string sub)",
    "starts_with": ": (string s, string prefix)",
    "ends_with": ": (string s, string suffix)",
    "index_of": ": (string s, string needle)",
    "trim": ": (string s)",
    "replace": ": (string s, string old, string new)",
    "to_upper": ": (string s)",
    "to_lower": ": (string s)",
    "concat": ": (string a, string b)",
    "split": ": (string s, string delimiter)",
}

# 5.3 Math Library: sys.math is compiled directly onto C99 libm — no runtime
# helpers, so the arithmetic cannot diverge between stages (the shared
# velo_runtime.h carries #include <math.h> once). Constants are bare member
# properties emitted as full-precision decimal literals (WRAPS THE DIGITS in
# parens); the digit strings must stay character-identical with Stage 2's
# src/analysis/math_checks.vl math_constant_tables. Function members are
# compile-checked by _math_expect (arg spellings widen to (double); bool /
# string / collection args reject with the mirrored wording).
MATH_CONSTANTS = {
    "PI": "3.14159265358979323846",
    "TAU": "6.28318530717958647692",
    "RAD2DEG": "57.2957795130823208768",
    "DEG2RAD": "0.01745329251994329577",
}

MATH_CALLS = {
    "sqrt": (1, ": (f64 x)"),
    "pow": (2, ": (f64 base, f64 exp)"),
    "cbrt": (1, ": (f64 x)"),
    "sin": (1, ": (f64 x)"),
    "cos": (1, ": (f64 x)"),
    "tan": (1, ": (f64 x)"),
    "atan2": (2, ": (f64 y, f64 x)"),
    "acos": (1, ": (f64 x)"),
    "asin": (1, ": (f64 x)"),
    "exp": (1, ": (f64 x)"),
    "log": (1, ": (f64 x)"),
    "log2": (1, ": (f64 x)"),
    # 5.3 slice 4: the utility family — abs/min/max dispatch on their arg
    # spells; floor/ceil/round/clamp/lerp are plain f64 libm lowers.
    "abs": (1, ": (f64 x)"),
    "min": (2, ": (f64 a, f64 b)"),
    "max": (2, ": (f64 a, f64 b)"),
    "floor": (1, ": (f64 x)"),
    "ceil": (1, ": (f64 x)"),
    "round": (1, ": (f64 x)"),
    "clamp": (3, ": (f64 v, f64 lo, f64 hi)"),
    "lerp": (3, ": (f64 a, f64 b, f64 t)"),
}

# 5.5 High-Resolution Clock & Timing (sys.time): closed-namespace call set.
# now/delta are zero-arg i64 microsecond clocks; sleep_ms takes ONE int
# duration (floats reject). Mirrored by stage 2's src/analysis/time_checks.vl
# and velo/runtime/velo_runtime.h helpers — both stages must reject the same
# programs with the same words and emit the same helper call bytes.
TIME_CALLS = {
    "now": 0,
    "delta": 0,
    "sleep_ms": 1,
}
# 0-ary members carry no sig tail (a ": ()" would read wrong); the sig only
# decorates the sleep_ms arity wall. Must stay character-identical with
# stage 2's time_member_sig.
TIME_SIGS = {
    "sleep_ms": ": (i64 ms)",
}
TIME_FUNCS_TEXT = "now, delta, sleep_ms"

def time_member_result_type(member: str, arg_types: List[str]) -> str:
    """5.5: result spell per time member (args validated elsewhere)."""
    if member == "sleep_ms":
        return "void"
    if member in ("now", "delta"):
        return "i64"
    return ""


# 5.4 Extended File System & OS Primitives (sys.os): closed-namespace call
# set. args reads the full argv (argv[0] included); get_env/set_env ride the
# environment surface; exit terminates with a process code (direct C exit).
# Mirrored by stage 2's src/analysis/os_checks.vl — both stages must reject
# the same programs with the same words and emit the same helper bytes.
OS_CALLS = {
    "args": 0,
    "get_env": 1,
    "set_env": 2,
    "exit": 1,
}
# 0-ary members carry no sig tail; the sig only decorates the arity walls.
# Must stay character-identical with stage 2's os_member_sig.
OS_SIGS = {
    "get_env": ": (string key)",
    "set_env": ": (string key, string val)",
    "exit": ": (i64 code)",
}
OS_FUNCS_TEXT = "args, exit, get_env, set_env"
# every leading N argument of these members is a STRING (keys/values); the
# remaining members take ints. S1 os members are homogeneous per member —
# a mixed-arg member would need per-position wording (sheet: open design).
OS_STRING_ARGS = {
    "get_env": 1,
    "set_env": 2,
}
OS_INT_ARGS = {
    "exit": 1,
}

def os_member_result_type(member: str) -> str:
    """5.4 S1: result spell per os member (empty = unknown member)."""
    if member == "args":
        return "shelf[string]"
    if member == "get_env":
        return "string"
    if member == "set_env":
        return "bool"
    if member == "exit":
        return "void"
    return ""


# 5.4 slice 2 — sys.fs metadata family: the fs namespace goes CLOSED. The
# six legacy members (old §4.2) migrate into the checked umbrella with
# their result spells preserved exactly; the six new members ride the rt
# helpers (velo_fs_is_dir/is_file/create_dir/create_dir_all/copy/rename).
# Mirrored by stage 2's src/analysis/fs_checks.vl — both stages must
# reject the same programs with the same words and emit the same helper
# bytes. Member listing order = ship order (legacy six first, then the
# metadata family).
FS_CALLS = {
    "read_file": 1,
    "write_file": 2,
    "size": 1,
    "exists": 1,
    "remove": 1,
    "remove_file": 1,
    "is_dir": 1,
    "is_file": 1,
    "create_dir": 1,
    "create_dir_all": 1,
    "copy": 2,
    "rename": 2,
}
# Must stay character-identical with stage 2's fs_member_sig.
FS_SIGS = {
    "read_file": ": (string path)",
    "write_file": ": (string path, string contents)",
    "size": ": (string path)",
    "exists": ": (string path)",
    "remove": ": (string path)",
    "remove_file": ": (string path)",
    "is_dir": ": (string path)",
    "is_file": ": (string path)",
    "create_dir": ": (string path)",
    "create_dir_all": ": (string path)",
    "copy": ": (string src, string dst)",
    "rename": ": (string src, string dst)",
}
FS_FUNCS_TEXT = "read_file, write_file, size, exists, remove, remove_file, is_dir, is_file, create_dir, create_dir_all, copy, rename"

def fs_member_result_type(member: str) -> str:
    """5.4 S2: result spell per fs member (empty = unknown member). The
    legacy six keep their exact old spells."""
    if member == "read_file":
        return "string"
    if member == "size":
        return "usize"
    if member in ("write_file", "exists", "remove", "remove_file",
                  "is_dir", "is_file", "create_dir", "create_dir_all",
                  "copy", "rename"):
        return "bool"
    return ""


# 5.3 slice 4: the math RESULT type stops being constant-f64 and becomes
# arg-aware. Floats lift everything to f64; abs mirrors its argument's int
# spell back (float args pin to f64); min/max keep the same-spell int type
# and lift mixed widths to i64 (self widening-ladder spirit). Two ladder
# consumers here (_infer_raw_velo_type + _resolve_expr_type) and Stage 2's
# math_abs_ret / math_minmax_ret acts must compute the same spread.
def math_member_result_type(member: str, arg_types: List[str]) -> str:
    if member == "abs":
        t = arg_types[0] if arg_types else "f64"
        return "f64" if t in DYN_FLOAT_TYPES else t
    if member in ("min", "max"):
        if any(t in DYN_FLOAT_TYPES for t in arg_types):
            return "f64"
        if len(arg_types) == 2 and arg_types[0] == arg_types[1]:
            return arg_types[0]
        return "i64"
    return "f64"


# 5.2 Dynamic Collections: the shelf surface is compile-checked per member
# (mirrored by Stage 2's src/analysis/shelf_checks.vl — identical wording)
# and lowered onto the runtime's single VeloShelf struct + velo_shelf_* helpers.
SHELF_INT_TYPES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize", "isize"}

# 5.2 slice 8: the concrete compare lattice — numeric, string, bool. Mixed
# families reject; pointer/shelf/struct sides return None (pointer identity
# compares like `p == q` stay untouched by the wall).
def _compare_family(t: Optional[str]) -> Optional[str]:
    if t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES:
        return "n"
    if t == "string":
        return "s"
    if t == "bool":
        return "b"
    return None

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
        self.current_scope_mut: Dict[str, bool] = {}
        self.global_scope_mut: Dict[str, bool] = {}
        self.current_function: Optional[FunctionDecl] = None
        self.defer_stack: List[List[Stmt]] = []
        self.zone_counter = 0
        self.match_counter = 0
        self.fresh_counter = 0
        # 5.2 slice 11: the --unsafe-shelf-index knob — lowers shelf index
        # READS to the unguarded data-pointer read (writes stay guarded)
        self.unsafe_shelf_index = False

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

        # 5.2: every shelf[T] maps onto the runtime's single VeloShelf struct
        if type_str.startswith("shelf[") or type_str == "shelf[]":
            return "VeloShelf" + ("*" * pointer_count)
        if type_str == "shelf":
            raise ValueError("a bare 'shelf' needs an element type: use shelf[T]")
        # 5.2 slice 10: `heap shelf[T]` — the same layout, heap-backed payload
        if type_str.lstrip("@").startswith("heap shelf["):
            return "VeloShelf" + ("*" * pointer_count)
        if type_str.lstrip("@") == "heap shelf":
            raise ValueError("a bare 'heap shelf' needs an element type: use heap shelf[T]")
        # 5.2 slice 6: every Map[K, V] maps onto the runtime's single VeloMap
        if type_str.startswith("Map["):
            return "VeloMap" + ("*" * pointer_count)
        if type_str == "Map":
            raise ValueError("a bare 'Map' needs key and value types: use Map[K, V]")
        # 5.2 slice 9: ring[T] maps onto the runtime's single VeloRing struct;
        # `bitset` is the first bare collection type (VeloBitset)
        if type_str.startswith("ring["):
            return "VeloRing" + ("*" * pointer_count)
        if type_str == "ring":
            raise ValueError("a bare 'ring' needs an element type: use ring[T]")
        if type_str == "bitset":
            return "VeloBitset" + ("*" * pointer_count)

        base_c_type = TYPE_MAP.get(type_str, type_str)
        return base_c_type + ("*" * pointer_count)

    def _fresh_name(self, prefix: str) -> str:
        self.fresh_counter += 1
        return f"_velo_{prefix}{self.fresh_counter}"

    def _shelf_elem_type(self, type_str: Optional[str]) -> Optional[str]:
        """Extracts the element type from a `shelf[T]`, `@shelf[T]`, or
        (slice 10) `heap shelf[T]` type string, or None otherwise."""
        if not type_str:
            return None
        raw = type_str.lstrip("@").strip()
        if raw.startswith("heap shelf[") and raw.endswith("]"):
            raw = raw[5:]   # strip the heap modifier; the shelf spell follows
        if raw.startswith("shelf[") and raw.endswith("]"):
            inner = raw[6:-1].strip()
            return inner if inner else None
        return None

    # ------------------------------------------------------------------
    # 5.2 slice 6 — Map[K, V] core. Mirrored by the Stage 2 checker
    # (src/analysis/map_checks.vl) and emitter (map_gen.vl) with identical
    # wording; the engine + fatal repr live in velo_runtime.h (VeloMap).
    # ------------------------------------------------------------------

    def is_map_type(self, type_str: Optional[str]) -> bool:
        """True for `Map[K, V]` (or `@Map[K, V]`). Bare `Map` reads as a map
        ONLY at lowering time, where it raises the bare-type error."""
        if not type_str:
            return False
        raw = type_str.lstrip("@").strip()
        return raw.startswith("Map[")

    def _map_kv(self, type_str: Optional[str]) -> Optional[Tuple[str, str]]:
        """Extracts (key_type, value_type) from a `Map[K, V]` spelling, or
        None. The comma carrier scan is bracket-depth aware — value slots
        may be child maps (Map[i32, Map[string, i64]])."""
        if not type_str:
            return None
        raw = type_str.lstrip("@").strip()
        if not raw.startswith("Map[") or not raw.endswith("]"):
            return None
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
                    # the key-family gate fires at first touch — every map
                    # spelling with an illegal key family rejects here, at
                    # declares, uses, and borrows alike (mirrored in stage 2)
                    err = self._map_family_error(key)
                    if err:
                        raise ValueError(err)
                    return key, val
        return None

    def _map_family_error(self, key: Optional[str]) -> Optional[str]:
        """None when `key` is in the pinned key families (10 int widths +
        bool + string); else the uniform compile reject. Floats stand on
        NaN being unordered; struct/dyn/@T rows are unordered object rows."""
        if key in DYN_INT_TYPES or key in ("string", "bool"):
            return None
        return f"map keys must be integer, bool, or string (got {key})"

    def _map_key_slot_c(self, key: str) -> str:
        """The C slot type for key bytes: string keys store a pointer; every
        other pinned family stores its scalar value."""
        return "const char*" if key == "string" else self._map_type(key)

    def _map_value_ladder(self, types: List[str]) -> str:
        """The value slot of a map literal mirrors the shelf element ladder
        exactly: homogeneous unchanged; all-numeric with a float widens to
        f64; mixed int widths stay a strict differ; any other mix lowers to
        dyn (boxability wording reused verbatim from the shelf machinery)."""
        first = types[0]
        if first == "@void":
            raise ValueError("map values cannot be null (use a @T pointer value)")
        for t in types:
            if t == "@void":
                raise ValueError("map values cannot be null (use a @T pointer value)")
        mixed = any(t != first for t in types)
        if not mixed:
            return first
        if all(t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES for t in types):
            if any(t in DYN_FLOAT_TYPES for t in types):
                return "f64"
            second = next(t for t in types if t != first)
            raise ValueError(f"map literal value types differ: {first} vs {second}")
        for t in types:
            err = self._dyn_boxable_error(t)
            if err:
                raise ValueError(err)
        return "dyn"

    def _infer_map_literal_type(self, lit: "MapLiteral") -> str:
        """Infers the `Map[K, V]` spelling of a map literal. Empty literals
        only infer when an annotation established kv_type beforehand."""
        if lit.kv_type:
            return lit.kv_type
        if not lit.keys:
            raise ValueError("cannot infer key and value types of empty map literal — annotate it (e.g. let m: Map[i32, string] = map[])")
        key_types = [self._infer_raw_velo_type(k) for k in lit.keys]
        val_types = [self._infer_raw_velo_type(v) for v in lit.vals]
        key0 = key_types[0]
        for kt in key_types[1:]:
            if kt != key0:
                raise ValueError(f"map literal key types differ: {key0} vs {kt}")
        err = self._map_family_error(key0)
        if err:
            raise ValueError(err)
        val = self._map_value_ladder(val_types)
        return f"Map[{key0}, {val}]"

    def _check_map_annotation(self, decl_type: Optional[str], value: Optional[Expr]) -> None:
        """5.2 slice 6 contract: annotated map declarations — an empty literal
        borrows BOTH slots from the annotation's `Map[K, V]` spelling; a
        non-empty literal must match it exactly (one combined message).
        Mirrored by the Stage 2 checker's check_map_annotation."""
        if not isinstance(value, MapLiteral) or not decl_type or not decl_type.startswith("Map["):
            return
        ann_kv = self._map_kv(decl_type)
        if not value.keys:
            if ann_kv is not None:
                value.kv_type = decl_type
            return
        if ann_kv is None:
            return
        lit_kv = self._map_kv(self._infer_map_literal_type(value))
        if lit_kv is not None and lit_kv != ann_kv:
            raise ValueError(f"map literal type Map[{lit_kv[0]}, {lit_kv[1]}] does not match annotation Map[{ann_kv[0]}, {ann_kv[1]}]")

    def _check_map_value(self, member: str, val: str, got: str) -> None:
        """Value-slot contract shared by put and subscript writes: exact V,
        dyn values box any boxable element (void/null reject; the boxability
        wording is the shelf machinery's, reused verbatim)."""
        if val == "dyn":
            if got == "unknown":
                return  # the argument itself already failed to infer
            if got == "void":
                raise ValueError(f"shelf[dyn] {member}: cannot box a void value")
            if got == "@void":
                raise ValueError("map values cannot be null (use a @T pointer value)")
            err = self._dyn_boxable_error(got)
            if err:
                raise ValueError(err)
        elif got != val:
            raise ValueError(f"map value mismatch: expected {val} (got {got})")

    def _map_expect(self, member: str, target_expr: Expr, args: List[Expr], kv: Optional[Tuple[str, str]]) -> None:
        """5.2 compile-checks map member calls (put/get/has and the slice-7
        get_or/take twins) and the subscript forms. Mirrored by the Stage 2
        checker — both stages reject the same programs with the same
        messages. `kv` carries the receiver's (K, V) when known (None flows
        to mono like shelves do)."""
        if member not in ("put", "get", "has", "get_or", "take"):
            raise ValueError(f"unknown map member '{member}' (put, get, has, len, get_or, take are available)")
        expected_args = {"put": 2, "get": 1, "has": 1, "get_or": 2, "take": 1}[member]
        arg_names = {"put": "(map m, key, value)", "get": "(map m, key)", "has": "(map m, key)",
                     "get_or": "(map m, key, default)", "take": "(map m, key)"}
        if len(args) != expected_args:
            raise ValueError(f"map.{member} expects exactly {expected_args} argument{'s' * (expected_args != 1)}: {arg_names[member]}")
        if kv is not None and member in ("put", "get", "has", "get_or", "take"):
            key_t = self._resolve_expr_type(args[0])
            if key_t is not None and key_t != kv[0]:
                raise ValueError(f"map key mismatch: expected {kv[0]} (got {key_t})")
            if member in ("put", "get_or"):
                # 5.2 slice 7: the get_or default rides the put value-slot
                # gates verbatim ("put" keeps the dyn-void wording identical).
                got = self._thread_arg_type(args[1])
                self._check_map_value("put", kv[1], got)
        if member in ("put", "take"):
            root = self._shelf_root_binding(target_expr)
            if root is not None and not self.current_scope_mut.get(root, False):
                if member == "put":
                    raise ValueError("cannot put into a map held by a let (declare with mut)")
                raise ValueError("cannot take from a map held by a let (declare with mut)")

    def _emit_map_literal(self, lit: "MapLiteral") -> str:
        """5.2 slice 6: lowers `map[k0: v0, ...]` into a GCC statement
        expression so the literal can live in any value position. Each key
        and each value is bound exactly once into a typed temp (left-to-right
        evaluation order guaranteed)."""
        raw = self._infer_map_literal_type(lit)
        kv = self._map_kv(raw)
        if kv is None:
            raise ValueError("cannot infer key and value types of empty map literal — annotate it (e.g. let m: Map[i32, string] = map[])")
        key_c = self._map_key_slot_c(kv[0])
        val_c = self._map_type(kv[1])
        kstring = "true" if kv[0] == "string" else "false"
        recv = self._fresh_name("mpt_")
        parts = [
            f"VeloMap {recv} = {{0}}",
            f"velo_map_init(&{recv}, (usize)sizeof({key_c}), {kstring}, (usize)sizeof({val_c}))",
        ]
        for k, v in zip(lit.keys, lit.vals):
            k_slot = self._fresh_name("mk_")
            v_slot = self._fresh_name("mv_")
            k_code = self._emit_expression(k)
            v_code = self._emit_expression(v)
            if kv[1] == "dyn":
                v_raw = self._infer_raw_velo_type(v)
                if v_raw != "dyn":
                    v_code = self._emit_dyn_box(v_raw, v_code, v)
            parts.append(
                f"{{ {key_c} {k_slot} = ({k_code}); {val_c} {v_slot} = ({v_code}); "
                f"velo_map_put(&{recv}, (const void*)(&{k_slot}), (const void*)(&{v_slot})); }}"
            )
        parts.append(f"{recv}")
        return "({ " + "; ".join(parts) + "; })"

    # ------------------------------------------------------------------
    # 5.2 slice 9 — ring[T] + bitset. Mirrored by Stage 2's
    # src/analysis/ring_checks.vl + src/analysis/bitset_checks.vl and the
    # src/backend/ring_gen.vl / bitset_gen.vl emitters (identical wording);
    # the runtime fatals live in velo_runtime.h.
    # ------------------------------------------------------------------
    def _ring_elem_type(self, type_str: Optional[str]) -> Optional[str]:
        """Extracts the element type from a `ring[T]` (or `@ring[T]`) type
        string, or None when the type is not a ring."""
        if not type_str:
            return None
        raw = type_str.lstrip("@").strip()
        if raw.startswith("ring[") and raw.endswith("]"):
            inner = raw[5:-1].strip()
            return inner or None
        return None

    def _ring_elem_error(self, raw: Optional[str]) -> Optional[str]:
        """Returns the compile error for a non-family ring element, or None.
        The shelf families minus dyn (the tagged-box machinery is shelf-
        specific; ring[dyn] is a later slice)."""
        if raw is None:
            return None
        if raw in DYN_INT_TYPES or raw in DYN_FLOAT_TYPES or raw in ("bool", "string"):
            return None
        if raw.startswith("@"):
            return None
        if raw.startswith("shelf[") or raw.startswith("Map["):
            return None
        if raw in self.struct_defs:
            return None
        return f"ring element type {raw} is not supported — use a @{raw} pointer element"

    def _ring_literal_elem(self, value: "RingLiteral") -> str:
        """The ring literal element ladder (pre-slice-2 shelf spirit, no dyn
        arm): homogeneous unchanged, all-numeric-with-float widens to f64,
        ANY other mix is one strict differ error."""
        if value.elem_type:
            return value.elem_type
        if not value.args:
            raise ValueError("cannot infer element type of empty ring literal — annotate it (e.g. let r: ring[i32] = ring[])")
        types = [self._infer_raw_velo_type(a) for a in value.args]
        first = types[0]
        mixed = any(t != first for t in types)
        if not mixed:
            err = self._ring_elem_error(first)
            if err:
                raise ValueError(err)
            return first
        second = next(t for t in types if t != first)
        if all(t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES for t in types):
            if any(t in DYN_FLOAT_TYPES for t in types):
                return "f64"
        raise ValueError(f"ring literal element types differ: {first} vs {second}")

    def _check_ring_annotation(self, decl_type: Optional[str], value: Optional[Expr]) -> None:
        """5.2 slice 9 contract: annotated ring declarations — an empty
        literal borrows the annotation's element (validated against the ring
        families); a non-empty literal must match it. Mirrored by the Stage 2
        checker's check_ring_annotation."""
        if not isinstance(value, RingLiteral) or not decl_type:
            return
        if not decl_type.lstrip("@").startswith("ring["):
            return
        ann_elem = self._ring_elem_type(decl_type)
        if ann_elem is not None:
            err = self._ring_elem_error(ann_elem)
            if err:
                raise ValueError(err)
        if not value.args:
            if ann_elem is not None:
                value.elem_type = ann_elem
            return
        if ann_elem is None:
            return
        lit_elem = self._ring_literal_elem(value)
        if lit_elem != ann_elem:
            raise ValueError(f"ring literal element type ring[{lit_elem}] does not match annotation {decl_type}")

    def _check_bitset_annotation(self, decl_type: Optional[str], value: Optional[Expr]) -> None:
        """5.2 slice 9: a bitset literal under a non-bitset annotation rejects
        (`bitset[]` needs no annotation at all — no element ladder exists)."""
        if not isinstance(value, BitsetLiteral) or not decl_type:
            return
        if decl_type.lstrip("@") != "bitset":
            raise ValueError(f"bitset literal does not match annotation {decl_type}")
        value.pinned = True

    BITSET_MEMBERS = ("set", "clear", "toggle", "has", "count", "first_unset", "and", "or_with", "xor_with", "flip")

    def _bitset_index_type(self, arg: Expr, member: str) -> str:
        it = self._resolve_expr_type(arg)
        if it not in DYN_INT_TYPES:
            raise ValueError(f"bitset index must be an integer (got {it})")
        return it

    def _bitset_expect(self, member: str, target_expr: Expr, args: List[Expr]) -> None:
        """5.2 slice 9 compile-checks bitset member calls. Mirrored by the
        Stage 2 checker — both stages reject the same programs with the same
        messages."""
        if member not in self.BITSET_MEMBERS:
            raise ValueError(f"unknown bitset member '{member}' (set, clear, toggle, has, count, first_unset, and, or_with, xor_with, flip are available)")
        if member in ("set", "clear", "toggle"):
            if len(args) != 1:
                raise ValueError(f"bitset.{member} expects exactly 1 argument: (bitset b, index)")
            self._bitset_index_type(args[0], member)
        elif member == "has":
            if len(args) != 1:
                raise ValueError(f"bitset.has expects exactly 1 argument: (bitset b, index)")
            self._bitset_index_type(args[0], member)
        elif member in ("count", "first_unset", "flip"):
            if args:
                raise ValueError(f"bitset.{member} takes no arguments")
        else:  # and / or_with / xor_with
            if len(args) != 1:
                raise ValueError(f"bitset.{member} expects exactly 1 argument: (bitset b, other)")
            got = self._resolve_expr_type(args[0])
            if got != "unknown" and got.lstrip("@") != "bitset":
                raise ValueError(f"bitset.{member} expects a bitset argument (got {got})")
        if member in ("set", "clear", "toggle", "and", "or_with", "xor_with", "flip"):
            root = self._shelf_root_binding(target_expr)
            if root is not None and not self.current_scope_mut.get(root, False):
                raise ValueError("cannot mutate a bitset held by a let (declare with mut)")

    def _ring_expect(self, member: str, target_expr: Expr, args: List[Expr], elem: Optional[str]) -> None:
        """5.2 slice 9 compile-checks ring member calls (put/pop/peek).
        `elem` carries the receiver's element when known (None flows to mono
        like shelves do)."""
        if member not in ("put", "pop", "peek"):
            raise ValueError(f"unknown ring member '{member}' (put, pop, peek, len are available)")
        expected = {"put": 1, "pop": 0, "peek": 0}[member]
        if len(args) != expected:
            if expected == 0:
                # the zero-arity verb template (the shelf.take shape)
                raise ValueError(f"ring.{member} takes no arguments")
            raise ValueError("ring.put expects exactly 1 argument: (ring r, element value)")
        if member == "put" and elem is not None:
            got = self._thread_arg_type(args[0])
            if got == "unknown":
                return  # the argument itself already failed to infer
            if got != elem:
                raise ValueError(f"ring.put element mismatch: expected {elem} (got {got})")
        if member in ("put", "pop"):
            root = self._shelf_root_binding(target_expr)
            if root is not None and not self.current_scope_mut.get(root, False):
                if member == "put":
                    raise ValueError("cannot put into a ring held by a let (declare with mut)")
                raise ValueError("cannot pop from a ring held by a let (declare with mut)")

    def _emit_ring_literal(self, lit: "RingLiteral") -> str:
        """5.2 slice 9: lowers `ring[...]` into a GCC statement expression —
        a fresh VeloRing header plus one typed slot per element (left-to-right
        evaluation order guaranteed)."""
        elem = self._ring_literal_elem(lit)
        elem_c = self._map_type(elem)
        recv = self._fresh_name("rng_")
        parts = [f"VeloRing {recv} = {{0}}"]
        for a in lit.args:
            slot = self._fresh_name("rel_")
            val_code = self._emit_expression(a)
            parts.append(
                f"{{ {elem_c} {slot} = ({val_code}); "
                f"velo_ring_put(&{recv}, (const void*)(&{slot}), (usize)sizeof({elem_c})); }}"
            )
        parts.append(f"{recv}")
        return "({ " + "; ".join(parts) + "; })"

    def _emit_bitset_literal(self, lit: "BitsetLiteral") -> str:
        """5.2 slice 9: lowers `bitset[...]` — a fresh VeloBitset header plus
        one runtime set() per integer element (negative elements ride the
        runtime OOB fatal)."""
        recv = self._fresh_name("bst_")
        parts = [f"VeloBitset {recv} = {{0}}"]
        for a in lit.args:
            self._bitset_index_type(a, "set")
            code = self._emit_expression(a)
            parts.append(f"velo_bitset_set(&{recv}, (int64_t)({code}))")
        parts.append(f"{recv}")
        return "({ " + "; ".join(parts) + "; })"

    # ------------------------------------------------------------------
    # 5.2 slice 2 — shelf[dyn] tagged boxes. Mirrored by Stage 2's
    # src/analysis/shelf_checks.vl + src/backend/shelf_gen.vl (identical
    # wording); the unbox fatal lives in velo_runtime.h (velo_dyn_expect).
    # ------------------------------------------------------------------
    DYN_GATE_ERROR = "shelf[dyn] unbox: raw dyn values must be cast (as) to a concrete type first"

    def _dyn_boxable_error(self, raw: Optional[str]) -> Optional[str]:
        """Returns the compile error for a non-boxable element type, or None."""
        if raw == "@void":
            return "shelf elements cannot be null (use a @T pointer element)"
        if raw in DYN_INT_TYPES or raw in DYN_FLOAT_TYPES:
            return None
        if raw in ("bool", "string", "dyn"):
            return None
        if raw and raw.startswith("@"):
            return None  # any @T pointer boxes (unchecked shape at unbox)
        if raw and (raw.startswith("shelf[") or raw == "shelf"):
            return None
        return f"shelf[dyn] element type {raw} cannot be boxed — use a @{raw} pointer element"

    def _emit_dyn_box(self, raw: str, code: str, expr: Optional[Expr] = None) -> str:
        """Boxes one element value (already emitted as `code`) into a VeloDyn
        literal by its source Velo type. Raw dyn values pass through whole.
        5.2 slice 8: u64-typed sources box the U64 tag (full uint64 payload,
        no impl-defined i64 cast); an integer literal above the i64 range
        promotes too — the callers hand over the expr node for that check."""
        if raw == "u64":
            return f"(VeloDyn){{ .tag = VELO_DYN_U64, .as = {{ .u64 = (uint64_t)({code}) }} }}"
        if raw in DYN_INT_TYPES:
            if isinstance(expr, IntLiteral) and expr.value > 9223372036854775807:
                return f"(VeloDyn){{ .tag = VELO_DYN_U64, .as = {{ .u64 = (uint64_t)({code}) }} }}"
            return f"(VeloDyn){{ .tag = VELO_DYN_I64, .as = {{ .i64 = (int64_t)({code}) }} }}"
        if raw in DYN_FLOAT_TYPES:
            return f"(VeloDyn){{ .tag = VELO_DYN_F64, .as = {{ .f64 = (double)({code}) }} }}"
        if raw == "bool":
            return f"(VeloDyn){{ .tag = VELO_DYN_BOOL, .as = {{ .b = ({code}) ? 1 : 0 }} }}"
        if raw == "string":
            return f"(VeloDyn){{ .tag = VELO_DYN_STR, .as = {{ .s = (const char*)({code}) }} }}"
        if raw.startswith("@"):
            return f"(VeloDyn){{ .tag = VELO_DYN_PTR, .as = {{ .p = (void*)({code}) }} }}"
        if raw.startswith("shelf[") or raw == "shelf":
            return f"(VeloDyn){{ .tag = VELO_DYN_CHILD, .as = {{ .child = ({code}) }} }}"
        return code  # raw dyn pass-through (tag preserved)

    def _emit_dyn_unbox(self, code: str, target: str) -> str:
        """Unboxes a raw dyn value via an explicit `as` cast to a concrete
        type. Family targets share one ring: int widths read off the I64 box,
        f32/f64 off F64, bool/string, @T pointers (unchecked shape), and
        shelf[T] child copies (`@shelf` is rejected — the header copy would
        dangle). Empty target 'dyn' is an identity pass-through."""
        base = target.strip()
        if base == "dyn":
            return code
        # 5.2 slice 10: `as @shelf[T]` is RE-OPENED — the PTR box holds a real
        # pointer the user owns (trust doctrine; a heap shelf is the safe way
        # to own shared rows). The slice-2 dangle reject retires.
        if base in DYN_INT_TYPES:
            tag, family = "VELO_DYN_I64", "int"
            cast_c = self._map_type(base)
            member = "i64"
        elif base in DYN_FLOAT_TYPES:
            tag, family = "VELO_DYN_F64", "float"
            cast_c = self._map_type(base)
            member = "f64"
        elif base == "bool":
            tag, family = "VELO_DYN_BOOL", "bool"
            cast_c = "bool"
            member = "b"
        elif base == "string":
            tag, family = "VELO_DYN_STR", "string"
            cast_c = "const char*"
            member = "s"
        elif base.startswith("@"):
            tag, family = "VELO_DYN_PTR", "pointer"
            cast_c = self._map_type(base)
            member = "p"
        elif base.startswith("shelf[") or base == "shelf":
            tag, family = "VELO_DYN_CHILD", "shelf"
            cast_c = "VeloShelf"
            member = "child"
        else:
            raise ValueError(
                f"cannot unbox a shelf[dyn] value into {base} — targets: int family, f32/f64, bool, string, @T, shelf[T]")
        temp = self._fresh_name("dyn_")
        # 5.2 slice 8: int targets unbox through the I64/U64 ring gate
        expect = f"velo_dyn_expect({temp}, {tag}, \"{family}\")"
        if tag == "VELO_DYN_I64":
            expect = f"velo_dyn_expect_int({temp})"
        return (f"({{ VeloDyn {temp} = ({code}); {expect}; "
                f"({cast_c})({temp}.as.{member}); }})")

    def _emit_dyn_binop(self, expr: BinaryExpr, l_t: Optional[str], r_t: Optional[str],
                        op: str, arith: bool) -> str:
        """5.2 slice 8: lowers a raw-dyn binop — both operands bound once into
        VeloDyn temps (left first, evaluation order pinned), the concrete side
        boxed by its Velo type through _emit_dyn_box, then the runtime ladder
        helper (velo_dyn_arith / velo_dyn_compare). Identical C on both
        stages; the ladder and family rules live only in velo_runtime.h."""
        for side_t in (l_t, r_t):
            if side_t != "dyn":
                if arith:
                    # the arithmetic witness must be numeric (the dyn-op wall)
                    if side_t not in DYN_INT_TYPES and side_t not in DYN_FLOAT_TYPES:
                        raise ValueError(
                            f"shelf[dyn] op: cannot apply '{op}' between dyn and {side_t} — unbox with as first")
                else:
                    # compares accept every boxable family; null rejects with
                    # the boxable-null words, structs with the boxable wall
                    if side_t == "@void":
                        raise ValueError("shelf elements cannot be null (use a @T pointer element)")
                    err = self._dyn_boxable_error(side_t)
                    if err:
                        raise ValueError(err)
        left = self._emit_expression(expr.left)
        right = self._emit_expression(expr.right)
        if l_t != "dyn":
            left = self._emit_dyn_box(l_t, left, expr.left)
        if r_t != "dyn":
            right = self._emit_dyn_box(r_t, right, expr.right)
        tl = self._fresh_name("dynl_")
        tr = self._fresh_name("dynr_")
        if arith:
            return (f"({{ VeloDyn {tl} = ({left}); VeloDyn {tr} = ({right}); "
                    f"velo_dyn_arith('{op}', {tl}, {tr}); }})")
        cmp_map = {"==": "== 0", "!=": "!= 0", "<": "< 0", "<=": "<= 0", ">": "> 0", ">=": ">= 0"}
        return (f"({{ VeloDyn {tl} = ({left}); VeloDyn {tr} = ({right}); "
                f"(velo_dyn_compare({tl}, {tr}) {cmp_map[op]}); }})")

    def _shelf_root_binding(self, expr: Optional[Expr]) -> Optional[str]:
        """Walks a receiver chain down to its root binding name (or None for
        call results etc). Used by the mut-binding check for put/take/set."""
        node = expr
        while node is not None and not isinstance(node, Identifier):
            if isinstance(node, (MemberAccess, IndexExpr)):
                node = node.target
            elif isinstance(node, CastExpr):
                node = node.expr
            elif isinstance(node, DerefExpr):
                node = node.operand
            else:
                return None
        return node.name if isinstance(node, Identifier) else None

    def _shelf_expect(self, member: str, target_expr: Expr, args: List[Expr]) -> None:
        """5.2 compile-checks shelf surface calls (put/take/sorted/insert/
        remove_at/reversed/join). Mirrored by the Stage 2 checker — both
        stages reject the same programs with the same messages."""
        if member not in ("put", "take", "sorted", "insert", "remove_at", "reversed", "join"):
            raise ValueError(f"unknown shelf member '{member}' (put, take, len, sorted, insert, remove_at, reversed, join are available)")
        if member == "join":
            # 5.2 slice 5: read-only stringify glue (legal on a let)
            if len(args) != 1:
                raise ValueError("shelf.join expects exactly 1 argument: (shelf s, separator)")
            sep_t = self._resolve_expr_type(args[0])
            if sep_t != "string":
                raise ValueError(f"shelf.join separator must be a string (got {sep_t})")
            recv = self._resolve_expr_type(target_expr)
            elem = self._shelf_elem_type(recv)
            if elem:
                err = self._join_family_error(elem)
                if err:
                    raise ValueError(err)
            return
        if member == "sorted":
            if len(args) != 0:
                raise ValueError("shelf.sorted takes no arguments")
            recv = self._resolve_expr_type(target_expr)
            elem = self._shelf_elem_type(recv)
            if elem:
                err = self._sorted_family_error(elem)
                if err:
                    raise ValueError(err)
            return  # NOT a mutation: a sorted copy is legal on a let
        if member == "reversed":
            if len(args) != 0:
                raise ValueError("shelf.reversed takes no arguments")
            return  # NOT a mutation: a reversed copy is legal on a let (no family restriction)
        if member == "insert":
            if len(args) != 2:
                raise ValueError("shelf.insert expects exactly 2 arguments: (shelf s, index, element value)")
        elif member == "remove_at":
            if len(args) != 1:
                raise ValueError("shelf.remove_at expects exactly 1 argument: (shelf s, index)")
        elif member == "put" and len(args) != 1:
            raise ValueError("shelf.put expects exactly 1 argument: (shelf s, element value)")
        elif member == "take" and len(args) != 0:
            raise ValueError("shelf.take takes no arguments")
        if member in ("insert", "remove_at"):
            it = self._thread_arg_type(args[0])
            if it not in DYN_INT_TYPES:
                raise ValueError(f"shelf index must be an integer (got {it})")
        if member in ("put", "insert"):
            recv = self._resolve_expr_type(target_expr)
            elem = self._shelf_elem_type(recv)
            if elem:
                got = self._thread_arg_type(args[-1])
                self._check_shelf_put_element(member, elem, got)
        root = self._shelf_root_binding(target_expr)
        if root is not None and not self.current_scope_mut.get(root, False):
            # verbs mirror the put/take doctrine: remove_at speaks "remove"
            verb = "remove" if member == "remove_at" else member
            word = "into" if member in ("put", "insert") else "from"
            raise ValueError(f"cannot {verb} {word} a shelf held by a let (declare with mut)")

    def _check_shelf_put_element(self, member: str, elem: str, got: str) -> None:
        """Element-type contract shared by put and insert (5.2 slice 1/2/3):
        exact match, dyn shelves box any boxable element (void/null reject)."""
        if elem == "dyn":
            # 5.2 slice 2: any boxable element goes in (boxed by the emitter);
            # the tag-based mismatch check is skipped
            if got == "unknown":
                return  # the argument itself already failed to infer
            if got == "void":
                raise ValueError(f"shelf[dyn] {member}: cannot box a void value")
            if got == "@void":
                raise ValueError("shelf elements cannot be null (use a @T pointer element)")
            err = self._dyn_boxable_error(got)
            if err:
                raise ValueError(err)
        elif got != elem and got not in ("void", "@void"):
            raise ValueError(f"shelf.{member} element mismatch: expected {elem} (got {got})")

    def _sorted_family_error(self, elem: str):
        """None when `sorted()` can order `elem`; else the pinned reject.
        Bare type parameters (generic bodies) flow through mono — everything
        else non-numeric/non-string is rejected concretely."""
        if elem in DYN_INT_TYPES or elem in DYN_FLOAT_TYPES or elem == "string":
            return None
        if elem == "bool" or elem == "dyn":
            return f"shelf.sorted() supports numeric or string elements (got {elem})"
        if elem.startswith("@"):
            return f"shelf.sorted() supports numeric or string elements (got {elem})"
        if elem in self.struct_defs or elem in self.kind_defs:
            return f"shelf.sorted() supports numeric or string elements (got {elem})"
        return None

    def _join_family_error(self, elem: str):
        """None when `join()` can stringify `elem`; else the pinned reject
        (5.2 slice 5). bool IS joinable (it is not sorted-joinable); dyn has
        no repr (tagged boxes), struct/pointer/shelf rows follow. Bare type
        parameters (generic bodies) flow through mono."""
        if elem in DYN_INT_TYPES or elem in DYN_FLOAT_TYPES or elem in ("string", "bool"):
            return None
        if elem == "dyn":
            return "shelf[dyn] join is not supported — cast elements first"
        return f"shelf.join is not supported on {elem} elements"

    def _check_shelf_annotation(self, decl_type: Optional[str], value: Optional[Expr]) -> None:
        """5.2 contract: annotated shelf declarations — an empty literal borrows
        the annotation's element type; a non-empty literal must match it
        exactly. Mirrored by the Stage 2 checker's check_shelf_annotation.
        Slice 10: `heap shelf[T]` annotations ride the same check (the
        storage modifier is part of the compared spelling)."""
        if not isinstance(value, ShelfLiteral) or not decl_type:
            return
        clean_decl = decl_type.lstrip("@")
        if not clean_decl.startswith("shelf[") and not clean_decl.startswith("heap shelf["):
            return
        ann_elem = self._shelf_elem_type(decl_type)
        # 5.2 slice 10: the storage modifier is part of the spelling — a heap
        # literal under a zone-backed annotation (or the reverse) rejects with
        # the full literal spelling in the elem slot, BEFORE the empty borrow
        ann_is_heap = clean_decl.startswith("heap ")
        if value.is_heap != ann_is_heap:
            if value.args:
                lit_full = self._infer_raw_velo_type(value)
            else:
                lit_full = "heap shelf[]" if value.is_heap else "shelf[]"
            raise ValueError(f"shelf literal element type {lit_full} does not match annotation {decl_type}")
        if not value.args:
            if ann_elem is not None:
                value.elem_type = ann_elem
            return
        if ann_elem is None:
            return
        lit_elem = self._shelf_elem_type(self._infer_raw_velo_type(value))
        if lit_elem is not None and lit_elem != ann_elem:
            raise ValueError(f"shelf literal element type shelf[{lit_elem}] does not match annotation {decl_type}")

    def _check_split_retire(self, type_str: Optional[str], value: Optional[Expr]) -> None:
        """5.2 slice 11: the `@string` token-array spelling retired — a
        str.split result binds to shelf[string] only, so the retired pairing
        rejects at the type wall instead of the GCC stage. Mirrored by the
        Stage 2 checker with identical wording."""
        if not type_str or value is None:
            return
        base = type_str.lstrip("@").strip()
        if base != "string":
            return
        if self._infer_raw_velo_type(value) != "shelf[string]":
            return
        raise ValueError(f"str.split returns shelf[string] — annotating {type_str} is retired (slice 11)")

    def _emit_shelf_literal(self, lit: ShelfLiteral) -> str:
        """5.2: lowers `shelf[..., ...]` into a GCC statement-expression so the
        literal can live in any value position. Each element is bound exactly
        once into a typed temp (left-to-right evaluation order guaranteed)."""
        raw = self._infer_raw_velo_type(lit)
        elem = self._shelf_elem_type(raw)
        if elem is None:
            raise ValueError("cannot infer element type of empty shelf literal — annotate it (e.g. let e: shelf[i32] = shelf[])")
        elem_c = self._map_type(elem)
        recv = self._fresh_name("shl_")
        parts = [f"VeloShelf {recv} = {{0}}"]
        if lit.is_heap:
            # 5.2 slice 10: the heap sentinel routes every growth/put through
            # velo_heap_alloc — the shelf outlives its zone
            parts.append(f"{recv}.src = VELO_SHELF_HEAP_SRC")
        for a in lit.args:
            slot = self._fresh_name("esl_")
            val_code = self._emit_expression(a)
            if elem == "dyn":
                # 5.2 slice 2: box each element into the tag (raw dyn passes
                # through whole); f64-widened elements ride the slot cast
                raw = self._infer_raw_velo_type(a)
                if raw != "dyn":
                    val_code = self._emit_dyn_box(raw, val_code, a)
            parts.append(
                f"{{ {elem_c} {slot} = ({val_code}); "
                f"velo_shelf_put(&{recv}, (const void*)(&{slot}), (usize)sizeof({elem_c})); }}"
            )
        parts.append(f"{recv}")
        return "({ " + "; ".join(parts) + "; })"

    def generate(self, program: Program) -> str:
        program = Monomorphizer().monomorphize(program)

        self.output = []
        self.struct_defs = {}
        self.current_scope_types = {}
        self.current_scope_mut = {}
        self.global_types: Dict[str, str] = {}
        self.global_scope_mut: Dict[str, bool] = {}
        self.func_return_types: Dict[str, str] = {}
        self.defer_stack = []
        self.zone_counter = 0
        self.fresh_counter = 0

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
            elif isinstance(e, ShelfLiteral):
                for a in e.args: scan_expr(a)
            elif isinstance(e, MapLiteral):
                for a in e.keys: scan_expr(a)
                for a in e.vals: scan_expr(a)

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
                if s.of_expr: scan_expr(s.of_expr)
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
                    # 5.2: annotated shelf decls pin empties / reject mismatches
                    # 5.2 slice 6: same contract for annotated map decls
                    self._check_shelf_annotation(decl.type_name, decl.value)
                    self._check_map_annotation(decl.type_name, decl.value)
                    self._check_ring_annotation(decl.type_name, decl.value)
                    self._check_bitset_annotation(decl.type_name, decl.value)
                    type_str = self._infer_or_map_type(decl.type_name, decl.value)
                    raw_velo_type = decl.type_name or self._infer_raw_velo_type(decl.value)
                    self.global_types[decl.name] = raw_velo_type
                    self.global_scope_mut[decl.name] = decl.is_mut
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
        self.current_scope_mut = dict(self.global_scope_mut)
        self.defer_stack = [[]]

        for p in func.params:
            self.current_scope_types[p.name] = p.type_name
            self.current_scope_mut[p.name] = True
        
        if is_main:
            self._emit_line("int main(int argc, char** argv) {")
            # 5.4 S1: stash argv for sys.os (both stages emit these two
            # identical indent-0 lines as the first lines of main).
            self._emit_line("g_velo_os_argc = argc;")
            self._emit_line("g_velo_os_argv = argv;")
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
            # 5.2: an empty shelf literal in a return borrows its element type
            # from the act's declared return type; slice 6: an empty map
            # literal borrows BOTH slots the same way
            if stmt.value and isinstance(stmt.value, ShelfLiteral) and not stmt.value.args:
                ret_t = self.current_function.return_type if self.current_function else None
                if ret_t and (ret_t.lstrip("@").startswith("shelf[") or ret_t.lstrip("@").startswith("heap shelf[")):
                    stmt.value.elem_type = self._shelf_elem_type(ret_t)
            if stmt.value and isinstance(stmt.value, MapLiteral) and not stmt.value.keys:
                ret_t = self.current_function.return_type if self.current_function else None
                if ret_t and ret_t.lstrip("@").startswith("Map["):
                    stmt.value.kv_type = ret_t
            # 5.2 slice 9: an empty ring literal in a return borrows its
            # element type the same way; a bitset literal needs no pinning
            if stmt.value and isinstance(stmt.value, RingLiteral) and not stmt.value.args:
                ret_t = self.current_function.return_type if self.current_function else None
                if ret_t and ret_t.lstrip("@").startswith("ring["):
                    stmt.value.elem_type = self._ring_elem_type(ret_t)
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
            # 5.2: annotated shelf decls pin empties / reject mismatches
            # 5.2 slice 6: same contract for annotated map decls
            self._check_shelf_annotation(stmt.type_name, stmt.value)
            self._check_map_annotation(stmt.type_name, stmt.value)
            self._check_ring_annotation(stmt.type_name, stmt.value)
            self._check_bitset_annotation(stmt.type_name, stmt.value)
            self._check_split_retire(stmt.type_name, stmt.value)  # slice 11
            type_str = self._infer_or_map_type(stmt.type_name, stmt.value)
            raw_velo_type = stmt.type_name or self._infer_raw_velo_type(stmt.value)
            self.current_scope_types[stmt.name] = raw_velo_type
            self.current_scope_mut[stmt.name] = stmt.is_mut

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
            # 5.2: shelf indexed write (xs[i] = v) — bounds-checked via helper
            if isinstance(stmt.target, IndexExpr):
                base_type = self._resolve_expr_type(stmt.target.target)
                shelf_elem = self._shelf_elem_type(base_type)
                if shelf_elem is not None:
                    if stmt.op != "=":
                        raise ValueError("compound assignments on shelves are not supported yet — use an explicit '=' write")
                    root = self._shelf_root_binding(stmt.target)
                    if root is not None and not self.current_scope_mut.get(root, False):
                        raise ValueError("cannot write into a shelf held by a let (declare with mut)")
                    if isinstance(stmt.target.target, IndexExpr) and not base_type.startswith("@"):
                        # 5.2 slice 10: the guard tests the ROW TYPE's pointer-
                        # ness — @shelf[..] rows share their storage, so writes
                        # through them are the shared-rows closure; value rows
                        # (shelf[T]) stay rejected
                        raise ValueError("cannot write through a shelf row copy (snapshot rows) — use @shelf[int] rows for in-place mutation")
                    itype = self._resolve_expr_type(stmt.target.index)
                    if itype not in SHELF_INT_TYPES:
                        raise ValueError(f"shelf index must be an integer (got {itype})")
                    elem_c = self._map_type(shelf_elem)
                    target_code = self._emit_expression(stmt.target.target)
                    rec = f"({target_code})" if base_type.startswith("@") else f"&({target_code})"
                    slot = self._fresh_name("set_")
                    val_code = self._emit_expression(stmt.value)
                    if shelf_elem == "dyn":
                        # 5.2 slice 2: box the written value into the tag
                        raw = self._infer_raw_velo_type(stmt.value)
                        if raw != "dyn":
                            val_code = self._emit_dyn_box(raw, val_code, stmt.value)
                    self._emit_line(
                        f"{{ {elem_c} {slot} = ({val_code}); "
                        f"velo_shelf_set({rec}, (usize)({self._emit_expression(stmt.target.index)}), "
                        f"(const void*)(&{slot}), (usize)sizeof({elem_c})); }}"
                    )
                    return
                kv = self._map_kv(base_type)
                if kv is not None:
                    # 5.2 slice 6: map subscript upsert — the `put` payload twin
                    if stmt.op != "=":
                        raise ValueError("compound assignments on maps are not supported yet — use an explicit '=' write")
                    root = self._shelf_root_binding(stmt.target)
                    if root is not None and not self.current_scope_mut.get(root, False):
                        raise ValueError("cannot write into a map held by a let (declare with mut)")
                    key_t = self._resolve_expr_type(stmt.target.index)
                    if key_t != kv[0]:
                        raise ValueError(f"map key mismatch: expected {kv[0]} (got {key_t})")
                    got = self._thread_arg_type(stmt.value)
                    self._check_map_value("put", kv[1], got)
                    key_c = self._map_key_slot_c(kv[0])
                    val_c = self._map_type(kv[1])
                    target_code = self._emit_expression(stmt.target.target)
                    rec = f"({target_code})" if base_type.startswith("@") else f"&({target_code})"
                    k_slot = self._fresh_name("mk_")
                    v_slot = self._fresh_name("mv_")
                    key_code = self._emit_expression(stmt.target.index)
                    val_code = self._emit_expression(stmt.value)
                    if kv[1] == "dyn":
                        # 5.2 slice 2: box the written value into the tag
                        raw = self._infer_raw_velo_type(stmt.value)
                        if raw != "dyn":
                            val_code = self._emit_dyn_box(raw, val_code, stmt.value)
                    self._emit_line(
                        f"{{ {key_c} {k_slot} = ({key_code}); {val_c} {v_slot} = ({val_code}); "
                        f"velo_map_put({rec}, (const void*)(&{k_slot}), (const void*)(&{v_slot})); }}"
                    )
                    return
            target_code = self._emit_expression(stmt.target)
            # 5.2 slice 11: the retire wall rides plain assignments too
            if isinstance(stmt.target, Identifier):
                self._check_split_retire(self.current_scope_types.get(stmt.target.name), stmt.value)
            val_code = self._emit_expression(stmt.value)
            self._emit_line(f"{target_code} {stmt.op} {val_code};")

        elif isinstance(stmt, IfStmt):
            self._emit_if(stmt)

        elif isinstance(stmt, LoopStmt):
            # 5.2: `loop v of coll { }` — snapshot iteration. The source is
            # evaluated ONCE into a stable view (data pointer + length); puts
            # or takes during the body mutate the shelf, never the view.
            if stmt.of_expr is not None:
                coll_type = self._resolve_expr_type(stmt.of_expr)
                kv = self._map_kv(coll_type)
                if kv is not None:
                    # 5.2 slice 7: `loop k of m { }` — key iteration in HASH
                    # order (deterministic FNV derivation, NOT insertion
                    # order). Snapshot doctrine: at entry the live rows are
                    # scanned once and their key bytes copied into a fresh
                    # key-typed array in the active arena; put/take during
                    # the body mutate the live map, never the view.
                    it = stmt.iterator or "v"
                    key_c = self._map_key_slot_c(kv[0])
                    key_usz = "sizeof(char*)" if kv[0] == "string" else f"sizeof({self._map_type(kv[0])})"
                    src = self._fresh_name("lsrc_")
                    cnt = self._fresh_name("lcnt_")
                    idx = self._fresh_name("lidx_")
                    iname = stmt.of_index or idx  # the optional user index binding
                    dat = self._fresh_name("ldat_")
                    run = self._fresh_name("lrun_")
                    fill = self._fresh_name("lfill_")
                    scan = self._fresh_name("lscan_")
                    coll_code = self._emit_expression(stmt.of_expr)
                    cap_src = f"(*({coll_code}))" if coll_type.startswith("@") else f"({coll_code})"
                    alive = f"({src}.hashes[{scan}] != 0 && {src}.hashes[{scan}] != VELO_MAP_TOMB)"
                    self._emit_line("{")
                    self.indent_level += 1
                    self._emit_line(f"VeloMap {src} = {cap_src};")
                    self._emit_line(f"const usize {cnt} = ({{ size_t {run} = 0; for (size_t {scan} = 0; {scan} < {src}.cap; ++{scan}) if ({alive}) ++{run}; {run}; }});")
                    self._emit_line(f"void* {dat} = velo_mem_alloc((usize){key_usz}, {cnt});")
                    self._emit_line(f"{{ size_t {fill} = 0; for (size_t {scan} = 0; {scan} < {src}.cap; ++{scan}) if ({alive}) {{ memcpy((char*){dat} + {fill} * (usize){key_usz}, (const char*){src}.keys + {scan} * (usize){key_usz}, (usize){key_usz}); ++{fill}; }} }}")
                    self._emit_line(f"for (usize {iname} = 0; {iname} < {cnt}; ++{iname}) {{")
                    self.indent_level += 1
                    self._emit_line(f"const {key_c} {it} = (({key_c}*){dat})[{iname}];")
                    self.current_scope_types[it] = kv[0]
                    self.current_scope_mut[it] = False
                    if stmt.of_index:
                        # the second binding names the step index (usize)
                        self.current_scope_types[iname] = "usize"
                        self.current_scope_mut[iname] = False
                    self.defer_stack.append([])
                    self._emit_block_body(stmt.body.statements)
                    self.indent_level -= 1
                    self._emit_line("}")
                    self.indent_level -= 1
                    self._emit_line("}")
                    return
                # 5.2 slice 9: `loop v of r { }` — FIFO snapshot iteration.
                # At entry the live elements are copied front-to-back into a
                # fresh element-typed arena array; put/pop during the body
                # mutate the live ring, never the view.
                ring_elem = self._ring_elem_type(coll_type)
                if ring_elem is not None:
                    it = stmt.iterator or "v"
                    elem_c = self._map_type(ring_elem)
                    elem_sz = f"sizeof({elem_c})"
                    src = self._fresh_name("lsrc_")
                    cnt = self._fresh_name("lcnt_")
                    iname = stmt.of_index or self._fresh_name("lidx_")
                    dat = self._fresh_name("ldat_")
                    run = self._fresh_name("lrun_")
                    coll_code = self._emit_expression(stmt.of_expr)
                    cap_src = f"(*({coll_code}))" if coll_type.startswith("@") else f"({coll_code})"
                    self._emit_line("{")
                    self.indent_level += 1
                    self._emit_line(f"VeloRing {src} = {cap_src};")
                    self._emit_line(f"const usize {cnt} = {src}.len;")
                    self._emit_line(f"void* {dat} = velo_mem_alloc((usize){elem_sz}, {cnt});")
                    self._emit_line(f"for (size_t {run} = 0; {run} < {cnt}; ++{run}) {{ memcpy((char*){dat} + {run} * (usize){elem_sz}, (const char*){src}.data + ((({src}.head + {run}) & ({src}.cap - 1)) * (usize){elem_sz}), (usize){elem_sz}); }}")
                    self._emit_line(f"for (usize {iname} = 0; {iname} < {cnt}; ++{iname}) {{")
                    self.indent_level += 1
                    self._emit_line(f"const {elem_c} {it} = (({elem_c}*){dat})[{iname}];")
                    self.current_scope_types[it] = ring_elem
                    self.current_scope_mut[it] = False
                    if stmt.of_index:
                        # the second binding names the step index (usize)
                        self.current_scope_types[iname] = "usize"
                        self.current_scope_mut[iname] = False
                    self.defer_stack.append([])
                    self._emit_block_body(stmt.body.statements)
                    self.indent_level -= 1
                    self._emit_line("}")
                    self.indent_level -= 1
                    self._emit_line("}")
                    return
                elem = self._shelf_elem_type(coll_type)
                if elem is None:
                    raise ValueError(f"the 'of' source of a loop must be a shelf, map, or ring (got {coll_type})")
                it = stmt.iterator or "v"
                elem_c = self._map_type(elem)
                src = self._fresh_name("lsrc_")
                cnt = self._fresh_name("lcnt_")
                idx = self._fresh_name("lidx_")
                iname = stmt.of_index or idx  # 5.2 slice 4: the optional user index binding
                dat = self._fresh_name("ldat_")
                coll_code = self._emit_expression(stmt.of_expr)
                cap = f"(*({coll_code}))" if coll_type.startswith("@") else f"({coll_code})"
                self._emit_line("{")
                self.indent_level += 1
                self._emit_line(f"VeloShelf {src} = {cap};")
                self._emit_line(f"const usize {cnt} = {src}.len;")
                self._emit_line(f"void* {dat} = {src}.data;")
                self._emit_line(f"for (usize {iname} = 0; {iname} < {cnt}; ++{iname}) {{")
                self.indent_level += 1
                self._emit_line(f"const {elem_c} {it} = (({elem_c}*){dat})[{iname}];")
                self.current_scope_types[it] = elem
                self.current_scope_mut[it] = False
                if stmt.of_index:
                    # 5.2 slice 4: the second binding names the step index (usize)
                    self.current_scope_types[iname] = "usize"
                    self.current_scope_mut[iname] = False
                self.defer_stack.append([])
                self._emit_block_body(stmt.body.statements)
                self.indent_level -= 1
                self._emit_line("}")
                self.indent_level -= 1
                self._emit_line("}")
                return

            it = stmt.iterator or "it"
            self.current_scope_types[it] = "i64"
            self.current_scope_mut[it] = False
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
        if isinstance(value, ShelfLiteral):
            # 5.2: strict-homogeneous inference; empty literals only infer
            # when an annotation established elem_type beforehand. Slice 10:
            # a heap literal's inferred spelling carries the `heap ` prefix.
            heap_pfx = "heap " if value.is_heap else ""
            if value.elem_type:
                return f"{heap_pfx}shelf[{value.elem_type}]"
            if not value.args:
                raise ValueError("cannot infer element type of empty shelf literal — annotate it (e.g. let e: shelf[i32] = shelf[])")
            types = [self._infer_raw_velo_type(a) for a in value.args]
            first = types[0]
            if first == "@void":
                raise ValueError("shelf elements cannot be null (use a @T pointer element)")
            for t in types:
                if t == "@void":
                    raise ValueError("shelf elements cannot be null (use a @T pointer element)")
            # 5.2 slice 2 — the element inference ladder: homogeneous unchanged;
            # an all-numeric mix with a float widens to f64; a mixed-width
            # all-integer literal stays a strict differ error (deliberate);
            # any other mix lowers to shelf[dyn] (every element must box).
            mixed = any(t != first for t in types)
            if not mixed:
                return f"{heap_pfx}shelf[{first}]"
            if all(t in DYN_INT_TYPES or t in DYN_FLOAT_TYPES for t in types):
                if any(t in DYN_FLOAT_TYPES for t in types):
                    return f"{heap_pfx}shelf[f64]"
                second = next(t for t in types if t != first)
                raise ValueError(f"shelf literal element types differ: {first} vs {second}")
            for t in types:
                err = self._dyn_boxable_error(t)
                if err:
                    raise ValueError(err)
            return f"{heap_pfx}shelf[dyn]"
        if isinstance(value, MapLiteral):
            # 5.2 slice 6: the map literal ladder. Annotated empties return
            # the pinned `Map[K, V]`; non-empty literals run the key gate +
            # the value ladder (mirrored by Stage 2's map_checks.vl).
            if value.kv_type:
                return value.kv_type
            if not value.keys:
                raise ValueError("cannot infer key and value types of empty map literal — annotate it (e.g. let m: Map[i32, string] = map[])")
            return self._infer_map_literal_type(value)
        if isinstance(value, RingLiteral):
            # 5.2 slice 9: the ring ladder (no dyn arm) — annotated empties
            # return the pinned ring[T]; non-empty run the element ladder.
            if value.elem_type:
                return f"ring[{value.elem_type}]"
            return f"ring[{self._ring_literal_elem(value)}]"
        if isinstance(value, BitsetLiteral):
            # 5.2 slice 9: bitset is monomorphic — no element ladder exists
            return "bitset"
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
        if isinstance(value, BinaryExpr):
            # 5.2 slice 2 parity fix: unannotated arith/comparison lets infer
            # like Stage 2's checker (comparisons are bool, otherwise the left
            # operand's type — widened dyn literals read f64 through clauses).
            if value.op in ("==", "!=", "<", "<=", ">", ">=", "and", "or"):
                return "bool"
            # 5.2 slice 8: arithmetic with a raw dyn operand re-boxes — the
            # result type is dyn regardless of which side carries it
            if value.op in ("+", "-", "*", "/", "%"):
                if self._resolve_expr_type(value.left) == "dyn" or self._resolve_expr_type(value.right) == "dyn":
                    return "dyn"
            return self._resolve_expr_type(value.left)
        if isinstance(value, UnaryExpr):
            if value.op in ("!", "not"):
                return "bool"
            return self._resolve_expr_type(value.operand)
        if isinstance(value, MemberAccess):
            if isinstance(value.target, Identifier) and value.target.name in self.kind_defs:
                return value.target.name
            return self._resolve_expr_type(value)
        if isinstance(value, IndexExpr):
            target_type = self._resolve_expr_type(value.target)
            if target_type == "string":
                return "u8"
            shelf_elem = self._shelf_elem_type(target_type)
            if shelf_elem is not None:
                return shelf_elem
            map_kv = self._map_kv(target_type)
            if map_kv is not None:
                # 5.2 slice 6: a map read yields V (the strict key check and
                # the fatal live in the emitter for the same expression)
                return map_kv[1]
            if self._ring_elem_type(target_type) is not None:
                # 5.2 slice 9: rings have no subscript — the differentiator
                # is pop/peek, not indexing
                raise ValueError("ring does not support subscript reads — use peek()")
            if target_type.lstrip("@") == "bitset":
                raise ValueError("bitset does not support subscript reads — use has()")
            if target_type.startswith("@"):
                return target_type[1:]
            return "i32"
        if isinstance(value, CallExpr):
            # 5.2: shelf receiver calls — put/insert return void, take/
            # remove_at the element, sorted() a new shelf[elem]
            if isinstance(value.callee, MemberAccess):
                recv = self._resolve_expr_type(value.callee.target)
                shelf_elem = self._shelf_elem_type(recv)
                if shelf_elem is not None:
                    if value.callee.member in ("put", "insert"):
                        return "void"
                    if value.callee.member in ("take", "remove_at"):
                        return shelf_elem
                    if value.callee.member == "join":
                        # 5.2 slice 5: join renders into a fresh string
                        return "string"
                    if value.callee.member == "sorted" or value.callee.member == "reversed":
                        return f"shelf[{shelf_elem}]"
                    raise ValueError(f"unknown shelf member '{value.callee.member}' (put, take, len, sorted, insert, remove_at, reversed, join are available)")
            if isinstance(value.callee, MemberAccess):
                # 5.2 slice 6/7: map receiver calls — put is void, get and
                # the get_or/take twins return the value, has returns bool
                # (unknown members stay loud)
                recv_kv = self._map_kv(self._resolve_expr_type(value.callee.target))
                if recv_kv is not None:
                    if value.callee.member == "put":
                        return "void"
                    if value.callee.member in ("get", "get_or", "take"):
                        return recv_kv[1]
                    if value.callee.member == "has":
                        return "bool"
                    raise ValueError(f"unknown map member '{value.callee.member}' (put, get, has, len, get_or, take are available)")
                # 5.2 slice 9: ring/bitset receiver calls
                recv_ring = self._ring_elem_type(self._resolve_expr_type(value.callee.target))
                if recv_ring is not None:
                    if value.callee.member == "put":
                        return "void"
                    if value.callee.member in ("pop", "peek"):
                        return recv_ring
                    raise ValueError(f"unknown ring member '{value.callee.member}' (put, pop, peek, len are available)")
                recv_bs = self._resolve_expr_type(value.callee.target).lstrip("@")
                if recv_bs == "bitset":
                    if value.callee.member in ("set", "clear", "toggle", "and", "or_with", "xor_with", "flip"):
                        return "void"
                    if value.callee.member == "has":
                        return "bool"
                    if value.callee.member == "count":
                        return "usize"
                    if value.callee.member == "first_unset":
                        return "i32"
                    raise ValueError(f"unknown bitset member '{value.callee.member}' (set, clear, toggle, has, count, first_unset, and, or_with, xor_with, flip are available)")
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
                    # 5.4 S2: fs is a closed namespace — the legacy six keep
                    # their exact spells; unknown members fall through to
                    # the default (the emit path's checker raises).
                    return fs_member_result_type(value.callee.member)
                elif value.callee.target.name == "str":
                    m = value.callee.member
                    if m == "len":
                        return "usize"
                    if m in ("contains", "starts_with", "ends_with"):
                        return "bool"
                    if m in ("trim", "replace", "to_upper", "to_lower", "concat"):
                        return "string"
                    if m == "index_of":
                        return "i64"  # -1 = not found; usize has no room for it
                    if m == "split":
                        return "shelf[string]"  # slice 11: the owning-shelf swap
                elif value.callee.target.name == "math":
                    # 5.3 S4: the result spell is arg-aware (abs/min/max
                    # dispatch on their arguments) — library-literal element
                    # estimation stays exact
                    if value.callee.member in MATH_CALLS:
                        return math_member_result_type(
                            value.callee.member,
                            [self._thread_arg_type(a) for a in value.args])
                elif value.callee.target.name == "time":
                    # 5.5: now/delta are zero-arg i64 microsecond clocks;
                    # sleep_ms is void. Unknown members fall through to the
                    # default below (the emit path's checker raises — the
                    # math unknown-member shape).
                    if value.callee.member in TIME_CALLS:
                        return time_member_result_type(value.callee.member, [])
                elif value.callee.target.name == "os":
                    # 5.4 S1: os result spells (time-style closed namespace).
                    # Unknown members fall through to the default — the emit
                    # path's checker raises.
                    return os_member_result_type(value.callee.member)
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
        if isinstance(expr, ShelfLiteral):
            return self._infer_raw_velo_type(expr)
        if isinstance(expr, MapLiteral):
            return self._infer_raw_velo_type(expr)
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
            shelf_elem = self._shelf_elem_type(target_type)
            if shelf_elem is not None:
                return shelf_elem
            map_kv = self._map_kv(target_type)
            if map_kv is not None:
                # 5.2 slice 6: a map read yields V (the strict key check and
                # the fatal live in the emitter for the same expression)
                return map_kv[1]
            if self._ring_elem_type(target_type) is not None:
                # 5.2 slice 9: rings have no subscript — the differentiator
                # is pop/peek, not indexing
                raise ValueError("ring does not support subscript reads — use peek()")
            if target_type.lstrip("@") == "bitset":
                raise ValueError("bitset does not support subscript reads — use has()")
            if target_type == "string":
                return "u8"
            if target_type.startswith("@"):
                return target_type[1:]
            return target_type
        elif isinstance(expr, MemberAccess):
            if isinstance(expr.target, Identifier) and expr.target.name in self.kind_defs:
                return expr.target.name
            # 5.3: math constants are bare member properties on the math
            # receiver (no parens); unknown names reject with the mirrored
            # wording (functions need parens hint rides along)
            if isinstance(expr.target, Identifier) and expr.target.name == "math":
                if expr.member in MATH_CONSTANTS:
                    return "f64"
                hint = f" (functions need parens: math.{expr.member}(...))" if expr.member in MATH_CALLS else ""
                raise ValueError(f"unknown math constant '{expr.member}' (constants: PI, TAU, RAD2DEG, DEG2RAD){hint}")
            # 5.5: time has NO constants — bare member reads reject with the
            # mirrored wording (the parens hint rides when the member names
            # a known function; math's bare-`math.sqrt` precedent)
            if isinstance(expr.target, Identifier) and expr.target.name == "time":
                hint = f" (functions need parens: time.{expr.member}())" if expr.member in TIME_CALLS else ""
                raise ValueError(f"unknown time constant '{expr.member}' (time functions are: {TIME_FUNCS_TEXT}){hint}")
            # 5.4: os has NO constants — bare member reads reject with the
            # mirrored wording
            if isinstance(expr.target, Identifier) and expr.target.name == "os":
                hint = f" (functions need parens: os.{expr.member}())" if expr.member in OS_CALLS else ""
                raise ValueError(f"unknown os constant '{expr.member}' (os functions are: {OS_FUNCS_TEXT}){hint}")
            # 5.4 S2: the fs namespace goes CLOSED — bare member reads
            # reject with the mirrored wording (fs has no constants)
            if isinstance(expr.target, Identifier) and expr.target.name == "fs":
                hint = f" (functions need parens: fs.{expr.member}())" if expr.member in FS_CALLS else ""
                raise ValueError(f"unknown fs constant '{expr.member}' (fs functions are: {FS_FUNCS_TEXT}){hint}")
            target_type = self._resolve_expr_type(expr.target)
            # 5.2: shelf property reads (len); other members are loud errors
            if self._shelf_elem_type(target_type) is not None:
                if expr.member == "len":
                    return "usize"
                raise ValueError(f"unknown shelf member '{expr.member}' (put, take, len, sorted, insert, remove_at, reversed, join are available)")
            # 5.2 slice 6: map property reads (len); other members are loud
            # errors naming the map surface
            map_kv = self._map_kv(target_type)
            if map_kv is not None:
                if expr.member == "len":
                    return "usize"
                raise ValueError(f"unknown map member '{expr.member}' (put, get, has, len, get_or, take are available)")
            # 5.2 slice 9: ring property reads (len); bitset has NO property
            # members (count/first_unset are calls)
            if self._ring_elem_type(target_type) is not None:
                if expr.member == "len":
                    return "usize"
                raise ValueError(f"unknown ring member '{expr.member}' (put, pop, peek, len are available)")
            if target_type.lstrip("@") == "bitset":
                raise ValueError(f"unknown bitset member '{expr.member}' (set, clear, toggle, has, count, first_unset, and, or_with, xor_with, flip are available)")
            clean_type = target_type.lstrip("@")
            fields = self.struct_defs.get(clean_type, {})
            return fields.get(expr.member, "i32")
        elif isinstance(expr, AnonFuncExpr):
            return f"act({', '.join(p.type_name for p in expr.params)}) -> {expr.return_type}"
        elif isinstance(expr, CallExpr):
            # 5.2: shelf receiver calls — put/insert void, take/remove_at the
            # element, sorted() shelf[elem]
            if isinstance(expr.callee, MemberAccess):
                recv = self._resolve_expr_type(expr.callee.target)
                shelf_elem = self._shelf_elem_type(recv)
                if shelf_elem is not None:
                    if expr.callee.member in ("put", "insert"):
                        return "void"
                    if expr.callee.member in ("take", "remove_at"):
                        return shelf_elem
                    if expr.callee.member == "join":
                        # 5.2 slice 5: join renders into a fresh string
                        return "string"
                    if expr.callee.member == "sorted" or expr.callee.member == "reversed":
                        return f"shelf[{shelf_elem}]"
                    raise ValueError(f"unknown shelf member '{expr.callee.member}' (put, take, len, sorted, insert, remove_at, reversed, join are available)")
                # 5.2 slice 6/7: map receiver calls — put void / get,
                # get_or, take value / has bool
                recv_kv = self._map_kv(recv)
                if recv_kv is not None:
                    if expr.callee.member == "put":
                        return "void"
                    if expr.callee.member in ("get", "get_or", "take"):
                        return recv_kv[1]
                    if expr.callee.member == "has":
                        return "bool"
                    raise ValueError(f"unknown map member '{expr.callee.member}' (put, get, has, len, get_or, take are available)")
                # 5.2 slice 9: ring receiver calls — put void, pop/peek the
                # element; bitset calls — mutators void, has bool
                ring_elem = self._ring_elem_type(recv)
                if ring_elem is not None:
                    if expr.callee.member == "put":
                        return "void"
                    if expr.callee.member in ("pop", "peek"):
                        return ring_elem
                    raise ValueError(f"unknown ring member '{expr.callee.member}' (put, pop, peek, len are available)")
                if recv.lstrip("@") == "bitset":
                    if expr.callee.member in ("set", "clear", "toggle", "and", "or_with", "xor_with", "flip"):
                        return "void"
                    if expr.callee.member == "has":
                        return "bool"
                    if expr.callee.member == "count":
                        return "usize"
                    if expr.callee.member == "first_unset":
                        return "i32"
                    raise ValueError(f"unknown bitset member '{expr.callee.member}' (set, clear, toggle, has, count, first_unset, and, or_with, xor_with, flip are available)")
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
                elif expr.callee.target.name == "mem" and expr.callee.member == "realloc":
                    # §4.3: mem.realloc(ptr, @T, count) -> @T (like alloc_with)
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
                    # 5.4 S2: closed namespace (mirror of the infer branch)
                    return fs_member_result_type(expr.callee.member)
                elif expr.callee.target.name == "str":
                    m = expr.callee.member
                    if m == "len":
                        return "usize"
                    if m in ("contains", "starts_with", "ends_with"):
                        return "bool"
                    if m in ("trim", "replace", "to_upper", "to_lower", "concat"):
                        return "string"
                    if m == "index_of":
                        return "i64"  # -1 = not found; usize has no room for it
                    if m == "split":
                        return "shelf[string]"  # slice 11: the owning-shelf swap
                elif expr.callee.target.name == "math":
                    # 5.3 S4: arg-aware result spell — see
                    # math_member_result_type (abs/min/max branch, all
                    # other members stay f64)
                    if expr.callee.member in MATH_CALLS:
                        return math_member_result_type(
                            expr.callee.member,
                            [self._thread_arg_type(a) for a in expr.args])
                elif expr.callee.target.name == "time":
                    # 5.5: now/delta -> i64, sleep_ms -> void (mirror of the
                    # _infer_raw_velo_type branch above)
                    if expr.callee.member in TIME_CALLS:
                        return time_member_result_type(expr.callee.member, [])
                elif expr.callee.target.name == "os":
                    # 5.4 S1: args -> shelf[string], get_env -> string,
                    # set_env -> bool, exit -> void (mirror of the infer branch)
                    return os_member_result_type(expr.callee.member)
                elif expr.callee.target.name == "io":
                    # All io calls are void (mirrors type_checker.vl), so
                    # mem count/fill checks can render and reject them.
                    return "void"
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
            target_type = self._resolve_expr_type(expr.target)
            shelf_elem = self._shelf_elem_type(target_type)
            if shelf_elem is not None:
                # 5.2: bounds-checked shelf read through the runtime helper
                itype = self._resolve_expr_type(expr.index)
                if itype not in SHELF_INT_TYPES:
                    raise ValueError(f"shelf index must be an integer (got {itype})")
                target_code = self._emit_expression(expr.target)
                index_code = self._emit_expression(expr.index)
                recv = f"({target_code})" if target_type.startswith("@") else f"&({target_code})"
                elem_c = self._map_type(shelf_elem)
                if self.unsafe_shelf_index:
                    # 5.2 slice 11: the --unsafe-shelf-index knob — the
                    # unguarded read; out-of-range indexes are silent UB
                    # (documented; flag-gated, not exercised by the suite)
                    return f"((({elem_c}*)({recv})->data)[(usize)({index_code})])"
                return f"(*(({elem_c}*)velo_shelf_get({recv}, (usize)({index_code}))))"
            kv = self._map_kv(target_type)
            if kv is not None:
                # 5.2 slice 6: fatal-on-miss map read via velo_map_copy_out —
                # key and value bind into slots first (eval order key → value),
                # the key-family token drives the fatal repr (S5 writers).
                key_t = self._resolve_expr_type(expr.index)
                if key_t != kv[0]:
                    raise ValueError(f"map key mismatch: expected {kv[0]} (got {key_t})")
                target_code = self._emit_expression(expr.target)
                key_code = self._emit_expression(expr.index)
                recv = f"({target_code})" if target_type.startswith("@") else f"&({target_code})"
                key_c = self._map_key_slot_c(kv[0])
                val_c = self._map_type(kv[1])
                k_slot = self._fresh_name("mk_")
                v_slot = self._fresh_name("mv_")
                return (f"({{ {key_c} {k_slot} = ({key_code}); {val_c} {v_slot}; "
                        f"if (!velo_map_copy_out({recv}, (const void*)(&{k_slot}), (void*)(&{v_slot}))) "
                        f"velo_map_fatal_missing({recv}, (const void*)(&{k_slot}), \"{kv[0]}\"); {v_slot}; }})")
            # 5.2 slice 9: rings/bitsets have no subscript — loud, before C
            sub_t = self._resolve_expr_type(expr.target)
            if self._ring_elem_type(sub_t) is not None:
                raise ValueError("ring does not support subscript reads — use peek()")
            if sub_t.lstrip("@") == "bitset":
                raise ValueError("bitset does not support subscript reads — use has()")
            target_code = self._emit_expression(expr.target)
            index_code = self._emit_expression(expr.index)
            return f"{target_code}[{index_code}]"
        elif isinstance(expr, ShelfLiteral):
            return self._emit_shelf_literal(expr)
        elif isinstance(expr, MapLiteral):
            return self._emit_map_literal(expr)
        elif isinstance(expr, RingLiteral):
            return self._emit_ring_literal(expr)
        elif isinstance(expr, BitsetLiteral):
            return self._emit_bitset_literal(expr)
        elif isinstance(expr, CastExpr):
            sub_t = self._resolve_expr_type(expr.expr)
            sub = self._emit_expression(expr.expr)
            if sub_t == "dyn":
                # 5.2 slice 2: the only extraction from a raw dyn
                return self._emit_dyn_unbox(sub, expr.target_type)
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
            # 5.3: math constants emit the shared decimal literals wrapped in
            # parens (digit strings identical to math_checks.vl); unknown
            # names reject with the mirrored wording
            if isinstance(expr.target, Identifier) and expr.target.name == "math":
                if expr.member in MATH_CONSTANTS:
                    return f"({MATH_CONSTANTS[expr.member]})"
                hint = f" (functions need parens: math.{expr.member}(...))" if expr.member in MATH_CALLS else ""
                raise ValueError(f"unknown math constant '{expr.member}' (constants: PI, TAU, RAD2DEG, DEG2RAD){hint}")
            target_code = self._emit_expression(expr.target)
            target_type = self._resolve_expr_type(expr.target)
            if target_type == "dyn":
                # 5.2 slice 2: raw dyn values expose no members — cast (as) first
                raise ValueError(self.DYN_GATE_ERROR)
            arrow = "->" if target_type.startswith("@") else "."
            return f"{target_code}{arrow}{expr.member}"
        elif isinstance(expr, BinaryExpr):
            l_t = self._resolve_expr_type(expr.left)
            r_t = self._resolve_expr_type(expr.right)
            op = expr.op
            if l_t == "dyn" or r_t == "dyn":
                # 5.2 slice 8: raw dyn arithmetic/compares auto-unbox — both
                # operands bound once into VeloDyn temps (left first), the
                # concrete side boxed by its Velo type, the ladder living in
                # velo_runtime.h so the stages cannot diverge on it. Unary
                # and logic operators stay gated below.
                if op in ("+", "-", "*", "/", "%"):
                    return self._emit_dyn_binop(expr, l_t, r_t, op, True)
                if op in ("==", "!=", "<", "<=", ">", ">="):
                    return self._emit_dyn_binop(expr, l_t, r_t, op, False)
                raise ValueError(self.DYN_GATE_ERROR)
            # 5.2 slice 8: concrete mixed-family compares reject (the old
            # pointer-vs-int GCC warning tier is now a pinned semantic wall;
            # pointer identity compares like `p == q` stay untouched)
            if op in ("==", "!=", "<", "<=", ">", ">="):
                lf = _compare_family(l_t)
                rf = _compare_family(r_t)
                if lf is not None and rf is not None and lf != rf:
                    raise ValueError(
                        f"mismatched compare operand families: {l_t} and {r_t} (no implicit conversion)")
            elif op in ("+", "-", "*", "/", "%") and l_t == "string" and r_t == "string":
                # 5.2 slice 8: `+` is not concatenation — the pinned wording
                raise ValueError(f"cannot apply '{op}' to string operands (concatenation is str.concat)")
            left = self._emit_expression(expr.left)
            right = self._emit_expression(expr.right)

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
            if self._resolve_expr_type(expr.operand) == "dyn":
                raise ValueError(self.DYN_GATE_ERROR)
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
                        elif expr.callee.member == "realloc":
                            # §4.3: resize a persistent heap block
                            return self._lower_mem_realloc(expr.args)
                        elif expr.callee.member in ("copy", "move", "set"):
                            # §4.3: raw byte primitives (C memcpy trio)
                            return self._lower_mem_byte_op(expr.callee.member, expr.args)

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
                        # 5.4 S2: closed-namespace lowering — _fs_expect
                        # lives on the emit path (checker + emitter in one);
                        # the legacy six keep their _lower_fs_* emitters
                        # byte-identically, the metadata family rides the
                        # new runtime helpers.
                        return self._emit_fs_call(expr.callee.member, expr.args)

                    elif expr.callee.target.name == "str":
                        if expr.callee.member == "len":
                            return f"((usize)strlen({self._emit_expression(expr.args[0])}))"
                        if expr.callee.member in STR_RUNTIME_MEMBERS:
                            # 5.1: compile-check, then one runtime helper call
                            # (single evaluation per argument, guaranteed).
                            self._str_expect(expr.callee.member, expr.args)
                            codes = [self._emit_expression(a) for a in expr.args]
                            return f"velo_str_{expr.callee.member}({', '.join(codes)})"

                    elif expr.callee.target.name == "math":
                        # 5.3: direct C99 libm lowering — int/float args widen
                        # through (double)(...) casts (math.sqrt(2) is legal);
                        # bool/string/collection args reject in _math_expect.
                        return self._emit_math_call(expr.callee.member, expr.args)

                    elif expr.callee.target.name == "time":
                        # 5.5: one runtime helper per member (_time_expect
                        # lives on the emit path — checker + emitter in one).
                        return self._emit_time_call(expr.callee.member, expr.args)

                    elif expr.callee.target.name == "os":
                        # 5.4 S1: one runtime helper per member — exit
                        # lowers straight onto C's exit (_os_expect lives on
                        # the emit path — checker + emitter in one).
                        return self._emit_os_call(expr.callee.member, expr.args)

                # 5.2: shelf receiver member calls — put/take helpers, compile-checked
                target_type = self._resolve_expr_type(expr.callee.target)
                if self._shelf_elem_type(target_type) is not None:
                    self._shelf_expect(expr.callee.member, expr.callee.target, expr.args)
                    elem = self._shelf_elem_type(target_type)
                    target_code = self._emit_expression(expr.callee.target)
                    rec = f"({target_code})" if target_type.startswith("@") else f"&({target_code})"
                    elem_c = self._map_type(elem)
                    if expr.callee.member == "put":
                        slot = self._fresh_name("esl_")
                        arg_code = self._emit_expression(expr.args[0])
                        if elem == "dyn":
                            # 5.2 slice 2: box the appended value into the tag
                            raw = self._infer_raw_velo_type(expr.args[0])
                            if raw != "dyn":
                                arg_code = self._emit_dyn_box(raw, arg_code, expr.args[0])
                        return (f"({{ {elem_c} {slot} = ({arg_code}); "
                                f"velo_shelf_put({rec}, (const void*)(&{slot}), (usize)sizeof({elem_c})); }})")
                    if expr.callee.member == "insert":
                        # 5.2 slice 3: grow-and-shift; i == len appends; the
                        # element contract matches put (dyn values box)
                        slot = self._fresh_name("esl_")
                        idx_code = self._emit_expression(expr.args[0])
                        arg_code = self._emit_expression(expr.args[1])
                        if elem == "dyn":
                            raw = self._infer_raw_velo_type(expr.args[1])
                            if raw != "dyn":
                                arg_code = self._emit_dyn_box(raw, arg_code, expr.args[1])
                        return (f"({{ {elem_c} {slot} = ({arg_code}); "
                                f"velo_shelf_insert({rec}, (usize)({idx_code}), (const void*)(&{slot}), "
                                f"(usize)sizeof({elem_c})); }})")
                    if expr.callee.member == "remove_at":
                        # returns the removed element BY VALUE (the runtime
                        # stash-copies the victim before shifting the tail)
                        idx_code = self._emit_expression(expr.args[0])
                        return f"(*(({elem_c}*)velo_shelf_remove_at({rec}, (usize)({idx_code}))))"
                    if expr.callee.member == "sorted":
                        # 5.2 slice 3: fresh copy, ascending natural order —
                        # the wrapper token is the ELEMENT SPELLING (i32/f64/string)
                        out = self._fresh_name("srt_")
                        return f"({{ VeloShelf {out} = velo_shelf_sorted_{elem}({rec}); {out}; }})"
                    if expr.callee.member == "reversed":
                        # 5.2 slice 4: fresh copy, elements reversed — one
                        # runtime function for every element family
                        out = self._fresh_name("rev_")
                        return f"({{ VeloShelf {out} = velo_shelf_reversed({rec}); {out}; }})"
                    if expr.callee.member == "join":
                        # 5.2 slice 5: per-family stringify at runtime (the
                        # interpolation printf ladder), separator verbatim;
                        # fresh arena string returned by value
                        out = self._fresh_name("jj_")
                        sep_code = self._emit_expression(expr.args[0])
                        return (f"({{ const char* {out} = velo_shelf_join_{elem}({rec}, "
                                f"(const char*)({sep_code})); {out}; }})")
                    return f"(*(({elem_c}*)velo_shelf_take({rec})))"

                # 5.2 slice 6: map receiver member calls — put/get/has,
                # compile-checked; `_map_expect` mirrors the Stage 2 checker
                kv = self._map_kv(target_type)
                if kv is not None:
                    self._map_expect(expr.callee.member, expr.callee.target, expr.args, kv)
                    target_code = self._emit_expression(expr.callee.target)
                    rec = f"({target_code})" if target_type.startswith("@") else f"&({target_code})"
                    key_c = self._map_key_slot_c(kv[0])
                    val_c = self._map_type(kv[1])
                    k_slot = self._fresh_name("mk_")
                    key_code = self._emit_expression(expr.args[0])
                    if expr.callee.member == "put":
                        v_slot = self._fresh_name("mv_")
                        val_code = self._emit_expression(expr.args[1])
                        if kv[1] == "dyn":
                            # 5.2 slice 2: box the stored value into the tag
                            raw = self._infer_raw_velo_type(expr.args[1])
                            if raw != "dyn":
                                val_code = self._emit_dyn_box(raw, val_code, expr.args[1])
                        return (f"({{ {key_c} {k_slot} = ({key_code}); {val_c} {v_slot} = ({val_code}); "
                                f"velo_map_put({rec}, (const void*)(&{k_slot}), (const void*)(&{v_slot})); }})")
                    if expr.callee.member == "get":
                        v_slot = self._fresh_name("mv_")
                        return (f"({{ {key_c} {k_slot} = ({key_code}); {val_c} {v_slot}; "
                                f"if (!velo_map_copy_out({rec}, (const void*)(&{k_slot}), (void*)(&{v_slot}))) "
                                f"velo_map_fatal_missing({rec}, (const void*)(&{k_slot}), \"{kv[0]}\"); {v_slot}; }})")
                    if expr.callee.member == "get_or":
                        # 5.2 slice 7: absence without an option type. The key
                        # binds first; the default is LAZY — evaluated only
                        # inside the miss branch, never on the hit. A dyn V
                        # boxes the default at the miss-assign.
                        v_slot = self._fresh_name("mv_")
                        val_code = self._emit_expression(expr.args[1])
                        if kv[1] == "dyn":
                            raw = self._infer_raw_velo_type(expr.args[1])
                            if raw != "dyn":
                                val_code = self._emit_dyn_box(raw, val_code, expr.args[1])
                        return (f"({{ {key_c} {k_slot} = ({key_code}); {val_c} {v_slot}; "
                                f"if (!velo_map_copy_out({rec}, (const void*)(&{k_slot}), (void*)(&{v_slot}))) "
                                f"{{ {v_slot} = ({val_code}); }} {v_slot}; }})")
                    if expr.callee.member == "take":
                        # 5.2 slice 7: remove at most once — value copies out
                        # FIRST, then the slot tombstones; a miss is the loud
                        # fatal family byte-identical with get/subscript.
                        v_slot = self._fresh_name("mv_")
                        return (f"({{ {key_c} {k_slot} = ({key_code}); {val_c} {v_slot}; "
                                f"if (!velo_map_take({rec}, (const void*)(&{k_slot}), (void*)(&{v_slot}))) "
                                f"velo_map_fatal_missing({rec}, (const void*)(&{k_slot}), \"{kv[0]}\"); {v_slot}; }})")
                    return (f"({{ {key_c} {k_slot} = ({key_code}); "
                            f"velo_map_has({rec}, (const void*)(&{k_slot})); }})")

                # 5.2 slice 9: ring receiver member calls — put/pop/peek,
                # compile-checked; `_ring_expect` mirrors the Stage 2 checker
                ring_elem = self._ring_elem_type(target_type)
                if ring_elem is not None:
                    self._ring_expect(expr.callee.member, expr.callee.target, expr.args, ring_elem)
                    target_code = self._emit_expression(expr.callee.target)
                    rec = f"({target_code})" if target_type.startswith("@") else f"&({target_code})"
                    elem_c = self._map_type(ring_elem)
                    if expr.callee.member == "put":
                        slot = self._fresh_name("rpl_")
                        val_code = self._emit_expression(expr.args[0])
                        return (f"({{ {elem_c} {slot} = ({val_code}); "
                                f"velo_ring_put({rec}, (const void*)(&{slot}), (usize)sizeof({elem_c})); }})")
                    if expr.callee.member == "pop":
                        # value copies out FIRST, then the head advances (the
                        # take discipline); empty is the loud fatal family
                        slot = self._fresh_name("rpo_")
                        return (f"({{ {elem_c} {slot}; velo_ring_pop({rec}, (void*)(&{slot}), (usize)sizeof({elem_c})); {slot}; }})")
                    slot = self._fresh_name("rpk_")
                    return (f"({{ {elem_c} {slot}; velo_ring_peek({rec}, (void*)(&{slot}), (usize)sizeof({elem_c})); {slot}; }})")

                # 5.2 slice 9: bitset receiver member calls
                if target_type.lstrip("@") == "bitset":
                    self._bitset_expect(expr.callee.member, expr.callee.target, expr.args)
                    target_code = self._emit_expression(expr.callee.target)
                    rec = f"({target_code})" if target_type.startswith("@") else f"&({target_code})"
                    if expr.callee.member in ("set", "clear", "toggle"):
                        idx_code = self._emit_expression(expr.args[0])
                        return f"velo_bitset_{expr.callee.member}({rec}, (int64_t)({idx_code}))"
                    if expr.callee.member == "has":
                        idx_code = self._emit_expression(expr.args[0])
                        return f"velo_bitset_has({rec}, (int64_t)({idx_code}))"
                    if expr.callee.member == "count":
                        return f"velo_bitset_count({rec})"
                    if expr.callee.member == "first_unset":
                        return f"((int32_t)velo_bitset_first_unset({rec}))"
                    if expr.callee.member == "flip":
                        return f"velo_bitset_flip({rec})"
                    # and / or_with / xor_with — the other binds first
                    other_code = self._emit_expression(expr.args[0])
                    other_t = self._resolve_expr_type(expr.args[0])
                    other_rec = f"({other_code})" if other_t.startswith("@") else f"&({other_code})"
                    rt = {"and": "and", "or_with": "or", "xor_with": "xor"}[expr.callee.member]
                    return f"velo_bitset_{rt}({rec}, {other_rec})"

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

            # 5.2: shelf element types must string-match across call boundaries —
            # a silent VeloShelf↔VeloShelf pass-through would corrupt reads (esz)
            decl = self.func_decls.get(expr.callee.name) if isinstance(expr.callee, Identifier) else None
            if decl is not None:
                for p, a in zip(decl.params, expr.args):
                    want = (p.type_name or "").strip()
                    want_l = want.lstrip("@")
                    if want_l.startswith("shelf["):
                        # 5.2: shelf element types must string-match across call
                        # boundaries — a silent VeloShelf↔VeloShelf pass-through
                        # would corrupt reads (esz). Slice 10: heap spellings
                        # count as shelf spellings (strict, both directions)
                        got = self._resolve_expr_type(a)
                        got_l = got.lstrip("@")
                        if (got_l.startswith("shelf[") or got_l.startswith("heap shelf[")) and got != want:
                            raise ValueError(f"shelf argument element types must match exactly: got {got}, expected {want}")
                    elif want_l.startswith("Map["):
                        # 5.2 slice 6: maps string-match BOTH slots across calls
                        got = self._resolve_expr_type(a)
                        if got.lstrip("@").startswith("Map[") and got != want:
                            raise ValueError(f"map argument types must match exactly: got {got}, expected {want}")
                    elif want_l.startswith("ring["):
                        # 5.2 slice 9: rings string-match the element slot
                        got = self._resolve_expr_type(a)
                        if got.lstrip("@").startswith("ring[") and got != want:
                            raise ValueError(f"ring argument element types must match exactly: got {got}, expected {want}")
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

    def _is_ptr_like(self, got: str) -> bool:
        # §4.3: pointer-ish values (@T handles, @void from null). Plain
        # "string" is deliberately NOT accepted as a byte buffer — writing
        # through a const char* is UB; use @u8 for buffers.
        return bool(got) and got[0] == "@"

    def _is_count_like(self, got: str) -> bool:
        # §4.3: byte counts / fill values must not be pointers, strings,
        # acts, or void — anything else (ints, floats, bools) casts to a
        # number and is the caller's precision business. void matters
        # because callers reach it via io calls (io.println returns void)
        # and the stages DIVERGE on it: Stage 2 inlines io emission as
        # int-valued printf, so admitting void would silently produce
        # count = chars-printed instead of failing like Stage 1.
        if not got or got[0] == "@" or got == "string" or got == "void":
            return False
        t = got.replace(" ", "").replace("\t", "")
        return not t.startswith("act(")

    def _mem_expect(self, member: str, args: List[Expr]) -> None:
        """§4.3: compile-checks mem.copy/move/set/realloc arguments.
        Mirrored by the Stage 2 type checker — both stages must reject
        the same programs with the same messages."""
        sigs = {
            "copy": ": (pointer dest, pointer src, byte count)",
            "move": ": (pointer dest, pointer src, byte count)",
            "set": ": (pointer dest, byte value, byte count)",
            "realloc": ": (pointer, @Type, count)",
        }
        if member not in sigs:
            return  # alloc/heap_alloc/free etc. keep their legacy checks
        if len(args) != 3:
            raise ValueError(f"mem.{member} expects exactly 3 arguments{sigs[member]}")
        # _thread_arg_type (shared with 4.2) instead of bare resolve: it ALSO
        # renders named-function identifiers as their act types, matching
        # Stage 2's infer of a bare act name — without this, a bare act name
        # as count fell back to "i32" and sailed to a runtime crash while
        # Stage 2 rejected it (parity divergence found in the untested-list
        # audit).
        got = self._thread_arg_type(args[0])
        if not self._is_ptr_like(got):
            raise ValueError(f"mem.{member} expects pointer arguments (got {got})")
        if member == "realloc":
            # @T type arg: render type names as written (Stage 2's
            # is_known_type path reports "i64" for a bare `i64`, not the
            # variable-scope fallback "i32").
            if isinstance(args[1], Identifier) and args[1].name in TYPE_MAP:
                ty = args[1].name
            else:
                ty = self._thread_arg_type(args[1])
            if not self._is_ptr_like(ty):
                raise ValueError(f"mem.realloc expects a @Type argument (got {ty})")
        elif member != "set":
            src_got = self._thread_arg_type(args[1])
            if not self._is_ptr_like(src_got):
                raise ValueError(f"mem.{member} expects pointer arguments (got {src_got})")
        else:
            val_got = self._thread_arg_type(args[1])
            if not self._is_count_like(val_got):
                raise ValueError(f"mem.set expects an integer fill value (got {val_got})")
        cnt = self._thread_arg_type(args[2])
        if not self._is_count_like(cnt):
            word = "fill value" if member == "set" else "byte count"
            raise ValueError(f"mem.{member} expects an integer {word} (got {cnt})")
        # §4.3 hardening: a negative literal count is a caller bug — reject
        # it at compile time when statically knowable (variable-held
        # negatives are caught at runtime by the velo_byte_* wrappers).
        if isinstance(args[2], UnaryExpr) and args[2].op == "-" and isinstance(args[2].operand, IntLiteral):
            raise ValueError(f"mem.{member} expects a non-negative byte count")

    def _str_expect(self, member: str, args: List[Expr]) -> None:
        """5.1: compile-checks the sys.str intrinsics beyond legacy .len.
        Mirrored by Stage 2's src/analysis/str_checks.vl — both stages must
        reject the same programs with the same messages."""
        expect_n = STR_RUNTIME_MEMBERS[member]
        sig = _STR_SIGS[member]
        if len(args) != expect_n:
            plural = "" if expect_n == 1 else "s"
            raise ValueError(f"str.{member} expects exactly {expect_n} argument{plural}{sig}")
        for arg in args:
            got = self._thread_arg_type(arg)
            if got != "string":
                raise ValueError(f"str.{member} expects string arguments (got {got})")

    def _fs_expect(self, member: str, args: List[Expr]) -> None:
        """5.4 S2: compile-checks the sys.fs call surface — the SIX LEGACY
        members migrate into this closed umbrella (result spells preserved
        exactly), joining the six new metadata members. Mirrored by Stage
        2's src/analysis/fs_checks.vl. Every member joins on strings; a
        non-string argument rejects with the os-family got wall (first
        failing argument reported)."""
        if member not in FS_CALLS:
            raise ValueError(
                f"unknown fs member '{member}' (functions: {FS_FUNCS_TEXT})")
        expect_n = FS_CALLS[member]
        if len(args) != expect_n:
            sig = FS_SIGS[member]
            plural = "" if expect_n == 1 else "s"
            raise ValueError(f"fs.{member} expects exactly {expect_n} argument{plural}{sig}")
        for arg in args:
            got = self._thread_arg_type(arg)
            if got != "string":
                raise ValueError(f"fs.{member} expects string arguments (got {got})")

    def _emit_fs_call(self, member: str, args: List[Expr]) -> str:
        # 5.4 S2: the closed-namespace lowering — the legacy six ride their
        # existing _lower_fs_* emitters byte-identically (now pre-checked);
        # the metadata family rides the new runtime helpers. Single
        # evaluation per argument — codes are emitted exactly once each.
        self._fs_expect(member, args)
        if member == "read_file":
            return self._lower_fs_read_file(args)
        if member == "write_file":
            return self._lower_fs_write_file(args)
        if member == "exists":
            return self._lower_fs_exists(args)
        if member == "size":
            return self._lower_fs_size(args)
        if member in ("remove", "remove_file"):
            return self._lower_fs_remove(args)
        code = ", ".join(self._emit_expression(a) for a in args)
        return f"velo_fs_{member}({code})"

    def _os_expect(self, member: str, args: List[Expr]) -> None:
        """5.4 S1: compile-checks the sys.os call surface. Mirrored by
        Stage 2's src/analysis/os_checks.vl — both stages must reject the
        same programs with the same messages. args is zero-ary; get_env
        takes one string key, set_env takes two strings; exit takes one INT
        code (floats/bool/string reject). The namespace is CLOSED for both
        lanes."""
        if member not in OS_CALLS:
            raise ValueError(
                f"unknown os member '{member}' (functions: {OS_FUNCS_TEXT})")
        expect_n = OS_CALLS[member]
        if len(args) != expect_n:
            sig = OS_SIGS.get(member, "")
            plural = "" if expect_n == 1 else "s"
            raise ValueError(f"os.{member} expects exactly {expect_n} argument{plural}{sig}")
        n_str = OS_STRING_ARGS.get(member, 0)
        for i, arg in enumerate(args):
            got = self._thread_arg_type(arg)
            if i < n_str:
                if got != "string":
                    raise ValueError(f"os.{member} expects string arguments (got {got})")
            else:
                if got not in DYN_INT_TYPES:
                    raise ValueError(f"os.{member} expects int arguments (got {got})")

    def _emit_os_call(self, member: str, args: List[Expr]) -> str:
        # 5.4 S1: one runtime helper per member — exit lowers DIRECTLY onto
        # C's exit (stdlib.h is already in the runtime). Single evaluation
        # per argument — codes are emitted exactly once each.
        self._os_expect(member, args)
        if member == "args":
            return "velo_os_args()"
        if member == "get_env":
            return f"velo_os_get_env({self._emit_expression(args[0])})"
        if member == "set_env":
            return (f"velo_os_set_env({self._emit_expression(args[0])}, "
                    f"{self._emit_expression(args[1])})")
        return f"exit((int)({self._emit_expression(args[0])}))"

    def _time_expect(self, member: str, args: List[Expr]) -> None:
        """5.5: compile-checks the sys.time call surface. Mirrored by
        Stage 2's src/analysis/time_checks.vl — both stages must reject the
        same programs with the same messages. now/delta are zero-ary;
        sleep_ms takes exactly one INT duration (every int spell rides an
        emitted (long long)(...) widen; f32/f64/bool/string/collections
        reject). The namespace is CLOSED for both lanes."""
        if member not in TIME_CALLS:
            raise ValueError(
                f"unknown time member '{member}' (functions: {TIME_FUNCS_TEXT})")
        expect_n = TIME_CALLS[member]
        if len(args) != expect_n:
            sig = TIME_SIGS.get(member, "")
            plural = "" if expect_n == 1 else "s"
            raise ValueError(f"time.{member} expects exactly {expect_n} argument{plural}{sig}")
        for arg in args:
            got = self._thread_arg_type(arg)
            if got not in DYN_INT_TYPES:
                raise ValueError(f"time.sleep_ms expects int arguments (got {got})")

    def _emit_time_call(self, member: str, args: List[Expr]) -> str:
        # 5.5: one runtime helper per member (velo_runtime.h owns the
        # platform #if). Single evaluation per argument — codes are emitted
        # exactly once each; the duration rides a (long long)(...) widen.
        self._time_expect(member, args)
        if member == "now":
            return "velo_time_now_us()"
        if member == "delta":
            return "velo_time_delta_us()"
        return f"velo_time_sleep((long long)({self._emit_expression(args[0])}))"

    def _math_expect(self, member: str, args: List[Expr]) -> None:
        """5.3: compile-checks the sys.math call surface (constants live on
        the property path below). Mirrored by Stage 2's
        src/analysis/math_checks.vl — both stages must reject the same
        programs with the same messages. Args widen: every int spell and
        f32/f64 ride an emitted (double)(...) cast; bool/string/collections
        reject."""
        if member not in MATH_CALLS:
            # 5.3: the math namespace is CLOSED for calls (shelf unknown
            # member precedent): both stages reject with the same words.
            # The functions list grows per slice (S2 adds the trig family).
            raise ValueError(
                f"unknown math member '{member}' (functions: sqrt, pow, cbrt, sin, cos, tan, atan2, acos, asin, exp, log, log2, abs, min, max, floor, ceil, round, clamp, lerp; constants: PI, TAU, RAD2DEG, DEG2RAD are available)")
        expect_n, sig = MATH_CALLS[member]
        if len(args) != expect_n:
            plural = "" if expect_n == 1 else "s"
            raise ValueError(f"math.{member} expects exactly {expect_n} argument{plural}{sig}")
        for arg in args:
            got = self._thread_arg_type(arg)
            if got not in DYN_INT_TYPES and got not in DYN_FLOAT_TYPES:
                raise ValueError(f"math.{member} expects f64 (or int) arguments (got {got})")

    def _emit_math_call(self, member: str, args: List[Expr]) -> str:
        # 5.3: direct C99 libm lowering (single evaluation per argument,
        # guaranteed — codes are emitted exactly once each).
        self._math_expect(member, args)
        codes = [self._emit_expression(a) for a in args]
        # S4: abs/min/max branch on the argument spells (verified valid by
        # _math_expect above — every spelling is in the int/float set).
        types = [self._thread_arg_type(a) for a in args]
        if member == "sqrt":
            return f"sqrt((double)({codes[0]}))"
        if member == "pow":
            return f"pow((double)({codes[0]}), (double)({codes[1]}))"
        if member == "cbrt":
            return f"cbrt((double)({codes[0]}))"
        # 5.3 slice 2: the trig family — same widening shape, atan2 is 2-ary
        if member == "sin":
            return f"sin((double)({codes[0]}))"
        if member == "cos":
            return f"cos((double)({codes[0]}))"
        if member == "tan":
            return f"tan((double)({codes[0]}))"
        if member == "atan2":
            return f"atan2((double)({codes[0]}), (double)({codes[1]}))"
        if member == "acos":
            return f"acos((double)({codes[0]}))"
        if member == "asin":
            return f"asin((double)({codes[0]}))"
        # 5.3 slice 3: exponentials & logs (log10 deliberately unshipped —
        # not on the gaps 5.3 list; it rides the closed-set wording)
        if member == "exp":
            return f"exp((double)({codes[0]}))"
        if member == "log":
            return f"log((double)({codes[0]}))"
        if member == "log2":
            return f"log2((double)({codes[0]}))"
        # 5.3 slice 4: the utility family. abs rides fabs for floats;
        # unsigned ints are the identity (abs of a non-negative value);
        # signed ints go through llabs at the argument's exact spell.
        # min/max: any float arg lifts to fmin/fmax (each argument emitted
        # exactly once); equal int spells use a C ternary over that spell;
        # mixed int widths cast both sides to i64 first (signedness-safe).
        # The ternary shapes re-evaluate each argument twice (documented
        # residual — battery pins literal/local spellings only).
        if member == "floor":
            return f"floor((double)({codes[0]}))"
        if member == "ceil":
            return f"ceil((double)({codes[0]}))"
        if member == "round":
            return f"round((double)({codes[0]}))"
        if member == "abs":
            t = types[0]
            if t in DYN_FLOAT_TYPES:
                return f"fabs((double)({codes[0]}))"
            if t in ("u8", "u16", "u32", "u64", "usize"):
                return f"({codes[0]})"
            return f"({t})llabs((long long)({codes[0]}))"
        if member in ("min", "max"):
            op = "<" if member == "min" else ">"
            if types[0] in DYN_FLOAT_TYPES or types[1] in DYN_FLOAT_TYPES:
                fn = "fmin" if member == "min" else "fmax"
                return f"{fn}((double)({codes[0]}), (double)({codes[1]}))"
            if types[0] == types[1]:
                spell = types[0]
                return (f"(({spell})(({codes[0]}) {op} ({codes[1]}) "
                        f"? ({codes[0]}) : ({codes[1]})))")
            w0 = f"(i64)({codes[0]})"
            w1 = f"(i64)({codes[1]})"
            return f"((i64)(({w0}) {op} ({w1}) ? ({w0}) : ({w1})))"
        if member == "clamp":
            # Canonical order (v, lo, hi): inner fmax clamps the floor,
            # outer fmin clamps the ceiling — each argument emitted once.
            return (f"fmin(fmax((double)({codes[0]}), (double)({codes[1]})), "
                    f"(double)({codes[2]}))")
        if member == "lerp":
            # (a + (b - a) * t) with every argument widened through
            # (double)(...); a appears twice (documented residual).
            d0 = f"(double)({codes[0]})"
            d1 = f"(double)({codes[1]})"
            d2 = f"(double)({codes[2]})"
            return f"(({d0}) + (({d1}) - ({d0})) * ({d2}))"
        raise ValueError(f"unknown math member '{member}'")

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

    def _lower_mem_realloc(self, args: List[Expr]) -> str:
        # §4.3: mem.realloc(ptr, @Type, count) -> @Type — keeps the heap
        # size-header protocol and the atomic ledger exact.
        self._mem_expect("realloc", args)
        type_name = self._extract_type_name(args[1])
        c_type = self._map_type(type_name)
        ptr_code = self._emit_expression(args[0])
        cnt_code = self._emit_expression(args[2])
        return f"({c_type}*)velo_heap_realloc((void*)({ptr_code}), sizeof({c_type}), (long long)({cnt_code}))"

    def _lower_mem_byte_op(self, member: str, args: List[Expr]) -> str:
        # §4.3: mem.copy/move/set map straight onto the C trio; type
        # checking happened in _mem_expect, emission is byte-level.
        self._mem_expect(member, args)
        d = self._emit_expression(args[0])
        s = self._emit_expression(args[1])
        c = self._emit_expression(args[2])
        if member == "set":
            return f"velo_byte_set((void*)({d}), (int)({s}), (long long)({c}))"
        cfn = "velo_byte_copy" if member == "copy" else "velo_byte_move"
        return f"{cfn}((void*)({d}), (void*)({s}), (long long)({c}))"

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
        path_code = self._emit_expression(args[0])
        return f"velo_fs_read_file({path_code})"

    def _lower_fs_write_file(self, args: List[Expr]) -> str:
        path_code = self._emit_expression(args[0])
        content_code = self._emit_expression(args[1])
        return f"velo_fs_write_file({path_code}, {content_code})"

    def _lower_fs_exists(self, args: List[Expr]) -> str:
        path_code = self._emit_expression(args[0])
        return f"velo_fs_exists({path_code})"

    def _lower_fs_size(self, args: List[Expr]) -> str:
        path_code = self._emit_expression(args[0])
        return f"velo_fs_size({path_code})"

    def _lower_fs_remove(self, args: List[Expr]) -> str:
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

                    if resolved_type == "dyn":
                        # 5.2 slice 2: raw dyn prints nothing useful — cast (as) first
                        raise ValueError(self.DYN_GATE_ERROR)

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
        if resolved == "dyn":
            raise ValueError(self.DYN_GATE_ERROR)
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

        # 5.3: math constants ride interpolations as bare member paths
        # ({math.PI} → f64 — the emit side spells the shared digits)
        if path.startswith("math.") and path[5:] in MATH_CONSTANTS:
            return "f64"

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

        # 5.3: math constants emit the shared decimal literals (digits
        # identical to math_checks.vl) wrapped in parens
        if path.startswith("math.") and path[5:] in MATH_CONSTANTS:
            return f"({MATH_CONSTANTS[path[5:]]})"

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
