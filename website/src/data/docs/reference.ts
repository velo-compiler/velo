import { DocCategory } from '../../types/docs';

export const REFERENCE_CATEGORY: DocCategory = {
  id: 'reference',
  name: '14. Language Reference',
  description: 'Complete formal EBNF language grammar, compiler diagnostic codes, and troubleshooting guide.',
  iconName: 'Terminal',
  pages: [
    {
      id: 'reference-grammar',
      slug: 'reference-grammar',
      title: 'Formal Language Grammar',
      category: '14. Language Reference',
      categoryOrder: 14,
      order: 1,
      description: 'The complete EBNF specification of Velo lexical grammar, declarations, types, and expressions.',
      readTimeMinutes: 7,
      badge: 'EBNF',
      whatYoullLearn: [
        'Formal EBNF notation for Velo programs',
        'Declaration syntax rules (act, data, kind, aka)',
        'Statement and expression grammar',
        'Type expressions and pointer syntax'
      ],
      sections: [
        {
          id: 'ebnf-declarations',
          title: 'Declarations Grammar (EBNF)',
          content: `The top-level structure of a Velo translation unit:

\`\`\`ebnf
Program         ::= { UseDecl | TopDecl }
UseDecl         ::= "use" ( StringLiteral | ModulePath | GroupedImport )
GroupedImport   ::= ModulePath ".{" Identifier { "," Identifier } "}"
TopDecl         ::= FunctionDecl | StructDecl | KindDecl | AliasDecl | ExternDecl | TestDecl

FunctionDecl    ::= "act" ( Identifier | "op" Operator ) [ GenericParams ] 
                    "(" [ ParamList ] ")" [ "->" Type ] Block
StructDecl      ::= "data" Identifier [ GenericParams ] [ LayoutAttr ] "{" { FieldDecl } "}"
KindDecl        ::= "kind" Identifier [ GenericParams ] "{" { VariantDecl } "}"
AliasDecl       ::= "aka" Identifier "=" Type
ExternDecl      ::= "extern" "act" Identifier "(" [ ParamList ] ")" [ "->" Type ]
\`\`\``
        },
        {
          id: 'ebnf-statements',
          title: 'Statements & Control Flow Grammar',
          content: `\`\`\`ebnf
Statement       ::= VarDecl | AssignStmt | IfStmt | LoopStmt | OnStmt 
                  | ReturnStmt | DeferStmt | ZoneStmt | ExprStmt

VarDecl         ::= [ "mut" | "let" ] Identifier [ ":" Type ] [ "=" Expr ]
AssignStmt      ::= LValue ( "=" | "+=" | "-=" | "*=" | "/=" ) Expr
IfStmt          ::= "if" Expr Block [ "else" ( IfStmt | Block ) ]
LoopStmt        ::= "loop" [ LoopHead ] Block
LoopHead        ::= Expr                         (* Conditional / Repeat *)
                  | Identifier "in" Expr ".." Expr [ ":" Expr ] (* Range *)
                  | Identifier "of" Expr         (* Collection snapshot *)
OnStmt          ::= "on" Expr "{" { Arm } "}"
Arm             ::= [ "." ] Identifier [ "(" [ ParamList ] ")" ] "=>" Block
ZoneStmt        ::= "zone" Block
DeferStmt       ::= "defer" Statement
\`\`\``
        }
      ],
      prevPage: { title: 'Tutorial: Real-Time Particle Simulation', slug: 'case-study-gamedev' },
      nextPage: { title: 'Compiler Diagnostics & Troubleshooting', slug: 'reference-diagnostics' }
    },
    {
      id: 'reference-diagnostics',
      slug: 'reference-diagnostics',
      title: 'Compiler Diagnostics & Troubleshooting',
      category: '14. Language Reference',
      categoryOrder: 14,
      order: 2,
      description: 'Understanding Velo error diagnostics, common compiler errors, and how to fix them quickly.',
      readTimeMinutes: 6,
      badge: 'Troubleshooting',
      whatYoullLearn: [
        'Interpreting visual snippet compiler diagnostics',
        'Common beginner errors and exact solutions',
        'Fixing immutability reassignments',
        'Resolving pointer vs value mismatches'
      ],
      sections: [
        {
          id: 'diagnostics-format',
          title: 'Diagnostic Snippet Format',
          content: `When the Velo compiler detects an error, it prints a pinpointed source snippet:

\`\`\`
[Velo Error] semantic: cannot assign to immutable variable 'score'. Declare with 'mut score' to allow mutation.
  --> app.vl:14:5
   |
14 |     score = 100
   |     ^^^^^ immutable variable reassignment
\`\`\``
        },
        {
          id: 'common-errors',
          title: 'Common Compiler Errors & Solutions',
          content: `### 1. "cannot assign to immutable variable 'x'"
- **Cause**: Attempting to reassign a variable declared without \`mut\`.
- **Fix**: Change \`x = ...\` or \`let x = ...\` to \`mut x = ...\`.

### 2. "unexpected character '\\ufeff'"
- **Cause**: Saving a file with UTF-8 BOM encoding.
- **Fix**: Re-save the file in your editor as standard UTF-8 without BOM.

### 3. "missing field 'y' with no default initializer"
- **Cause**: Initializing a struct literal without specifying a non-defaulted field.
- **Fix**: Supply the missing field in the literal: \`Point{ x: 10.0, y: 20.0 }\` or add a default initializer in the struct definition: \`y: f32 = 0.0\`.

### 4. "target of aka must be primitive"
- **Cause**: Aliasing a complex struct or kind with \`aka\` (e.g. \`aka P = Point\`).
- **Fix**: \`aka\` only aliases primitive types (\`u64\`, \`f32\`) or pointer-to-primitives (\`@u8\`). For structs, use the struct name directly.`
        }
      ],
      prevPage: { title: 'Formal Language Grammar', slug: 'reference-grammar' }
    }
  ]
};

