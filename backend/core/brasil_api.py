import httpx
from backend.utils.logger import logger

class BrasilAPIClient:
    BASE_URL = "https://brasilapi.com.br/api"

    async def get_company_data(self, cnpj: str) -> dict:
        """
        Fetches company data from BrasilAPI by CNPJ.
        Returns a dict with company details or raises Exception.
        """
        # Remove non-digits
        clean_cnpj = "".join(filter(str.isdigit, cnpj))
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.BASE_URL}/cnpj/v1/{clean_cnpj}", timeout=10.0)
                
                if response.status_code == 404:
                    return {"error": "CNPJ não encontrado"}
                
                if response.status_code != 200:
                    logger.error(f"BrasilAPI Error: {response.text}")
                    return {"error": f"Erro na consulta: {response.status_code}"}
                
                return response.json()
                
            except httpx.RequestError as e:
                logger.error(f"BrasilAPI Connection Error: {e}")
                return {"error": "Erro de conexão com BrasilAPI"}
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return {"error": str(e)}

brasil_api = BrasilAPIClient()
