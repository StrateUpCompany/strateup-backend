import logging
from PyQt5.QtWidgets import QTextEdit

class QTextEditLogger(logging.Handler):
    """Handler de log que envia mensagens para um QTextEdit"""
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        
    def emit(self, record):
        msg = self.format(record)
        # Usa invokeMethod ou similar se fosse entre threads diferentes, 
        # mas aqui assumimos que o sinal/slot do Qt cuida da thread safety na UI se conectado corretamente,
        # ou que o log vem da mesma thread. 
        # Para ser seguro com threads, o ideal é usar sinais e slots.
        # No código original era direto. Vou manter simples por enquanto.
        try:
            self.text_edit.append(msg)
            # Rola para o final
            cursor = self.text_edit.textCursor()
            cursor.movePosition(cursor.End)
            self.text_edit.setTextCursor(cursor)
        except Exception:
            # Evita crash se a UI já foi destruída
            pass
