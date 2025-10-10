"""
LLM Base Class

Defining the abstract base class for all LLM providers.
"""

# 从abc模块导入ABC（抽象基类的基类）和abstractmethod（用于定义抽象方法）
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Iterator

class BaseLLM(ABC):
    """
    any llm class should inherit from this abstract class

    """

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text according to the prompt

        Args:
            prompt
            **kwargs: additional generating parameters（eg. temperature、max_tokens等）

        Returns:
            text response
        """
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> Iterator[str]:
        """
        Streaming text generation (starting from the prompt).

        Args:
            prompt
            **kwargs: additional generating parameters

        Yields:
            Text chunks generated during the generation process
        """
        pass

    def __repr__(self) -> str:
         """The string representation of an LLM instance."""
         return f"{self.__class__.__name__}(model={self.model})"