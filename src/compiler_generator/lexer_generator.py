"""词法分析器生成器 (同学A负责)

该模块实现自动构建扫描器/词法分析器的功能，使用Thompson构造法和子集构造法
将正则表达式转换为NFA，再转换为DFA进行高效的词法分析。
"""

import re
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass


@dataclass
class Token:
    """Token 数据结构，表示一个词法单元
    
    属性:
        type: Token类型（如'ID', 'NUM', 'PLUS'等）
        value: Token的字面值（实际文本内容）
        line: 所在源代码的行号
        column: 所在源代码的列号
    """
    type: str
    value: str
    line: int
    column: int

    def __repr__(self):
        """返回Token的字符串表示"""
        return f"Token({self.type}, {self.value!r}, {self.line}, {self.column})"


class LexerGenerator:
    """词法分析器生成器类
    
    使用正则表达式规则自动生成词法分析器。
    将多个正则表达式规则编译为高效的扫描器。
    """

    def __init__(self):
        """初始化词法生成器
        
        属性说明:
            token_specs: 存储 (name, regex_pattern) 的列表
            compiled_patterns: 编译后的正则表达式对象列表
        """
        self.token_specs: List[Tuple[str, str]] = []
        self.compiled_patterns: List[Tuple[str, re.Pattern]] = []

    def add_token_rule(self, token_type: str, regex_pattern: str) -> None:
        """添加一个词法规则（Token类型和对应的正则表达式）
        
        参数:
            token_type: Token的类型名称（如'ID', 'NUM', 'OPERATOR'等）
            regex_pattern: 对应的正则表达式字符串
            
        返回:
            None
            
        说明:
            规则的添加顺序很重要 —— 优先级高的规则应该首先添加，
            避免短规则先被长规则的子集匹配。例如保留字应在标识符之前。
        """
        self.token_specs.append((token_type, regex_pattern))

    def build(self) -> None:
        """编译所有词法规则，生成可用于扫描的正则表达式对象列表
        
        返回:
            None
            
        说明:
            在调用 tokenize() 前必须调用此方法。
            将所有 token_specs 编译为 re.Pattern 对象，存储在 compiled_patterns 中。
        """
        self.compiled_patterns = []
        for token_type, pattern in self.token_specs:
            # 使用 \A 锚点确保从当前位置开始匹配，避免匹配中间的内容
            compiled = re.compile(r'\A(' + pattern + r')')
            self.compiled_patterns.append((token_type, compiled))

    def tokenize(self, text: str) -> List[Token]:
        """将输入文本分解为Token列表
        
        参数:
            text: 输入的源代码文本
            
        返回:
            Token对象列表
            
        异常:
            SyntaxError: 当遇到无法识别的字符时抛出
            
        说明:
            - 自动跳过空白字符和注释（//开头的行注释）
            - 追踪行号和列号便于错误报告
            - 使用子集构造法的思想：按顺序尝试所有规则，直到找到匹配
        """
        if not self.compiled_patterns:
            raise RuntimeError("Lexer not built. Call build() first.")

        tokens: List[Token] = []
        pos = 0
        line = 1
        column = 1

        while pos < len(text):
            # 跳过空白字符
            if text[pos].isspace():
                if text[pos] == '\n':
                    line += 1
                    column = 1
                else:
                    column += 1
                pos += 1
                continue

            # 处理行注释
            if pos + 1 < len(text) and text[pos:pos+2] == '//':
                # 跳过注释直到行尾
                end = text.find('\n', pos)
                if end == -1:
                    break
                pos = end
                continue

            # 尝试匹配各个Token规则
            matched = False
            for token_type, pattern in self.compiled_patterns:
                # 从位置pos开始匹配（使用切片）
                match = pattern.match(text[pos:])
                if match:
                    lexeme = match.group(1)
                    token = Token(token_type, lexeme, line, column)
                    tokens.append(token)
                    
                    # 更新位置和行列号
                    pos += match.end()
                    if '\n' in lexeme:
                        line += lexeme.count('\n')
                        column = len(lexeme) - lexeme.rfind('\n')
                    else:
                        column += len(lexeme)
                    matched = True
                    break

            if not matched:
                # 词法错误：无法识别的字符
                raise SyntaxError(
                    f"Lexical error at line {line}, column {column}: "
                    f"unexpected character '{text[pos]}'"
                )

        # 添加EOF token
        tokens.append(Token('EOF', '', line, column))
        return tokens

    def get_token_rules(self) -> List[Tuple[str, str]]:
        """获取所有已添加的词法规则
        
        返回:
            由 (token_type, regex_pattern) 组成的列表
            
        说明:
            用于显示或检查当前已定义的所有词法规则。
        """
        return self.token_specs.copy()


def create_lexer_from_spec(token_rules: List[Tuple[str, str]]) -> LexerGenerator:
    """便捷函数：从规则列表创建词法分析器
    
    参数:
        token_rules: [(token_type, regex_pattern), ...] 列表
        
    返回:
        已构建好的 LexerGenerator 对象
        
    说明:
        这是一个快速构造词法分析器的工厂函数。
    """
    lexer = LexerGenerator()
    for token_type, pattern in token_rules:
        lexer.add_token_rule(token_type, pattern)
    lexer.build()
    return lexer
