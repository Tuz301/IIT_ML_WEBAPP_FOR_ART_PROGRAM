/**
 * Comprehensive End-to-End Tests for IIT ML Service
 * 
 * This test suite covers:
 * - Authentication flow (login, logout, token refresh)
 * - Cookie-based authentication
 * - Patient management
 * - Prediction workflow
 * - Risk visualization
 * - Session timeout
 */

describe('Authentication Flow', () => {
  const testUser = {
    username: 'testuser',
    password: 'TestPassword123!',
    email: 'test@example.com'
  };

  beforeEach(() => {
    // Clear cookies and localStorage before each test
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('should display login page', () => {
    cy.visit('/login');
    cy.contains('h1', /login|sign in/i).should('be.visible');
    cy.get('input[name="username"]').should('be.visible');
    cy.get('input[name="password"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
  });

  it('should show validation errors for empty credentials', () => {
    cy.visit('/login');
    cy.get('button[type="submit"]').click();
    
    // Check for error messages
    cy.contains(/username|required|invalid credentials/i).should('be.visible');
  });

  it('should show error for invalid credentials', () => {
    cy.visit('/login');
    cy.get('input[name="username"]').type('invaliduser');
    cy.get('input[name="password"]').type('wrongpassword');
    cy.get('button[type="submit"]').click();
    
    cy.contains(/invalid|incorrect|failed/i, { timeout: 10000 }).should('be.visible');
  });

  it('should login successfully with valid credentials', () => {
    cy.visit('/login');
    cy.get('input[name="username"]').type(testUser.username);
    cy.get('input[name="password"]').type(testUser.password);
    cy.get('button[type="submit"]').click();
    
    // Should redirect to dashboard
    cy.url().should('include', '/dashboard');
    cy.contains(/welcome|dashboard|predict/i, { timeout: 10000 }).should('be.visible');
  });

  it('should set httpOnly cookies on login', () => {
    cy.visit('/login');
    cy.get('input[name="username"]').type(testUser.username);
    cy.get('input[name="password"]').type(testUser.password);
    cy.get('button[type="submit"]').click();
    
    // Check for auth cookies (httpOnly cookies won't be visible to JS, but we can check behavior)
    cy.url().should('include', '/dashboard');
    
    // Verify we can access protected routes
    cy.visit('/patients');
    cy.contains(/patients|patient list/i).should('be.visible');
  });

  it('should logout successfully', () => {
    // Login first
    cy.login(testUser.username, testUser.password);
    
    // Logout
    cy.get('[data-testid="logout-button"]').click();
    cy.contains(/logout|sign out/i).click();
    
    // Should redirect to login
    cy.url().should('include', '/login');
    
    // Should not be able to access protected routes
    cy.visit('/dashboard');
    cy.url().should('include', '/login');
  });

  it('should handle session timeout', () => {
    cy.login(testUser.username, testUser.password);
    
    // Wait for session to expire (adjust based on your session timeout)
    // For testing, we can simulate this by clearing cookies
    cy.clearCookies();
    
    // Try to access a protected route
    cy.visit('/dashboard');
    
    // Should redirect to login with session expired message
    cy.url().should('include', '/login');
    cy.contains(/session expired|logged out/i).should('be.visible');
  });
});

describe('Patient Management', () => {
  beforeEach(() => {
    cy.login('testuser', 'TestPassword123!');
  });

  it('should display patient list', () => {
    cy.visit('/patients');
    cy.contains(/patients|patient list/i).should('be.visible');
    
    // Check for table or list of patients
    cy.get('table, [data-testid="patient-list"]').should('be.visible');
  });

  it('should search patients', () => {
    cy.visit('/patients');
    
    // Enter search term
    cy.get('input[placeholder*="search" i]').type('John');
    cy.get('button[aria-label*="search" i]').click();
    
    // Wait for results
    cy.contains(/john/i, { timeout: 10000 }).should('be.visible');
  });

  it('should create new patient', () => {
    cy.visit('/patients/new');
    
    // Fill in patient form
    cy.get('input[name="given_name"]').type('Jane');
    cy.get('input[name="family_name"]').type('Doe');
    cy.get('input[name="phone_number"]').type('+1234567890');
    
    // Submit form
    cy.get('button[type="submit"]').click();
    
    // Should show success message
    cy.contains(/success|created|saved/i, { timeout: 10000 }).should('be.visible');
  });

  it('should view patient details', () => {
    // Navigate to a specific patient
    cy.visit('/patients');
    
    // Click on first patient in list
    cy.get('table tbody tr:first-child').click();
    
    // Should show patient details
    cy.contains(/patient details|patient information/i).should('be.visible');
    cy.contains(/given name|family name|phone/i).should('be.visible');
  });
});

describe('Prediction Workflow', () => {
  beforeEach(() => {
    cy.login('testuser', 'TestPassword123!');
  });

  it('should display prediction form', () => {
    cy.visit('/predict');
    cy.contains(/predict|prediction|risk assessment/i).should('be.visible');
    
    // Check for form fields
    cy.get('form').should('be.visible');
  });

  it('should validate prediction form', () => {
    cy.visit('/predict');
    
    // Try to submit empty form
    cy.get('button[type="submit"]').click();
    
    // Should show validation errors
    cy.contains(/required|invalid|missing/i).should('be.visible');
  });

  it('should submit prediction request', () => {
    cy.visit('/predict');
    
    // Fill in required fields (adjust based on your form)
    cy.get('input[name="patient_uuid"]').type('123e4567-e89b-12d3-a456-426614174000');
    cy.get('input[name="age"]').type('35');
    cy.get('select[name="gender"]').select('M');
    
    // Submit form
    cy.get('button[type="submit"]').click();
    
    // Should show prediction result
    cy.contains(/risk score|risk level|prediction/i, { timeout: 15000 }).should('be.visible');
  });

  it('should display risk visualization', () => {
    cy.visit('/predict');
    
    // Submit a prediction first
    cy.submitPrediction({
      patient_uuid: '123e4567-e89b-12d3-a456-426614174000',
      age: 35,
      gender: 'M'
    });
    
    // Check for risk chart or visualization
    cy.get('[data-testid="risk-chart"], svg, canvas').should('be.visible');
  });

  it('should show prediction history', () => {
    cy.visit('/patients');
    
    // Click on a patient
    cy.get('table tbody tr:first-child').click();
    
    // Should show prediction history
    cy.contains(/predictions|history|risk assessment/i).should('be.visible');
  });
});

describe('Dashboard Analytics', () => {
  beforeEach(() => {
    cy.login('testuser', 'TestPassword123!');
  });

  it('should display dashboard', () => {
    cy.visit('/dashboard');
    cy.contains(/dashboard|overview/i).should('be.visible');
  });

  it('should show statistics cards', () => {
    cy.visit('/dashboard');
    
    // Check for stat cards
    cy.get('[data-testid="stat-card"]').should('have.length.greaterThan', 0);
  });

  it('should display risk distribution', () => {
    cy.visit('/dashboard');
    
    // Check for risk distribution chart
    cy.contains(/risk distribution|low risk|medium risk|high risk/i).should('be.visible');
  });

  it('should show recent predictions', () => {
    cy.visit('/dashboard');
    
    // Check for recent predictions section
    cy.contains(/recent predictions|latest predictions/i).should('be.visible');
  });
});

describe('Error Handling', () => {
  it('should handle network errors gracefully', () => {
    // Simulate network error
    cy.intercept('POST', '/v1/auth/login', { forceNetworkError: true });
    
    cy.visit('/login');
    cy.get('input[name="username"]').type('testuser');
    cy.get('input[name="password"]').type('TestPassword123!');
    cy.get('button[type="submit"]').click();
    
    // Should show error message
    cy.contains(/network error|unable to connect|failed/i).should('be.visible');
  });

  it('should handle server errors', () => {
    cy.intercept('POST', '/v1/auth/login', { statusCode: 500 });
    
    cy.visit('/login');
    cy.get('input[name="username"]').type('testuser');
    cy.get('input[name="password"]').type('TestPassword123!');
    cy.get('button[type="submit"]').click();
    
    // Should show server error message
    cy.contains(/server error|internal error|try again/i).should('be.visible');
  });
});

describe('Performance', () => {
  it('should load dashboard within acceptable time', () => {
    cy.login('testuser', 'TestPassword123!');
    
    cy.visit('/dashboard', {
      onBeforeLoad: (win) => {
        win.performance.mark('start');
      }
    }).then((win) => {
      win.performance.mark('end');
      win.performance.measure('dashboardLoad', 'start', 'end');
      
      const measure = win.performance.getEntriesByName('dashboardLoad')[0];
      expect(measure.duration).to.be.lessThan(3000); // 3 seconds
    });
  });

  it('should complete prediction within acceptable time', () => {
    cy.login('testuser', 'TestPassword123!');
    cy.visit('/predict');
    
    // Submit prediction and measure time
    cy.submitPrediction({
      patient_uuid: '123e4567-e89b-12d3-a456-426614174000',
      age: 35,
      gender: 'M'
    }, {
      timeout: 10000
    });
    
    // Should complete within 10 seconds
    cy.contains(/risk score|prediction/i, { timeout: 10000 }).should('be.visible');
  });
});

// Custom commands
declare global {
  namespace Cypress {
    interface Chainable {
      login(username: string, password: string): Chainable<void>;
      submitPrediction(data: any, options?: any): Chainable<void>;
    }
  }
}

Cypress.Commands.add('login', (username, password) => {
  cy.visit('/login');
  cy.get('input[name="username"]').type(username);
  cy.get('input[name="password"]').type(password);
  cy.get('button[type="submit"]').click();
  cy.url().should('include', '/dashboard', { timeout: 10000 });
});

Cypress.Commands.add('submitPrediction', (data, options = {}) => {
  cy.visit('/predict');
  
  if (data.patient_uuid) {
    cy.get('input[name="patient_uuid"]').type(data.patient_uuid);
  }
  if (data.age) {
    cy.get('input[name="age"]').type(data.age);
  }
  if (data.gender) {
    cy.get('select[name="gender"]').select(data.gender);
  }
  
  cy.get('button[type="submit"]').click();
});
