from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional

class TokenType(Enum):
    # Keywords
    ACT = auto()
    DATA = auto()
    MUT = auto()
    LET = auto()
    IF = auto()
    ELSE = auto()
    LOOP = auto()
    IN = auto()
    RETURN = auto()
    ZONE = auto()
    DEFER = auto()
    EXTERN = auto()
    USE = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    SIZEOF = auto()
    AS = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    BREAK = auto()
    CONTINUE = auto()
    ON = auto()
    KIND = auto()
    OP = auto()
    SHELF = auto()
    MAP = auto()
    # 5.2 slice 9: `ring` / `bitset` — reserved for the literal forms.
    RING = auto()
    BITSET = auto()
    # 5.2 slice 10: `heap` — the heap-shelf storage modifier.
    HEAP = auto()
    OF = auto()

    # Literals
    IDENTIFIER = auto()
    INT_LIT = auto()
    FLOAT_LIT = auto()
    STRING_LIT = auto()

    # Operators & Memory
    AT = auto()           # @ (address-of / pointer type)
    PLUS = auto()         # +
    MINUS = auto()        # -
    STAR = auto()         # *
    SLASH = auto()        # /
    PERCENT = auto()      # %
    DOT = auto()          # .
    DOTDOT = auto()       # ..
    DOTDOTEQ = auto()     # ..=
    ARROW = auto()        # ->
    FAT_ARROW = auto()    # =>
    BANG = auto()         # !

    # Comparisons & Assignments
    ASSIGN = auto()       # =
    PLUS_ASSIGN = auto()  # +=
    MINUS_ASSIGN = auto() # -=
    STAR_ASSIGN = auto()  # *=
    SLASH_ASSIGN = auto() # /=
    EQ = auto()           # ==
    NE = auto()           # !=
    LT = auto()           # <
    LE = auto()           # <=
    GT = auto()           # >
    GE = auto()           # >=
    # Bitwise Operators & Assignments
    AMP = auto()          # &
    PIPE = auto()         # |
    CARET = auto()        # ^
    TILDE = auto()        # ~
    SHL = auto()          # <<
    SHR = auto()          # >>
    AMP_ASSIGN = auto()   # &=
    PIPE_ASSIGN = auto()  # |=
    CARET_ASSIGN = auto() # ^=
    SHL_ASSIGN = auto()   # <<=
    SHR_ASSIGN = auto()   # >>=

    # Delimiters
    LPAREN = auto()       # (
    RPAREN = auto()       # )
    LBRACE = auto()       # {
    RBRACE = auto()       # }
    LBRACKET = auto()     # [
    RBRACKET = auto()     # ]
    COMMA = auto()        # ,
    COLON = auto()        # :
    SEMICOLON = auto()    # ;
    HASH = auto()         # # (struct attribute marker)

    # Formatting / Stream
    NEWLINE = auto()
    EOF = auto()

KEYWORDS = {
    "act": TokenType.ACT,
    "data": TokenType.DATA,
    "mut": TokenType.MUT,
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "loop": TokenType.LOOP,
    "in": TokenType.IN,
    "return": TokenType.RETURN,
    "zone": TokenType.ZONE,
    "defer": TokenType.DEFER,
    "extern": TokenType.EXTERN,
    "use": TokenType.USE,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "sizeof": TokenType.SIZEOF,
    "as": TokenType.AS,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "on": TokenType.ON,
    "kind": TokenType.KIND,
    "op": TokenType.OP,
    # 5.2: `shelf` (dynamic collections) and `of` (value iteration) are
    # reserved words. `shelf[` must be grammar-stable, NOT scope-dependent,
    # so `shelf` is a true keyword (documented trade in gaps.md §5.2).
    "shelf": TokenType.SHELF,
    # 5.2 slice 6: `map` is reserved for the literal form `map[k: v, ...]`;
    # the TYPE spelling `Map[K, V]` stays a plain identifier (capital). Same
    # grammar-stability trade as `shelf` documented in gaps.md §5.2.
    "map": TokenType.MAP,
    # 5.2 slice 9: `ring` / `bitset` are reserved for their literal forms.
    "ring": TokenType.RING,
    "bitset": TokenType.BITSET,
    # 5.2 slice 10: `heap` is reserved — the heap-shelf storage modifier
    # (`heap shelf[T]` types, `heap shelf[...]` literals).
    "heap": TokenType.HEAP,
    "of": TokenType.OF,
}

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int
    raw_str: Optional[str] = None
    type_name: Optional[str] = None

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"
