"""规则文件解析器

从文本文件中解析词法规则和语法规则。
支持标准的正则表达式和BNF文法格式。
"""

from typing import Dict, List, Tuple, Any
import re


class RuleParser:
    """规则文件解析器
    
    解析词法规则文件和语法规则文件，提取词法/语法定义。
    """

    def __init__(self):
        """初始化规则解析器"""
        pass

    @staticmethod
    def parse_lexer_rules(filename: str) -> List[Tuple[str, str]]:
        """解析词法规则文件
        
        参数:
            filename: 词法规则文件的路径
            
        返回:
            [(token_type, regex_pattern), ...] 列表
            
        文件格式说明:
            每行一个规则，格式为: TOKEN_TYPE = regex_pattern
            # 开头的行为注释
            空行被忽略
            
        示例:
            ID = [a-zA-Z_][a-zA-Z0-9_]*
            NUM = [0-9]+
            PLUS = \\+
            MINUS = -
        """
        rules = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析规则行
                if '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        token_type = parts[0].strip()
                        pattern = parts[1].strip()
                        rules.append((token_type, pattern))

        return rules

    @staticmethod
    def parse_grammar_rules(filename: str) -> Tuple[Dict[str, List[List[str]]], Dict[str, any]]:
        """解析语法规则文件
        
        参数:
            filename: 语法规则文件的路径
            
        返回:
            (grammar, metadata) 元组
            - grammar: 语法规则字典 {nonterminal: [[production1], [production2], ...]}
            - metadata: 元数据字典，包含语言特性配置
            
        文件格式说明:
            使用BNF形式：
            - 每条产生式占一行
            - 左侧非终结符后跟 ->
            - 右侧为符号序列，用空格分隔
            - 同一非终结符的多条产生式用 | 分隔
            - 终结符用引号包围（如 'if', '+'）
            - 非终结符直接写名字
            
            元数据注释格式：
            - # @REQUIRE_EXPLICIT_DECLARATION: true/false
            - 用于声明语言特性
            
        示例:
            # @REQUIRE_EXPLICIT_DECLARATION: true
            Expr -> Term
            Expr -> Term '+' Expr
            Term -> Factor
            Term -> Factor '*' Term
            Factor -> 'NUM' | 'ID' | '(' Expr ')'
        """
        grammar = {}
        metadata = {
            'require_explicit_declaration': None  # None表示未指定，需要自动检测
        }
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 跳过空行
                if not line:
                    continue
                
                # 解析元数据注释（格式：@KEY: VALUE）
                if line.startswith('# @'):
                    # 移除 # 和 @
                    meta_line = line[3:].strip()
                    if ':' in meta_line:
                        key, value = meta_line.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip().lower()
                        
                        if key == 'require_explicit_declaration':
                            metadata['require_explicit_declaration'] = value in ('true', '1', 'yes')
                
                # 跳过普通注释
                elif line.startswith('#'):
                    continue
                
                # 解析产生式行
                elif '->' in line:
                    parts = line.split('->', 1)
                    if len(parts) == 2:
                        nonterminal = parts[0].strip()
                        rhs = parts[1].strip()
                        
                        # 处理多个产生式 (使用 | 分隔)
                        alternatives = rhs.split('|')
                        
                        if nonterminal not in grammar:
                            grammar[nonterminal] = []
                        
                        for alt in alternatives:
                            alt = alt.strip()
                            # 将符号序列分解为列表
                            symbols = RuleParser._parse_symbols(alt)
                            grammar[nonterminal].append(symbols)
        
        # 如果未明确指定，自动检测：如果语法中有VarDecl或IDList，则需要显式声明
        if metadata['require_explicit_declaration'] is None:
            has_var_decl = 'VarDecl' in grammar or 'IDList' in grammar
            # 或者检查产生式中是否包含VarDecl或IDList
            if not has_var_decl:
                for prods in grammar.values():
                    for prod in prods:
                        if 'VarDecl' in prod or 'IDList' in prod:
                            has_var_decl = True
                            break
                    if has_var_decl:
                        break
            metadata['require_explicit_declaration'] = has_var_decl

        return grammar, metadata

    @staticmethod
    def _parse_symbols(rhs: str) -> List[str]:
        """解析产生式右侧，提取符号列表
        
        参数:
            rhs: 产生式右侧的字符串
            
        返回:
            符号列表
            
        说明:
            处理带引号的终结符和不带引号的非终结符。
            示例: "Term '+' Expr" -> ['Term', "'+'", 'Expr']
        """
        symbols = []
        i = 0
        current = ""
        
        while i < len(rhs):
            # 处理带引号的终结符
            if rhs[i] == "'":
                # 找到匹配的右引号
                j = i + 1
                while j < len(rhs) and rhs[j] != "'":
                    j += 1
                if j < len(rhs):
                    symbols.append(rhs[i:j+1])  # 包括引号
                    i = j + 1
                else:
                    i += 1
            # 处理空白
            elif rhs[i].isspace():
                if current:
                    symbols.append(current)
                    current = ""
                i += 1
            # 处理非终结符
            else:
                current += rhs[i]
                i += 1
        
        if current:
            symbols.append(current)
        
        return symbols

    @staticmethod
    def validate_grammar(grammar: Dict[str, List[List[str]]]) -> bool:
        """验证语法规则的有效性
        
        参数:
            grammar: 语法规则字典
            
        返回:
            True 如果语法有效，False 否则
            
        说明:
            检查是否所有引用的非终结符都有定义。
        """
        defined_symbols = set(grammar.keys())
        
        for nonterminal, productions in grammar.items():
            for production in productions:
                for symbol in production:
                    # 移除引号检查非终结符
                    clean_symbol = symbol.strip("'")
                    
                    # 如果符号不是终结符（没有引号），应该在定义中
                    if not symbol.startswith("'"):
                        if clean_symbol not in defined_symbols:
                            print(f"Warning: Undefined symbol '{clean_symbol}' in production for '{nonterminal}'")
        
        return True


def load_rules_from_files(lexer_file: str, grammar_file: str) -> Tuple[List[Tuple[str, str]], Dict[str, List[List[str]]], Dict[str, Any]]:
    """便捷函数：从文件加载词法规则和语法规则
    
    参数:
        lexer_file: 词法规则文件路径
        grammar_file: 语法规则文件路径
        
    返回:
        (lexer_rules, grammar_rules, metadata) 的元组
        
    说明:
        一次性加载完整的语言定义，包括元数据。
    """
    lexer_rules = RuleParser.parse_lexer_rules(lexer_file)
    grammar_rules, metadata = RuleParser.parse_grammar_rules(grammar_file)
    
    return lexer_rules, grammar_rules, metadata
