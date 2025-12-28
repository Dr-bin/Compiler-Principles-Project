"""
End-to-end integration tests:
From rule files -> generated lexer/parser -> parse -> IR generation

Goals:
- Do not swallow parsing errors for the main demo language (simple_expr)
- Ensure IR is actually produced (non-empty)
- Add negative cases (lexical error / syntax error)
"""

from pathlib import Path
import pytest

from src.frontend.rule_parser import RuleParser, load_rules_from_files
from src.compiler_generator.lexer_generator import create_lexer_from_spec
from src.compiler_generator.parser_generator import create_parser_from_spec
from src.compiler_generator.code_generator import CodeGenerator


EXAMPLES = Path("examples")


def _require(path: Path):
    if not path.exists():
        pytest.skip(f"Missing example file: {path}")


def _pick_start_symbol(grammar_rules: dict) -> str:
    # Try common start symbol names first
    for cand in ("Program", "program", "S", "Start", "start"):
        if cand in grammar_rules:
            return cand
    return next(iter(grammar_rules.keys()))


def _try_codegen_generate(codegen: CodeGenerator, ast):
    """
    Adapt to different CodeGenerator APIs.
    If your project later switches to SDT (emit during parse),
    this will simply do nothing but still keep tests compatible.
    """
    if ast is None:
        return

    # common method names
    for name in ("generate", "gen", "visit", "traverse", "emit_from_ast"):
        fn = getattr(codegen, name, None)
        if callable(fn):
            fn(ast)
            return


@pytest.fixture
def simple_expr_rules():
    lexer_file = EXAMPLES / "simple_expr" / "lexer_rules.txt"
    grammar_file = EXAMPLES / "simple_expr" / "grammar_rules.txt"
    _require(lexer_file)
    _require(grammar_file)

    lexer_rules, grammar_rules = load_rules_from_files(str(lexer_file), str(grammar_file))
    assert lexer_rules, "Lexer rules should not be empty"
    assert grammar_rules, "Grammar rules should not be empty"
    return lexer_rules, grammar_rules


@pytest.mark.integration
def test_end_to_end_simple_expr_generates_ir(simple_expr_rules):
    lexer_rules, grammar_rules = simple_expr_rules

    lexer = create_lexer_from_spec(lexer_rules)
    start_symbol = _pick_start_symbol(grammar_rules)
    parser = create_parser_from_spec(grammar_rules, start_symbol)

    src = "x = 1 + 2 ;"
    tokens = lexer.tokenize(src)
    assert tokens and tokens[-1].type == "EOF"

    codegen = CodeGenerator()

    # Prefer SDT-style parse(tokens, codegen=codegen) if supported; else parse(tokens) then codegen(ast)
    try:
        ast = parser.parse(tokens, codegen=codegen)
    except TypeError:
        ast = parser.parse(tokens)

    assert ast is not None, "Parser should return AST for a valid program"

    # If codegen still requires AST traversal, do it here
    _try_codegen_generate(codegen, ast)

    ir = codegen.get_code()
    assert isinstance(ir, str)
    assert ir.strip() != "", "IR should not be empty for a valid program"

    # Soft checks: avoid binding to exact TAC format, but ensure meaningful content.
    assert ("=" in ir) or ("t" in ir) or ("temp" in ir) or ("goto" in ir.lower())


@pytest.mark.integration
def test_end_to_end_lexical_error(simple_expr_rules):
    lexer_rules, _ = simple_expr_rules
    lexer = create_lexer_from_spec(lexer_rules)

    with pytest.raises(SyntaxError):
        lexer.tokenize("1 + @ ;")


@pytest.mark.integration
def test_end_to_end_syntax_error(simple_expr_rules):
    lexer_rules, grammar_rules = simple_expr_rules
    lexer = create_lexer_from_spec(lexer_rules)

    start_symbol = _pick_start_symbol(grammar_rules)
    parser = create_parser_from_spec(grammar_rules, start_symbol)

    # Missing semicolon (or other expected terminator)
    tokens = lexer.tokenize("x = 1 + 2")
    with pytest.raises(Exception):
        parser.parse(tokens)


@pytest.mark.integration
def test_rule_parser_smoke():
    lexer_file = EXAMPLES / "simple_expr" / "lexer_rules.txt"
    _require(lexer_file)

    rules = RuleParser.parse_lexer_rules(str(lexer_file))
    assert rules, "Should parse some rules"
    assert all(isinstance(r, tuple) and len(r) == 2 for r in rules), \
        "Each rule should be a (token_type, pattern) tuple"
