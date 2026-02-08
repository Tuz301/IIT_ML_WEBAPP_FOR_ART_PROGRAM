// Custom Cypress commands for IIT ML Healthcare Application

// Login command
Cypress.Commands.add('login', (username: string, password: string) => {
  cy.intercept('POST', '**/auth/login', {
    statusCode: 200,
    body: {
      access_token: 'mock-token',
      token_type: 'bearer',
      expires_in: 3600,
    },
  }).as('loginRequest');

  cy.visit('/login');
  cy.get('input[type="text"]').type(username);
  cy.get('input[type="password"]').type(password);
  cy.get('button[type="submit"]').click();

  cy.wait('@loginRequest');
  cy.url().should('include', '/');
});

// Create patient command
Cypress.Commands.add('createPatient', (patientData: any) => {
  cy.intercept('POST', '**/patients', {
    statusCode: 201,
    body: {
      patient_uuid: 'test-uuid-' + Date.now(),
      ...patientData,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  }).as('createPatient');

  cy.visit('/patients/new');

  // Fill form
  if (patientData.given_name) cy.get('input[name="given_name"]').type(patientData.given_name);
  if (patientData.family_name) cy.get('input[name="family_name"]').type(patientData.family_name);
  if (patientData.birthdate) cy.get('input[name="birthdate"]').type(patientData.birthdate);
  if (patientData.gender) cy.get('select[name="gender"]').select(patientData.gender);
  if (patientData.phone_number) cy.get('input[name="phone_number"]').type(patientData.phone_number);

  cy.get('button[type="submit"]').click();
  cy.wait('@createPatient');
});

// Create prediction command
Cypress.Commands.add('createPrediction', (predictionData: any) => {
  cy.intercept('POST', '**/predictions', {
    statusCode: 201,
    body: {
      id: Date.now(),
      ...predictionData,
      risk_level: predictionData.risk_score > 0.7 ? 'high' : predictionData.risk_score > 0.4 ? 'medium' : 'low',
      confidence: 0.85,
      model_version: '1.0.0',
      prediction_timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  }).as('createPrediction');

  cy.visit('/predict');

  // Fill form
  cy.get('input[name="patient_uuid"]').type(predictionData.patient_uuid);
  cy.get('input[name="age"]').type(predictionData.age.toString());
  cy.get('input[name="viral_load"]').type(predictionData.viral_load.toString());

  cy.get('button[type="submit"]').click();
  cy.wait('@createPrediction');
});

// Wait for API calls to complete
Cypress.Commands.add('waitForAllAPICalls', () => {
  cy.window().then((win) => {
    // Wait for any pending fetch requests
    cy.wait(1000); // Simple wait, could be improved with more sophisticated waiting
  });
});

// Clear all app data
Cypress.Commands.add('clearAppData', () => {
  cy.window().then((win) => {
    win.localStorage.clear();
    win.sessionStorage.clear();
  });
});

// Check for loading states
Cypress.Commands.add('shouldNotBeLoading', () => {
  cy.get('[data-testid="loading"]').should('not.exist');
  cy.get('.animate-spin').should('not.exist');
});

// Check for error states
Cypress.Commands.add('shouldNotHaveErrors', () => {
  cy.get('[data-testid="error"]').should('not.exist');
  cy.get('.text-red-500').should('not.exist');
});

// Navigation helpers
Cypress.Commands.add('navigateToDashboard', () => {
  cy.get('[data-testid="nav-dashboard"]').click();
  cy.url().should('include', '/');
});

Cypress.Commands.add('navigateToPatients', () => {
  cy.get('[data-testid="nav-patients"]').click();
  cy.url().should('include', '/patients');
});

Cypress.Commands.add('navigateToPredict', () => {
  cy.get('[data-testid="nav-predict"]').click();
  cy.url().should('include', '/predict');
});

Cypress.Commands.add('navigateToMetrics', () => {
  cy.get('[data-testid="nav-metrics"]').click();
  cy.url().should('include', '/metrics');
});

Cypress.Commands.add('navigateToReports', () => {
  cy.get('[data-testid="nav-reports"]').click();
  cy.url().should('include', '/reports');
});

Cypress.Commands.add('navigateToProfile', () => {
  cy.get('[data-testid="nav-profile"]').click();
  cy.url().should('include', '/profile');
});

// Type definitions for custom commands
declare global {
  namespace Cypress {
    interface Chainable {
      login(username: string, password: string): Chainable<void>;
      createPatient(patientData: any): Chainable<void>;
      createPrediction(predictionData: any): Chainable<void>;
      waitForAllAPICalls(): Chainable<void>;
      clearAppData(): Chainable<void>;
      shouldNotBeLoading(): Chainable<void>;
      shouldNotHaveErrors(): Chainable<void>;
      navigateToDashboard(): Chainable<void>;
      navigateToPatients(): Chainable<void>;
      navigateToPredict(): Chainable<void>;
      navigateToMetrics(): Chainable<void>;
      navigateToReports(): Chainable<void>;
      navigateToProfile(): Chainable<void>;
    }
  }
}

export {};
