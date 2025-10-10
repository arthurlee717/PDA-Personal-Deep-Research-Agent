"""
Coordinator Agent which serves as the entry point
and orchestrator for the research workflow.

"""
# 从typing模块导入类型注解：Dict（字典）、Optional（可选类型）、Any（任意类型）
from typing import Dict, Optional, Any
# 从llm/base模块导入BaseLLM抽象基类，确保协调器使用的LLM符合统一接口
from llm.base import BaseLLM
# 从prompts/loader模块导入PromptLoader，用于加载预设的提示词模板
from prompts.loader import PromptLoader

class Coordinator:
    """
    Coordinator agent - the entry point for research workflow.

    Responsibilities:
    - Receive user research requests
    - Classify query type (greeting, inappropriate, or research)
    - Handle simple queries directly (greetings, inappropriate requests)
    - Initialize research workflow state for complex queries
    - Delegate research tasks to the Planner
    - Manage user-system interaction
    - Handle workflow lifecycle
    """

    def __init__(self, llm: BaseLLM):
        """
        Initialize the Coordinator.

        Args:
            llm: Language model instance for processing
        """
        self.llm = llm
        self.prompt_loader = PromptLoader()

    def classify_query(self, user_query: str) -> str:
        """
        Classify the user query type.

        Args:
            user_query: User's input query

        Returns:
            Query type: 'GREETING', 'INAPPROPRIATE', or 'RESEARCH'
        """

        prompt = self.prompt_loader.load(
            'coordinator_classify_query',
            user_query = user_query
        )
        # 开发者添加的代码功能注释：解释llm.generate方法的作用——向大语言模型输入提示词并获取输出
        #.generate(prompt)：调用 llm 对象的 generate 方法，作用是向大语言模型输入 “提示词（prompt）”，并让模型生成对应输出
        # 调用大语言模型生成分类结果，去除首尾空格并转为大写（统一格式）
        query_type = self.llm.generate(prompt).strip().upper()

        #validate classification
        if query_type not in ['GREETING', 'INAPPROPRIATE', 'RESEARCH']:
            query_type = 'RESEARCH'

        return query_type
    
    def handle_simple_query(self, user_query: str, query_type: str) -> str:
        """
        Handle simple queries that don't require research.

        Args:
            user_query: User's input query
            query_type: Type of query ('GREETING' or 'INAPPROPRIATE')

        Returns:
            Direct response to the user
        """
        prompt = self.prompt_loader.load(
            'coordinator_simple_response',
            user_query = user_query,
            query_type=query_type
        )

        response = self.llm.generate(prompt).strip()
        return response
    
    def initialize_research(self, user_query: str, auto_approve: bool = False, output_format: str = "markdown") -> Dict[str, Any]:
        """
        Initialize a new research task.

        Args:
            user_query: User's research question/request
            auto_approve: Whether to auto-approve the research plan
            output_format: Output format for the final report ("markdown" or "html")

        Returns:
            Initialized research state
        """
        query_type = self.classify_query(user_query)
        # create initial state
        state = {
            'query': user_query,  # 存储用户原始研究查询
            'query_type': query_type,  # Add query type to state：存储查询分类结果
            'research_plan': None,  # 存储研究计划，初始为None（未生成）
            'plan_approved': False,  # 存储计划是否批准，初始为False（未批准）
            'research_results': [],  # 存储研究结果集合，初始为空列表
            'current_task': None,  # 存储当前执行的任务，初始为None（无任务）
            'iteration_count': 0,  # 存储已执行的迭代次数，初始为0
            'max_iterations': 5,  # Default maximum iterations：默认最大迭代次数（防止无限循环）
            'final_report': None,  # 存储最终报告，初始为None（未生成）
            'current_step': 'initializing',  # 存储当前工作流步骤，初始为"initializing"（初始化中）
            'needs_more_research': True,  # 存储是否需要继续研究，初始为True
            'user_feedback': None,  # 存储用户反馈，初始为None
            'auto_approve': auto_approve,  # Add auto_approve flag to state：存储自动批准开关状态
            'simple_response': None,  # For storing direct responses to simple queries：存储简单查询的回复
            'output_format': output_format  # Add output format to state：存储最终报告的输出格式
        }

        # handle simple queries directly
        if query_type in ['GREETING', 'INAPPROPRIATE']:
            state['simple_response'] = self.handle_simple_query(user_query, query_type)
            state['current_step'] = 'completed'
            state['needs_more_research'] = False

        return state
    
    def process_user_input(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """
        Process user feedback or input.

        Args:
            state: Current research state
            user_input: User's input text

        Returns:
            Updated research state
        """

        #store user feedback
        state['user_feedback'] = user_input
        #analyze user intent
        prompt = self.prompt_loader.load(
            'coordinator_analyze_intent',
            user_input=user_input,
            current_step=state['current_step']
        )

        intent = self.llm.generate(prompt).strip().upper()

        #update state based on intent
        if intent == "APPROVE":
            state['plan_approved'] = True

        elif intent == "MODIFY":
            state['plan_approved'] = False
            # Plan will be revised by Planner
        # 若意图为"REJECT"（拒绝），将计划批准状态设为False并清空现有计划
        elif intent == "REJECT":
            state['plan_approved'] = False
            state['research_plan'] = None
        # 代码注释：若意图为"QUESTION"（提问），不修改状态，由Planner后续处理
        # For QUESTION, we keep state as is and let Planner handle it

        # 返回更新后的研究状态
        return state
    
    def delegate_to_planner(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate the task to Planner.

        Args:
            state: Current research state

        Returns:
            Updated research state with delegation info
        """
        state['current_step'] = 'planning'
        return state
    
    def handle_completion(self, state: Dict[str, Any]) -> Dict:
        """
        Handle workflow completion.

        Args:
            state: Final research state

        Returns:
            Completion summary
        """
        return {
            'status': 'completed',
            'query': state['query'],
            'iterations': state['iteration_count'],
            'report': state['final_report'],
            'total_results': len(state['research_results'])
        }
def __repr__(self) -> str:
    """String representation."""
    return f"Coordinator(llm={self.llm})"

