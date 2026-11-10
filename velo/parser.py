from typing import List, Optional, Tuple
from velo.tokens import Token, TokenType
from velo.ast_nodes import (
    Program, Decl, UseStmt, FunctionDecl, ExternDecl, Param, BlockStmt, DataDecl, Field, KindDecl, VariantDecl,
    Stmt, ExprStmt, ReturnStmt, BreakStmt, ContinueStmt, VarDeclStmt, AssignStmt, IfStmt, LoopStmt, ZoneStmt, DeferStmt,
    MatchCase, MatchStmt, FailStmt,
    Expr, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral, NullLiteral,
    Identifier, MemberAccess, IndexExpr, DerefExpr, StructLiteral, CastExpr, CallExpr, AddressOf, BinaryExpr, UnaryExpr, VariantExpr, AnonFuncExpr,
    ShelfLiteral, MapLiteral, RingLiteral, BitsetLiteral, OrReturnExpr, UnwrapExpr,
    TypeAliasDecl, TestDecl,
    mangle_op_name
)

# Types permitted as `aka Alias = <target>` targets (primitive aliases only).
ALIAS_TARGET_PRIMITIVES = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
                           "f32", "f64", "bool", "usize", "isize", "string",
                           "f32x4", "i32x4"}

CONTEXTUAL_IDENT_TOKENS = (
    TokenType.IDENTIFIER,
    TokenType.KIND,
    TokenType.OP,
    TokenType.DATA,
    TokenType.TEST,
    TokenType.USE,
    TokenType.ACT,
    TokenType.LOOP,
    TokenType.ZONE,
    TokenType.DEFER,
    TokenType.RETURN,
    TokenType.BREAK,
    TokenType.CONTINUE,
    TokenType.ON,
    TokenType.EXTERN,
    TokenType.FAIL,
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
        cur_type = self._peek().type
        if token_type == TokenType.IDENTIFIER:
            return cur_type in (TokenType.IDENTIFIER, TokenType.KIND, TokenType.OP, TokenType.DATA, TokenType.TEST)
        return cur_type == token_type

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

    def _consume_ident(self, err_msg: str) -> Token:
        if self._peek().type in CONTEXTUAL_IDENT_TOKENS:
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
        elif self._check(TokenType.KIND):
            return self._parse_kind_decl()
        elif self._check(TokenType.ACT):
            return self._parse_function_decl()
        elif self._check(TokenType.TEST):
            return self._parse_test_decl()
        elif self._check(TokenType.LET) or self._check(TokenType.MUT):
            return self._parse_statement()
        elif self._check(TokenType.IDENTIFIER) and self._peek().value == "aka":
            return self._parse_type_alias_decl()
        else:
            raise ParserError(f"Unexpected top-level token '{self._peek().value}'", self._peek())

    def _parse_test_decl(self) -> TestDecl:
        test_tok = self._consume(TokenType.TEST, "Expected 'test'")
        if self._check(TokenType.STRING_LIT):
            name_tok = self._advance()
            name = name_tok.value
        elif self._check(TokenType.IDENTIFIER):
            name_tok = self._advance()
            name = name_tok.value
        else:
            raise ParserError("Expected test name string literal or identifier after 'test'", self._peek())
        self._skip_newlines()
        body = self._parse_block()
        return TestDecl(name=name, body=body, line=test_tok.line, col=test_tok.col)


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
                param_name = self._consume_ident("Expected parameter name")
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

    def _parse_type_params(self) -> List[str]:
        if not self._match(TokenType.LBRACKET):
            return []
        params: List[str] = []
        while not self._check(TokenType.RBRACKET) and not self._is_at_end():
            p_tok = self._consume(TokenType.IDENTIFIER, "Expected type parameter name")
            params.append(p_tok.value)
            if not self._match(TokenType.COMMA):
                break
        self._consume(TokenType.RBRACKET, "Expected ']' after type parameters")
        return params

    def _parse_data_attributes(self) -> Tuple[Optional[int], bool]:
        """Parses `#align(N)` and `#packed` markers between the header and '{'."""
        align_value: Optional[int] = None
        is_packed = False
        while self._check(TokenType.HASH):
            hash_tok = self._advance()
            attr_tok = self._consume(TokenType.IDENTIFIER, "Expected attribute name after '#'")
            if attr_tok.value == "align":
                self._consume(TokenType.LPAREN, "Expected '(' after '#align'")
                num_tok = self._consume(TokenType.INT_LIT, "Expected integer alignment after '#align('")
                align_raw = str(num_tok.value).replace("_", "")
                align_value = int(align_raw, 0)
                if align_value <= 0:
                    raise ParserError(f"#align(N) requires a positive integer, got {align_value}", num_tok)
                self._consume(TokenType.RPAREN, "Expected ')' after alignment value")
            elif attr_tok.value == "packed":
                is_packed = True
            else:
                raise ParserError(f"Unknown data attribute '#{attr_tok.value}' (expected 'align' or 'packed')", attr_tok)
        return align_value, is_packed

    def _parse_field_default(self) -> Expr:
        """Parses a constant field default: literal or unary `-` on a numeric literal."""
        if self._match(TokenType.MINUS):
            num_tok = self._peek()
            if not (num_tok.type == TokenType.INT_LIT or num_tok.type == TokenType.FLOAT_LIT):
                raise ParserError("Field default after '-' must be a numeric literal", num_tok)
            self._advance()
            prev = self.tokens[self.pos - 1]
            if prev.type == TokenType.FLOAT_LIT:
                return FloatLiteral(value=-prev.value, line=prev.line, col=prev.col,
                                    raw_str="-" + (prev.raw_str or str(prev.value)), type_name=prev.type_name)
            return IntLiteral(value=-prev.value, line=prev.line, col=prev.col,
                              raw_str="-" + (prev.raw_str or str(prev.value)), type_name=prev.type_name)
        lit_tok = self._peek()
        if lit_tok.type == TokenType.INT_LIT:
            self._advance()
            prev = self.tokens[self.pos - 1]
            return IntLiteral(value=prev.value, line=prev.line, col=prev.col, raw_str=prev.raw_str, type_name=prev.type_name)
        if lit_tok.type == TokenType.FLOAT_LIT:
            self._advance()
            prev = self.tokens[self.pos - 1]
            return FloatLiteral(value=prev.value, line=prev.line, col=prev.col, raw_str=prev.raw_str, type_name=prev.type_name)
        if lit_tok.type == TokenType.STRING_LIT:
            self._advance()
            return StringLiteral(value=lit_tok.value, line=lit_tok.line, col=lit_tok.col)
        if lit_tok.type == TokenType.TRUE:
            self._advance()
            return BoolLiteral(value=True, line=lit_tok.line, col=lit_tok.col)
        if lit_tok.type == TokenType.FALSE:
            self._advance()
            return BoolLiteral(value=False, line=lit_tok.line, col=lit_tok.col)
        raise ParserError("Field default must be a constant literal (number, string, or bool)", lit_tok)

    def _parse_data_decl(self) -> DataDecl:
        data_tok = self._consume(TokenType.DATA, "Expected 'data'")
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected struct name after 'data'")
        type_params = self._parse_type_params()

        self._skip_newlines()
        align_value, is_packed = self._parse_data_attributes()

        self._consume(TokenType.LBRACE, "Expected '{' after struct name")
        self._skip_newlines()

        fields: List[Field] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            fname = self._consume_ident("Expected field name")
            self._consume(TokenType.COLON, "Expected ':' after field name")
            ftype = self._parse_type_annotation()
            default_expr = None
            if self._match(TokenType.ASSIGN):
                default_expr = self._parse_field_default()
            fields.append(Field(name=fname.value, type_name=ftype, line=fname.line, col=fname.col, default_expr=default_expr))
            self._skip_newlines()
            self._match(TokenType.COMMA)
            self._skip_newlines()

        self._consume(TokenType.RBRACE, "Expected '}' after struct body")
        decl = DataDecl(name=name_tok.value, fields=fields, line=data_tok.line, col=data_tok.col, type_params=type_params)
        decl.align = align_value
        decl.packed = is_packed
        return decl

    def _parse_type_alias_decl(self) -> TypeAliasDecl:
        self._consume(TokenType.IDENTIFIER, "Expected 'aka'")
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected alias name after 'aka'")
        self._consume(TokenType.ASSIGN, "Expected '=' in type alias")
        target = self._parse_type_annotation()
        base = target[1:] if target.startswith("@") else target
        if base not in ALIAS_TARGET_PRIMITIVES:
            raise ParserError(f"Type alias '{name_tok.value}' must target a primitive type (or @primitive), got '{target}'", name_tok)
        self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
        return TypeAliasDecl(name=name_tok.value, target_type=target, line=name_tok.line, col=name_tok.col)

    def _parse_kind_decl(self) -> KindDecl:
        kind_tok = self._consume(TokenType.KIND, "Expected 'kind'")
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected kind name after 'kind'")
        type_params = self._parse_type_params()

        self._skip_newlines()
        self._consume(TokenType.LBRACE, "Expected '{' after kind name")
        self._skip_newlines()

        variants: List[VariantDecl] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            vname = self._consume(TokenType.IDENTIFIER, "Expected variant name")
            disc = None
            ptype = None
            fields = None

            if self._match(TokenType.ASSIGN):
                num_tok = self._consume(TokenType.INT_LIT, "Expected integer discriminant after '='")
                disc = num_tok.value
            elif self._match(TokenType.COLON):
                ptype = self._parse_type_annotation()
            elif self._match(TokenType.LPAREN):
                fields = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        fname = self._consume_ident("Expected field name")
                        self._consume(TokenType.COLON, "Expected ':' after field name")
                        ftype = self._parse_type_annotation()
                        fields.append(Field(name=fname.value, type_name=ftype, line=fname.line, col=fname.col))
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after variant fields")

            variants.append(VariantDecl(
                name=vname.value,
                line=vname.line,
                col=vname.col,
                discriminant=disc,
                payload_type=ptype,
                fields=fields,
            ))
            self._skip_newlines()
            self._match(TokenType.COMMA)
            self._skip_newlines()

        self._consume(TokenType.RBRACE, "Expected '}' after kind body")
        return KindDecl(name=name_tok.value, variants=variants, line=kind_tok.line, col=kind_tok.col, type_params=type_params)

    def _parse_function_decl(self) -> FunctionDecl:
        act_tok = self._consume(TokenType.ACT, "Expected 'act'")
        is_operator = False
        op_symbol = None
        valid_op_types = (
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
            TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE,
            TokenType.BANG, TokenType.NOT, TokenType.TILDE, TokenType.AMP, TokenType.PIPE,
            TokenType.CARET, TokenType.SHL, TokenType.SHR
        )
        if self._peek().type == TokenType.OP and self._peek(1).type in valid_op_types:
            self._advance()
            is_operator = True
            op_tok = self._advance()
            op_symbol = op_tok.value
            name = None
        else:
            name_tok = self._consume(TokenType.IDENTIFIER, "Expected function name")
            name = name_tok.value
        type_params = self._parse_type_params()

        self._consume(TokenType.LPAREN, "Expected '(' after function name")
        params: List[Param] = []

        if not self._check(TokenType.RPAREN):
            while True:
                param_name = self._consume_ident("Expected parameter name")
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

        if is_operator:
            param_types = [p.type_name for p in params]
            name = mangle_op_name(op_symbol, param_types)

        return FunctionDecl(
            name=name,
            params=params,
            return_type=return_type,
            body=body,
            line=act_tok.line,
            col=act_tok.col,
            type_params=type_params,
            is_operator=is_operator,
            operator_symbol=op_symbol
        )

    def _parse_type_annotation(self, allow_or: bool = True) -> str:
        is_opt = False
        if self._match(TokenType.QUESTION):
            is_opt = True
        prefix = ""
        while self._match(TokenType.AT):
            prefix += "@"

        if self._match(TokenType.ACT):
            self._consume(TokenType.LPAREN, "Expected '(' after 'act' in function type")
            params = []
            if not self._check(TokenType.RPAREN):
                while True:
                    if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.COLON:
                        self._advance()
                        self._advance()
                    param_type = self._parse_type_annotation()
                    params.append(param_type)
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RPAREN, "Expected ')' after parameter types in function type")
            ret_type = "void"
            if self._match(TokenType.ARROW):
                ret_type = self._parse_type_annotation()
            act_str = f"act({', '.join(params)}) -> {ret_type}"
            full_type = prefix + act_str
            if is_opt or self._match(TokenType.QUESTION):
                full_type = "?" + full_type
            if allow_or and self._match(TokenType.OR):
                err_type = self._parse_type_annotation(allow_or=True)
                full_type = f"{full_type} or {err_type}"
            return full_type

        if self._check(TokenType.HEAP):
            # 5.2 slice 10: `heap shelf[T]` / Task 7.2: `heap Map[K, V]`
            self._advance()
            if self._match(TokenType.SHELF):
                base_name = "heap shelf"
            elif self._match(TokenType.MAP) or (self._check(TokenType.IDENTIFIER) and self._peek().value == "Map"):
                if not self._match(TokenType.MAP):
                    self._advance()
                base_name = "heap Map"
            else:
                self._error("Expected 'shelf' or 'map' after 'heap'")
        elif self._check(TokenType.SHELF) or self._check(TokenType.RING) or self._check(TokenType.BITSET) or self._check(TokenType.MAP):
            type_tok = self._consume(self.tokens[self.pos].type, "Expected type name")
            base_name = "Map" if type_tok.type == TokenType.MAP else type_tok.value
        else:
            type_tok = self._consume(TokenType.IDENTIFIER, "Expected type name")
            base_name = type_tok.value
        if self._match(TokenType.LBRACKET):
            args = []
            while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                args.append(self._parse_type_annotation())
                if not self._match(TokenType.COMMA):
                    break
            self._consume(TokenType.RBRACKET, "Expected ']' after type arguments")
            base_name += "[" + ", ".join(args) + "]"
        # 5.2 slice 9: a bare `ring` lowers to the loud codegen reject (the
        # bare-shelf pattern); `bitset` is legal bare by design.

        full_type = prefix + base_name
        if is_opt or self._match(TokenType.QUESTION):
            full_type = "?" + full_type
        if allow_or and self._match(TokenType.OR):
            err_type = self._parse_type_annotation(allow_or=True)
            full_type = f"{full_type} or {err_type}"
        return full_type

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
            size = None  # §4.1: `zone <bytes> { ... }` scrimps a private arena; plain `zone {` uses the default one
            if not self._check(TokenType.LBRACE):
                size = self._parse_expression()
                self._skip_newlines()
            body = self._parse_block()
            return ZoneStmt(body=body, size=size, line=zone_tok.line, col=zone_tok.col)

        # 3. Variable declaration with 'mut'
        if self._check(TokenType.MUT):
            mut_tok = self._advance()
            name_tok = self._consume_ident("Expected variable name after 'mut'")
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
            name_tok = self._consume_ident("Expected variable name after 'let'")
            type_name = None
            if self._match(TokenType.COLON):
                type_name = self._parse_type_annotation()
            val = None
            if self._match(TokenType.ASSIGN):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return VarDeclStmt(name=name_tok.value, type_name=type_name, value=val, is_mut=False, line=let_tok.line, col=let_tok.col)

        # 5. Variable declaration with explicit type (e.g. x: i32 = 10, ptr: @Point = @p)
        if self._peek().type in CONTEXTUAL_IDENT_TOKENS and self._peek(1).type == TokenType.COLON:
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

        # 7. Loop statement
        if self._check(TokenType.LOOP):
            return self._parse_loop_stmt()

        # 8.5. 'on' Branching statement
        if self._check(TokenType.ON):
            return self._parse_on_stmt()

        # 9. Return statement
        if self._check(TokenType.RETURN):
            ret_tok = self._advance()
            val = None
            if not self._check(TokenType.NEWLINE) and not self._check(TokenType.SEMICOLON) and not self._check(TokenType.RBRACE):
                val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return ReturnStmt(value=val, line=ret_tok.line, col=ret_tok.col)

        # 9.1. Fail statement (error return)
        if self._check(TokenType.FAIL):
            fail_tok = self._advance()
            val = self._parse_expression()
            self._match(TokenType.NEWLINE, TokenType.SEMICOLON)
            return FailStmt(value=val, line=fail_tok.line, col=fail_tok.col)

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

    def _parse_loop_stmt(self) -> LoopStmt:
        loop_tok = self._consume(TokenType.LOOP, "Expected 'loop'")
        self._skip_newlines()

        # 1. Infinite loop: loop { ... }
        if self._check(TokenType.LBRACE):
            body = self._parse_block()
            return LoopStmt(
                iterator="it",
                start_expr=None,
                end_expr=None,
                body=body,
                line=loop_tok.line,
                col=loop_tok.col,
            )

        # 2. Shelf value loop: loop <var> of <collection> { ... }
        #    5.2 slice 4: optional second binding — `loop v, i of coll { }`
        #    (value, then index). More than two bindings rejects at parse.
        if self._check(TokenType.IDENTIFIER) and self._peek(1).type in (TokenType.OF, TokenType.COMMA):
            iterator_tok = self._advance()
            of_index = None
            if self._match(TokenType.COMMA):
                index_tok = self._advance()
                if self._check(TokenType.COMMA):
                    raise ValueError("loop of takes at most two bindings (value, then index)")
                self._consume(TokenType.OF, "Expected 'of' after loop bindings")
                of_index = index_tok.value
            else:
                self._consume(TokenType.OF, "Expected 'of' after loop variable")
            of_expr = self._parse_expression()
            self._skip_newlines()
            body = self._parse_block()
            return LoopStmt(
                iterator=iterator_tok.value,
                start_expr=None,
                end_expr=None,
                of_expr=of_expr,
                of_index=of_index,
                body=body,
                line=loop_tok.line,
                col=loop_tok.col,
            )

        # 2. Named range loop: loop <var> in <start>..<end>[:<step>] { ... }
        if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.IN:
            iterator_tok = self._advance()
            self._consume(TokenType.IN, "Expected 'in' after loop variable")
            start_expr = self._parse_expression()
            is_inclusive = False
            if self._match(TokenType.DOTDOTEQ):
                is_inclusive = True
            else:
                self._consume(TokenType.DOTDOT, "Expected '..' or '..=' in range")
            end_expr = self._parse_expression()
            step_expr = None
            if self._match(TokenType.COLON):
                step_expr = self._parse_expression()
            self._skip_newlines()
            body = self._parse_block()
            return LoopStmt(
                iterator=iterator_tok.value,
                start_expr=start_expr,
                end_expr=end_expr,
                step_expr=step_expr,
                is_inclusive=is_inclusive,
                body=body,
                line=loop_tok.line,
                col=loop_tok.col,
            )

        # 3. Anonymous range or expression (count / condition) loop:
        first_expr = self._parse_expression()
        if self._check(TokenType.DOTDOT) or self._check(TokenType.DOTDOTEQ):
            is_inclusive = False
            if self._match(TokenType.DOTDOTEQ):
                is_inclusive = True
            else:
                self._advance()
            end_expr = self._parse_expression()
            step_expr = None
            if self._match(TokenType.COLON):
                step_expr = self._parse_expression()
            self._skip_newlines()
            body = self._parse_block()
            return LoopStmt(
                iterator="it",
                start_expr=first_expr,
                end_expr=end_expr,
                step_expr=step_expr,
                is_inclusive=is_inclusive,
                body=body,
                line=loop_tok.line,
                col=loop_tok.col,
            )
        else:
            self._skip_newlines()
            body = self._parse_block()
            is_count = isinstance(first_expr, IntLiteral)
            return LoopStmt(
                iterator="it",
                start_expr=None,
                end_expr=None,
                expr=first_expr,
                body=body,
                line=loop_tok.line,
                col=loop_tok.col,
                is_count=is_count,
            )

    def _parse_on_stmt(self) -> MatchStmt:
        on_tok = self._consume(TokenType.ON, "Expected 'on'")
        expr = self._parse_expression()
        self._skip_newlines()
        self._consume(TokenType.LBRACE, "Expected '{' after on expression")
        self._skip_newlines()

        cases: List[MatchCase] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            case_start = self._peek()
            is_default = False
            values: List[Expr] = []

            # Check if else / _ fallback branch
            if self._check(TokenType.ELSE) or (self._check(TokenType.IDENTIFIER) and self._peek().value == "_"):
                self._advance()
                is_default = True
                if self._check(TokenType.FAT_ARROW) or self._check(TokenType.COLON):
                    self._advance()
            else:
                values.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    values.append(self._parse_expression())
                if self._check(TokenType.FAT_ARROW) or self._check(TokenType.COLON):
                    self._advance()
                else:
                    raise ParserError("Expected '=>' or ':' after pattern", self._peek())

            self._skip_newlines()
            if self._check(TokenType.LBRACE):
                body = self._parse_block()
            else:
                stmt = self._parse_statement()
                body = BlockStmt(statements=[stmt] if stmt else [], line=case_start.line, col=case_start.col)

            cases.append(MatchCase(values=values, is_default=is_default, body=body, line=case_start.line, col=case_start.col))
            self._skip_newlines()

        self._consume(TokenType.RBRACE, "Expected '}' at end of on block")
        return MatchStmt(expr=expr, cases=cases, line=on_tok.line, col=on_tok.col)

    # Expression Precedence Hierarchy
    def _parse_expression(self) -> Expr:
        return self._parse_coalesce()

    def _parse_coalesce(self) -> Expr:
        expr = self._parse_logical_or()
        while self._match(TokenType.DOUBLE_QUESTION):
            op_tok = self.tokens[self.pos - 1]
            right = self._parse_logical_or()
            expr = BinaryExpr(left=expr, op="??", right=right, line=expr.line, col=expr.col)
        return expr

    def _parse_logical_or(self) -> Expr:
        expr = self._parse_logical_and()
        while self._match(TokenType.OR):
            op_tok = self.tokens[self.pos - 1]
            if self._match(TokenType.RETURN):
                expr = OrReturnExpr(operand=expr, line=op_tok.line, col=op_tok.col)
            else:
                right = self._parse_logical_and()
                expr = BinaryExpr(left=expr, op=op_tok.value, right=right, line=expr.line, col=expr.col)
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

    def _is_generic_call(self) -> bool:
        if not self._check(TokenType.LBRACKET):
            return False
        depth = 1
        idx = 1
        while self.pos + idx < len(self.tokens) and depth > 0:
            tok = self.tokens[self.pos + idx]
            if tok.type == TokenType.LBRACKET:
                depth += 1
            elif tok.type == TokenType.RBRACKET:
                depth -= 1
            idx += 1
        if depth != 0:
            return False
        if self.pos + idx < len(self.tokens) and self.tokens[self.pos + idx].type == TokenType.LPAREN:
            return True
        return False

    def _parse_postfix(self) -> Expr:
        expr = self._parse_primary()

        while True:
            if self._match(TokenType.DOT):
                if self._match(TokenType.AT):
                    at_tok = self.tokens[self.pos - 1]
                    expr = DerefExpr(operand=expr, line=at_tok.line, col=at_tok.col)
                else:
                    # 5.2 slice 9: `.and(` — the AND keyword is contextual after a
                    # dot (the pinned bitset pair-op surface)
                    if not (self._check(TokenType.IDENTIFIER) or self._peek().type in CONTEXTUAL_IDENT_TOKENS or self._check(TokenType.AND)):
                        raise ParserError("Expected member name after '.'", self._peek())
                    member_tok = self._advance()
                    expr = MemberAccess(target=expr, member=member_tok.value, line=member_tok.line, col=member_tok.col)
            elif self._check(TokenType.LBRACKET) and self._is_generic_call():
                self._advance()
                type_args: List[str] = []
                while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                    type_args.append(self._parse_type_annotation())
                    if not self._match(TokenType.COMMA):
                        break
                self._consume(TokenType.RBRACKET, "Expected ']' after generic type arguments")
                lparen = self._consume(TokenType.LPAREN, "Expected '(' after generic type arguments")
                args: List[Expr] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after arguments")
                expr = CallExpr(callee=expr, args=args, line=lparen.line, col=lparen.col, type_args=type_args)
            elif self._match(TokenType.LBRACKET):
                lbracket = self.tokens[self.pos - 1]
                idx_expr = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Expected ']' after array index")
                expr = IndexExpr(target=expr, index=idx_expr, line=lbracket.line, col=lbracket.col)
            elif self._match(TokenType.AS):
                as_tok = self.tokens[self.pos - 1]
                target_type = self._parse_type_annotation(allow_or=False)
                expr = CastExpr(expr=expr, target_type=target_type, line=as_tok.line, col=as_tok.col)
            elif self._match(TokenType.BANG):
                bang_tok = self.tokens[self.pos - 1]
                expr = UnwrapExpr(operand=expr, line=bang_tok.line, col=bang_tok.col)
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
        if not self._check(TokenType.IDENTIFIER):
            return False
        
        ident_name = self._peek().value
        if not ident_name or not ident_name[0].isupper():
            return False

        idx = 1
        if self._peek(idx).type == TokenType.LBRACKET:
            depth = 1
            idx += 1
            while self.pos + idx < len(self.tokens) and depth > 0:
                tok = self.tokens[self.pos + idx]
                if tok.type == TokenType.LBRACKET:
                    depth += 1
                elif tok.type == TokenType.RBRACKET:
                    depth -= 1
                idx += 1
            if depth != 0:
                return False

        if self._peek(idx).type != TokenType.LBRACE:
            return False

        idx += 1
        while self.pos + idx < len(self.tokens) and self.tokens[self.pos + idx].type in (TokenType.NEWLINE, TokenType.SEMICOLON):
            idx += 1
        
        target_tok = self._peek(idx)
        if target_tok.type == TokenType.RBRACE:
            return True
        if target_tok.type in CONTEXTUAL_IDENT_TOKENS and self._peek(idx + 1).type == TokenType.COLON:
            return True
        return False

    def _parse_primary(self) -> Expr:
        if self._is_struct_literal():
            id_tok = self._advance()
            struct_name = id_tok.value
            if self._match(TokenType.LBRACKET):
                args = []
                while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                    args.append(self._parse_type_annotation())
                    if not self._match(TokenType.COMMA):
                        break
                self._consume(TokenType.RBRACKET, "Expected ']' after type arguments in struct literal")
                struct_name += "[" + ", ".join(args) + "]"
            self._consume(TokenType.LBRACE, "Expected '{' after struct name")
            self._skip_newlines()
            field_inits: List[Tuple[str, Expr]] = []
            while not self._check(TokenType.RBRACE) and not self._is_at_end():
                fname = self._consume_ident("Expected field name in struct literal")
                self._consume(TokenType.COLON, "Expected ':' after field name")
                fval = self._parse_expression()
                field_inits.append((fname.value, fval))
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    self._skip_newlines()
                    break
            self._consume(TokenType.RBRACE, "Expected '}' at end of struct literal")
            return StructLiteral(struct_name=struct_name, field_inits=field_inits, line=id_tok.line, col=id_tok.col)

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
        if self._match(TokenType.HEAP):
            # 5.2 slice 10: `heap shelf[...]` / Task 7.2: `heap map[...]`
            heap_tok = self.tokens[self.pos - 1]
            if self._match(TokenType.SHELF):
                self._consume(TokenType.LBRACKET, "Expected '[' after 'heap shelf' (heap shelf literal: heap shelf[1, 2])")
                self._skip_newlines()
                args: List[Expr] = []
                while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                    args.append(self._parse_expression())
                    self._skip_newlines()
                    if not self._match(TokenType.COMMA):
                        break
                    self._skip_newlines()
                self._consume(TokenType.RBRACKET, "Expected ']' at end of heap shelf literal")
                return ShelfLiteral(args=args, line=heap_tok.line, col=heap_tok.col, is_heap=True)
            elif self._match(TokenType.MAP):
                self._consume(TokenType.LBRACKET, "Expected '[' after 'heap map' (heap map literal: heap map[1: \"a\", 2: \"b\"])")
                self._skip_newlines()
                keys: List[Expr] = []
                vals: List[Expr] = []
                while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                    keys.append(self._parse_expression())
                    self._skip_newlines()
                    self._consume(TokenType.COLON, "Expected ':' between a map key and value (heap map[k: v])")
                    self._skip_newlines()
                    vals.append(self._parse_expression())
                    self._skip_newlines()
                    if not self._match(TokenType.COMMA):
                        break
                    self._skip_newlines()
                self._consume(TokenType.RBRACKET, "Expected ']' at end of heap map literal")
                return MapLiteral(keys=keys, vals=vals, line=heap_tok.line, col=heap_tok.col, is_heap=True)
            else:
                self._error("Expected 'shelf' or 'map' after 'heap'")

        if self._match(TokenType.SHELF):
            # 5.2: shelf constructor literal — bracket args are VALUES
            # (homogeneous; empty `shelf[]` needs a type annotation).
            shelf_tok = self.tokens[self.pos - 1]
            self._consume(TokenType.LBRACKET, "Expected '[' after 'shelf' (shelf literal: shelf[1, 2, 3])")
            self._skip_newlines()
            args: List[Expr] = []
            while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                args.append(self._parse_expression())
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    break
                self._skip_newlines()
            self._consume(TokenType.RBRACKET, "Expected ']' at end of shelf literal")
            return ShelfLiteral(args=args, line=shelf_tok.line, col=shelf_tok.col)

        if self._match(TokenType.MAP):
            # 5.2 slice 6: map constructor literal `map[k0: v0, k1: v1, ...]`.
            # Alternating key/value pairs; empty `map[]` needs an annotation.
            map_tok = self.tokens[self.pos - 1]
            self._consume(TokenType.LBRACKET, "Expected '[' after 'map' (map literal: map[1: \"a\", 2: \"b\"])")
            self._skip_newlines()
            keys: List[Expr] = []
            vals: List[Expr] = []
            while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                keys.append(self._parse_expression())
                self._skip_newlines()
                self._consume(TokenType.COLON, "Expected ':' between a map key and value (map[k: v])")
                self._skip_newlines()
                vals.append(self._parse_expression())
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    break
                self._skip_newlines()
            self._consume(TokenType.RBRACKET, "Expected ']' at end of map literal")
            return MapLiteral(keys=keys, vals=vals, line=map_tok.line, col=map_tok.col)

        if self._match(TokenType.RING):
            # 5.2 slice 9: ring constructor literal `ring[v0, v1, ...]` —
            # the shelf bracket-value shape; the element ladder (no dyn arm)
            # lives in the checker. Empty `ring[]` needs an annotation.
            ring_tok = self.tokens[self.pos - 1]
            self._consume(TokenType.LBRACKET, "Expected '[' after 'ring' (ring literal: ring[1, 2, 3])")
            self._skip_newlines()
            args = []
            while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                args.append(self._parse_expression())
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    break
                self._skip_newlines()
            self._consume(TokenType.RBRACKET, "Expected ']' at end of ring literal")
            return RingLiteral(args=args, line=ring_tok.line, col=ring_tok.col)

        if self._match(TokenType.BITSET):
            # 5.2 slice 9: bitset constructor literal `bitset[i0, i1, ...]` —
            # integer-typed elements lower to set() calls; `bitset[]` infers
            # `bitset` with no annotation.
            bs_tok = self.tokens[self.pos - 1]
            self._consume(TokenType.LBRACKET, "Expected '[' after 'bitset' (bitset literal: bitset[1, 9])")
            self._skip_newlines()
            args = []
            while not self._check(TokenType.RBRACKET) and not self._is_at_end():
                args.append(self._parse_expression())
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    break
                self._skip_newlines()
            self._consume(TokenType.RBRACKET, "Expected ']' at end of bitset literal")
            return BitsetLiteral(args=args, line=bs_tok.line, col=bs_tok.col)

        if self._match(TokenType.IDENTIFIER):
            return Identifier(name=tok.value, line=tok.line, col=tok.col)
        if self._match(TokenType.DOT):
            dot_tok = self.tokens[self.pos - 1]
            var_tok = self._consume(TokenType.IDENTIFIER, "Expected variant name after '.'")
            args: List[Expr] = []
            if self._match(TokenType.LPAREN):
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after variant arguments")
            return VariantExpr(kind_name=None, variant_name=var_tok.value, args=args, line=dot_tok.line, col=dot_tok.col)
        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')' after grouped expression")
            return expr
        if self._match(TokenType.ACT):
            act_tok = self.tokens[self.pos - 1]
            self._consume(TokenType.LPAREN, "Expected '(' after 'act' in anonymous function")
            params: List[Param] = []
            if not self._check(TokenType.RPAREN):
                while True:
                    pname_tok = self._consume_ident("Expected parameter name")
                    self._consume(TokenType.COLON, "Expected ':' after parameter name")
                    ptype = self._parse_type_annotation()
                    params.append(Param(name=pname_tok.value, type_name=ptype, line=pname_tok.line, col=pname_tok.col))
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RPAREN, "Expected ')' after parameters")
            ret_type = "void"
            if self._match(TokenType.ARROW):
                ret_type = self._parse_type_annotation()
            self._skip_newlines()
            body = self._parse_block()
            return AnonFuncExpr(params=params, return_type=ret_type, body=body, line=act_tok.line, col=act_tok.col)

        raise ParserError(f"Unexpected token in expression: {tok.type.name} ('{tok.value}')", tok)
