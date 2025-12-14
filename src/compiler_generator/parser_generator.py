"""语法分析器生成器 (同学B负责)

该模块实现自动构建解析器的功能，使用LL(1)分析法和递归下降法
将上下文无关文法(BNF)转换为解析器。
"""

from typing import List, Dict, Tuple, Any, Optional, Set
from dataclasses import dataclass
from src.compiler_generator.lexer_generator import Token


@dataclass
class ASTNode:
    """抽象语法树(AST)节点
    
    属性:
        name: 节点对应的非终结符名称（如'Expr', 'Stmt'等）
        children: 子节点列表
        token: 如果是叶子节点，存储对应的Token对象
    """
    name: str
    children: List['ASTNode'] = None
    token: Token = None

    def __post_init__(self):
        """初始化后处理：确保children为列表"""
        if self.children is None:
            self.children = []

    def __repr__(self, indent=0):
        """返回AST树的字符串表示，用于调试"""
        prefix = "  " * indent
        result = f"{prefix}{self.name}"
        if self.token:
            result += f" ('{self.token.value}')"
        result += "\n"
        for child in self.children:
            result += child.__repr__(indent + 1)
        return result


class ParseError(Exception):
    """语法分析错误异常"""
    pass


class ParserGenerator:
    """语法分析器生成器类
    
    从BNF文法规范自动生成递归下降解析器。
    支持LL(1)文法的解析。
    """

    def __init__(self):
        """初始化语法分析器生成器
        
        属性说明:
            grammar: 存储文法规则，格式为 nonterminal: [production_list]
            start_symbol: 开始符号
            tokens: 待解析的Token列表
            pos: 当前解析位置
        """
        self.grammar: Dict[str, List[List[str]]] = {}
        self.start_symbol: str = ""
        self.tokens: List[Token] = []
        self.pos: int = 0
        self.non_terminals: Set[str] = set()
        self.terminals: Set[str] = set()
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        self.epsilon_symbol: str = 'EPSILON'
        self.analysis_sets_built = False

    def _compute_first_sets(self):
        """
        [算法核心] 迭代计算所有符号的 FIRST 集合。
        FIRST(X) 是可以从 X 推导出的所有终结符的集合。
        """
        # 1. 初始化 FIRST 集合
        self.first_sets = {}

        # 为所有非终结符初始化空集合
        for non_term in self.non_terminals:
            self.first_sets[non_term] = set()

        # 迭代直到集合不再变化
        changed = True
        while changed:
            changed = False

            # 2. 遍历所有非终结符 X
            for X in self.non_terminals:

                # 3. 遍历 X 的所有产生式：X -> Y1 Y2 ... Yk
                for production in self.grammar[X]:

                    # 4. 计算 FIRST(Y1 Y2 ... Yk) 并加入 FIRST(X)

                    # 辅助变量，用于检查是否所有前导符号都能推出 ε
                    can_all_derive_epsilon = True

                    for Y in production:
                        current_len = len(self.first_sets[X])

                        # ----------------------------------------------------
                        # Case 1: Y 是终结符
                        # ----------------------------------------------------
                        if self._is_terminal(Y):
                            token_type = Y[1:-1] if Y.startswith("'") else Y
                            self.first_sets[X].add(token_type)
                            can_all_derive_epsilon = False  # 终结符不能推出 ε
                            break  # Y是终结符，无需再看后面的符号

                        # ----------------------------------------------------
                        # Case 2: Y 是非终结符
                        # ----------------------------------------------------
                        else:
                            # 2a. 将 FIRST(Y) 中除了 ε 之外的元素加入 FIRST(X)
                            first_Y_without_epsilon = self.first_sets.get(Y, set()) - {self.epsilon_symbol}
                            self.first_sets[X].update(first_Y_without_epsilon)

                            # 2b. 检查 Y 是否能推出 ε
                            if self.epsilon_symbol not in self.first_sets.get(Y, set()):
                                can_all_derive_epsilon = False
                                break  # Y 不能推出 ε，无需再看后面的符号

                    # ----------------------------------------------------
                    # Case 3: 整个产生式 Y1 Y2 ... Yk 都能推出 ε
                    # ----------------------------------------------------
                    # 如果所有符号都能推出 ε，或者产生式本身就是 ε (空列表)
                    if can_all_derive_epsilon or not production:
                        self.first_sets[X].add(self.epsilon_symbol)

                    # 检查是否有变化
                    if current_len != len(self.first_sets[X]):
                        changed = True

        # 最终移除所有空产生式（如果有的话，取决于您的文法定义）
        for X in self.non_terminals:
            if not self.first_sets[X]:
                # 如果 FIRST(X) 为空，但 X 的产生式中有 ε，则加入 ε
                # (在迭代中已处理，这里仅做安全检查)
                pass

    def _compute_follow_sets(self):
        """
        [算法核心] 迭代计算所有非终结符的 FOLLOW 集合。
        FOLLOW(A) 是所有出现在文法中 A 之后的位置的终结符集合。
        """
        # 1. 初始化 FOLLOW 集合
        self.follow_sets = {}
        for non_term in self.non_terminals:
            self.follow_sets[non_term] = set()

        # 2. 初始条件：将 EOF 符号 $ 加入开始符号的 FOLLOW 集合中
        if self.start_symbol:
            self.follow_sets[self.start_symbol].add('EOF')

        # 迭代直到集合不再变化
        changed = True
        while changed:
            changed = False

            # 3. 遍历所有产生式：A -> α B β
            for A in self.non_terminals:
                for production in self.grammar[A]:

                    # 遍历产生式中的每一个符号 B
                    for i, B in enumerate(production):

                        # 只处理非终结符 B
                        if B not in self.non_terminals:
                            continue

                        # ----------------------------------------------------
                        # Case 1: B 后面有符号 (β = B后面的所有符号)
                        # ----------------------------------------------------
                        # β 是 B 后面的符号序列
                        beta = production[i + 1:]

                        if beta:
                            # 1a. 将 FIRST(β) 中除了 ε 之外的元素加入 FOLLOW(B)
                            first_beta = self._get_first_set_for_sequence(beta)
                            current_len = len(self.follow_sets[B])

                            self.follow_sets[B].update(first_beta - {self.epsilon_symbol})

                            if current_len != len(self.follow_sets[B]):
                                changed = True

                            # 1b. 如果 β 可以推导出 ε，则将 FOLLOW(A) 加入 FOLLOW(B)
                            if self._sequence_can_derive_epsilon(beta):
                                current_len = len(self.follow_sets[B])
                                self.follow_sets[B].update(self.follow_sets.get(A, set()))

                                if current_len != len(self.follow_sets[B]):
                                    changed = True

                        # ----------------------------------------------------
                        # Case 2: B 是产生式中的最后一个符号 (β 为空)
                        # ----------------------------------------------------
                        # 或者 B 后面的所有符号 β 都能推导出 ε
                        elif i == len(production) - 1:
                            # 将 FOLLOW(A) 加入 FOLLOW(B)
                            current_len = len(self.follow_sets[B])
                            self.follow_sets[B].update(self.follow_sets.get(A, set()))

                            if current_len != len(self.follow_sets[B]):
                                changed = True

        #

    # ----------------------------------------------------------------------
    # 辅助方法：计算符号序列的 FIRST 集合和 ε-推导能力
    # ----------------------------------------------------------------------
    def _get_first_set_for_sequence(self, sequence: List[str]) -> Set[str]:
        """计算符号序列 (Y1 Y2 ...) 的 FIRST 集合"""
        first_set = set()
        for Y in sequence:
            if self._is_terminal(Y):
                # 终结符
                token_type = Y[1:-1] if Y.startswith("'") else Y
                first_set.add(token_type)
                return first_set
            else:
                # 非终结符
                first_set.update(self.first_sets.get(Y, set()) - {self.epsilon_symbol})
                if self.epsilon_symbol not in self.first_sets.get(Y, set()):
                    return first_set  # Y不能推导出ε，无需再看后面的符号

        # 如果序列为空或者所有符号都能推出 ε
        first_set.add(self.epsilon_symbol)
        return first_set

    def _sequence_can_derive_epsilon(self, sequence: List[str]) -> bool:
        """检查符号序列 (Y1 Y2 ...) 是否可以推导出空串"""
        if not sequence:
            return True  # 空序列可以推导出 ε

        for Y in sequence:
            if self._is_terminal(Y):
                return False  # 终结符不能推导出 ε
            if self.epsilon_symbol not in self.first_sets.get(Y, set()):
                return False  # 非终结符 Y 不能推导出 ε

        return True

    def _eliminate_immediate_left_recursion(self, A: str):
        """消除非终结符 A 的即时左递归 (A -> Aα | β)"""

        # 1. 划分产生式：左递归部分 (alphas) 和 非左递归部分 (betas)
        alphas = []
        betas = []

        # 临时存储 A 的当前所有产生式
        productions = self.grammar[A]

        for production in productions:
            if production and production[0] == A:
                # 发现左递归: A -> A alpha
                alphas.append(production[1:])  # alpha 是 A 后面的符号序列
            else:
                # 非左递归: A -> beta
                betas.append(production)

        # 如果不存在左递归，则直接返回
        if not alphas:
            return

        # 2. 生成新的非终结符 A'
        A_tail = A + '_TAIL'

        # 3. 构造新的文法规则

        # a. 构造 A' 的产生式: A' -> alpha A' | epsilon
        new_A_tail_productions = []
        for alpha in alphas:
            # A' -> alpha A'
            new_A_tail_productions.append(alpha + [A_tail])

        # A' -> epsilon (空列表)
        new_A_tail_productions.append([])  # 使用空列表 [] 表示 epsilon

        self.grammar[A_tail] = new_A_tail_productions
        self.non_terminals.add(A_tail)

        # b. 构造 A 的新产生式: A -> beta A'
        new_A_productions = []
        for beta in betas:
            # A -> beta A'
            new_A_productions.append(beta + [A_tail])

        # 覆盖 A 的旧产生式
        self.grammar[A] = new_A_productions

        # 警告：如果 betas 为空，这会导致 A 没有任何产生式，这通常意味着文法错误，
        # 属于死循环（A -> Aα1），但在这里我们仍然按规则转换。
        if not betas:
            print(f"Warning: Non-terminal {A} only had left-recursive productions. It is now useless.")

    def _eliminate_left_recursion(self):
        """消除所有非终结符的即时左递归"""

        # 注意：这里只处理即时左递归。如果需要处理间接左递归，
        # 需要使用更复杂的算法，例如将非终结符排序并迭代替换。

        # 拷贝非终结符列表，因为在消除过程中可能会添加新的 _TAIL 符号
        non_terminals_to_process = list(self.non_terminals)

        for A in non_terminals_to_process:
            # 只对原始非终结符进行消除，不处理新生成的 _TAIL 符号
            if A in self.grammar:
                self._eliminate_immediate_left_recursion(A)

        # 消除后，重新识别所有符号，因为增加了新的 _TAIL 非终结符
        self._identify_symbols()

    def build_analysis_sets(self):
        """执行文法分析，计算 FIRST 和 FOLLOW 集合 (已包含左递归消除)"""
        # 1. 识别初始符号集
        self._identify_symbols()

        # 2. 消除即时左递归 (此方法内部会重新调用 _identify_symbols 来识别新增的 _TAIL 符号)
        self._eliminate_left_recursion()

        # 3. 计算 FIRST 集合 (这是所有分析的基础)
        self._compute_first_sets()

        # 4. 计算 FOLLOW 集合 (依赖于 FIRST 集合)
        self._compute_follow_sets()

        self.analysis_sets_built = True

    def _identify_symbols(self):
        """识别所有的非终结符和终结符"""
        self.non_terminals = set(self.grammar.keys())
        self.terminals = set()

        # 遍历所有产生式，识别出所有的符号
        all_symbols = set()
        for non_term in self.grammar:
            for production in self.grammar[non_term]:
                for symbol in production:
                    all_symbols.add(symbol)

        # 终结符是所有符号中，不属于非终结符的符号
        # 并且根据您之前的设计，我们假设终结符是以引号包裹的字符串（如"'ID'"）
        for symbol in all_symbols:
            # 终结符识别逻辑：检查是否是带引号的字符串
            if symbol.startswith("'") and symbol.endswith("'"):
                self.terminals.add(symbol[1:-1])  # 存储不带引号的 Token Type
            elif symbol not in self.non_terminals:
                # 理论上不应该出现不带引号且不是非终结符的符号
                pass

        # 确保 EOF 是一个终结符
        self.terminals.add('EOF')

        # --------------------------------------------------------
        # 注意：为了方便计算，我们使用 token type 作为 FIRST/FOLLOW 集合的元素
        # 在计算时，文法规则中的 "'ID'" 会被视为 'ID'
        # --------------------------------------------------------

    # 辅助方法：判断一个符号是否是终结符
    def _is_terminal(self, symbol: str) -> bool:
        """检查一个文法符号是否是终结符"""
        # 检查是否是带引号的符号
        if symbol.startswith("'") and symbol.endswith("'"):
            return True
        # 检查是否是已识别的 Token Type (如 'EOF')
        return symbol in self.terminals

    # 辅助方法：判断一个非终结符是否可以推出空串
    def _can_derive_epsilon(self, non_terminal: str) -> bool:
        """检查一个非终结符是否可以推导出空串"""
        # 这需要在 FIRST/FOLLOW 计算过程中迭代确定，所以单独实现
        return self.epsilon_symbol in self.first_sets.get(non_terminal, set())

    def add_production(self, nonterminal: str, production: List[str]) -> None:
        """添加一个产生式（文法规则）
        
        参数:
            nonterminal: 产生式左侧的非终结符
            production: 产生式右侧的符号列表（可包含终结符和非终结符）
            
        返回:
            None
            
        说明:
            - 终结符使用引号标记（如 'if', '+'）
            - 非终结符直接使用名称（如 'Expr', 'Stmt'）
            - 同一非终结符可以有多条产生式（选择规则）
        """
        if nonterminal not in self.grammar:
            self.grammar[nonterminal] = []
        self.grammar[nonterminal].append(production)

    def set_start_symbol(self, symbol: str) -> None:
        """设置开始符号
        
        参数:
            symbol: 开始符号名称（通常为'Program'或'S'）
            
        返回:
            None
        """
        self.start_symbol = symbol

    def current_token(self) -> Token:
        """获取当前指向的Token
        
        返回:
            当前Token对象，如果已到达末尾返回EOF token
            
        说明:
            用于查看下一个要匹配的Token，不消耗Token。
        """
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # 返回EOF token

    def match(self, expected_type: str) -> ASTNode:
        """
        匹配并消耗当前 Token。

        参数:
            expected_type: 期望的 Token 类型 (如 'ID', 'NUM', 'PLUS')

        返回:
            匹配到的 Token 对应的 ASTNode 叶子节点。

        抛出:
            ParseError: 如果类型不匹配。
        """
        current = self.current_token()

        # 1. 检查类型是否匹配
        if current.type == expected_type:

            # 2. 匹配成功：消耗 Token，将位置指针前移
            self.pos += 1

            # 3. 创建 AST 叶子节点并返回
            # AST 叶子节点的 name 通常就是 Token 的 type，token 属性存储了原始 Token 对象
            return ASTNode(name=current.type, token=current)

        else:
            # 4. 匹配失败：抛出精确的语法错误 (使用 Token 的行号和列号)
            raise ParseError(
                f"Syntax Error at Line {current.line}, Column {current.column}: "
                f"Expected token type '{expected_type}', but found '{current.type}' "
                f"with value '{current.value}'."
            )

    def parse_symbol(self, symbol: str) -> ASTNode:
        """
        [LL(1) 风格] 递归解析一个符号（可以是终结符或非终结符）。

        参数:
            symbol: 要解析的符号名称 (如 'Expr' 或 "'NUM'")

        返回:
            对应的 AST 节点

        异常:
            ParseError: 当无法匹配时抛出

        说明:
            - 终结符 (带引号如 "'NUM'")：调用 self.match()
            - 非终结符 (如 'Expr')：使用当前 Token (Lookahead) 选择产生式。
            - 纯LL(1)设计，不使用回溯。
        """
        # ----------------------------------------------------
        # 1. 处理终结符 (Terminal)
        # ----------------------------------------------------
        # 文法规则中，终结符通常用引号包裹 (如 "'NUM'")
        if symbol.startswith("'") and symbol.endswith("'"):
            # 提取引号内的 token 类型
            token_type = symbol[1:-1]

            # 终结符直接交由 match 方法处理：检查、消耗、构建 AST 叶子节点
            return self.match(token_type)

        # ----------------------------------------------------
        # 2. 处理非终结符 (Non-Terminal)
        # ----------------------------------------------------
        if symbol not in self.grammar:
            raise ParseError(f"Unknown symbol reference in grammar: {symbol}")

        # 获取当前前瞻 Token 类型
        current_token_type = self.current_token().type
        productions = self.grammar[symbol]

        found_production = None

        # *** LL(1) 核心：基于 FIRST 和 FOLLOW 集合进行严格选择 ***
        for production in productions:
            # 1. 计算该产生式 (即符号序列) 的 FIRST 集合
            # 依赖于您在上一轮实现的辅助方法：
            production_first_set = self._get_first_set_for_sequence(production)

            # 2. Case A: 如果当前 Token 在 FIRST(Production) 中
            if current_token_type in production_first_set:
                # 找到唯一匹配的产生式（LL(1)文法保证了这一点）
                found_production = production
                break

            # 3. Case B: 如果该产生式可以推导出 ε (即 ε 存在于 FIRST 集合中)
            if self.epsilon_symbol in production_first_set:

                # 检查当前 Token 是否在 FOLLOW(Symbol) 中
                if current_token_type in self.follow_sets.get(symbol, set()):
                    # 选择 ε 产生式（因为这是唯一一个包含 ε 的选择）
                    found_production = production
                    break

        # ----------------------------------------------------
        # 3. 执行选定的产生式
        # ----------------------------------------------------
        if found_production is not None:
            children_nodes = []

            # 检查是否是 ε 产生式：如果是，则不消耗任何 Token
            if not found_production and self.epsilon_symbol in production_first_set:
                return ASTNode(name=symbol, children=[], token=None)

            # 递归解析产生式中的每一个符号
            for sym in found_production:
                child_node = self.parse_symbol(sym)
                children_nodes.append(child_node)

            # 成功解析，构建并返回 ASTNode
            return ASTNode(name=symbol, children=children_nodes)

        # ----------------------------------------------------
        # 4. 错误处理
        # ----------------------------------------------------
        else:
            # 遍历完所有产生式，没有一个能匹配当前的前瞻 Token
            # 提示用户期望的 Token 类型
            expected_tokens = self.first_sets.get(symbol, set()) - {self.epsilon_symbol}
            if self.epsilon_symbol in self.first_sets.get(symbol, set()):
                expected_tokens.update(self.follow_sets.get(symbol, set()))

            raise ParseError(
                f"Syntax Error at Line {self.current_token().line}, Column {self.current_token().column}: "
                f"Non-terminal '{symbol}' encountered unexpected token '{self.current_token().type}'. "
                f"Expected one of: {', '.join(sorted(expected_tokens))}"
            )

    def parse(self, tokens: List[Token]) -> ASTNode:
        """从Token列表生成抽象语法树
        
        参数:
            tokens: 词法分析器输出的Token列表
            
        返回:
            根节点AST对象
            
        异常:
            ParseError: 当语法分析失败时抛出
            RuntimeError: 当start_symbol未设置时抛出
            
        说明:
            - 调用前必须通过set_start_symbol()设置开始符号
            - tokens应该包含EOF token作为结尾
        """
        if not self.start_symbol:
            raise RuntimeError("Start symbol not set. Call set_start_symbol() first.")
        if not self.analysis_sets_built:
            self.build_analysis_sets()

        self.tokens = tokens
        self.pos = 0

        # 从开始符号开始解析
        ast = self.parse_symbol(self.start_symbol)

        # 检查是否已完全解析所有tokens
        if self.current_token().type != 'EOF':
            raise ParseError(
                f"Unexpected trailing tokens at position {self.pos}: "
                f"{self.current_token()}\nTokens remaining: "
                f"{[str(t) for t in self.tokens[self.pos:]]}"
            )

        return ast

    def get_grammar(self) -> Dict[str, List[List[str]]]:
        """获取当前的文法规则
        
        返回:
            文法规则字典
            
        说明:
            用于显示或调试当前定义的文法。
        """
        return self.grammar.copy()


def create_parser_from_spec(grammar: Dict[str, List[List[str]]], 
                            start: str) -> ParserGenerator:
    """便捷函数：从文法规范创建语法分析器
    
    参数:
        grammar: 文法规则字典
        start: 开始符号
        
    返回:
        已配置好的 ParserGenerator 对象
        
    说明:
        快速构造语法分析器的工厂函数。
    """
    parser = ParserGenerator()
    parser.set_start_symbol(start)
    
    for nonterminal, productions in grammar.items():
        for production in productions:
            parser.add_production(nonterminal, production)
    
    return parser
