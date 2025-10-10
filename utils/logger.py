"""
Logging Utility

This is the logging module for the application

"""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console

def setup_logger(
        name: str = "Personal_Deepresearch_Agent",
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        use_rich: bool = True
) -> logging.Logger:
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []

    if use_rich:
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=False
        )
    else:
        console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setLevel(level)

    if not use_rich:
        formatter = logging.Formatter(
            datefmt="%Y-%m-%D %H:%M:%S"
        )

        console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    if log_file:
        log_path=Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            datefmt="%Y-%m-%D %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

def get_logger(name: str = "Personal_Deepresearch_Agent") ->logging.Logger:
    return logging.getLogger(name)

class LoggerMixin:
    @property
    def logger(self)->logging.Logger:
        name=f"Personal_Deepresearch_Agent.{self.__class__.__name__}"
        return logging.getLogger(name)
    
console=Console()

def print_success(message: str):
    console.print(f"[green]√[/green]{message}")

def print_error(message: str):
    console.print(f"[red]❌[/red]{message}")


# 定义一个函数，用于在控制台打印警告信息
def print_warning(message: str):
    # 使用rich的print方法，打印黄色的感叹号和消息
    console.print(f"[yellow]⚠[/yellow] {message}")


# 定义一个函数，用于在控制台打印信息
def print_info(message: str):
    # 使用rich的print方法，打印蓝色的信息图标和消息
    console.print(f"[blue]ℹ[/blue] {message}")


# 定义一个函数，用于在控制台打印步骤信息
def print_step(message: str):
    # 使用rich的print方法，打印青色的箭头和消息，用于指示流程步骤
    console.print(f"[cyan]▶[/cyan] {message}")