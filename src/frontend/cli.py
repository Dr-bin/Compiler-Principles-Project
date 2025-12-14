"""命令行接口 (CLI)

提供用户交互的命令行工具，调度编译器生成和编译过程。
"""

import sys
import os
import argparse
from src.frontend.rule_parser import load_rules_from_files
from src.compiler_generator.lexer_generator import create_lexer_from_spec, generate_lexer_code
from src.compiler_generator.parser_generator import create_parser_from_spec, generate_parser_code
from src.compiler_generator.code_generator import CodeGenerator, generate_compiler_code
from src.utils.logger import Logger
from src.utils.error_handler import ErrorHandler


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
            compiler_code = generate_compiler_code(lexer_code, parser_code)
            
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
            tokens = lexer.tokenize(source_code)
            self.logger.info(f"词法分析完成，产生 {len(tokens)} 个token")

            # 语法分析
            self.logger.info("执行语法分析...")
            # 需要从grammar_rules中确定起始符号
            start_symbol = list(grammar_rules.keys())[0] if grammar_rules else 'Program'
            parser = create_parser_from_spec(grammar_rules, start_symbol)
            ast = parser.parse(tokens)
            self.logger.info("语法分析完成，生成AST")

            # 代码生成
            self.logger.info("执行代码生成...")
            codegen = CodeGenerator()
            intermediate_code = codegen.generate_from_ast(ast)

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
        except Exception as e:
            self.logger.error(f"编译失败: {e}")
            return 1


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
