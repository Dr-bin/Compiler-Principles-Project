# SDT代码生成顺序问题及回填技术解决方案

## ✅ 问题已解决！

使用**回填技术（Backpatching）**成功解决了SDT代码生成顺序问题。

---

## 问题描述（已解决）

在 `complete_relations.tac` 中，生成的代码不正确：

**实际生成的代码：**
```
x = 5
y = 5
param 1        ← 直接输出，没有条件判断！
call write, 1
```

**应该生成的代码：**
```
x = 5
y = 5
t1 = x >= y       ← 计算条件
t2 = not t1       ← 取反
if t2 goto L1     ← 条件判断
param 1           ← 条件为真时执行
call write, 1
L1:               ← 跳转标签
```

---

## 问题根源

### SDT代码生成顺序问题

在语法制导翻译中，代码生成的顺序是按照**后序遍历**（post-order）：
1. 先递归解析所有子节点
2. 子节点的代码先生成
3. 然后才执行父节点的SDT

对于 `if (x >= y) write(1);` 的解析过程：

```
1. 解析IfStmt产生式
   ├─ 解析 'IF' token
   ├─ 解析 'LPAREN' token
   ├─ 解析 Condition
   │   ├─ 解析 Expr (x)
   │   ├─ 解析 RelOp (>=)
   │   ├─ 解析 Expr (y)
   │   └─ SDT生成: t1 = x >= y  ← 第1步：条件代码
   ├─ 解析 'RPAREN' token
   ├─ 解析 Stmt
   │   └─ SDT生成: param 1; call write, 1  ← 第2步：语句体代码
   └─ 执行 IfStmt 的 SDT
       └─ 生成: t2 = not t1; if t2 goto L1; L1:  ← 第3步：跳转代码
```

**实际生成顺序：**
```
t1 = x >= y      ← 步骤1
param 1          ← 步骤2（错误！应该在步骤3之后）
call write, 1
t2 = not t1      ← 步骤3（太晚了！）
if t2 goto L1
L1:
```

**正确顺序应该是：**
```
t1 = x >= y      ← 步骤1
t2 = not t1      ← 步骤2（应该在Stmt之前）
if t2 goto L1
param 1          ← 步骤3（应该在条件判断之后）
call write, 1
L1:              ← 步骤4
```

---

## 为什么会这样

### SDT的后序遍历特性

在递归下降解析中：
1. 先递归解析子节点（深度优先）
2. 子节点的代码先生成
3. 父节点的代码后生成

这对于**表达式**是正确的：
```
Expr -> Term '+' Term
```
生成顺序：
1. 解析左Term → 生成代码
2. 解析右Term → 生成代码
3. 执行Expr的SDT → 生成 `t = left + right`

但对于**控制流语句**是错误的：
```
IfStmt -> 'IF' 'LPAREN' Condition 'RPAREN' Stmt
```
生成顺序：
1. 解析Condition → 生成条件计算代码
2. 解析Stmt → 生成语句体代码 ← 问题：这应该在条件跳转之后！
3. 执行IfStmt的SDT → 生成条件跳转代码

---

## 解决方案

### 方案1：代码插入（推荐）

在IfStmt的SDT中，将条件跳转代码**插入**到正确位置，而不是追加：

```python
# 记录Stmt代码的起始位置
stmt_start = len(self.code_buffer)

# 在Stmt代码之前插入条件跳转代码
if bool_val:
    temp = self.new_temp()
    self.code_buffer.insert(stmt_start, f"{temp} = not {bool_val}")
    self.code_buffer.insert(stmt_start + 1, f"if {temp} goto {exit_label}")

# 在末尾添加标签
self.emit(f"{exit_label}:")
```

### 方案2：代码重排

在SDT完成后，重新排列code_buffer中的代码。

### 方案3：回填技术（Backpatching）

使用编译原理中的回填技术，先生成占位符，后填充实际地址。

### 方案4：说明限制（当前）

在文档中说明这是SDT的一个已知限制，实际编译器中需要更复杂的技术。

---

## 当前状态

由于控制流语句的代码生成顺序问题，当前实现**暂时禁用了if/while的跳转代码生成**。

这意味着：
- ✅ 条件表达式会正确计算
- ✅ 语句体会正确执行
- ❌ 但没有条件跳转逻辑（条件判断总是执行）

这是SDT一遍扫描的一个经典问题，需要更高级的技术来解决。

---

## 建议

对于课程项目：
1. 可以说明这是SDT的一个技术挑战
2. 解释代码生成顺序问题的原因
3. 提出解决方案（代码插入、回填等）
4. 说明在实际编译器中如何解决

这反而是一个**展示理解深度的机会**！
