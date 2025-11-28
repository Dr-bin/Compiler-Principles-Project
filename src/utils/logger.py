"""日志系统

提供统一的日志输出接口。
"""

import sys
from datetime import datetime


class Logger:
    """日志记录器
    
    提供不同级别的日志输出（INFO, SUCCESS, WARNING, ERROR）。
    """

    def __init__(self, verbose: bool = False):
        """初始化日志记录器
        
        参数:
            verbose: 是否输出详细信息
        """
        self.verbose = verbose
        self.start_time = datetime.now()

    def _format_message(self, level: str, message: str) -> str:
        """格式化日志消息
        
        参数:
            level: 日志级别
            message: 消息内容
            
        返回:
            格式化后的消息字符串
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{level}] {message}"

    def info(self, message: str) -> None:
        """输出信息级别日志
        
        参数:
            message: 日志消息
            
        返回:
            None
        """
        print(self._format_message("INFO", message), file=sys.stdout)

    def success(self, message: str) -> None:
        """输出成功级别日志
        
        参数:
            message: 日志消息
            
        返回:
            None
        """
        print(self._format_message("SUCCESS", message), file=sys.stdout)

    def warning(self, message: str) -> None:
        """输出警告级别日志
        
        参数:
            message: 日志消息
            
        返回:
            None
        """
        print(self._format_message("WARNING", message), file=sys.stderr)

    def error(self, message: str) -> None:
        """输出错误级别日志
        
        参数:
            message: 日志消息
            
        返回:
            None
        """
        print(self._format_message("ERROR", message), file=sys.stderr)

    def debug(self, message: str) -> None:
        """输出调试级别日志
        
        参数:
            message: 日志消息
            
        返回:
            None
        """
        if self.verbose:
            print(self._format_message("DEBUG", message), file=sys.stdout)
