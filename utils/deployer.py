import os
import shutil
import webbrowser
import logging
import sys
import subprocess

logger = logging.getLogger(__name__)

class Deployer:
    """
    Utilitário para preparar deployment.
    Estratégia: Netlify Drop (Zip & Drag).
    """
    
    @staticmethod
    def _create_zip_with_filter(zip_path, folder_path):
        """Cria zip ignorando arquivos indesejados"""
        import zipfile
        
        ignored_extensions = {'.log', '.db', '.zip', '.pyc', '.git', '.idea', '.vscode', '.DS_Store'}
        ignored_dirs = {'__pycache__', '.git', 'logs', 'seo'}
        
        with zipfile.ZipFile(zip_path + ".zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                # Filtra diretórios
                dirs[:] = [d for d in dirs if d not in ignored_dirs]
                
                for file in files:
                    if any(file.endswith(ext) for ext in ignored_extensions):
                        continue
                    if file == "funnel_map.json" or file == "funnel_graph.html":
                        pass # Esses a gente quer
                        
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
                    
        return zip_path + ".zip"

    @staticmethod
    def package_for_deploy(folder_path):
        """
        Compacta a pasta do projeto em um arquivo .zip (versão segura).
        Retorna o caminho do arquivo zip.
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Pasta não encontrada: {folder_path}")
            
        base_name = os.path.basename(folder_path)
        zip_path = os.path.join(os.path.dirname(folder_path), f"{base_name}_deploy")
        
        logger.info(f"Compactando {folder_path} para {zip_path}.zip (Safe Mode)")
        
        # Usa método customizado seguro em vez de shutil.make_archive
        return Deployer._create_zip_with_filter(zip_path, folder_path)

    @staticmethod
    def open_deploy_page():
        """Abre a página do Netlify Drop no navegador padrão"""
        url = "https://app.netlify.com/drop"
        logger.info(f"Abrindo {url}")
        
        try:
            if sys.platform == 'darwin':
                subprocess.call(('open', url))
            elif sys.platform == 'win32':
                os.startfile(url)
            else:
                subprocess.call(('xdg-open', url))
        except Exception as e:
            # Fallback
            webbrowser.open(url)
