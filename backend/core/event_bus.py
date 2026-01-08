from typing import Callable, Dict, List, Any

class EventBus:
    """
    Sistema de Pub/Sub simples para desacoplar componentes.
    """
    _subscribers: Dict[str, List[Callable]] = {}

    @classmethod
    def subscribe(cls, event_type: str, callback: Callable):
        """Inscreve um callback para um tipo de evento"""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def emit(cls, event_type: str, data: Any = None):
        """Emite um evento para todos os inscritos"""
        if event_type in cls._subscribers:
            for callback in cls._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Erro no callback do EventBus ({event_type}): {e}")

    @classmethod
    def clear(cls):
        """Limpa todos os inscritos (útil para testes/reset)"""
        cls._subscribers = {}
