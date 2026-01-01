"""语法分析器生成器 (同学B负责)

该模块实现自动构建解析器的功能，使用LL(1)分析法和递归下降法
将上下文无关文法(BNF)转换为解析器。

[SDT实现] 使用语法制导翻译(Syntax-Directed Translation)在解析过程中同时生成中间代码
[智能提示] 使用编辑距离算法提供变量拼写错误的修复建议
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from src.compiler_generator.lexer_generator import Token
from src.utils.smart_suggest import suggest_variable_fix


@dataclass
class ASTNode:
    """抽象语法树(AST)节点
    
    [SDT扩展] 节点现在携带语义信息：
    - synthesized_value: 综合属性，用于代码生成（变量名、临时变量等）
    """
    name: str
    children: List['ASTNode'] = None
    token: Token = None
    synthesized_value: str = None  # SDT: 综合属性，用于存储代码生成结果

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def __repr__(self, indent=0):
        prefix = "  " * indent
        result = f"{prefix}{self.name}"
        if self.token:
            result += f" ('{self.token.value}')"
        if self.synthesized_value:
            result += f" [val={self.synthesized_value}]"
        result += "\n"
        for child in self.children:
            result += child.__repr__(indent + 1)
        return result


class ParseError(Exception):
    """语法分析错误异常"""
    pass


class ParserGenerator:
    """语法分析器生成器类
    
    [SDT增强] 在语法分析过程中同时进行代码生成：
    - 每个产生式识别后立即执行翻译动作
    - 生成的中间代码保存在code_buffer中
    - 实现真正的一遍扫描编译
    """

    def __init__(self, enable_sdt: bool = True):
        """初始化解析器
        
        参数:
            enable_sdt: 是否启用语法制导翻译（默认启用）
        """
        self.grammar: Dict[str, List[List[str]]] = {}
        self.start_symbol: str = ""
        self.tokens: List[Token] = []
        self.pos: int = 0
        self.non_terminals: Set[str] = set()
        self.terminals: Set[str] = set()
        self.first_sets: Dict[str, Set[str]] = {}
        self.follow_sets: Dict[str, Set[str]] = {}
        self.select_sets: Dict[str, List[Set[str]]] = {}  # 存储每个非终结符的产生式SELECT集合
        self.epsilon_symbol: str = 'EPSILON'
        self.analysis_sets_built = False
        
        # [SDT] 语法制导翻译相关属性
        self.enable_sdt = enable_sdt
        self.code_buffer: List[str] = []  # 存储生成的中间代码
        self.temp_counter: int = 0  # 临时变量计数器
        self.label_counter: int = 0  # 标签计数器
        self.symbol_table: Dict[str, Dict] = {}  # 符号表
        
        # [智能提示] 变量检查相关属性
        self.enable_variable_check = True  # 是否启用变量检查
        self.semantic_errors: List[str] = []  # 收集语义错误
        self.requires_explicit_declaration = False  # 是否需要显式声明（PL/0需要，Simple不需要）

    def _compute_first_sets(self):
        """[算法核心] 迭代计算所有符号的 FIRST 集合。"""
        self.first_sets = {}
        for non_term in self.non_terminals:
            self.first_sets[non_term] = set()

        changed = True
        while changed:
            changed = False
            for X in self.non_terminals:
                for production in self.grammar[X]:
                    # 修复：将 current_len 的获取移到处理每个产生式之前
                    # 这样即使产生式为空(epsilon)，current_len 也能被正确初始化
                    current_len = len(self.first_sets[X])

                    can_all_derive_epsilon = True
                    for Y in production:
                        if self._is_terminal(Y):
                            token_type = Y[1:-1] if Y.startswith("'") else Y
                            self.first_sets[X].add(token_type)
                            can_all_derive_epsilon = False
                            break
                        else:
                            first_Y_without_epsilon = self.first_sets.get(Y, set()) - {self.epsilon_symbol}
                            self.first_sets[X].update(first_Y_without_epsilon)
                            if self.epsilon_symbol not in self.first_sets.get(Y, set()):
                                can_all_derive_epsilon = False
                                break

                    if can_all_derive_epsilon or not production:
                        self.first_sets[X].add(self.epsilon_symbol)

                    if current_len != len(self.first_sets[X]):
                        changed = True

    def _compute_follow_sets(self):
        """[算法核心] 迭代计算所有非终结符的 FOLLOW 集合。"""
        self.follow_sets = {}
        for non_term in self.non_terminals:
            self.follow_sets[non_term] = set()

        if self.start_symbol:
            self.follow_sets[self.start_symbol].add('EOF')

        changed = True
        while changed:
            changed = False
            for A in self.non_terminals:
                for production in self.grammar[A]:
                    for i, B in enumerate(production):
                        if B not in self.non_terminals:
                            continue

                        beta = production[i + 1:]
                        current_len = len(self.follow_sets[B])  # 记录初始长度

                        if beta:
                            first_beta = self._get_first_set_for_sequence(beta)
                            self.follow_sets[B].update(first_beta - {self.epsilon_symbol})
                            if self._sequence_can_derive_epsilon(beta):
                                self.follow_sets[B].update(self.follow_sets.get(A, set()))
                        else:
                            self.follow_sets[B].update(self.follow_sets.get(A, set()))

                        # 检查是否有变化
                        if current_len != len(self.follow_sets[B]):
                            changed = True

    def _get_first_set_for_sequence(self, sequence: List[str]) -> Set[str]:
        first_set = set()
        for Y in sequence:
            if self._is_terminal(Y):
                token_type = Y[1:-1] if Y.startswith("'") else Y
                first_set.add(token_type)
                return first_set
            else:
                first_set.update(self.first_sets.get(Y, set()) - {self.epsilon_symbol})
                if self.epsilon_symbol not in self.first_sets.get(Y, set()):
                    return first_set
        first_set.add(self.epsilon_symbol)
        return first_set

    def _sequence_can_derive_epsilon(self, sequence: List[str]) -> bool:
        if not sequence: return True
        for Y in sequence:
            if self._is_terminal(Y): return False
            if self.epsilon_symbol not in self.first_sets.get(Y, set()): return False
        return True

    def _eliminate_immediate_left_recursion(self, A: str):
        alphas, betas = [], []
        productions = self.grammar[A]
        for production in productions:
            if production and production[0] == A:
                alphas.append(production[1:])
            else:
                betas.append(production)

        if not alphas: return

        A_tail = A + '_TAIL'
        new_A_tail_productions = []
        for alpha in alphas:
            new_A_tail_productions.append(alpha + [A_tail])
        new_A_tail_productions.append([])

        self.grammar[A_tail] = new_A_tail_productions
        self.non_terminals.add(A_tail)

        new_A_productions = []
        for beta in betas:
            new_A_productions.append(beta + [A_tail])
        self.grammar[A] = new_A_productions

    def _check_potential_indirect_recursion(self, start_sym: str, target_sym: str, visited: Set[str] = None) -> bool:
        """
        [新增辅助方法] 检查是否存在从 start_sym 开始，经过推导首字符能到达 target_sym 的路径。
        用于判断是否真的需要进行非左递归的代换。
        """
        if visited is None: visited = set()
        if start_sym == target_sym: return True
        if start_sym in visited: return False

        visited.add(start_sym)

        # 我们只关心产生式的第一个符号，因为只有第一个符号会导致左递归
        for prod in self.grammar.get(start_sym, []):
            if not prod: continue
            first_symbol = prod[0]
            # 如果第一个符号是非终结符，则继续递归检查
            if first_symbol in self.non_terminals:
                if self._check_potential_indirect_recursion(first_symbol, target_sym, visited):
                    return True
        return False

    def _eliminate_left_recursion(self):
        """
        通用算法消除所有左递归。
        [优化] 增加了循环检测，只有在存在潜在左递归环路时才进行代换，
        避免不必要地将无害的非终结符代入，保留文法原有结构。
        """
        non_terminals_list = sorted(list(self.non_terminals))

        for i in range(len(non_terminals_list)):
            Ai = non_terminals_list[i]
            for j in range(i):
                Aj = non_terminals_list[j]

                # [优化关键点]
                # 只有当 Aj 能推导出以 Ai 开头的串时（即存在 Ai -> Aj ... -> Ai ... 的风险），
                # 我们才执行代换。否则保留 S -> A 'a' 这种结构。
                if not self._check_potential_indirect_recursion(Aj, Ai):
                    continue

                new_productions_for_Ai = []
                if Ai in self.grammar:
                    current_productions = self.grammar[Ai]
                    self.grammar[Ai] = []
                    for production in current_productions:
                        if production and production[0] == Aj:
                            gamma = production[1:]
                            for beta_prod in self.grammar.get(Aj, []):
                                new_productions_for_Ai.append(beta_prod + gamma)
                        else:
                            self.grammar[Ai].append(production)
                    self.grammar[Ai].extend(new_productions_for_Ai)

            if Ai in self.grammar:
                self._eliminate_immediate_left_recursion(Ai)

        self._identify_symbols()

    def _perform_left_factoring(self):
        """对文法进行左因子提取"""
        new_grammar = self.grammar.copy()
        counter = 0
        # 迭代处理，直到所有非终结符都没有公共左因子
        non_terminals_to_check = set(self.grammar.keys())

        # 设置一个安全计数器，防止无限循环
        max_iterations = len(self.grammar) * 2

        while non_terminals_to_check and max_iterations > 0:
            A = non_terminals_to_check.pop()
            max_iterations -= 1

            productions = new_grammar.get(A, [])
            if not productions: continue

            # 1. 对产生式列表进行排序，便于寻找公共前缀
            # 排序规则：按符号类型和长度，以确保稳定性
            sorted_productions = sorted(productions)

            groups = []  # 存储分组后的产生式：[[prod1, prod2], [prod3], ...]
            i = 0
            while i < len(sorted_productions):
                current_prod = sorted_productions[i]
                current_group = [current_prod]

                # 寻找与 current_prod 具有公共前缀的所有产生式
                j = i + 1
                while j < len(sorted_productions):
                    next_prod = sorted_productions[j]

                    # 寻找 current_prod 和 next_prod 之间的公共前缀
                    alpha = []
                    min_len = min(len(current_prod), len(next_prod))
                    for k in range(min_len):
                        if current_prod[k] == next_prod[k]:
                            alpha.append(current_prod[k])
                        else:
                            break

                    # 如果公共前缀非空，则将 next_prod 视为同一组的候选项
                    if alpha:
                        # 确保 current_group 存储的是具有最长公共前缀的组
                        # 这里的逻辑比较复杂，为了保证找到最长的公共前缀，我们采用贪婪策略
                        # 简化处理：我们只检查第一个符号是否相同，如果有公共前缀，就分组
                        # 但为了提取最长公共前缀，我们应该使用更精细的逻辑。
                        # 重新简化：只检查第一个符号，然后对组内寻找最长公共前缀
                        if current_prod and next_prod and current_prod[0] == next_prod[0]:
                            current_group.append(next_prod)
                            j += 1
                        else:
                            break
                    else:
                        break  # 没有公共前缀，结束这个组的寻找

                groups.append(current_group)
                i += len(current_group)  # 跳过已经分组的产生式

            new_productions_for_A = []

            for group in groups:
                if len(group) < 2:
                    new_productions_for_A.extend(group)
                    continue

                # 寻找组内所有产生式的最长公共前缀 (Alpha)
                # 假设 group 不为空
                alpha = []
                min_len = min(len(p) for p in group)

                for i_sym in range(min_len):
                    current_symbol = group[0][i_sym]
                    # 检查组内所有产生式在 i_sym 位置是否都匹配
                    if all(len(p) > i_sym and p[i_sym] == current_symbol for p in group[1:]):
                        alpha.append(current_symbol)
                    else:
                        break

                if not alpha:
                    # 没有公共前缀，或者公共前缀为空串
                    new_productions_for_A.extend(group)
                    continue

                # 找到最长公共前缀 alpha，现在执行提取操作
                new_non_terminal = f"{A}_LF_TAIL_{counter}"
                counter += 1

                new_tail_productions = []
                for prod in group:
                    # 剩余部分 (Beta)
                    new_tail_productions.append(prod[len(alpha):])

                # 添加新的非终结符到待检查列表，因为它也可能需要左因子提取
                if len(new_tail_productions) > 1:
                    non_terminals_to_check.add(new_non_terminal)

                new_grammar[new_non_terminal] = new_tail_productions
                new_productions_for_A.append(alpha + [new_non_terminal])

            new_grammar[A] = new_productions_for_A

        self.grammar = new_grammar
        self._identify_symbols()

    def _precompute_select_sets(self):
        """预计算所有产生式的SELECT集合，用于高效解析"""
        self.select_sets = {}
        for non_terminal in self.non_terminals:
            self.select_sets[non_terminal] = []
            for production in self.grammar[non_terminal]:
                select_set = self._compute_select_set(non_terminal, production)
                self.select_sets[non_terminal].append(select_set)

    def _compute_select_set(self, non_terminal: str, production: List[str]) -> Set[str]:
        first_alpha = self._get_first_set_for_sequence(production)
        if self.epsilon_symbol not in first_alpha:
            return first_alpha.copy()

        select_set = first_alpha - {self.epsilon_symbol}
        select_set.update(self.follow_sets.get(non_terminal, set()))
        return select_set

    def _check_ll1_conflicts(self):
        for A in self.non_terminals:
            productions = self.grammar.get(A, [])
            if len(productions) <= 1: continue

            select_sets = self.select_sets[A]

            for i in range(len(select_sets)):
                for j in range(i + 1, len(select_sets)):
                    set_i = select_sets[i]
                    set_j = select_sets[j]
                    intersection = set_i.intersection(set_j)

                    if intersection:
                        prod_i_str = " ".join(productions[i]) if productions[i] else self.epsilon_symbol
                        prod_j_str = " ".join(productions[j]) if productions[j] else self.epsilon_symbol
                        raise ParseError(
                            f"LL(1) Conflict detected for non-terminal '{A}'.\n"
                            f"Productions:\n  1. {A} -> {prod_i_str}\n  2. {A} -> {prod_j_str}\n"
                            f"Conflict tokens (intersection of SELECT sets): {intersection}"
                        )

    def build_analysis_sets(self):
        """执行文法分析"""
        self._identify_symbols()
        self._eliminate_left_recursion()  # 这里的改动将确保不必要的代换不会发生
        self._perform_left_factoring()
        self._compute_first_sets()  # 修复了 UnboundLocalError
        self._compute_follow_sets()  # 修正了 FOLLOW 集合的计算
        self._precompute_select_sets()  # 预计算所有产生式的SELECT集合
        self._check_ll1_conflicts()
        self.analysis_sets_built = True

    def _identify_symbols(self):
        self.non_terminals = set(self.grammar.keys())
        self.terminals = set()
        all_symbols = set()
        for non_term in self.grammar:
            for production in self.grammar[non_term]:
                for symbol in production:
                    all_symbols.add(symbol)

        for symbol in all_symbols:
            if symbol.startswith("'") and symbol.endswith("'"):
                self.terminals.add(symbol[1:-1])
            elif symbol not in self.non_terminals:
                pass
        self.terminals.add('EOF')

    def _is_terminal(self, symbol: str) -> bool:
        if symbol.startswith("'") and symbol.endswith("'"): return True
        return symbol in self.terminals

    def _can_derive_epsilon(self, non_terminal: str) -> bool:
        return self.epsilon_symbol in self.first_sets.get(non_terminal, set())

    def add_production(self, nonterminal: str, production: List[str]) -> None:
        if nonterminal not in self.grammar:
            self.grammar[nonterminal] = []
        self.grammar[nonterminal].append(production)

    def set_start_symbol(self, symbol: str) -> None:
        self.start_symbol = symbol
    
    # ========================================================================
    # [SDT] 代码生成辅助方法
    # ========================================================================
    
    def new_temp(self) -> str:
        """生成新的临时变量名"""
        self.temp_counter += 1
        return f"t{self.temp_counter}"
    
    def new_label(self) -> str:
        """生成新的标签名"""
        self.label_counter += 1
        return f"L{self.label_counter}"
    
    def emit(self, code: str) -> None:
        """发出一条中间代码指令"""
        if self.enable_sdt:
            self.code_buffer.append(code)
    
    def get_generated_code(self) -> str:
        """获取生成的中间代码"""
        return '\n'.join(self.code_buffer)
    
    def reset_code_generation(self) -> None:
        """重置代码生成状态（用于新的编译）"""
        self.code_buffer = []
        self.temp_counter = 0
        self.label_counter = 0
        self.symbol_table = {}
        self.semantic_errors = []
    
    def check_variable_defined(self, var_name: str, token: Token = None) -> bool:
        """检查变量是否已定义，如果未定义则记录错误并提供建议
        
        参数:
            var_name: 变量名
            token: 对应的 Token（用于获取位置信息）
            
        返回:
            True 如果变量已定义，False 否则
        """
        if not self.enable_variable_check:
            return True
            
        if var_name in self.symbol_table:
            return True
        
        # 变量未定义，生成智能建议
        line = token.line if token else 0
        column = token.column if token else 0
        
        # 获取所有已定义的变量名
        defined_vars = set(self.symbol_table.keys())
        suggestion = suggest_variable_fix(var_name, defined_vars)
        
        error_msg = f"语义错误：第 {line} 行，第 {column} 列 - 变量 '{var_name}' 未定义"
        if suggestion:
            error_msg += f"\n  [建议] 您是否想使用 '{suggestion}'？"
        elif defined_vars:
            error_msg += f"\n  [提示] 已定义的变量：{', '.join(sorted(defined_vars))}"
        
        self.semantic_errors.append(error_msg)
        return False
    
    def get_semantic_errors(self) -> List[str]:
        """获取所有语义错误"""
        return self.semantic_errors.copy()
    
    def has_semantic_errors(self) -> bool:
        """检查是否有语义错误"""
        return len(self.semantic_errors) > 0

    def current_token(self) -> Token:
        if self.pos < len(self.tokens): return self.tokens[self.pos]
        return self.tokens[-1]

    def match(self, expected_type: str) -> ASTNode:
        current = self.current_token()
        if current.type == expected_type:
            self.pos += 1
            return ASTNode(name=current.type, token=current)
        else:
            raise ParseError(
                f"Syntax Error at Line {current.line}, Column {current.column}: "
                f"Expected token type '{expected_type}', but found '{current.type}' "
                f"with value '{current.value}'."
            )

    def parse_symbol(self, symbol: str) -> ASTNode:
        """解析符号并同时进行代码生成（SDT）
        
        [SDT核心] 在识别产生式后立即执行翻译动作：
        - 终结符：直接匹配并返回节点
        - 非终结符：递归解析子符号，然后根据产生式生成代码
        """
        if symbol.startswith("'") and symbol.endswith("'"):
            token_type = symbol[1:-1]
            node = self.match(token_type)
            # [SDT] 终结符的综合属性就是其词法值
            if node.token:
                node.synthesized_value = node.token.value
            return node

        if symbol not in self.grammar:
            raise ParseError(f"Unknown symbol reference in grammar: {symbol}")

        current_token_type = self.current_token().type
        productions = self.grammar[symbol]
        select_sets_for_symbol = self.select_sets[symbol]
        found_production = None
        found_index = -1

        for i, select_set in enumerate(select_sets_for_symbol):
            if current_token_type in select_set:
                found_production = productions[i]
                found_index = i
                break

        if found_production is not None:
            children_nodes = []
            # 处理空产生式（epsilon）
            if not found_production or (found_production == []):
                return ASTNode(name=symbol, children=[], token=None, synthesized_value=None)
            
            # 递归解析所有子符号
            for sym in found_production:
                children_nodes.append(self.parse_symbol(sym))
            
            node = ASTNode(name=symbol, children=children_nodes)
            
            # [SDT] *** 关键：识别产生式后立即执行翻译动作 ***
            if self.enable_sdt:
                self._apply_translation_scheme(symbol, found_production, node)
            
            return node
        else:
            expected = self.first_sets.get(symbol, set()) - {self.epsilon_symbol}
            if self.epsilon_symbol in self.first_sets.get(symbol, set()):
                expected.update(self.follow_sets.get(symbol, set()))
            raise ParseError(f"Syntax Error: Expected one of {expected}")
    
    def _is_binary_operator_by_structure(self, production: List[str], op_index: int) -> bool:
        """通过产生式结构识别二元运算符（完全不硬编码token类型）
        
        参数:
            production: 产生式
            op_index: 操作符在产生式中的位置索引
            
        返回:
            如果通过结构判断是二元运算符返回True，否则返回False
            
        说明:
            通过产生式结构识别：如果产生式是 Expr Op Expr 模式（非终结符 终结符 非终结符），
            那么中间的终结符就是二元运算符。完全不依赖token类型名称。
        """
        if op_index < 0 or op_index >= len(production):
            return False
        # 检查是否是二元运算符结构：非终结符 终结符 非终结符
        if op_index > 0 and op_index < len(production) - 1:
            left = production[op_index - 1]
            op = production[op_index]
            right = production[op_index + 1]
            # 结构模式：非终结符 终结符 非终结符
            if (not left.startswith("'") and op.startswith("'") and not right.startswith("'")):
                return True
        return False
    
    def _is_keyword_by_structure(self, production: List[str], keyword_index: int) -> bool:
        """通过产生式结构识别关键字（完全不硬编码token类型）
        
        参数:
            production: 产生式
            keyword_index: 关键字在产生式中的位置索引
            
        返回:
            如果通过结构判断是关键字返回True，否则返回False
            
        说明:
            通过产生式结构识别：如果产生式是 Keyword 'LPAREN' Expr 'RPAREN' 模式，
            那么第一个终结符可能是关键字。完全不依赖token类型名称。
        """
        if keyword_index < 0 or keyword_index >= len(production):
            return False
        # 检查是否是关键字结构：终结符 'LPAREN' 非终结符 'RPAREN'
        if (keyword_index == 0 and len(production) >= 4 and 
            production[0].startswith("'") and production[1] == "'LPAREN'" and 
            not production[2].startswith("'") and production[3] == "'RPAREN'"):
            return True
        return False
    
    def _apply_binary_op(self, op_type: str, left_val: str, right_val: str) -> str:
        """应用二元运算符（通过属性传递识别操作符类型）
        
        参数:
            op_type: 操作符类型（通过属性传递获得）
            left_val: 左操作数的值
            right_val: 右操作数的值
            
        返回:
            生成的临时变量名
        """
        if not left_val or not right_val:
            return None
        temp = self.new_temp()
        self.emit(f"{temp} = {left_val} {op_type} {right_val}")
        return temp
    
    def _apply_translation_scheme(self, symbol: str, production: List[str], node: ASTNode) -> None:
        """应用翻译方案：根据产生式生成中间代码（SDT核心 - 基于属性文法）
        
        这是语法制导翻译的核心方法，每识别一个产生式就立即执行翻译动作。
        使用属性文法思想：通过产生式结构和属性传递识别语义模式，而不是硬编码token类型。
        
        参数:
            symbol: 非终结符名称（LL(1)已经识别了产生式，这里只用于代码生成）
            production: 产生式右部（LL(1)已经选择的具体产生式）
            node: 已解析的AST节点（包含子节点）
        
        说明:
            LL(1)已经通过FIRST/FOLLOW集选择了正确的产生式。
            这里使用属性文法思想：通过产生式结构识别语义模式，通过属性传递识别操作符类型。
            不依赖非终结符名称，不硬编码token类型列表，提高可扩展性。
        """
        children = node.children
        
        # ====================================================================
        # 1. 表达式和算术运算（直接检查产生式内容）
        # ====================================================================
        
        # 单个子节点（传递值）
        if len(production) == 1:
            node.synthesized_value = children[0].synthesized_value
        
        # 表达式尾部（处理加减法）：通过结构识别（第一个是表达式，第二个是尾部）
        # 尾部可能是：操作符 + 操作数 + 尾部，或单个操作节点
        elif len(production) == 2 and not production[0].startswith("'") and not production[1].startswith("'"):
            # 检查第二个符号是否是尾部（通过检查其子节点结构）
            left_val = children[0].synthesized_value
            tail_val = self._process_expr_tail(children[1], left_val)
            node.synthesized_value = tail_val
        
        # 项尾部（处理乘除法）：通过结构识别
        elif len(production) == 2 and not production[0].startswith("'") and not production[1].startswith("'"):
            # 如果第一个处理失败，尝试作为项尾部处理
            left_val = children[0].synthesized_value
            tail_val = self._process_term_tail(children[1], left_val)
            node.synthesized_value = tail_val
        
        # 因子 - 数字：'NUM'
        elif len(production) == 1 and production[0] == "'NUM'":
            node.synthesized_value = children[0].synthesized_value
        
        # 因子 - 标识符：'ID'
        elif len(production) == 1 and production[0] == "'ID'":
            var_name = children[0].synthesized_value
            # [智能提示] 检查变量是否已定义
            if var_name and self.enable_variable_check:
                self.check_variable_defined(var_name, children[0].token)
            node.synthesized_value = var_name
        
        # 括号表达式：'LPAREN' Expr 'RPAREN'
        elif len(production) == 3 and production[0] == "'LPAREN'" and production[2] == "'RPAREN'":
            node.synthesized_value = children[1].synthesized_value
        
        # ====================================================================
        # 2. 语句处理（直接检查产生式内容，LL(1)已经识别了产生式）
        # ====================================================================
        
        # 赋值语句：'ID' 'ASSIGN' Expr 'SEMI'
        elif len(production) >= 3 and production[0] == "'ID'" and production[1] == "'ASSIGN'":
            var_name = children[0].synthesized_value
            expr_val = children[2].synthesized_value
            if var_name:
                # [语义检查] 根据语言类型决定是否检查变量声明
                if var_name not in self.symbol_table:
                    if self.requires_explicit_declaration:
                        token = children[0].token if children[0].token else None
                        self.check_variable_defined(var_name, token)
                    self.symbol_table[var_name] = {'type': 'var'}
                if expr_val:
                    self.emit(f"{var_name} = {expr_val}")
        
        # 输出语句：通过产生式结构识别（关键字 'LPAREN' Expr 'RPAREN'模式）
        # 模式：第一个是关键字（终结符），第二个是'LPAREN'，第三个是表达式（非终结符）
        # 完全通过产生式结构识别，不硬编码token类型
        elif len(production) >= 4 and production[0].startswith("'") and production[1] == "'LPAREN'" and not production[2].startswith("'"):
            # 通过产生式结构识别：如果是关键字结构，则处理输出语句
            if self._is_keyword_by_structure(production, 0):
                expr_val = children[2].synthesized_value
                if expr_val:
                    self.emit(f"param {expr_val}")
                    self.emit(f"call write, 1")
        
        # 输入语句：'READ' 'ID' 'SEMI'
        elif len(production) >= 2 and production[0] == "'READ'" and production[1] == "'ID'":
            var_name = children[1].synthesized_value
            if var_name:
                temp = self.new_temp()
                self.emit(f"{temp} = call read, 0")
                self.emit(f"{var_name} = {temp}")
        
        # ====================================================================
        # 3. 控制流语句（直接检查产生式内容）
        # ====================================================================
        
        # while循环：'WHILE' 'LPAREN' Condition 'RPAREN' Stmt
        elif len(production) >= 5 and production[0] == "'WHILE'" and production[1] == "'LPAREN'":
            loop_label = self.new_label()
            exit_label = self.new_label()
            self.emit(f"{loop_label}:")
            bool_val = children[2].synthesized_value
            if bool_val:
                temp = self.new_temp()
                self.emit(f"{temp} = not {bool_val}")
                self.emit(f"if {temp} goto {exit_label}")
            self.emit(f"goto {loop_label}")
            self.emit(f"{exit_label}:")
        
        # if语句：'IF' 'LPAREN' Condition 'RPAREN' Stmt
        elif len(production) >= 5 and production[0] == "'IF'" and production[1] == "'LPAREN'":
            bool_val = children[2].synthesized_value
            exit_label = self.new_label()
            if bool_val:
                temp = self.new_temp()
                self.emit(f"{temp} = not {bool_val}")
                self.emit(f"if {temp} goto {exit_label}")
            self.emit(f"{exit_label}:")
        
        # 布尔表达式：通过产生式结构识别（Expr Op Expr模式）
        # 模式：第一个是表达式（非终结符），第二个是操作符（终结符），第三个是表达式（非终结符）
        # 完全通过产生式结构识别，不硬编码token类型
        elif len(production) >= 3 and not production[0].startswith("'") and production[1].startswith("'") and not production[2].startswith("'"):
            # 通过产生式结构识别：如果是二元运算符结构，则处理
            if self._is_binary_operator_by_structure(production, 1):
                op_node = children[1]
                if op_node.token:
                    e1 = children[0].synthesized_value
                    op_val = op_node.synthesized_value
                    e2 = children[2].synthesized_value
                    if e1 and op_val and e2:
                        # 使用通用的二元运算符处理函数
                        temp = self._apply_binary_op(op_val, e1, e2)
                        node.synthesized_value = temp
        
        # 关系运算符（单个token）：通过结构识别（单个终结符）
        # 模式：单个终结符，且不是常见的非操作符token
        elif len(production) == 1 and production[0].startswith("'"):
            op_token_type = production[0][1:-1]
            # 排除已知的非操作符token类型
            # 如果是操作符（不是标识符、数字、括号、分号、赋值、逗号等），传递值
            if op_token_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL']:
                node.synthesized_value = children[0].synthesized_value
        
        # ====================================================================
        # 4. 变量声明列表（通过产生式结构识别）
        # ====================================================================
        # 变量声明列表：'ID' ... （第一个是ID，第二个是非终结符，且可能包含COMMA模式）
        elif len(production) >= 2 and production[0] == "'ID'" and not production[1].startswith("'"):
            # 收集所有声明的变量并添加到符号表
            # 模式：'ID' Tail，其中Tail可能是 'COMMA' 'ID' Tail | ε
            def collect_ids_from_tail(tail_node):
                """递归收集尾部的所有变量名（通过结构识别：COMMA ID ...）"""
                var_names = []
                if not tail_node or not tail_node.children:
                    return var_names
                
                # 检查是否是 'COMMA' 'ID' ... 模式
                if len(tail_node.children) >= 2:
                    comma_node = tail_node.children[0]
                    id_node = tail_node.children[1]
                    # 通过token类型判断，而不是节点名称
                    if comma_node.token and comma_node.token.type == 'COMMA':
                        if id_node.token and id_node.token.type == 'ID':
                            var_name = id_node.synthesized_value
                            if var_name:
                                var_names.append(var_name)
                                self.symbol_table[var_name] = {'type': 'var'}
                        
                        # 递归处理剩余的尾部
                        if len(tail_node.children) > 2:
                            next_tail = tail_node.children[2]
                            var_names.extend(collect_ids_from_tail(next_tail))
                
                return var_names
            
            # 处理第一个ID（通过token类型判断）
            if children[0].token and children[0].token.type == 'ID':
                var_name = children[0].synthesized_value
                if var_name:
                    self.symbol_table[var_name] = {'type': 'var'}
            
            # 处理尾部中的所有ID
            if len(children) > 1:
                tail = children[1]
                collect_ids_from_tail(tail)
        
        # ====================================================================
        # 5. 其他情况（不匹配任何已知模式的结构性节点，不生成代码）
        # ====================================================================
        # 如果产生式不匹配任何已知的代码生成模式，则跳过（结构性节点）
    
    def _process_expr_tail(self, tail_node: ASTNode, left_val: str) -> str:
        """处理表达式尾部（加减法）- SDT辅助方法
        
        支持两种文法格式：
        1. simple_expr: Expr_LF_TAIL_X -> AddOp
        2. PL/0: ExprTail -> 'PLUS'/'MINUS' Term ExprTail
        """
        if not tail_node or not tail_node.children:
            return left_val
        
        children = tail_node.children
        
        # 格式1: 单个子节点，且是操作节点（通过结构识别：操作符 + 操作数）
        # 模式：单个子节点，且该子节点有至少2个子节点（操作符 + 操作数）
        if len(children) == 1 and children[0].children:
            if len(children[0].children) >= 2:
                first_child = children[0].children[0]
                if first_child.token:
                    op_type = first_child.token.type
                    # 通过结构识别：第一个是操作符，第二个是操作数
                    # 检查是否是算术运算符（排除非操作符token）
                    if op_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL', 'IF', 'WHILE', 'READ', 'WRITE', 'PRINT']:
                        # 可能是加减运算符
                        if op_type in ['PLUS', 'MINUS']:
                            return self._process_add_op(children[0], left_val)
        
        # 格式2: 直接包含操作符的结构（未优化的文法）
        # 通过结构识别：第一个是操作符token，第二个是操作数
        if children and children[0].token and len(children) >= 2:
            op_type = children[0].token.type
            # 检查是否是算术运算符（排除非操作符token）
            if op_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL', 'IF', 'WHILE', 'READ', 'WRITE', 'PRINT']:
                # 检查是否是已知的算术运算符
                if op_type in ['PLUS', 'MINUS']:
                    op = children[0].synthesized_value
                    right_val = children[1].synthesized_value if len(children) > 1 else None
                    if op and right_val:
                        temp = self.new_temp()
                        self.emit(f"{temp} = {left_val} {op} {right_val}")
                        # 递归处理剩余的ExprTail
                        if len(children) > 2 and children[2].children:
                            return self._process_expr_tail(children[2], temp)
                        return temp
        
        return left_val
    
    def _process_add_op(self, add_op_node: ASTNode, left_val: str) -> str:
        """处理AddOp节点
        
        AddOp结构: AddOp -> 'PLUS'/'MINUS' Term AddOp_LF_TAIL_X
        """
        if not add_op_node or not add_op_node.children:
            return left_val
        
        children = add_op_node.children
        # DEBUG: print(f"[SDT] _process_add_op: children={[c.name for c in children]}, left={left_val}")
        
        if len(children) >= 2:
            # children[0]是操作符，children[1]是操作数，children[2]可能是递归尾部
            # 通过token类型判断操作符
            if children[0].token:
                op_type = children[0].token.type
                # 检查是否是加减运算符（排除非操作符token）
                if op_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL', 'IF', 'WHILE', 'READ', 'WRITE', 'PRINT']:
                    if op_type in ['PLUS', 'MINUS']:
                        op = children[0].synthesized_value
                        right_val = children[1].synthesized_value
                        if op and right_val:
                            temp = self.new_temp()
                            self.emit(f"{temp} = {left_val} {op} {right_val}")
                            # 检查是否还有递归的操作节点（通过结构识别：单个子节点且是操作节点）
                            if len(children) > 2:
                                tail = children[2]
                                if tail.children and len(tail.children) == 1:
                                    tail_child = tail.children[0]
                                    # 检查是否是操作节点结构（操作符 + 操作数）
                                    if tail_child.children and len(tail_child.children) >= 2:
                                        if tail_child.children[0].token:
                                            tail_op_type = tail_child.children[0].token.type
                                            if tail_op_type in ['PLUS', 'MINUS']:
                                                return self._process_add_op(tail_child, temp)
                            return temp
        return left_val
    
    def _process_term_tail(self, tail_node: ASTNode, left_val: str) -> str:
        """处理项尾部（乘除法）- SDT辅助方法
        
        支持两种文法格式：
        1. simple_expr: Term_LF_TAIL_X -> MulOp
        2. PL/0: TermTail -> 'MUL'/'DIV' Factor TermTail
        """
        if not tail_node or not tail_node.children:
            return left_val
        
        children = tail_node.children
        
        # 格式1: 单个子节点，且是操作节点（通过结构识别）
        # 模式：单个子节点，且该子节点有至少2个子节点（操作符 + 操作数）
        if len(children) == 1 and children[0].children:
            if len(children[0].children) >= 2:
                first_child = children[0].children[0]
                if first_child.token:
                    op_type = first_child.token.type
                    # 通过结构识别：第一个是操作符，第二个是操作数
                    # 检查是否是算术运算符（排除非操作符token）
                    if op_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL', 'IF', 'WHILE', 'READ', 'WRITE', 'PRINT']:
                        # 可能是乘除运算符
                        if op_type in ['MUL', 'DIV']:
                            return self._process_mul_op(children[0], left_val)
        
        # 格式2: 直接包含操作符的结构（未优化的文法）
        # 通过结构识别：第一个是操作符token，第二个是操作数
        if children and children[0].token and len(children) >= 2:
            op_type = children[0].token.type
            # 检查是否是算术运算符（排除非操作符token）
            if op_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL', 'IF', 'WHILE', 'READ', 'WRITE', 'PRINT']:
                # 检查是否是已知的算术运算符
                if op_type in ['MUL', 'DIV']:
                    op = children[0].synthesized_value
                    right_val = children[1].synthesized_value if len(children) > 1 else None
                    if op and right_val:
                        temp = self.new_temp()
                        self.emit(f"{temp} = {left_val} {op} {right_val}")
                        # 递归处理剩余的TermTail
                        if len(children) > 2 and children[2].children:
                            return self._process_term_tail(children[2], temp)
                        return temp
        
        return left_val
    
    def _process_mul_op(self, mul_op_node: ASTNode, left_val: str) -> str:
        """处理MulOp节点
        
        MulOp结构: MulOp -> 'MUL'/'DIV' Factor MulOp_LF_TAIL_X
        """
        if not mul_op_node or not mul_op_node.children:
            return left_val
        
        children = mul_op_node.children
        # DEBUG: print(f"[SDT] _process_mul_op: children={[c.name for c in children]}, left={left_val}")
        
        if len(children) >= 2:
            # children[0]是操作符，children[1]是操作数，children[2]可能是递归尾部
            # 通过token类型判断操作符
            if children[0].token:
                op_type = children[0].token.type
                # 检查是否是乘除运算符（排除非操作符token）
                if op_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL', 'IF', 'WHILE', 'READ', 'WRITE', 'PRINT']:
                    if op_type in ['MUL', 'DIV']:
                        op = children[0].synthesized_value
                        right_val = children[1].synthesized_value
                        if op and right_val:
                            temp = self.new_temp()
                            self.emit(f"{temp} = {left_val} {op} {right_val}")
                            # 检查是否还有递归的操作节点（通过结构识别：单个子节点且是操作节点）
                            if len(children) > 2:
                                tail = children[2]
                                if tail.children and len(tail.children) == 1:
                                    tail_child = tail.children[0]
                                    # 检查是否是操作节点结构（操作符 + 操作数）
                                    if tail_child.children and len(tail_child.children) >= 2:
                                        if tail_child.children[0].token:
                                            tail_op_type = tail_child.children[0].token.type
                                            if tail_op_type in ['MUL', 'DIV']:
                                                return self._process_mul_op(tail_child, temp)
                            return temp
        return left_val

    def parse(self, tokens: List[Token]) -> ASTNode:
        """解析tokens并生成AST
        
        [SDT增强] 在解析过程中同时生成中间代码：
        - 每次调用前重置代码生成状态
        - 解析完成后，中间代码已经在code_buffer中
        - 可通过get_generated_code()获取生成的代码
        """
        if not self.start_symbol:
            raise RuntimeError("Start symbol not set.")
        if not self.analysis_sets_built:
            self.build_analysis_sets()
        
        # [SDT] 初始化代码生成状态
        self.reset_code_generation()
        
        self.tokens = tokens
        self.pos = 0
        ast = self.parse_symbol(self.start_symbol)
        if self.current_token().type != 'EOF':
            raise ParseError("Unexpected trailing tokens")
        
        # [SDT] 此时中间代码已经生成在code_buffer中
        return ast

    def get_grammar(self) -> Dict[str, List[List[str]]]:
        return self.grammar.copy()


def create_parser_from_spec(grammar, start, metadata: Dict = None):
    p = ParserGenerator()
    p.set_start_symbol(start)
    for k, v in grammar.items():
        for prod in v: p.add_production(k, prod)
    # 设置元数据
    if metadata:
        p.requires_explicit_declaration = metadata.get('require_explicit_declaration', False)
    return p


def generate_parser_code(grammar: Dict[str, List[List[str]]], start_symbol: str, 
                        first_sets: Dict[str, Set[str]] = None, 
                        follow_sets: Dict[str, Set[str]] = None,
                        metadata: Dict = None) -> str:
    """生成支持SDT的语法分析器Python代码

    [SDT版本] 生成的解析器在解析过程中同时生成中间代码

    参数:
        grammar: 文法规则字典 {非终结符: [[产生式1], [产生式2], ...]}
        start_symbol: 开始符号

    返回:
        包含完整语法分析器的Python代码字符串（支持SDT）
    """
    # 序列化文法
    grammar_dict_str = "{\n"
    for non_terminal, productions in grammar.items():
        # 对产生式按长度降序排序，避免短匹配问题
        sorted_productions = sorted(productions, key=lambda x: len(x), reverse=True)
        grammar_dict_str += f"            '{non_terminal}': [\n"
        for production in sorted_productions:
            # 使用repr()确保正确转义引号
            prod_str = ", ".join([repr(sym) for sym in production])
            grammar_dict_str += f"                [{prod_str}],\n"
        grammar_dict_str += "            ],\n"
    grammar_dict_str += "        }"
    
    # 序列化FIRST和FOLLOW集合
    first_sets = first_sets or {}
    follow_sets = follow_sets or {}
    first_sets_str = "{\n"
    for nt, first_set in first_sets.items():
        first_list = sorted(list(first_set))
        first_sets_str += f"            '{nt}': {{" + ", ".join([repr(t) for t in first_list]) + "},\n"
    first_sets_str += "        }"
    
    follow_sets_str = "{\n"
    for nt, follow_set in follow_sets.items():
        follow_list = sorted(list(follow_set))
        follow_sets_str += f"            '{nt}': {{" + ", ".join([repr(t) for t in follow_list]) + "},\n"
    follow_sets_str += "        }"
    
    # 从元数据中获取语言特性配置
    require_explicit = False
    if metadata:
        require_explicit = metadata.get('require_explicit_declaration', False)

    parser_code = f'''
# =============================================================================
# 自动生成的语法分析器 [SDT版本]
# 在解析过程中同时生成中间代码（语法制导翻译）
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Optional, Set

@dataclass
class ASTNode:
    """AST节点 [SDT扩展]"""
    name: str
    children: List['ASTNode'] = field(default_factory=list)
    token: Optional[object] = None
    synthesized_value: str = None  # SDT: 综合属性
    
    def __repr__(self, indent=0):
        prefix = "  " * indent
        result = f"{{prefix}}{{self.name}}"
        if self.token:
            result += f" ('{{self.token.value}}')"
        if self.synthesized_value:
            result += f" [val={{self.synthesized_value}}]"
        result += "\\n"
        for child in self.children:
            result += child.__repr__(indent + 1)
        return result

class GeneratedParser:
    """自动生成的语法分析器 [SDT版本]
    
    在解析过程中同时进行代码生成
    """
    
    def __init__(self):
        self.tokens = []
        self.pos = 0
        self.grammar = {grammar_dict_str}
        self.start_symbol = '{start_symbol}'
        
        # FIRST和FOLLOW集合（用于错误处理和空产生式判断）
        self.first_sets = {first_sets_str}
        self.follow_sets = {follow_sets_str}
        self.epsilon_symbol = 'EPSILON'
        
        # [SDT] 代码生成相关
        self.code_buffer = []
        self.temp_counter = 0
        self.label_counter = 0
        self.symbol_table = {{}}
        
        # [语言特性] 变量声明要求（从语法规则元数据中读取）
        self.requires_explicit_declaration = {require_explicit}
        self.enable_variable_check = True
        self.semantic_errors = []
    
    # [SDT] 代码生成辅助方法
    def new_temp(self):
        self.temp_counter += 1
        return f"t{{self.temp_counter}}"
    
    def new_label(self):
        self.label_counter += 1
        return f"L{{self.label_counter}}"
    
    def emit(self, code):
        self.code_buffer.append(code)
    
    def get_generated_code(self):
        return '\\n'.join(self.code_buffer)
    
    def reset_code_generation(self):
        self.code_buffer = []
        self.temp_counter = 0
        self.label_counter = 0
        self.symbol_table = {{}}
    
    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]
    
    def advance(self):
        if self.pos < len(self.tokens) - 1:
            token = self.tokens[self.pos]
            self.pos += 1
            return token
        return self.tokens[-1]
    
    def expect(self, token_type: str):
        token = self.current_token()
        if token.type == token_type:
            return self.advance()
        raise SyntaxError(
            f"语法错误：第 {{token.line}} 行，第 {{token.column}} 列\\n"
            f"  期望：{{token_type}}\\n"
            f"  实际：{{token.type}} (值: '{{token.value}}')"
        )
    
    def _is_terminal(self, symbol: str) -> bool:
        if symbol.startswith("'") and symbol.endswith("'"):
            return True
        return symbol in ['EOF']  # 基本终结符检查
    
    def _get_first_set_for_sequence(self, sequence: List[str]) -> Set[str]:
        """计算符号序列的FIRST集"""
        first_set = set()
        for Y in sequence:
            if self._is_terminal(Y):
                token_type = Y[1:-1] if Y.startswith("'") else Y
                first_set.add(token_type)
                return first_set
            else:
                first_set.update(self.first_sets.get(Y, set()) - {{'EPSILON'}})
                if 'EPSILON' not in self.first_sets.get(Y, set()):
                    return first_set
        first_set.add('EPSILON')
        return first_set
    
    def parse_symbol(self, symbol: str):
        # 终结符（带引号）[SDT: 设置综合属性]
        if symbol.startswith("'") and symbol.endswith("'"):
            token_type = symbol[1:-1]
            token = self.expect(token_type)
            node = ASTNode(name=symbol, token=token)
            node.synthesized_value = token.value if token else None
            return node
        
        # 非终结符 [SDT: 解析后立即生成代码]
        if symbol in self.grammar:
            current_token_type = self.current_token().type
            productions = self.grammar[symbol]
            found_production = None
            
            # 使用FIRST集进行预测，选择匹配的产生式
            if found_production is None:
                for production in productions:
                    production_first_set = self._get_first_set_for_sequence(production)
                    if current_token_type in production_first_set:
                        found_production = production
                        break
                    if 'EPSILON' in production_first_set:
                        if current_token_type in self.follow_sets.get(symbol, set()):
                            found_production = production
                            break
            
            if found_production is not None:
                # 处理空产生式（epsilon）
                if not found_production or len(found_production) == 0:
                    node = ASTNode(name=symbol, children=[])
                    # [SDT] 识别产生式后立即执行翻译动作
                    if hasattr(self, '_apply_sdt_rules'):
                        self._apply_sdt_rules(symbol, found_production, node)
                    return node
                
                children = []
                for sym in found_production:
                    child = self.parse_symbol(sym)
                    children.append(child)
                
                node = ASTNode(name=symbol, children=children)
                
                # [SDT] 识别产生式后立即执行翻译动作
                if hasattr(self, '_apply_sdt_rules'):
                    self._apply_sdt_rules(symbol, found_production, node)
                
                return node
            
            # 所有产生式都失败，生成详细的错误信息
            current = self.current_token()
            expected_tokens = []
            for prod in self.grammar[symbol]:
                if prod and len(prod) > 0 and prod[0].startswith("'") and prod[0].endswith("'"):
                    expected_tokens.append(prod[0][1:-1])
            
            # 如果符号可以为空，添加FOLLOW集
            if self.epsilon_symbol in self.first_sets.get(symbol, set()):
                expected_tokens.extend(list(self.follow_sets.get(symbol, set())))
            
            expected_str = ", ".join(set(expected_tokens)) if expected_tokens else "未知"
            raise SyntaxError(
                f"语法错误：第 {{current.line}} 行，第 {{current.column}} 列\\n"
                f"  无法解析非终结符 '{{symbol}}'\\n"
                f"  当前符号：{{current.type}} (值: '{{current.value}}')\\n"
                f"  期望的符号类型：{{expected_str}}"
            )
        
        # 直接匹配token类型
        if self.current_token().type == symbol:
            token = self.advance()
            return ASTNode(name=symbol, token=token)
        
        raise SyntaxError(f"未知符号: {{symbol}}")
    
    def _is_binary_operator_by_structure(self, production: List[str], op_index: int) -> bool:
        """通过产生式结构识别二元运算符（完全不硬编码token类型）
        
        参数:
            production: 产生式
            op_index: 操作符在产生式中的位置索引
            
        返回:
            如果通过结构判断是二元运算符返回True，否则返回False
            
        说明:
            通过产生式结构识别：如果产生式是 Expr Op Expr 模式（非终结符 终结符 非终结符），
            那么中间的终结符就是二元运算符。完全不依赖token类型名称。
        """
        if op_index < 0 or op_index >= len(production):
            return False
        # 检查是否是二元运算符结构：非终结符 终结符 非终结符
        if op_index > 0 and op_index < len(production) - 1:
            left = production[op_index - 1]
            op = production[op_index]
            right = production[op_index + 1]
            # 结构模式：非终结符 终结符 非终结符
            if (not left.startswith("'") and op.startswith("'") and not right.startswith("'")):
                return True
        return False
    
    def _is_keyword_by_structure(self, production: List[str], keyword_index: int) -> bool:
        """通过产生式结构识别关键字（完全不硬编码token类型）
        
        参数:
            production: 产生式
            keyword_index: 关键字在产生式中的位置索引
            
        返回:
            如果通过结构判断是关键字返回True，否则返回False
            
        说明:
            通过产生式结构识别：如果产生式是 Keyword 'LPAREN' Expr 'RPAREN' 模式，
            那么第一个终结符可能是关键字。完全不依赖token类型名称。
        """
        if keyword_index < 0 or keyword_index >= len(production):
            return False
        # 检查是否是关键字结构：终结符 'LPAREN' 非终结符 'RPAREN'
        if (keyword_index == 0 and len(production) >= 4 and 
            production[0].startswith("'") and production[1] == "'LPAREN'" and 
            not production[2].startswith("'") and production[3] == "'RPAREN'"):
            return True
        return False
    
    def _apply_binary_op(self, op_type: str, left_val: str, right_val: str) -> str:
        """应用二元运算符（通过属性传递识别操作符类型）
        
        参数:
            op_type: 操作符类型（通过属性传递获得）
            left_val: 左操作数的值
            right_val: 右操作数的值
            
        返回:
            生成的临时变量名
        """
        if not left_val or not right_val:
            return None
        temp = self.new_temp()
        self.emit(f"{{temp}} = {{left_val}} {{op_type}} {{right_val}}")
        return temp
    
    def _apply_sdt_rules(self, symbol, production, node):
        """应用SDT规则：根据产生式生成代码（基于属性文法，不硬编码token类型）"""
        children = node.children
        
        # 单个子节点（传递值）
        if len(production) == 1:
            node.synthesized_value = children[0].synthesized_value
        
        # 表达式尾部（处理加减法）：Term ExprTail 或 Term Expr_LF_TAIL_X
        elif len(production) == 2 and not production[0].startswith("'") and not production[1].startswith("'"):
            left_val = children[0].synthesized_value
            tail_val = self._handle_tail(children[1], left_val)
            node.synthesized_value = tail_val
        
        # 因子 - 数字：'NUM'
        elif len(production) == 1 and production[0] == "'NUM'":
            node.synthesized_value = children[0].synthesized_value
        
        # 因子 - 标识符：'ID'
        elif len(production) == 1 and production[0] == "'ID'":
            var_name = children[0].synthesized_value
            # [智能提示] 检查变量是否已定义
            if var_name and self.enable_variable_check:
                token = children[0].token if hasattr(children[0], 'token') and children[0].token else None
                self.check_variable_defined(var_name, token)
            node.synthesized_value = var_name
        
        # 括号表达式：'LPAREN' Expr 'RPAREN'
        elif len(production) == 3 and production[0] == "'LPAREN'" and production[2] == "'RPAREN'":
            node.synthesized_value = children[1].synthesized_value
        
        # 赋值语句：'ID' 'ASSIGN' Expr 'SEMI'
        elif len(production) >= 3 and production[0] == "'ID'" and production[1] == "'ASSIGN'":
            var_name = children[0].synthesized_value
            expr_val = children[2].synthesized_value
            if var_name:
                # [语义检查] 根据语言类型决定是否检查变量声明
                if var_name not in self.symbol_table:
                    if self.requires_explicit_declaration:
                        token = children[0].token if hasattr(children[0], 'token') and children[0].token else None
                        self.check_variable_defined(var_name, token)
                    self.symbol_table[var_name] = {{'type': 'var'}}
                if expr_val:
                    self.emit(f"{{var_name}} = {{expr_val}}")
        
        # 输出语句：通过结构识别（关键字 'LPAREN' Expr 'RPAREN' ...）
        # 模式：第一个是关键字（终结符），第二个是'LPAREN'，第三个是表达式（非终结符）
        elif len(production) >= 4 and production[0].startswith("'") and production[1] == "'LPAREN'" and not production[2].startswith("'"):
            # 通过结构识别：关键字后跟括号表达式
            # 排除已知的操作符和标识符模式
            first_token_type = production[0][1:-1]
            # 如果第一个token不是操作符、关系符、赋值符、标识符或数字，则可能是关键字
            if first_token_type not in ['PLUS', 'MINUS', 'MUL', 'DIV', 'LT', 'LE', 'GT', 'GE', 'EQ', 'NE', 'ASSIGN', 'ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'COMMA']:
                expr_val = children[2].synthesized_value
                if expr_val:
                    self.emit(f"param {{expr_val}}")
                    self.emit(f"call write, 1")
        
        # 输入语句：'READ' 'ID' 'SEMI'
        elif len(production) >= 2 and production[0] == "'READ'" and production[1] == "'ID'":
            var_name = children[1].synthesized_value
            if var_name:
                temp = self.new_temp()
                self.emit(f"{{temp}} = call read, 0")
                self.emit(f"{{var_name}} = {{temp}}")
        
        # 变量声明列表：'ID' ... （通过产生式结构识别）
        elif len(production) >= 2 and production[0] == "'ID'" and not production[1].startswith("'"):
            # 收集所有声明的变量并添加到符号表
            # 模式：'ID' Tail，其中Tail可能是 'COMMA' 'ID' Tail | ε
            def collect_ids_from_tail(tail_node):
                """递归收集尾部的所有变量名（通过结构识别：COMMA ID ...）"""
                var_names = []
                if not tail_node or not tail_node.children:
                    return var_names
                
                # 检查是否是 'COMMA' 'ID' ... 模式
                if len(tail_node.children) >= 2:
                    comma_node = tail_node.children[0]
                    id_node = tail_node.children[1]
                    # 通过token类型判断，而不是节点名称
                    if comma_node.token and comma_node.token.type == 'COMMA':
                        if id_node.token and id_node.token.type == 'ID':
                            var_name = id_node.synthesized_value
                            if var_name:
                                var_names.append(var_name)
                                self.symbol_table[var_name] = {{'type': 'var'}}
                        
                        # 递归处理剩余的尾部
                        if len(tail_node.children) > 2:
                            next_tail = tail_node.children[2]
                            var_names.extend(collect_ids_from_tail(next_tail))
                
                return var_names
            
            # 处理第一个ID（通过token类型判断）
            if children[0].token and children[0].token.type == 'ID':
                var_name = children[0].synthesized_value
                if var_name:
                    self.symbol_table[var_name] = {{'type': 'var'}}
            
            # 处理尾部中的所有ID
            if len(children) > 1:
                tail = children[1]
                collect_ids_from_tail(tail)
        
        # 布尔表达式：通过结构识别（Expr Op Expr，其中Op是关系运算符）
        # 模式：第一个是表达式，第二个是操作符（终结符），第三个是表达式
        elif len(production) >= 3 and not production[0].startswith("'") and production[1].startswith("'") and not production[2].startswith("'"):
            # 检查中间的操作符是否是关系运算符（通过token类型判断）
            op_token_type = production[1][1:-1]
            # 关系运算符通常是比较操作符（可以通过结构识别：两个表达式之间的操作符）
            if children[1].token and children[1].token.type == op_token_type:
                e1 = children[0].synthesized_value
                op = children[1].synthesized_value
                e2 = children[2].synthesized_value
                if e1 and op and e2:
                    temp = self.new_temp()
                    self.emit(f"{{temp}} = {{e1}} {{op}} {{e2}}")
                    node.synthesized_value = temp
        
        # 关系运算符（单个token）：通过结构识别（单个终结符）
        # 模式：单个终结符，且不是常见的非操作符token
        elif len(production) == 1 and production[0].startswith("'"):
            op_token_type = production[0][1:-1]
            # 排除已知的非操作符token类型
            # 如果是操作符（不是标识符、数字、括号、分号、赋值、逗号等），传递值
            if op_token_type not in ['ID', 'NUM', 'LPAREN', 'RPAREN', 'SEMI', 'ASSIGN', 'COMMA', 'LBRACE', 'RBRACE', 'BEGIN', 'END', 'VAR', 'CONST', 'PROCEDURE', 'CALL']:
                node.synthesized_value = children[0].synthesized_value
        
        # while循环：'WHILE' 'LPAREN' Condition 'RPAREN' Stmt
        elif len(production) >= 5 and production[0] == "'WHILE'" and production[1] == "'LPAREN'":
            loop_label = self.new_label()
            exit_label = self.new_label()
            self.emit(f"{{loop_label}}:")
            bool_val = children[2].synthesized_value
            if bool_val:
                temp = self.new_temp()
                self.emit(f"{{temp}} = not {{bool_val}}")
                self.emit(f"if {{temp}} goto {{exit_label}}")
            self.emit(f"goto {{loop_label}}")
            self.emit(f"{{exit_label}}:")
        
        # if语句：'IF' 'LPAREN' Condition 'RPAREN' Stmt
        elif len(production) >= 5 and production[0] == "'IF'" and production[1] == "'LPAREN'":
            bool_val = children[2].synthesized_value
            exit_label = self.new_label()
            if bool_val:
                temp = self.new_temp()
                self.emit(f"{{temp}} = not {{bool_val}}")
                self.emit(f"if {{temp}} goto {{exit_label}}")
            self.emit(f"{{exit_label}}:")
        
        # 其他情况（不匹配任何已知模式的结构性节点，不生成代码）
    
    def _handle_tail(self, tail_node, left_val):
        """处理表达式尾部（通过结构识别，不依赖节点名称）"""
        if not tail_node or not tail_node.children:
            return left_val
        children = tail_node.children
        
        # 格式1: 单个子节点，且是操作节点（通过产生式结构识别：操作符 + 操作数）
        # 模式：单个子节点，且该子节点有至少2个子节点（操作符 + 操作数）
        # 完全基于结构：第一个是终结符（操作符），第二个是非终结符或终结符（操作数）
        if len(children) == 1 and children[0].children:
            if len(children[0].children) >= 2:
                first_child = children[0].children[0]
                if first_child.token:
                    # 通过结构识别：第一个是终结符，第二个是操作数
                    op_val = first_child.synthesized_value
                    right_val = children[0].children[1].synthesized_value
                    if op_val and right_val:
                        # 使用通用的二元运算符处理函数
                        return self._apply_binary_op(op_val, left_val, right_val)
        
        # 格式2: 直接包含操作符的结构（未优化的文法）
        # 通过结构识别：第一个是操作符token（终结符），第二个是操作数
        # 完全基于结构：不判断token类型，只判断结构
        if children and children[0].token and len(children) >= 2:
            # 通过结构判断：第一个是终结符，第二个是操作数
            op = children[0].synthesized_value
            right = children[1].synthesized_value
            if op and right:
                temp = self.new_temp()
                self.emit(f"{{temp}} = {{left_val}} {{op}} {{right}}")
                if len(children) > 2:
                    return self._handle_tail(children[2], temp)
                return temp
        return left_val
    
    def _handle_add_op(self, add_op_node, left_val):
        """处理加法操作节点（通过结构识别，不依赖节点名称和token类型）"""
        if not add_op_node or not add_op_node.children:
            return left_val
        children = add_op_node.children
        # 通过结构识别：第一个是操作符（终结符），第二个是操作数（非终结符或终结符）
        # 完全基于结构：不判断token类型，只判断结构
        if len(children) >= 2 and children[0].token:
            op = children[0].synthesized_value
            right_val = children[1].synthesized_value
            if op and right_val:
                temp = self.new_temp()
                self.emit(f"{{temp}} = {{left_val}} {{op}} {{right_val}}")
                # 检查是否还有递归的操作节点（通过结构识别）
                if len(children) > 2:
                    tail = children[2]
                    if tail.children and len(tail.children) == 1:
                        tail_child = tail.children[0]
                        # 检查是否是操作节点结构（操作符 + 操作数）
                        if tail_child.children and len(tail_child.children) >= 2:
                            if tail_child.children[0].token:
                                # 递归处理，不判断token类型
                                return self._handle_add_op(tail_child, temp)
                return temp
        return left_val
    
    def _handle_mul_op(self, mul_op_node, left_val):
        """处理乘法操作节点（通过结构识别，不依赖节点名称和token类型）"""
        if not mul_op_node or not mul_op_node.children:
            return left_val
        children = mul_op_node.children
        # 通过结构识别：第一个是操作符（终结符），第二个是操作数（非终结符或终结符）
        # 完全基于结构：不判断token类型，只判断结构
        if len(children) >= 2 and children[0].token:
            op = children[0].synthesized_value
            right_val = children[1].synthesized_value
            if op and right_val:
                temp = self.new_temp()
                self.emit(f"{{temp}} = {{left_val}} {{op}} {{right_val}}")
                # 检查是否还有递归的操作节点（通过结构识别）
                if len(children) > 2:
                    tail = children[2]
                    if tail.children and len(tail.children) == 1:
                        tail_child = tail.children[0]
                        # 检查是否是操作节点结构（操作符 + 操作数）
                        if tail_child.children and len(tail_child.children) >= 2:
                            if tail_child.children[0].token:
                                # 递归处理，不判断token类型
                                return self._handle_mul_op(tail_child, temp)
                return temp
        return left_val
    
    def check_variable_defined(self, var_name: str, token = None):
        """检查变量是否已定义，如果未定义则记录错误并提供建议"""
        if not self.enable_variable_check:
            return True
            
        if var_name in self.symbol_table:
            return True
        
        # 变量未定义，生成智能建议
        line = token.line if token else 0
        column = token.column if token else 0
        
        # 获取所有已定义的变量名
        defined_vars = set(self.symbol_table.keys())
        
        # 简单的编辑距离建议（可以改进）
        suggestion = None
        if defined_vars:
            # 简单的字符串相似度检查
            for defined_var in defined_vars:
                if len(var_name) == len(defined_var):
                    diff = sum(1 for a, b in zip(var_name, defined_var) if a != b)
                    if diff == 1:  # 只有一个字符不同
                        suggestion = defined_var
                        break
        
        error_msg = f"语义错误：第 {{line}} 行，第 {{column}} 列 - 变量 '{{var_name}}' 未定义"
        if suggestion:
            error_msg += f"\\n  [建议] 您是否想使用 '{{suggestion}}'？"
        elif defined_vars:
            error_msg += f"\\n  [提示] 已定义的变量：{{', '.join(sorted(defined_vars))}}"
        
        self.semantic_errors.append(error_msg)
        return False
    
    def get_semantic_errors(self):
        """获取所有语义错误"""
        return self.semantic_errors.copy()
    
    def has_semantic_errors(self):
        """检查是否有语义错误"""
        return len(self.semantic_errors) > 0
    
    def parse(self, tokens: List):
        """解析tokens [SDT: 同时生成代码]"""
        self.reset_code_generation()
        
        self.tokens = tokens
        self.pos = 0
        try:
            ast = self.parse_symbol(self.start_symbol)
        except SyntaxError as e:
            # 重新抛出，保持错误信息
            raise
        
        current = self.current_token()
        if current.type != 'EOF':
            raise SyntaxError(
                f"语法错误：第 {{current.line}} 行，第 {{current.column}} 列\\n"
                f"  解析不完整，仍有未处理的符号\\n"
                f"  剩余符号：{{current.type}} (值: '{{current.value}}')"
            )
        return ast
'''
    return parser_code
