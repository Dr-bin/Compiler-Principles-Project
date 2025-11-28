"""错误处理系统

提供统一的错误处理接口。
"""

import sys
import traceback


class CompilerError(Exception):
    """编译器异常基类"""
    pass


class LexicalError(CompilerError):
    """词法错误"""
    pass


class SyntaxError(CompilerError):
    """语法错误"""
    pass


class SemanticError(CompilerError):
    """语义错误"""
    pass


class ErrorHandler:
    """错误处理器
    
    捕获和处理编译过程中的各类错误。
    """

    def __init__(self):
        """初始化错误处理器"""
        self.errors = []
        self.warnings = []

    def add_error(self, error_type: str, message: str, 
                  line: int = None, column: int = None) -> None:
        """添加一个错误记录
        
        参数:
            error_type: 错误类型（如 'Lexical', 'Syntax'等）
            message: 错误消息
            line: 错误所在的行号（可选）
            column: 错误所在的列号（可选）
            
        返回:
            None
        """
        error_info = {
            'type': error_type,
            'message': message,
            'line': line,
            'column': column
        }
        self.errors.append(error_info)

    def add_warning(self, message: str, line: int = None, column: int = None) -> None:
        """添加一个警告记录
        
        参数:
            message: 警告消息
            line: 警告所在的行号（可选）
            column: 警告所在的列号（可选）
            
        返回:
            None
        """
        warning_info = {
            'message': message,
            'line': line,
            'column': column
        }
        self.warnings.append(warning_info)

    def handle_error(self, error: Exception) -> None:
        """处理异常对象
        
        参数:
            error: 异常对象
            
        返回:
            None
            
        说明:
            打印错误信息和堆栈跟踪。
        """
        print(f"ERROR: {error}", file=sys.stderr)
        if isinstance(error, CompilerError):
            # 编译器相关错误
            print(f"Type: {type(error).__name__}", file=sys.stderr)
        else:
            # 系统错误，打印完整的堆栈跟踪
            traceback.print_exc(file=sys.stderr)

    def has_errors(self) -> bool:
        """检查是否有错误
        
        返回:
            True 如果有错误，False 否则
        """
        return len(self.errors) > 0

    def get_error_count(self) -> int:
        """获取错误数量
        
        返回:
            错误总数
        """
        return len(self.errors)

    def get_warning_count(self) -> int:
        """获取警告数量
        
        返回:
            警告总数
        """
        return len(self.warnings)

    def print_errors(self) -> None:
        """打印所有错误
        
        返回:
            None
        """
        if not self.errors:
            print("No errors.")
            return

        print(f"\nTotal {len(self.errors)} error(s):\n")
        for i, error in enumerate(self.errors, 1):
            location = ""
            if error['line'] is not None:
                location = f" at line {error['line']}"
                if error['column'] is not None:
                    location += f", column {error['column']}"
            
            print(f"{i}. [{error['type']}] {error['message']}{location}")

    def print_warnings(self) -> None:
        """打印所有警告
        
        返回:
            None
        """
        if not self.warnings:
            print("No warnings.")
            return

        print(f"\nTotal {len(self.warnings)} warning(s):\n")
        for i, warning in enumerate(self.warnings, 1):
            location = ""
            if warning['line'] is not None:
                location = f" at line {warning['line']}"
                if warning['column'] is not None:
                    location += f", column {warning['column']}"
            
            print(f"{i}. {warning['message']}{location}")

    def reset(self) -> None:
        """重置所有错误和警告
        
        返回:
            None
        """
        self.errors = []
        self.warnings = []
