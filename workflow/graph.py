"""
Research Workflow Graph

This module creates and manages the LangGraph workflow for the research system.
"""
# 从typing模块导入Optional类型：用于标记可选参数
from typing import Optional
# 从langgraph.graph导入核心组件：StateGraph（工作流图）、END（结束节点）、START（开始节点）
from langgraph.graph import StateGraph, END, START
# 从langgraph.checkpoint.memory导入MemorySaver：用于工作流状态的内存存储（检查点）
from langgraph.checkpoint.memory import MemorySaver
# 从当前目录导入ResearchState（研究状态类）和WorkflowNodes（工作流节点类）
from .state import ResearchState
from .nodes import WorkflowNodes
# 从agents模块导入所有智能体类（协调者、规划者、研究者、报告生成者）
from agents.coordinator import Coordinator
from agents.planner import Planner
from agents.researcher import Researcher
from agents.rapporteur import Rapporteur

def create_research_graph(
    coordinator: Coordinator,
    planner: Planner,
    researcher: Researcher,
    rapporteur: Rapporteur
):
    """
    Create the research workflow graph.

    Args:
        coordinator: Coordinator agent instance
        planner: Planner agent instance
        researcher: Researcher agent instance
        rapporteur: Rapporteur agent instance

    Returns:
        Compiled LangGraph workflow
    """
    # Create workflow nodes
    nodes = WorkflowNodes(coordinator, planner, researcher, rapporteur)
    # Initialize state graph
    workflow = StateGraph(dict)
    # Add nodes to the graph
    workflow.add_node("coordinator", nodes.coordinator_node)  # 协调者节点：工作流入口
    workflow.add_node("planner", nodes.planner_node)          # 规划者节点：创建/修改研究计划
    workflow.add_node("human_review", nodes.human_review_node)# 人工审核节点：等待用户批准计划
    workflow.add_node("researcher", nodes.researcher_node)    # 研究者节点：执行信息检索任务
    workflow.add_node("rapporteur", nodes.rapporteur_node)    # 报告生成者节点：生成最终报告
    # Add edges from START instead of using set_entry_point
    # Coordinator -> conditional edge (simple query ends, research continues)
    workflow.add_edge(START, "coordinator")
    workflow.add_conditional_edges(
        "coordinator",                  # 源节点：协调者节点
        nodes.should_continue_to_planner, # 条件判断函数：决定下一步节点
        {                               # 条件结果映射：
            "planner": "planner",      # 结果为"planner"→跳转到规划者节点（研究类查询）
            "end": END                  # 结果为"end"→跳转到END（内置结束节点，简单查询）
        }
    )
    # Planner -> Human Review
    workflow.add_edge("planner", "human_review")
    # Human Review -> conditional edge
    workflow.add_conditional_edges(
        "human_review",                 # 源节点：人工审核节点
        nodes.should_continue_research,  # 条件判断函数：检查计划是否批准
        {                               # 条件结果映射：
            "planner": "planner",       # 结果为"planner"→返回规划者节点（用户需修改计划）
            "researcher": "researcher"  # 结果为"researcher"→跳转到研究者节点（计划已批准）
        }
    )
    # Researcher -> conditional edge
    workflow.add_conditional_edges(
        "researcher",                   # 源节点：研究者节点
        nodes.should_generate_report,    # 条件判断函数：是否需要生成报告
        {                               # 条件结果映射：
            "researcher": "researcher", # 结果为"researcher"→继续执行研究（需更多信息）
            "rapporteur": "rapporteur"  # 结果为"rapporteur"→跳转到报告生成者节点（信息充分）
        }
    )
    # Rapporteur -> END
    workflow.add_edge("rapporteur", END)
    # Compile the graph with checkpointer
    # Add interrupt before human_review for human-in-the-loop
    checkpointer = MemorySaver()  # 创建内存检查点实例（保存工作流状态）
    return workflow.compile(
        checkpointer=checkpointer,       # 传入检查点：支持状态持久化
        interrupt_before=["human_review"]# 在"human_review"节点前中断：等待人工输入
    )

class ResearchWorkflow:
    """
    Research workflow manager.

    This class provides a high-level interface for running the research workflow.
    """
    def __init__(
        self,
        coordinator: Coordinator,
        planner: Planner,
        researcher: Researcher,
        rapporteur: Rapporteur
    ):
        """
        Initialize the research workflow.

        Args:
            coordinator: Coordinator agent
            planner: Planner agent
            researcher: Researcher agent
            rapporteur: Rapporteur agent
        """
        # 保存4个智能体实例到类属性
        self.coordinator = coordinator
        self.planner = planner
        self.researcher = researcher
        self.rapporteur = rapporteur
        # 调用create_research_graph函数创建并保存编译后的工作流图
        self.graph = create_research_graph(
            coordinator, planner, researcher, rapporteur
        )

    # 定义工作流运行方法：同步执行工作流，返回最终研究状态
    def run(
        self,
        query: str,
        max_iterations: Optional[int] = None,
        auto_approve: bool = False,
        output_format: str = "markdown"
    ) -> dict:
        """
        Run the research workflow.

        Args:
            query: Research query
            max_iterations: Maximum number of research iterations
            auto_approve: Whether to auto-approve the research plan
            output_format: Output format for the final report ("markdown" or "html")

        Returns:
            Final research state
        """
        # 代码功能注释：第一步——初始化研究状态（调用协调者的initialize_research方法）
        # Initialize state
        initial_state = self.coordinator.initialize_research(query, auto_approve=auto_approve, output_format=output_format)

        # 若指定了最大迭代次数，更新初始状态
        if max_iterations:
            initial_state['max_iterations'] = max_iterations

        # 代码功能注释：第二步——执行工作流（传入初始状态和线程配置，确保检查点隔离）
        # Run the graph with thread configuration for checkpointer
        config = {"configurable": {"thread_id": "1"}}  # 线程ID：用于区分不同工作流实例的状态
        final_state = self.graph.invoke(initial_state, config=config)  # 同步调用工作流

        # 返回工作流结束后的最终状态
        return final_state

    # 定义工作流流式输出方法：异步生成工作流执行过程中的状态更新
    def stream(
        self,
        query: str,
        max_iterations: Optional[int] = None,
        auto_approve: bool = False,
        output_format: str = "markdown"
    ):
        """
        Stream the research workflow execution.

        Args:
            query: Research query
            max_iterations: Maximum number of research iterations
            auto_approve: Whether to auto-approve the research plan
            output_format: Output format for the final report ("markdown" or "html")

        Yields:
            State updates during execution
        """
        # 代码功能注释：第一步——初始化研究状态（同run方法）
        # Initialize state
        initial_state = self.coordinator.initialize_research(query, auto_approve=auto_approve, output_format=output_format)

        # 若指定了最大迭代次数，更新初始状态
        if max_iterations:
            initial_state['max_iterations'] = max_iterations

        # 代码功能注释：第二步——流式执行工作流（逐个生成节点执行后的状态）
        # Stream the graph execution with thread configuration for checkpointer
        config = {"configurable": {"thread_id": "1"}}
        for output in self.graph.stream(initial_state, config=config):  # 流式调用工作流
            yield output  # 逐个返回状态更新

    # 定义交互式流式输出方法：支持人工审核回调，实现人机交互
    def stream_interactive(
        self,
        query: str,
        max_iterations: Optional[int] = None,
        auto_approve: bool = False,
        human_approval_callback = None,
        output_format: str = "markdown"
    ):
        """
        Stream the research workflow execution with interactive human approval.

        Args:
            query: Research query
            max_iterations: Maximum number of research iterations
            auto_approve: Whether to auto-approve the research plan
            human_approval_callback: Callback function for human approval
                                   Should return (approved: bool, feedback: str)
            output_format: Output format for the final report ("markdown" or "html")

        Yields:
            State updates during execution
        """
        # 代码功能注释：第一步——初始化研究状态（同run方法）
        # Initialize state
        initial_state = self.coordinator.initialize_research(query, auto_approve=auto_approve, output_format=output_format)

        # 若指定了最大迭代次数，更新初始状态
        if max_iterations:
            initial_state['max_iterations'] = max_iterations

        # 设置工作流配置（线程ID确保状态隔离）
        config = {"configurable": {"thread_id": "1"}}

        # 标记是否已处理人工审核（避免重复处理）
        approval_handled = False

        # 代码功能注释：第二步——流式执行工作流，监测中断点（人工审核前）
        # Stream execution
        for output in self.graph.stream(initial_state, config=config):
            # 先返回当前输出（节点执行后的状态）
            yield output

            # 代码功能注释：第三步——检查是否触发中断（人工审核节点前）
            # Check if we hit an interrupt
            if "__interrupt__" in output and not approval_handled:
                # 获取当前工作流的状态快照（从检查点中读取）
                current_snapshot = self.graph.get_state(config)
                current_state = current_snapshot.values

                # 代码功能注释：第四步——确认当前状态需要人工审核（存在研究计划）
                # Check if this state needs approval (we interrupt after planning, before human_review)
                if isinstance(current_state, dict) and current_state.get('research_plan'):
                    # 若启用自动批准，直接标记计划为已批准
                    if auto_approve:
                        current_state['plan_approved'] = True
                        current_state['user_feedback'] = None
                        self.graph.update_state(config, current_state)  # 更新工作流状态
                    # 若未启用自动批准且有审核回调函数，调用回调获取用户输入
                    elif human_approval_callback and not current_state.get('plan_approved', False):
                        # 设置当前步骤为"等待批准"（用于前端显示）
                        current_state['current_step'] = 'awaiting_approval'

                        # 调用审核回调函数，获取用户的批准结果和反馈
                        approved, feedback = human_approval_callback(current_state)

                        # 代码功能注释：第五步——根据用户反馈更新状态
                        # Update the state
                        if approved:
                            current_state['plan_approved'] = True
                            current_state['user_feedback'] = None  # 无反馈（计划通过）
                        else:
                            current_state['plan_approved'] = False
                            current_state['user_feedback'] = feedback  # 保存用户反馈（用于修改计划）

                        # 将更新后的状态写回工作流（检查点）
                        self.graph.update_state(config, current_state)

                # 标记人工审核已处理（避免重复进入）
                approval_handled = True

                # 代码功能注释：第六步——继续执行工作流剩余部分（从审核后节点开始）
                # Continue from this point
                for continue_output in self.graph.stream(None, config=config):
                    yield continue_output
                return  # 处理完审核后退出，避免重复循环
    # 定义获取工作流 schema 的方法：返回工作流的节点和边结构（便于文档或前端展示）
    def get_workflow_schema(self) -> dict:
        """
        Get the workflow schema/structure.

        Returns:
            Workflow schema dictionary
        """
        return {
            "nodes": [  # 工作流包含的所有节点
                "coordinator",
                "planner",
                "human_review",
                "researcher",
                "rapporteur"
            ],
            "edges": [  # 工作流的固定边（节点间的直接连接）
                ("coordinator", "planner"),
                ("planner", "human_review"),
                ("human_review", ["planner", "researcher"]),  # 人工审核的两个可能去向
                ("researcher", ["researcher", "rapporteur"]),# 研究者的两个可能去向
                ("rapporteur", "END")
            ],
            "entry_point": "coordinator",  # 工作流入口节点
            "conditional_edges": [  # 工作流的条件边（带判断逻辑的连接）
                {
                    "from": "human_review",
                    "function": "should_continue_research",  # 判断函数
                    "destinations": ["planner", "researcher"]  # 可能的去向节点
                },
                {
                    "from": "researcher",
                    "function": "should_generate_report",  # 判断函数
                    "destinations": ["researcher", "rapporteur"]  # 可能的去向节点
                }
            ]
        }
# 定义工作流可视化方法：生成Mermaid图（可选保存到文件）
    def visualize(self, output_path: Optional[str] = None) -> str:
        """
        Visualize the workflow graph.

        Args:
            output_path: Optional path to save the visualization

        Returns:
            Path to the visualization file or visualization string
        """
        try:
            # 代码功能注释：尝试生成Mermaid格式的可视化图
            # Try to get graph visualization
            from langgraph.graph import Graph  # 导入Graph类用于绘图

            mermaid = self.graph.get_graph().draw_mermaid()  # 生成Mermaid字符串

            # 若指定输出路径，将Mermaid图保存到文件
            if output_path:
                with open(output_path, 'w') as f:
                    f.write(mermaid)
                return output_path  # 返回文件路径
            else:
                return mermaid  # 直接返回Mermaid字符串
        # 捕获异常（如依赖缺失），返回错误信息
        except Exception as e:
            return f"Visualization not available: {str(e)}"
