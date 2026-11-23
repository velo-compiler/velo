// Phase 4 grammar spot-checks (dependency-free stand-in for a full TM engine):
// each case takes a REAL language sample line and asserts which scopes the
// grammar's own patterns produce — encoding behavioral decisions (aka shape
// guard, sys.str root exclusion, PascalCase dot-variants) as tests.
//
// Engine semantics reproduced: the top-level include list is walked in order;
// at each scan position the FIRST matching pattern (highlight ordering) wins
// and consumes its match. That is exactly how TM engines resolve, minus begin/
// while blocks (this grammar uses none for the lines under test).
//
// Full tokenization with the industry tool (vscode-tmgrammar-test) is the CI
// tier; this static harness proves the critical regex behaviors locally with
// zero npm installs.
"use strict";
const assert = require("assert");
const path = require("path");

const grammar = require(path.join(__dirname, "..", "syntaxes", "velo.tmLanguage.json"));
const pkgGrammar = require(path.join(__dirname, "..", "syntaxes", "velo.pkg.tmLanguage.json"));

function* flatten(node) {
    if (Array.isArray(node)) { for (const item of node) yield* flatten(item); return; }
    if (!node || typeof node !== "object") return;
    if (node.patterns) { yield* flatten(node.patterns); return; }
    yield node;
}

function compileRules(g) {
    const r = [];
    for (const include of g.patterns) {
        const section = g.repository[include.include.slice(1)];
        for (const pattern of flatten(section)) {
            const scopes = new Set();
            if (pattern.name) scopes.add(pattern.name);
            for (const cap of Object.values(pattern.captures || {})) {
                if (cap.name) scopes.add(cap.name);
            }
            try {
                r.push({ re: new RegExp(pattern.begin || pattern.match, ""), scopes });
            } catch (err) {
                throw new Error(`grammar pattern failed to compile: ${err.message} (${JSON.stringify(pattern.match)})`);
            }
        }
    }
    return r;
}

const rules = compileRules(grammar);
const pkgRules = compileRules(pkgGrammar);

function scopesForRules(rList, line) {
    const scopes = new Set();
    let at = 0;
    outer: while (at < line.length) {
        for (const rule of rList) {
            const hit = rule.re.exec(line.slice(at));
            if (hit && hit.index === 0 && hit[0].length > 0) {
                for (const s of rule.scopes) scopes.add(s);
                at += hit[0].length;
                continue outer;
            }
        }
        at += 1;
    }
    return scopes;
}

function scopesFor(line) { return scopesForRules(rules, line); }
function scopesForPkg(line) { return scopesForRules(pkgRules, line); }

let passed = 0;
const ok = (name) => { passed++; console.log(`PASS ${name}`); };

const CASES = [
    ["aka declaration shape highlights at column 0", "aka EntityId = u32", "keyword.declaration.alias.velo", true],
    ["aka mid-line stays a plain identifier (contextual keyword)", "let aka = 1", "keyword.declaration.alias.velo", false],
    ["#align attribute gets attribute scopes", "data P { #align(8) }", "entity.other.attribute-name.velo", true],
    ["#packed attribute highlighted", "data Q #packed { }", "punctuation.definition.attribute.velo", true],
    [".KeyDown dot-variant is an enum member", "on e { .KeyDown(65) => break }", "variable.other.enummember.dot.velo", true],
    ["lowercase .keydown is NOT a dot-variant", "let x = e.keydown", "variable.other.enummember.dot.velo", false],
    ["sys.io use-root highlighted", "use sys.io", "support.class.module.velo", true],
    ["sys.str is NOT a use root (Stage 2 loader truth)", "use sys.str", "support.class.module.velo", false],
    ["io.println call-site highlighted", "    io.println(\"ok\")", "support.function.builtin.io.velo", true],
    ["fs.remove_file call-site highlighted", "    fs.remove_file(p)", "support.function.builtin.fs.velo", true],
    ["str.len call-site highlighted (str stays a member surface)", "str.len(s)", "support.function.builtin.str.velo", true],
    ["integer with suffix", "let x: u64 = 255u8", "constant.numeric.integer.velo", true],
    ["hex number", "let m: u32 = 0xFFu32", "constant.numeric.hex.velo", true],
    ["char literal escape", "let nl: u8 = '\\n'", "constant.character.velo", true],
    ["std.io use-root highlighted", "use std.io", "support.class.module.velo", true],
    ["std.fs use-root highlighted", "use std.fs", "support.class.std.velo", true],
    ["std.invalid is NOT a std root", "use std.invalid", "support.class.std.velo", false],
    ["println_str call-site highlighted", 'println_str("ok")', "support.function.std.velo", true],
    ["fs_read_to_str call-site highlighted", 'fs_read_to_str("f.txt")', "support.function.std.velo", true],
    ["f32x4 SIMD type highlighted", "let v: f32x4 = x", "support.type.primitive.simd.velo", true],
    ["i32x4 SIMD type highlighted", "let v: i32x4 = y", "support.type.primitive.simd.velo", true],
    ["view storage modifier highlighted", "view act add(a: i32) -> i32", "storage.modifier.view.velo", true],
    ["pact contract type highlighted", "pact Printable { act print() }", "storage.type.contract.pact.velo", true],
    ["unsafe control block highlighted", "unsafe { let p = 0 }", "keyword.control.unsafe.velo", true],
];

for (const [name, line, expected, wantPresent] of CASES) {
    const produced = scopesFor(line);
    assert(produced.has(expected) === wantPresent,
        `${name}\n  line:    ${JSON.stringify(line)}\n  want ${wantPresent ? "presence" : "absence"}: ${expected}\n  got:     ${[...produced].join(", ")}`);
    ok(name);
}

const PKG_CASES = [
    ["velo.pkg block keyword", 'pkg "my_app" {', "keyword.declaration.block.pkg.velo", true],
    ["velo.pkg package name string", 'pkg "my_app" {', "string.quoted.double.package.name.velo", true],
    ["velo.pkg version property", '    version: "0.1.0"', "support.type.property-name.velo", true],
    ["velo.pkg deps block", "deps {", "keyword.declaration.block.velo", true],
    ["velo.pkg git protocol", '    raylib: git "https://github.com/..." @ "v1.0"', "keyword.other.protocol.velo", true],
    ["velo.pkg link block", "link {", "keyword.declaration.block.velo", true],
    ["velo.pkg libs property", '    libs: ["raylib"]', "support.type.property-name.velo", true],
];

for (const [name, line, expected, wantPresent] of PKG_CASES) {
    const produced = scopesForPkg(line);
    assert(produced.has(expected) === wantPresent,
        `${name}\n  line:    ${JSON.stringify(line)}\n  want ${wantPresent ? "presence" : "absence"}: ${expected}\n  got:     ${[...produced].join(", ")}`);
    ok(name);
}

console.log(`\nALL ${passed} GRAMMAR SPOT-CHECKS PASSED`);
process.exit(0);
