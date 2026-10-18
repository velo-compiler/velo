from typing import List, Optional
from velo.tokens import Token, TokenType
from velo.ast_nodes import (
    Program, Decl, UseStmt, FunctionDecl, Param, BlockStmt,
    Stmt, ExprStmt, ReturnStmt, VarDeclStmt,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    Identifier, MemberAccess, CallExpr, AddressOf, BinaryExpr, UnaryExpr
)

class ParserError(Exception):
    def __init__(self, message: str, token: Token):
        super().__init__(f"Parser Error at line {token.line}, col {token.col}: {message}")
        self.token = token

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1] # Return EOF

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _advance(self) -> Token:
        tok = self._peek()
        if not self._is_at_end():
            self.pos += 1
        return tok

    def _check(self, token_type: TokenType) -> bool:
        return self._peek().type == token_type

    def _match(self, *types: TokenType) -> bool:
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, err_msg: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise ParserError(f"{err_msg} (got {self._peek().type.name} '{self._peek().value}')", self._peek())

    def _skip_newlines(self):
        while self._match(TokenType.NEWLINE, TokenType.SEMICOLON):
            pass

    def parse(self) -> Program:
        declarations: List[Decl] = []
        self._skip_newlines()

        while not self._is_at_end():
            decl = self._parse_top_level_declaration()
            if decl:
                declarations.append(decl)
            self._skip_newlines()

        return Program(declarations=declarations)

    def _parse_top_level_declaration(self) -> Optional[Decl]:
        if self._check(TokenType.USE):
            return self._parse_use_decl()
        elif self._check(TokenType.ACT):
            return self._parse_function_decl()
        else:
            raise ParserError(f"Unexpected top-level token '{self._peek().value}'", self._peek())

    def _parse_use_decl(self) -> UseStmt:
        use_tok = self._consume(TokenType.USE, "Expected 'use'")
        # Module path e.g. sys.io
        parts = []
        first_part = self._consume(TokenType.IDENTIFIER, "Expected module name after 'use'")
        parts.append(first_part.value)

        while self._match(TokenType.DOT):
            part = self._consume(TokenType.IDENTIFIER, "Expected module component after '.'")
            parts.append(part.value)

        module_path = ".".join(parts)
        self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
        return UseStmt(module_path=module_path, line=use_tok.line, col=use_tok.col)

    def _parse_function_decl(self) -> FunctionDecl:
        act_tok = self._consume(TokenType.ACT, "Expected 'act'")
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected function name")

        self._consume(TokenType.LPAREN, "Expected '(' after function name")
        params: List[Param] = []

        if not self._check(TokenType.RPAREN):
            while True:
                param_name = self._consume(TokenType.IDENTIFIER, "Expected parameter name")
                self._consume(TokenType.COLON, "Expected ':' after parameter name")
                param_type = self._parse_type_annotation()
                params.append(Param(name=param_name.value, type_name=param_type, line=param_name.line, col=param_name.col))

                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RPAREN, "Expected ')' after parameters")

        return_type: Optional[str] = None
        if self._match(TokenType.ARROW):
            return_type = self._parse_type_annotation()

        self._skip_newlines()
        body = self._parse_block()

        return FunctionDecl(
            name=name_tok.value,
            params=params,
            return_type=return_type,
            body=body,
            line=act_tok.line,
            col=act_tok.col
        )

    def _parse_type_annotation(self) -> str:
        # Handles @T, @@T, or regular types like i32, string, void
        prefix = ""
        while self._match(TokenType.AT):
            prefix += "@"

        type_tok = self._consume(TokenType.IDENTIFIER, "Expected type name")
        return prefix + type_tok.value

    def _parse_block(self) -> BlockStmt:
        lbrace = self._consume(TokenType.LBRACE, "Expected '{'")
        self._skip_newlines()

        statements: List[Stmt] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
            self._skip_newlines()

        self._consume(TokenType.RBRACE, "Expected '}' at end of block")
        return BlockStmt(statements=statements, line=lbrace.line, col=lbrace.col)

    def _parse_statement(self) -> Stmt:
        self._skip_newlines()

        if self._check(TokenType.RETURN):
            ret_tok = self._advance()
            val = None
            if not self._check(TokenType.NEWLINE) and not self._check(TokenType.SEMICOLON) and not self._check(TokenType.RBRACE):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return ReturnStmt(value=val, line=ret_tok.line, col=ret_tok.col)

        # Expression statement (e.g. io.println(...))
        expr = self._parse_expression()
        self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
        return ExprStmt(expr=expr, line=expr.line, col=expr.col)

    def _parse_expression(self) -> Expr:
        return self._parse_equality()

    def _parse_equality(self) -> Expr:
        expr = self._parse_comparison()
        while self._match(TokenType.EQ, TokenType.NE):
            op = self.tokens[self.pos - 1].value
            right = self._parse_comparison()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_comparison(self) -> Expr:
        expr = self._parse_term()
        while self._match(TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE):
            op = self.tokens[self.pos - 1].value
            right = self._parse_term()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_term(self) -> Expr:
        expr = self._parse_factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self.tokens[self.pos - 1].value
            right = self._parse_factor()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_factor(self) -> Expr:
        expr = self._parse_unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.tokens[self.pos - 1].value
            right = self._parse_unary()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_unary(self) -> Expr:
        if self._match(TokenType.AT):
            tok = self.tokens[self.pos - 1]
            operand = self._parse_unary()
            return AddressOf(operand=operand, line=tok.line, col=tok.col)
        if self._match(TokenType.MINUS, TokenType.BANG, TokenType.NOT):
            tok = self.tokens[self.pos - 1]
            operand = self._parse_unary()
            return UnaryExpr(op=tok.value, operand=operand, line=tok.line, col=tok.col)
        return self._parse_postfix()

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.DOT):
                # Member access e.g. io.println or p.x
                member_tok = self._consume(TokenType.IDENTIFIER, "Expected member name after '.'")
                expr = MemberAccess(target=expr, member=member_tok.value, line=member_tok.line, col=member_tok.col)
            elif self._match(TokenType.LPAREN):
                # Call expression e.g. println("Hello")
                lparen = self.tokens[self.pos - 1]
                args: List[Expr] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after arguments")
                expr = CallExpr(callee=expr, args=args, line=lparen.line, col=lparen.col)
            else:
                break

        return expr

    def _parse_primary(self) -> Expr:
        tok = self._peek()

        if self._match(TokenType.INT_LIT):
            return IntLiteral(value=tok.value, line=tok.line, col=tok.col)
        if self._match(TokenType.FLOAT_LIT):
            return FloatLiteral(value=tok.value, line=tok.line, col=tok.col)
        if self._match(TokenType.STRING_LIT):
            return StringLiteral(value=tok.value, line=tok.line, col=tok.col)
        if self._match(TokenType.TRUE):
            return BoolLiteral(value=True, line=tok.line, col=tok.col)
        if self._match(TokenType.FALSE):
            return BoolLiteral(value=False, line=tok.line, col=tok.col)
        if self._match(TokenType.IDENTIFIER):
            return Identifier(name=tok.value, line=tok.line, col=tok.col)
        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')' after grouped expression")
            return expr

        raise ParserError(f"Unexpected token in expression: {tok.type.name} ('{tok.value}')", tok)
