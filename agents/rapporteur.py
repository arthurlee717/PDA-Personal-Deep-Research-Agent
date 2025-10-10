"""
Rapporteur Agent, for generating the final research report.

"""
# 从typing模块导入类型注解：Dict（字典类型）、List（列表类型）
from typing import Dict, List
# 从datetime模块导入datetime类：用于生成报告的时间戳
from datetime import datetime
# 从workflow/state模块导入ResearchState类：约束研究状态的数据格式
from workflow.state import ResearchState
# 从llm/base模块导入BaseLLM抽象类：约束报告生成使用的大语言模型需符合统一接口
from llm.base import BaseLLM
# 从prompts/loader模块导入PromptLoader类：用于加载报告生成相关的提示词模板
from prompts.loader import PromptLoader

class Rapporteur:
    """
    Rapporteur agent - report generation component.

    Responsibilities:
    - Summarize research findings
    - Organize collected information
    - Generate structured reports (Markdown or HTML)
    - Format citations and references
    - Ensure report coherence and readability
    """
    def __init__(self, llm: BaseLLM):
        """
        Initialize the Rapporteur.

        Args:
            llm: Language model instance for report generation
        """
        self.llm = llm
        self.prompt_loader = PromptLoader()

    def generate_report(self, state: ResearchState) -> ResearchState:
        """
        Generate a comprehensive research report.

        Args:
            state: Current research state with all research results

        Returns:
            Updated state with final report
        """
        query = state['query']  # 用户原始研究查询（报告标题依据）
        plan = state.get('research_plan', {})  # 研究计划（无则空字典）
        results = state.get('research_results', [])  # 研究结果列表（无则空列表）
        output_format = state.get('output_format', 'markdown')  # 报告输出格式（默认Markdown）

        summary = self._summarize_findings(query, results)
        # Organize information
        organized_info = self._organize_information(summary, results)

        #generate report based on format
        if output_format == 'html':
            report = self._generate_html_report(
                query=query,
                plan=plan,
                summary=summary,
                organized_info=organized_info,
                results=results
            )

        else:
            # default format: markdown
            report = self._generate_markdown_report(
                query=query,
                plan=plan,
                summary=summary,
                organized_info=organized_info,
                results=results
            )
             # Update state
        state['final_report'] = report  # 将最终报告存入状态
        state['current_step'] = 'completed'  # 将当前工作流步骤标记为"completed"（已完成）

        return state
    
    def _summarize_findings(self, query: str, results: List[Dict]) -> str:
        """
        Summarize all research findings.

        Args:
            query: Research query
            results: List of research results

        Returns:
            Summary of findings
        """
        all_content = []
        for result in results: #Each result is a collection of outcomes from a single search.
            for item in result.get('results', []): #Each item is a specific search result
                title = item.get('title', 'No title')
                snippet = item.get('snippet', '')[:300]
                all_content.append(f"- {title}: {snippet}")  # 按格式添加到列
        content_text = '\n'.join(all_content[:30]) #limit to 30 items
        prompt = self.prompt_loader.load(
            'rapporteur_summarize',  # 提示词模板名称（用于总结研究发现）
            query=query,  # 传入用户查询（明确总结目标）
            research_findings=content_text  # 传入整理后的结果片段
        )

        summary = self.llm.generate(prompt, temperature= 0.5, max_tokens=2000)
        return summary
    
    def _organize_information(self, summary: str, results: List[Dict]) -> Dict:
        """
        Organize information into structured sections.

        Args:
            summary: Research summary
            results: List of research results

        Returns:
            Organized information structure
        """
        prompt = self.prompt_loader.load(
            'rapporteur_organize_info', 
            summary=summary  # 传入研究摘要（提取主题的依据）
        )

        response = self.llm.generate(prompt, temperature=0.5)

        import json
        try:
            start = response.find('{')  # 找到第一个"{"（JSON起始）
            end = response.rfind('}') + 1  # 找到最后一个"}"并+1（包含闭合符号）
            # 若成功定位JSON边界，解析为Python字典
            if start != -1 and end > start:
                json_str = response[start:end]  # 截取纯JSON字符串
                organized = json.loads(json_str)  # 解析为结构化字典
                return organized  # 返回解析后的结构化信息
        # 捕获JSON解析异常（如模型返回格式错误）
        except json.JSONDecodeError:
            pass  # 解析失败则跳过，使用后续备用结构

        return{
            'themes': [  # 主题列表（仅1个基础主题）
                {
                    'name': 'core finding',  # 主题名称
                    'key_points': [summary[:750] ] # 核心要点（截取摘要前500字符）
                }
            ]
        }
    def _generate_markdown_report(
        self,
        query: str,
        plan: Dict,
        summary: str,
        organized_info: Dict,
        results: List[Dict]
    ) -> str:
        # 方法文档字符串：说明方法功能（生成Markdown报告）、参数和返回值
        """
        Generate a structured Markdown report.

        Args:
            query: Research query
            plan: Research plan
            summary: Research summary
            organized_info: Organized information
            results: Research results

        Returns:
            Markdown formatted report
        """
        # 代码功能注释：初始化报告章节列表（用列表拼接字符串更高效）
        # Build report sections
        sections = []

        # 代码功能注释：1. 添加报告标题（一级标题，基于用户查询）
        # Title
        sections.append(f"# Research Report: {query}\n")

        # 代码功能注释：2. 添加报告元数据（生成时间、研究目标、信息来源数量）
        # Metadata
        # 生成当前时间戳（格式：年-月-日 时:分:秒）
        sections.append(f"**Generating Time** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        # 提取研究计划中的研究目标（无则用用户查询）
        sections.append(f"**Research Goal: ** {plan.get('research_goal', query) if plan else query}\n")
        # 统计信息来源数量（研究结果列表的长度）
        sections.append(f"**Information Sources: ** {len(results)}\n")

        # 代码功能注释：3. 添加执行摘要章节（二级标题+研究摘要）
        # Executive Summary
        sections.append("\n## Executive Summary\n")
        sections.append(summary)

        # 代码功能注释：4. 添加核心发现章节（按主题组织，二级标题+主题列表）
        # Key Findings (organized by themes)
        sections.append("\n## Key Findings\n")
        # 遍历结构化信息中的主题列表（无则空列表）
        for theme in organized_info.get('themes', []):
            sections.append(f"\n### {theme['name']}\n")  # 主题名称（三级标题）
            # 遍历当前主题的核心要点（无则空列表），按列表项格式添加
            for point in theme.get('key_points', []):
                sections.append(f"- {point}\n")

        # 代码功能注释：5. 添加深度分析章节（调用私有方法生成整合分析）
        # Synthesized Analysis (NEW: generate integrated analysis instead of simple listing)
        sections.append("\n## Synthesized Analysis\n")
        sections.append(self._generate_synthesized_analysis(query, summary, organized_info, results))

        # 代码功能注释：6. 添加参考资料章节（调用私有方法格式化引用）
        # References
        sections.append("\n## References\n")
        sections.append(self._format_citations(results))

        # 代码功能注释：7. 添加结论章节（调用私有方法生成结论）
        # Conclusion
        sections.append("\n## Conclusion\n")
        sections.append(self._generate_conclusion(query, summary))

        # 将所有章节拼接为完整Markdown字符串，返回报告
        return '\n'.join(sections)
    def _format_detailed_results(self, results: List[Dict]) -> str:
        """
        Format detailed results section.

        Args:
            results: Research results

        Returns:
            Formatted results string
        """
        formatted = []
        result_num = 1
        for result in results:
            source = result.get('source', 'Unknown')
            query = result.get('query', 'N/A')
            formatted.append(f"\n### Source: {source.capitalize()}\n")
            formatted.append(f"**Query:** {query}\n")
            for item in result.get('results', [])[:5]:  # Top 5 per source
                title = item.get('title', 'No title')  # 条目标题（无则"No title"）
                snippet = item.get('snippet', 'No description')  # 条目摘要（无则"No description"）
                url = item.get('url', '')  # 条目链接（无则空字符串）

                formatted.append(f"{result_num}. **{title}**")  # 带编号的标题（加粗）
                if url:  # 若有链接，添加链接信息
                    formatted.append(f"   - URL: {url}")
                # 添加摘要（截取前450字符，避免过长）
                formatted.append(f"   - {snippet[:450]}...\n")
                result_num += 1  # 编号自增

        # 将格式化结果列表拼接为字符串，返回
        return '\n'.join(formatted)
    
    def _format_citations(self, results: List[Dict]) -> str:
        """
        Format citations and references.

        Args:
            results: Research results

        Returns:
            Formatted citations
        """
        citations = []
        citation_num = 1
        for result in results:
            # 遍历当前来源的每个结果条目（每个条目对应一个引用）
            for item in result.get('results', []):
                title = item.get('title', 'Untitled')  # 条目标题（无则"Untitled"）
                url = item.get('url', '')  # 条目链接（无则空字符串）
                source = result.get('source', 'Unknown')  # 信息来源（无则"Unknown"）

                # 按格式添加引用：有链接则生成Markdown超链接，无链接则仅文本
                if url:
                    citations.append(f"{citation_num}. {title} - {source.capitalize()} - [{url}]({url})")
                else:
                    citations.append(f"{citation_num}. {title} - {source.capitalize()}")

                citation_num += 1  # 编号自增

        # 拼接引用列表为字符串，最多显示50条（避免引用过长），返回
        return '\n'.join(citations[:50])  # Limit to 50 citations
    def _generate_synthesized_analysis(
        self,
        query: str,
        summary: str,
        organized_info: Dict,
        results: List[Dict]
    ) -> str:
        """
        Generate synthesized analysis that integrates all findings.

        Args:
            query: Research query
            summary: Research summary
            organized_info: Organized themes
            results: Research results

        Returns:
            Integrated analysis text
        """
        # Extract key content from results
        key_content = []
        for result in results[:10]:  # Limit to first 10 results
            for item in result.get('results', [])[:3]:  # Top 3 per result
                key_content.append(f"- {item.get('snippet', '')[:300]}")

        content_text = '\n'.join(key_content)

        prompt = self.prompt_loader.load(
            'rapporteur_synthesized_analysis',
            query=query,
            summary=summary[:1500],
            key_content=content_text
        )

        analysis = self.llm.generate(prompt, temperature=0.6, max_tokens=2000)
        return analysis
    
    def _generate_conclusion(self, query: str, summary: str) -> str:
        """
        Generate a conclusion section.

        Args:
            query: Research query
            summary: Research summary

        Returns:
            Conclusion text
        """
        prompt = self.prompt_loader.load(
        'rapporteur_conclusion',
        query=query,
        summary=summary[:1500]
    )
        conclusion = self.llm.generate(prompt, temperature=0.5, max_tokens = 800)

        return conclusion 
    
    def _generate_html_report(
        self,
        query: str,
        plan: Dict,
        summary: str,
        organized_info: Dict,
        results: List[Dict]
    ) -> str:
        """
        Generate a structured HTML report.

        Args:
            query: Research query
            plan: Research plan
            summary: Research summary
            organized_info: Organized information
            results: Research results

        Returns:
            HTML formatted report
        """
        analysis = self._generate_synthesized_analysis(query, summary,organized_info, results)
        conclusion = self._generate_conclusion(query, summary)
        # Format themes as HTML-friendly text
        themes_text = ""  # 初始化HTML主题内容字符串
        # 遍历主题列表（无则空列表）
        for theme in organized_info.get('themes', []):
            # 主题名称使用<h3>标签
            themes_text += f"<h3>{theme['name']}</h3>\n<ul>\n"
            # 核心要点使用无序列表<ul><li>标签
            for point in theme.get('key_points', []):
                themes_text += f"<li>{point}</li>\n"
            themes_text += "</ul>\n"  # 闭合无序列表标签

        # 代码功能注释：第三步——格式化参考资料（调用已有私有方法）
        # Format citations
        citations = self._format_citations(results)
        # Generate HTML using LLM
        prompt = self.prompt_loader.load(
            'rapporteur_generate_html',  # 提示词模板名称（用于生成HTML）
            query=query,  # 用户查询（用于标题）
            research_goal=plan.get('research_goal', query) if plan else query,  # 研究目标（无则用查询）
            summary=summary,  # 执行摘要
            themes=themes_text,  # 核心发现（已转为HTML片段）
            analysis=analysis,  # 深度分析
            citations=citations,  # 参考资料
            conclusion=conclusion  # 结论
        )
        html_report = self.llm.generate(prompt, temperature=0.3, max_tokens=4000)
        # Clean up the HTML (remove markdown code blocks if LLM added them)
        if '```html' in html_report:
            html_report = html_report.split('```html')[1].split('```')[0].strip()
    # 若包含通用```标记，同样提取中间部分
        elif '```' in html_report:
            html_report = html_report.split('```')[1].split('```')[0].strip()

        # 返回最终清理后的HTML报告
        return html_report
    
    def save_report(self, report: str, filepath: str) -> bool:
        """
        Save report to file.

        Args:
            report: Report content
            filepath: Path to save the report

        Returns:
            True if successful, False otherwise
        """
        try:
        # 以写模式、UTF-8编码打开文件，写入报告内容
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            # 成功则返回True
            return True
    # 捕获所有可能的异常
        except Exception as e:
        # 打印错误信息（包含异常详情）
            print(f"Error saving report: {e}")
            # 失败则返回False
            return False

# 定义类的字符串表示方法：返回实例的可读字符串，便于调试
    def __repr__(self) -> str:
        """String representation."""
        # 返回包含大语言模型信息的Rapporteur实例字符串
        return f"Rapporteur(llm={self.llm})"