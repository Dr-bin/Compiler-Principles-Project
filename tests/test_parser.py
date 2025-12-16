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

        # 1. 检查 AST 结构 (S -> A 'EOF')
        # S 应该有两个子节点：A 和 EOF
        assert ast.name == 'S'
        assert len(
            ast.children) == 2, f"S 节点子节点数量错误。期望 2 (A, EOF), 实际 {len(ast.children)}: {[c.name for c in ast.children]}"

        # 2. 检查 A 节点 (S 的第一个子节点)
        a_node = ast.children[0]
        assert a_node.name == 'A'
        assert len(a_node.children) == 2  # A -> 'x' B

        # 3. 检查 'x' 节点 (A 的第一个子节点)
        x_node = a_node.children[0]
        assert x_node.name == 'x'

        # 4. 检查 B 节点 (A 的第二个子节点)
        b_node = a_node.children[1]
        assert b_node.name == 'B'
        # B -> ε (空串)，AST 中 B 节点存在，但没有子节点
        assert len(b_node.children) == 0

        # 5. 检查 EOF 节点 (S 的第二个子节点)
        eof_node = ast.children[1]
        assert eof_node.name == 'EOF'

    def test_left_factoring_simplest(self):
        """测试左因子提取功能 (A -> alpha beta1 | alpha beta2)"""
        parser = ParserGenerator()
        parser.set_start_symbol('Stmt')

        # 使用简化的符号来表示结构，以便检查转换结果
        alpha = ["'if'", "'E'", "'then'", "'S'"]
        beta2 = ["'else'", "'S'"]  # beta1 是空串 []

        parser.add_production('Stmt', alpha)
        parser.add_production('Stmt', alpha + beta2)

        # 强制构建分析集，触发左因子提取
        parser.build_analysis_sets()

        # --- 开始动态查找 ---

        # 1. 检查原始 Stmt 产生式数量是否正确 (应只有 1 条)
        assert 'Stmt' in parser.grammar
        assert len(parser.grammar['Stmt']) == 1, f"Stmt 产生式数量错误，期望 1 条，实际 {len(parser.grammar['Stmt'])}"

        # 2. 从唯一的产生式中提取新非终结符名称
        stmt_productions = parser.grammar['Stmt'][0]

        # 新非终结符是产生式中的最后一个符号
        new_non_terminal = stmt_productions[-1]

        # 3. 增加断言以确认动态获取的名称符合预期模式 (可选但推荐)
        assert new_non_terminal.startswith('Stmt_LF_TAIL_'), \
            f"动态获取的非终结符名称不符合预期模式 (Stmt_LF_TAIL_): {new_non_terminal}"

        # --- 结束动态查找 ---

        # 1. 检查新的非终结符是否存在
        assert new_non_terminal in parser.grammar, f"左因子提取失败：未创建非终结符 {new_non_terminal}"

        # 2. 检查原始 Stmt 的新产生式
        # Stmt 应该只剩下一条产生式: Stmt -> alpha NewTail
        expected_stmt_production = alpha + [new_non_terminal]
        assert parser.grammar['Stmt'][0] == expected_stmt_production, \
            f"Stmt 转换错误: 期望 {expected_stmt_production}, 实际 {parser.grammar['Stmt'][0]}"

        # 3. 检查新的 NewTail (即 new_non_terminal) 的产生式数量
        assert len(parser.grammar[new_non_terminal]) == 2

        # 4. 检查 NewTail 的第一个产生式 (beta1，即空串)
        assert [] in parser.grammar[new_non_terminal], f"新非终结符 {new_non_terminal} 缺少 ε (空串) 产生式"

        # 5. 检查 NewTail 的第二个产生式 (beta2，即 'else' 'S')
        assert beta2 in parser.grammar[new_non_terminal], \
            f"新非终结符 {new_non_terminal} 缺少 'else' 'S' 产生式: 期望 {beta2}, 实际 {parser.grammar[new_non_terminal]}"
        # 6. 验证转换后的文法可以解析

        # 测试 'if E then S' (选择 Stmt_TAIL -> epsilon)
        tokens_short = [
            Token('if', 'if', 1, 1),
            Token('E', 'cond', 1, 4),
            Token('then', 'then', 1, 9),
            Token('S', 'body', 1, 14),
            Token('EOF', '', 1, 18)
        ]
        ast_short = parser.parse(tokens_short)
        assert ast_short.name == 'Stmt'

        # 测试 'if E then S else S' (选择 Stmt_TAIL -> 'else' 'S')
        tokens_long = [
            Token('if', 'if', 1, 1),
            Token('E', 'cond', 1, 4),
            Token('then', 'then', 1, 9),
            Token('S', 'body1', 1, 14),
            Token('else', 'else', 1, 20),
            Token('S', 'body2', 1, 25),
            Token('EOF', '', 1, 29)
        ]
        ast_long = parser.parse(tokens_long)
        assert ast_long.name == 'Stmt'

    def test_indirect_left_recursion_elimination(self):
        """测试间接左递归消除功能 (A -> B 'c', B -> A 'd' | 'e')"""
        parser = ParserGenerator()
        parser.set_start_symbol('A')

        # 原始文法 (间接左递归)
        parser.add_production('A', ['B', "'c'"])
        parser.add_production('B', ['A', "'d'"])
        parser.add_production('B', ["'e'"])

        # 强制构建分析集，触发左递归消除和 LL(1) 冲突检查
        try:
            parser.build_analysis_sets()
            # 如果没有抛出异常，则说明冲突未被检测，这本身是错误的
            assert False, "build_analysis_sets 应该检测到 B_TAIL 的 LL(1) 冲突并抛出 ParseError"
        except ParseError as e:
            # 预期：冲突被检测到，且冲突发生在新生成的 B_TAIL 符号上
            error_message = str(e)
            assert "LL(1) Conflict detected for non-terminal 'B_TAIL'" in error_message
            assert "'c'" in error_message, "冲突标记应包含 'c'"

    def test_ll1_conflict_detection(self):
        """测试LL(1)冲突的自动解决功能（FIRST/FIRST冲突通过左因子提取解决）"""
        parser = ParserGenerator()
        parser.set_start_symbol('Expr')

        # 原始文法 (具有左公共因子): Expr -> 'ID' '=' 'ID' | 'ID'
        parser.add_production('Expr', ["'ID'", "'='", "'ID'"])
        parser.add_production('Expr', ["'ID'"])

        # 强制构建分析集，现在期望它不抛出异常，并自动修复文法
        try:
            parser.build_analysis_sets()
        except ParseError as e:
            # 如果仍有错误，说明左因子提取失败了
            assert False, f"左因子提取失败或引入了新的冲突: {e}"

        # 检查文法是否被转换 (类似于 test_left_factoring_simplest 的检查)

        # 1. 动态获取新非终结符名称
        assert len(parser.grammar['Expr']) == 1
        new_non_terminal = parser.grammar['Expr'][0][-1]

        # 2. 检查新非终结符的产生式
        assert new_non_terminal.startswith('Expr_LF_TAIL_')
        assert len(parser.grammar[new_non_terminal]) == 2

        # beta1: '=' 'ID'
        assert ["'='", "'ID'"] in parser.grammar[new_non_terminal]
        # beta2: epsilon (空列表)
        assert [] in parser.grammar[new_non_terminal]

        # 现在，我们应该能成功解析这两种输入：
        tokens_assign = [Token('ID', 'x', 1, 1), Token('=', '=', 1, 2), Token('ID', 'y', 1, 3), Token('EOF', '', 1, 4)]
        tokens_id = [Token('ID', 'z', 1, 1), Token('EOF', '', 1, 2)]

        assert parser.parse(tokens_assign).name == 'Expr'
        assert parser.parse(tokens_id).name == 'Expr'

    def test_ll1_conflict_first_follow(self):
        """测试LL(1)冲突检测功能（FIRST/FOLLOW冲突）"""
        parser = ParserGenerator()
        parser.set_start_symbol('A')

        # A -> 'a' | epsilon (空串)
        # FOLLOW(A) 中包含 'a' 时，会发生冲突
        parser.add_production('A', ["'a'"])
        parser.add_production('A', [])  # A -> epsilon

        # S -> A 'a' (让 FOLLOW(A) 包含 'a')
        parser.add_production('S', ['A', "'a'"])
        parser.set_start_symbol('S')

        # 强制构建分析集，期望抛出异常
        try:
            parser.build_analysis_sets()
            assert False, "build_analysis_sets 应该因为 FIRST/FOLLOW 冲突而抛出 ParseError"
        except ParseError as e:
            # 检查错误信息是否提及冲突 token 'a'
            error_message = str(e)
            assert "LL(1) Conflict detected" in error_message
            assert "'a'" in error_message


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
