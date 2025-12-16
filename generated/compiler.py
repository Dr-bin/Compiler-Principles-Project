#!/usr/bin/env python3
# =============================================================================
# 自动生成的编译器
# 生成时间: 2025-12-16 23:43:13
# =============================================================================

import sys
import argparse
from typing import List, Optional

# =============================================================================
# 编译错误异常类
# =============================================================================

class CompilationError(Exception):
    """编译错误异常"""
    pass


# =============================================================================
# 自动生成的词法分析器
# =============================================================================

import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Token:
    """Token数据结构"""
    type: str
    value: str
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, {self.line}, {self.column})"

class GeneratedLexer:
    """自动生成的词法分析器"""
    
    def __init__(self):
        self.token_specs = [
            ('VAR', r'var'),
            ('WHILE', r'while'),
            ('IF', r'if'),
            ('ELSE', r'else'),
            ('READ', r'read'),
            ('WRITE', r'write'),
            ('AND', r'and'),
            ('OR', r'or'),
            ('NOT', r'not'),
            ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('NUM', r'[0-9]+'),
            ('ASSIGN', r'='),
            ('PLUS', r'\+'),
            ('MINUS', r'-'),
            ('MUL', r'\*'),
            ('DIV', r'/'),
            ('MOD', r'%'),
            ('LT', r'<'),
            ('LE', r'<='),
            ('GT', r'>'),
            ('GE', r'>='),
            ('EQ', r'=='),
            ('NE', r'<>'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('LBRACE', r'\{'),
            ('RBRACE', r'\}'),
            ('SEMI', r';'),
            ('COMMA', r','),
        ]
        self.compiled_patterns = [(name, re.compile(pattern)) for name, pattern in self.token_specs]
    
    def tokenize(self, text: str) -> List[Token]:
        """词法分析"""
        tokens = []
        line = 1
        column = 1
        position = 0
        
        while position < len(text):
            # 跳过空白符
            if text[position].isspace():
                if text[position] == '\n':
                    line += 1
                    column = 1
                else:
                    column += 1
                position += 1
                continue
            
            # 跳过注释（//开头）
            if position + 1 < len(text) and text[position:position+2] == '//':
                while position < len(text) and text[position] != '\n':
                    position += 1
                continue
            
            # 匹配token（最长匹配）
            matched = False
            max_len = 0
            matched_type = None
            matched_value = None
            
            for token_type, pattern in self.compiled_patterns:
                match = pattern.match(text, position)
                if match:
                    match_len = match.end() - match.start()
                    if match_len > max_len:
                        max_len = match_len
                        matched_type = token_type
                        matched_value = match.group()
                        matched = True
            
            if matched:
                tokens.append(Token(matched_type, matched_value, line, column))
                position += max_len
                column += max_len
            else:
                raise SyntaxError(f"词法错误 行{line} 列{column}: 无法识别 '{text[position]}'")
        
        tokens.append(Token('EOF', '', line, column))
        return tokens



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
        result = f"{prefix}{self.name}"
        if self.token:
            result += f" ('{self.token.value}')"
        result += "\n"
        for child in self.children:
            result += child.__repr__(indent + 1)
        return result

class GeneratedParser:
    """自动生成的语法分析器"""
    
    def __init__(self):
        self.tokens = []
        self.pos = 0
        self.grammar = {
            'Program': [
                ['DeclList', 'StmtList'],
            ],
            'DeclList': [
                ['VarDecl', 'DeclList'],
                ['VarDecl'],
                [],
            ],
            'VarDecl': [
                ["'VAR'", 'IDList', "'SEMI'"],
            ],
            'IDList': [
                ["'ID'", "'COMMA'", 'IDList'],
                ["'ID'"],
            ],
            'StmtList': [
                ['Stmt', 'StmtList'],
                ['Stmt'],
            ],
            'Stmt': [
                ['AssignStmt'],
                ['IfStmt'],
                ['WhileStmt'],
                ['ReadStmt'],
                ['WriteStmt'],
                ['Block'],
            ],
            'AssignStmt': [
                ["'ID'", "'ASSIGN'", 'Expr', "'SEMI'"],
            ],
            'IfStmt': [
                ["'IF'", "'LPAREN'", 'BoolExpr', "'RPAREN'", 'Stmt', "'ELSE'", 'Stmt'],
                ["'IF'", "'LPAREN'", 'BoolExpr', "'RPAREN'", 'Stmt'],
            ],
            'WhileStmt': [
                ["'WHILE'", "'LPAREN'", 'BoolExpr', "'RPAREN'", 'Stmt'],
            ],
            'ReadStmt': [
                ["'READ'", "'ID'", "'SEMI'"],
            ],
            'WriteStmt': [
                ["'WRITE'", "'LPAREN'", 'Expr', "'RPAREN'", "'SEMI'"],
            ],
            'Block': [
                ["'LBRACE'", 'StmtList', "'RBRACE'"],
            ],
            'BoolExpr': [
                ['Expr', 'RelOp', 'Expr'],
            ],
            'RelOp': [
                ["'LT'"],
                ["'LE'"],
                ["'GT'"],
                ["'GE'"],
                ["'EQ'"],
                ["'NE'"],
            ],
            'Expr': [
                ['Term', "'PLUS'", 'Expr'],
                ['Term', "'MINUS'", 'Expr'],
                ['Term'],
            ],
            'Term': [
                ['Factor', "'MUL'", 'Term'],
                ['Factor', "'DIV'", 'Term'],
                ['Factor'],
            ],
            'Factor': [
                ["'LPAREN'", 'Expr', "'RPAREN'"],
                ["'NUM'"],
                ["'ID'"],
            ],
        }
        self.start_symbol = 'Program'
    
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
            f"语法错误: 第{token.line}行, 第{token.column}列\n"
            f"  期望: {token_type}\n"
            f"  实际: {token.type} (值: '{token.value}')"
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
                f"语法错误: 第{current.line}行, 第{current.column}列\n"
                f"  无法解析非终结符 '{symbol}'\n"
                f"  当前token: {current.type} (值: '{current.value}')\n"
                f"  期望的token类型: {expected_str}"
            )
        
        # 直接匹配token类型
        if self.current_token().type == symbol:
            token = self.advance()
            return ASTNode(name=symbol, token=token)
        
        raise SyntaxError(f"未知符号: {symbol}")
    
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
                f"语法错误: 第{current.line}行, 第{current.column}列\n"
                f"  解析未完成，仍有未处理的token\n"
                f"  剩余token: {current.type} (值: '{current.value}')"
            )
        return ast


# =============================================================================
# 代码生成器
# =============================================================================

class CodeGenerator:
    """代码生成器 - 从AST生成三地址码"""
    
    def __init__(self):
        self.code_list = []
        self.temp_counter = 0
    
    def new_temp(self):
        self.temp_counter += 1
        return f"t{self.temp_counter}"
    
    def generate(self, ast):
        """从AST生成三地址码"""
        self._traverse(ast)
        return self.code_list
    
    def _traverse(self, node):
        if not node:
            return None
        
        # 程序和语句列表
        if node.name in ['Program', 'StmtList']:
            for child in node.children:
                self._traverse(child)
            return None
        
        # 语句
        elif node.name == 'Stmt':
            # 赋值语句: ID = Expr ;
            if len(node.children) >= 4 and node.children[0].name == "'ID'":
                var_name = node.children[0].token.value
                expr_value = self._traverse(node.children[2])
                if var_name and expr_value:
                    self.code_list.append(f"{var_name} = {expr_value}")
            # print语句
            elif len(node.children) >= 5 and node.children[0].name == "'PRINT'":
                expr_value = self._traverse(node.children[2])
                if expr_value:
                    self.code_list.append(f"print({expr_value})")
            return None
        
        # 表达式
        elif node.name == 'Expr':
            if len(node.children) == 1:
                return self._traverse(node.children[0])
            elif len(node.children) >= 2:
                result = self._traverse(node.children[0])
                for child in node.children[1:]:
                    if child.name == 'AddOp':
                        result = self._handle_addop(child, result)
                return result
        
        # 项
        elif node.name == 'Term':
            if len(node.children) == 1:
                return self._traverse(node.children[0])
            elif len(node.children) >= 2:
                result = self._traverse(node.children[0])
                for child in node.children[1:]:
                    if child.name == 'MulOp':
                        result = self._handle_mulop(child, result)
                return result
        
        # 因子
        elif node.name == 'Factor':
            if len(node.children) == 1:
                return self._traverse(node.children[0])
            elif len(node.children) >= 3:
                return self._traverse(node.children[1])
        
        # 终结符
        elif node.name in ['NUM', 'ID'] or (node.name.startswith("'") and node.name.endswith("'")):
            if node.token:
                return node.token.value
        
        return None
    
    def _handle_addop(self, node, left):
        if len(node.children) >= 2:
            op = node.children[0].token.value
            right = self._traverse(node.children[1])
            temp = self.new_temp()
            self.code_list.append(f"{temp} = {left} {op} {right}")
            if len(node.children) >= 3:
                return self._handle_addop(node.children[2], temp)
            return temp
        return left
    
    def _handle_mulop(self, node, left):
        if len(node.children) >= 2:
            op = node.children[0].token.value
            right = self._traverse(node.children[1])
            temp = self.new_temp()
            self.code_list.append(f"{temp} = {left} {op} {right}")
            if len(node.children) >= 3:
                return self._handle_mulop(node.children[2], temp)
            return temp
        return left

# =============================================================================
# 主程序
# =============================================================================

class GeneratedCompiler:
    """生成的编译器主类"""
    
    def __init__(self):
        self.lexer = GeneratedLexer()
        self.parser = GeneratedParser()
        self.codegen = CodeGenerator()
    
    def compile(self, source_code: str) -> List[str]:
        """编译源代码"""
        # 词法分析
        try:
            tokens = self.lexer.tokenize(source_code)
        except SyntaxError as e:
            raise CompilationError(f"词法错误: {str(e)}")
        except Exception as e:
            raise CompilationError(f"词法分析失败: {str(e)}")
        
        # 语法分析
        try:
            ast = self.parser.parse(tokens)
        except SyntaxError as e:
            raise CompilationError(f"语法错误: {str(e)}")
        except Exception as e:
            raise CompilationError(f"语法分析失败: {str(e)}")
        
        # 代码生成
        try:
            code = self.codegen.generate(ast)
        except Exception as e:
            raise CompilationError(f"代码生成失败: {str(e)}")
        
        return code
    
    def compile_file(self, input_file: str, output_file: str):
        """编译文件"""
        print(f"[编译] 开始编译: {input_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"[错误] 文件不存在: {input_file}")
            sys.exit(1)
        except Exception as e:
            print(f"[错误] 读取文件失败: {str(e)}")
            sys.exit(1)
        
        try:
            code = self.compile(source_code)
        except CompilationError as e:
            print(f"\n======================================================================")
            print(f"[错误] 编译失败")
            print(f"======================================================================")
            print(f"{str(e)}")
            print(f"======================================================================\n")
            sys.exit(1)
        except Exception as e:
            print(f"\n[错误] 编译过程出现异常: {str(e)}")
            sys.exit(1)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in code:
                    f.write(line + '\n')
        except Exception as e:
            print(f"[错误] 写入输出文件失败: {str(e)}")
            sys.exit(1)
        
        print(f"[成功] 编译完成: {output_file}")
        print(f"[统计] 生成 {len(code)} 条三地址码")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动生成的编译器")
    parser.add_argument("input", help="输入源代码文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出三地址码文件路径")
    
    args = parser.parse_args()
    
    compiler = GeneratedCompiler()
    compiler.compile_file(args.input, args.output)
