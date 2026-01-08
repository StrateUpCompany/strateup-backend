"""
LGPD Consent Management Module

Gerencia consentimentos de usuários para coleta e processamento de dados
em conformidade com a Lei Geral de Proteção de Dados (LGPD).
"""
from datetime import datetime
from typing import Optional, Dict, Any
from backend.core.supabase_manager import SupabaseManager
from backend.utils.logger import logger


class LGPDConsentManager:
    """
    Gerenciador de consentimentos LGPD.
    
    Registra e valida consentimentos de usuários para:
    - Coleta de dados (Data Hunter)
    - Uso de cookies/analytics
    - Email marketing
    """
    
    CONSENT_TYPES = {
        "data_collection": "Coleta de dados de leads",
        "cookies": "Uso de cookies e analytics",
        "email_marketing": "Envio de emails promocionais",
        "third_party": "Compartilhamento com terceiros"
    }
    
    def __init__(self):
        self.db = SupabaseManager()
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Registra um consentimento do usuário.
        
        Args:
            user_id: ID do usuário
            consent_type: Tipo de consentimento (data_collection, cookies, etc)
            granted: True se consentiu, False se recusou
            ip_address: IP do usuário (para auditoria)
            user_agent: Browser/dispositivo do usuário
            metadata: Dados adicionais
            
        Returns:
            Registro do consentimento criado
        """
        if consent_type not in self.CONSENT_TYPES:
            raise ValueError(f"Tipo de consentimento inválido: {consent_type}")
        
        consent_record = {
            "user_id": user_id,
            "consent_type": consent_type,
            "granted": granted,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0"  # Versão da política de privacidade
        }
        
        try:
            result = await self.db.insert("lgpd_consents", consent_record)
            logger.info(f"Consent recorded: {user_id} - {consent_type} = {granted}")
            return result
        except Exception as e:
            logger.error(f"Failed to record consent: {e}")
            raise
    
    async def get_user_consents(self, user_id: str) -> Dict[str, bool]:
        """
        Retorna todos os consentimentos de um usuário.
        
        Returns:
            Dict com cada tipo de consentimento e seu status
        """
        try:
            records = await self.db.query(
                "lgpd_consents",
                filters={"user_id": user_id}
            )
            
            # Agrupa por tipo, pegando o mais recente de cada
            consents = {}
            for record in sorted(records, key=lambda x: x.get("created_at", ""), reverse=True):
                consent_type = record.get("consent_type")
                if consent_type and consent_type not in consents:
                    consents[consent_type] = record.get("granted", False)
            
            return consents
        except Exception as e:
            logger.error(f"Failed to get consents: {e}")
            return {}
    
    async def has_consent(self, user_id: str, consent_type: str) -> bool:
        """
        Verifica se usuário tem consentimento ativo para um tipo.
        """
        consents = await self.get_user_consents(user_id)
        return consents.get(consent_type, False)
    
    async def revoke_consent(self, user_id: str, consent_type: str) -> bool:
        """
        Revoga um consentimento do usuário.
        (Registra um novo consent com granted=False)
        """
        await self.record_consent(user_id, consent_type, granted=False)
        logger.info(f"Consent revoked: {user_id} - {consent_type}")
        return True
    
    async def get_consent_audit_log(self, user_id: str) -> list:
        """
        Retorna histórico completo de consentimentos para auditoria.
        """
        try:
            records = await self.db.query(
                "lgpd_consents",
                filters={"user_id": user_id},
                order_by="created_at"
            )
            return records
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []


def require_consent(consent_type: str):
    """
    Decorator para exigir consentimento antes de executar uma função.
    
    Uso:
        @require_consent("data_collection")
        async def collect_leads(user_id, ...):
            ...
    """
    def decorator(func):
        async def wrapper(user_id: str, *args, **kwargs):
            manager = LGPDConsentManager()
            if not await manager.has_consent(user_id, consent_type):
                raise PermissionError(
                    f"Consentimento '{consent_type}' não concedido. "
                    f"Aceite a política de privacidade para continuar."
                )
            return await func(user_id, *args, **kwargs)
        return wrapper
    return decorator
