"""代码生成器 (同学C负责)

该模块实现从抽象语法树(AST)生成中间代码(三地址码)或目标代码的功能。
使用语法制导翻译(Syntax-Directed Translation)技术。
"""

from typing import  Dict, Optional, Any
from src.compiler_generator.parser_generator import ASTNode

class CodeGenerator:
    """代码生成器类

    从AST生成中间代码（三地址码）。
    支持简单的表达式、赋值语句等。
    """

    def __init__(self):
        """初始化代码生成器

        属性说明:
            code_list: 生成的中间代码指令列表
            temp_counter: 临时变量计数器（用于生成 t1, t2, ...）
            label_counter: 标签计数器（用于跳转）
            symbol_table: 符号表，记录变量信息
        """
        self.code_list: List[str] = []
        self.temp_counter: int = 0
        self.label_counter: int = 0
        self.symbol_table: Dict[str, Dict[str, Any]] = {}

    def new_temp(self) -> str:
        """生成一个新的临时变量名称

        返回:
            临时变量名称，格式为 t1, t2, t3, ...
        """
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self) -> str:
        """生成一个新的标签名称

        返回:
            标签名称，格式为 L1, L2, L3, ...
        """
        self.label_counter += 1
        return f"L{self.label_counter}"

    def emit(self, op: str, arg1: str = "", arg2: str = "", result: str = "") -> None:
        """发出一条三地址码指令

        生成的指令格式：result = arg1 op arg2
        """
        if result:
            instruction = f"{result} = {arg1} {op} {arg2}".strip()
        else:
            instruction = f"{op} {arg1} {arg2}".strip()

        self.code_list.append(instruction)

    def add_symbol(self, name: str, var_type: str = "int", value: Any = None) -> None:
        """将一个符号（变量）添加到符号表"""
        self.symbol_table[name] = {
            'type': var_type,
            'value': value,
            'defined': False
        }

    def lookup_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """查找符号表中的一个符号"""
        return self.symbol_table.get(name)

    def generate_from_ast(self, node: ASTNode) -> str:
        """从AST生成中间代码的主方法"""
        self._traverse_ast(node)
        return self.get_code()

    def _handle_tail_recursive(self, tail_node: ASTNode, left_val: str) -> str:
        """
        递归处理优化后的右深嵌套 AST，生成符合左结合的三地址码。
        适用于加减法(Expr_LF_TAIL)和乘除法(Term_LF_TAIL)。
        """
        if not tail_node or not tail_node.children:
            return left_val

        # 结构通常为: [Op_Node, Next_Operand, Optional_Further_Tail]
        # 1. 提取操作符和右操作数
        op_group_node = tail_node.children[0]

        # 兼容性处理：如果 op 节点本身还有子节点(如 AddOp -> '+' Term)
        if op_group_node.children:
            op_symbol = op_group_node.children[0].token.value
            right_val = self._traverse_ast(op_group_node.children[1])

            # 生成临时变量存放计算结果
            target = self.new_temp()
            self.emit(op_symbol, left_val, right_val, target)

            # 2. 检查 Op_Node 内部是否带有递归尾部
            if len(op_group_node.children) > 2:
                return self._handle_tail_recursive(op_group_node.children[2], target)

            # 3. 检查 Tail_Node 本身是否带有递归尾部
            if len(tail_node.children) > 1:
                return self._handle_tail_recursive(tail_node.children[1], target)

            return target

        return left_val

    def _traverse_ast(self, node: ASTNode) -> Optional[str]:
        """递归遍历AST并生成代码"""
        if not node:
            return None

        # 1. 程序与列表逻辑
        if node.name in ['Program', 'StmtList', 'StmtList_LF_TAIL_0']:
            for child in node.children:
                self._traverse_ast(child)
            return None

        # 2. 语句处理：赋值 ID = Expr ; 或 PRINT ( Expr ) ;
        elif node.name == 'Stmt' or node.name == 'Statement':
            if not node.children: return None

            first_child = node.children[0]
            # 识别赋值语句 (第一个孩子是 ID)
            if first_child.name == "'ID'":
                var_name = first_child.token.value if first_child.token else ""
                expr_value = self._traverse_ast(node.children[2])
                if var_name and expr_value:
                    self.code_list.append(f"{var_name} = {expr_value}")
                    self.add_symbol(var_name)
            # 识别打印语句 (第一个孩子是 PRINT) - 严格三地址码
            elif first_child.name == "'PRINT'":
                expr_value = self._traverse_ast(node.children[2])
                if expr_value:
                    self.code_list.append(f"param {expr_value}")
                    self.code_list.append(f"call print, 1")
            return None

        # 3. 表达式处理 (Expr 和 Term 结构在 LL1 下是一致的)
        elif node.name in ['Expr', 'Expression', 'Term']:
            # 第一个孩子永远是左操作数 (Term 或 Factor)
            left_val = self._traverse_ast(node.children[0])
            # 第二个孩子是 _LF_TAIL 节点
            if len(node.children) > 1:
                return self._handle_tail_recursive(node.children[1], left_val)
            return left_val

        # 4. 因子处理 (数字、标识符、括号)
        elif node.name == 'Factor':
            if not node.children: return None
            # 处理 ( Expr )
            if node.children[0].name == "'LPAREN'":
                return self._traverse_ast(node.children[1])
            # 处理 ID 或 NUM
            return self._traverse_ast(node.children[0])

        # 5. 终端节点处理
        elif node.name in ['NUM', 'ID'] or (node.name.startswith("'") and node.name.endswith("'")):
            if node.token:
                return node.token.value
            return None

        # 默认递归处理
        else:
            result = None
            for child in node.children:
                result = self._traverse_ast(child)
            return result

    def get_code(self) -> str:
        """获取生成的中间代码"""
        return '\n'.join(self.code_list)

    def print_symbol_table(self) -> str:
        """打印符号表的内容"""
        result = "=== Symbol Table ===\n"
        for name, info in self.symbol_table.items():
            result += f"{name}: {info}\n"
        return result

    def reset(self) -> None:
        """重置代码生成器状态"""
        self.code_list = []
        self.temp_counter = 0
        self.label_counter = 0
        self.symbol_table = {}


from typing import List, Dict, Any
from datetime import datetime
from src.compiler_generator.parser_generator import ParserGenerator, generate_parser_code
import os


def _get_inline_error_formatter() -> str:
    """获取内联的 ErrorFormatter 代码（如果文件读取失败时使用）"""
    return '''from typing import List, Optional, Tuple
import os

class ErrorFormatter:
    """错误格式化器类"""
    
    def __init__(self, source_code: str = None, source_file: str = None):
        if source_file and os.path.exists(source_file):
            with open(source_file, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
            self.source_file = source_file
        else:
            self.source_code = source_code or ""
            self.source_file = source_file
        self.source_lines = self.source_code.split('\\n') if self.source_code else []
    
    def format_syntax_error(self, error_message: str, line: int, column: int, 
                           expected_tokens: List[str] = None) -> str:
        result = []
        result.append("=" * 70)
        result.append("[错误] 语法错误")
        result.append("=" * 70)
        result.append("")
        location = f"文件: {{self.source_file}}" if self.source_file else "源代码"
        result.append(f"[位置] {{location}}, 第 {{line}} 行, 第 {{column}} 列")
        result.append("")
        context_lines = 2
        start_line = max(1, line - context_lines)
        end_line = min(len(self.source_lines), line + context_lines)
        result.append("[源代码片段]:")
        result.append("-" * 70)
        for i in range(start_line, end_line + 1):
            line_num = str(i).rjust(4)
            line_content = self.source_lines[i - 1] if i <= len(self.source_lines) else ""
            if i == line:
                result.append(f">>> {{line_num}} | {{line_content}}")
                arrow = " " * (len(line_num) + 4) + " " * (column - 1) + "^" * max(1, len(line_content[column-1:column]) or 1)
                result.append(f"    {{arrow}}")
            else:
                result.append(f"    {{line_num}} | {{line_content}}")
        result.append("-" * 70)
        result.append("")
        result.append("[错误详情]:")
        result.append(f"   {{error_message}}")
        result.append("")
        if expected_tokens:
            result.append("[期望的符号类型]:")
            if len(expected_tokens) <= 5:
                result.append(f"   {{', '.join(expected_tokens)}}")
            else:
                result.append(f"   {{', '.join(expected_tokens[:5])}} ... (共 {{len(expected_tokens)}} 种类型)")
            result.append("")
        result.append("[建议]:")
        if expected_tokens:
            token_suggestions = {{
                'SEMI': '缺少分号 (;)',
                'RPAREN': '缺少右括号 ())',
                'LPAREN': '缺少左括号 (()',
                'NUM': '此处需要一个数字',
                'ID': '此处需要一个标识符（变量名）',
            }}
            for token in expected_tokens[:3]:
                if token in token_suggestions:
                    result.append(f"   - {{token_suggestions[token]}}")
        else:
            result.append("   - 请检查语法规则是否正确")
        result.append("")
        result.append("=" * 70)
        return "\\n".join(result)
    
    def format_lexical_error(self, error_message: str, line: int, column: int) -> str:
        result = []
        result.append("=" * 70)
        result.append("[错误] 词法错误")
        result.append("=" * 70)
        result.append("")
        location = f"文件: {{self.source_file}}" if self.source_file else "源代码"
        result.append(f"[位置] {{location}}, 第 {{line}} 行, 第 {{column}} 列")
        result.append("")
        context_lines = 2
        start_line = max(1, line - context_lines)
        end_line = min(len(self.source_lines), line + context_lines)
        result.append("[源代码片段]:")
        result.append("-" * 70)
        for i in range(start_line, end_line + 1):
            line_num = str(i).rjust(4)
            line_content = self.source_lines[i - 1] if i <= len(self.source_lines) else ""
            if i == line:
                result.append(f">>> {{line_num}} | {{line_content}}")
                arrow = " " * (len(line_num) + 4) + " " * (column - 1) + "^" * max(1, len(line_content[column-1:column]) or 1)
                result.append(f"    {{arrow}}")
            else:
                result.append(f"    {{line_num}} | {{line_content}}")
        result.append("-" * 70)
        result.append("")
        result.append(f"[错误详情] {{error_message}}")
        result.append("")
        result.append("=" * 70)
        return "\\n".join(result)
    
    def format_general_error(self, error_message: str, error_type: str = "Error") -> str:
        result = []
        result.append("=" * 70)
        result.append(f"[错误] {{error_type}}")
        result.append("=" * 70)
        result.append("")
        result.append(f"[错误详情] {{error_message}}")
        result.append("")
        result.append("=" * 70)
        return "\\n".join(result)
'''


def generate_compiler_code(lexer_code: str, grammar_rules: Dict, start_symbol: str, metadata: Dict = None) -> str:
    """生成完整的编译器代码
    
    参数:
        lexer_code: 词法分析器代码
        grammar_rules: 语法规则字典
        start_symbol: 开始符号
        metadata: 语言特性元数据（可选）
    """

    # --- 第一步：强制使用 ParserGenerator 优化文法并生成 Parser 代码 ---
    pg = ParserGenerator()
    pg.set_start_symbol(start_symbol)
    for nt, prods in grammar_rules.items():
        for p in prods:
            pg.add_production(nt, p)

    # 执行 LL(1) 转换（消除左递归、左公因子）
    pg.build_analysis_sets()

    # 获取优化后的文法和分析集合，传给 generate_parser_code 得到源码
    optimized_grammar = pg.grammar
    first_sets = pg.first_sets
    follow_sets = pg.follow_sets
    parser_code = generate_parser_code(optimized_grammar, start_symbol, first_sets, follow_sets, metadata=metadata)

    # --- 第二步：读取 ErrorFormatter 代码 ---
    error_formatter_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                        'src', 'utils', 'error_formatter.py')
    try:
        with open(error_formatter_path, 'r', encoding='utf-8') as f:
            error_formatter_code = f.read()
        # 移除文件开头的文档字符串，只保留类定义
        lines = error_formatter_code.split('\n')
        class_start = -1
        for i, line in enumerate(lines):
            if line.startswith('class ErrorFormatter'):
                class_start = i
                break
        
        if class_start >= 0:
            # 保留必要的导入和类定义
            error_formatter_code = '\n'.join([
                'from typing import List, Optional, Tuple',
                'import os',
                ''] + lines[class_start:])
    except Exception:
        # 如果读取失败，使用内联的简化版本
        error_formatter_code = _get_inline_error_formatter()

    # --- 第三步：生成编译器字符串 ---
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# 自动生成的编译器 (LL(1) 优化版)
# 生成时间: {current_time}
# =============================================================================

import sys
import argparse
import re
import io
import os
from dataclasses import dataclass, field
from typing import List, Optional

# --- 编码处理（Windows 兼容） ---
# 确保在 Windows 上也能正确显示 UTF-8 中文
if sys.platform == 'win32':
    try:
        # Python 3.7+ 支持 reconfigure
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        else:
            # Python 3.6 及以下版本，使用 TextIOWrapper
            if sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
            if sys.stderr.encoding != 'utf-8':
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        # 如果所有方法都失败，至少确保不会崩溃
        pass

# --- 错误格式化器部分 ---
{error_formatter_code}

# --- 词法分析器部分 ---
{lexer_code}

# --- 语法分析器部分 ---
{parser_code}

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
        return f"t{{self.temp_counter}}"

    def new_label(self):
        self.label_counter += 1
        return f"L{{self.label_counter}}"

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
                self.code_list.append(f"{{var_name}} = {{val}}")
                return None

            # 打印语句 PRINT ( Expr ) ; (严格三地址码)
            elif first_child.name == "'PRINT'":
                val = self._traverse(node.children[2])
                if val:
                    self.code_list.append(f"param {{val}}")
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
                    self.code_list.append(f"{{var_name}} = {{val}}")
            return None

        # 5. WriteStmt: WRITE ( Expr ) SEMI
        elif node.name == 'WriteStmt':
            if len(node.children) >= 3:
                val = self._traverse(node.children[2])
                if val:
                    self.code_list.append(f"param {{val}}")
                    self.code_list.append(f"call write, 1")
            return None

        # 6. ReadStmt: READ ID SEMI
        elif node.name == 'ReadStmt':
            if len(node.children) >= 2:
                var_name = node.children[1].token.value if node.children[1].token else "var"
                temp = self.new_temp()
                self.code_list.append(f"{{temp}} = call read, 0")
                self.code_list.append(f"{{var_name}} = {{temp}}")
            return None

        # 7. WhileStmt: WHILE ( BoolExpr ) Stmt
        elif node.name == 'WhileStmt':
            if len(node.children) >= 5:
                loop_label = self.new_label()
                exit_label = self.new_label()
                self.code_list.append(f"{{loop_label}}:")
                bool_result = self._traverse(node.children[2])
                if bool_result:
                    temp = self.new_temp()
                    self.code_list.append(f"{{temp}} = not {{bool_result}}")
                    self.code_list.append(f"if {{temp}} goto {{exit_label}}")
                self._traverse(node.children[4])
                self.code_list.append(f"goto {{loop_label}}")
                self.code_list.append(f"{{exit_label}}:")
            return None

        # 8. IfStmt: IF ( BoolExpr ) Stmt
        elif node.name == 'IfStmt':
            if len(node.children) >= 5:
                exit_label = self.new_label()
                bool_result = self._traverse(node.children[2])
                if bool_result:
                    temp = self.new_temp()
                    self.code_list.append(f"{{temp}} = not {{bool_result}}")
                    self.code_list.append(f"if {{temp}} goto {{exit_label}}")
                self._traverse(node.children[4])
                self.code_list.append(f"{{exit_label}}:")
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
                    self.code_list.append(f"{{temp}} = {{e1}} {{op}} {{e2}}")
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
            self.code_list.append(f"{{target}} = {{left_val}} {{op_symbol}} {{right_val}}")
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
        self.code_list.append(f"{{target}} = {{left_val}} {{op_symbol}} {{right_val}}")

        if len(op_group.children) > 2:
            return self._handle_tail_recursive(op_group.children[2], target)
        if len(tail_node.children) > 1:
            return self._handle_tail_recursive(tail_node.children[1], target)

        return target

# =============================================================================
# 编译器入口封装 [SDT版本]
# =============================================================================

class GeneratedCompiler:
    """自动生成的编译器（使用语法制导翻译）
    
    [SDT实现] 在解析过程中同时生成中间代码，实现一遍扫描编译
    """
    def __init__(self):
        self.lexer = GeneratedLexer() 
        self.parser = GeneratedParser()

    def compile(self, source_code: str) -> List[str]:
        """编译源代码，返回中间代码列表
        
        [SDT] 解析和代码生成同时进行：
        1. 词法分析生成tokens
        2. 语法分析过程中同时生成中间代码
        3. 从parser获取生成的代码
        """
        tokens = self.lexer.tokenize(source_code)
        
        # [SDT关键] parse过程中已经同时生成了中间代码
        ast = self.parser.parse(tokens)
        
        # [语义检查] 检查是否有语义错误（如未定义变量）
        if self.parser.has_semantic_errors():
            print("\\n" + "=" * 60)
            print("[错误] 检测到语义错误")
            print("=" * 60)
            for error in self.parser.get_semantic_errors():
                print(error)
            print("=" * 60 + "\\n")
            raise SyntaxError("编译失败：存在语义错误")
        
        # [SDT] 直接从parser获取生成的中间代码
        code_str = self.parser.get_generated_code()
        return code_str.split('\\n') if code_str else []

    def compile_file(self, input_file: str, output_file: str):
        """编译文件并保存结果
        
        [SDT] 使用语法制导翻译进行编译
        """
        source_code = ""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            code_lines = self.compile(source_code)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in code_lines:
                    if line.strip():  # 只写入非空行
                        f.write(line + '\\n')
            
            print(f"[Success] Compilation completed (Syntax-Directed Translation) -> {{output_file}}")
            print(f"         Generated {{len([l for l in code_lines if l.strip()])}} intermediate code instructions")
        except SyntaxError as e:
            # 使用 ErrorFormatter 格式化语法/词法错误
            formatter = ErrorFormatter(source_code=source_code, source_file=input_file)
            error_msg = str(e)
            
            # Extract line and column numbers from error message
            line_match = re.search(r'line (\\d+)', error_msg, re.IGNORECASE)
            col_match = re.search(r'column (\\d+)', error_msg, re.IGNORECASE)
            line = int(line_match.group(1)) if line_match else 1
            col = int(col_match.group(1)) if col_match else 1
            
            # Determine if it's a lexical error or syntax error
            if 'lexical error' in error_msg.lower() or 'unrecognized' in error_msg.lower():
                formatted_error = formatter.format_lexical_error(error_msg, line, col)
            else:
                # Try to extract expected tokens
                expected_tokens = None
                expected_match = re.search(r'expected[：:]?\\s*([^\\n]+)', error_msg, re.IGNORECASE)
                if expected_match:
                    expected_tokens = [t.strip() for t in expected_match.group(1).split(',')]
                formatted_error = formatter.format_syntax_error(error_msg, line, col, expected_tokens)
            
            print("\\n" + formatted_error)
            sys.exit(1)
        except Exception as e:
            # 其他错误也使用 ErrorFormatter
            formatter = ErrorFormatter(source_code=source_code, source_file=input_file)
            formatted_error = formatter.format_general_error(str(e), "编译错误")
            print("\\n" + formatted_error)
            sys.exit(1)

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="自动生成的编译器（SDT版）")
    arg_parser.add_argument("input", help="输入源代码文件")
    arg_parser.add_argument("-o", "--output", default="output.tac", help="输出中间代码文件")

    args = arg_parser.parse_args()
    compiler = GeneratedCompiler()
    compiler.compile_file(args.input, args.output)
'''