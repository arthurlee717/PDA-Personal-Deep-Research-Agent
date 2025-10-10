# 从typing模块导入字典和任意类型的注解，用于定义节点函数的输入输出类型
from typing import Dict, Any
# 从agents模块中导入四个核心智能体类：协调者、规划者、研究者、报告生成者
from agents.coordinator import Coordinator
from agents.planner import Planner
from agents.researcher import Researcher
from agents.rapporteur import Rapporteur

class WorkflowNodes:
    """
    Container for workflow node functions.
    """

    def __init__(
        self,
        coordinator: Coordinator,
        planner: Planner,
        researcher: Researcher,
        rapporteur: Rapporteur
    ):
        """
        Initialize workflow nodes.

        Args:
            coordinator: Coordinator agent instance
            planner: Planner agent instance
            researcher: Researcher agent instance
            rapporteur: Rapporteur agent instance
        """
        self.coordinator = coordinator
        self.planner = planner
        self.researcher = researcher
        self.rapporteur = rapporteur

    def coordinator_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinator node - entry point of the workflow.

        Args:
            state: Current research state

        Returns:
            Updated state
        """
        if state.get('query_type') in ['GREETING', 'INAPPROPRIATE']:
            # 简单查询已在initialize_research中处理，标记步骤为完成
            state['current_step'] = 'completed'
            return state

        # 对于研究类查询，委托给planner节点
        state['current_step'] = 'coordinating'
        state = self.coordinator.delegate_to_planner(state)
        return state
    def planner_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planner node - creates or updates research plan.

        Args:
            state: Current research state

        Returns:
            Updated state with research plan
        """
        # 标记当前步骤为规划中
        state['current_step'] = 'planning'

        # 如果有用户反馈且已有研究计划，修改计划
        if state.get('user_feedback') and state.get('research_plan'):
            state = self.planner.modify_plan(state, state['user_feedback'])
        # 否则创建新计划
        elif not state.get('research_plan'):
            state = self.planner.create_research_plan(state)

        return state
    def human_review_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Human review node - pauses for user approval.

        Args:
            state: Current research state

        Returns:
            Updated state
        """
        # 标记当前步骤为等待批准
        state['current_step'] = 'awaiting_approval'

        # 检查是否启用自动批准
        if state.get('auto_approve', False):
            state['plan_approved'] = True

        # 实际实现中会暂停等待用户输入，此处仅标记状态
        return state

    def researcher_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Researcher node - executes research tasks.

        Args:
            state: Current research state

        Returns:
            Updated state with research results
        """
        # 标记当前步骤为研究中
        state['current_step'] = 'researching'

        # 从计划中获取下一个任务
        next_task = self.planner.get_next_task(state)

        if next_task:
            # 先增加迭代次数，再执行任务
            state['iteration_count'] += 1  # 迭代次数加1
            # 执行任务
            state = self.researcher.execute_task(state, next_task)
            state['current_task'] = next_task  # 记录当前执行的任务
        else:
            # 没有更多任务，标记无需继续研究
            state['needs_more_research'] = False

        return state

    def rapporteur_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rapporteur node - generates final report.

        Args:
            state: Current research state

        Returns:
            Updated state with final report
        """
        # 标记当前步骤为生成报告中
        state['current_step'] = 'generating_report'
        # 调用rapporteur生成报告并更新状态
        state = self.rapporteur.generate_report(state)
        return state
    
    def should_continue_to_planner(self, state: Dict[str, Any]) -> str:
        """
        Conditional edge function - determines if we continue to planner or end.

        Args:
            state: Current research state

        Returns:
            Next node name: "planner" for research queries, "end" for simple queries
        """
        # 如果是简单查询（问候或不适当内容），结束工作流
        if state.get('query_type') in ['GREETING', 'INAPPROPRIATE']:
            return "end"

        # 否则，继续到planner节点进行研究
        return "planner"

    def should_continue_research(self, state: Dict[str, Any]) -> str:
        """
        Conditional edge function - determines next step after human review.

        Args:
            state: Current research state

        Returns:
            Next node name
        """
        # 如果计划未批准，返回planner节点
        if not state.get('plan_approved'):
            return "planner"

        # 如果计划已批准，开始研究，返回researcher节点
        return "researcher"

    def should_generate_report(self, state: Dict[str, Any]) -> str:
        """
        Conditional edge function - determines if we should generate report.

        Args:
            state: Current research state

        Returns:
            Next node name
        """
        # 检查是否达到最大迭代次数
        if state['iteration_count'] >= state['max_iterations']:
            return "rapporteur"

        # 检查上下文是否充分
        if self.planner.evaluate_context_sufficiency(state):
            return "rapporteur"

        # 检查是否有更多任务
        next_task = self.planner.get_next_task(state)
        if next_task:
            return "researcher"
        else:
            return "rapporteur"
        
def create_node_functions(
    coordinator: Coordinator,
    planner: Planner,
    researcher: Researcher,
    rapporteur: Rapporteur
) -> WorkflowNodes:
    """
    Create workflow node functions.

    Args:
        coordinator: Coordinator agent
        planner: Planner agent
        researcher: Researcher agent
        rapporteur: Rapporteur agent

    Returns:
        WorkflowNodes instance
    """
        # 创建并返回WorkflowNodes实例，用于工作流中的节点函数
    return WorkflowNodes(coordinator, planner, researcher, rapporteur)