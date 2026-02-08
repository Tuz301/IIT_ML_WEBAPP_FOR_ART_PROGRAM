describe('Prediction Workflow', () => {
  beforeEach(() => {
    // Login before each test
    cy.intercept('POST', '**/auth/login', {
      statusCode: 200,
      body: {
        access_token: 'mock-token',
        token_type: 'bearer',
        expires_in: 3600,
      },
    });

    cy.visit('/login');
    cy.get('input[type="text"]').type('testuser');
    cy.get('input[type="password"]').type('testpass');
    cy.get('button[type="submit"]').click();

    // Wait for navigation to dashboard
    cy.url().should('include', '/');
  });

  it('should display prediction form', () => {
    cy.visit('/predict');

    cy.contains('Make Prediction').should('be.visible');
    cy.get('input[name="patient_uuid"]').should('be.visible');
    cy.get('input[name="age"]').should('be.visible');
    cy.get('input[name="viral_load"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
  });

  it('should create prediction successfully', () => {
    // Mock patient lookup
    cy.intercept('GET', '**/patients/123', {
      statusCode: 200,
      body: {
        patient_uuid: '123',
        given_name: 'John',
        family_name: 'Doe',
        birthdate: '1990-01-01',
        gender: 'M',
      },
    });

    // Mock prediction creation
    cy.intercept('POST', '**/predictions', {
      statusCode: 201,
      body: {
        id: 1,
        patient_uuid: '123',
        risk_score: 0.75,
        risk_level: 'high',
        confidence: 0.85,
        features_used: { age: 34, viral_load: 1500 },
        model_version: '1.0.0',
        prediction_timestamp: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    }).as('createPrediction');

    cy.visit('/predict');

    // Fill prediction form
    cy.get('input[name="patient_uuid"]').type('123');
    cy.get('input[name="age"]').type('34');
    cy.get('input[name="viral_load"]').type('1500');

    // Submit form
    cy.get('button[type="submit"]').click();

    cy.wait('@createPrediction');

    // Should show prediction results
    cy.contains('High Risk').should('be.visible');
    cy.contains('75%').should('be.visible');
    cy.contains('Confidence: 85%').should('be.visible');
  });

  it('should display prediction history', () => {
    // Mock predictions list
    cy.intercept('GET', '**/predictions?skip=0&limit=10', {
      statusCode: 200,
      body: {
        predictions: [
          {
            id: 1,
            patient_uuid: '123',
            risk_score: 0.75,
            risk_level: 'high',
            confidence: 0.85,
            features_used: { age: 34, viral_load: 1500 },
            model_version: '1.0.0',
            prediction_timestamp: '2024-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 2,
            patient_uuid: '456',
            risk_score: 0.3,
            risk_level: 'low',
            confidence: 0.92,
            features_used: { age: 28, viral_load: 200 },
            model_version: '1.0.0',
            prediction_timestamp: '2024-01-02T00:00:00Z',
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z',
          },
        ],
        total: 2,
      },
    }).as('getPredictions');

    cy.visit('/predict');

    cy.wait('@getPredictions');

    // Should display prediction history
    cy.contains('Prediction History').should('be.visible');
    cy.contains('High Risk').should('be.visible');
    cy.contains('Low Risk').should('be.visible');
    cy.contains('Patient 123').should('be.visible');
    cy.contains('Patient 456').should('be.visible');
  });

  it('should filter predictions by risk level', () => {
    // Mock filtered predictions
    cy.intercept('GET', '**/predictions?skip=0&limit=10&risk_level=high', {
      statusCode: 200,
      body: {
        predictions: [
          {
            id: 1,
            patient_uuid: '123',
            risk_score: 0.75,
            risk_level: 'high',
            confidence: 0.85,
            features_used: { age: 34, viral_load: 1500 },
            model_version: '1.0.0',
            prediction_timestamp: '2024-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
    }).as('filterPredictions');

    cy.visit('/predict');

    // Select risk level filter
    cy.get('select[name="risk_level"]').select('high');

    cy.wait('@filterPredictions');

    // Should show only high risk predictions
    cy.contains('High Risk').should('be.visible');
    cy.contains('Low Risk').should('not.exist');
  });

  it('should handle prediction errors', () => {
    // Mock prediction creation failure
    cy.intercept('POST', '**/predictions', {
      statusCode: 400,
      body: { detail: 'Invalid prediction data' },
    }).as('createPredictionError');

    cy.visit('/predict');

    // Fill form with invalid data
    cy.get('input[name="patient_uuid"]').type('invalid');
    cy.get('input[name="age"]').type('-5'); // Invalid age
    cy.get('input[name="viral_load"]').type('abc'); // Invalid number

    // Submit form
    cy.get('button[type="submit"]').click();

    cy.wait('@createPredictionError');

    // Should show error message
    cy.contains('Invalid prediction data').should('be.visible');

    // Should stay on prediction page
    cy.url().should('include', '/predict');
  });

  it('should validate prediction form inputs', () => {
    cy.visit('/predict');

    // Try to submit empty form
    cy.get('button[type="submit"]').click();

    // Should show validation errors
    cy.contains('Patient UUID is required').should('be.visible');
    cy.contains('Age is required').should('be.visible');
    cy.contains('Viral load is required').should('be.visible');

    // Fill invalid data
    cy.get('input[name="age"]').type('150'); // Invalid age
    cy.contains('Age must be between 0 and 120').should('be.visible');

    cy.get('input[name="viral_load"]').type('-100'); // Invalid viral load
    cy.contains('Viral load must be positive').should('be.visible');
  });

  it('should show model metrics integration', () => {
    // Mock model metrics
    cy.intercept('GET', '**/metrics', {
      statusCode: 200,
      body: {
        accuracy: 0.87,
        precision: 0.82,
        recall: 0.91,
        f1_score: 0.86,
        model_version: '1.0.0',
        last_trained: '2024-01-01T00:00:00Z',
      },
    }).as('getMetrics');

    cy.visit('/predict');

    // Should display model confidence info
    cy.contains('Model Version: 1.0.0').should('be.visible');

    cy.wait('@getMetrics');

    // Should show metrics
    cy.contains('Accuracy: 87%').should('be.visible');
    cy.contains('F1 Score: 86%').should('be.visible');
  });

  it('should handle real-time prediction updates', () => {
    // Mock initial prediction
    cy.intercept('POST', '**/predictions', {
      statusCode: 201,
      body: {
        id: 1,
        patient_uuid: '123',
        risk_score: 0.75,
        risk_level: 'high',
        confidence: 0.85,
        features_used: { age: 34, viral_load: 1500 },
        model_version: '1.0.0',
        prediction_timestamp: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    });

    cy.visit('/predict');

    // Fill and submit form
    cy.get('input[name="patient_uuid"]').type('123');
    cy.get('input[name="age"]').type('34');
    cy.get('input[name="viral_load"]').type('1500');
    cy.get('button[type="submit"]').click();

    // Should show prediction results
    cy.contains('High Risk').should('be.visible');

    // Mock updated prediction (simulating real-time update)
    cy.intercept('GET', '**/predictions?skip=0&limit=10', {
      statusCode: 200,
      body: {
        predictions: [
          {
            id: 1,
            patient_uuid: '123',
            risk_score: 0.8, // Updated risk score
            risk_level: 'high',
            confidence: 0.88, // Updated confidence
            features_used: { age: 34, viral_load: 1500 },
            model_version: '1.0.0',
            prediction_timestamp: '2024-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
    });

    // Trigger refresh (assuming there's a refresh button)
    cy.contains('Refresh').click();

    // Should show updated prediction
    cy.contains('80%').should('be.visible');
    cy.contains('Confidence: 88%').should('be.visible');
  });

  it('should export prediction results', () => {
    // Mock predictions for export
    cy.intercept('GET', '**/predictions?skip=0&limit=10', {
      statusCode: 200,
      body: {
        predictions: [
          {
            id: 1,
            patient_uuid: '123',
            risk_score: 0.75,
            risk_level: 'high',
            confidence: 0.85,
            features_used: { age: 34, viral_load: 1500 },
            model_version: '1.0.0',
            prediction_timestamp: '2024-01-01T00:00:00Z',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
    });

    cy.visit('/predict');

    // Click export button (assuming it exists)
    cy.contains('Export').click();

    // Should trigger download (can't easily test actual download in Cypress)
    // But we can check that the export API was called
    cy.intercept('GET', '**/predictions/export', {
      statusCode: 200,
      body: 'mock,csv,data',
      headers: {
        'content-type': 'text/csv',
        'content-disposition': 'attachment; filename=predictions.csv',
      },
    }).as('exportPredictions');

    cy.wait('@exportPredictions');
  });
});
