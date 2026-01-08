"""
AI Manager - Refactored to use multi-provider system

Uses ai_providers.py for:
- Ollama (optimized with streaming, 32K context, model selector)
- OpenAI (fallback)
- Claude (fallback)
"""
import json
from typing import Generator, Optional
from backend.utils.logger import logger
from backend.core.ai_providers import (
    get_provider,
    complete_with_fallback,
    stream_with_fallback,
    ProviderError,
    AllProvidersFailed
)


class AIManager:
    """
    AI Manager with multi-provider support.
    
    Optimizations:
    - Streaming responses
    - 32K context window for Ollama
    - Intelligent model selection
    - Automatic fallback chain
    """
    
    def __init__(self, provider: str = None):
        """
        Initialize AI Manager.
        
        Args:
            provider: Provider name (ollama, openai, claude) or None for env default
        """
        self.provider = get_provider(provider)
        logger.info(f"AIManager initialized with provider: {self.provider.name}")
    
    def check_connection(self) -> bool:
        """Check if the current provider is available"""
        return self.provider.is_available()
    
    # =========================================================================
    # GENERIC METHODS
    # =========================================================================

    def generate_text(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        """
        Generate text from a raw prompt (bypassing preset types).
        """
        try:
            return complete_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="creative_writing"
            )
        except Exception as e:
            logger.error(f"Generate text failed: {e}")
            return f"Error: {str(e)}"

    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================
    
    def analyze_text(self, text: str, prompt_type: str = "copy_analysis") -> str:
        """
        Analyze text (non-streaming).
        
        Args:
            text: Text to analyze
            prompt_type: Type of analysis prompt
        
        Returns:
            Analysis result
        """
        system_prompt = self._get_system_prompt(prompt_type)
        
        # Truncate text to fit context (leave room for system prompt and response)
        max_text = 25000  # ~6K tokens, leaving room in 32K context
        truncated = text[:max_text] + "..." if len(text) > max_text else text
        
        prompt = f"TEXTO DO SITE:\n{truncated}"
        
        try:
            return complete_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="copy_analysis"
            )
        except AllProvidersFailed as e:
            logger.error(f"All providers failed: {e}")
            return f"Erro: Nenhum provedor de IA disponível. {str(e)}"
    
    def analyze_text_stream(
        self,
        text: str,
        prompt_type: str = "copy_analysis"
    ) -> Generator[str, None, None]:
        """
        Analyze text with streaming response.
        
        Args:
            text: Text to analyze
            prompt_type: Type of analysis prompt
        
        Yields:
            Text chunks as they are generated
        """
        system_prompt = self._get_system_prompt(prompt_type)
        max_text = 25000
        truncated = text[:max_text] + "..." if len(text) > max_text else text
        prompt = f"TEXTO DO SITE:\n{truncated}"
        
        try:
            yield from stream_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="copy_analysis"
            )
        except AllProvidersFailed as e:
            yield f"Erro: {str(e)}"
    
    def analyze_structure(self, json_data: dict, prompt_type: str = "funnel_critique") -> str:
        """
        Analyze JSON structure (funnel map, etc).
        
        Args:
            json_data: Structure to analyze
            prompt_type: Type of analysis
        
        Returns:
            Analysis result
        """
        system_prompt = self._get_system_prompt(prompt_type)
        
        data_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        max_data = 15000
        truncated = data_str[:max_data] + "..." if len(data_str) > max_data else data_str
        
        prompt = f"DADOS ESTRUTURAIS:\n{truncated}"
        
        try:
            return complete_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="quick_analysis"
            )
        except AllProvidersFailed as e:
            return f"Erro na análise estrutural: {str(e)}"
    
    def analyze_structure_stream(
        self,
        json_data: dict,
        prompt_type: str = "funnel_critique"
    ) -> Generator[str, None, None]:
        """Streaming version of analyze_structure"""
        system_prompt = self._get_system_prompt(prompt_type)
        data_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        max_data = 15000
        truncated = data_str[:max_data] + "..." if len(data_str) > max_data else data_str
        prompt = f"DADOS ESTRUTURAIS:\n{truncated}"
        
        try:
            yield from stream_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="quick_analysis"
            )
        except AllProvidersFailed as e:
            yield f"Erro: {str(e)}"
    
    # =========================================================================
    # CONTENT GENERATION
    # =========================================================================
    
    def generate_content(self, context_data: str, prompt_type: str = "b2b_lead_magnet") -> str:
        """
        Generate content based on context.
        
        Args:
            context_data: Context information
            prompt_type: Type of content to generate
        
        Returns:
            Generated content
        """
        system_prompt = self._get_generation_prompt(prompt_type)
        
        max_context = 10000
        truncated = context_data[:max_context] if len(context_data) > max_context else context_data
        
        prompt = f"CONTEXTO DO PRODUTO/SERVIÇO:\n{truncated}"
        
        try:
            return complete_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="content_generation"
            )
        except AllProvidersFailed as e:
            return f"Erro ao gerar conteúdo: {str(e)}"
    
    def generate_content_stream(
        self,
        context_data: str,
        prompt_type: str = "b2b_lead_magnet"
    ) -> Generator[str, None, None]:
        """Streaming version of generate_content"""
        system_prompt = self._get_generation_prompt(prompt_type)
        max_context = 10000
        truncated = context_data[:max_context] if len(context_data) > max_context else context_data
        prompt = f"CONTEXTO DO PRODUTO/SERVIÇO:\n{truncated}"
        
        try:
            yield from stream_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="content_generation"
            )
        except AllProvidersFailed as e:
            yield f"Erro: {str(e)}"
    
    # =========================================================================
    # PROPOSAL GENERATION
    # =========================================================================
    
    def generate_proposal(
        self,
        lead_data: dict,
        clone_data: dict
    ) -> str:
        """
        Generate a commercial proposal combining lead and clone data.
        
        Args:
            lead_data: Lead information
            clone_data: Cloned funnel data
        
        Returns:
            Generated proposal in Markdown
        """
        system_prompt = self._get_system_prompt("proposal_generator")
        
        prompt = f"""
DADOS DO LEAD:
{json.dumps(lead_data, indent=2, ensure_ascii=False)}

DADOS DO CLONE (FUNIL):
{json.dumps(clone_data, indent=2, ensure_ascii=False)}

Gere uma proposta comercial irrecusável combinando esses dados.
"""
        
        try:
            return complete_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="content_generation"
            )
        except AllProvidersFailed as e:
            return f"Erro ao gerar proposta: {str(e)}"
    
    def generate_proposal_stream(
        self,
        lead_data: dict,
        clone_data: dict
    ) -> Generator[str, None, None]:
        """Streaming version of generate_proposal"""
        system_prompt = self._get_system_prompt("proposal_generator")
        
        prompt = f"""
DADOS DO LEAD:
{json.dumps(lead_data, indent=2, ensure_ascii=False)}

DADOS DO CLONE (FUNIL):
{json.dumps(clone_data, indent=2, ensure_ascii=False)}

Gere uma proposta comercial irrecusável combinando esses dados.
"""
        
        try:
            yield from stream_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="content_generation"
            )
        except AllProvidersFailed as e:
            yield f"Erro: {str(e)}"
    
    # =========================================================================
    # PROMPT LOADERS
    # =========================================================================
    
    def _get_generation_prompt(self, p_type: str) -> str:
        """Load generation prompt from knowledge base"""
        try:
            from backend.core.knowledge.dotcom_secrets import DOTCOM_GENERATION_PROMPTS
            if p_type in DOTCOM_GENERATION_PROMPTS:
                return DOTCOM_GENERATION_PROMPTS[p_type]
        except ImportError:
            pass
            
        try:
            from backend.core.knowledge.marketing_40 import MKT40_GENERATION_PROMPTS
            if p_type in MKT40_GENERATION_PROMPTS:
                return MKT40_GENERATION_PROMPTS[p_type]
        except ImportError:
            pass

        try:
            from backend.core.knowledge.commercial_proposals import COMMERCIAL_PROPOSAL_PROMPTS
            if p_type in COMMERCIAL_PROPOSAL_PROMPTS:
                return COMMERCIAL_PROPOSAL_PROMPTS[p_type]
        except ImportError:
            pass
            
        return "Gere um texto de vendas para este produto."

    def _get_system_prompt(self, p_type: str) -> str:
        """Load system prompt from knowledge base"""
        # Marketing 4.0 Integration (Priority)
        try:
            from backend.core.knowledge.marketing_40 import MKT40_SYSTEM_PROMPTS
            if p_type in MKT40_SYSTEM_PROMPTS:
                return MKT40_SYSTEM_PROMPTS[p_type]
        except ImportError:
            pass

        # DotCom Secrets
        try:
            from backend.core.knowledge.dotcom_secrets import DOTCOM_SYSTEM_PROMPTS
            if p_type in DOTCOM_SYSTEM_PROMPTS:
                return DOTCOM_SYSTEM_PROMPTS[p_type]
        except ImportError:
            pass

        # Default prompts
        prompts = {
            "copy_analysis": """Você é um especialista em Marketing Digital e Copywriting de Resposta Direta.
Analise o texto da página de vendas a seguir. Identifique e explique:
1. A Grande Promessa (Big Promise).
2. O Mecanismo Único (se houver).
3. As principais Dores e Desejos explorados.
4. Gatilhos Mentais utilizados.
5. Nível de Consciência do Público Alvo.

Responda em Tópicos e Português.""",

            "funnel_strategy": """Você é um Estrategista de Funis de Vendas.
Analise o conteúdo desta página e deduza a estratégia:
1. Qual o objetivo desta página?
2. Qual a oferta principal?
3. Há indícios de Order Bump ou Upsell?
4. Pontos fortes e fracos da estrutura.

Responda de forma analítica e resumida.""",

            "funnel_critique": """Você é um Especialista em CRO (Conversion Rate Optimization) e Funnel Hacking.
Analise o fluxo JSON abaixo que representa os passos de um funil (Página -> CTA -> Próxima Página).
Critique a lógica e sugira melhorias:
1. O fluxo faz sentido lógico?
2. Os CTAs (textos dos botões) são persuasivos ou genéricos?
3. Há muitos passos (fricção) ou poucos passos?
4. Sugira 1 melhoria concreta para aumentar a conversão.

Responda em Tópicos curtos.""",

            "swipe_rewrite": """Você é um Copywriter Sênior.
Reescreva a IDEIA CENTRAL desta copy para um nicho genérico, criando um 'Swipe File' (modelo).
Extraia a estrutura lógica da persuasão para que possa ser usada em outros produtos.
Não copie o texto, extraia a ESTRUTURA.""",

            "proposal_generator": """Você é um Consultor de Crescimento (Growth Consultant) especializado em Funis de Vendas.
Seu objetivo é gerar uma PROPOSTA IRRECUSÁVEL (Pitch Kit) cruzando dois contextos:
1. O CONTEXTO DO LEAD (O alvo): Suas dores, nicho e presença digital atual (ou falta dela).
2. O CONTEXTO DO CLONE (A Solução): A estrutura de alta conversão que você clonou e quer adaptar para o Lead.

Gere um documento Markdown estruturado assim:
# Proposta de Aceleração Digital para [Nome do Lead]

## 1. O Diagnóstico (Dores)
Cite 3 pontos fracos da presença atual deles (baseado nos dados do Lead).

## 2. A Solução (O Funil [Nome do Clone])
Explique por que a estrutura do Clone (ex: Quiz, VSL, High Ticket) é perfeita para eles.

## 3. A Estratégia (O Match)
Sugira:
- Como adaptar a Headline do Clone para o Lead.
- Que isca digital (Lead Magnet) usar.
- Qual a oferta principal.

## 4. O Próximo Passo
Um CTA agressivo para fechar o contrato.

Seja direto, persuasivo e use dados reais fornecidos."""
        }
        
        return prompts.get(p_type, "Analise este texto.")
