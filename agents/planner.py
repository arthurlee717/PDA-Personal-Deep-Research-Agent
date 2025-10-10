"""
Planner Agent

This module implements the Planner agent, which is responsible for
creating and managing research plans.
"""

# 导入json模块：用于解析和生成JSON格式数据（研究计划多为JSON结构）
import json
# 从typing模块导入类型注解：
# Dict[str, X]定义字典类型，List[X]定义列表类型，Optional[X]表示变量可为X类型或None
from typing import Dict, List, Optional
# 从workflow/state模块导入自定义状态类：
# ResearchState（研究状态）、PlanStructure（计划结构）、SubTask（子任务），约束数据格式
from workflow.state import ResearchState, PlanStructure, SubTask
# 从llm/base模块导入BaseLLM抽象类：约束规划者使用的大语言模型需符合统一接口
from llm.base import BaseLLM
# 从prompts/loader模块导入PromptLoader类：用于加载预设的提示词模板
from prompts.loader import PromptLoader

class Planner:
    """
    Planner agent - strategic planning component.

    Responsibilities:
    - Analyze research objectives
    - Create structured research plans
    - Break down complex tasks into subtasks
    - Accept and process user modifications
    - Evaluate context sufficiency
    - Decide when to continue research or generate report
    """

    def __init__(self, llm: BaseLLM):
        """
        Initialize the Planner.

        Args:
            llm: Language model instance for planning
        """
        self.llm = llm
        self.prompt_loader = PromptLoader()

    def create_research_plan(self, state: ResearchState) -> ResearchState:
        """
        Create a research plan based on the query.

        Args:
            state: Current research state

        Returns:
            Updated state with research plan
        """
        query = state['query']
        user_feedback = state.get('user_feedback', '')  # 从研究状态中提取用户反馈（若存在则用于优化计划，默认空字符串）
        prompt = self.prompt_loader.load(
            'planner_create_plan',
            query = query,
            user_feedback=user_feedback if user_feedback else None
        )

        response = self.llm.generate(prompt, temperature=0.7)
        try:
            start = response.find('{') #json start position
            end = response.rfind('}') + 1 #json end position, +1 make it including closing
            if start != -1 and end >start:
                json_str = response[start:end] #extract the pure json string
                plan = json.loads(json_str) #parse to python dict
            else:
                plan = self._create_fallback_plan(query)

            # 设置研究计划和最大迭代次数
            state['research_plan'] = plan
            state['max_iterations'] = plan.get('estimated_iterations', 3)
            
            # 为每个子任务设置状态
            for task in plan.get('sub_task', []): # iterate（遍历）through the list of subtasks in the plan(or an empty list if there are none)
                task['status'] = 'pending'
        except json.JSONDecodeError:
            plan = self._create_fallback_plan(query)
            state['research_plan'] = plan

        return state
    
    def _create_fallback_plan(self, query: str) -> PlanStructure:
        """
        Create a simple fallback plan if JSON parsing fails.

        Args:
            query: Research query

        Returns:
            Basic research plan
        """
        return {
            'research_goal': query,  # 研究目标=用户原始查询
            'sub_tasks': [  # 子任务列表（仅1个基础任务）
                {
                    'task_id': 1,  # 任务ID（唯一标识）
                    'description': f'Research: {query}',  # 任务描述（明确研究内容）
                    'search_queries': [query],  # 搜索关键词（默认用原始查询）
                    'sources': ['tavily'],  # 数据来源（默认用tavily搜索引擎）
                    'status': 'pending',  # 任务状态（待执行）
                    'priority': 1  # 任务优先级（最高优先级）
                }
            ],
            'completion_criteria': 'Gather sufficient information to answer the query',  # 完成标准（收集足够信息回答查询）
            'estimated_iterations': 2  # 预估迭代次数（默认2次）
        }
    
    def modify_plan(self, state: ResearchState, modifications: str) -> ResearchState:
        """
        Modify the research plan based on user feedback.

        Args:
            state: Current research state
            modifications: User's modification requests

        Returns:
            Updated state with modified plan
        """
        current_plan = state['research_plan']
        prompt = self.prompt_loader.load(
            'planner_modify_plan',
            current_plan=json.dumps(current_plan, indent=2),
            modifications=modifications
        )

        response = self.llm.generate(prompt, temperature=0.7)
        try:
            start = response.find('{')  # 定位JSON起始
            end = response.rfind('}') + 1  # 定位JSON结束
            if start != -1 and end > start:
                json_str = response[start:end]  # 截取JSON片段
                modified_plan = json.loads(json_str)  # 解析为修改后的计划
                state['research_plan'] = modified_plan  # 更新状态中的计划
        # 捕获JSON解析异常
        except json.JSONDecodeError:
            # 代码功能注释：解析失败时，保留当前计划不修改
            # Keep current plan if parsing fails
            pass

        # 返回更新后的研究状态（可能包含修改后计划或原计划）
        return state

    def evaluate_context_sufficiency(self, state: ResearchState) -> bool:
        """
        Evaluate whether gathered context is sufficient.

        Args:
            state: Current research state

        Returns:
            True if context is sufficient, False otherwise
        """
        query = state['query']
        plan = state['research_plan']
        results = state['research_results']
        iteration = state['iteration_count']
        max_iterations = state['max_iterations']

        if iteration >= max_iterations:
            return False
        if not results:
            return False
        
        prompt = self.prompt_loader.load(
            'planner_evaluate_context',
            query=query,
            research_goal=plan.get('research_goal', query),  # 研究目标（无则用原始查询）
            completion_criteria=plan.get('completion_criteria', 'N/A'),  # 完成标准（无则标N/A）
            results_count=len(results),  # 研究结果数量
            current_iteration=iteration + 1,  # 当前迭代次数（+1是因为迭代从0开始计数，用户易理解）
            max_iterations=max_iterations

        )
        response = self.llm.generate(prompt, temperature=0.3).strip().upper()
        return response == "YES"

    def get_next_task(self, state: ResearchState) -> Optional[SubTask]: #return sub tasks or None
        """
        Get the next pending task from the plan.

        Args:
            state: Current research state

        Returns:
            Next task to execute, or None if all tasks completed
        """
        plan = state.get('research_plan')
        if not plan:
            return None
        tasks = sorted(
            plan.get('sub_tasks' , []),
            key = lambda t: (t.get('priority' , 99), t.get('task_id', 0))

        )

        for task in tasks:
            if task.get('status') =='pending':
                return task
            
        return None

    def format_plan_for_display(self, plan: PlanStructure) -> str:
        """
        Format plan for display to user.

        Args:
            plan: Research plan

        Returns:
            Formatted plan string
        """
        output = []
        output.append(f"=Ë Research Goal: {plan.get('research_goal', 'N/A')}") #Mark with special symbols to enhance readability
        output.append(f"\n=Ê Estimated Iterations: {plan.get('estimated_iterations', 'N/A')}")
        # 添加完成标准
        output.append(f"\n Completion Criteria: {plan.get('completion_criteria', 'N/A')}")
        # 添加子任务标题（空两行分隔，增强结构）
        output.append("\n\n=Ý Subtasks:")

        for task in plan.get('sub_tasks', []):
            output.append(f"\n  {task['task_id']}. {task['description']}")  # 任务ID和描述
            output.append(f"     Queries: {', '.join(task.get('search_queries', []))}")  # 搜索关键词（用逗号连接列表）
            output.append(f"     Sources: {', '.join(task.get('sources', []))}")  # 数据来源（用逗号连接列表）
            output.append(f"     Priority: {task.get('priority', 'N/A')}")  # 优先级（无则标N/A）
            output.append(f"     Status: {task.get('status', 'pending')}")  # 状态（默认待执行）

        # 将列表中的所有字符串拼接为一个完整的展示文本，返回给用户
        return ''.join(output)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Planner(llm={self.llm})"

