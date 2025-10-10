"""
Researcher Agent, which is responsible for 
executing information retrieval tasks.
"""
# 从typing模块导入类型注解：Dict（字典）、List（列表）、Optional（可选类型）
from typing import Dict, List, Optional
# 从workflow/state模块导入自定义状态类：
# ResearchState（研究状态）、SubTask（子任务）、SearchResult（搜索结果）
from workflow.state import ResearchState, SubTask, SearchResult
# 从tools模块导入搜索工具类：
# TavilySearch（Tavily搜索引擎）、ArxivSearch（arXiv论文检索）、MCPClient（MCP服务客户端）
from tools.tavily_search import TavilySearch
from tools.arxiv_search import ArxivSearch
from tools.mcp_client import MCPClient
# 从llm/base模块导入BaseLLM抽象类：约束研究者使用的大语言模型需符合统一接口
from llm.base import BaseLLM
# 从prompts/loader模块导入PromptLoader类：用于加载研究者相关的提示词模板
from prompts.loader import PromptLoader
class Researcher:
    # 类文档字符串：详细说明研究者的定位和核心职责
    """
    Researcher agent - information collection component.

    Responsibilities:
    - Execute information retrieval tasks
    - Search from multiple data sources
    - Filter and organize search results
    - Aggregate results from different sources
    - Extract relevant information
    """

    # 类的构造方法：初始化研究者实例，接收大语言模型和可选的API密钥/服务地址
    def __init__(
        self,
        llm: BaseLLM,
        tavily_api_key: Optional[str] = None,
        mcp_server_url: Optional[str] = None,
        mcp_api_key: Optional[str] = None
    ):
        # 构造方法的文档字符串：说明初始化参数的含义和用途
        """
        Initialize the Researcher.

        Args:
            llm: Language model instance for processing
            tavily_api_key: Tavily API key (optional)
            mcp_server_url: MCP server URL (optional)
            mcp_api_key: MCP API key (optional)
        """
        # 保存传入的大语言模型实例到类属性：用于后续信息提取和总结
        self.llm = llm
        # 初始化TavilySearch工具：若提供API密钥则创建实例，否则为None
        self.tavily = TavilySearch(tavily_api_key) if tavily_api_key else None
        # 初始化ArxivSearch工具：无需API密钥，直接创建实例
        self.arxiv = ArxivSearch()
        # 初始化MCPClient工具：若提供服务地址则创建实例，否则为None
        self.mcp = MCPClient(mcp_server_url, mcp_api_key) if mcp_server_url else None
        # 创建PromptLoader实例并保存到类属性：用于加载研究者相关的提示词模板
        self.prompt_loader = PromptLoader()

    # 定义任务执行方法：接收当前研究状态和待执行任务，返回更新后的状态
    def execute_task(self, state: ResearchState, task: SubTask) -> ResearchState:
        # 方法文档字符串：说明方法功能（执行研究任务）、参数和返回值
        """
        Execute a research task.

        Args:
            state: Current research state
            task: Task to execute

        Returns:
            Updated state with research results
        """
        # 初始化空列表，用于存储本次任务的搜索结果
        results = []

        # 代码功能注释：遍历任务中的每个搜索关键词和每个指定数据源，执行搜索
        # Execute searches for each query
        for query in task.get('search_queries', []):  # 遍历任务中的搜索关键词列表（无则空列表）
            for source in task.get('sources', []):  # 遍历任务中的数据源列表（无则空列表）
                # 调用私有方法_search执行搜索，传入关键词和数据源
                result = self._search(query, source)
                # 若搜索成功（result非空），添加任务ID并加入结果列表
                if result:
                    result['task_id'] = task['task_id']  # 标记结果所属任务ID
                    results.append(result)

        # 代码功能注释：将本次任务的搜索结果添加到研究状态中
        # Add results to state
        # 若状态中尚无'research_results'字段，先创建空列表
        if 'research_results' not in state:
            state['research_results'] = []

        # 将本次任务的搜索结果追加到状态的'research_results'列表中
        state['research_results'].extend(results)

        # 代码功能注释：将已完成的任务在研究计划中标记为"completed"（已完成）
        # Mark task as completed
        # 若状态中存在研究计划
        if state.get('research_plan'):
            # 遍历计划中的所有子任务
            for t in state['research_plan'].get('sub_tasks', []):
                # 找到与当前任务ID匹配的子任务
                if t.get('task_id') == task['task_id']:
                    t['status'] = 'completed'  # 将其状态更新为"completed"
                    break  # 找到后立即退出循环

        # 返回包含新搜索结果的更新状态
        return state
    def _search(self, query: str, source: str) -> Optional[SearchResult]:
        # 方法文档字符串：说明方法功能（执行特定来源的搜索）、参数和返回值
        """
        Perform search using specified source.

        Args:
            query: Search query
            source: Source name ('tavily', 'arxiv', 'mcp')

        Returns:
            Search results or None
        """
        # 使用try-except捕获搜索过程中的异常
        try:
            # 若数据源为'tavily'且tavily工具已初始化，执行tavily搜索
            if source == 'tavily' and self.tavily:
                return self.tavily.search(query)
            # 若数据源为'arxiv'，执行arxiv搜索
            elif source == 'arxiv':
                return self.arxiv.search(query)
            # 若数据源为'mcp'且mcp工具已初始化，执行mcp搜索（MCP为异步，需用asyncio.run调用）
            elif source == 'mcp' and self.mcp:
                import asyncio  # 局部导入asyncio模块
                return asyncio.run(self.mcp.search(query))
            # 若数据源不支持或工具未初始化，返回None
            else:
                return None
        # 捕获所有可能的异常
        except Exception as e:
            # 异常情况下返回包含错误信息的字典（仍保持SearchResult基本结构）
            return {
                'query': query,  # 搜索关键词
                'source': source,  # 数据源
                'results': [],  # 空结果列表
                'error': str(e)  # 错误详情字符串
            }
    def aggregate_results(self, results: List[SearchResult]) -> Dict:
        # 方法文档字符串：说明方法功能（聚合搜索结果）、参数和返回值
        """
        Aggregate and organize search results.

        Args:
            results: List of search results

        Returns:
            Aggregated results summary
        """
        # 代码功能注释：按数据源对结果进行分组
        # Group results by source
        by_source = {}  # 用于存储按来源分组的结果字典
        for result in results:
            source = result.get('source', 'unknown')  # 获取来源（无则"unknown"）
            if source not in by_source:
                by_source[source] = []  # 若该来源首次出现，创建空列表
            by_source[source].append(result)  # 将结果添加到对应来源的列表中

        # 代码功能注释：计算总体统计信息（结果总数）
        # Calculate statistics
        total_results = sum(len(r.get('results', [])) for r in results)

        # 返回包含聚合统计的字典：总搜索次数、总结果数、按来源的详细统计
        return {
            'total_searches': len(results),  # 总搜索次数（每次调用数据源为一次）
            'total_results': total_results,  # 所有搜索返回的结果条目总数
            'by_source': {  # 按来源的详细统计
                source: {
                    'count': len(source_results),  # 该来源的搜索次数
                    'total_items': sum(len(r.get('results', [])) for r in source_results)  # 该来源返回的结果条目总数
                }
                for source, source_results in by_source.items()
            }
        }
    
    def extract_relevant_info(self, state: ResearchState) -> str:
        # 方法文档字符串：说明方法功能（提取相关信息）、参数和返回值
        """
        Extract relevant information from all research results.

        Args:
            state: Current research state

        Returns:
            Extracted and summarized information
        """
        # 从状态中获取所有研究结果（无则空列表）
        results = state.get('research_results', [])

        # 若没有研究结果，直接返回提示信息
        if not results:
            return "No research results available."

        # 代码功能注释：整理所有搜索结果条目，提取关键字段
        # Compile all search results
        all_items = []  # 用于存储所有结果条目的列表
        for result in results:
            for item in result.get('results', []):
                all_items.append({
                    'source': result.get('source'),  # 数据来源
                    'query': result.get('query'),  # 搜索关键词
                    'title': item.get('title'),  # 条目标题
                    'snippet': item.get('snippet'),  # 条目摘要
                    'url': item.get('url')  # 条目链接
                })

        # 代码功能注释：调用大语言模型提取并总结相关信息
        # Use LLM to extract and summarize
        # 加载名为"researcher_extract_info"的提示词模板，传入研究问题和格式化的结果条目（限制前20条）
        prompt = self.prompt_loader.load(
            'researcher_extract_info',
            query=state['query'],
            search_results=self._format_results_for_prompt(all_items[:20])  # Limit to top 20 results
        )

        # 调用大语言模型生成信息摘要，temperature=0.5（平衡创造性与准确性）
        summary = self.llm.generate(prompt, temperature=0.5)
        # 返回生成的信息摘要
        return summary
    def _format_results_for_prompt(self, items: List[Dict]) -> str:
        # 方法文档字符串：说明方法功能（格式化结果用于提示词）、参数和返回值
        """
        Format search results for LLM prompt.

        Args:
            items: List of search result items

        Returns:
            Formatted string
        """
        # 初始化空列表，用于存储格式化后的结果条目
        formatted = []
        # 遍历结果条目并编号（从1开始）
        for i, item in enumerate(items, 1):
            # 添加带编号的来源和标题
            formatted.append(f"\n{i}. [{item.get('source')}] {item.get('title', 'No title')}")
            # 添加链接（无则显示"N/A"）
            formatted.append(f"   URL: {item.get('url', 'N/A')}")
            # 添加摘要（截取前300字符，无则显示"No snippet"）
            formatted.append(f"   {item.get('snippet', 'No snippet')[:300]}...")

        # 将格式化列表拼接为单个字符串，返回
        return '\n'.join(formatted)
    
    def __repr__(self) -> str:
        """String representation."""
        sources = []  # 用于存储已初始化的数据源名称列表
        if self.tavily:
            sources.append('tavily')
        if self.arxiv:
            sources.append('arxiv')
        if self.mcp:
            sources.append('mcp')
        # 返回包含支持的数据源的研究者实例字符串
        return f"Researcher(sources={sources})"