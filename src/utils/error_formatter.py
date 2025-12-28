"""错误格式化器

提供友好的错误消息格式化功能，包括源代码片段显示和错误位置标记。
"""

from typing import List, Optional, Tuple
import os


class ErrorFormatter:
    """错误格式化器类
    
    将编译器错误格式化为用户友好的格式，包括：
    - 源代码片段显示
    - 错误位置标记（箭头指向）
    - 上下文信息
    """
    
    def __init__(self, source_code: str = None, source_file: str = None):
        """初始化错误格式化器
        
        参数:
            source_code: 源代码内容（字符串）
            source_file: 源代码文件路径（如果提供，会自动读取）
        """
        if source_file and os.path.exists(source_file):
            with open(source_file, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
            self.source_file = source_file
        else:
            self.source_code = source_code or ""
            self.source_file = source_file
        
        # 将源代码按行分割
        self.source_lines = self.source_code.split('\n') if self.source_code else []
    
    def format_syntax_error(self, error_message: str, line: int, column: int, 
                           expected_tokens: List[str] = None) -> str:
        """格式化语法错误消息
        
        参数:
            error_message: 原始错误消息
            line: 错误所在行号（从1开始）
            column: 错误所在列号（从1开始）
            expected_tokens: 期望的token类型列表
            
        返回:
            格式化后的错误消息字符串
        """
        result = []
        
        # 1. 错误标题
        result.append("=" * 70)
        result.append("[ERROR] 语法错误 (Syntax Error)")
        result.append("=" * 70)
        result.append("")
        
        # 2. 位置信息
        location = f"文件: {self.source_file}" if self.source_file else "源代码"
        result.append(f"[位置] {location}, 第 {line} 行, 第 {column} 列")
        result.append("")
        
        # 3. 显示源代码片段（前后各2行）
        context_lines = 2
        start_line = max(1, line - context_lines)
        end_line = min(len(self.source_lines), line + context_lines)
        
        result.append("[源代码片段]:")
        result.append("-" * 70)
        
        for i in range(start_line, end_line + 1):
            line_num = str(i).rjust(4)
            line_content = self.source_lines[i - 1] if i <= len(self.source_lines) else ""
            
            # 当前错误行用特殊标记
            if i == line:
                result.append(f">>> {line_num} | {line_content}")
                # 添加箭头指向错误位置
                arrow = " " * (len(line_num) + 4) + " " * (column - 1) + "^" * max(1, len(line_content[column-1:column]) or 1)
                result.append(f"    {arrow}")
            else:
                result.append(f"    {line_num} | {line_content}")
        
        result.append("-" * 70)
        result.append("")
        
        # 4. 错误详情
        result.append("[错误详情]:")
        result.append(f"   {error_message}")
        result.append("")
        
        # 5. 期望的token（如果有）
        if expected_tokens:
            result.append("[期望的token类型]:")
            if len(expected_tokens) <= 5:
                result.append(f"   {', '.join(expected_tokens)}")
            else:
                result.append(f"   {', '.join(expected_tokens[:5])} ... (共 {len(expected_tokens)} 种)")
            result.append("")
        
        # 6. 建议
        result.append("[建议]:")
        if expected_tokens:
            # 尝试提供更友好的建议
            suggestions = self._generate_suggestions(expected_tokens, line, column)
            for suggestion in suggestions:
                result.append(f"   - {suggestion}")
        else:
            result.append("   - 请检查语法规则是否正确")
            result.append("   - 确认是否缺少必要的符号（如分号、括号等）")
        result.append("")
        
        result.append("=" * 70)
        
        return "\n".join(result)
    
    def format_lexical_error(self, error_message: str, line: int, column: int) -> str:
        """格式化词法错误消息
        
        参数:
            error_message: 原始错误消息
            line: 错误所在行号
            column: 错误所在列号
            
        返回:
            格式化后的错误消息字符串
        """
        result = []
        
        result.append("=" * 70)
        result.append("[ERROR] 词法错误 (Lexical Error)")
        result.append("=" * 70)
        result.append("")
        
        location = f"文件: {self.source_file}" if self.source_file else "源代码"
        result.append(f"[位置] {location}, 第 {line} 行, 第 {column} 列")
        result.append("")
        
        # 显示源代码片段
        context_lines = 2
        start_line = max(1, line - context_lines)
        end_line = min(len(self.source_lines), line + context_lines)
        
        result.append("[源代码片段]:")
        result.append("-" * 70)
        
        for i in range(start_line, end_line + 1):
            line_num = str(i).rjust(4)
            line_content = self.source_lines[i - 1] if i <= len(self.source_lines) else ""
            
            if i == line:
                result.append(f">>> {line_num} | {line_content}")
                arrow = " " * (len(line_num) + 4) + " " * (column - 1) + "^" * max(1, len(line_content[column-1:column]) or 1)
                result.append(f"    {arrow}")
            else:
                result.append(f"    {line_num} | {line_content}")
        
        result.append("-" * 70)
        result.append("")
        result.append(f"[错误详情] {error_message}")
        result.append("")
        result.append("=" * 70)
        
        return "\n".join(result)
    
    def _generate_suggestions(self, expected_tokens: List[str], line: int, column: int) -> List[str]:
        """根据期望的token生成建议
        
        参数:
            expected_tokens: 期望的token类型列表
            line: 行号
            column: 列号
            
        返回:
            建议列表
        """
        suggestions = []
        
        # 获取当前行的内容
        if line <= len(self.source_lines):
            current_line = self.source_lines[line - 1]
        else:
            current_line = ""
        
        # 根据token类型提供建议
        token_suggestions = {
            'SEMI': '可能缺少分号 (;)',
            'RPAREN': '可能缺少右括号 ())',
            'LPAREN': '可能缺少左括号 (()',
            'NUM': '这里需要一个数字',
            'ID': '这里需要一个标识符（变量名）',
            'PLUS': '可能缺少加号 (+)',
            'MINUS': '可能缺少减号 (-)',
            'MUL': '可能缺少乘号 (*)',
            'DIV': '可能缺少除号 (/)',
            'ASSIGN': '可能缺少赋值号 (=)',
        }
        
        for token in expected_tokens[:3]:  # 只显示前3个建议
            if token in token_suggestions:
                suggestions.append(token_suggestions[token])
        
        # 如果没有特定建议，提供通用建议
        if not suggestions:
            suggestions.append(f"期望以下token之一: {', '.join(expected_tokens[:3])}")
        
        return suggestions
    
    def format_general_error(self, error_message: str, error_type: str = "Error") -> str:
        """格式化一般错误消息
        
        参数:
            error_message: 错误消息
            error_type: 错误类型
            
        返回:
            格式化后的错误消息字符串
        """
        result = []
        result.append("=" * 70)
        result.append(f"[ERROR] {error_type}")
        result.append("=" * 70)
        result.append("")
        result.append(f"[错误详情] {error_message}")
        result.append("")
        result.append("=" * 70)
        return "\n".join(result)

