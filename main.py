"""编译器-编译器项目主入口

这是项目的入口点，用于启动编译器生成器的CLI。
"""

import sys
from src.frontend.cli import main


if __name__ == '__main__':
    """主程序入口
    
    使用方式:
        python main.py build examples/simple_expr/lexer_rules.txt examples/simple_expr/grammar_rules.txt
        python main.py compile examples/simple_expr/lexer_rules.txt examples/simple_expr/grammar_rules.txt source.src
    """
    sys.exit(main())
