# TypedDict用于定义有类型约束的字典结构，List表示列表，Annotated用于添加元数据，Optional表示值可None，Any表示任意类型
from typing import TypedDict, List, Annotated, Optional, Any
# 导入operator模块，用于获取加法运算符（此处用于LangGraph的状态合并配置）
import operator

class ResearchState(TypedDict):
    query: str
    research_plan: Optional[dict]
    plan_approved: bool
    research_results: Annotated[list, operator.add]
    current_task: Optional[dict]
    iteration_count: int
    max_iterations: int
    final_report: Optional[str]
    current_step: str
    needs_more_research: bool
    user_feedback: Optional[str]
    output_format: str

class PlanStructure(TypedDict):
    research_goal: str
    sub_tasks: List[dict]
    completion_criteria: str
    estimated_iterations: int

class SubTask(TypedDict):
    task_id: int
    description: str
    search_queries: List[str]
    sources: List[str]
    status: str
    priority: Optional[int]

class SearchResult(TypedDict):
    task_id: int
    query: str
    source: str
    results: List[dict]
    timestamp: str

class IndividualResult(TypedDict):
    title: str
    url: Optional[str]
    snippet: str
    relevance_score: Optional[float]
    metadata: Optional[dict]

