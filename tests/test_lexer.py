"""Lexer unit tests (from easy to hard, covering comprehensively)"""

import pytest
from src.compiler_generator.lexer_generator import LexerGenerator, Token


class TestLexerGenerator:
    """Test class for lexer generator"""

    # ===================== 1. Basic API & State =====================

    def test_add_and_get_token_rule(self):
        """[Basic] Test adding lexical rules & getting rules"""
        lexer = LexerGenerator()
        lexer.add_token_rule('ID', r'[a-zA-Z_][a-zA-Z0-9_]*')
        lexer.add_token_rule('NUM', r'[0-9]+')

        rules = lexer.get_token_rules()
        assert len(rules) == 2
        assert rules[0] == ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*')
        assert rules[1] == ('NUM', r'[0-9]+')

    def test_build_lexer_compiles_patterns(self):
        """[Basic] Test that building lexer compiles all rules"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.add_token_rule('PLUS', r'\+')

        lexer.build()
        # Assume internally regexes are compiled and stored in compiled_patterns
        assert hasattr(lexer, "compiled_patterns")
        assert len(lexer.compiled_patterns) == 2

    # ===================== 2. Simplest Token Sequences =====================

    def test_tokenize_single_token(self):
        """[Simple] Input contains only one token"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.build()

        tokens = lexer.tokenize('123')
        assert len(tokens) == 2  # NUM, EOF
        assert tokens[0].type == 'NUM'
        assert tokens[0].value == '123'
        assert tokens[1].type == 'EOF'

    def test_tokenize_simple_expression(self):
        """[Simple] Test lexical analysis of simple expression: NUM + ID"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.add_token_rule('PLUS', r'\+')
        lexer.add_token_rule('ID', r'[a-zA-Z_][a-zA-Z0-9_]*')
        lexer.build()

        tokens = lexer.tokenize('123 + abc')
        # Expected: NUM, PLUS, ID, EOF
        assert [t.type for t in tokens] == ['NUM', 'PLUS', 'ID', 'EOF']
        assert tokens[0].value == '123'
        assert tokens[1].value == '+'
        assert tokens[2].value == 'abc'

    # ===================== 3. Empty Input / Whitespace Only =====================

    def test_empty_input(self):
        """[Simple] Empty string returns only EOF"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.build()

        tokens = lexer.tokenize('')
        assert len(tokens) == 1
        assert tokens[0].type == 'EOF'

    def test_only_whitespace(self):
        """[Simple] Only whitespace characters should all be skipped, leaving only EOF"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.build()

        tokens = lexer.tokenize('   \t  \n  ')
        assert len(tokens) == 1
        assert tokens[0].type == 'EOF'

    def test_tokenize_with_whitespace_between_tokens(self):
        """[Simple] Test that lexer automatically skips whitespace between tokens"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.build()

        tokens = lexer.tokenize('  123   456  ')
        assert [t.type for t in tokens] == ['NUM', 'NUM', 'EOF']
        assert tokens[0].value == '123'
        assert tokens[1].value == '456'

    # ===================== 4. Multi-line & Line/Column Tracking =====================

    def test_line_column_tracking_basic(self):
        """[Moderate] Different tokens on different lines, check if line/column numbers are correct"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.add_token_rule('ID', r'[a-zA-Z]+')
        lexer.build()

        # 123\nabc
        tokens = lexer.tokenize('123\nabc')
        # NUM is at line 1, column 1
        assert tokens[0].type == 'NUM'
        assert tokens[0].line == 1
        assert tokens[0].column == 1
        # ID is at line 2, column 1
        assert tokens[1].type == 'ID'
        assert tokens[1].line == 2
        assert tokens[1].column == 1

    def test_line_column_with_spaces_and_newlines(self):
        """[Moderate] Check if column number updates correctly when mixing spaces and newlines"""
        lexer = LexerGenerator()
        lexer.add_token_rule('ID', r'[a-zA-Z]+')
        lexer.build()

        # First line has leading spaces, second line also has spaces
        #   foo\n  bar
        code = '  foo\n  bar'
        tokens = lexer.tokenize(code)

        # 'foo' is at line 1, column 3
        assert tokens[0].type == 'ID'
        assert tokens[0].value == 'foo'
        assert tokens[0].line == 1
        assert tokens[0].column == 3

        # 'bar' is at line 2, column 3
        assert tokens[1].type == 'ID'
        assert tokens[1].value == 'bar'
        assert tokens[1].line == 2
        assert tokens[1].column == 3

    # ===================== 5. Keywords vs Identifiers (Priority & Longest Match) =====================

    def test_keyword_before_identifier(self):
        """
        [Medium] Test "keyword vs identifier" priority:
        When 'if' can be matched by both ID and IF, should choose IF according to rule order.
        """
        lexer = LexerGenerator()
        # Keywords placed first have higher priority
        lexer.add_token_rule('IF', r'if')
        lexer.add_token_rule('ID', r'[a-zA-Z_][a-zA-Z0-9_]*')
        lexer.build()

        tokens = lexer.tokenize('if ifx')
        # First is keyword IF
        assert tokens[0].type == 'IF'
        assert tokens[0].value == 'if'
        # Second is identifier ID
        assert tokens[1].type == 'ID'
        assert tokens[1].value == 'ifx'
        assert tokens[2].type == 'EOF'

    # ===================== 6. Operator Conflicts (== vs =) =====================

    def test_longest_match_for_operators(self):
        """
        [Medium] Test conflicting operators: == and =
        When '==' appears in code, it should be recognized as EQ, not two ASSIGNs.
        """
        lexer = LexerGenerator()
        # Note order: longer one first to ensure '==' is matched first
        lexer.add_token_rule('EQ', r'==')
        lexer.add_token_rule('ASSIGN', r'=')
        lexer.build()

        tokens = lexer.tokenize('== =')
        assert [t.type for t in tokens] == ['EQ', 'ASSIGN', 'EOF']
        assert tokens[0].value == '=='
        assert tokens[1].value == '='

    # ===================== 7. Character Classes / Multi-digit Numbers / Mixed Expressions =====================

    def test_char_class_and_multi_digit_number(self):
        """[Medium] Test character class [0-9] and multi-digit number matching"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9][0-9]*')
        lexer.add_token_rule('PLUS', r'\+')
        lexer.add_token_rule('MUL', r'\*')
        lexer.add_token_rule('LPAREN', r'\(')
        lexer.add_token_rule('RPAREN', r'\)')
        lexer.add_token_rule('ID', r'[a-zA-Z_][a-zA-Z0-9_]*')
        lexer.build()

        code = 'sum1 + 23 * (x2 + 456)'
        tokens = lexer.tokenize(code)
        types = [t.type for t in tokens]
        values = [t.value for t in tokens]

        assert types == [
            'ID', 'PLUS', 'NUM', 'MUL',
            'LPAREN', 'ID', 'PLUS', 'NUM', 'RPAREN', 'EOF'
        ]
        assert values[0] == 'sum1'
        assert values[2] == '23'
        assert values[7] == '456'

    # ===================== 8. Error Handling =====================

    def test_tokenize_unrecognized_character_raises(self):
        """[Medium] Should raise SyntaxError when input contains unrecognized characters"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.build()

        with pytest.raises(SyntaxError):
            lexer.tokenize('123 @invalid')

    def test_tokenize_error_position_message_optional(self):
        """
        [Optional Moderate] If your implementation has error position information,
        you can check here that error messages include line/column numbers.
        If position information is not yet available, this test can be commented out
        or assertions can be relaxed.
        """
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', r'[0-9]+')
        lexer.build()

        try:
            lexer.tokenize('1 2 # 3')
        except SyntaxError as e:
            msg = str(e)
            # Not a hard requirement, just needs to contain '#' or 'illegal character' etc.
            assert '#' in msg or 'illegal' in msg or 'invalid' in msg or 'unexpected' in msg


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
