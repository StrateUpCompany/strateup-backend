
import io
import csv
import json
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from backend.utils.logger import logger

class ExportService:
    """
    Service for exporting data to various formats.
    Supports: CSV, JSON, Excel (xlsx)
    """
    
    def export_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """
        Convert list of dicts to CSV string.
        Flatten nested JSONB data where possible.
        """
        if not data:
            return ""
            
        # Flatten data for better CSV usage
        flat_data = [self._flatten_lead(item) for item in data]
        
        output = io.StringIO()
        if flat_data:
            keys = flat_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=keys)
            writer.writeheader()
            writer.writerows(flat_data)
            
        return output.getvalue()

    def export_to_excel(self, data: List[Dict[str, Any]]) -> bytes:
        """
        Convert list of dicts to Excel bytes.
        """
        if not data:
            return b""
            
        flat_data = [self._flatten_lead(item) for item in data]
        df = pd.DataFrame(flat_data)
        
        output = io.BytesIO()
        # writing to bytes buffer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
            
        return output.getvalue()

    def export_to_json(self, data: List[Dict[str, Any]]) -> str:
        """
        Convert list of dicts to JSON string.
        """
        return json.dumps(data, indent=2, default=str, ensure_ascii=False)

    def _flatten_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to flatten lead structure for tabular formats.
        Prioritizes 'data' keys (name, email) but keeps top level info (id, created_at)
        """
        flat = {}
        
        # Top level
        flat['id'] = lead.get('id')
        flat['created_at'] = lead.get('created_at')
        flat['project_id'] = lead.get('project_id')
        
        # Data level (Main lead info)
        lead_data = lead.get('data', {}) or {}
        if isinstance(lead_data, str):
            try:
                lead_data = json.loads(lead_data)
            except:
                lead_data = {}
                
        for k, v in lead_data.items():
            if k not in ['enrichment', 'raw_data']: # Skip complex nested for CSV main cols
                flat[k] = v
                
        # Enrichment Level (Flatten some key metrics)
        enrichment = lead_data.get('enrichment', {})
        if enrichment:
            # Quality Score
            score_data = enrichment.get('data', {})
            if isinstance(score_data, dict):
                 flat['quality_score'] = score_data.get('score')
                 flat['quality_grade'] = score_data.get('grade')
                 
                 # Insights
                 insights = score_data.get('business_insights', [])
                 if isinstance(insights, list):
                     for insight in insights:
                         if isinstance(insight, dict):
                             i_type = insight.get('type')
                             i_val = insight.get('value')
                             if i_type and i_val:
                                 flat[f"ai_{i_type}"] = i_val

        return flat

export_service = ExportService()
