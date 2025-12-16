"""语法分析器生成器 (同学B负责)

该模块实现自动构建解析器的功能，使用LL(1)分析法和递归下降法
将上下文无关文法(BNF)转换为解析器。
"""

from typing import List, Dict, Tuple, Any, Optional, Set
from dataclasses import dataclass
from src.compiler_generator.lexer_generator import Token


@dataclass
class ASTNode:
    """抽象语法树(AST)节点"""
    name: str
    children: List['ASTNode'] = None
    token: Token = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

    def __repr__(self, indent=0):
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
    """语法分析器生成器类"""

    def __init__(self):
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

        for A, productions in self.grammar.items():
            if not productions: continue

            groups = {}
            for prod in productions:
                first_symbol = prod[0] if prod else self.epsilon_symbol
                groups.setdefault(first_symbol, []).append(prod)

            new_productions_for_A = []
            for first_symbol, group in groups.items():
                if len(group) < 2:
                    new_productions_for_A.extend(group)
                    continue

                # 寻找最长公共前缀
                min_len = min(len(p) for p in group)
                alpha = []
                for i in range(min_len):
                    current_symbol = group[0][i]
                    if all(len(p) > i and p[i] == current_symbol for p in group[1:]):
                        alpha.append(current_symbol)
                    else:
                        break

                if not alpha:
                    new_productions_for_A.extend(group)
                    continue

                # 修改：使用 _LF_TAIL_ 命名以符合测试预期
                new_non_terminal = f"{A}_LF_TAIL_{counter}"
                counter += 1

                new_tail_productions = []
                for prod in group:
                    new_tail_productions.append(prod[len(alpha):])

                new_grammar[new_non_terminal] = new_tail_productions
                new_productions_for_A.append(alpha + [new_non_terminal])

            new_grammar[A] = new_productions_for_A

        self.grammar = new_grammar
        self._identify_symbols()

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

            select_sets_info = []
            for production in productions:
                select_sets_info.append({
                    'production': production,
                    'select': self._compute_select_set(A, production)
                })

            for i in range(len(select_sets_info)):
                for j in range(i + 1, len(select_sets_info)):
                    set_i = select_sets_info[i]['select']
                    set_j = select_sets_info[j]['select']
                    intersection = set_i.intersection(set_j)

                    if intersection:
                        prod_i_str = " ".join(select_sets_info[i]['production']) if select_sets_info[i][
                            'production'] else self.epsilon_symbol
                        prod_j_str = " ".join(select_sets_info[j]['production']) if select_sets_info[j][
                            'production'] else self.epsilon_symbol
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
        if symbol.startswith("'") and symbol.endswith("'"):
            token_type = symbol[1:-1]
            return self.match(token_type)

        if symbol not in self.grammar:
            raise ParseError(f"Unknown symbol reference in grammar: {symbol}")

        current_token_type = self.current_token().type
        productions = self.grammar[symbol]
        found_production = None

        for production in productions:
            production_first_set = self._get_first_set_for_sequence(production)
            if current_token_type in production_first_set:
                found_production = production
                break
            if self.epsilon_symbol in production_first_set:
                if current_token_type in self.follow_sets.get(symbol, set()):
                    found_production = production
                    break

        if found_production is not None:
            children_nodes = []
            if not found_production and self.epsilon_symbol in self._get_first_set_for_sequence(found_production):
                return ASTNode(name=symbol, children=[], token=None)
            for sym in found_production:
                children_nodes.append(self.parse_symbol(sym))
            return ASTNode(name=symbol, children=children_nodes)
        else:
            expected = self.first_sets.get(symbol, set()) - {self.epsilon_symbol}
            if self.epsilon_symbol in self.first_sets.get(symbol, set()):
                expected.update(self.follow_sets.get(symbol, set()))
            raise ParseError(f"Syntax Error: Expected one of {expected}")

    def parse(self, tokens: List[Token]) -> ASTNode:
        if not self.start_symbol:
            raise RuntimeError("Start symbol not set.")
        if not self.analysis_sets_built:
            self.build_analysis_sets()
        self.tokens = tokens
        self.pos = 0
        ast = self.parse_symbol(self.start_symbol)
        if self.current_token().type != 'EOF':
            raise ParseError("Unexpected trailing tokens")
        return ast

    def get_grammar(self) -> Dict[str, List[List[str]]]:
        return self.grammar.copy()


def create_parser_from_spec(grammar, start):
    p = ParserGenerator()
    p.set_start_symbol(start)
    for k, v in grammar.items():
        for prod in v: p.add_production(k, prod)
    return p


def generate_parser_code(grammar: Dict[str, List[List[str]]], start_symbol: str) -> str:
    """生成语法分析器的Python代码

    参数:
        grammar: 文法规则字典 {非终结符: [[产生式1], [产生式2], ...]}
        start_symbol: 开始符号

    返回:
        包含完整语法分析器的Python代码字符串
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

    parser_code = f'''
# =============================================================================
# 自动生成的语法分析器
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ASTNode:
    """AST节点"""
    name: str
    children: List['ASTNode'] = field(default_factory=list)
    token: Optional[object] = None
    
    def __repr__(self, indent=0):
        prefix = "  " * indent
        result = f"{{prefix}}{{self.name}}"
        if self.token:
            result += f" ('{{self.token.value}}')"
        result += "\\n"
        for child in self.children:
            result += child.__repr__(indent + 1)
        return result

class GeneratedParser:
    """自动生成的语法分析器"""
    
    def __init__(self):
        self.tokens = []
        self.pos = 0
        self.grammar = {grammar_dict_str}
        self.start_symbol = '{start_symbol}'
    
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
            f"语法错误: 第{{token.line}}行, 第{{token.column}}列\\n"
            f"  期望: {{token_type}}\\n"
            f"  实际: {{token.type}} (值: '{{token.value}}')"
        )
    
    def parse_symbol(self, symbol: str):
        # 终结符（带引号）
        if symbol.startswith("'") and symbol.endswith("'"):
            token_type = symbol[1:-1]
            token = self.expect(token_type)
            return ASTNode(name=symbol, token=token)
        
        # 非终结符
        if symbol in self.grammar:
            saved_pos = self.pos
            for production in self.grammar[symbol]:
                try:
                    children = []
                    for sym in production:
                        child = self.parse_symbol(sym)
                        children.append(child)
                    return ASTNode(name=symbol, children=children)
                except SyntaxError:
                    self.pos = saved_pos
                    continue
                except Exception:
                    self.pos = saved_pos
                    raise
            
            # 所有产生式都失败，生成详细的错误信息
            current = self.current_token()
            expected_tokens = []
            for prod in self.grammar[symbol]:
                if prod and prod[0].startswith("'") and prod[0].endswith("'"):
                    expected_tokens.append(prod[0][1:-1])
            
            expected_str = ", ".join(set(expected_tokens)) if expected_tokens else "未知"
            raise SyntaxError(
                f"语法错误: 第{{current.line}}行, 第{{current.column}}列\\n"
                f"  无法解析非终结符 '{{symbol}}'\\n"
                f"  当前token: {{current.type}} (值: '{{current.value}}')\\n"
                f"  期望的token类型: {{expected_str}}"
            )
        
        # 直接匹配token类型
        if self.current_token().type == symbol:
            token = self.advance()
            return ASTNode(name=symbol, token=token)
        
        raise SyntaxError(f"未知符号: {{symbol}}")
    
    def parse(self, tokens: List):
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
                f"语法错误: 第{{current.line}}行, 第{{current.column}}列\\n"
                f"  解析未完成，仍有未处理的token\\n"
                f"  剩余token: {{current.type}} (值: '{{current.value}}')"
            )
        return ast
'''
    return parser_code
