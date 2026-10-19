from typing import List, Optional, Tuple
from velo.tokens import Token, TokenType
from velo.ast_nodes import (
    Program, Decl, UseStmt, FunctionDecl, ExternDecl, Param, BlockStmt, DataDecl, Field,
    Stmt, ExprStmt, ReturnStmt, BreakStmt, ContinueStmt, VarDeclStmt, AssignStmt, IfStmt, WhileStmt, LoopStmt, ZoneStmt, DeferStmt,
    MatchCase, MatchStmt,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral,
    Identifier, MemberAccess, IndexExpr, DerefExpr, StructLiteral, CastExpr, CallExpr, AddressOf, BinaryExpr, UnaryExpr
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
        return self.tokens[-1]

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
        elif self._check(TokenType.EXTERN):
            return self._parse_extern_decl()
        elif self._check(TokenType.DATA):
            return self._parse_data_decl()
        elif self._check(TokenType.ACT):
            return self._parse_function_decl()
        elif self._check(TokenType.LET) or self._check(TokenType.MUT):
            return self._parse_statement()
        else:
            raise ParserError(f"Unexpected top-level token '{self._peek().value}'", self._peek())


    def _parse_use_decl(self) -> UseStmt:
        use_tok = self._consume(TokenType.USE, "Expected 'use'")
        if self._check(TokenType.STRING_LIT):
            str_tok = self._advance()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return UseStmt(module_path=str_tok.value, line=use_tok.line, col=use_tok.col)

        parts = []
        first_part = self._consume(TokenType.IDENTIFIER, "Expected module name or string path after 'use'")
        parts.append(first_part.value)

        while self._match(TokenType.DOT):
            part = self._consume(TokenType.IDENTIFIER, "Expected module component after '.'")
            parts.append(part.value)

        module_path = ".".join(parts)
        self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
        return UseStmt(module_path=module_path, line=use_tok.line, col=use_tok.col)


    def _parse_extern_decl(self) -> ExternDecl:
        extern_tok = self._consume(TokenType.EXTERN, "Expected 'extern'")
        self._consume(TokenType.ACT, "Expected 'act' after 'extern'")
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected external function name")

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

        self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
        return ExternDecl(
            name=name_tok.value,
            params=params,
            return_type=return_type,
            line=extern_tok.line,
            col=extern_tok.col
        )

    def _parse_data_decl(self) -> DataDecl:
        data_tok = self._consume(TokenType.DATA, "Expected 'data'")
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected struct name after 'data'")

        self._skip_newlines()
        self._consume(TokenType.LBRACE, "Expected '{' after struct name")
        self._skip_newlines()

        fields: List[Field] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            fname = self._consume(TokenType.IDENTIFIER, "Expected field name")
            self._consume(TokenType.COLON, "Expected ':' after field name")
            ftype = self._parse_type_annotation()
            fields.append(Field(name=fname.value, type_name=ftype, line=fname.line, col=fname.col))
            self._skip_newlines()
            self._match(TokenType.COMMA)
            self._skip_newlines()

        self._consume(TokenType.RBRACE, "Expected '}' after struct body")
        return DataDecl(name=name_tok.value, fields=fields, line=data_tok.line, col=data_tok.col)

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

        # 1. Defer statement
        if self._check(TokenType.DEFER):
            defer_tok = self._advance()
            stmt = self._parse_statement()
            return DeferStmt(statement=stmt, line=defer_tok.line, col=defer_tok.col)

        # 2. Zone statement
        if self._check(TokenType.ZONE):
            zone_tok = self._advance()
            self._skip_newlines()
            body = self._parse_block()
            return ZoneStmt(body=body, line=zone_tok.line, col=zone_tok.col)

        # 3. Variable declaration with 'mut'
        if self._check(TokenType.MUT):
            mut_tok = self._advance()
            name_tok = self._consume(TokenType.IDENTIFIER, "Expected variable name after 'mut'")
            type_name = None
            if self._match(TokenType.COLON):
                type_name = self._parse_type_annotation()
            val = None
            if self._match(TokenType.ASSIGN):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return VarDeclStmt(name=name_tok.value, type_name=type_name, value=val, is_mut=True, line=mut_tok.line, col=mut_tok.col)

        # 4. Variable declaration with 'let'
        if self._check(TokenType.LET):
            let_tok = self._advance()
            name_tok = self._consume(TokenType.IDENTIFIER, "Expected variable name after 'let'")
            type_name = None
            if self._match(TokenType.COLON):
                type_name = self._parse_type_annotation()
            val = None
            if self._match(TokenType.ASSIGN):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return VarDeclStmt(name=name_tok.value, type_name=type_name, value=val, is_mut=False, line=let_tok.line, col=let_tok.col)

        # 5. Variable declaration with explicit type (e.g. x: i32 = 10, ptr: @Point = @p)
        if self._peek().type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.COLON:
            name_tok = self._advance()
            self._advance() # Consume ':'
            type_name = self._parse_type_annotation()
            val = None
            if self._match(TokenType.ASSIGN):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return VarDeclStmt(name=name_tok.value, type_name=type_name, value=val, is_mut=False, line=name_tok.line, col=name_tok.col)

        # 6. If statement
        if self._check(TokenType.IF):
            return self._parse_if_stmt()

        # 7. While statement
        if self._check(TokenType.WHILE):
            return self._parse_while_stmt()

        # 8. Loop range statement
        if self._check(TokenType.LOOP):
            return self._parse_loop_stmt()

        # 8.5. Match / Switch statement
        if self._check(TokenType.MATCH) or self._check(TokenType.SWITCH):
            return self._parse_match_stmt()

        # 9. Return statement
        if self._check(TokenType.RETURN):
            ret_tok = self._advance()
            val = None
            if not self._check(TokenType.NEWLINE) and not self._check(TokenType.SEMICOLON) and not self._check(TokenType.RBRACE):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return ReturnStmt(value=val, line=ret_tok.line, col=ret_tok.col)

        # 9.5. Break statement
        if self._check(TokenType.BREAK):
            tok = self._advance()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return BreakStmt(line=tok.line, col=tok.col)

        # 9.6. Continue statement
        if self._check(TokenType.CONTINUE):
            tok = self._advance()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return ContinueStmt(line=tok.line, col=tok.col)

        # 10. Assignment or Expression Statement
        expr = self._parse_expression()

        assign_ops = (
            TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN, TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN,
            TokenType.AMP_ASSIGN, TokenType.PIPE_ASSIGN, TokenType.CARET_ASSIGN, TokenType.SHL_ASSIGN, TokenType.SHR_ASSIGN
        )
        for op_type in assign_ops:
            if self._match(op_type):
                op_val = self.tokens[self.pos - 1].value
                val = self._parse_expression()
                self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
                return AssignStmt(target=expr, op=op_val, value=val, line=expr.line, col=expr.col)

        self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
        return ExprStmt(expr=expr, line=expr.line, col=expr.col)

    def _parse_if_stmt(self) -> IfStmt:
        if_tok = self._consume(TokenType.IF, "Expected 'if'")
        condition = self._parse_expression()
        self._skip_newlines()
        then_branch = self._parse_block()

        else_branch = None
        self._skip_newlines()
        if self._match(TokenType.ELSE):
            self._skip_newlines()
            if self._check(TokenType.IF):
                else_branch = self._parse_if_stmt()
            else:
                else_branch = self._parse_block()

        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch, line=if_tok.line, col=if_tok.col)

    def _parse_while_stmt(self) -> WhileStmt:
        while_tok = self._consume(TokenType.WHILE, "Expected 'while'")
        condition = self._parse_expression()
        self._skip_newlines()
        body = self._parse_block()
        return WhileStmt(condition=condition, body=body, line=while_tok.line, col=while_tok.col)

    def _parse_loop_stmt(self) -> LoopStmt:
        loop_tok = self._consume(TokenType.LOOP, "Expected 'loop'")
        iterator_tok = self._consume(TokenType.IDENTIFIER, "Expected loop variable name")
        self._consume(TokenType.IN, "Expected 'in' after loop variable")
        start_expr = self._parse_expression()
        self._consume(TokenType.DOTDOT, "Expected '..' in range")
        end_expr = self._parse_expression()
        self._skip_newlines()
        body = self._parse_block()
        return LoopStmt(
            iterator=iterator_tok.value,
            start_expr=start_expr,
            end_expr=end_expr,
            body=body,
            line=loop_tok.line,
            col=loop_tok.col
        )

    def _parse_match_stmt(self) -> MatchStmt:
        match_tok = self._advance() # consume 'match' or 'switch'
        expr = self._parse_expression()
        self._skip_newlines()
        self._consume(TokenType.LBRACE, "Expected '{' after match expression")
        self._skip_newlines()

        cases: List[MatchCase] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            case_start = self._peek()
            is_default = False
            values: List[Expr] = []

            # Check if default / else / _ branch
            if self._check(TokenType.DEFAULT) or self._check(TokenType.ELSE) or (self._check(TokenType.IDENTIFIER) and self._peek().value == "_"):
                self._advance()
                is_default = True
                if self._check(TokenType.FAT_ARROW) or self._check(TokenType.COLON):
                    self._advance()
            else:
                if self._check(TokenType.CASE):
                    self._advance()
                values.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    values.append(self._parse_expression())
                if self._check(TokenType.FAT_ARROW) or self._check(TokenType.COLON):
                    self._advance()
                else:
                    raise ParserError("Expected '=>' or ':' after case pattern", self._peek())

            self._skip_newlines()
            if self._check(TokenType.LBRACE):
                body = self._parse_block()
            else:
                stmt = self._parse_statement()
                body = BlockStmt(statements=[stmt] if stmt else [], line=case_start.line, col=case_start.col)

            cases.append(MatchCase(values=values, is_default=is_default, body=body, line=case_start.line, col=case_start.col))
            self._skip_newlines()

        self._consume(TokenType.RBRACE, "Expected '}' at end of match block")
        return MatchStmt(expr=expr, cases=cases, line=match_tok.line, col=match_tok.col)

    # Expression Precedence Hierarchy
    def _parse_expression(self) -> Expr:
        return self._parse_logical_or()

    def _parse_logical_or(self) -> Expr:
        expr = self._parse_logical_and()
        while self._match(TokenType.OR):
            op = self.tokens[self.pos - 1].value
            right = self._parse_logical_and()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_logical_and(self) -> Expr:
        expr = self._parse_bitwise_or()
        while self._match(TokenType.AND):
            op = self.tokens[self.pos - 1].value
            right = self._parse_bitwise_or()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_bitwise_or(self) -> Expr:
        expr = self._parse_bitwise_xor()
        while self._match(TokenType.PIPE):
            op = self.tokens[self.pos - 1].value
            right = self._parse_bitwise_xor()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_bitwise_xor(self) -> Expr:
        expr = self._parse_bitwise_and()
        while self._match(TokenType.CARET):
            op = self.tokens[self.pos - 1].value
            right = self._parse_bitwise_and()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_bitwise_and(self) -> Expr:
        expr = self._parse_equality()
        while self._match(TokenType.AMP):
            op = self.tokens[self.pos - 1].value
            right = self._parse_equality()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_equality(self) -> Expr:
        expr = self._parse_comparison()
        while self._match(TokenType.EQ, TokenType.NE):
            op = self.tokens[self.pos - 1].value
            right = self._parse_comparison()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_comparison(self) -> Expr:
        expr = self._parse_shift()
        while self._match(TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE):
            op = self.tokens[self.pos - 1].value
            right = self._parse_shift()
            expr = BinaryExpr(left=expr, op=op, right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_shift(self) -> Expr:
        expr = self._parse_term()
        while self._match(TokenType.SHL, TokenType.SHR):
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
        if self._match(TokenType.MINUS, TokenType.BANG, TokenType.NOT, TokenType.TILDE):
            tok = self.tokens[self.pos - 1]
            operand = self._parse_unary()
            return UnaryExpr(op=tok.value, operand=operand, line=tok.line, col=tok.col)
        return self._parse_postfix()

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.DOT):
                if self._match(TokenType.AT):
                    at_tok = self.tokens[self.pos - 1]
                    expr = DerefExpr(operand=expr, line=at_tok.line, col=at_tok.col)
                else:
                    member_tok = self._consume(TokenType.IDENTIFIER, "Expected member name after '.'")
                    expr = MemberAccess(target=expr, member=member_tok.value, line=member_tok.line, col=member_tok.col)
            elif self._match(TokenType.LBRACKET):
                lbracket = self.tokens[self.pos - 1]
                idx_expr = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Expected ']' after array index")
                expr = IndexExpr(target=expr, index=idx_expr, line=lbracket.line, col=lbracket.col)
            elif self._match(TokenType.AS):
                as_tok = self.tokens[self.pos - 1]
                target_type = self._parse_type_annotation()
                expr = CastExpr(expr=expr, target_type=target_type, line=as_tok.line, col=as_tok.col)
            elif self._match(TokenType.LPAREN):
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

    def _is_struct_literal(self) -> bool:
        if not (self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.LBRACE):
            return False
        
        ident_name = self._peek().value
        if not ident_name or not ident_name[0].isupper():
            return False

        idx = 2
        while self.pos + idx < len(self.tokens) and self.tokens[self.pos + idx].type in (TokenType.NEWLINE, TokenType.SEMICOLON):
            idx += 1
        
        target_tok = self._peek(idx)
        if target_tok.type == TokenType.RBRACE:
            return True
        if target_tok.type == TokenType.IDENTIFIER and self._peek(idx + 1).type == TokenType.COLON:
            return True
        return False

    def _parse_primary(self) -> Expr:
        if self._is_struct_literal():
            id_tok = self._advance()
            self._advance()
            self._skip_newlines()
            field_inits: List[Tuple[str, Expr]] = []
            while not self._check(TokenType.RBRACE) and not self._is_at_end():
                fname = self._consume(TokenType.IDENTIFIER, "Expected field name in struct literal")
                self._consume(TokenType.COLON, "Expected ':' after field name")
                fval = self._parse_expression()
                field_inits.append((fname.value, fval))
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    self._skip_newlines()
                    break
            self._consume(TokenType.RBRACE, "Expected '}' at end of struct literal")
            return StructLiteral(struct_name=id_tok.value, field_inits=field_inits, line=id_tok.line, col=id_tok.col)

        tok = self._peek()

        if self._match(TokenType.NULL):
            return NullLiteral(line=tok.line, col=tok.col)
        if self._match(TokenType.INT_LIT):
            prev = self.tokens[self.pos - 1]
            return IntLiteral(value=prev.value, line=prev.line, col=prev.col, raw_str=prev.raw_str, type_name=prev.type_name)
        if self._match(TokenType.FLOAT_LIT):
            prev = self.tokens[self.pos - 1]
            return FloatLiteral(value=prev.value, line=prev.line, col=prev.col, raw_str=prev.raw_str, type_name=prev.type_name)
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
