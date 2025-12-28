#!/usr/bin/env python3
# =============================================================================
# 自动生成的编译器 (LL(1) 优化版)
# 生成时间: 2025-12-17 17:33:50
# =============================================================================

import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Optional

# --- 词法分析器部分 ---

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


# --- 语法分析器部分 ---

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
                ['VarDecl', 'DeclListTail'],
                [],
            ],
            'DeclListTail': [
                ['VarDecl', 'DeclListTail'],
                [],
            ],
            'VarDecl': [
                ["'VAR'", 'IDList', "'SEMI'"],
            ],
            'IDList': [
                ["'ID'", 'IDListTail'],
            ],
            'IDListTail': [
                ["'COMMA'", "'ID'", 'IDListTail'],
                [],
            ],
            'StmtList': [
                ['Stmt', 'StmtListTail'],
            ],
            'StmtListTail': [
                ['Stmt', 'StmtListTail'],
                [],
            ],
            'Stmt': [
                ['AssignStmt'],
                ['Block'],
                ['IfStmt'],
                ['ReadStmt'],
                ['WhileStmt'],
                ['WriteStmt'],
            ],
            'AssignStmt': [
                ["'ID'", "'ASSIGN'", 'Expr', "'SEMI'"],
            ],
            'IfStmt': [
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
                ["'EQ'"],
                ["'GE'"],
                ["'GT'"],
                ["'LE'"],
                ["'LT'"],
                ["'NE'"],
            ],
            'Expr': [
                ['Term', 'ExprTail'],
            ],
            'ExprTail': [
                ["'MINUS'", 'Term', 'ExprTail'],
                ["'PLUS'", 'Term', 'ExprTail'],
                [],
            ],
            'Term': [
                ['Factor', 'TermTail'],
            ],
            'TermTail': [
                ["'DIV'", 'Factor', 'TermTail'],
                ["'MUL'", 'Factor', 'TermTail'],
                [],
            ],
            'Factor': [
                ["'LPAREN'", 'Expr', "'RPAREN'"],
                ["'ID'"],
                ["'NUM'"],
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
# 异常定义
# =============================================================================

class CompilationError(Exception):
    """编译过程中的自定义错误"""
    pass

# =============================================================================
# 代码生成器
# =============================================================================

class CodeGenerator:
    def __init__(self):
        self.code_list = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self):
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self):
        self.label_counter += 1
        return f"L{self.label_counter}"

    def generate(self, ast):
        self.code_list = []
        self.temp_counter = 0
        self.label_counter = 0
        self._traverse(ast)
        return self.code_list

    def _traverse(self, node):
        if not node: return None

        # 1. 结构性节点处理 (Program / StmtList)
        if node.name in ['Program', 'StmtList'] or "StmtList_LF_TAIL" in node.name:
            # 递归处理所有子节点
            for child in node.children:
                self._traverse(child)
            return None
        
        # 1.5 表达式尾部处理 (Expr_LF_TAIL / Term_LF_TAIL / AddOp_LF_TAIL 等)
        if "_LF_TAIL" in node.name and "StmtList" not in node.name:
            if not node.children:
                return None
            return self._handle_tail_recursive(node)

        # 2. 表达式处理 (Expr / Term)
        if node.name in ['Expr', 'Expression', 'Term']:
            left_val = self._traverse(node.children[0])
            if len(node.children) > 1:
                return self._handle_tail_recursive(node.children[1], left_val)
            return left_val

        # 3. 语句处理
        elif node.name == 'Stmt' or node.name == 'Statement':
            if not node.children: return None
            first_child = node.children[0]

            # 赋值语句 ID = Expr ;
            if first_child.name == "'ID'":
                var_name = first_child.token.value if first_child.token else "var"
                val = self._traverse(node.children[2])
                self.code_list.append(f"{var_name} = {val}")
                return None

            # 打印语句 PRINT ( Expr ) ; (严格三地址码)
            elif first_child.name == "'PRINT'":
                val = self._traverse(node.children[2])
                if val:
                    self.code_list.append(f"param {val}")
                    self.code_list.append(f"call print, 1")
                return None

            # PL/0格式: 转发给具体语句类型(AssignStmt/WriteStmt等)
            else:
                return self._traverse(first_child)

        # 4. AssignStmt: ID ASSIGN Expr SEMI
        elif node.name == 'AssignStmt':
            if len(node.children) >= 3:
                var_name = node.children[0].token.value if node.children[0].token else "var"
                val = self._traverse(node.children[2])
                if val:
                    self.code_list.append(f"{var_name} = {val}")
            return None

        # 5. WriteStmt: WRITE ( Expr ) SEMI
        elif node.name == 'WriteStmt':
            if len(node.children) >= 3:
                val = self._traverse(node.children[2])
                if val:
                    self.code_list.append(f"param {val}")
                    self.code_list.append(f"call write, 1")
            return None

        # 6. ReadStmt: READ ID SEMI
        elif node.name == 'ReadStmt':
            if len(node.children) >= 2:
                var_name = node.children[1].token.value if node.children[1].token else "var"
                temp = self.new_temp()
                self.code_list.append(f"{temp} = call read, 0")
                self.code_list.append(f"{var_name} = {temp}")
            return None

        # 7. WhileStmt: WHILE ( BoolExpr ) Stmt
        elif node.name == 'WhileStmt':
            if len(node.children) >= 5:
                loop_label = self.new_label()
                exit_label = self.new_label()
                self.code_list.append(f"{loop_label}:")
                bool_result = self._traverse(node.children[2])
                if bool_result:
                    temp = self.new_temp()
                    self.code_list.append(f"{temp} = not {bool_result}")
                    self.code_list.append(f"if {temp} goto {exit_label}")
                self._traverse(node.children[4])
                self.code_list.append(f"goto {loop_label}")
                self.code_list.append(f"{exit_label}:")
            return None

        # 8. IfStmt: IF ( BoolExpr ) Stmt
        elif node.name == 'IfStmt':
            if len(node.children) >= 5:
                exit_label = self.new_label()
                bool_result = self._traverse(node.children[2])
                if bool_result:
                    temp = self.new_temp()
                    self.code_list.append(f"{temp} = not {bool_result}")
                    self.code_list.append(f"if {temp} goto {exit_label}")
                self._traverse(node.children[4])
                self.code_list.append(f"{exit_label}:")
            return None

        # 9. Block: LBRACE StmtList RBRACE
        elif node.name == 'Block':
            if len(node.children) >= 2:
                self._traverse(node.children[1])
            return None

        # 10. BoolExpr: Expr RelOp Expr
        elif node.name == 'BoolExpr':
            if len(node.children) >= 3:
                e1 = self._traverse(node.children[0])
                op = self._traverse(node.children[1])
                e2 = self._traverse(node.children[2])
                if e1 and op and e2:
                    temp = self.new_temp()
                    self.code_list.append(f"{temp} = {e1} {op} {e2}")
                    return temp
            return None

        # 11. RelOp
        elif node.name == 'RelOp':
            if node.children:
                return self._traverse(node.children[0])
            return None

        # 12. 变量声明(忽略)
        elif node.name in ['VarDecl', 'IDList', 'DeclList', 'DeclListTail', 'IDListTail']:
            return None

        # 13. 因子处理 (Factor)
        elif node.name == 'Factor':
            if not node.children:
                return None
            if node.children[0].name == "'LPAREN'":
                return self._traverse(node.children[1])
            return self._traverse(node.children[0])

        # 14. 终端节点
        if node.token:
            return node.token.value

        # 默认递归
        result = None
        for child in node.children:
            result = self._traverse(child)
        return result

    def _handle_tail_recursive(self, tail_node, left_val=None):
        """递归处理优化后的右深嵌套 AST，生成符合左结合的三地址码"""
        if not tail_node or not tail_node.children:
            return left_val

        first_child = tail_node.children[0]
        
        # 情况1: PL/0格式 - ExprTail -> 'PLUS' Term ExprTail
        # 第一个子节点直接是操作符终端节点
        if first_child.token and first_child.token.value in ['+', '-', '*', '/']:
            op_symbol = first_child.token.value
            if len(tail_node.children) < 2:
                return left_val
            right_val = self._traverse(tail_node.children[1])
            target = self.new_temp()
            self.code_list.append(f"{target} = {left_val} {op_symbol} {right_val}")
            if len(tail_node.children) > 2:
                return self._handle_tail_recursive(tail_node.children[2], target)
            return target
        
        # 情况2: simple_expr格式 - Expr_LF_TAIL -> AddOp Term ...
        # 第一个子节点是AddOp/MulOp组节点
        op_group = first_child
        if not op_group.children:
            return left_val

        op_node = op_group.children[0]
        if not op_node.token:
            return left_val
        op_symbol = op_node.token.value
        
        if len(op_group.children) < 2:
            return left_val
        right_operand_node = op_group.children[1]
        right_val = self._traverse(right_operand_node)

        target = self.new_temp()
        self.code_list.append(f"{target} = {left_val} {op_symbol} {right_val}")

        if len(op_group.children) > 2:
            return self._handle_tail_recursive(op_group.children[2], target)
        if len(tail_node.children) > 1:
            return self._handle_tail_recursive(tail_node.children[1], target)

        return target

# =============================================================================
# 编译器入口封装
# =============================================================================

class GeneratedCompiler:
    def __init__(self):
        self.lexer = GeneratedLexer() 
        self.parser = GeneratedParser()
        self.codegen = CodeGenerator()

    def compile(self, source_code: str) -> List[str]:
        tokens = self.lexer.tokenize(source_code)
        ast = self.parser.parse(tokens)
        return self.codegen.generate(ast)

    def compile_file(self, input_file: str, output_file: str):
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            code = self.compile(source_code)
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in code:
                    f.write(line + '\n')
            print(f"[成功] 编译完成 -> {output_file}")
        except Exception as e:
            print(f"[错误] {str(e)}")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="自动生成的编译器")
    arg_parser.add_argument("input", help="输入文件")
    arg_parser.add_argument("-o", "--output", default="output.3ac", help="输出文件")

    args = arg_parser.parse_args()
    compiler = GeneratedCompiler()
    compiler.compile_file(args.input, args.output)
