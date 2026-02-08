describe('Patient Management Flow', () => {
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

  it('should display patient list', () => {
    // Mock patient list API
    cy.intercept('GET', '**/patients?skip=0&limit=100', {
      statusCode: 200,
      body: {
        patients: [
          {
            patient_uuid: '123',
            given_name: 'John',
            family_name: 'Doe',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          {
            patient_uuid: '456',
            given_name: 'Jane',
            family_name: 'Smith',
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z',
          },
        ],
        total: 2,
      },
    }).as('getPatients');

    cy.visit('/patients');

    cy.wait('@getPatients');

    // Check that patients are displayed
    cy.contains('John Doe').should('be.visible');
    cy.contains('Jane Smith').should('be.visible');
  });

  it('should navigate to patient detail page', () => {
    // Mock patient list
    cy.intercept('GET', '**/patients?skip=0&limit=100', {
      statusCode: 200,
      body: {
        patients: [
          {
            patient_uuid: '123',
            given_name: 'John',
            family_name: 'Doe',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
    });

    // Mock patient detail
    cy.intercept('GET', '**/patients/123', {
      statusCode: 200,
      body: {
        patient_uuid: '123',
        given_name: 'John',
        family_name: 'Doe',
        birthdate: '1990-01-01',
        gender: 'M',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    }).as('getPatientDetail');

    cy.visit('/patients');

    // Click on patient name/link
    cy.contains('John Doe').click();

    cy.wait('@getPatientDetail');

    // Should navigate to patient detail page
    cy.url().should('include', '/patients/123');
    cy.contains('John Doe').should('be.visible');
  });

  it('should create new patient', () => {
    // Mock patient creation
    cy.intercept('POST', '**/patients', {
      statusCode: 201,
      body: {
        patient_uuid: '789',
        given_name: 'Alice',
        family_name: 'Johnson',
        birthdate: '1985-05-15',
        gender: 'F',
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-03T00:00:00Z',
      },
    }).as('createPatient');

    cy.visit('/patients/new');

    // Fill in patient form
    cy.get('input[name="given_name"]').type('Alice');
    cy.get('input[name="family_name"]').type('Johnson');
    cy.get('input[name="birthdate"]').type('1985-05-15');
    cy.get('select[name="gender"]').select('F');

    // Submit form
    cy.get('button[type="submit"]').click();

    cy.wait('@createPatient');

    // Should redirect to patient list or detail
    cy.url().should('include', '/patients');
  });

  it('should edit existing patient', () => {
    // Mock patient detail
    cy.intercept('GET', '**/patients/123', {
      statusCode: 200,
      body: {
        patient_uuid: '123',
        given_name: 'John',
        family_name: 'Doe',
        birthdate: '1990-01-01',
        gender: 'M',
        phone_number: '+1234567890',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    });

    // Mock patient update
    cy.intercept('PUT', '**/patients/123', {
      statusCode: 200,
      body: {
        patient_uuid: '123',
        given_name: 'John',
        family_name: 'Updated',
        birthdate: '1990-01-01',
        gender: 'M',
        phone_number: '+0987654321',
        updated_at: '2024-01-03T00:00:00Z',
      },
    }).as('updatePatient');

    cy.visit('/patients/123/edit');

    // Update patient information
    cy.get('input[name="family_name"]').clear().type('Updated');
    cy.get('input[name="phone_number"]').clear().type('+0987654321');

    // Submit form
    cy.get('button[type="submit"]').click();

    cy.wait('@updatePatient');

    // Should redirect to patient detail
    cy.url().should('include', '/patients/123');
    cy.contains('Updated').should('be.visible');
  });

  it('should delete patient', () => {
    // Mock patient list
    cy.intercept('GET', '**/patients?skip=0&limit=100', {
      statusCode: 200,
      body: {
        patients: [
          {
            patient_uuid: '123',
            given_name: 'John',
            family_name: 'Doe',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
    });

    // Mock patient deletion
    cy.intercept('DELETE', '**/patients/123', {
      statusCode: 200,
    }).as('deletePatient');

    cy.visit('/patients');

    // Click delete button (assuming it exists)
    cy.contains('Delete').click();

    // Confirm deletion (if confirmation dialog exists)
    cy.contains('Confirm').click();

    cy.wait('@deletePatient');

    // Patient should be removed from list
    cy.contains('John Doe').should('not.exist');
  });

  it('should handle patient creation errors', () => {
    // Mock patient creation failure
    cy.intercept('POST', '**/patients', {
      statusCode: 400,
      body: { detail: 'Invalid patient data' },
    }).as('createPatientError');

    cy.visit('/patients/new');

    // Fill in invalid data
    cy.get('input[name="given_name"]').type('A'); // Too short
    cy.get('input[name="family_name"]').type('B'); // Too short

    // Submit form
    cy.get('button[type="submit"]').click();

    cy.wait('@createPatientError');

    // Should show error message
    cy.contains('Invalid patient data').should('be.visible');

    // Should stay on form page
    cy.url().should('include', '/patients/new');
  });

  it('should search and filter patients', () => {
    // Mock filtered patient list
    cy.intercept('GET', '**/patients?skip=0&limit=100&search=john', {
      statusCode: 200,
      body: {
        patients: [
          {
            patient_uuid: '123',
            given_name: 'John',
            family_name: 'Doe',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      },
    }).as('searchPatients');

    cy.visit('/patients');

    // Type in search field
    cy.get('input[placeholder*="search"]').type('john');

    // Submit search or wait for auto-search
    cy.get('button[type="submit"]').click();

    cy.wait('@searchPatients');

    // Should show filtered results
    cy.contains('John Doe').should('be.visible');
  });
});
