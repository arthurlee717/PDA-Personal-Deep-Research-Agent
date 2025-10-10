from typing import List, Dict, Optional, Any
# 导入datetime用于生成时间戳
from datetime import datetime
# 导入httpx用于异步HTTP请求
import httpx

class MCPClient:
    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'

    async def search(
            self,
            query: str,
            tool_name: str = "web_search",
            **kwargs
    ) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/tools/{tool_name}",
                    json={
                        "query":query,
                        **kwargs
                    },
                    headers=self.headers
                )
                response.raise_for_status()

                data = response.json()

                results = []

                for item in data.get('results', []):
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        # 优先使用snippet，如果不存在则使用content
                        'snippet': item.get('snippet', item.get('content', '')),
                        'relevance_score': item.get('score'),
                        'metadata': item.get('metadata', {})
                    })

                return {
                    'query': query,
                    'source': 'mcp',
                    'tool': tool_name,
                    'results': results,
                    'timestamp': datetime.now().isoformat(),
                    'total_results': len(results)
                }
        except Exception as e:
            # 异常处理：返回包含错误信息的字典
            return {
                'query': query,
                'source': 'mcp',
                'tool': tool_name,
                'results': [],
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    async def list_tools(self) -> List[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.server_url}/tools",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json().get('tools', [])
            
        except Exception as e:
            return []
    async def execute_tool(
            self,
            tool_name: str,
            parameters: Dict[str, Any]
    ) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.server_url}/tools/{tool_name}",
                    json=parameters,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            
        except Exception as e:
            return {
                'error': str(e),
                'tool': tool_name
            }