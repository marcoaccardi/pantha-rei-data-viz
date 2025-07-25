/**
 * Date utilities for ocean data temporal coverage and random date generation
 */

// Temporal coverage constants based on backend-api data availability
export const TEMPORAL_COVERAGE = {
  // Guaranteed availability window (all 10 data types available)
  GUARANTEED_START: '2022-06-01',
  GUARANTEED_END: (() => {
    const today = new Date();
    today.setUTCHours(0, 0, 0, 0);
    return today.toISOString().split('T')[0];
  })(),
  
  // Extended availability (some data types from earlier dates)
  EXTENDED_START: '2021-11-01',
  
  // Maximum historical coverage (biodiversity and microplastics)
  HISTORICAL_START: '1972-01-01',
  
  // Data source specific coverage
  SST_START: '2021-01-01',
  SALINITY_START: '2022-06-01',
  CURRENTS_START: '2022-06-01',
  WAVES_START: '2022-06-01',
  CHLOROPHYLL_START: '2021-11-01',
  PH_START: '2021-11-01',
  BIODIVERSITY_START: '1972-01-01',
  MICROPLASTICS_START: '1972-01-01'
};

export interface DateRange {
  start: string;
  end: string;
}

export interface DateValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  suggestedDate?: string;
  coverageInfo?: {
    guaranteedCoverage: boolean;
    extendedCoverage: boolean;
    availableDataTypes: string[];
    unavailableDataTypes: string[];
  };
}

/**
 * Generate a random date within the data availability window
 * @param options Configuration for random date generation
 * @returns Random date string in YYYY-MM-DD format
 */
export function generateRandomDate(options: {
  preferRecent?: boolean; // Weight towards recent dates (default: true)
  guaranteedOnly?: boolean; // Only use guaranteed availability window (default: false)
  minDate?: string; // Custom minimum date
  maxDate?: string; // Custom maximum date
} = {}): string {
  const {
    preferRecent = true,
    guaranteedOnly = false,
    minDate,
    maxDate
  } = options;

  // Determine date range
  let startDateStr: string;
  let endDateStr: string;

  if (minDate && maxDate) {
    startDateStr = minDate;
    endDateStr = maxDate;
  } else if (guaranteedOnly) {
    startDateStr = TEMPORAL_COVERAGE.GUARANTEED_START;
    endDateStr = TEMPORAL_COVERAGE.GUARANTEED_END;
  } else {
    startDateStr = TEMPORAL_COVERAGE.EXTENDED_START;
    endDateStr = TEMPORAL_COVERAGE.GUARANTEED_END;
  }

  const startDate = new Date(startDateStr);
  const endDate = new Date(endDateStr);

  // Validate date range with recursion protection
  if (startDate >= endDate) {
    if (guaranteedOnly) {
      // Prevent infinite recursion - use hardcoded fallback
      console.error('Invalid guaranteed date range, using fallback');
      return '2023-06-01';
    }
    console.warn('Invalid date range for random generation, using guaranteed window');
    return generateRandomDate({ guaranteedOnly: true });
  }

  let selectedDate: Date;

  if (preferRecent) {
    // Weighted distribution: 70% chance for recent dates (last 2 years)
    const recentCutoff = new Date();
    recentCutoff.setFullYear(recentCutoff.getFullYear() - 2);
    
    // Ensure recent cutoff is within our available range
    const effectiveRecentStart = new Date(Math.max(recentCutoff.getTime(), startDate.getTime()));
    
    if (Math.random() < 0.7 && effectiveRecentStart < endDate) {
      // Generate recent date
      const randomTime = effectiveRecentStart.getTime() + 
        Math.random() * (endDate.getTime() - effectiveRecentStart.getTime());
      selectedDate = new Date(randomTime);
    } else {
      // Generate any date in range
      const randomTime = startDate.getTime() + 
        Math.random() * (endDate.getTime() - startDate.getTime());
      selectedDate = new Date(randomTime);
    }
  } else {
    // Uniform distribution across entire range
    const randomTime = startDate.getTime() + 
      Math.random() * (endDate.getTime() - startDate.getTime());
    selectedDate = new Date(randomTime);
  }

  const result = selectedDate.toISOString().split('T')[0];
  
  // Development logging (can be replaced with proper logging system)
  console.log(`📅 Generated random date: ${result} (range: ${startDateStr} to ${endDateStr})`);
  
  return result;
}

/**
 * Validate a date for ocean data availability
 * @param date Date string in YYYY-MM-DD format
 * @returns Validation result with coverage information
 */
export function validateDate(date: string): DateValidationResult {
  const result: DateValidationResult = {
    isValid: true,
    errors: [],
    warnings: [],
    coverageInfo: {
      guaranteedCoverage: false,
      extendedCoverage: false,
      availableDataTypes: [],
      unavailableDataTypes: []
    }
  };

  // Basic format validation
  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  if (!dateRegex.test(date)) {
    result.isValid = false;
    result.errors.push('Invalid date format. Use YYYY-MM-DD format.');
    return result;
  }
  
  // Semantic date validation
  const [year, month, day] = date.split('-').map(Number);
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    result.isValid = false;
    result.errors.push('Invalid date values.');
    return result;
  }

  const inputDate = new Date(date);
  const today = new Date();
  
  // Check if date is valid
  if (isNaN(inputDate.getTime())) {
    result.isValid = false;
    result.errors.push('Invalid date value.');
    return result;
  }

  // Check if date is in the future
  if (inputDate > today) {
    result.isValid = false;
    result.errors.push('Date cannot be in the future.');
    result.suggestedDate = today.toISOString().split('T')[0];
    return result;
  }

  // Check coverage windows
  const guaranteedStart = new Date(TEMPORAL_COVERAGE.GUARANTEED_START);
  const extendedStart = new Date(TEMPORAL_COVERAGE.EXTENDED_START);
  const historicalStart = new Date(TEMPORAL_COVERAGE.HISTORICAL_START);

  if (inputDate >= guaranteedStart) {
    // Guaranteed coverage - all data types available
    result.coverageInfo!.guaranteedCoverage = true;
    result.coverageInfo!.extendedCoverage = true;
    result.coverageInfo!.availableDataTypes = [
      'Sea Surface Temperature',
      'Ocean Currents', 
      'Salinity',
      'Wave Height & Period',
      'Chlorophyll/Plankton',
      'pH/Ocean Acidification',
      'Water Quality Indicators',
      'Marine Biodiversity',
      'Sea Ice Extent',
      'Microplastics'
    ];
  } else if (inputDate >= extendedStart) {
    // Extended coverage - most data types available  
    result.coverageInfo!.extendedCoverage = true;
    result.coverageInfo!.availableDataTypes = [
      'Sea Surface Temperature',
      'Chlorophyll/Plankton', 
      'pH/Ocean Acidification',
      'Water Quality Indicators',
      'Marine Biodiversity',
      'Sea Ice Extent',
      'Microplastics'
    ];
    result.coverageInfo!.unavailableDataTypes = [
      'Ocean Currents',
      'Salinity', 
      'Wave Height & Period'
    ];
    result.warnings.push('Limited data coverage - some ocean parameters not available for this date.');
  } else if (inputDate >= historicalStart) {
    // Historical coverage - only research data available
    result.coverageInfo!.availableDataTypes = [
      'Marine Biodiversity',
      'Microplastics'
    ];
    result.coverageInfo!.unavailableDataTypes = [
      'Sea Surface Temperature',
      'Ocean Currents',
      'Salinity',
      'Wave Height & Period', 
      'Chlorophyll/Plankton',
      'pH/Ocean Acidification',
      'Water Quality Indicators',
      'Sea Ice Extent'
    ];
    result.warnings.push('Very limited historical data - only biodiversity and microplastics available.');
    result.suggestedDate = TEMPORAL_COVERAGE.GUARANTEED_START;
  } else {
    // Date too old
    result.isValid = false;
    result.errors.push(`Date is before data coverage begins (${TEMPORAL_COVERAGE.HISTORICAL_START}).`);
    result.suggestedDate = TEMPORAL_COVERAGE.GUARANTEED_START;
  }

  return result;
}

/**
 * Get the date range with guaranteed data availability
 * @returns DateRange with guaranteed coverage dates
 */
export function getGuaranteedDateRange(): DateRange {
  return {
    start: TEMPORAL_COVERAGE.GUARANTEED_START,
    end: TEMPORAL_COVERAGE.GUARANTEED_END
  };
}

/**
 * Get the extended date range with partial data availability  
 * @returns DateRange with extended coverage dates
 */
export function getExtendedDateRange(): DateRange {
  return {
    start: TEMPORAL_COVERAGE.EXTENDED_START,
    end: TEMPORAL_COVERAGE.GUARANTEED_END
  };
}

/**
 * Format a date for display with coverage information
 * @param date Date string in YYYY-MM-DD format
 * @returns Formatted display string with coverage info
 */
export function formatDateWithCoverage(date: string): string {
  const validation = validateDate(date);
  
  if (!validation.isValid) {
    return `${date} (Invalid)`;
  }

  if (validation.coverageInfo?.guaranteedCoverage) {
    return `${date} (All Data Available)`;
  } else if (validation.coverageInfo?.extendedCoverage) {
    return `${date} (Limited Data)`;
  } else {
    return `${date} (Research Data Only)`;
  }
}

/**
 * Get a user-friendly description of data availability for a date
 * @param date Date string in YYYY-MM-DD format  
 * @returns Description of what data is available
 */
export function getDataAvailabilityDescription(date: string): string {
  const validation = validateDate(date);
  
  if (!validation.isValid) {
    return 'Invalid date - no data available';
  }

  const available = validation.coverageInfo?.availableDataTypes?.length || 0;
  const unavailable = validation.coverageInfo?.unavailableDataTypes?.length || 0;
  const total = available + unavailable;

  if (validation.coverageInfo?.guaranteedCoverage) {
    return `All 10 ocean data types available (100% coverage)`;
  } else if (validation.coverageInfo?.extendedCoverage) {
    return `${available} of ${total} ocean data types available (${Math.round(available/total*100)}% coverage)`;
  } else {
    return `Only ${available} research data types available`;
  }
}

/**
 * Generate a random date and location combination
 * @param options Configuration for generation
 * @returns Object with random coordinates and date
 */
export function generateRandomDateAndLocation(options: {
  guaranteedOnly?: boolean;
  preferRecent?: boolean;
} = {}) {
  // This function would work with the existing coordinate generation
  // For now, just return the date part - coordinates handled by existing function
  return {
    date: generateRandomDate(options),
    // Note: coordinates will be generated by existing generateRandomOceanLocation function
  };
}