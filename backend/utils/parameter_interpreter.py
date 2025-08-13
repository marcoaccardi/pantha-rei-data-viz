"""
Contextual Intelligence System for Ocean Parameter Interpretation.

Provides dynamic, value-based descriptions and educational context for ocean measurements.
Leverages the existing classifyMeasurement logic from the frontend with enhanced backend intelligence.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from dataclasses import dataclass

from api.models.responses import ParameterClassification, EducationalContext

logger = logging.getLogger(__name__)

@dataclass
class ValueRange:
    """Represents a value range with its associated interpretation."""
    min_val: float
    max_val: float
    classification: str
    severity: str
    description: str
    environmental_impact: str
    context: str

class ParameterInterpreter:
    """Contextual intelligence system for interpreting ocean parameter measurements."""
    
    def __init__(self):
        """Initialize the parameter interpreter with configuration data."""
        self.config_path = Path("config/parameter_descriptions.yaml")
        self.config = self._load_config()
        
        # Enhanced classification mapping with more parameters
        self.classification_colors = {
            'low': '#10b981',      # Green
            'medium': '#f59e0b',   # Orange  
            'high': '#ef4444',     # Red
            'critical': '#991b1b'  # Dark Red
        }
        
        logger.info("🧠 Parameter interpreter initialized with dynamic descriptions")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load parameter descriptions configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load parameter descriptions config: {e}")
            return {}
    
    def get_parameter_classification(
        self, 
        parameter: str, 
        value: Union[float, str, None],
        location: Optional[Tuple[float, float]] = None,
        date: Optional[str] = None
    ) -> Optional[ParameterClassification]:
        """
        Get dynamic classification and interpretation for a parameter value.
        
        Args:
            parameter: Parameter name (e.g., 'sst', 'ph', 'VHM0')
            value: Measured value
            location: Optional (lat, lon) tuple for geographic context
            date: Optional date string for temporal context
            
        Returns:
            ParameterClassification with dynamic description or None if not found
        """
        if value is None or not self.config.get('parameters', {}).get(parameter):
            return None
        
        # Handle string values (like microplastics data_source)
        if isinstance(value, str):
            return self._classify_categorical_parameter(parameter, value)
        
        # Handle numeric values
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return None
        
        param_config = self.config['parameters'][parameter]
        value_ranges = param_config.get('value_ranges', [])
        
        # Find the appropriate range for this value
        for range_config in value_ranges:
            if range_config['min'] <= numeric_value < range_config['max']:
                # Add contextual enhancement based on location/date
                enhanced_context = self._enhance_context(
                    range_config['context'], parameter, numeric_value, location, date
                )
                
                return ParameterClassification(
                    classification=range_config['classification'],
                    severity=range_config['severity'],
                    color=self.classification_colors.get(range_config['severity'], '#6b7280'),
                    description=range_config['description'],
                    environmental_impact=range_config['environmental_impact'],
                    context=enhanced_context
                )
        
        # Handle values outside defined ranges
        return self._handle_outlier_value(parameter, numeric_value, value_ranges)
    
    def _classify_categorical_parameter(self, parameter: str, value: str) -> Optional[ParameterClassification]:
        """Handle categorical parameters like data source types."""
        if parameter == 'data_source':
            if value == 'real':
                return ParameterClassification(
                    classification="Observational Data",
                    severity="low",
                    color="#10b981",
                    description="Direct measurements from oceanographic sampling",
                    environmental_impact="High reliability for ecosystem assessment",
                    context="Real-world observations with full scientific confidence"
                )
            elif value == 'synthetic':
                return ParameterClassification(
                    classification="Modeled Data", 
                    severity="medium",
                    color="#f59e0b",
                    description="AI-generated data based on historical patterns",
                    environmental_impact="Estimated conditions for trend analysis",
                    context="Synthetic data with 70% confidence, useful for pattern detection"
                )
        
        elif parameter == 'concentration_class':
            class_colors = {
                'Very Low': '#10b981',
                'Low': '#06b6d4', 
                'Medium': '#f59e0b',
                'High': '#ef4444',
                'Very High': '#991b1b'
            }
            return ParameterClassification(
                classification=value,
                severity='low' if value in ['Very Low', 'Low'] else 'high',
                color=class_colors.get(value, '#6b7280'),
                description=f"{value} microplastics contamination level",
                environmental_impact=f"Indicates {value.lower()} ecosystem plastic pollution stress",
                context=f"Classification based on global marine pollution standards"
            )
        
        return None
    
    def _enhance_context(
        self, 
        base_context: str, 
        parameter: str, 
        value: float,
        location: Optional[Tuple[float, float]], 
        date: Optional[str]
    ) -> str:
        """Enhance contextual description with geographic and temporal information."""
        enhanced_context = base_context
        
        # Add geographic context
        if location:
            lat, lon = location
            region_context = self._get_regional_context(lat, lon, parameter, value)
            if region_context:
                enhanced_context += f" {region_context}"
        
        # Add temporal context  
        if date:
            temporal_context = self._get_temporal_context(date, parameter, value)
            if temporal_context:
                enhanced_context += f" {temporal_context}"
        
        return enhanced_context
    
    def _get_regional_context(self, lat: float, lon: float, parameter: str, value: float) -> str:
        """Provide geographic context based on location."""
        # Arctic regions
        if abs(lat) > 66.5:
            if parameter == 'sst' and value > 5:
                return "Unusually warm for Arctic/Antarctic waters, may indicate ice melt."
            elif parameter == 'ph' and value < 8.0:
                return "Arctic acidification is accelerating due to cold water CO₂ absorption."
        
        # Tropical regions  
        elif abs(lat) < 23.5:
            if parameter == 'sst' and value > 29:
                return "Approaching coral bleaching threshold for tropical reefs."
            elif parameter == 'chl' and value > 2:
                return "High productivity unusual for nutrient-poor tropical waters."
        
        # Temperate regions
        else:
            if parameter == 'sst' and abs(lat) > 40:
                if value > 20:
                    return "Warmer than typical for mid-latitude waters."
        
        # Coastal vs open ocean (rough approximation)
        if self._is_likely_coastal(lat, lon):
            if parameter == 'microplastics_concentration' and value > 1.0:
                return "High plastic pollution typical near populated coastlines."
            elif parameter == 'chl' and value > 5.0:
                return "Elevated productivity common in nutrient-rich coastal upwelling."
        
        return ""
    
    def _get_temporal_context(self, date: str, parameter: str, value: float) -> str:
        """Provide temporal context based on date and seasonality."""
        try:
            dt = datetime.strptime(date, '%Y-%m-%d')
            month = dt.month
            year = dt.year
            
            # Seasonal context
            if parameter == 'sst':
                # Northern hemisphere summer
                if month in [6, 7, 8] and value > 25:
                    return "Summer maximum temperatures, monitor for heat stress."
                # Winter cooling
                elif month in [12, 1, 2] and value < 15:
                    return "Winter cooling phase, normal seasonal variation."
            
            elif parameter == 'chl':
                # Spring bloom season
                if month in [3, 4, 5] and value > 3:
                    return "Likely spring phytoplankton bloom period."
                # Fall productivity
                elif month in [9, 10] and value > 2:
                    return "Fall productivity increase, secondary bloom season."
            
            # Climate change context
            if year >= 2020:
                if parameter == 'sst' and value > 28:
                    return "Recent warming consistent with climate change trends."
                elif parameter == 'ph' and value < 7.9:
                    return "Continued ocean acidification from rising atmospheric CO₂."
            elif year >= 2024:
                if parameter == 'sst' and value > 27:
                    return "2024-2025 measurements show continued ocean warming."
                elif parameter == 'microplastics_concentration' and value > 2.0:
                    return "Current high pollution levels reflect growing plastic crisis."
        
        except (ValueError, TypeError):
            pass
        
        return ""
    
    def _is_likely_coastal(self, lat: float, lon: float) -> bool:
        """Rough approximation of coastal vs open ocean location."""
        # This is a simplified heuristic - in a real system, you'd use coastline data
        # Major coastal regions and islands tend to have higher variability
        # This is just for demo purposes
        return (
            (abs(lat) < 60 and abs(lon) < 20) or  # Near major landmasses
            (20 < abs(lat) < 50 and abs(lon) > 120) or  # Pacific rim
            (abs(lat) > 50 and abs(lon) < 60)  # North Atlantic
        )
    
    def _handle_outlier_value(
        self, 
        parameter: str, 
        value: float, 
        ranges: List[Dict[str, Any]]
    ) -> Optional[ParameterClassification]:
        """Handle values outside defined ranges."""
        if not ranges:
            return None
        
        # Determine if value is above or below range
        min_range_val = min(r['min'] for r in ranges)
        max_range_val = max(r['max'] for r in ranges)
        
        if value < min_range_val:
            # Below minimum - use lowest range but mark as extreme
            lowest_range = min(ranges, key=lambda r: r['min'])
            return ParameterClassification(
                classification=f"Extremely {lowest_range['classification']}",
                severity="critical",
                color="#7c2d12",  # Very dark red
                description=f"Extremely low {parameter} value (below normal range)",
                environmental_impact="Unusual conditions requiring investigation",
                context="Value below expected range, potential data quality issue or extreme event"
            )
        
        elif value >= max_range_val:
            # Above maximum - use highest range but mark as extreme  
            highest_range = max(ranges, key=lambda r: r['max'])
            return ParameterClassification(
                classification=f"Extremely {highest_range['classification']}",
                severity="critical", 
                color="#7c2d12",  # Very dark red
                description=f"Extremely high {parameter} value (above normal range)",
                environmental_impact="Unusual conditions requiring investigation",
                context="Value above expected range, potential extreme event or data anomaly"
            )
        
        return None
    
    def get_educational_context(self, parameter: str) -> Optional[EducationalContext]:
        """Get educational information about a parameter."""
        if parameter not in self.config.get('parameters', {}):
            return None
        
        param_config = self.config['parameters'][parameter]
        
        return EducationalContext(
            short_description=param_config.get('short_description', ''),
            scientific_context=param_config.get('scientific_context', ''),
            unit_explanation=param_config.get('unit_explanation', ''),
            health_implications=param_config.get('health_implications', {}),
            measurement_context=param_config.get('measurement_context', {})
        )
    
    def get_global_context_indicators(self) -> Dict[str, List[str]]:
        """Get global environmental context indicators."""
        return self.config.get('global_context', {})
    
    def interpret_multi_parameter_context(self, measurements: Dict[str, float]) -> List[str]:
        """
        Analyze multiple parameters together for ecosystem-level insights.
        
        Args:
            measurements: Dictionary of parameter names to values
            
        Returns:
            List of contextual insights based on parameter combinations
        """
        insights = []
        
        # Ocean acidification + temperature stress
        if 'ph' in measurements and 'sst' in measurements:
            ph_val = measurements['ph']
            temp_val = measurements['sst']
            
            if ph_val < 8.0 and temp_val > 28:
                insights.append(
                    "🚨 Combined ocean acidification and heat stress - severe threat to coral ecosystems"
                )
            elif ph_val < 8.1 and temp_val > 26:
                insights.append(
                    "⚠️ Moderate acidification with elevated temperature - coral stress conditions"
                )
        
        # Hypoxia + productivity relationship
        if 'o2' in measurements and 'chl' in measurements:
            o2_val = measurements['o2']
            chl_val = measurements['chl']
            
            if o2_val < 180 and chl_val > 10:
                insights.append(
                    "🔴 Low oxygen with high productivity - possible harmful algal bloom or eutrophication"
                )
        
        # Plastic pollution + ecosystem health
        if 'microplastics_concentration' in measurements:
            plastic_val = measurements['microplastics_concentration']
            
            if plastic_val > 5.0:
                insights.append(
                    "🏭 High microplastics concentration - significant marine ecosystem contamination"
                )
            
            # Combined with low pH
            if 'ph' in measurements and measurements['ph'] < 8.0 and plastic_val > 1.0:
                insights.append(
                    "⚡ Combined pollution stress: acidification + plastic contamination"
                )
        
        # Current + wave relationship
        if 'speed' in measurements and 'VHM0' in measurements:
            current_val = measurements['speed']  
            wave_val = measurements['VHM0']
            
            if current_val > 0.5 and wave_val > 3.0:
                insights.append(
                    "🌊 High energy environment: strong currents detected - extreme mixing conditions"
                )
        
        return insights

# Global instance for use across the application
parameter_interpreter = ParameterInterpreter()