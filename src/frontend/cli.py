"""命令行接口 (CLI)

提供用户交互的命令行工具，调度编译器生成和编译过程。
"""

import sys
import os
import argparse
import re
import subprocess
from src.frontend.rule_parser import load_rules_from_files
from src.compiler_generator.lexer_generator import create_lexer_from_spec, generate_lexer_code
from src.compiler_generator.parser_generator import create_parser_from_spec, generate_parser_code, ParseError
from src.compiler_generator.code_generator import CodeGenerator, generate_compiler_code
from src.utils.logger import Logger
from src.utils.error_handler import ErrorHandler
from src.utils.error_formatter import ErrorFormatter


class CompilerCLI:
    """编译器CLI类
    
    管理命令行参数解析和编译过程调度。
    """

    def __init__(self):
        """初始化CLI"""
        self.logger = Logger()
        self.error_handler = ErrorHandler()
        self.raw_args = None  # 保存原始命令行参数

    def run(self, args: list = None) -> int:
        """运行CLI程序
        
        参数:
            args: 命令行参数列表，如果为None则使用sys.argv
            
        返回:
            程序退出码（0表示成功，非0表示失败）
            
        说明:
            这是CLI的主入口点。
        """
        # 保存原始参数用于判断是否使用了默认值
        if args is None:
            self.raw_args = sys.argv[1:]  # 跳过脚本名
        else:
            self.raw_args = args
        
        parser = self._build_parser()
        parsed_args = parser.parse_args(args)

        try:
            if parsed_args.command == 'build':
                return self._cmd_build(parsed_args)
            elif parsed_args.command == 'compile':
                return self._cmd_compile(parsed_args)
            elif parsed_args.command == 'test-compiler':
                return self._cmd_test_compiler(parsed_args)
            else:
                parser.print_help()
                return 1
        except Exception as e:
            self.error_handler.handle_error(e)
            return 1

    def _build_parser(self) -> argparse.ArgumentParser:
        """构建命令行参数解析器
        
        返回值: ArgumentParser 对象
            
        说明: 定义所有支持的命令和选项
        """
        parser = argparse.ArgumentParser(
            description='编译器生成器 - 从规则文件自动生成编译器'
        )

        subparsers = parser.add_subparsers(dest='command', help='子命令')

        # build 子命令：从规则文件生成编译器
        build_parser = subparsers.add_parser('build', help='从规则文件生成编译器')
        build_parser.add_argument('lexer_rules', nargs='?', 
                                 default='examples/simple_expr/lexer_rules.txt',
                                 help='词法规则文件路径（默认：examples/simple_expr/lexer_rules.txt）')
        build_parser.add_argument('grammar_rules', nargs='?',
                                 default='examples/simple_expr/grammar_rules.txt',
                                 help='语法规则文件路径（默认：examples/simple_expr/grammar_rules.txt）')
        build_parser.add_argument('-o', '--output', default='generated/compiler.py',
                                 help='输出文件路径（默认：generated/compiler.py）')

        # compile 子命令：使用生成的编译器编译源代码
        compile_parser = subparsers.add_parser('compile', help='编译源代码')
        compile_parser.add_argument('lexer_rules', nargs='?',
                                   default='examples/simple_expr/lexer_rules.txt',
                                   help='词法规则文件路径（默认：examples/simple_expr/lexer_rules.txt）')
        compile_parser.add_argument('grammar_rules', nargs='?',
                                   default='examples/simple_expr/grammar_rules.txt',
                                   help='语法规则文件路径（默认：examples/simple_expr/grammar_rules.txt）')
        compile_parser.add_argument('source', nargs='?',
                                   default='examples/sample.src',
                                   help='要编译的源代码文件（默认：examples/sample.src）')
        compile_parser.add_argument('-o', '--output', help='输出文件路径（可选）')

        # test-compiler 子命令：构建并测试生成的编译器
        test_parser = subparsers.add_parser(
            'test-compiler',
            help='构建并用内置示例程序测试生成的编译器'
        )
        test_parser.add_argument('lexer_rules', nargs='?',
                                 default='examples/simple_expr/lexer_rules.txt',
                                 help='词法规则文件路径（默认：examples/simple_expr/lexer_rules.txt）')
        test_parser.add_argument('grammar_rules', nargs='?',
                                 default='examples/simple_expr/grammar_rules.txt',
                                 help='语法规则文件路径（默认：examples/simple_expr/grammar_rules.txt）')
        test_parser.add_argument('-c', '--compiler-output',
                                 default='generated/compiler.py',
                                 help='生成的编译器路径（默认：generated/compiler.py）')
        test_parser.add_argument('-p', '--program-dir',
                                 default='examples/simple_expr/programs',
                                 help='测试程序所在目录（默认：examples/simple_expr/programs）')
        test_parser.add_argument('-o', '--output-dir',
                                 default='generated/test_outputs',
                                 help='测试输出目录（默认：generated/test_outputs）')

        return parser

    def _cmd_build(self, args) -> int:
        """处理 build 命令
        
        参数:
            args: 解析后的命令行参数
            
        返回:
            退出码
            
        说明:
            从规则文件生成编译器代码。
        """
        try:
            # 检查是否使用了默认路径（通过检查原始参数中是否提供了这些参数）
            # 如果原始参数中只有 'build'，说明使用了默认值
            using_default = (self.raw_args is not None and 
                           len(self.raw_args) >= 1 and
                           self.raw_args[0] == 'build' and
                           len([a for a in self.raw_args[1:] if not a.startswith('-')]) == 0)
            
            self.logger.info(f"读取规则文件...")
            if using_default:
                self.logger.info(f"  使用默认规则文件")
            self.logger.info(f"  词法规则: {args.lexer_rules}")
            self.logger.info(f"  语法规则: {args.grammar_rules}")

            lexer_rules, grammar_rules = load_rules_from_files(
                args.lexer_rules, args.grammar_rules
            )

            self.logger.info(f"词法规则数量: {len(lexer_rules)}")
            self.logger.info(f"文法规则数量: {len(grammar_rules)}")

            # 生成词法分析器代码
            self.logger.info("生成词法分析器代码...")
            lexer_code = generate_lexer_code(lexer_rules)
            
            # 生成语法分析器代码
            self.logger.info("生成语法分析器代码...")
            # grammar_rules已经是Dict[str, List[List[str]]]格式
            # 提取开始符号（第一个非终结符）
            start_symbol = list(grammar_rules.keys())[0] if grammar_rules else None
            
            parser_code = generate_parser_code(grammar_rules, start_symbol)

            # 生成完整编译器代码
            self.logger.info("组合生成完整编译器...")

            # 提取开始符号（通常是文法文件中的第一个非终结符）
            start_symbol = list(grammar_rules.keys())[0] if grammar_rules else 'Program'

            # 核心修复：传入 grammar_rules 字典而不是 parser_code 字符串，并传入 start_symbol
            # 现在的 code_generator 会在内部调用 pg.build_analysis_sets() 来消除冲突
            compiler_code = generate_compiler_code(lexer_code, grammar_rules, start_symbol)
            
            # 写入文件
            os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(compiler_code)
            
            self.logger.info(f"编译器已生成到: {args.output}")
            self.logger.success("编译器生成成功！")
            self.logger.info(f"\n使用方法: python {args.output} <source_file> -o <output_file>")

            return 0

        except FileNotFoundError as e:
            self.logger.error(f"文件不存在: {e}")
            return 1
        except Exception as e:
            self.logger.error(f"生成失败: {e}")
            return 1

    def _cmd_compile(self, args) -> int:
        """处理 compile 命令
        
        参数:
            args: 解析后的命令行参数
            
        返回:
            退出码
            
        说明:
            使用生成的编译器编译源代码文件。
        """
        try:
            # 检查是否使用了默认路径（通过检查原始参数中是否提供了这些参数）
            # 如果原始参数中只有 'compile'，说明使用了默认值
            using_default = (self.raw_args is not None and 
                           len(self.raw_args) >= 1 and
                           self.raw_args[0] == 'compile' and
                           len([a for a in self.raw_args[1:] if not a.startswith('-')]) == 0)
            
            if using_default:
                self.logger.info(f"使用默认配置编译...")
            self.logger.info(f"编译源文件: {args.source}")
            self.logger.info(f"  词法规则: {args.lexer_rules}")
            self.logger.info(f"  语法规则: {args.grammar_rules}")

            # 加载规则
            lexer_rules, grammar_rules = load_rules_from_files(
                args.lexer_rules, args.grammar_rules
            )

            # 创建词法分析器
            lexer = create_lexer_from_spec(lexer_rules)
            
            # 读取源代码
            with open(args.source, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # 词法分析
            self.logger.info("执行词法分析...")
            try:
                tokens = lexer.tokenize(source_code)
                self.logger.info(f"词法分析完成，产生 {len(tokens)} 个token")
            except (SyntaxError, Exception) as e:
                # 处理词法错误
                formatter = ErrorFormatter(source_code=source_code, source_file=args.source)
                # 从错误消息中提取行号和列号
                error_msg = str(e)
                line_match = re.search(r'line\s+(\d+)', error_msg, re.IGNORECASE)
                col_match = re.search(r'column\s+(\d+)', error_msg, re.IGNORECASE)
                line = int(line_match.group(1)) if line_match else 1
                col = int(col_match.group(1)) if col_match else 1
                formatted_error = formatter.format_lexical_error(error_msg, line, col)
                try:
                    print("\n" + formatted_error)
                except UnicodeEncodeError:
                    print(f"\n词法错误: {error_msg}")
                return 1

            # [SDT] 语法分析与代码生成（一遍扫描）
            self.logger.info("执行语法制导翻译（解析+代码生成）...")
            # 需要从grammar_rules中确定起始符号
            start_symbol = list(grammar_rules.keys())[0] if grammar_rules else 'Program'
            parser = create_parser_from_spec(grammar_rules, start_symbol)
            try:
                # [SDT关键] parse方法现在会在解析过程中同时生成中间代码
                ast = parser.parse(tokens)
                self.logger.info("[完成] 语法分析完成")
                self.logger.info("[完成] 中间代码生成完成（语法制导翻译）")
                
                # [SDT] 从解析器中获取生成的中间代码
                intermediate_code = parser.get_generated_code()
                
            except ParseError as e:
                # 使用错误格式化器显示友好的错误信息
                formatter = ErrorFormatter(source_code=source_code, source_file=args.source)
                # 从错误消息中提取行号、列号和期望的token
                error_info = self._parse_error_message(str(e))
                formatted_error = formatter.format_syntax_error(
                    error_info['message'],
                    error_info['line'],
                    error_info['column'],
                    error_info.get('expected_tokens')
                )
                try:
                    print("\n" + formatted_error)
                except UnicodeEncodeError:
                    # 如果编码失败，使用简化版本
                    print(f"\n语法错误: {error_info['message']}")
                    print(f"位置: 第 {error_info['line']} 行, 第 {error_info['column']} 列")
                return 1

            # 输出结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(intermediate_code)
                self.logger.info(f"中间代码已保存到: {args.output}")
            else:
                print("\n=== 中间代码 ===")
                print(intermediate_code)

            self.logger.success("编译成功！")
            return 0

        except FileNotFoundError as e:
            self.logger.error(f"文件不存在: {e}")
            return 1
        except ParseError as e:
            # 语法错误已经在上面处理了，这里作为备用
            try:
                formatter = ErrorFormatter(source_file=args.source if 'args' in locals() else None)
                error_info = self._parse_error_message(str(e))
                formatted_error = formatter.format_syntax_error(
                    error_info['message'],
                    error_info['line'],
                    error_info['column'],
                    error_info.get('expected_tokens')
                )
                print("\n" + formatted_error)
            except UnicodeEncodeError:
                print(f"\n语法错误: {str(e)}")
            return 1
        except Exception as e:
            # 其他错误，使用通用格式化
            try:
                formatter = ErrorFormatter()
                formatted_error = formatter.format_general_error(str(e), "编译错误")
                print("\n" + formatted_error)
            except UnicodeEncodeError:
                print(f"\n编译错误: {str(e)}")
            self.error_handler.handle_error(e)
            return 1

    def _cmd_test_compiler(self, args) -> int:
        """处理 test-compiler 命令

        步骤:
        1. 调用 build 逻辑生成编译器（默认 generated/compiler.py）
        2. 扫描程序目录中所有 .src 文件
        3. 依次调用生成的编译器进行编译，输出到指定目录
        """
        try:
            self.logger.info("开始构建生成的编译器用于测试...")

            # 复用 _cmd_build 逻辑
            from types import SimpleNamespace
            build_args = SimpleNamespace(
                lexer_rules=args.lexer_rules,
                grammar_rules=args.grammar_rules,
                output=args.compiler_output,
            )
            build_result = self._cmd_build(build_args)
            if build_result != 0:
                self.logger.error("构建生成的编译器失败，终止测试。")
                return build_result

            compiler_path = args.compiler_output
            program_dir = args.program_dir
            output_dir = args.output_dir

            if not os.path.isdir(program_dir):
                self.logger.error(f"测试程序目录不存在: {program_dir}")
                return 1

            os.makedirs(output_dir, exist_ok=True)

            self.logger.info(f"使用生成的编译器测试目录中的程序: {program_dir}")

            success_count = 0
            fail_count = 0

            for filename in sorted(os.listdir(program_dir)):
                if not filename.endswith('.src'):
                    continue

                src_path = os.path.join(program_dir, filename)
                out_path = os.path.join(
                    output_dir,
                    os.path.splitext(filename)[0] + '.tac'
                )

                self.logger.info(f"  测试程序: {src_path}")

                cmd = [
                    sys.executable,
                    compiler_path,
                    src_path,
                    '-o',
                    out_path,
                ]

                try:
                    completed = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                    )
                except Exception as e:
                    self.logger.error(f"  运行生成的编译器失败: {e}")
                    fail_count += 1
                    continue

                if completed.returncode == 0:
                    self.logger.success(f"  通过: {filename} -> {out_path}")
                    success_count += 1
                else:
                    self.logger.error(f"  失败: {filename}")
                    if completed.stdout:
                        print("  --- stdout ---")
                        print(completed.stdout)
                    if completed.stderr:
                        print("  --- stderr ---", file=sys.stderr)
                        print(completed.stderr, file=sys.stderr)
                    fail_count += 1

            self.logger.info(
                f"测试完成: 成功 {success_count} 个，失败 {fail_count} 个，"
                f"共 {success_count + fail_count} 个程序。"
            )

            return 0 if fail_count == 0 else 1
        except Exception as e:
            self.logger.error(f"test-compiler 执行失败: {e}")
            return 1
    
    def _parse_error_message(self, error_msg: str) -> dict:
        """解析错误消息，提取行号、列号和期望的token
        
        参数:
            error_msg: 错误消息字符串
            
        返回:
            包含解析信息的字典
        """
        result = {
            'message': error_msg,
            'line': 1,
            'column': 1,
            'expected_tokens': None
        }
        
        # 提取行号: "Line 2" 或 "at Line 2"
        line_match = re.search(r'[Ll]ine\s+(\d+)', error_msg)
        if line_match:
            result['line'] = int(line_match.group(1))
        
        # 提取列号: "Column 8" 或 "列 8"
        col_match = re.search(r'[Cc]olumn\s+(\d+)', error_msg)
        if col_match:
            result['column'] = int(col_match.group(1))
        
        # 提取期望的token: "Expected one of: ID, NUM, ..."
        expected_match = re.search(r'Expected\s+(?:one\s+of\s*:)?\s*([^\.]+)', error_msg)
        if expected_match:
            tokens_str = expected_match.group(1).strip()
            # 分割token列表
            tokens = [t.strip() for t in tokens_str.split(',') if t.strip()]
            result['expected_tokens'] = tokens
        
        return result


def main(args: list = None) -> int:
    """CLI的主入口函数
    
    参数:
        args: 命令行参数列表
        
    返回:
        程序退出码
        
    说明:
        供 main.py 或其他脚本调用。
    """
    cli = CompilerCLI()
    return cli.run(args)


if __name__ == '__main__':
    sys.exit(main())
