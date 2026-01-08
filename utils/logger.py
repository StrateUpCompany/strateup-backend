import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name="ClonadorSite", log_file="clonador_site.log"):
    """Configura e retorna um logger padrão"""
    # Cria o logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Evita duplicidade de handlers
    if not logger.handlers:
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File Handler (Rotating: 5MB max, 3 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Stream Handler (Console)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    
    return logger

# Instância global do logger
logger = setup_logger()
