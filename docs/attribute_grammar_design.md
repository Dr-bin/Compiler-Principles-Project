# 基于属性文法的SDT设计

## 问题分析

当前实现中存在硬编码token类型列表的问题，例如：
- `if op_type in ['PLUS', 'MINUS', 'MUL', 'DIV']`
- `production[0] in ["'WRITE'", "'PRINT'"]`

这些硬编码使得代码生成器与具体的语法规则耦合，不够通用。

## 解决方案：属性文法

### 核心思想

1. **综合属性（Synthesized）**：自底向上传递，从子节点计算父节点属性
   - 当前已实现：`node.synthesized_value`
   
2. **继承属性（Inherited）**：自顶向下传递，从父节点传递到子节点
   - 新增：`node.inherited_attributes` 字典

3. **语义动作模式**：在语法规则中定义通用的语义模式，而不是硬编码token类型

### 设计思路

#### 方案1：通过属性传递识别操作符类型

```python
# ASTNode扩展
class ASTNode:
    synthesized_value: str = None  # 综合属性（已存在）
    inherited_attributes: Dict[str, Any] = None  # 继承属性（新增）
    semantic_pattern: str = None  # 语义模式（新增）
```

#### 方案2：在语法规则中定义语义模式

在语法规则文件中定义语义动作模式：

```
# 定义语义模式：二元运算符
# @SEMANTIC_PATTERN: binary_op
Expr -> Expr '+' Term { Expr.val = Expr.val + Term.val }
Expr -> Expr '-' Term { Expr.val = Expr.val - Term.val }

# 定义语义模式：赋值语句
# @SEMANTIC_PATTERN: assignment
Stmt -> 'ID' 'ASSIGN' Expr 'SEMI' { symbol_table[ID] = Expr.val }
```

#### 方案3：通过属性传递识别操作符（推荐）

在解析过程中，通过继承属性传递操作符类型：

```python
# 当识别到二元运算符产生式时
# Expr -> Expr Op Term
# 通过属性传递识别操作符类型，而不是硬编码

def _apply_translation_scheme(self, symbol, production, node):
    # 通过产生式结构识别：Expr Op Expr 模式
    if len(production) == 3 and not production[0].startswith("'") and \
       production[1].startswith("'") and not production[2].startswith("'"):
        # 中间是操作符（终结符）
        op_node = children[1]
        # 通过属性传递操作符类型，而不是硬编码token类型列表
        op_type = op_node.token.type if op_node.token else None
        
        # 使用通用的二元运算符处理，而不是硬编码 ['PLUS', 'MINUS', ...]
        if self._is_binary_operator(op_type):  # 通过属性判断
            e1 = children[0].synthesized_value
            e2 = children[2].synthesized_value
            node.synthesized_value = self._apply_binary_op(op_type, e1, e2)
```

### 实现步骤

1. **扩展ASTNode**：添加继承属性支持
2. **定义语义模式识别**：通过产生式结构自动识别语义模式
3. **通用操作符处理**：通过属性传递识别操作符，而不是硬编码列表
4. **更新语法规则解析器**：支持语义动作定义（可选）

### 优势

1. **消除硬编码**：不再需要硬编码token类型列表
2. **更通用**：可以处理任意操作符，只要符合产生式结构
3. **可扩展**：新增操作符不需要修改代码生成器
4. **符合理论**：完全基于属性文法的理论
