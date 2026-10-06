"""PydanticAI entry point and wiring for the Campus Customs shop agent."""
from pathlib import Path
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
try:
    from .models import ChatResponse
    from .tools import AgentDeps, check_stock, get_product_details, search_products
except ImportError:  # Supports direct imports when Uvicorn runs from backend/.
    from models import ChatResponse
    from tools import AgentDeps, check_stock, get_product_details, search_products

BASE_DIR = Path(__file__).resolve().parent

def make_agent(api_key: str, model_name: str = 'gpt-5.6-luna') -> tuple[Agent, AsyncOpenAI]:
    client = AsyncOpenAI(api_key=api_key, base_url='https://api.portkey.ai/v1', default_headers={'x-portkey-api-key': api_key, 'x-portkey-provider': 'openai'})
    model = OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))
    prompt = (BASE_DIR / 'prompts' / 'prompt.md').read_text(encoding='utf-8')
    agent = Agent(model, deps_type=AgentDeps, output_type=ChatResponse, system_prompt=prompt, tools=[search_products, get_product_details, check_stock], retries=2)
    return agent, client
