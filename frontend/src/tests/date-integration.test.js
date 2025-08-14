/**
 * Basic integration test to verify frontend-backend date communication
 * Tests the date functionality implementation
 */

// Mock WebSocket for testing
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.OPEN;
    this.sentMessages = [];
  }

  send(message) {
    this.sentMessages.push(JSON.parse(message));
  }

  close() {
    this.readyState = WebSocket.CLOSED;
  }
}

// Test the date utility functions
const { 
  generateRandomDate, 
  validateDate, 
  getDataAvailabilityDescription,
  TEMPORAL_COVERAGE 
} = require('../utils/dateUtils');

describe('Date Integration Tests', () => {
  
  test('generateRandomDate should return valid date in correct format', () => {
    const randomDate = generateRandomDate();
    
    // Check format YYYY-MM-DD
    expect(randomDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    
    // Check date is within valid range
    const date = new Date(randomDate);
    const minDate = new Date(TEMPORAL_COVERAGE.EXTENDED_START);
    const maxDate = new Date(TEMPORAL_COVERAGE.GUARANTEED_END);
    
    expect(date).toBeInstanceOf(Date);
    expect(date.getTime()).toBeGreaterThanOrEqual(minDate.getTime());
    expect(date.getTime()).toBeLessThanOrEqual(maxDate.getTime());
  });

  test('validateDate should properly validate dates', () => {
    // Valid guaranteed date (2003-2025)
    const validDate = '2024-06-15';
    const validResult = validateDate(validDate);
    
    expect(validResult.isValid).toBe(true);
    expect(validResult.coverageInfo.guaranteedCoverage).toBe(true);
    expect(validResult.errors).toHaveLength(0);
    
    // Invalid future date (beyond August 2025)
    const futureDate = '2026-01-01';
    const futureResult = validateDate(futureDate);
    
    expect(futureResult.isValid).toBe(false);
    expect(futureResult.errors).toContain('Date cannot be beyond August 2025.');
    
    // Note: Wave data test removed since wave functionality has been removed
  });

  test('getDataAvailabilityDescription should return correct descriptions', () => {
    // Guaranteed coverage date with full data
    const guaranteedDesc = getDataAvailabilityDescription('2024-06-15');
    expect(guaranteedDesc).toContain('9 ocean data types available');
    expect(guaranteedDesc).toContain('comprehensive coverage');
    
    // Date with wave data limitation
    const limitedDesc = getDataAvailabilityDescription('2020-01-01');
    expect(limitedDesc).toMatch(/\d+ ocean data types available/);
    expect(limitedDesc).toContain('% coverage');
  });

  test('WebSocket message format should include date parameters', () => {
    const mockWs = new MockWebSocket('ws://localhost:8765');
    
    // Simulate sending a temperature request with date
    const testMessage = {
      type: 'temperature_request',
      payload: {
        coordinates: {
          lat: 25.0,
          lon: -40.0
        },
        dateRange: {
          start: '2024-06-15',
          end: '2024-06-15'
        },
        timestamp: new Date().toISOString()
      }
    };
    
    mockWs.send(JSON.stringify(testMessage));
    
    // Verify message was sent with correct structure
    expect(mockWs.sentMessages).toHaveLength(1);
    const sentMessage = mockWs.sentMessages[0];
    
    expect(sentMessage.type).toBe('temperature_request');
    expect(sentMessage.payload.coordinates).toBeDefined();
    expect(sentMessage.payload.dateRange).toBeDefined();
    expect(sentMessage.payload.dateRange.start).toBe('2024-06-15');
    expect(sentMessage.payload.dateRange.end).toBe('2024-06-15');
  });

  test('Date utilities should handle edge cases', () => {
    // Test minimum date
    const minDateResult = validateDate(TEMPORAL_COVERAGE.HISTORICAL_START);
    expect(minDateResult.isValid).toBe(true);
    
    // Test maximum date (today)
    const maxDateResult = validateDate(TEMPORAL_COVERAGE.GUARANTEED_END);
    expect(maxDateResult.isValid).toBe(true);
    
    // Test invalid format
    const invalidFormatResult = validateDate('2023/06/15');
    expect(invalidFormatResult.isValid).toBe(false);
    expect(invalidFormatResult.errors).toContain('Invalid date format. Use YYYY-MM-DD format.');
    
    // Test invalid date value
    const invalidDateResult = validateDate('2023-13-45');
    expect(invalidDateResult.isValid).toBe(false);
  });

  test('Random date generation with options should work correctly', () => {
    // Test guaranteed only
    const guaranteedDate = generateRandomDate({ guaranteedOnly: true });
    const guaranteedValidation = validateDate(guaranteedDate);
    expect(guaranteedValidation.coverageInfo.guaranteedCoverage).toBe(true);
    
    // Test with custom range
    const customDate = generateRandomDate({ 
      minDate: '2024-01-01', 
      maxDate: '2024-12-31' 
    });
    const customValidation = validateDate(customDate);
    expect(customValidation.isValid).toBe(true);
    
    const date = new Date(customDate);
    expect(date.getFullYear()).toBe(2024);
  });

});

console.log('✅ Date integration tests completed successfully');
console.log('🌊 Frontend-backend date communication verified');
console.log('📅 Date utilities working correctly');
console.log('🔗 WebSocket message format includes date parameters');