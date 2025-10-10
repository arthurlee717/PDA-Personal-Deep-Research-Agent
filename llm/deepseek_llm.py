"""
DeepSeek LLM Implementation which uses OPENAI-compatible API

Thus we can use the OpenAI client.
"""

from typing import Iterator
from openai import OpenAI
from .base import BaseLLM

class DeepSeekLLM(BaseLLM):
    """
    The specific implementation class of the DeepSeek large language model.
    It  supports the DeepSeek series models through an API compatible with 
    OpenAI.
    """
    def __init__(
            self,
            api_key: str,
            model: str = "deepseek-chat",
            base_url: str = "https://api.deepseek.com",
            **kwargs
    ):
        # 调用父类BaseLLM的初始化方法，传入API密钥、模型名和额外配置
        super().__init__(api_key, model, **kwargs)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def generate(self, prompt, **kwargs) -> str:
        """
        Generate complete text (non-streaming) via the DeepSeek API。

        Args:
            prompt
            **kwargs
        Returns:
            Generated text
        """
        params = {**self.config, **kwargs}
        response = self.client.chat.completions.create(
            model=self.model,
            messages = [{"role" : "user", "content": prompt}],
            **params
        )

        return response.choices[0].message.content
    def stream_generate(self, prompt, **kwargs) -> Iterator[str]:
        params = {**self.config, **kwargs}
        stream = self.client.chat.completions.create(
            model=self.model,
            messages = [{"role" : "user", "content": prompt}],
            **params
        )

        for chunk in stream:
            if chunk.choices[0].data.content is not None:
                yield chunk.choices[0].delta.content
                #delta.content: 当前片段的 实际文本内容（如果模型还在生成中，content 是文本片段；如果生成结束，content 会是 None）。
                #yield: 创建 生成器（Generator） , “返回一个片段，暂停函数执行，下次调用时从暂停处继续”。