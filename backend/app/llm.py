"""Provider-agnostic LLM access with automatic fallback: Groq -> Gemini -> Hugging Face."""
from functools import lru_cache

from .config import settings


@lru_cache
def _candidates() -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    if settings.groq_api_key:
        from langchain_groq import ChatGroq

        out.append(("groq", ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key,
                                     temperature=0.2, max_retries=2)))
        for alt in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]:
            if alt != settings.groq_model:
                out.append(("groq-alt", ChatGroq(model=alt, api_key=settings.groq_api_key,
                                                  temperature=0.2, max_retries=1)))
    if settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        out.append(("gemini", ChatGoogleGenerativeAI(model=settings.gemini_model,
                                                     google_api_key=settings.google_api_key,
                                                     temperature=0.2, max_retries=2)))
    if settings.hf_token:
        try:  # experimental: structured output support varies by model/provider
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

            out.append(("huggingface", ChatHuggingFace(llm=HuggingFaceEndpoint(
                repo_id=settings.hf_model, huggingfacehub_api_token=settings.hf_token, temperature=0.2))))
        except ImportError:
            pass
    if not out:
        raise RuntimeError("No LLM configured. Set GROQ_API_KEY and/or GOOGLE_API_KEY in backend/.env")
    return out


def configured_providers() -> list[str]:
    try:
        return [name for name, _ in _candidates()]
    except RuntimeError:
        return []


def structured_llm(schema):
    """Runnable returning a validated `schema` instance; falls back to the next provider on any error."""
    runnables = [m.with_structured_output(schema) for _, m in _candidates()]
    first, *rest = runnables
    return first.with_fallbacks(rest) if rest else first
