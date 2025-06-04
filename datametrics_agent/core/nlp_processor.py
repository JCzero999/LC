"""
Natural Language Processing module for DataMetrics Agent.

This module handles parsing natural language descriptions of metrics
and converting them into structured metric definitions.
"""

import re
from typing import Any, Dict, List, Optional

from datametrics_agent.core.config import Config
from datametrics_agent.core.exceptions import AIServiceError
from datametrics_agent.core.logging import get_logger
from datametrics_agent.core.models import MetricType


class NLPProcessor:
    """Processes natural language descriptions to extract metric information."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize NLP processor.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Initialize AI client if configured
        self._ai_client = None
        if config.ai.openai.get('api_key'):
            self._init_openai_client()
    
    def _init_openai_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            import openai
            self._ai_client = openai.OpenAI(
                api_key=self.config.ai.openai['api_key']
            )
            self.logger.info("OpenAI client initialized")
        except ImportError:
            self.logger.warning("OpenAI package not available")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
    
    def parse_metric_description(self, description: str) -> Dict[str, Any]:
        """
        Parse natural language description to extract metric information.
        
        Args:
            description: Natural language description of the metric
            
        Returns:
            Dict[str, Any]: Extracted metric information
        """
        self.logger.info(f"Parsing metric description: {description}")
        
        # Try AI-powered parsing first
        if self._ai_client:
            try:
                return self._parse_with_ai(description)
            except Exception as e:
                self.logger.warning(f"AI parsing failed, falling back to rule-based: {e}")
        
        # Fallback to rule-based parsing
        return self._parse_with_rules(description)
    
    def _parse_with_ai(self, description: str) -> Dict[str, Any]:
        """Parse description using AI/LLM."""
        if not self._ai_client:
            raise AIServiceError("AI client not available")
        
        prompt = self._build_parsing_prompt(description)
        
        try:
            response = self._ai_client.chat.completions.create(
                model=self.config.ai.openai.get('model', 'gpt-4'),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data analyst expert. Parse metric descriptions and return structured JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.config.ai.openai.get('max_tokens', 2000),
                temperature=self.config.ai.openai.get('temperature', 0.1)
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            import json
            result = json.loads(content)
            
            self.logger.info("Successfully parsed description with AI")
            return result
            
        except Exception as e:
            self.logger.error(f"AI parsing failed: {e}")
            raise AIServiceError(f"AI parsing failed: {e}")
    
    def _parse_with_rules(self, description: str) -> Dict[str, Any]:
        """Parse description using rule-based approach."""
        description_lower = description.lower()
        
        result = {
            'name': self._extract_metric_name(description),
            'metric_type': self._extract_metric_type(description_lower),
            'table_name': self._extract_table_name(description_lower),
            'measure_column': self._extract_measure_column(description_lower),
            'time_column': self._extract_time_column(description_lower),
            'filters': self._extract_filters(description_lower),
            'dimensions': self._extract_dimensions(description_lower)
        }
        
        # Remove None values
        result = {k: v for k, v in result.items() if v is not None}
        
        self.logger.info("Successfully parsed description with rules")
        return result
    
    def _extract_metric_name(self, description: str) -> str:
        """Extract metric name from description."""
        # Simple heuristic: use first few words or the whole description
        words = description.split()
        if len(words) <= 5:
            return description.title()
        else:
            return ' '.join(words[:5]).title()
    
    def _extract_metric_type(self, description: str) -> MetricType:
        """Extract metric type from description."""
        # Count patterns
        count_patterns = [
            r'\bcount\b', r'\bnumber of\b', r'\bhow many\b', 
            r'\btotal.*users?\b', r'\btotal.*events?\b'
        ]
        
        # Sum patterns
        sum_patterns = [
            r'\bsum\b', r'\btotal.*amount\b', r'\btotal.*value\b',
            r'\btotal.*revenue\b', r'\btotal.*sales?\b'
        ]
        
        # Average patterns
        avg_patterns = [
            r'\baverage\b', r'\bmean\b', r'\bavg\b'
        ]
        
        # Ratio/percentage patterns
        ratio_patterns = [
            r'\bratio\b', r'\brate\b', r'\bpercentage\b', 
            r'\bpercent\b', r'\bconversion\b'
        ]
        
        # Distinct count patterns
        distinct_patterns = [
            r'\bunique\b', r'\bdistinct\b', r'\bdifferent\b'
        ]
        
        for pattern in distinct_patterns:
            if re.search(pattern, description):
                return MetricType.DISTINCT_COUNT
        
        for pattern in count_patterns:
            if re.search(pattern, description):
                return MetricType.COUNT
        
        for pattern in sum_patterns:
            if re.search(pattern, description):
                return MetricType.SUM
        
        for pattern in avg_patterns:
            if re.search(pattern, description):
                return MetricType.AVERAGE
        
        for pattern in ratio_patterns:
            if re.search(pattern, description):
                return MetricType.RATIO
        
        # Default to count
        return MetricType.COUNT
    
    def _extract_table_name(self, description: str) -> Optional[str]:
        """Extract table name from description."""
        # Look for common table name patterns
        table_patterns = [
            r'\bfrom\s+(\w+)\b',
            r'\bin\s+(\w+)\s+table\b',
            r'\b(\w+)_events?\b',
            r'\b(\w+)_data\b',
            r'\buser_(\w+)\b'
        ]
        
        for pattern in table_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_measure_column(self, description: str) -> Optional[str]:
        """Extract measure column from description."""
        # Look for column name patterns
        column_patterns = [
            r'\bsum\s+of\s+(\w+)\b',
            r'\baverage\s+(\w+)\b',
            r'\btotal\s+(\w+)\b'
        ]
        
        for pattern in column_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_time_column(self, description: str) -> Optional[str]:
        """Extract time column from description."""
        # Common time column names
        time_columns = [
            'created_at', 'updated_at', 'timestamp', 'date', 
            'event_time', 'occurred_at', 'time'
        ]
        
        for col in time_columns:
            if col in description:
                return col
        
        # Look for time-related patterns
        if re.search(r'\bby\s+(day|week|month|year)\b', description):
            return 'created_at'  # Default assumption
        
        return None
    
    def _extract_filters(self, description: str) -> List[Dict[str, Any]]:
        """Extract filters from description."""
        filters = []
        
        # Look for filter patterns
        filter_patterns = [
            (r'\bwhere\s+(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]', '='),
            (r'\bwhere\s+(\w+)\s+in\s+\(([^)]+)\)', 'IN'),
            (r'\bactive\s+users?\b', ('status', '=', 'active')),
            (r'\bpaid\s+users?\b', ('user_type', '=', 'paid')),
        ]
        
        for pattern in filter_patterns:
            if isinstance(pattern[1], str):
                matches = re.finditer(pattern[0], description)
                for match in matches:
                    filters.append({
                        'column': match.group(1),
                        'operator': pattern[1],
                        'value': match.group(2)
                    })
            else:
                if re.search(pattern[0], description):
                    column, operator, value = pattern[1]
                    filters.append({
                        'column': column,
                        'operator': operator,
                        'value': value
                    })
        
        return filters
    
    def _extract_dimensions(self, description: str) -> List[str]:
        """Extract dimensions from description."""
        dimensions = []
        
        # Look for dimension patterns
        dimension_patterns = [
            r'\bby\s+(\w+)\b',
            r'\bper\s+(\w+)\b',
            r'\bgroup\s+by\s+(\w+)\b',
            r'\bbroken\s+down\s+by\s+(\w+)\b'
        ]
        
        for pattern in dimension_patterns:
            matches = re.finditer(pattern, description)
            for match in matches:
                dimension = match.group(1)
                if dimension not in ['day', 'week', 'month', 'year']:  # These are time periods, not dimensions
                    dimensions.append(dimension)
        
        return list(set(dimensions))  # Remove duplicates
    
    def _build_parsing_prompt(self, description: str) -> str:
        """Build prompt for AI parsing."""
        return f"""
Parse the following metric description and extract structured information:

Description: "{description}"

Please return a JSON object with the following fields:
- name: A concise name for the metric
- metric_type: One of [count, sum, average, ratio, percentage, distinct_count, median, percentile, custom]
- table_name: The primary table name (if mentioned)
- measure_column: The column to measure (for sum, average, etc.)
- time_column: The time/date column (if time-based analysis is mentioned)
- filters: Array of filter objects with column, operator, and value
- dimensions: Array of dimension names for grouping

Example output:
{{
    "name": "Daily Active Users",
    "metric_type": "distinct_count",
    "table_name": "user_events",
    "measure_column": "user_id",
    "time_column": "created_at",
    "filters": [
        {{"column": "event_type", "operator": "=", "value": "login"}}
    ],
    "dimensions": ["date", "platform"]
}}

Return only the JSON object, no additional text.
"""