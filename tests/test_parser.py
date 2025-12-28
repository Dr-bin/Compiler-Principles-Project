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
        parser.add_production('Expr', ["'NUM'"])
        
        tokens = [Token('NUM', '123', 1, 1), Token('EOF', '', 1, 4)]
        ast = parser.parse(tokens)
        
        assert ast.name == 'Expr'

    def test_parse_with_alternatives(self):
        """测试有多个选择的产生式"""
        parser = ParserGenerator()
        parser.set_start_symbol('Expr')
        parser.add_production('Expr', ["'NUM'"])
        parser.add_production('Expr', ["'ID'"])
        
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

    def test_left_recursion_elimination(self):
        """测试即时左递归消除功能"""
        parser = ParserGenerator()
        parser.set_start_symbol('E')

        # E -> E '+' T | T （即时左递归文法）
        parser.add_production('E', ['E', "'+'", 'T'])
        parser.add_production('E', ['T'])

        # 强制构建分析集，触发左递归消除
        parser.build_analysis_sets()

        # 检查文法是否被转换为:
        # E -> T E_TAIL
        # E_TAIL -> '+' T E_TAIL | EPSILON

        # 1. 检查 E 的新产生式
        assert 'E' in parser.grammar
        assert len(parser.grammar['E']) == 1
        assert parser.grammar['E'][0] == ['T', 'E_TAIL']  # E -> T E_TAIL

        # 2. 检查 E_TAIL 的产生式
        assert 'E_TAIL' in parser.grammar
        assert len(parser.grammar['E_TAIL']) == 2
        # E_TAIL -> '+' T E_TAIL
        assert ["'+'", 'T', 'E_TAIL'] in parser.grammar['E_TAIL']
        # E_TAIL -> EPSILON (空列表)
        assert [] in parser.grammar['E_TAIL']

    def test_parse_with_epsilon_production(self):
        """测试ε（空串）产生式和FOLLOW集合选择"""

        # 转换为 LL(1) 的文法示例 (非左递归):
        # S -> A 'EOF'
        # A -> 'x' B
        # B -> 'y' | EPSILON (空串)
        parser = ParserGenerator()
        parser.set_start_symbol('S')
        parser.add_production('S', ['A', "'EOF'"])
        parser.add_production('A', ["'x'", 'B'])
        parser.add_production('B', ["'y'"])
        parser.add_production('B', [])  # B -> ε

        tokens = [
            Token('x', 'x', 1, 1),
            Token('EOF', '', 1, 2)  # 当解析到 'EOF' 时，B应该选择 ε
        ]

        ast = parser.parse(tokens)

        # 1. 检查 AST 结构是否正确 (S -> A 'EOF')
        assert ast.name == 'S'
        assert len(ast.children) == 2
        assert ast.children[0].name == 'A'

        # 2. 检查 ε 产生式是否被正确选择 (A -> 'x' B)
        a_node = ast.children[0]
        assert len(a_node.children) == 2

        # 3. B 节点应该被解析为 ε (空串，子节点列表为空)
        b_node = a_node.children[1]
        assert b_node.name == 'B'
        assert len(b_node.children) == 0  # ε 产生式不消耗 token，AST 子节点为空


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
