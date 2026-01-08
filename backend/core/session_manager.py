import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict
from backend.utils.logger import logger

class SessionManager:
    """
    Gerencia o histórico de sessões usando SQLite.
    """
    def __init__(self, db_path="history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Cria a tabela se não existir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                mode TEXT,
                status TEXT,
                local_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                error_msg TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def create_entry(self, url: str, mode: str) -> int:
        """Cria um novo registro de clonagem e retorna o ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO clones (url, mode, status)
                VALUES (?, ?, ?)
            ''', (url, mode, "STARTED"))
            entry_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return entry_id
        except Exception as e:
            logger.error(f"Erro no DB (create): {e}")
            return -1

    def update_entry(self, entry_id: int, status: str, local_path: str = None, error: str = None):
        """Atualiza o status de um registro"""
        if entry_id == -1: return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updates = ["status = ?"]
            params = [status]
            
            if local_path:
                updates.append("local_path = ?")
                params.append(local_path)
                
            if error:
                updates.append("error_msg = ?")
                params.append(error)
                
            params.append(entry_id)
            
            query = f"UPDATE clones SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erro no DB (update): {e}")

    def get_history(self, limit=10):
        """Retorna últimos N registros"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clones ORDER BY timestamp DESC LIMIT ?', (limit,))
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except:
            return []

    def get_by_id(self, project_id: int):
        """Retorna um único projeto pelo ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clones WHERE id = ?', (project_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Erro no DB (get_by_id): {e}")
            return None
