# 编译器-编译器 (Compiler-Compiler) 项目

## 项目概述

本项目是一个**编译器生成器**（Compiler-Compiler，简称"编译器的编译器"），
能够根据形式化的词法规则和语法规则自动生成编译器。

项目使用**经典编译原理算法**：
- **词法分析**：使用正则表达式和扫描方法
- **语法分析**：使用递归下降解析和LL(1)技术
- **代码生成**：使用语法制导翻译（SDT）在解析过程中同时生成三地址中间代码

## 核心特性：语法制导翻译（Syntax-Directed Translation）

本项目实现了真正的**语法制导翻译（SDT）**，满足编译原理课程的严格要求：

✅ **一遍扫描编译**：在语法分析过程中同时生成中间代码，无需单独的代码生成阶段  
✅ **语义动作嵌入**：每识别一个产生式，立即执行相应的翻译动作  
✅ **综合属性计算**：使用综合属性（Synthesized Attributes）在AST节点中传递语义信息  
✅ **三地址码生成**：实时生成规范的三地址中间代码（临时变量、标签等）

### SDT实现示例

**源代码**：
```
x = 10;
y = 20;
print(x + y);
```

**编译过程**（语法制导翻译）：
1. 解析 `x = 10;` → **立即生成** `x = 10`
2. 解析 `y = 20;` → **立即生成** `y = 20`
3. 解析 `x + y` → **立即生成** `t1 = x + y`
4. 解析 `print(...)` → **立即生成** `param t1` 和 `call print, 1`

**生成的中间代码**（三地址码）：
```
x = 10
y = 20
t1 = x + y
param t1
call print, 1
```

**关键点**：所有代码都是在解析过程中生成的，不需要等到整个AST构建完成！

## 项目特点

✅ **完整的编译器流程**：从源代码到中间代码的完整实现
✅ **自动化生成**：从规则文件自动生成编译器
✅ **易于扩展**：模块化设计，便于添加新语言
✅ **教学友好**：所有代码包含详尽的中文注释和文档
✅ **完整的测试**：包含单元测试和集成测试

## 项目结构

```
compiler_project/
├── src/                          # 源代码目录
│   ├── compiler_generator/       # 编译器生成器核心
│   │   ├── __init__.py
│   │   ├── lexer_generator.py    # 词法分析器生成器
│   │   ├── parser_generator.py   # 语法分析器生成器
│   │   └── code_generator.py     # 代码生成器
│   ├── frontend/                 # 前端接口
│   │   ├── __init__.py
│   │   ├── rule_parser.py        # 规则文件解析器
│   │   └── cli.py                # 命令行接口
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       ├── error_handler.py      # 错误处理
│       └── logger.py             # 日志系统
├── examples/                     # 示例语言定义
│   ├── simple_expr/              # 简单表达式语言
│   │   ├── lexer_rules.txt       # 词法规则
│   │   └── grammar_rules.txt     # 语法规则
│   └── pl0_subset/               # PL/0子集语言
│       ├── lexer_rules.txt
│       └── grammar_rules.txt
├── generated/                    # 生成的编译器输出目录
├── tests/                        # 测试用例
│   ├── __init__.py
│   ├── test_lexer.py             # 词法分析器测试
│   ├── test_parser.py            # 语法分析器测试
│   └── test_integration.py       # 集成测试
├── main.py                       # 主程序入口
├── requirements.txt              # 项目依赖
└── README.md                     # 本文件
```
## 项目类图
![alt text](compiler.drawio.svg)

## 快速开始

### 环境设置

```bash
# 安装依赖
pip install -r requirements.txt
```

### 运行示例

```bash
# 编译一个简单的源代码
python main.py compile examples/simple_expr/lexer_rules.txt examples/simple_expr/grammar_rules.txt examples/sample.src -o output.tac

# 运行测试
python -m pytest tests/ -v
```

## 核心模块说明

### 1. 词法分析器生成器 (lexer_generator.py)

**功能**：将正则表达式规则自动编译为词法扫描器

关键类：
- `Token`：表示一个词法单元，包含类型、值、位置信息
- `LexerGenerator`：生成器，用于构建词法分析器

主要方法：
- `add_token_rule(type, pattern)`：添加词法规则
- `build()`：编译所有规则
- `tokenize(text)`：进行词法分析

### 2. 语法分析器生成器 (parser_generator.py)

**功能**：将BNF文法规范自动转换为递归下降解析器

关键类：
- `ASTNode`：抽象语法树节点
- `ParserGenerator`：语法分析器生成器

主要方法：
- `add_production(nonterminal, production)`：添加文法产生式
- `set_start_symbol(symbol)`：设置开始符号
- `parse(tokens)`：进行语法分析，返回AST

### 3. 代码生成器 (code_generator.py)

**功能**：~~从AST生成三地址中间代码~~ **[已升级为SDT]** 在解析过程中同时生成中间代码

**[重要变更]** 代码生成现已集成到 `parser_generator.py` 中：
- 解析器在识别产生式时，**立即调用翻译动作**
- 无需单独的代码生成阶段
- 实现真正的**一遍扫描编译**

关键方法（在 `ParserGenerator` 类中）：
- `_apply_translation_scheme()`：根据产生式执行翻译动作（SDT核心）
- `emit(code)`：发出一条三地址指令
- `new_temp()`、`new_label()`：生成临时变量和标签
- `get_generated_code()`：获取生成的中间代码

### 4. 规则解析器 (rule_parser.py)

**功能**：解析词法和语法规则的文本文件

关键类：
- `RuleParser`：规则解析器

主要方法：
- `parse_lexer_rules(filename)`：解析词法规则
- `parse_grammar_rules(filename)`：解析语法规则
- `validate_grammar(grammar)`：验证文法有效性

### 5. 命令行接口 (cli.py)

**功能**：提供用户友好的命令行工具

关键类：
- `CompilerCLI`：CLI管理器

支持的命令：
- `python main.py build`：生成编译器
- `python main.py compile`：编译源代码

### 6. 工具模块

#### Logger (logger.py)
- 统一的日志输出接口
- 支持 INFO, SUCCESS, WARNING, ERROR, DEBUG 级别

#### ErrorHandler (error_handler.py)
- 错误收集和报告
- 异常处理和堆栈跟踪

## 规则文件格式

### 词法规则文件 (lexer_rules.txt)

```
# 格式: TOKEN_TYPE = regex_pattern
# 支持标准的正则表达式语法

ID = [a-zA-Z_][a-zA-Z0-9_]*
NUM = [0-9]+(?:\.[0-9]+)?
PLUS = \+
MINUS = -
LPAREN = \(
RPAREN = \)
```

### 语法规则文件 (grammar_rules.txt)

```
# 格式: NonTerminal -> production1 | production2
# 使用BNF表示法
# 终结符用单引号括起来，非终结符不加引号

Program -> StmtList
StmtList -> Stmt | Stmt StmtList
Stmt -> 'ID' 'ASSIGN' Expr 'SEMI' | 'PRINT' '(' Expr ')'
Expr -> Term 'PLUS' Expr | Term
Term -> Factor 'MUL' Term | Factor
Factor -> 'NUM' | 'ID' | '(' Expr ')'
```

## 使用示例

### 示例1：编译简单表达式

```bash
# 创建源代码文件
echo "x = 1 + 2 ;" > test.src

# 使用简单表达式语言的规则编译
python main.py compile \
  examples/simple_expr/lexer_rules.txt \
  examples/simple_expr/grammar_rules.txt \
  test.src -o output.tac

# 查看生成的中间代码
cat output.tac
```

### 示例2：运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_lexer.py -v

# 运行特定测试函数
python -m pytest tests/test_parser.py::TestParserGenerator::test_parse_simple -v

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

### 示例3：创建新语言

1. 创建目录：`examples/my_lang/`
2. 编写 `lexer_rules.txt` 和 `grammar_rules.txt`
3. 创建 `test_code.src` 源文件
4. 编译：`python main.py compile examples/my_lang/lexer_rules.txt examples/my_lang/grammar_rules.txt test_code.src`

## 测试用例

### 词法分析器测试 (test_lexer.py)

| 测试 | 说明 |
|------|------|
| `test_add_token_rule` | 添加词法规则 |
| `test_build_lexer` | 构建词法分析器 |
| `test_tokenize_simple` | 简单词法分析 |
| `test_tokenize_with_whitespace` | 空白符处理 |
| `test_tokenize_error` | 错误处理 |
| `test_line_column_tracking` | 位置追踪 |

### 语法分析器测试 (test_parser.py)

| 测试 | 说明 |
|------|------|
| `test_create_parser` | 创建解析器 |
| `test_add_production` | 添加产生式 |
| `test_parse_simple` | 简单解析 |
| `test_parse_with_alternatives` | 产生式选择 |
| `test_parse_error` | 语法错误 |
| `test_ast_node_creation` | AST节点 |

### 集成测试 (test_integration.py)

| 测试 | 说明 |
|------|------|
| `test_end_to_end` | 完整编译流程 |
| `test_rule_parser` | 规则解析 |

## 项目成员分工

| 模块 | 负责人 | 文件 |
|------|--------|------|
| 词法分析 | 同学A | `src/compiler_generator/lexer_generator.py` |
| 语法分析 | 同学B | `src/compiler_generator/parser_generator.py` |
| 代码生成 | 同学C | `src/compiler_generator/code_generator.py` |
| 前端接口 | 全体 | `src/frontend/` |
| 工具模块 | 全体 | `src/utils/` |
| 测试 | 全体 | `tests/` |
| 文档 | 全体 | `README.md` |

## 语法制导翻译（SDT）技术细节

### 翻译方案设计

本项目使用**L-attributed语法制导定义**，在自顶向下解析过程中计算综合属性：

1. **产生式识别**：使用LL(1)算法选择产生式
2. **语义动作执行**：识别产生式后立即调用`_apply_translation_scheme()`
3. **属性计算**：通过`synthesized_value`传递语义信息
4. **代码发射**：调用`emit()`立即生成三地址码

### 典型翻译规则示例

```python
# 产生式: Expr -> Term '+' Term
# 翻译规则: 
#   temp = new_temp()
#   emit(temp + " = " + Term1.value + " + " + Term2.value)
#   Expr.value = temp
```

**实际实现**（在`_apply_translation_scheme()`中）：
```python
if symbol == 'Expr' and has_add_operator(children):
    left_val = children[0].synthesized_value
    op = children[1].synthesized_value  # '+'
    right_val = children[2].synthesized_value
    temp = self.new_temp()
    self.emit(f"{temp} = {left_val} {op} {right_val}")
    node.synthesized_value = temp
```

### SDT与两遍扫描的对比

| 特性 | 传统两遍扫描 | 本项目（SDT） |
|------|------------|-------------|
| 扫描次数 | 2次（解析+代码生成） | 1次（同时进行） |
| AST需求 | 必须完整构建 | 仅用于属性传递 |
| 代码生成时机 | 解析完成后 | **解析过程中** |
| 内存占用 | 较高（存储完整AST） | 较低（实时发射代码） |
| 符合理论 | 一般实现 | **严格符合SDT定义** |

### 验证SDT实现

运行以下命令验证SDT是否正常工作：
```bash
python test_sdt_debug.py  # 查看解析过程中的代码生成
```

您会看到：
- 每识别一个产生式
- 立即生成对应的中间代码
- 无需等待整个解析完成

## 扩展指南

### 支持更复杂的文法

1. 实现FIRST/FOLLOW集合分析 ✅ **已实现**
2. 改进冲突解决策略 ✅ **已实现**（消除左递归、左公因子）
3. 支持更多的文法特性（如EBNF）

### 增强代码生成

1. 添加类型检查 → 在`_apply_translation_scheme()`中添加类型检查逻辑
2. 生成优化的中间代码 → 实现常量折叠、死代码消除等
3. 支持目标代码生成 → 添加目标平台的指令选择

### 集成优化

1. 词法分析优化（DFA最小化）
2. 语法分析优化（LR解析）
3. **代码生成优化** ✅ **已采用SDT实现一遍扫描**

## 常见问题

**Q: 如何调试规则文件中的错误？**
A: 
- 检查正则表达式语法
- 使用注释标记规则
- 从简单规则开始逐步扩展

**Q: 支持哪些语法结构？**
A: 
- 表达式、语句、条件、循环等
- 具体取决于语法规则文件的定义

**Q: 如何生成其他形式的中间代码？**
A: 
- 修改 `CodeGenerator._traverse_ast()` 方法
- 添加新的 `emit()` 调用或指令格式

## 参考资源

- [龙书：编译原理](https://en.wikipedia.org/wiki/Compilers:_Principles,_Techniques,_and_Tools)
- [ANTLR编译器生成器](https://www.antlr.org/)
- [正则表达式教程](https://regex101.com/)
- [BNF范式](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form)

## 许可证

本项目用于教学和学习编译原理。

---

**创建日期**: 2025年11月28日
**最后更新**: 2025年11月28日
