"""
LLM Factory pattern for llm instances

"""
# 从typing模块导入Optional，用于标注可选类型的参数（如model参数可传None）
from typing import Optional
# 从当前目录的base模块导入BaseLLM抽象基类，确保工厂创建的LLM实例都遵循统一接口
from .base import BaseLLM

class LLMFactory:
    """
    A factory class 
    used to create instances of LLM (Large Language Model).
    This factory allows for easy instantiation of different 
    LLM providers (such as OpenAI, Claude)
    without the need to directly import the corresponding
    LLM classes when using them.

    """
    # class level private dict，用于存储已注册的LLM提供商：key是提供商名称（小写），value是对应的LLM类
    _providers = {}

    @classmethod
    def register_provider(cls, name: str, provider_class):
        cls._providers[name.lower()] = provider_class

    @classmethod
    def create_llm(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLM:
        provider = provider.lower()
        if provider not in cls._providers:
            cls._lazy_load_provider(provider)

        if provider not in cls._providers:
            available = ','.join(cls._providers.key())
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Available providers: {available}"
            )
        llm_class = cls._providers[provider]
        if model:
            return llm_class(api_key=api_key, model=model, **kwargs)
        else:
            # 若未传入model，使用LLM类的默认模型（依赖LLM类自身的__init__默认参数）
            return llm_class(api_key=api_key, **kwargs)
        
    @classmethod
    def _lazy_load_provider(cls, provider: str): #Import only when necessary to reduce resource consumption during initialization
        try:
            if provider =="openai":
                from .openai_llm import OpenAILLM
                cls.register_provider('openai', OpenAILLM)
            elif provider == 'claude':
                # 导入Claude的LLM类（假设文件名为claude_llm.py）
                from .claude_llm import ClaudeLLM
                cls.register_provider('claude', ClaudeLLM)
            elif provider == 'gemini':
                # 导入Gemini的LLM类（假设文件名为gemini_llm.py）
                from .gemini_llm import GeminiLLM
                cls.register_provider('gemini', GeminiLLM)
            elif provider == 'deepseek':
                # 导入DeepSeek的LLM类（对应之前实现的DeepSeekLLM，文件名为deepseek_llm.py）
                from .deepseek_llm import DeepSeekLLM
                cls.register_provider('deepseek', DeepSeekLLM)
        except ImportError as e:
            # Provider module not available
            pass

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered providers.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
