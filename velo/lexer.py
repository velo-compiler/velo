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
                    TokenType.BREAK,
                    TokenType.CONTINUE,
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

            # Raw multi-line string literals (`raw`)
            if ch == '`':
                tok = self._scan_raw_string(start_line, start_col)
                self.tokens.append(tok)
                last_meaningful_token = tok
                continue

            # String literals
            if ch == '"':
                tok = self._scan_string(start_line, start_col)
                self.tokens.append(tok)
                last_meaningful_token = tok
                continue

            # Character literals ('a', '\n', etc.)
            if ch == "'":
                tok = self._scan_char(start_line, start_col)
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

    def _scan_raw_string(self, line: int, col: int) -> Token:
        self._advance() # Consume opening '`'
        chars = []
        while True:
            ch = self._peek()
            if ch is None:
                raise LexerError("Unterminated raw string literal", line, col)
            if ch == '`':
                self._advance() # Consume closing '`'
                break
            if ch == '\r':
                self._advance()
                if self._peek() == '\n':
                    self._advance()
                self.line += 1
                self.col = 1
                chars.append('\n')
            elif ch == '\n':
                self.line += 1
                self.col = 1
                self._advance()
                chars.append('\n')
            else:
                chars.append(self._advance())
        return Token(TokenType.STRING_LIT, "".join(chars), line, col)

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
                elif escape == '0': chars.append('\0')
                elif escape == '"': chars.append('"')
                elif escape == '\'': chars.append('\'')
                elif escape == '\\': chars.append('\\')
                elif escape == '{': chars.append('{')
                elif escape == '}': chars.append('}')
                elif escape == 'x':
                    h1 = self._advance()
                    h2 = self._advance()
                    if h1 is None or h2 is None:
                        raise LexerError("Invalid hex escape in string literal", line, col)
                    chars.append(chr(int(h1 + h2, 16)))
                elif escape == 'u':
                    h = ""
                    for _ in range(4):
                        hc = self._advance()
                        if hc is None:
                            raise LexerError("Invalid unicode escape in string literal", line, col)
                        h += hc
                    chars.append(chr(int(h, 16)))
                else:
                    raise LexerError(f"Unknown escape sequence '\\{escape}'", line, col)
            else:
                chars.append(self._advance())
        return Token(TokenType.STRING_LIT, "".join(chars), line, col)

    def _scan_char(self, line: int, col: int) -> Token:
        self._advance() # Consume opening "'"
        ch = self._advance()
        if ch is None:
            raise LexerError("Unterminated character literal", line, col)
        if ch == '\\':
            esc = self._advance()
            if esc == 'n': val = ord('\n')
            elif esc == 't': val = ord('\t')
            elif esc == 'r': val = ord('\r')
            elif esc == '0': val = 0
            elif esc == '\'': val = ord('\'')
            elif esc == '"': val = ord('"')
            elif esc == '\\': val = ord('\\')
            elif esc == 'x':
                h1 = self._advance()
                h2 = self._advance()
                if h1 is None or h2 is None:
                    raise LexerError("Invalid hex escape in character literal", line, col)
                val = int(h1 + h2, 16)
            elif esc == 'u':
                h = ""
                for _ in range(4):
                    hc = self._advance()
                    if hc is None:
                        raise LexerError("Invalid unicode escape in character literal", line, col)
                    h += hc
                val = int(h, 16)
            else: val = ord(esc) if esc else 0
        else:
            val = ord(ch)

        if self._peek() == "'":
            self._advance() # Consume closing "'"
        else:
            raise LexerError("Unclosed character literal", line, col)

        return Token(TokenType.INT_LIT, val, line, col)

    def _scan_number(self, line: int, col: int) -> Token:
        chars = []
        is_float = False

        # Check for numeric base prefixes: 0x, 0b, 0o
        if self._peek() == '0' and self._peek(1) in ('x', 'X', 'b', 'B', 'o', 'O'):
            chars.append(self._advance()) # '0'
            base_char = self._advance()
            chars.append(base_char)
            if base_char in ('x', 'X'):
                while self._peek() is not None and (self._peek().isdigit() or self._peek() in 'abcdefABCDEF_'):
                    chars.append(self._advance())
            elif base_char in ('b', 'B'):
                while self._peek() is not None and (self._peek() in '01_'):
                    chars.append(self._advance())
            else: # octal
                while self._peek() is not None and (self._peek() in '01234567_'):
                    chars.append(self._advance())

            # Optional integer suffix (e.g. 0xFFu8, 0x1000i64)
            suffix_chars = []
            if self._peek() is not None and self._peek().isalpha():
                while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
                    suffix_chars.append(self._advance())
            chars.extend(suffix_chars)

            raw_str = "".join(chars)
            clean_str = "".join(c for c in chars if c != '_')
            suffix = "".join(suffix_chars)
            num_part = clean_str[:len(clean_str)-len(suffix)] if suffix else clean_str
            if base_char in ('x', 'X'):
                val = int(num_part, 16)
            elif base_char in ('b', 'B'):
                val = int(num_part, 2)
            else:
                val = int(num_part[2:], 8)
            return Token(TokenType.INT_LIT, val, line, col, raw_str=raw_str, type_name=suffix if suffix else None)

        # Decimal numbers with optional underscores
        while self._peek() is not None and (self._peek().isdigit() or self._peek() == '_'):
            chars.append(self._advance())

        # Check decimal point for float (ensuring not '..' range)
        if self._peek() == '.' and self._peek(1) is not None and self._peek(1).isdigit():
            is_float = True
            chars.append(self._advance()) # '.'
            while self._peek() is not None and (self._peek().isdigit() or self._peek() == '_'):
                chars.append(self._advance())

        # Check scientific notation exponent (e / E)
        if self._peek() in ('e', 'E'):
            has_exp_digit = False
            if self._peek(1) is not None and self._peek(1).isdigit():
                has_exp_digit = True
            elif self._peek(1) in ('+', '-') and self._peek(2) is not None and self._peek(2).isdigit():
                has_exp_digit = True
            if has_exp_digit:
                is_float = True
                chars.append(self._advance()) # 'e' or 'E'
                if self._peek() in ('+', '-'):
                    chars.append(self._advance())
                while self._peek() is not None and (self._peek().isdigit() or self._peek() == '_'):
                    chars.append(self._advance())

        # Check suffix
        suffix_chars = []
        if self._peek() is not None and self._peek().isalpha():
            while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
                suffix_chars.append(self._advance())
            suffix = "".join(suffix_chars)
            if suffix in ('f32', 'f64', 'f', 'F'):
                is_float = True
        else:
            suffix = ""
        chars.extend(suffix_chars)

        raw_str = "".join(chars)
        clean_str = "".join(c for c in chars if c != '_')
        num_part = clean_str[:len(clean_str)-len(suffix)] if suffix else clean_str

        if is_float:
            val = float(num_part)
            return Token(TokenType.FLOAT_LIT, val, line, col, raw_str=raw_str, type_name=suffix if suffix else None)
        else:
            val = int(num_part)
            return Token(TokenType.INT_LIT, val, line, col, raw_str=raw_str, type_name=suffix if suffix else None)

    def _scan_identifier(self, line: int, col: int) -> Token:
        chars = []
        while self._peek() is not None and (self._peek().isalnum() or self._peek() == '_'):
            chars.append(self._advance())
        name = "".join(chars)
        token_type = KEYWORDS.get(name, TokenType.IDENTIFIER)
        # 5.2 slice 11: contextual `shelf` — identifier unless immediately
        # followed by `[` or preceded by `heap` (the heap pair stays parse-level)
        if (name == "shelf" and token_type == TokenType.SHELF
                and self._peek() != "[" and (not self.tokens or self.tokens[-1].type != TokenType.HEAP)):
            token_type = TokenType.IDENTIFIER
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
            if self._match('.'):
                if self._match('='): return Token(TokenType.DOTDOTEQ, "..=", line, col)
                return Token(TokenType.DOTDOT, "..", line, col)
            return Token(TokenType.DOT, ".", line, col)
        if ch == '=':
            if self._match('='): return Token(TokenType.EQ, "==", line, col)
            if self._match('>'): return Token(TokenType.FAT_ARROW, "=>", line, col)
            return Token(TokenType.ASSIGN, "=", line, col)
        if ch == '!':
            if self._match('='): return Token(TokenType.NE, "!=", line, col)
            return Token(TokenType.BANG, "!", line, col)
        if ch == '<':
            if self._match('<'):
                if self._match('='): return Token(TokenType.SHL_ASSIGN, "<<=", line, col)
                return Token(TokenType.SHL, "<<", line, col)
            if self._match('='): return Token(TokenType.LE, "<=", line, col)
            return Token(TokenType.LT, "<", line, col)
        if ch == '>':
            if self._match('>'):
                if self._match('='): return Token(TokenType.SHR_ASSIGN, ">>=", line, col)
                return Token(TokenType.SHR, ">>", line, col)
            if self._match('='): return Token(TokenType.GE, ">=", line, col)
            return Token(TokenType.GT, ">", line, col)
        if ch == '&':
            if self._match('='): return Token(TokenType.AMP_ASSIGN, "&=", line, col)
            return Token(TokenType.AMP, "&", line, col)
        if ch == '|':
            if self._match('='): return Token(TokenType.PIPE_ASSIGN, "|=", line, col)
            return Token(TokenType.PIPE, "|", line, col)
        if ch == '^':
            if self._match('='): return Token(TokenType.CARET_ASSIGN, "^=", line, col)
            return Token(TokenType.CARET, "^", line, col)
        if ch == '~':
            return Token(TokenType.TILDE, "~", line, col)
        if ch == '(': return Token(TokenType.LPAREN, "(", line, col)
        if ch == ')': return Token(TokenType.RPAREN, ")", line, col)
        if ch == '{': return Token(TokenType.LBRACE, "{", line, col)
        if ch == '}': return Token(TokenType.RBRACE, "}", line, col)
        if ch == '[': return Token(TokenType.LBRACKET, "[", line, col)
        if ch == ']': return Token(TokenType.RBRACKET, "]", line, col)
        if ch == ',': return Token(TokenType.COMMA, ",", line, col)
        if ch == ':': return Token(TokenType.COLON, ":", line, col)
        if ch == '#': return Token(TokenType.HASH, "#", line, col)

        raise LexerError(f"Unexpected character '{ch}'", line, col)
