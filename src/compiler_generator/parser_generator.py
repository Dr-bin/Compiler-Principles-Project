"""语法分析器生成器 (同学B负责)

该模块实现自动构建解析器的功能，使用LL(1)分析法和递归下降法
将上下文无关文法(BNF)转换为解析器。
"""

from typing import List, Dict, Tuple, Any, Optional
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

    def advance(self) -> Token:
        """消耗一个Token，移动到下一个
        
        返回:
            被消耗的Token对象
            
        说明:
            将解析位置向前移动一步。
        """
        token = self.current_token()
        if token.type != 'EOF':
            self.pos += 1
        return token

    def expect(self, token_type: str) -> Token:
        """期望并消耗一个特定类型的Token
        
        参数:
            token_type: 期望的Token类型
            
        返回:
            匹配的Token对象
            
        异常:
            ParseError: 当当前Token类型不匹配时抛出
            
        说明:
            这是语法分析中最基础的操作，用于匹配终结符。
        """
        if self.current_token().type != token_type:
            raise ParseError(
                f"Expected {token_type} but got {self.current_token().type} "
                f"at position {self.pos}: {self.current_token()}"
            )
        return self.advance()

    def parse_symbol(self, symbol: str) -> ASTNode:
        """递归解析一个符号（可以是终结符或非终结符）
        
        参数:
            symbol: 要解析的符号名称
            
        返回:
            对应的AST节点
            
        异常:
            ParseError: 当无法匹配时抛出
            
        说明:
            - 如果symbol是终结符（Token类型），则匹配该Token
            - 如果symbol是非终结符，则尝试其所有产生式（回溯式选择）
        """
        # 如果是终结符（带引号的形式），直接匹配
        if symbol.startswith("'") and symbol.endswith("'"):
            # 提取引号内的token类型
            token_type = symbol[1:-1]
            token = self.expect(token_type)
            return ASTNode(name=symbol, token=token)
        
        # 如果是不带引号的token类型名称（用于与Token类型匹配），直接匹配
        # 检查当前token是否与symbol匹配
        if self.current_token().type == symbol:
            token = self.advance()
            return ASTNode(name=symbol, token=token)

        # 如果是非终结符
        if symbol not in self.grammar:
            raise ParseError(f"Unknown symbol: {symbol}")

        # 保存当前位置用于回溯
        saved_pos = self.pos
        
        # 尝试所有可能的产生式
        for production in self.grammar[symbol]:
            try:
                children = []
                for sym in production:
                    child_node = self.parse_symbol(sym)
                    children.append(child_node)
                
                # 成功解析此产生式
                return ASTNode(name=symbol, children=children)
            
            except ParseError:
                # 该产生式不匹配，回溯并尝试下一个
                self.pos = saved_pos
                continue

        # 所有产生式都失败
        raise ParseError(
            f"No matching production for {symbol} at position {self.pos}: "
            f"{self.current_token()}"
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
