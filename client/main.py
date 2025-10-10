"""
Main Program

"""
# 导入Python内置模块和第三方库
from __future__ import annotations  # 支持Python 3.7+的类型注解向前兼容

import argparse  # 用于解析命令行参数
import json      # 用于处理配置文件的JSON格式
import os        # 用于环境变量操作和文件路径处理
import sys       # 用于系统级操作（如标准输出/错误流、程序退出）
from dataclasses import dataclass  # 用于定义CLI配置的数据类
from pathlib import Path           # 用于更便捷的文件路径处理
from typing import Any, Dict, Tuple# 用于类型注解
from datetime import datetime      # 用于生成报告的时间戳

# 导入第三方库：dotenv（加载.env环境变量）、rich（美化CLI输出）
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# 导入项目内部模块：配置、日志、LLM工厂、智能体、工作流
from utils.config import load_config_from_env
from utils.logger import setup_logger
from llm.factory import LLMFactory
from agents.coordinator import Coordinator
from agents.planner import Planner
from agents.researcher import Researcher
from agents.rapporteur import Rapporteur
from workflow.graph import ResearchWorkflow

console = Console()

@dataclass
class CLIConfig:
    provider: str="deepseek"
    model: str = "deepseek-chat"     # 模型名称（默认deepseek-chat）
    max_iterations: int = 5          # 研究最大迭代次数（默认5次）
    auto_approve: bool = False       # 是否自动批准研究计划（默认关闭）
    output_dir: str = "./outputs"    # 报告输出目录（默认./outputs）
    show_steps: bool = False         # 是否显示详细执行步骤（默认关闭）
    output_format: str = "markdown"  # 报告输出格式（markdown/html，默认markdown）

CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json" # 定义配置文件路径：项目根目录下的config.json（用于持久化保存配置）

def load_config_from_file() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]⚠ config file load failed：{e}，use default config[/yellow]")

    return {}

def save_config_to_file(config: CLIConfig) -> None:
    try:
        config_data ={
            "provider": config.provider,
            "model": config.model,
            "max_iterations": config.max_iterations,
            "auto_approve": config.auto_approve,
            "output_dir": config.output_dir,
            "show_steps": config.show_steps,
            "output_format": config.output_format,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        console.print("[green]OK config saved[/green]")
    except Exception as e:
        # 红色错误：提示配置保存失败
        console.print(f"[red]X config saving failed：{e}[/red]")
def get_api_key_for_provider(provider: str) -> str | None:
    provider_env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }

    env_var = provider_env_map.get(provider.lower())
    return os.getenv(env_var) if env_var else None

def print_separator(char: str = "-", length: int = 70) -> None:
    """打印分隔线（用于美化CLI界面，区分不同模块）"""
    console.print(f"[cyan]{char * length}[/cyan]")

def print_header(text: str) -> None:
    """打印标题（使用rich的Panel组件，带青色边框和加粗文字）"""
    console.print(Panel.fit(
        f"[bold cyan]{text}[/bold cyan]",
        border_style="cyan"
    ))

def print_welcome() -> None:
    """打印欢迎界面（程序启动时显示）"""
    console.print("\n")  # 空行分隔
    print_header("Your Own Deep Research Agent")  # 主标题
    # 黄色提示：介绍系统基于LangGraph多智能体
    console.print("[yellow]Welcome to the multi-agent research system based on LangGraph！[/yellow]")

    # 显示配置文件状态：存在则绿色提示，不存在则青色说明
    if CONFIG_FILE.exists():
        console.print(f"[green]OK config file loaded: {CONFIG_FILE.name}[/green]")
    else:
        console.print("[cyan]i use default config (max_iterations=5, auto_approve=False)[/cyan]")
    console.print()  # 空行分隔

def print_menu() -> None:
    console.print("\n[bold cyan]Main Menu：[/bold cyan]\n")  # 菜单标题
    console.print("  [green]1.[/green] Execute Research Task")  # 选项1：执行研究
    console.print("  [green]2.[/green] Check Available Models")  # 选项2：查看模型列表
    console.print("  [green]3.[/green] Configuration settings")      # 选项3：修改系统配置
    console.print("  [green]4.[/green] Check the current configuration")  # 选项4：显示当前配置
    console.print("  [green]5.[/green] Exit")      # 选项5：退出系统
    console.print()  # 空行分隔

def show_models(provider: str) -> None:
    """显示指定LLM提供商的可用模型列表"""
    # 预定义各提供商的常用模型（实际可根据API动态获取，此处为静态列表）
    models = {
        'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        'claude': ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-sonnet-20240229'],
        'gemini': ['gemini-pro', 'gemini-1.5-pro'],
        'deepseek': ['deepseek-chat', 'deepseek-coder']
    }

    print_separator("-")  # 打印分隔线
    # 青色加粗标题：显示当前提供商的可用模型
    console.print(f"\n[bold cyan]{provider.upper()} 's available models：[/bold cyan]\n")

    # 遍历模型列表，逐个打印
    for model in models.get(provider, []):
        console.print(f"  • {model}")
    console.print()  # 空行分隔
    print_separator("-")  # 打印分隔线

def configure_settings(config: CLIConfig) -> None:
    """配置设置（交互式修改CLIConfig参数，支持保存到配置文件）"""
    print_separator("-")  # 打印分隔线
    # 青色加粗标题：显示当前配置
    console.print("[bold cyan]Current Config: [/bold cyan]\n")
    # 黄色显示各配置项的当前值
    console.print(f"  Provider: [yellow]{config.provider}[/yellow]")
    console.print(f"  Models: [yellow]{config.model}[/yellow]")
    console.print(f"  Max Iterations: [yellow]{config.max_iterations}[/yellow]")
    console.print(f"  Auto Approve: [yellow]{'yes' if config.auto_approve else 'no'}[/yellow]")
    console.print(f"  Output Dir: [yellow]{config.output_dir}[/yellow]")
    console.print(f"  Output Format: [yellow]{config.output_format.upper()}[/yellow]")
    console.print(f"  Show Steps: [yellow]{'yes' if config.show_steps else 'no'}[/yellow]")
    console.print()  # 空行分隔

    # 青色提示：引导用户修改配置（直接回车跳过）
    console.print("[cyan]Select the setting to modify (press Enter directly to skip): [/cyan]\n")

    # 标记配置是否被修改（用于后续判断是否需要保存）
    config_changed = False

    # 1. 修改LLM提供商（仅支持预定义的4个选项）
    provider_input = input(f"LLM Providers (deepseek/openai/claude/gemini) [{config.provider}]: ").strip().lower()
    if provider_input and provider_input in ["deepseek", "openai", "claude", "gemini"]:
        # 仅当输入与当前值不同时才处理
        if provider_input != config.provider:
            # 检查新提供商对应的API密钥是否存在
            new_api_key = get_api_key_for_provider(provider_input)
            if not new_api_key:
                # 红色错误：提示缺少API密钥环境变量
                console.print(f"[red]X cannot find {provider_input.upper()}_API_KEY environment variable[/red]")
                console.print(f"[yellow]Please configure {provider_input.upper()}_API_KEY[/yellow] in the .env file")
            else:
                # 更新提供商，并自动调整默认模型
                config.provider = provider_input
                model_defaults = {
                    'deepseek': 'deepseek-chat',
                    'openai': 'gpt-4',
                    'claude': 'claude-3-5-sonnet-20241022',
                    'gemini': 'gemini-pro'
                }
                config.model = model_defaults.get(provider_input, config.model)
                config_changed = True  # 标记配置已修改
                # 绿色提示：更新成功
                console.print(f"[green]OK updated provider to {provider_input}，model changed to {config.model}[/green]")
    elif provider_input and provider_input not in ["deepseek", "openai", "claude", "gemini"]:
        # 红色错误：提示输入无效提供商
        console.print("[red]X Invalid provider[/red]")

    # 2. 修改模型名称（用户可自由输入，不做严格校验）
    model_input = input(f"Model Name [{config.model}]: ").strip()
    if model_input:
        config.model = model_input
        config_changed = True
        console.print(f"[green]OK Updated model to {model_input}[/green]")

    # 3. 修改最大迭代次数（需输入正整数）
    try:
        max_iter_input = input(f"Max Iterations [{config.max_iterations}]: ").strip()
        if max_iter_input:
            new_max_iter = int(max_iter_input)
            # 仅当输入为正整数时才更新
            if new_max_iter > 0:
                config.max_iterations = new_max_iter
                config_changed = True
                console.print(f"[green]OKUpdated Max Iterations to {new_max_iter}[/green]")
            else:
                console.print("[red]X The maximum number of iterations must be greater than 0[/red]")
    except ValueError:
        # 捕获非数字输入的异常
        console.print("[red]X Invalid number[/red]")

    # 4. 修改自动批准计划（支持y/yes/是或n/no/否）
    auto_approve_input = input(f"Auto Approve (y/n) [{'y' if config.auto_approve else 'n'}]: ").strip().lower()
    if auto_approve_input in ['y', 'yes', '是']:
        if not config.auto_approve:
            config.auto_approve = True
            config_changed = True
        console.print("[green]OK auto approve has been enabled[/green]")
    elif auto_approve_input in ['n', 'no', '否']:
        if config.auto_approve:
            config.auto_approve = False
            config_changed = True
        console.print("[green]OK auto approve has been unenabled[/green]")

    # 5. 修改输出目录（用户可输入任意路径，不做严格校验）
    output_dir_input = input(f"Output Dir [{config.output_dir}]: ").strip()
    if output_dir_input:
        config.output_dir = output_dir_input
        config_changed = True
        console.print(f"[green]OK Update Output Dir to {output_dir_input}[/green]")

    # 6. 修改输出格式（仅支持markdown/html，输入md会自动转为markdown）
    output_format_input = input(f"Output format (markdown/html) [{config.output_format}]: ").strip().lower()
    if output_format_input in ['markdown', 'md', 'html']:
        # 规范化格式名称：md → markdown
        normalized_format = 'markdown' if output_format_input in ['markdown', 'md'] else 'html'
        if normalized_format != config.output_format:
            config.output_format = normalized_format
            config_changed = True
            console.print(f"[green]OK Update output format to {normalized_format.upper()}[/green]")
    elif output_format_input:
        console.print("[red]X Invalid output format, please choose markdown or html[/red]")

    # 7. 修改显示步骤（支持y/yes/是或n/no/否）
    show_steps_input = input(f"Show Steps (y/n) [{'y' if config.show_steps else 'n'}]: ").strip().lower()
    if show_steps_input in ['y', 'yes', '是']:
        if not config.show_steps:
            config.show_steps = True
            config_changed = True
        console.print("[green]OK show steps has been enabled[/green]")
    elif show_steps_input in ['n', 'no', '否']:
        if config.show_steps:
            config.show_steps = False
            config_changed = True
        console.print("[green]OK show steps has been unenabled[/green]")

    # 配置修改后，询问是否保存为永久配置
    if config_changed:
        console.print()  # 空行分隔
        save_choice = input("Do you want to save it as a permanent configuration?？(y/n) [y]: ").strip().lower()
        # 默认为保存（直接回车等同于y）
        if save_choice in ['', 'y', 'yes', '是']:
            save_config_to_file(config)

    print_separator("-")  # 打印分隔线

# 定义人在闭环审批回调函数：在工作流需要人工审核研究计划时调用
def human_approval_callback(state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    人在闭环审批回调函数

    Args:
        state: 当前工作流状态

    Returns:
        (approved: bool, feedback: str) - 是否批准和用户反馈
    """
    console.print("\n")  # 空行分隔
    print_separator("=")  # 打印粗分隔线
    # 黄色加粗标题：提示用户进行决策
    console.print("[bold yellow]Waiting for your decision[/bold yellow]\n")

    # 青色提示：显示3个操作选项
    console.print("[cyan]You can choose: [/cyan]")
    console.print("  [green]1.[/green] Approve the plan - start implementing the research")
    console.print("  [green]2.[/green] Reject the plan - Provide feedback to reformulate it")
    console.print("  [green]3.[/green] Cancel Task - Exit Research")
    console.print()  # 空行分隔

    # 获取用户输入的选择（1-3）
    choice = input("Please select an operation (1-3): ").strip()

    # 选择1：批准计划
    if choice == "1":
        console.print("[green]OK 计划已批准，开始研究...[/green]\n")
        print_separator("=")
        return True, None  # 返回批准状态和空反馈

    # 选择2：拒绝计划并提供反馈
    elif choice == "2":
        console.print("\n[yellow]The plan has been approved; start the research.[/yellow]")
        console.print("[dim]Tip: You can request to add/remove certain research directions, adjust priorities, etc.[/dim]\n")

        feedback = input("> ").strip()  # 获取用户反馈

        # 如果用户未提供反馈，使用默认提示
        if not feedback:
            console.print("[yellow]No feedback was provided, so the plan will be regenerated....[/yellow]")
            feedback = "Please re-optimize the research plan"

        console.print(f"\n[cyan]Feedback has been received, and the plan is being reformulated....[/cyan]\n")
        print_separator("=")
        return False, feedback  # 返回拒绝状态和用户反馈

    # 选择3：取消任务
    elif choice == "3":
        console.print("\n[yellow]The task has been cancelled[/yellow]")
        raise KeyboardInterrupt("The user cancels the task")  # 抛出中断异常终止工作流

    # 无效选择：递归调用自身要求用户重新选择
    else:
        console.print("[red]Invalid selection, please make a new decision.[/red]")
        return human_approval_callback(state)


# 定义执行研究任务的主函数
def execute_research(config: CLIConfig, query: str = None) -> None:
    """执行研究任务"""
    print_separator("-")
    console.print("[bold cyan]Execute Research Task[/bold cyan]\n")

    # 如果未提供研究问题，提示用户输入
    if not query:
        query = input("Please enter the research question: \n> ").strip()

    # 如果用户输入为空，提示错误并返回
    if not query:
        console.print("[red]X Research questions cannot be empty[/red]")
        return

    try:
        # 设置日志记录器
        logger = setup_logger()

        # 从环境变量加载配置
        console.print("\n[dim]Loading configuration...[/dim]")
        env_cfg = load_config_from_env()

        # 使用CLI配置覆盖环境变量配置
        os.environ['LLM_PROVIDER'] = config.provider
        env_cfg = load_config_from_env()  # 重新加载配置
        env_cfg.llm.model = config.model
        env_cfg.workflow.max_iterations = config.max_iterations
        env_cfg.workflow.auto_approve_plan = config.auto_approve

        # 创建LLM实例
        console.print(f"[dim]Initializing {config.provider.upper()} LLM...[/dim]")
        llm = LLMFactory.create_llm(
            provider=env_cfg.llm.provider,
            api_key=env_cfg.llm.api_key,
            model=env_cfg.llm.model
        )

        # 创建所有智能体实例
        console.print("[dim]Initializing the agents...[/dim]")
        coordinator = Coordinator(llm)
        planner = Planner(llm)
        researcher = Researcher(
            llm=llm,
            tavily_api_key=env_cfg.search.tavily_api_key,
            mcp_server_url=env_cfg.search.mcp_server_url,
            mcp_api_key=env_cfg.search.mcp_api_key
        )
        rapporteur = Rapporteur(llm)

        # 创建研究工作流实例
        console.print("[dim]Setting up the research workflow...[/dim]\n")
        workflow = ResearchWorkflow(coordinator, planner, researcher, rapporteur)

        # 运行工作流
        print_separator("-")
        console.print(f"[bold green]Start the research:[/bold green]{query}\n")

        current_state = None  # 用于跟踪当前工作流状态

        # 使用stream_interactive方法执行工作流，支持人工审核中断
        stream_iter = workflow.stream_interactive(
            query,
            config.max_iterations,
            auto_approve=config.auto_approve,
            human_approval_callback=human_approval_callback if not config.auto_approve else None,
            output_format=config.output_format
        )

        # 遍历工作流执行过程中的状态更新
        for state_update in stream_iter:
            # 如果开启了详细步骤显示，打印状态更新类型
            if config.show_steps:
                console.print(f"[dim]state_update type: {type(state_update)}[/dim]")

            # 遍历状态更新中的每个节点及其状态
            for node_name, state in state_update.items():
                # 如果开启了详细步骤显示，打印节点名称和状态类型
                if config.show_steps:
                    console.print(f"[dim]node: {node_name}, state type: {type(state)}[/dim]")

                # 处理字典和元组两种状态格式
                if isinstance(state, tuple):
                    # LangGraph可能返回(values, next_node)元组
                    if len(state) >= 1:
                        current_state = state[0] if isinstance(state[0], dict) else state
                    else:
                        continue
                else:
                    current_state = state

                # 确保当前状态是字典格式
                if not isinstance(current_state, dict):
                    if config.show_steps:
                        console.print(f"[yellow]Warning: state is not dict: {type(current_state)}[/yellow]")
                    continue

                # 获取当前步骤名称
                step = current_state.get('current_step', 'unknown')

                # 如果开启了详细步骤显示，打印当前步骤
                if config.show_steps:
                    console.print(f"[magenta]step: {step}[/magenta]")

                # 处理简单响应（如问候或不适当的查询）
                if current_state.get('simple_response'):
                    console.print(f"\n{current_state['simple_response']}\n")
                    current_state = current_state  # 保存状态供后续使用
                    continue

                # 根据当前步骤显示相应的状态信息
                if step == 'planning':
                    console.print("[cyan]Creating a research plan...[/cyan]")
                    if current_state.get('research_plan'):
                        plan_display = planner.format_plan_for_display(current_state['research_plan'])
                        console.print(Panel(plan_display, title="Research Plan", border_style="blue"))

                elif step == 'awaiting_approval':
                    if config.auto_approve:
                        console.print("[green]OK Plan Auto Approved[/green]")
                    # 交互式批准由stream_interactive中的回调函数处理

                elif step == 'researching':
                    task = current_state.get('current_task', {})
                    iteration = current_state.get('iteration_count', 0)
                    console.print(f"[cyan]researching on {task.get('description', 'unknown task') if task else 'unknown task'}[/cyan]")
                    console.print(f"[dim]iteration {iteration}/{config.max_iterations}[/dim]")

                elif step == 'generating_report':
                    console.print("[cyan]Generating the final report...[/cyan]")

        # 工作流执行结束后处理最终结果
        if current_state and current_state.get('final_report'):
            report = current_state['final_report']

            # 在控制台显示最终报告
            console.print("\n")
            console.print(Panel(
                Markdown(report),
                title="Research Report",
                border_style="green"
            ))

            # 保存报告到文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 根据输出格式确定文件扩展名
            file_extension = 'html' if current_state.get('output_format') == 'html' else 'md'
            output_path = output_dir / f"research_report_{timestamp}.{file_extension}"

            rapporteur.save_report(report, str(output_path))
            console.print(f"\n[green]OK Report Saved to{output_path}[/green]")

        elif current_state and current_state.get('simple_response'):
            # 简单查询已处理，无需显示错误
            pass
        else:
            console.print("[red]X research failed[/red]")

        print_separator("-")

    # 处理用户中断（如Ctrl+C或取消任务）
    except KeyboardInterrupt:
        console.print("\n\n[yellow]The task has been interrupted by the user.[/yellow]")
        print_separator("-")
    # 处理其他所有异常
    except Exception as e:
        console.print(f"\n[red]X Error occured{e}[/red]")
        logger.exception("Research error")
        print_separator("-")

def interactive_mode(config: CLIConfig) -> int:
    """交互式菜单模式：提供可视化菜单，支持用户选择不同功能"""
    # 打印欢迎界面（包含系统名称和配置状态）
    print_welcome()

    try:
        # 无限循环：保持菜单持续可用，直到用户选择退出
        while True:
            try:
                # 打印主菜单（显示5个操作选项）
                print_menu()
                # 获取用户输入的选择（1-5），去除首尾空格
                choice = input("Please choose(1-5): ").strip()

                # 选择1：执行研究任务
                if choice == "1":
                    # 调用execute_research函数，传入当前配置
                    execute_research(config)

                # 选择2：查看可用模型
                elif choice == "2":
                    console.print("\n[bold]choose LLM provider[/bold]\n")
                    # 显示提供商选项列表（编号对应）
                    console.print("  [cyan]1[/cyan] - DeepSeek")
                    console.print("  [cyan]2[/cyan] - OpenAI")
                    console.print("  [cyan]3[/cyan] - Claude")
                    console.print("  [cyan]4[/cyan] - Gemini")

                    # 获取用户选择的提供商编号
                    provider_choice = input("\nchoose provider (1-4): ").strip()
                    # 编号与提供商名称的映射字典
                    provider_map = {'1': 'deepseek', '2': 'openai', '3': 'claude', '4': 'gemini'}
                    # 根据编号获取提供商名称
                    provider = provider_map.get(provider_choice)

                    # 若提供商有效，调用show_models显示该提供商的可用模型
                    if provider:
                        show_models(provider)
                    # 若编号无效，提示错误
                    else:
                        console.print("[red]X invalid choice[/red]")

                # 选择3：配置设置
                elif choice == "3":
                    # 调用configure_settings函数，允许用户修改当前配置
                    configure_settings(config)

                # 选择4：查看当前配置
                elif choice == "4":
                    print_separator("-")  # 打印分隔线
                    console.print("[bold cyan]current configuration[/bold cyan]\n")
                    # 黄色显示各配置项的当前值（包含提供商、模型、迭代次数等）
                    console.print(f"  Provider: [yellow]{config.provider}[/yellow]")
                    console.print(f"  Models: [yellow]{config.model}[/yellow]")
                    console.print(f"  Max Iterations: [yellow]{config.max_iterations}[/yellow]")
                    console.print(f"  Auto Approve: [yellow]{'yes' if config.auto_approve else 'no'}[/yellow]")
                    console.print(f"  Output Dir: [yellow]{config.output_dir}[/yellow]")
                    console.print(f"  Output Format: [yellow]{config.output_format.upper()}[/yellow]")
                    console.print(f"  Show Steps: [yellow]{'yes' if config.show_steps else 'no'}[/yellow]")
                    console.print()  # 空行分隔
                    print_separator("-")  # 打印分隔线

                # 选择5：退出程序
                elif choice == "5":
                    console.print("\n[yellow]Thanks for using Deep Research Agent! Goodbye! [/yellow]\n")
                    return 0  # 返回0表示正常退出

                # 无效选择（非1-5）
                else:
                    console.print("[red]X Invalid choice, please choose 1-5[/red]")

            # 捕获用户中断（如Ctrl+C）
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Thank you for using! Goodbye![/yellow]\n")
                return 0  # 正常退出
            # 捕获EOF错误（如输入Ctrl+D）
            except EOFError:
                console.print("\n\n[yellow]Thank you for using! Goodbye![/yellow]\n")
                return 0  # 正常退出
            # 捕获菜单操作中的其他异常
            except Exception as e:
                console.print(f"\n[red]X An error occurred: {e}[/red]\n")

    # 捕获交互式模式初始化或循环外的系统级异常
    except Exception as e:
        console.print(f"\n[red]X System error:  {e}[/red]\n")
        return 1  # 返回1表示异常退出


def run_single_task(config: CLIConfig, query: str) -> int:
    """运行单个任务（命令行模式）：直接执行指定研究问题，不进入交互式菜单"""
    try:
        # 调用execute_research，传入配置和研究问题
        execute_research(config, query)
        return 0  # 执行成功，返回0
    # 捕获执行过程中的异常
    except Exception as e:
        # 向标准错误流打印错误信息
        print(f"[red]X Error: {e}[/red]", file=sys.stderr)
        return 1  # 执行失败，返回1


def parse_args(argv: Any) -> argparse.Namespace:
    """解析命令行参数：处理用户通过命令行传入的参数，生成配置对象"""
    # 先从配置文件加载保存的默认值（若文件存在）
    saved_config = load_config_from_file()

    # 创建参数解析器，设置程序描述
    parser = argparse.ArgumentParser(
        description="Deep Research Agent - multi-agent system based on Lang-graph"
    )

    # 1. 位置参数：研究问题（可选，不提供则进入交互模式）
    parser.add_argument(
        "query",
        nargs="?",  # 允许0或1个参数
        help="Research question or topic (optional; if not provided, enter interactive mode)"
    )

    # 2. 可选参数：LLM提供商（默认值优先取配置文件，其次为deepseek）
    parser.add_argument(
        "--provider",
        default=saved_config.get("provider", "deepseek"),
        choices=["deepseek", "openai", "claude", "gemini"],  # 仅允许预定义选项
        help="LLM provider (default: deepseek)"
    )

    # 3. 可选参数：模型名称（默认值取配置文件，未配置则后续自动填充）
    parser.add_argument(
        "--model",
        default=saved_config.get("model"),
        help="Model name (selected by default according to the provider)"
    )

    # 4. 可选参数：最大研究迭代次数（默认值优先取配置文件，其次为5）
    parser.add_argument(
        "--max-iterations",
        type=int,  # 强制为整数类型
        default=saved_config.get("max_iterations", 5),
        help="Maximum number of research iterations (default: 5)"
    )

    # 5. 可选参数：自动批准研究计划（默认值取配置文件，其次为False）
    parser.add_argument(
        "--auto-approve",
        action="store_true",  # 无需参数，存在则为True
        default=saved_config.get("auto_approve", False),
        help="Auto Approve"
    )

    # 6. 可选参数：报告输出目录（默认值优先取配置文件，其次为./outputs）
    parser.add_argument(
        "--output-dir",
        default=saved_config.get("output_dir", "./outputs"),
        help="Report output directory (default: ./outputs)"
    )

    # 7. 可选参数：报告输出格式（默认值优先取配置文件，其次为markdown）
    parser.add_argument(
        "--output-format",
        default=saved_config.get("output_format", "markdown"),
        choices=["markdown", "html"],  # 仅允许两种格式
        help="Report output format (default: markdown)"
    )

    # 8. 可选参数：显示详细执行步骤（默认值取配置文件，其次为False）
    parser.add_argument(
        "--show-steps",
        action="store_true",  # 无需参数，存在则为True
        default=saved_config.get("show_steps", False),
        help="Show steps"
    )

    # 9. 可选参数：强制启动交互式菜单模式
    parser.add_argument(
        "--interactive",
        action="store_true",  # 无需参数，存在则为True
        help="Start interactive menu mode"
    )

    # 10. 可选参数：显示版本信息
    parser.add_argument(
        "--version",
        action="version",  # 自动处理版本显示
        version="Deep Research System 0.1.0"
    )

    # 解析传入的命令行参数，返回参数命名空间对象
    return parser.parse_args(argv)


def main(argv: Any = None) -> int:
    """主入口函数：程序启动后首先执行，负责初始化和流程分发"""
    # 加载.env文件中的环境变量（如API密钥）
    load_dotenv()
    # 解析命令行参数（若未传入argv，则使用sys.argv[1:]）
    args = parse_args(argv if argv is not None else sys.argv[1:])

    # 检查所选LLM提供商对应的API密钥是否存在
    api_key = get_api_key_for_provider(args.provider)
    if not api_key:
        # 向标准错误流打印缺少API密钥的错误
        print(f"[red]X lacks API key. [/red]", file=sys.stderr)
        print(f"please set {args.provider.upper()}_API_KEY in .env", file=sys.stderr)
        return 2  # 返回2表示API密钥缺失错误

    # 若未指定模型名称，根据提供商自动填充默认模型
    if not args.model:
        model_defaults = {
            'deepseek': 'deepseek-chat',
            'openai': 'gpt-4',
            'claude': 'claude-3-5-sonnet-20241022',
            'gemini': 'gemini-pro'
        }
        args.model = model_defaults.get(args.provider, 'deepseek-chat')

    # 创建CLIConfig实例：将解析后的参数整理为统一的配置对象
    config = CLIConfig(
        provider=args.provider,
        model=args.model,
        max_iterations=args.max_iterations,
        auto_approve=args.auto_approve,
        output_dir=args.output_dir,
        show_steps=args.show_steps,
        output_format=args.output_format,
    )

    # 分支1：若提供了研究问题（query参数），直接执行单个任务
    if args.query:
        return run_single_task(config, args.query)

    # 分支2：若指定了--interactive参数，或未提供query，进入交互式菜单模式
    if args.interactive or not args.query:
        return interactive_mode(config)

    # 默认返回0（正常退出）
    return 0


# 程序入口：若当前脚本被直接运行（而非导入），执行main函数并根据返回值退出
if __name__ == "__main__":
    raise SystemExit(main())        