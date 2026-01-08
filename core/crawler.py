import threading
from backend.core.engine import CloneEngine
from backend.core.event_bus import EventBus
from backend.utils.logger import logger

class ClonagemThread(threading.Thread):
    """
    Wrapper Python Standard Thread para o CloneEngine.
    Remove dependências de PyQt para uso em Backend API.
    """
    def __init__(self, url, opcoes=None, project_id=None):
        super().__init__()
        self.engine = CloneEngine(url, opcoes, project_id)
        self.daemon = True # Thread morre com a aplicação principal
        self._setup_listeners()
        
    def _setup_listeners(self):
        """
        Inscreve listeners no EventBus. 
        Nota: Em backend web, idealmente usaríamos WebSockets ou um Queue manager (Redis/Celery).
        Para MVP local, EventBus + Logging funciona.
        """
        # EventBus global é usado, cuidado com concorrência se escalar.
        # Por enquanto, mantemos a lógica original.
        pass

    def run(self):
        """Executa a engine"""
        # EventBus não deve ser limpo aqui pois remove subscribers do WebSocket Manager
        # EventBus.clear() 
        
        try:
            self.engine.run()
        except Exception as e:
            logger.error(f"Erro na thread wrapper: {e}")
            EventBus.emit("error", str(e))

    def stop(self):
        self.engine.stop()
