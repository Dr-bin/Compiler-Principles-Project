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
            # 识别打印语句 (第一个孩子是 PRINT)
            elif first_child.name == "'PRINT'":
                expr_value = self._traverse_ast(node.children[2])
                if expr_value:
                    self.code_list.append(f"print {expr_value}")
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


def generate_compiler_code(lexer_code: str, grammar_rules: Dict, start_symbol: str) -> str:
    """生成完整的编译器代码"""

    # --- 第一步：强制使用 ParserGenerator 优化文法并生成 Parser 代码 ---
    pg = ParserGenerator()
    pg.set_start_symbol(start_symbol)
    for nt, prods in grammar_rules.items():
        for p in prods:
            pg.add_production(nt, p)

    # 执行 LL(1) 转换（消除左递归、左公因子）
    pg.build_analysis_sets()

    # 获取优化后的文法，传给 generate_parser_code 得到源码
    optimized_grammar = pg.grammar
    parser_code = generate_parser_code(optimized_grammar, start_symbol)

    # --- 第二步：生成编译器字符串 ---
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f'''#!/usr/bin/env python3
# =============================================================================
# 自动生成的编译器 (LL(1) 优化版)
# 生成时间: {current_time}
# =============================================================================

import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Optional

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

    def new_temp(self):
        self.temp_counter += 1
        return f"t{{self.temp_counter}}"

    def generate(self, ast):
        self.code_list = []
        self.temp_counter = 0
        self._traverse(ast)
        return self.code_list

    def _traverse(self, node):
        if not node: return None

        # 1. 结构性节点处理 (Program / StmtList)
        if node.name in ['Program', 'StmtList'] or "_LF_TAIL" in node.name:
            if "_LF_TAIL" in node.name and not node.children:
                return None

            # 如果是 StmtList 或 Program，递归处理所有子节点
            if node.name in ['Program', 'StmtList']:
                for child in node.children:
                    self._traverse(child)
                return None

            # 如果是表达式尾部，特殊处理
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

            # 打印语句 PRINT ( Expr ) ;
            elif first_child.name == "'PRINT'":
                val = self._traverse(node.children[2])
                self.code_list.append(f"print {{val}}")
                return None

        # 4. 因子处理 (Factor)
        elif node.name == 'Factor':
            if node.children[0].name == "'LPAREN'":
                return self._traverse(node.children[1])
            return self._traverse(node.children[0])

        # 5. 终端节点
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

        # 提取操作符和右操作数
        # 结构通常为: [AddOp/MulOp, FurtherTail]
        op_group = tail_node.children[0]

        # 从 AddOp/MulOp 中提取具体的符号和对应的 Term/Factor
        op_symbol = op_group.children[0].token.value
        right_operand_node = op_group.children[1]
        right_val = self._traverse(right_operand_node)

        # 生成 TAC
        target = self.new_temp()
        self.code_list.append(f"{{target}} = {{left_val}} {{op_symbol}} {{right_val}}")

        # 递归处理后续的 Tail
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
                    f.write(line + '\\n')
            print(f"[成功] 编译完成 -> {{output_file}}")
        except Exception as e:
            print(f"[错误] {{str(e)}}")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="自动生成的编译器")
    arg_parser.add_argument("input", help="输入文件")
    arg_parser.add_argument("-o", "--output", default="output.3ac", help="输出文件")

    args = arg_parser.parse_args()
    compiler = GeneratedCompiler()
    compiler.compile_file(args.input, args.output)
'''