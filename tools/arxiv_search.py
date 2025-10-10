"""
arXiv Search Tool

"""
from typing import List, Dict, Optional
# 导入arxiv库，用于调用arXiv的API接口（获取学术论文数据）
import arxiv
# 从datetime模块导入datetime类，用于生成时间戳
from datetime import datetime

class ArxivSearch:
    def __init__(self):
        self.client = arxiv.Client()

    def search(
            self,
            query: str,
            max_results: int = 5,
            sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance,
            sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending
    ) -> Dict:
        try:
            serach = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )

            results = [] #store the papers data

            for paper in self.client.results(serach):
                results.append({
                    'title': paper.title,  # 论文标题
                    'url': paper.entry_id,  # 论文在arXiv的唯一链接（entry ID）
                    'snippet': paper.summary,  # 论文摘要（作为结果预览片段）
                    'relevance_score': None,  # 相关性分数（arXiv API不提供该字段，故设为None）
                    'metadata': {  # 论文元数据（详细信息）
                        'authors': [author.name for author in paper.authors],  # 作者列表（提取每个作者的姓名）
                        'published': paper.published.isoformat() if paper.published else None,  # 发表时间（转为ISO格式字符串，无则为None）
                        'updated': paper.updated.isoformat() if paper.updated else None,  # 更新时间（同上）
                        'categories': paper.categories,  # 论文所属分类（如cs.AI表示计算机科学-人工智能）
                        'primary_category': paper.primary_category,  # 主要分类
                        'pdf_url': paper.pdf_url,  # 论文PDF的直接下载链接
                        'doi': paper.doi,  # DOI编号（数字对象标识符，部分论文有）
                        'journal_ref': paper.journal_ref,  # 期刊引用信息（如发表在某期刊的卷期页）
                        'comment': paper.comment  # 论文备注（如页数、会议信息等）
                    }
                })

            return {
                'query': query,  # 原始搜索关键词（便于追溯）
                'source': 'arxiv',  # 数据来源（明确是arXiv）
                'results': results,  # 格式化后的论文列表
                'timestamp': datetime.now().isoformat(),  # 搜索执行的时间戳（ISO格式）
                'total_results': len(results)  # 实际返回的结果数量
            }
        except Exception as e:
            # error case
            return {
                'query': query,
                'source': 'arxiv',
                'results': [],  # empty result list
                'timestamp': datetime.now().isoformat(),
                'error': str(e)  # 
            }
        
    def get_paper_by_id(self, paper_id: str) -> Optional[Dict]:
        try:
            search= arxiv.Search(id_list=[paper_id])
            paper = next(self.client.results(search))

            return{
                'title': paper.title,
                'url': paper.entry_id,
                'summary': paper.summary,  # 完整摘要（区别于search方法的snippet，此处无截断）
                'authors': [author.name for author in paper.authors],
                'published': paper.published.isoformat() if paper.published else None,
                'pdf_url': paper.pdf_url,
                'categories': paper.categories
            }
                
        except Exception as e:
            return None
        
    def download_pdf(self, paper_id: str, dirpath: str = "./") -> Optional[str]:
        try:
            search = arxiv.Search(id_list=[paper_id])
            paper = next(self.client.results(search))

            filepath = paper.download_pdf(dirpath=dirpath)
            return filepath
        except Exception as e:
            return None
