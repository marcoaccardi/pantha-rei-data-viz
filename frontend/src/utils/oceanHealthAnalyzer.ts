import { OceanPointData, OceanDataValue, ParameterClassification } from './types';
import { TFunction } from 'i18next';

export interface SectionHealthAnalysis {
  overallSeverity: 'low' | 'medium' | 'high' | 'critical';
  overallColor: string;
  healthScore: number; // 0-1, 1 = healthiest
  summary: string;
  specificImpacts: ParameterImpact[];
  recommendations: string[];
  keyFindings: string[];
}

export interface ParameterImpact {
  parameter: string;
  displayName: string;
  currentValue: number | string | null;
  units: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  classification: string;
  impact: string;
  context: string;
}

const SECTION_PARAMETERS = {
  temperature: ['sst', 'analysed_sst', 'ice', 'anom', 'err', 'thetao'],
  chemistry: ['ph', 'ph_insitu', 'ph_insitu_total', 'dissic', 'dic', 'talk', 'pco2', 'revelle', 'o2', 'no3', 'po4', 'si', 'chl', 'nppv'],
  currents: ['uo', 'vo', 'u', 'v', 'ug', 'vg', 'speed', 'direction', 'so']
};

const SEVERITY_COLORS = {
  low: '#10b981',      // Green
  medium: '#f59e0b',   // Yellow
  high: '#ef4444',     // Orange/Red
  critical: '#991b1b'  // Dark Red
};

const SEVERITY_SCORES = {
  low: 0.8,
  medium: 0.6,
  high: 0.3,
  critical: 0.1
};

export function analyzeSectionHealth(
  sectionName: 'temperature' | 'chemistry' | 'currents',
  dataset: OceanPointData | { error: string },
  t?: TFunction
): SectionHealthAnalysis {
  
  if ('error' in dataset) {
    return {
      overallSeverity: 'medium',
      overallColor: SEVERITY_COLORS.medium,
      healthScore: 0.5,
      summary: 'Data not available for health assessment',
      specificImpacts: [],
      recommendations: ['Try a different location or date', 'Check data availability for this region'],
      keyFindings: ['No data available for ocean health analysis']
    };
  }

  const sectionParams = SECTION_PARAMETERS[sectionName];
  const availableParams = sectionParams.filter(param => param in dataset.data);
  
  if (availableParams.length === 0) {
    return {
      overallSeverity: 'medium',
      overallColor: SEVERITY_COLORS.medium,
      healthScore: 0.5,
      summary: `No ${sectionName} parameters available for this location and date`,
      specificImpacts: [],
      recommendations: [], // No recommendations when there's no data
      keyFindings: [`No ${sectionName} data available for ocean health analysis at this location`]
    };
  }

  const impacts: ParameterImpact[] = [];
  let totalHealthScore = 0;
  let parameterCount = 0;

  // Analyze each parameter
  availableParams.forEach(paramName => {
    const paramData = dataset.data[paramName];
    if (paramData && paramData.valid && paramData.value !== null) {
      // Generate basic classification if not present
      const classification = paramData.classification || generateBasicClassification(paramName, paramData.value, t);
      
      const impact: ParameterImpact = {
        parameter: paramName,
        displayName: paramData.long_name || getParameterDisplayName(paramName),
        currentValue: paramData.value,
        units: paramData.units,
        severity: classification.severity,
        classification: classification.classification,
        impact: classification.environmental_impact,
        context: classification.context
      };
      
      impacts.push(impact);
      totalHealthScore += SEVERITY_SCORES[classification.severity];
      parameterCount++;
    }
  });

  // Calculate overall metrics
  const avgHealthScore = parameterCount > 0 ? totalHealthScore / parameterCount : 0.5;
  const severityCounts = impacts.reduce((acc, impact) => {
    acc[impact.severity] = (acc[impact.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Determine overall severity
  let overallSeverity: 'low' | 'medium' | 'high' | 'critical' = 'low';
  if (severityCounts.critical > 0) overallSeverity = 'critical';
  else if (severityCounts.high > 0) overallSeverity = 'high';
  else if (severityCounts.medium > 0) overallSeverity = 'medium';

  // Generate summary and recommendations
  const summary = generateSectionSummary(sectionName, impacts, overallSeverity, t);
  const recommendations = generateRecommendations(sectionName, impacts, overallSeverity);
  const keyFindings = generateKeyFindings(sectionName, impacts);

  return {
    overallSeverity,
    overallColor: SEVERITY_COLORS[overallSeverity],
    healthScore: avgHealthScore,
    summary,
    specificImpacts: impacts,
    recommendations,
    keyFindings
  };
}

function generateSectionSummary(
  sectionName: string, 
  impacts: ParameterImpact[], 
  severity: 'low' | 'medium' | 'high' | 'critical',
  t?: TFunction
): string {
  const location = sectionName.charAt(0).toUpperCase() + sectionName.slice(1);
  const paramCount = impacts.length;
  
  const severityDescriptions: Record<'low' | 'medium' | 'high' | 'critical', string> = {
    low: t ? t('dataPanel.healthAnalysis.showingHealthyConditions') : 'showing healthy conditions',
    medium: t ? t('dataPanel.healthAnalysis.showingModerateStress') : 'showing moderate environmental stress',
    high: t ? t('dataPanel.healthAnalysis.showingSignificantStress') : 'experiencing significant stress',
    critical: t ? t('dataPanel.healthAnalysis.inCriticalCondition') : 'in critical condition requiring immediate attention'
  };

  const criticalParams = impacts.filter(i => i.severity === 'critical');
  const highParams = impacts.filter(i => i.severity === 'high');

  if (criticalParams.length > 0) {
    return `${location} parameters (${t ? t('dataPanel.healthAnalysis.parametersAnalyzed', { count: paramCount }) : `${paramCount} measured`}) ${severityDescriptions[severity]}. Critical concerns: ${criticalParams.map(p => p.displayName).join(', ')}.`;
  } else if (highParams.length > 0) {
    return `${location} parameters (${t ? t('dataPanel.healthAnalysis.parametersAnalyzed', { count: paramCount }) : `${paramCount} measured`}) ${severityDescriptions[severity]}. High stress indicators: ${highParams.map(p => p.displayName).join(', ')}.`;
  } else {
    return `${location} parameters (${t ? t('dataPanel.healthAnalysis.parametersAnalyzed', { count: paramCount }) : `${paramCount} measured`}) ${severityDescriptions[severity]}.`;
  }
}

function generateRecommendations(
  sectionName: string,
  impacts: ParameterImpact[],
  severity: 'low' | 'medium' | 'high' | 'critical'
): string[] {
  const recommendations: string[] = [];
  
  if (severity === 'critical') {
    recommendations.push('Immediate ecosystem monitoring required');
    recommendations.push('Potential marine life emergency in this region');
  } else if (severity === 'high') {
    recommendations.push('Enhanced monitoring recommended');
    recommendations.push('Marine ecosystem stress indicators present');
  } else if (severity === 'medium') {
    recommendations.push('Regular monitoring advised');
    recommendations.push('Early warning signs of environmental change');
  } else {
    recommendations.push('Conditions support healthy marine ecosystems');
    recommendations.push('Continue regular environmental monitoring');
  }

  // Section-specific recommendations
  if (sectionName === 'temperature') {
    const tempImpacts = impacts.filter(i => i.parameter.includes('sst') || i.parameter.includes('temp'));
    if (tempImpacts.some(i => i.severity === 'high' || i.severity === 'critical')) {
      recommendations.push('Coral bleaching risk assessment needed');
      recommendations.push('Monitor marine species distribution changes');
    }
  } else if (sectionName === 'chemistry') {
    const phImpacts = impacts.filter(i => i.parameter.includes('ph'));
    if (phImpacts.some(i => i.severity === 'high' || i.severity === 'critical')) {
      recommendations.push('Ocean acidification mitigation strategies needed');
      recommendations.push('Monitor calcifying organism populations');
    }
  } else if (sectionName === 'currents') {
    const currentImpacts = impacts.filter(i => i.parameter.includes('speed') || i.parameter.includes('current'));
    if (currentImpacts.some(i => i.severity === 'high' || i.severity === 'critical')) {
      recommendations.push('Monitor nutrient transport disruption');
      recommendations.push('Assess impacts on marine food webs');
    }
  }

  return recommendations;
}

function generateKeyFindings(sectionName: string, impacts: ParameterImpact[]): string[] {
  const findings: string[] = [];
  
  // Sort impacts by severity
  const criticalImpacts = impacts.filter(i => i.severity === 'critical');
  const highImpacts = impacts.filter(i => i.severity === 'high');
  const mediumImpacts = impacts.filter(i => i.severity === 'medium');
  
  // Add critical findings
  criticalImpacts.forEach(impact => {
    findings.push(`🚨 ${impact.displayName}: ${impact.classification} - ${impact.impact}`);
  });
  
  // Add high severity findings
  highImpacts.forEach(impact => {
    findings.push(`⚠️ ${impact.displayName}: ${impact.classification} - ${impact.impact}`);
  });
  
  // Add a few medium severity findings if there's space
  mediumImpacts.slice(0, 2).forEach(impact => {
    findings.push(`${impact.displayName}: ${impact.classification} - ${impact.context}`);
  });
  
  // If no concerning findings, add positive ones
  if (findings.length === 0) {
    const healthyImpacts = impacts.filter(i => i.severity === 'low');
    healthyImpacts.slice(0, 3).forEach(impact => {
      findings.push(`${impact.displayName}: ${impact.classification} - ${impact.impact}`);
    });
  }
  
  return findings;
}

export function formatValueWithUnits(value: number | string | null, units: string): string {
  if (value === null || value === undefined) return 'No data';
  
  if (typeof value === 'number') {
    // Format numbers based on their magnitude
    if (Math.abs(value) >= 1000) {
      return `${value.toExponential(2)} ${units}`;
    } else if (Math.abs(value) >= 1) {
      return `${value.toFixed(2)} ${units}`;
    } else {
      return `${value.toFixed(4)} ${units}`;
    }
  }
  
  return `${value} ${units}`;
}

export function getHealthScoreDescription(score: number, t?: TFunction): string {
  if (score >= 0.8) return t ? t('dataPanel.healthAnalysis.excellentOceanHealth') : 'Excellent ocean health';
  if (score >= 0.6) return t ? t('dataPanel.healthAnalysis.goodOceanHealth') : 'Good ocean health';
  if (score >= 0.4) return t ? t('dataPanel.healthAnalysis.moderateOceanHealth') : 'Moderate ocean health';
  if (score >= 0.2) return t ? t('dataPanel.healthAnalysis.poorOceanHealth') : 'Poor ocean health';
  return t ? t('dataPanel.healthAnalysis.poorOceanHealth') : 'Critical ocean health';
}

function getParameterDisplayName(paramName: string): string {
  const displayNames: Record<string, string> = {
    'ph': 'Ocean pH',
    'dissic': 'Dissolved Inorganic Carbon',
    'talk': 'Total Alkalinity',
    'o2': 'Dissolved Oxygen',
    'no3': 'Nitrate',
    'po4': 'Phosphate',
    'si': 'Silicate',
    'chl': 'Chlorophyll-a',
    'nppv': 'Net Primary Production',
    'sst': 'Sea Surface Temperature',
    'uo': 'Eastward Ocean Velocity',
    'vo': 'Northward Ocean Velocity',
    'speed': 'Current Speed',
    'direction': 'Current Direction',
    'thetao': 'Water Temperature',
    'so': 'Salinity'
  };
  return displayNames[paramName] || paramName;
}

function generateBasicClassification(paramName: string, value: number | string, t?: TFunction): {
  severity: 'low' | 'medium' | 'high' | 'critical';
  classification: string;
  environmental_impact: string;
  context: string;
} {
  const numValue = typeof value === 'number' ? value : parseFloat(value as string);
  
  // pH analysis
  if (paramName === 'ph') {
    if (numValue >= 8.1) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.healthyPH') : 'Healthy pH',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.optimalConditions') : 'Optimal conditions for marine calcification and coral growth',
        context: t ? t('dataPanel.contexts.normalOceanic') : 'Normal oceanic pH supports healthy marine ecosystems'
      };
    } else if (numValue >= 7.9) {
      return {
        severity: 'medium',
        classification: t ? t('dataPanel.classifications.slightlyAcidic') : 'Slightly Acidic',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.someStress') : 'Some stress on shell-forming organisms',
        context: t ? t('dataPanel.contexts.lowerThanOptimal') : 'pH is lower than optimal but within acceptable range'
      };
    } else {
      return {
        severity: 'high',
        classification: t ? t('dataPanel.classifications.oceanAcidification') : 'Ocean Acidification',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.significantThreat') : 'Significant threat to marine calcification processes',
        context: t ? t('dataPanel.contexts.concerningAcidification') : 'pH indicates concerning ocean acidification levels'
      };
    }
  }
  
  // Temperature analysis  
  if (paramName === 'sst' || paramName === 'thetao') {
    if (numValue < 15) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.coolWater') : 'Cool Water',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.supportsColdWater') : 'Supports cold-water marine species and ecosystems',
        context: t ? t('dataPanel.contexts.typicalHigherLatitude') : 'Typical of higher latitude or deeper water masses'
      };
    } else if (numValue < 25) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.moderateTemperature') : 'Moderate Temperature',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.optimalRange') : 'Optimal range for diverse marine life',
        context: t ? t('dataPanel.contexts.healthyTemperature') : 'Healthy temperature range for most marine ecosystems'
      };
    } else if (numValue < 30) {
      return {
        severity: 'medium',
        classification: t ? t('dataPanel.classifications.warmWater') : 'Warm Water',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.mayStress') : 'May stress some marine organisms if sustained',
        context: t ? t('dataPanel.contexts.warmTropical') : 'Warm but within normal tropical range'
      };
    } else {
      return {
        severity: 'high',
        classification: t ? t('dataPanel.classifications.veryWarm') : 'Very Warm',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.highStress') : 'High stress on marine ecosystems, coral bleaching risk',
        context: t ? t('dataPanel.contexts.marineHeatwave') : 'Unusually warm temperatures indicate potential marine heatwave'
      };
    }
  }
  
  // Current speed analysis
  if (paramName === 'speed' || paramName.includes('velocity')) {
    const speed = Math.abs(numValue);
    if (speed < 0.1) {
      return {
        severity: 'medium',
        classification: t ? t('dataPanel.classifications.verySlowCurrents') : 'Very Slow Currents',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.limitedTransport') : 'Limited nutrient transport and mixing',
        context: t ? t('dataPanel.contexts.stagnantWater') : 'Low current speeds may indicate stagnant water conditions'
      };
    } else if (speed < 0.5) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.moderateCurrents') : 'Moderate Currents',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.goodTransport') : 'Good for nutrient transport and marine ecosystem health',
        context: t ? t('dataPanel.contexts.healthyCurrents') : 'Healthy current speeds support marine productivity'
      };
    } else if (speed < 1.0) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.strongCurrents') : 'Strong Currents',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.excellentMixing') : 'Excellent nutrient mixing and transport',
        context: t ? t('dataPanel.contexts.enhancesProductivity') : 'Strong currents enhance marine productivity'
      };
    } else {
      return {
        severity: 'medium',
        classification: t ? t('dataPanel.classifications.veryStrongCurrents') : 'Very Strong Currents',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.challengingConditions') : 'May create challenging conditions for some marine life',
        context: t ? t('dataPanel.contexts.affectsOrganism') : 'Very strong currents can affect marine organism behavior'
      };
    }
  }
  
  // Dissolved oxygen
  if (paramName === 'o2') {
    if (numValue > 250) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.highOxygen') : 'High Oxygen',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.excellentRespiration') : 'Excellent conditions for marine respiration',
        context: t ? t('dataPanel.contexts.supportsDiverse') : 'High oxygen levels support diverse marine life'
      };
    } else if (numValue > 150) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.goodOxygen') : 'Good Oxygen',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.adequateOxygen') : 'Adequate oxygen for most marine organisms',
        context: t ? t('dataPanel.contexts.healthyOxygen') : 'Healthy oxygen levels for marine ecosystems'
      };
    } else {
      return {
        severity: 'high',
        classification: t ? t('dataPanel.classifications.lowOxygen') : 'Low Oxygen',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.potentialHypoxia') : 'Stress on marine organisms, potential hypoxia',
        context: t ? t('dataPanel.contexts.threatensLife') : 'Low oxygen conditions threaten marine life'
      };
    }
  }
  
  // Specific analysis for other parameters
  if (paramName === 'no3' || paramName === 'nitrate') {
    if (numValue < 0.1) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.lowNitrate') : 'Low Nitrate',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.nutrientPoor') : 'Indicates nutrient-poor surface waters typical of open ocean',
        context: t ? t('dataPanel.contexts.limitedUpwelling') : 'Low nitrate levels suggest limited recent upwelling or mixing'
      };
    } else {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.elevatedNitrate') : 'Elevated Nitrate',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.supportsPhytoplankton') : 'Higher nitrate supports phytoplankton growth',
        context: t ? t('dataPanel.contexts.suggestsUpwelling') : 'Elevated nitrate suggests upwelling or riverine input'
      };
    }
  }
  
  if (paramName === 'po4' || paramName === 'phosphate') {
    return {
      severity: 'low',
      classification: t ? t('dataPanel.classifications.normalPhosphate') : 'Normal Phosphate',
      environmental_impact: t ? t('dataPanel.environmentalImpacts.supportsProductivity') : 'Phosphate levels support marine primary productivity',
      context: t ? t('dataPanel.contexts.essentialNutrient') : 'Phosphate is essential nutrient for marine phytoplankton'
    };
  }
  
  if (paramName === 'si' || paramName === 'silicate') {
    return {
      severity: 'low',
      classification: t ? t('dataPanel.classifications.normalSilicate') : 'Normal Silicate',
      environmental_impact: t ? t('dataPanel.environmentalImpacts.supportsDiatoms') : 'Silicate supports diatom growth and marine food webs',
      context: t ? t('dataPanel.contexts.importantNutrient') : 'Important nutrient for siliceous marine organisms'
    };
  }
  
  if (paramName === 'chl' || paramName === 'chlorophyll') {
    if (numValue < 0.1) {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.lowChlorophyll') : 'Low Chlorophyll',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.oligotrophic') : 'Indicates oligotrophic (nutrient-poor) ocean conditions',
        context: t ? t('dataPanel.contexts.clearOcean') : 'Typical of clear, deep ocean waters with low productivity'
      };
    } else {
      return {
        severity: 'low',
        classification: t ? t('dataPanel.classifications.moderateChlorophyll') : 'Moderate Chlorophyll',
        environmental_impact: t ? t('dataPanel.environmentalImpacts.activePhytoplankton') : 'Indicates active phytoplankton productivity',
        context: t ? t('dataPanel.contexts.healthyPrimary') : 'Shows healthy primary production in marine ecosystem'
      };
    }
  }
  
  if (paramName === 'nppv') {
    return {
      severity: 'low',
      classification: t ? t('dataPanel.classifications.activePrimaryProduction') : 'Active Primary Production',
      environmental_impact: t ? t('dataPanel.environmentalImpacts.healthyProductivity') : 'Indicates healthy phytoplankton productivity and carbon fixation',
      context: t ? t('dataPanel.contexts.formsBase') : 'Primary production forms base of marine food web'
    };
  }
  
  // Direction parameters
  if (paramName === 'direction' || paramName.includes('direction')) {
    return {
      severity: 'low',
      classification: t ? t('dataPanel.classifications.currentDirection') : 'Current Direction',
      environmental_impact: t ? t('dataPanel.environmentalImpacts.affectsTransport') : 'Current direction affects regional water mass transport',
      context: t ? t('dataPanel.contexts.influencesNutrient') : 'Flow direction influences nutrient and heat distribution'
    };
  }
  
  // Velocity parameters  
  if (paramName === 'uo' || paramName === 'vo' || paramName.includes('velocity')) {
    return {
      severity: 'low',
      classification: t ? t('dataPanel.classifications.oceanVelocity') : 'Ocean Velocity',
      environmental_impact: t ? t('dataPanel.environmentalImpacts.contributes') : 'Contributes to regional circulation and mixing patterns',
      context: t ? t('dataPanel.contexts.affectingTransport') : 'Component of total current flow affecting marine transport'
    };
  }
  
  // Default case for other parameters
  return {
    severity: 'low',
    classification: t ? t('dataPanel.classifications.normalRange') : 'Normal Range',
    environmental_impact: t ? t('dataPanel.environmentalImpacts.withinExpected') : 'Parameter within expected range for ocean health',
    context: t ? t('dataPanel.contexts.stableConditions') : 'Measurement indicates stable marine conditions'
  };
}