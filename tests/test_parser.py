"""语法分析器单元测试"""

from src.compiler_generator.lexer_generator import Token, LexerGenerator
from src.compiler_generator.parser_generator import ParserGenerator, ParseError, ASTNode


class TestParserGenerator:
    """语法分析器生成器的测试类"""

    def test_create_parser(self):
        """测试创建语法分析器"""
        parser = ParserGenerator()
        parser.set_start_symbol('Expr')
        parser.add_production('Expr', ['Term'])
        
        assert parser.start_symbol == 'Expr'
        assert 'Expr' in parser.grammar

    def test_add_production(self):
        """测试添加产生式"""
        parser = ParserGenerator()
        parser.add_production('Expr', ['Term', "'+'" , 'Expr'])
        parser.add_production('Expr', ['Term'])
        
        assert len(parser.grammar['Expr']) == 2

    def test_parse_simple(self):
        """测试简单的语法分析"""
        parser = ParserGenerator()
        parser.set_start_symbol('Expr')
        parser.add_production('Expr', ['NUM'])
        
        tokens = [Token('NUM', '123', 1, 1), Token('EOF', '', 1, 4)]
        ast = parser.parse(tokens)
        
        assert ast.name == 'Expr'

    def test_parse_with_alternatives(self):
        """测试有多个选择的产生式"""
        parser = ParserGenerator()
        parser.set_start_symbol('Expr')
        parser.add_production('Expr', ['NUM'])
        parser.add_production('Expr', ['ID'])
        
        tokens = [Token('ID', 'x', 1, 1), Token('EOF', '', 1, 2)]
        ast = parser.parse(tokens)
        
        assert ast.name == 'Expr'

    def test_parse_error(self):
        """测试语法错误"""
        parser = ParserGenerator()
        parser.set_start_symbol('Expr')
        parser.add_production('Expr', ['NUM'])
        
        tokens = [Token('ID', 'x', 1, 1), Token('EOF', '', 1, 2)]
        
        try:
            ast = parser.parse(tokens)
            assert False, "Should raise ParseError"
        except ParseError:
            pass  # 预期异常

    def test_ast_node_creation(self):
        """测试AST节点创建"""
        token = Token('NUM', '123', 1, 1)
        node = ASTNode(name='NUM', token=token)
        
        assert node.name == 'NUM'
        assert node.token.value == '123'
        assert len(node.children) == 0


if __name__ == '__main__':
    import sys
    # 简单的测试运行器，不依赖pytest
    test_class = TestParserGenerator()
    test_methods = [m for m in dir(test_class) if m.startswith('test_')]
    
    passed = 0
    failed = 0
    
    for method in test_methods:
        try:
            getattr(test_class, method)()
            print(f"✓ {method}")
            passed += 1
        except Exception as e:
            print(f"✗ {method}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
