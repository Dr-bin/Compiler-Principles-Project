"""词法分析器单元测试"""

import pytest
from src.compiler_generator.lexer_generator import LexerGenerator, Token


class TestLexerGenerator:
    """词法分析器生成器的测试类"""

    def test_add_token_rule(self):
        """测试添加词法规则"""
        lexer = LexerGenerator()
        lexer.add_token_rule('ID', '[a-zA-Z_][a-zA-Z0-9_]*')
        
        rules = lexer.get_token_rules()
        assert len(rules) == 1
        assert rules[0] == ('ID', '[a-zA-Z_][a-zA-Z0-9_]*')

    def test_build_lexer(self):
        """测试构建词法分析器"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', '[0-9]+')
        lexer.add_token_rule('PLUS', '\\+')
        
        lexer.build()
        assert len(lexer.compiled_patterns) == 2

    def test_tokenize_simple(self):
        """测试简单的词法分析"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', '[0-9]+')
        lexer.add_token_rule('PLUS', '\\+')
        lexer.add_token_rule('ID', '[a-zA-Z_][a-zA-Z0-9_]*')
        lexer.build()

        tokens = lexer.tokenize('123 + abc')
        assert len(tokens) == 4  # NUM, PLUS, ID, EOF
        assert tokens[0].type == 'NUM'
        assert tokens[0].value == '123'
        assert tokens[1].type == 'PLUS'
        assert tokens[2].type == 'ID'
        assert tokens[3].type == 'EOF'

    def test_tokenize_with_whitespace(self):
        """测试词法分析自动跳过空白"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', '[0-9]+')
        lexer.build()

        tokens = lexer.tokenize('  123   456  ')
        assert len(tokens) == 3  # NUM, NUM, EOF
        assert tokens[0].value == '123'
        assert tokens[1].value == '456'

    def test_tokenize_error(self):
        """测试无法识别的字符"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', '[0-9]+')
        lexer.build()

        with pytest.raises(SyntaxError):
            lexer.tokenize('123 @invalid')

    def test_line_column_tracking(self):
        """测试行列号追踪"""
        lexer = LexerGenerator()
        lexer.add_token_rule('NUM', '[0-9]+')
        lexer.add_token_rule('ID', '[a-zA-Z]+')
        lexer.build()

        tokens = lexer.tokenize('123\nabc')
        assert tokens[0].line == 1
        assert tokens[0].column == 1
        assert tokens[1].line == 2
        assert tokens[1].column == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
