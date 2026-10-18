from typing import List, Optional
from velo.tokens import Token, TokenType, KEYWORDS

class LexerError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Lexer Error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col

class Lexer:
    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

    def _peek(self, offset: int = 0) -> Optional[str]:
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return None

    def _advance(self) -> Optional[str]:
        ch = self._peek()
        if ch is not None:
            self.pos += 1
            if ch == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def tokenize(self) -> List[Token]:
        last_meaningful_token: Optional[Token] = None

        while self.pos < len(self.source):
            ch = self._peek()

            # Skip spaces, tabs, carriage returns
            if ch in (' ', '\t', '\r'):
                self._advance()
                continue

            # Comments
            if ch == '/' and self._peek(1) == '/':
                # Single-line comment
                while self._peek() is not None and self._peek() != '\n':
                    self._advance()
                continue
            elif ch == '/' and self._peek(1) == '*':
                # Multi-line comment
                start_line = self.line
                start_col = self.col
                self._advance() # '/'
                self._advance() # '*'
                depth = 1
                while depth > 0:
                    curr = self._peek()
                    if curr is None:
                        raise LexerError("Unterminated block comment", start_line, start_col)
                    if curr == '/' and self._peek(1) == '*':
                        self._advance()
                        self._advance()
                        depth += 1
                    elif curr == '*' and self._peek(1) == '/':
                        self._advance()
                        self._advance()
                        depth -= 1
                    else:
                        self._advance()
                continue

            # Newline handling (Go-style statement termination)
            if ch == '\n':
                token_line = self.line
                token_col = self.col
                self._advance()

                # Rule: Emit NEWLINE only if previous token can terminate a statement
                if last_meaningful_token and last_meaningful_token.type in (
                    TokenType.IDENTIFIER,
                    TokenType.INT_LIT,
                    TokenType.FLOAT_LIT,
                    TokenType.STRING_LIT,
                    TokenType.TRUE,
                    TokenType.FALSE,
                    TokenType.NULL,
                    TokenType.RETURN,
                    TokenType.RPAREN,
                    TokenType.RBRACE,
                    TokenType.RBRACKET,
                ):
                    tok = Token(TokenType.NEWLINE, "\n", token_line, token_col)
                    self.tokens.append(tok)
                    last_meaningful_token = tok
                continue

            # Semicolon (explicit statement separator)
            if ch == ';':
                tok = Token(TokenType.SEMICOLON, ";", self.line, self.col)
                self._advance()
                self.tokens.append(tok)
                last_meaningful_token = tok
                continue

            start_line = self.line
            start_col = self.col

            # String literals
            if ch == '"':
                tok = self._scan_string(start_line, start_col)
                self.tokens.append(tok)
                last_meaningful_token = tok
                continue

            # Numbers
            if ch.isdigit():
                tok = self._scan_number(start_line, start_col)
                self.tokens.append(tok)
                last_meaningful_token = tok
                continue

            # Identifiers and Keywords
            if ch.isalpha() or ch == '_':
                tok = self._scan_identifier(start_line, start_col)
                self.tokens.append(tok)
                last_meaningful_token = tok
                continue

            # Multi-character & Single-character operators
            tok = self._scan_operator(start_line, start_col)
            self.tokens.append(tok)
            last_meaningful_token = tok

        # End of File token
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return self.tokens

    def _scan_string(self, line: int, col: int) -> Token:
        self._advance() # Consume opening '"'
        chars = []
        while True:
            ch = self._peek()
            if ch is None:
                raise LexerError("Unterminated string literal", line, col)
            if ch == '"':
                self._advance() # Consume closing '"'
                break
            if ch == '\\':
                self._advance()
                escape = self._advance()
                if escape == 'n': chars.append('\n')
                elif escape == 't': chars.append('\t')
                elif escape == 'r': chars.append('\r')
                elif escape == '"': chars.append('"')
                elif escape == '\\': chars.append('\\')
                elif escape == '{': chars.append('{')
                elif escape == '}': chars.append('}')
                else:
                    raise LexerError(f"Unknown escape sequence '\\{escape}'", line, col)
            else:
                chars.append(self._advance())
        return Token(TokenType.STRING_LIT, "".join(chars), line, col)

    def _scan_number(self, line: int, col: int) -> Token:
        chars = []
        is_float = False
        while self._peek() is not None and self._peek().isdigit():
            chars.append(self._advance())

        if self._peek() == '.' and self._peek(1) is not None and self._peek(1).isdigit():
            is_float = True
            chars.append(self._advance()) # '.'
            while self._peek() is not None and self._peek().isdigit():
                chars.append(self._advance())

        num_str = "".join(chars)
        if is_float:
            return Token(TokenType.FLOAT_LIT, float(num_str), line, col)
        return Token(TokenType.INT_LIT, int(num_str), line, col)

    def _scan_identifier(self, line: int, col: int) -> Token:
        chars = []
        while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
            chars.append(self._advance())
        name = "".join(chars)
        token_type = KEYWORDS.get(name, TokenType.IDENTIFIER)
        return Token(token_type, name, line, col)

    def _scan_operator(self, line: int, col: int) -> Token:
        ch = self._advance()

        # Two-character checks
        if ch == '@':
            return Token(TokenType.AT, "@", line, col)
        if ch == '-':
            if self._match('>'): return Token(TokenType.ARROW, "->", line, col)
            if self._match('='): return Token(TokenType.MINUS_ASSIGN, "-=", line, col)
            return Token(TokenType.MINUS, "-", line, col)
        if ch == '+':
            if self._match('='): return Token(TokenType.PLUS_ASSIGN, "+=", line, col)
            return Token(TokenType.PLUS, "+", line, col)
        if ch == '*':
            if self._match('='): return Token(TokenType.STAR_ASSIGN, "*=", line, col)
            return Token(TokenType.STAR, "*", line, col)
        if ch == '/':
            if self._match('='): return Token(TokenType.SLASH_ASSIGN, "/=", line, col)
            return Token(TokenType.SLASH, "/", line, col)
        if ch == '%':
            return Token(TokenType.PERCENT, "%", line, col)
        if ch == '.':
            if self._match('.'): return Token(TokenType.DOTDOT, "..", line, col)
            return Token(TokenType.DOT, ".", line, col)
        if ch == '=':
            if self._match('='): return Token(TokenType.EQ, "==", line, col)
            return Token(TokenType.ASSIGN, "=", line, col)
        if ch == '!':
            if self._match('='): return Token(TokenType.NE, "!=", line, col)
            return Token(TokenType.BANG, "!", line, col)
        if ch == '<':
            if self._match('='): return Token(TokenType.LE, "<=", line, col)
            return Token(TokenType.LT, "<", line, col)
        if ch == '>':
            if self._match('='): return Token(TokenType.GE, ">=", line, col)
            return Token(TokenType.GT, ">", line, col)
        if ch == '(': return Token(TokenType.LPAREN, "(", line, col)
        if ch == ')': return Token(TokenType.RPAREN, ")", line, col)
        if ch == '{': return Token(TokenType.LBRACE, "{", line, col)
        if ch == '}': return Token(TokenType.RBRACE, "}", line, col)
        if ch == '[': return Token(TokenType.LBRACKET, "[", line, col)
        if ch == ']': return Token(TokenType.RBRACKET, "]", line, col)
        if ch == ',': return Token(TokenType.COMMA, ",", line, col)
        if ch == ':': return Token(TokenType.COLON, ":", line, col)

        raise LexerError(f"Unexpected character '{ch}'", line, col)
