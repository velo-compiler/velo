from enum import Enum, auto
from dataclasses import dataclass
from typing import Any

class TokenType(Enum):
    # Keywords
    ACT = auto()
    DATA = auto()
    MUT = auto()
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    LOOP = auto()
    IN = auto()
    RETURN = auto()
    ZONE = auto()
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
    ARROW = auto()        # ->
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
    "while": TokenType.WHILE,
    "loop": TokenType.LOOP,
    "in": TokenType.IN,
    "return": TokenType.RETURN,
    "zone": TokenType.ZONE,
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
}

@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"
