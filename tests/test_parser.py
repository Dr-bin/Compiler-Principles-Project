"""
Parser unit tests (comprehensive coverage from basic to advanced)

Coverage:
1) ParserGenerator API and grammar storage
2) FIRST/FOLLOW and ε selection logic (if implementation exposes related structures)
3) LL(1) parsing correctness: single token -> sequence -> nested
4) Left recursion elimination: grammar rewriting + parsability verification
5) Error handling: unexpected token, missing token, leftover token, repeated parse state isolation
"""

import pytest

from src.compiler_generator.lexer_generator import Token
from src.compiler_generator.parser_generator import ParserGenerator, ParseError, ASTNode


# -------------------------
# Helpers
# -------------------------

def T(tp: str, val: str = "", line: int = 1, col: int = 1) -> Token:
    """Quick Token constructor: tp is token.type, val is token.value"""
    return Token(tp, val, line, col)


def build_num_only_parser() -> ParserGenerator:
    """
    Minimal grammar:
      Expr -> 'NUM'
    """
    p = ParserGenerator()
    p.set_start_symbol("Expr")
    p.add_production("Expr", ["'NUM'"])
    return p


def build_simple_expr_ll1_parser() -> ParserGenerator:
    """
    A more complete, LL(1) expression grammar with precedence support (no left recursion):
      Expr      -> Term ExprTail
      ExprTail  -> 'PLUS' Term ExprTail | ε
      Term      -> Factor TermTail
      TermTail  -> 'MUL' Factor TermTail | ε
      Factor    -> 'NUM' | 'ID' | 'LPAREN' Expr 'RPAREN'

    Note: ε is represented by []
    """
    p = ParserGenerator()
    p.set_start_symbol("Expr")

    p.add_production("Expr", ["Term", "ExprTail"])

    p.add_production("ExprTail", ["'PLUS'", "Term", "ExprTail"])
    p.add_production("ExprTail", [])  # ε

    p.add_production("Term", ["Factor", "TermTail"])

    p.add_production("TermTail", ["'MUL'", "Factor", "TermTail"])
    p.add_production("TermTail", [])  # ε

    p.add_production("Factor", ["'NUM'"])
    p.add_production("Factor", ["'ID'"])
    p.add_production("Factor", ["'LPAREN'", "Expr", "'RPAREN'"])

    return p


def assert_tree_has_node(root: ASTNode, name: str) -> None:
    """Weak constraint: AST contains at least one node with given name (does not enforce specific structure)"""
    stack = [root]
    while stack:
        cur = stack.pop()
        if cur.name == name:
            return
        stack.extend(getattr(cur, "children", []) or [])
    assert False, f"AST does not contain node '{name}'"


# -------------------------
# 1) API / Grammar building
# -------------------------

class TestParserGenerator:
    def test_create_parser(self):
        """Test creating parser + start_symbol"""
        parser = ParserGenerator()
        parser.set_start_symbol("Expr")
        parser.add_production("Expr", ["Term"])

        assert parser.start_symbol == "Expr"
        assert "Expr" in parser.grammar
        assert parser.grammar["Expr"] == [["Term"]]

    def test_add_production_multiple(self):
        """Test adding multiple productions"""
        parser = ParserGenerator()
        parser.set_start_symbol("Expr")
        parser.add_production("Expr", ["Term", "'PLUS'", "Expr"])
        parser.add_production("Expr", ["Term"])

        assert len(parser.grammar["Expr"]) == 2

    def test_ast_node_creation(self):
        """Test ASTNode basic construction"""
        token = T("NUM", "123", 1, 1)
        node = ASTNode(name="NUM", token=token)

        assert node.name == "NUM"
        assert node.token.value == "123"
        assert node.children == []


# -------------------------
# 2) Parsing correctness (shallow -> deep)
# -------------------------

class TestParsingBasics:
    def test_parse_single_terminal(self):
        """Expr -> 'NUM'"""
        parser = build_num_only_parser()
        tokens = [T("NUM", "123", 1, 1), T("EOF", "", 1, 4)]

        ast = parser.parse(tokens)
        assert ast.name == "Expr"
        assert_tree_has_node(ast, "NUM")

    @pytest.mark.parametrize(
        "tok_type,tok_val",
        [("NUM", "1"), ("ID", "x")]
    )
    def test_parse_with_alternatives(self, tok_type, tok_val):
        """Expr -> 'NUM' | 'ID'"""
        parser = ParserGenerator()
        parser.set_start_symbol("Expr")
        parser.add_production("Expr", ["'NUM'"])
        parser.add_production("Expr", ["'ID'"])

        tokens = [T(tok_type, tok_val, 1, 1), T("EOF", "", 1, 2)]
        ast = parser.parse(tokens)
        assert ast.name == "Expr"
        assert_tree_has_node(ast, tok_type)

    def test_parse_sequence_plus(self):
        """
        Parse using LL(1) expression grammar: NUM PLUS NUM
        Goal: correctly take ExprTail branch, not immediately choose ε
        """
        parser = build_simple_expr_ll1_parser()
        tokens = [
            T("NUM", "1", 1, 1),
            T("PLUS", "+", 1, 3),
            T("NUM", "2", 1, 5),
            T("EOF", "", 1, 6),
        ]

        ast = parser.parse(tokens)
        assert ast.name == "Expr"
        assert_tree_has_node(ast, "PLUS")
        assert_tree_has_node(ast, "NUM")

    def test_parse_precedence_mul_over_plus(self):
        """
        NUM PLUS NUM MUL NUM
        Goal: TermTail consumes MUL first, then returns to ExprTail to process PLUS
        (Only weak structure assertion: AST contains at least PLUS/MUL)
        """
        parser = build_simple_expr_ll1_parser()
        tokens = [
            T("NUM", "1", 1, 1),
            T("PLUS", "+", 1, 3),
            T("NUM", "2", 1, 5),
            T("MUL", "*", 1, 7),
            T("NUM", "3", 1, 9),
            T("EOF", "", 1, 10),
        ]

        ast = parser.parse(tokens)
        assert ast.name == "Expr"
        assert_tree_has_node(ast, "PLUS")
        assert_tree_has_node(ast, "MUL")

    def test_parse_parentheses_nested(self):
        """(NUM PLUS NUM) MUL NUM"""
        parser = build_simple_expr_ll1_parser()
        tokens = [
            T("LPAREN", "(", 1, 1),
            T("NUM", "1", 1, 2),
            T("PLUS", "+", 1, 4),
            T("NUM", "2", 1, 6),
            T("RPAREN", ")", 1, 7),
            T("MUL", "*", 1, 9),
            T("NUM", "3", 1, 11),
            T("EOF", "", 1, 12),
        ]

        ast = parser.parse(tokens)
        assert ast.name == "Expr"
        assert_tree_has_node(ast, "LPAREN")
        assert_tree_has_node(ast, "RPAREN")
        assert_tree_has_node(ast, "MUL")


# -------------------------
# 3) ε production and FOLLOW selection (critical LL(1) branch decision)
# -------------------------

class TestEpsilonAndFollowChoice:
    def test_parse_with_epsilon_production_follow_select(self):
        """
        S -> A 'EOF'
        A -> 'X' B
        B -> 'Y' | ε

        Input: X EOF
        Expected: B chooses ε (because lookahead is EOF, which is in FOLLOW(B))
        """
        p = ParserGenerator()
        p.set_start_symbol("S")
        p.add_production("S", ["A", "'EOF'"])
        p.add_production("A", ["'X'", "B"])
        p.add_production("B", ["'Y'"])
        p.add_production("B", [])  # ε

        tokens = [
            T("X", "x", 1, 1),
            T("EOF", "", 1, 2),
        ]

        ast = p.parse(tokens)
        assert ast.name == "S"
        assert_tree_has_node(ast, "X")
        # B should exist and take ε path: typically B node has empty children
        assert_tree_has_node(ast, "B")

    def test_build_analysis_sets_optional_introspection(self):
        """
        If implementation exposes first_sets / follow_sets / parse_table,
        make more detailed assertions; if fields are not exposed, skip.
        """
        p = build_simple_expr_ll1_parser()
        # Some implementations lazy-load analysis sets in parse(), explicitly trigger here
        if hasattr(p, "build_analysis_sets"):
            p.build_analysis_sets()

        # Only assert if fields exist, avoid binding to internal implementation
        if hasattr(p, "first_sets"):
            assert "Expr" in p.first_sets
        else:
            pytest.skip("ParserGenerator.first_sets not exposed")

        if hasattr(p, "follow_sets"):
            assert "Expr" in p.follow_sets
        else:
            pytest.skip("ParserGenerator.follow_sets not exposed")


# -------------------------
# 4) Left recursion elimination (more "advanced" capability)
# -------------------------

class TestLeftRecursionElimination:
    def test_left_recursion_elimination_transform(self):
        """
        E -> E 'PLUS' T | T

        After left recursion elimination is triggered, E_TAIL (or similar suffix nonterminal) should appear:
          E -> T E_TAIL
          E_TAIL -> 'PLUS' T E_TAIL | ε
        """
        p = ParserGenerator()
        p.set_start_symbol("E")
        p.add_production("E", ["E", "'PLUS'", "T"])
        p.add_production("E", ["T"])
        p.add_production("T", ["'NUM'"])

        p.build_analysis_sets()

        assert "E" in p.grammar
        assert len(p.grammar["E"]) == 1
        assert p.grammar["E"][0] == ["T", "E_TAIL"]

        assert "E_TAIL" in p.grammar
        assert ["'PLUS'", "T", "E_TAIL"] in p.grammar["E_TAIL"]
        assert [] in p.grammar["E_TAIL"]  # ε

    def test_left_recursion_elimination_parse_chain(self):
        """
        Use left-recursive grammar (rewritten during build_analysis_sets()) to parse: NUM PLUS NUM PLUS NUM
        """
        p = ParserGenerator()
        p.set_start_symbol("E")
        p.add_production("E", ["E", "'PLUS'", "T"])
        p.add_production("E", ["T"])
        p.add_production("T", ["'NUM'"])

        tokens = [
            T("NUM", "1", 1, 1),
            T("PLUS", "+", 1, 3),
            T("NUM", "2", 1, 5),
            T("PLUS", "+", 1, 7),
            T("NUM", "3", 1, 9),
            T("EOF", "", 1, 10),
        ]

        ast = p.parse(tokens)
        assert ast.name == "E"
        assert_tree_has_node(ast, "PLUS")


# -------------------------
# 5) Error handling & robustness
# -------------------------

class TestParserErrorsAndRobustness:
    def test_parse_error_unexpected_token(self):
        """Expr -> 'NUM', but input ID, should raise ParseError"""
        p = build_num_only_parser()
        tokens = [T("ID", "x", 1, 1), T("EOF", "", 1, 2)]

        with pytest.raises(ParseError):
            _ = p.parse(tokens)

    def test_parse_error_missing_token(self):
        """Missing RPAREN: ( NUM EOF"""
        p = build_simple_expr_ll1_parser()
        tokens = [
            T("LPAREN", "(", 1, 1),
            T("NUM", "1", 1, 2),
            T("EOF", "", 1, 3),
        ]

        with pytest.raises(ParseError):
            _ = p.parse(tokens)

    def test_parse_error_unconsumed_tokens(self):
        """
        Extra tokens remain after parsing ends (e.g., NUM NUM EOF)
        Ideal behavior: raise ParseError (or at least detect unconsumed tokens)
        """
        p = build_num_only_parser()
        tokens = [
            T("NUM", "1", 1, 1),
            T("NUM", "2", 1, 3),
            T("EOF", "", 1, 4),
        ]

        with pytest.raises(ParseError):
            _ = p.parse(tokens)

    def test_parse_twice_no_state_leak(self):
        """
        Same ParserGenerator parses twice consecutively, both results should be correct
        (Prevent leaking previous parse index/stack state to next parse)
        """
        p = build_num_only_parser()

        ast1 = p.parse([T("NUM", "1", 1, 1), T("EOF", "", 1, 2)])
        ast2 = p.parse([T("NUM", "2", 1, 1), T("EOF", "", 1, 2)])

        assert ast1.name == "Expr"
        assert ast2.name == "Expr"
