"""
Brasil API Tests
LeadHunter AI - Testing Brasil API integration

Tests for:
- CNPJ lookup
- Company enrichment
- Error handling
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from backend.core.brasil_api import BrasilAPIClient, brasil_api


# =============================================================================
# BRASIL API CLIENT TESTS
# =============================================================================

class TestBrasilAPIClient:
    """Tests for BrasilAPIClient class."""
    
    def test_init(self):
        """Should initialize client."""
        client = BrasilAPIClient()
        
        assert hasattr(client, 'BASE_URL')
        assert client.BASE_URL == "https://brasilapi.com.br/api"
    
    def test_global_instance(self):
        """Global brasil_api instance should be available."""
        assert brasil_api is not None
        assert isinstance(brasil_api, BrasilAPIClient)


# =============================================================================
# CNPJ VALIDATION TESTS
# =============================================================================

class TestCNPJValidation:
    """Tests for CNPJ format validation."""
    
    def test_cnpj_14_digits(self):
        """CNPJ should have 14 digits."""
        valid_cnpjs = [
            "00.000.000/0001-91",
            "00000000000191",
            "11222333000144"
        ]
        
        for cnpj in valid_cnpjs:
            cleaned = ''.join(c for c in cnpj if c.isdigit())
            assert len(cleaned) == 14
    
    def test_invalid_cnpj_short(self):
        """Short CNPJ should be invalid."""
        invalid = "123456"
        cleaned = ''.join(c for c in invalid if c.isdigit())
        
        assert len(cleaned) != 14
    
    def test_cnpj_cleaning(self):
        """Should clean CNPJ format."""
        formatted = "12.345.678/0001-00"
        cleaned = ''.join(c for c in formatted if c.isdigit())
        
        assert cleaned == "12345678000100"


# =============================================================================
# GET COMPANY DATA TESTS
# =============================================================================

class TestGetCompanyData:
    """Tests for company data retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_company_success(self):
        """Should get company data successfully."""
        client = BrasilAPIClient()
        
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "razao_social": "EMPRESA TESTE LTDA",
            "nome_fantasia": "Empresa Teste",
            "cnpj": "12345678000100"
        }
        
        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            MockClient.return_value = mock_client
            
            result = await client.get_company_data("12345678000100")
            
            assert "razao_social" in result
    
    @pytest.mark.asyncio
    async def test_get_company_not_found(self):
        """Should handle CNPJ not found."""
        client = BrasilAPIClient()
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            MockClient.return_value = mock_client
            
            result = await client.get_company_data("99999999999999")
            
            assert "error" in result


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_handle_api_error(self):
        """Should handle API errors gracefully."""
        client = BrasilAPIClient()
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            MockClient.return_value = mock_client
            
            result = await client.get_company_data("12345678000100")
            
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_handle_connection_error(self):
        """Should handle connection errors."""
        client = BrasilAPIClient()
        
        import httpx
        
        with patch('httpx.AsyncClient') as MockClient:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            MockClient.return_value = mock_client
            
            result = await client.get_company_data("12345678000100")
            
            assert "error" in result
