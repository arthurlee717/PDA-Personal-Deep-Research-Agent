# 导入操作系统相关功能（用于路径处理）
import os
# 导入Path类（用于更便捷的文件路径操作）
from pathlib import Path
# 导入类型注解（Dict字典类型、Any任意类型）
from typing import Dict, Any
# 导入datetime类（用于生成当前时间）
from datetime import datetime
# 导入Jinja2相关模块（用于模板加载和渲染，Jinja2是Python常用的模板引擎）
from jinja2 import Environment, FileSystemLoader, Template

class PromptLoader:
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = Path(prompts_dir)

        self.env = Environment(
            loader = FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
    def load(self, prompt_name: str, **variables: Any) -> str:
        if 'CURRENT_TIME' not in variables:
            variables['CURRENT_TIME'] = datetime.now().strftime('%Y-%m-%D %H:%M:%S')
        try:
            template = self.env.get_template(f"{prompt_name}.md")
            rendered = template.render(**variables)
            return rendered
        except Exception as e:
            raise FileNotFoundError(
                f"Could not load prompt '{prompt_name}' from {self.prompts_dir}: {e}"
            )
        
    def load_raw(self, prompt_name: str) -> str:
        prompt_path = self.prompts_dir / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}"
            )
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
        
    def render_string(self, template_str: str, **variables: Any) ->str:
        if 'CURRENT_TIME' not in variables:
            variables['CURRENT_TIME'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 创建Jinja2 Template对象（基于传入的字符串模板）
        template = Template(template_str)
        # 渲染模板并返回结果
        return template.render(**variables)
    
_default_loader = None
def get_default_loader() -> PromptLoader:
    global _default_loader
    if _default_loader is None:
        _default_loader = PromptLoader()
    return _default_loader