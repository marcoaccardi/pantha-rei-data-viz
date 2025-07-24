#!/usr/bin/env python3
"""
ERDDAP utilities for dynamic parameter discovery and query building.
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class ERDDAPUtils:
    """Utilities for working with ERDDAP datasets."""
    
    @staticmethod
    def get_dataset_info(base_url: str, dataset_id: str) -> Optional[Dict]:
        """
        Get dataset information including available variables.
        
        Args:
            base_url: ERDDAP base URL
            dataset_id: Dataset identifier
            
        Returns:
            Dataset info dict or None if failed
        """
        try:
            info_url = f"{base_url}/{dataset_id}.json"
            response = requests.get(info_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract variable information
            variables = []
            if 'table' in data and 'rows' in data['table']:
                rows = data['table']['rows']
                for row in rows:
                    if len(row) > 2 and row[0] == 'variable':
                        var_info = {
                            'name': row[1],
                            'type': row[2] if len(row) > 2 else 'unknown'
                        }
                        variables.append(var_info)
            
            return {
                'dataset_id': dataset_id,
                'base_url': base_url,
                'variables': variables
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"   ⚠️  Dataset {dataset_id} not found (404)")
            else:
                print(f"   ⚠️  HTTP error for {dataset_id}: {e.response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Network error for {dataset_id}: {e}")
            return None
        except Exception as e:
            print(f"   ⚠️  Unexpected error for {dataset_id}: {e}")
            return None
    
    @staticmethod
    def find_matching_variable(variables: List[Dict], target_types: List[str]) -> Optional[str]:
        """
        Find a variable matching one of the target types.
        
        Args:
            variables: List of variable info dicts
            target_types: List of target variable types to search for
            
        Returns:
            Variable name or None
        """
        # Common variable name patterns for different data types
        patterns = {
            'temperature': ['sst', 'temperature', 'temp', 'analysed_sst', 'sea_surface_temperature'],
            'chlorophyll': ['chlorophyll', 'chla', 'chl', 'chlor_a'],
            'wave_height': ['wave_height', 'hs', 'swh', 'significant_wave_height', 'htsgwsfc'],
            'wave_period': ['wave_period', 'tp', 'peak_period', 'dominant_period'],
            'wave_direction': ['wave_direction', 'dp', 'peak_direction', 'mean_direction'],
            'current_u': ['water_u', 'u', 'eastward_current', 'u_current'],
            'current_v': ['water_v', 'v', 'northward_current', 'v_current'],
            'salinity': ['salinity', 'sal', 'so', 'sea_water_salinity'],
            'oxygen': ['oxygen', 'o2', 'dissolved_oxygen']
        }
        
        # Get all variable names
        var_names = [v['name'].lower() for v in variables]
        
        # Check each target type
        for target_type in target_types:
            if target_type in patterns:
                # Check each pattern for this type
                for pattern in patterns[target_type]:
                    for var_name in var_names:
                        if pattern in var_name:
                            # Return the original case variable name
                            for v in variables:
                                if v['name'].lower() == var_name:
                                    return v['name']
        
        return None
    
    @staticmethod
    def build_query_url(base_url: str, dataset_id: str, variable: str, 
                       lat: float, lon: float, date: str) -> str:
        """
        Build ERDDAP query URL with proper formatting.
        
        Args:
            base_url: ERDDAP base URL
            dataset_id: Dataset identifier
            variable: Variable name to query
            lat: Latitude
            lon: Longitude
            date: Date string (YYYY-MM-DD)
            
        Returns:
            Formatted query URL
        """
        # Convert date to ISO format
        date_iso = f"{date}T12:00:00Z"
        
        # Build constraints
        time_constraint = f"[({date_iso}):1:({date_iso})]"
        lat_constraint = f"[({lat}):1:({lat})]"
        lon_constraint = f"[({lon}):1:({lon})]"
        
        # Build query
        query = f"{variable}{time_constraint}{lat_constraint}{lon_constraint}"
        
        return f"{base_url}/{dataset_id}.json?{query}"
    
    @staticmethod
    def get_recent_available_date(base_url: str, dataset_id: str) -> Optional[str]:
        """
        Get the most recent available date for a dataset.
        
        Args:
            base_url: ERDDAP base URL
            dataset_id: Dataset identifier
            
        Returns:
            Date string (YYYY-MM-DD) or None
        """
        try:
            # Query for time range
            time_url = f"{base_url}/{dataset_id}.json?time"
            response = requests.get(time_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'table' in data and 'rows' in data['table']:
                rows = data['table']['rows']
                if rows:
                    # Get the last time value
                    last_time = rows[-1][0]
                    # Convert to date
                    if 'T' in str(last_time):
                        date_obj = datetime.fromisoformat(str(last_time).replace('Z', '+00:00'))
                        return date_obj.strftime('%Y-%m-%d')
            
            return None
            
        except Exception:
            # If direct time query fails, try a different approach
            # Try dates going back from today
            today = datetime.now()
            for days_back in range(0, 30):
                test_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
                # Test with a simple query
                test_url = f"{base_url}/{dataset_id}.json?time[({test_date}T00:00:00Z):1:({test_date}T23:59:59Z)]"
                try:
                    response = requests.get(test_url, timeout=5)
                    if response.status_code == 200:
                        return test_date
                except:
                    continue
            
            return None
    
    @staticmethod
    def parse_erddap_response(response_text: str) -> Dict[str, any]:
        """
        Parse ERDDAP JSON response.
        
        Args:
            response_text: JSON response text
            
        Returns:
            Parsed data dict
        """
        try:
            data = json.loads(response_text)
            table = data.get('table', {})
            
            if not table or 'rows' not in table or not table['rows']:
                return {}
            
            column_names = table.get('columnNames', [])
            rows = table.get('rows', [])
            
            if not rows:
                return {}
            
            # Convert to dict
            result = {}
            row = rows[0]  # Take first row
            
            for i, col_name in enumerate(column_names):
                if i < len(row) and row[i] is not None:
                    result[col_name] = row[i]
            
            return result
            
        except (json.JSONDecodeError, KeyError, IndexError):
            return {}