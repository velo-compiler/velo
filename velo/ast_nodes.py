from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

# Base AST Node
class ASTNode:
    pass

class Expr(ASTNode):
    pass

class Stmt(ASTNode):
    pass

class Decl(ASTNode):
    pass

# Expressions
@dataclass
class IntLiteral(Expr):
    value: int
    line: int
    col: int
    raw_str: Optional[str] = None
    type_name: Optional[str] = None

@dataclass
class FloatLiteral(Expr):
    value: float
    line: int
    col: int
    raw_str: Optional[str] = None
    type_name: Optional[str] = None

@dataclass
class StringLiteral(Expr):
    value: str
    line: int
    col: int

@dataclass
class BoolLiteral(Expr):
    value: bool
    line: int
    col: int

@dataclass
class NullLiteral(Expr):
    line: int
    col: int

@dataclass
class Identifier(Expr):
    name: str
    line: int
    col: int

@dataclass
class MemberAccess(Expr):
    target: Expr
    member: str
    line: int
    col: int

@dataclass
class IndexExpr(Expr):
    target: Expr
    index: Expr
    line: int
    col: int

@dataclass
class DerefExpr(Expr):
    operand: Expr
    line: int
    col: int

@dataclass
class StructLiteral(Expr):
    struct_name: str
    field_inits: List[Tuple[str, Expr]]
    line: int
    col: int

@dataclass
class CastExpr(Expr):
    expr: Expr
    target_type: str
    line: int
    col: int

@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]
    line: int
    col: int
    type_args: Optional[List[str]] = None

@dataclass
class AddressOf(Expr):
    operand: Expr
    line: int
    col: int

@dataclass
class BinaryExpr(Expr):
    left: Expr
    op: str
    right: Expr
    line: int
    col: int

@dataclass
class UnaryExpr(Expr):
    op: str
    operand: Expr
    line: int
    col: int

@dataclass
class VariantExpr(Expr):
    kind_name: Optional[str]
    variant_name: str
    args: List[Expr]
    line: int
    col: int

# Statements
@dataclass
class ExprStmt(Stmt):
    expr: Expr
    line: int
    col: int

@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]
    line: int
    col: int

@dataclass
class BreakStmt(Stmt):
    line: int
    col: int

@dataclass
class ContinueStmt(Stmt):
    line: int
    col: int

@dataclass
class VarDeclStmt(Stmt):
    name: str
    type_name: Optional[str]
    value: Optional[Expr]
    is_mut: bool
    line: int
    col: int

@dataclass
class AssignStmt(Stmt):
    target: Expr
    op: str
    value: Expr
    line: int
    col: int

@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]
    line: int
    col: int

@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: BlockStmt
    else_branch: Optional[Stmt]
    line: int
    col: int

@dataclass
class LoopStmt(Stmt):
    iterator: str
    start_expr: Optional[Expr]
    end_expr: Optional[Expr]
    body: BlockStmt
    line: int
    col: int
    step_expr: Optional[Expr] = None
    is_inclusive: bool = False
    expr: Optional[Expr] = None
    is_count: bool = False

@dataclass
class ZoneStmt(Stmt):
    body: BlockStmt
    line: int
    col: int

@dataclass
class DeferStmt(Stmt):
    statement: Stmt
    line: int
    col: int

@dataclass
class MatchCase:
    values: List[Expr]
    is_default: bool
    body: BlockStmt
    line: int
    col: int

@dataclass
class MatchStmt(Stmt):
    expr: Expr
    cases: List[MatchCase]
    line: int
    col: int

# Top-level Declarations
@dataclass
class Field:
    name: str
    type_name: str
    line: int
    col: int

@dataclass
class DataDecl(Decl):
    name: str
    fields: List[Field]
    line: int
    col: int
    type_params: Optional[List[str]] = None

@dataclass
class VariantDecl:
    name: str
    line: int
    col: int
    discriminant: Optional[int] = None
    payload_type: Optional[str] = None
    fields: Optional[List[Field]] = None

@dataclass
class KindDecl(Decl):
    name: str
    variants: List[VariantDecl]
    line: int
    col: int
    type_params: Optional[List[str]] = None

@dataclass
class Param:
    name: str
    type_name: str
    line: int
    col: int

@dataclass
class FunctionDecl(Decl):
    name: str
    params: List[Param]
    return_type: Optional[str]
    body: BlockStmt
    line: int
    col: int
    type_params: Optional[List[str]] = None

@dataclass
class ExternDecl(Decl):
    name: str
    params: List[Param]
    return_type: Optional[str]
    line: int
    col: int

@dataclass
class UseStmt(Decl):
    module_path: str
    line: int
    col: int

@dataclass
class Program(ASTNode):
    declarations: List[Decl]
