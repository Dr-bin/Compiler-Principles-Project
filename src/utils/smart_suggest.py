"""智能错误修复建议模块

提供类似现代 IDE 的智能提示功能：
- 未定义变量时，推荐编辑距离最近的已定义变量
- 拼写错误检测和修复建议
"""

from typing import List, Tuple, Optional, Set


def levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离（Levenshtein Distance）
    
    编辑距离是将一个字符串转换为另一个字符串所需的最少操作次数，
    操作包括：插入、删除、替换一个字符。
    
    参数:
        s1: 第一个字符串
        s2: 第二个字符串
        
    返回:
        编辑距离（整数）
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def find_similar_variables(undefined_var: str, 
                           defined_vars: Set[str], 
                           max_distance: int = 2) -> List[Tuple[str, int]]:
    """查找与未定义变量相似的已定义变量
    
    参数:
        undefined_var: 未定义的变量名
        defined_vars: 已定义变量的集合
        max_distance: 最大编辑距离阈值（默认2）
        
    返回:
        [(变量名, 编辑距离), ...] 按距离排序
    """
    suggestions = []
    
    for var in defined_vars:
        dist = levenshtein_distance(undefined_var.lower(), var.lower())
        if dist <= max_distance:
            suggestions.append((var, dist))
    
    suggestions.sort(key=lambda x: x[1])
    return suggestions


def suggest_variable_fix(undefined_var: str, 
                         defined_vars: Set[str]) -> Optional[str]:
    """为未定义变量提供修复建议
    
    参数:
        undefined_var: 未定义的变量名
        defined_vars: 已定义变量的集合
        
    返回:
        最相似的变量名，如果没有相似的则返回 None
    """
    suggestions = find_similar_variables(undefined_var, defined_vars)
    if suggestions:
        return suggestions[0][0]
    return None



class SmartErrorReporter:
    """智能错误报告器
    
    收集已定义的变量，在发生错误时提供智能建议。
    """
    
    def __init__(self):
        self.defined_variables: Set[str] = set()
    
    def register_variable(self, name: str):
        """注册一个已定义的变量"""
        self.defined_variables.add(name)
    
    def check_variable(self, name: str) -> Tuple[bool, Optional[str]]:
        """检查变量是否已定义，如果未定义则返回建议
        
        返回:
            (是否已定义, 修复建议)
        """
        if name in self.defined_variables:
            return True, None
        
        suggestion = suggest_variable_fix(name, self.defined_variables)
        return False, suggestion
    
    def format_undefined_error(self, var_name: str, line: int, column: int) -> str:
        """格式化未定义变量错误信息"""
        is_defined, suggestion = self.check_variable(var_name)
        
        if is_defined:
            return ""
        
        error_msg = f"语义错误: 第 {line} 行, 第 {column} 列\n"
        error_msg += f"  变量 '{var_name}' 未定义\n"
        
        if suggestion:
            error_msg += f"\n  建议: 你是不是想用 '{suggestion}'?"
            all_suggestions = find_similar_variables(var_name, self.defined_variables, max_distance=3)
            if len(all_suggestions) > 1:
                others = [s[0] for s in all_suggestions[1:4]]
                if others:
                    error_msg += f"\n  其他可能: {', '.join(others)}"
        else:
            error_msg += f"\n  建议: 请先定义变量 '{var_name}' 再使用"
            if self.defined_variables:
                error_msg += f"\n  已定义的变量: {', '.join(sorted(self.defined_variables))}"
        
        return error_msg


if __name__ == '__main__':
    print("=== 编辑距离测试 ===")
    test_cases = [
        ("count", "cont"),
        ("index", "indx"),
        ("value", "valeu"),
    ]
    
    for s1, s2 in test_cases:
        dist = levenshtein_distance(s1, s2)
        print(f"  '{s1}' vs '{s2}': 距离 = {dist}")
    
    print("\n=== 变量建议测试 ===")
    defined = {'count', 'index', 'value', 'total'}
    
    for var in ['cont', 'indx', 'valeu', 'xyz']:
        suggestion = suggest_variable_fix(var, defined)
        if suggestion:
            print(f"  '{var}' 未定义 -> 建议: '{suggestion}'")
        else:
            print(f"  '{var}' 未定义 -> 无相似变量")
