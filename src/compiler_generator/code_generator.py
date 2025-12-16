"""代码生成器 (同学C负责)

该模块实现从抽象语法树(AST)生成中间代码(三地址码)或目标代码的功能。
使用语法制导翻译(Syntax-Directed Translation)技术。
"""

from typing import List, Dict, Optional, Any
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
            
        说明:
            临时变量用于存储中间计算结果。
        """
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self) -> str:
        """生成一个新的标签名称
        
        返回:
            标签名称，格式为 L1, L2, L3, ...
            
        说明:
            标签用于代码跳转（条件跳转、循环等）。
        """
        self.label_counter += 1
        return f"L{self.label_counter}"

    def emit(self, op: str, arg1: str = "", arg2: str = "", result: str = "") -> None:
        """发出一条三地址码指令
        
        参数:
            op: 操作符（如 '+', '-', '*', '=', 'goto'等）
            arg1: 第一个操作数
            arg2: 第二个操作数
            result: 结果变量
            
        返回:
            None
            
        说明:
            生成的指令格式：result = arg1 op arg2
            对于某些操作（如 goto、label），可能没有 result。
        """
        if result:
            instruction = f"{result} = {arg1} {op} {arg2}".strip()
        else:
            instruction = f"{op} {arg1} {arg2}".strip()
        
        self.code_list.append(instruction)

    def add_symbol(self, name: str, var_type: str = "int", value: Any = None) -> None:
        """将一个符号（变量）添加到符号表
        
        参数:
            name: 变量名称
            var_type: 变量类型（如 'int', 'float'等）
            value: 变量的初始值
            
        返回:
            None
            
        说明:
            符号表用于记录变量的类型、作用域等信息。
        """
        self.symbol_table[name] = {
            'type': var_type,
            'value': value,
            'defined': False
        }

    def lookup_symbol(self, name: str) -> Optional[Dict[str, Any]]:
        """查找符号表中的一个符号
        
        参数:
            name: 要查找的符号名称
            
        返回:
            符号信息字典，如果不存在则返回 None
            
        说明:
            用于检查变量是否已定义。
        """
        return self.symbol_table.get(name)

    def generate_from_ast(self, node: ASTNode) -> str:
        """从AST生成中间代码
        
        参数:
            node: AST根节点
            
        返回:
            生成的中间代码字符串
            
        说明:
            这是代码生成的主方法，递归遍历AST并生成代码。
            需要根据具体的语言语法进行定制。
        """
        self._traverse_ast(node)
        return self.get_code()

    def _traverse_ast(self, node: ASTNode) -> Optional[str]:
        """递归遍历AST并生成代码
        
        参数:
            node: 当前AST节点
            
        返回:
            该节点对应的计算结果（如果有的话）
            
        说明:
            这是一个通用的AST遍历方法。
            对于不同类型的语言，需要在子类中重写此方法。
        """
        if not node:
            return None

        # 根据节点名称处理不同的语言结构
        if node.name == 'Program':
            # 程序：遍历所有语句
            for child in node.children:
                self._traverse_ast(child)
            return None

        elif node.name == 'StmtList':
            # 语句列表：遍历所有语句
            for child in node.children:
                self._traverse_ast(child)
            return None

        elif node.name == 'Stmt' or node.name == 'Statement':
            # 语句：处理赋值、输出等
            # 赋值语句: ID = Expr ;
            if len(node.children) >= 4 and node.children[0].name == "'ID'":
                var_node = node.children[0]  # 'ID' 节点
                expr_node = node.children[2]  # Expr 节点
                
                var_name = var_node.token.value if var_node.token else ""
                expr_value = self._traverse_ast(expr_node)
                
                if var_name and expr_value:
                    # 格式: var_name = expr_value (空 op)
                    self.code_list.append(f"{var_name} = {expr_value}")
                    self.add_symbol(var_name)
            # print 语句: PRINT ( Expr ) ;
            elif len(node.children) >= 5 and node.children[0].name == "'PRINT'":
                expr_node = node.children[2]  # Expr 节点在位置 2
                expr_value = self._traverse_ast(expr_node)
                if expr_value:
                    self.code_list.append(f"print({expr_value})")
            return None

        elif node.name == 'Expr' or node.name == 'Expression':
            # 表达式：处理加减运算
            # Expr -> Term AddOp | Term
            if len(node.children) == 1:
                # 简单表达式（单个项）
                return self._traverse_ast(node.children[0])
            elif len(node.children) >= 2:
                # 二元运算: Term AddOp (或更多)
                # 获取第一个Term
                result = self._traverse_ast(node.children[0])
                
                # 处理所有的 AddOp/MulOp 或其他
                for i in range(1, len(node.children)):
                    child = node.children[i]
                    if child.name == 'AddOp':
                        result = self._traverse_add_op(child, result)
                    else:
                        result = self._traverse_ast(child)
                
                return result
            return None

        elif node.name == 'Term':
            # 项：处理乘除等高优先级运算
            # Term -> Factor MulOp | Factor
            if len(node.children) == 1:
                result = self._traverse_ast(node.children[0])
                return result
            elif len(node.children) >= 2:
                # 二元运算: Factor MulOp (或更多)
                result = self._traverse_ast(node.children[0])
                
                # 处理所有的 MulOp
                for i in range(1, len(node.children)):
                    child = node.children[i]
                    if child.name == 'MulOp':
                        result = self._traverse_mul_op(child, result)
                    else:
                        result = self._traverse_ast(child)
                
                return result
            return None

        elif node.name == 'Factor':
            # 因子：数字、标识符或括号表达式
            if len(node.children) == 1:
                # 数字或标识符或递归的 'NUM'/'ID' 节点
                child = node.children[0]
                result = self._traverse_ast(child)
                return result
            elif len(node.children) >= 3:
                # 括号表达式: '(' Expr ')'
                return self._traverse_ast(node.children[1])
            return None

        elif node.name in ['NUM', 'ID'] or (node.name.startswith("'") and node.name.endswith("'")):
            # 终结符：直接返回值
            if node.token:
                return node.token.value
            return None

        else:
            # 其他类型的节点：遍历所有子节点
            for child in node.children:
                self._traverse_ast(child)
            return None

    def _traverse_add_op(self, add_op_node: ASTNode, left: str) -> str:
        """处理 AddOp 节点并返回结果
        
        参数:
            add_op_node: AddOp 节点
            left: 左操作数
            
        返回:
            计算结果（临时变量或值）
        """
        if add_op_node.name != 'AddOp':
            return left
        
        if len(add_op_node.children) >= 2:
            op_node = add_op_node.children[0]
            op = op_node.token.value if op_node.token else ""
            term_node = add_op_node.children[1]
            right = self._traverse_ast(term_node)
            
            result = self.new_temp()
            self.emit(op, left, right, result)
            
            # 如果有继续的 AddOp
            if len(add_op_node.children) >= 3:
                return self._traverse_add_op(add_op_node.children[2], result)
            
            return result
        
        return left

    def _traverse_mul_op(self, mul_op_node: ASTNode, left: str) -> str:
        """处理 MulOp 节点并返回结果
        
        参数:
            mul_op_node: MulOp 节点
            left: 左操作数
            
        返回:
            计算结果（临时变量或值）
        """
        if mul_op_node.name != 'MulOp':
            return left
        
        if len(mul_op_node.children) >= 2:
            op_node = mul_op_node.children[0]
            op = op_node.token.value if op_node.token else ""
            factor_node = mul_op_node.children[1]
            right = self._traverse_ast(factor_node)
            
            result = self.new_temp()
            self.emit(op, left, right, result)
            
            # 如果有继续的 MulOp
            if len(mul_op_node.children) >= 3:
                return self._traverse_mul_op(mul_op_node.children[2], result)
            
            return result
        
        return left

    def get_code(self) -> str:
        """获取生成的中间代码
        
        返回:
            以换行符分隔的中间代码字符串
            
        说明:
            包含所有发出的指令。
        """
        return '\n'.join(self.code_list)

    def print_symbol_table(self) -> str:
        """打印符号表的内容
        
        返回:
            符号表的字符串表示
            
        说明:
            用于调试，显示所有已定义的符号。
        """
        result = "=== Symbol Table ===\n"
        for name, info in self.symbol_table.items():
            result += f"{name}: {info}\n"
        return result

    def reset(self) -> None:
        """重置代码生成器状态
        
        返回:
            None
            
        说明:
            用于生成多个代码段时清空状态。
        """
        self.code_list = []
        self.temp_counter = 0
        self.label_counter = 0
        self.symbol_table = {}


def generate_compiler_code(lexer_code: str, parser_code: str) -> str:
    """生成完整的编译器代码
    
    参数:
        lexer_code: 词法分析器代码字符串
        parser_code: 语法分析器代码字符串
        
    返回:
        完整的可执行编译器Python代码
    """
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    compiler_code = f'''#!/usr/bin/env python3
# =============================================================================
# 自动生成的编译器
# 生成时间: {current_time}
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

{lexer_code}

{parser_code}

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
        return f"t{{self.temp_counter}}"
    
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
                    self.code_list.append(f"{{var_name}} = {{expr_value}}")
            # print语句
            elif len(node.children) >= 5 and node.children[0].name == "'PRINT'":
                expr_value = self._traverse(node.children[2])
                if expr_value:
                    self.code_list.append(f"print({{expr_value}})")
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
            self.code_list.append(f"{{temp}} = {{left}} {{op}} {{right}}")
            if len(node.children) >= 3:
                return self._handle_addop(node.children[2], temp)
            return temp
        return left
    
    def _handle_mulop(self, node, left):
        if len(node.children) >= 2:
            op = node.children[0].token.value
            right = self._traverse(node.children[1])
            temp = self.new_temp()
            self.code_list.append(f"{{temp}} = {{left}} {{op}} {{right}}")
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
            raise CompilationError(f"词法错误: {{str(e)}}")
        except Exception as e:
            raise CompilationError(f"词法分析失败: {{str(e)}}")
        
        # 语法分析
        try:
            ast = self.parser.parse(tokens)
        except SyntaxError as e:
            raise CompilationError(f"语法错误: {{str(e)}}")
        except Exception as e:
            raise CompilationError(f"语法分析失败: {{str(e)}}")
        
        # 代码生成
        try:
            code = self.codegen.generate(ast)
        except Exception as e:
            raise CompilationError(f"代码生成失败: {{str(e)}}")
        
        return code
    
    def compile_file(self, input_file: str, output_file: str):
        """编译文件"""
        print(f"[编译] 开始编译: {{input_file}}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"[错误] 文件不存在: {{input_file}}")
            sys.exit(1)
        except Exception as e:
            print(f"[错误] 读取文件失败: {{str(e)}}")
            sys.exit(1)
        
        try:
            code = self.compile(source_code)
        except CompilationError as e:
            print(f"\\n{'='*70}")
            print(f"[错误] 编译失败")
            print(f"{'='*70}")
            print(f"{{str(e)}}")
            print(f"{'='*70}\\n")
            sys.exit(1)
        except Exception as e:
            print(f"\\n[错误] 编译过程出现异常: {{str(e)}}")
            sys.exit(1)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for line in code:
                    f.write(line + '\\n')
        except Exception as e:
            print(f"[错误] 写入输出文件失败: {{str(e)}}")
            sys.exit(1)
        
        print(f"[成功] 编译完成: {{output_file}}")
        print(f"[统计] 生成 {{len(code)}} 条三地址码")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自动生成的编译器")
    parser.add_argument("input", help="输入源代码文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出三地址码文件路径")
    
    args = parser.parse_args()
    
    compiler = GeneratedCompiler()
    compiler.compile_file(args.input, args.output)
'''
    
    return compiler_code
