"""
Export Service Tests
LeadHunter AI - Testing export module

Tests for:
- CSV export
- JSON export
- Report generation
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.core.export_service import ExportService, export_service


# =============================================================================
# EXPORT SERVICE TESTS
# =============================================================================

class TestExportService:
    """Tests for ExportService class."""
    
    def test_singleton_instance(self):
        """ExportService should be a singleton."""
        service1 = ExportService()
        service2 = ExportService()
        
        assert service1 is service2
    
    def test_global_instance(self):
        """Global export_service should be available."""
        assert export_service is not None
        assert isinstance(export_service, ExportService)


# =============================================================================
# CSV EXPORT TESTS
# =============================================================================

class TestCSVExport:
    """Tests for CSV export functionality."""
    
    def test_to_csv_basic(self):
        """Should export data to CSV."""
        service = ExportService()
        
        data = [
            {"name": "John", "email": "john@example.com"},
            {"name": "Jane", "email": "jane@example.com"}
        ]
        
        result = service.to_csv(data)
        
        assert result["success"] is True
        assert "content" in result
        assert result["mime_type"] == "text/csv"
        assert result["rows"] == 2
    
    def test_to_csv_empty_data(self):
        """Should handle empty data."""
        service = ExportService()
        
        result = service.to_csv([])
        
        assert result["success"] is False
        assert "error" in result
    
    def test_to_csv_custom_columns(self):
        """Should use custom columns."""
        service = ExportService()
        
        data = [
            {"name": "Test", "email": "test@example.com", "phone": "123"}
        ]
        
        result = service.to_csv(data, columns=["name", "email"])
        
        assert result["success"] is True
        assert "phone" not in result["content"].split("\n")[0]
    
    def test_to_csv_content_format(self):
        """CSV content should be properly formatted."""
        service = ExportService()
        
        data = [{"col1": "value1", "col2": "value2"}]
        
        result = service.to_csv(data)
        
        content = result["content"]
        lines = content.strip().split("\n")
        
        # Should have header + 1 data row
        assert len(lines) == 2
    
    def test_to_csv_custom_filename(self):
        """Should use custom filename."""
        service = ExportService()
        
        data = [{"name": "Test"}]
        
        result = service.to_csv(data, filename="custom_export.csv")
        
        assert result["filename"] == "custom_export.csv"


# =============================================================================
# JSON EXPORT TESTS
# =============================================================================

class TestJSONExport:
    """Tests for JSON export functionality."""
    
    def test_to_json_basic(self):
        """Should export data to JSON."""
        service = ExportService()
        
        data = [
            {"name": "John", "value": 100},
            {"name": "Jane", "value": 200}
        ]
        
        result = service.to_json(data)
        
        assert result["success"] is True
        assert "content" in result
        assert result["mime_type"] == "application/json"
        assert result["rows"] == 2
    
    def test_to_json_empty_data(self):
        """Should handle empty data."""
        service = ExportService()
        
        result = service.to_json([])
        
        assert result["success"] is False
        assert "error" in result
    
    def test_to_json_pretty(self):
        """Should pretty print by default."""
        service = ExportService()
        
        data = [{"key": "value"}]
        
        result = service.to_json(data, pretty=True)
        
        # Pretty print includes indentation
        assert "\n" in result["content"]
    
    def test_to_json_compact(self):
        """Should support compact format."""
        service = ExportService()
        
        data = [{"key": "value"}]
        
        result = service.to_json(data, pretty=False)
        
        # Compact has fewer newlines
        assert result["success"] is True
    
    def test_to_json_custom_filename(self):
        """Should use custom filename."""
        service = ExportService()
        
        data = [{"name": "Test"}]
        
        result = service.to_json(data, filename="custom.json")
        
        assert result["filename"] == "custom.json"


# =============================================================================
# REPORT GENERATION TESTS
# =============================================================================

class TestReportGeneration:
    """Tests for report generation."""
    
    def test_generate_report_basic(self):
        """Should generate basic report."""
        service = ExportService()
        
        data = [
            {"name": "Lead 1", "source": "instagram"},
            {"name": "Lead 2", "source": "google"}
        ]
        
        result = service.generate_report(data, report_type="leads")
        
        assert result["success"] is True
        assert "report" in result
        assert result["report"]["summary"]["total_records"] == 2
    
    def test_generate_report_has_metadata(self):
        """Report should have metadata."""
        service = ExportService()
        
        data = [{"name": "Test"}]
        
        result = service.generate_report(data)
        
        report = result["report"]
        assert "title" in report
        assert "generated_at" in report
        assert "generated_by" in report
    
    def test_generate_report_custom_title(self):
        """Should use custom title."""
        service = ExportService()
        
        data = [{"item": "test"}]
        
        result = service.generate_report(data, title="Custom Report Title")
        
        assert result["report"]["title"] == "Custom Report Title"
    
    def test_generate_report_leads_stats(self):
        """Leads report should have lead-specific stats."""
        service = ExportService()
        
        data = [
            {"name": "A", "email": "a@test.com", "source": "instagram"},
            {"name": "B", "phone": "123", "source": "google"},
            {"name": "C", "email": "c@test.com", "phone": "456", "source": "instagram"}
        ]
        
        result = service.generate_report(data, report_type="leads")
        
        summary = result["report"]["summary"]
        assert summary["with_email"] == 2
        assert summary["with_phone"] == 2
        assert "by_source" in summary


# =============================================================================
# STATS TESTS
# =============================================================================

class TestExportStats:
    """Tests for export statistics."""
    
    def test_get_stats(self):
        """Should get export stats."""
        service = ExportService()
        
        stats = service.get_stats()
        
        assert isinstance(stats, dict)
        assert "exports" in stats
        assert "csv" in stats
        assert "json" in stats
    
    def test_stats_increment_csv(self):
        """CSV export should increment stats."""
        service = ExportService()
        
        initial_stats = service.get_stats()
        initial_csv = initial_stats.get("csv", 0)
        
        service.to_csv([{"data": "test"}])
        
        new_stats = service.get_stats()
        assert new_stats["csv"] == initial_csv + 1
    
    def test_stats_increment_json(self):
        """JSON export should increment stats."""
        service = ExportService()
        
        initial_stats = service.get_stats()
        initial_json = initial_stats.get("json", 0)
        
        service.to_json([{"data": "test"}])
        
        new_stats = service.get_stats()
        assert new_stats["json"] == initial_json + 1


# =============================================================================
# COUNT BY FIELD TESTS
# =============================================================================

class TestCountByField:
    """Tests for _count_by_field utility."""
    
    def test_count_by_field(self):
        """Should count occurrences by field."""
        service = ExportService()
        
        data = [
            {"source": "instagram"},
            {"source": "instagram"},
            {"source": "google"}
        ]
        
        counts = service._count_by_field(data, "source")
        
        assert counts["instagram"] == 2
        assert counts["google"] == 1
    
    def test_count_missing_field(self):
        """Should handle missing field."""
        service = ExportService()
        
        data = [
            {"name": "A"},
            {"name": "B", "source": "test"}
        ]
        
        counts = service._count_by_field(data, "source")
        
        assert counts.get("unknown", 0) == 1
        assert counts.get("test", 0) == 1
