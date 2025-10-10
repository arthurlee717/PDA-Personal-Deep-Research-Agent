from typing import List, Dict, Optional
# 从tavily库导入TavilyClient类，用于调用Tavily的Web搜索API
from tavily import TavilyClient
# 从datetime模块导入datetime类，用于生成搜索时间戳
from datetime import datetime

class TavilySearch:
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)
    def search(
            self,
            query: str,
            max_results: int=5,
            search_depth: str="advanced",
            include_domains: Optional[List[str]] = None,
            exclude_domains: Optional[List[str]] = None
    ) -> Dict:
        try:
            response = self.client.search(
                query=query,          # 搜索关键词
                max_results=max_results,  # 最大结果数
                search_depth=search_depth,  # 搜索深度
                include_domains=include_domains,  # 包含域名
                exclude_domains=exclude_domains   # 排除域名            
            )

            results = []

            for item in response.get('results', []):
                results.append({
                    'title': item.get('title', ''),  # 结果标题（如网页标题、文章标题）
                    'url': item.get('url', ''),      # 结果对应的网页URL
                    'snippet': item.get('content', ''),  # 结果摘要（网页内容片段，便于快速预览）
                    'relevance_score': item.get('score', 0.0),  # 相关性分数（Tavily计算，0-1之间，分数越高越相关）
                    'metadata': {  # 结果元数据（补充信息）
                        'published_date': item.get('published_date'),  # 内容发布时间（如"2024-05-20"，部分结果有）
                        'raw_content': item.get('raw_content')        # 原始内容（完整网页文本，部分结果有）
                    }
                })
            return{
                'query': query,          # 原始搜索关键词（便于追溯搜索意图）
                'source': 'tavily',      # 数据来源（明确是Tavily搜索）
                'results': results,      # 格式化后的结果列表
                'timestamp': datetime.now().isoformat(),  # 搜索执行时间戳（ISO格式，如"2024-05-20T14:30:00"）
                'total_results': len(results)  # 实际返回的结果数量
            }
        
        except Exception as e:
            return {
                'query': query,
                'source': 'tavily',
                'results': [],  # 结果列表为空（无有效结果）
                'timestamp': datetime.now().isoformat(),
                'error': str(e)  # 错误详情（转为字符串，如"Invalid API key"）
            }
    def get_search_context(
        self,
        query: str,
        max_results: int = 5           
    ) -> str:
        try:
            context = self.client.get_search_context(
                query=query,
                max_results=max_results
            )
            return context
        except Exception as e:
            return f"Error retrieving search context: {str(e)}"

