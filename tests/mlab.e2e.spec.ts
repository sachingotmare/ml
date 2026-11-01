import { test, expect, Page } from '@playwright/test';

// ============================================================
// MLab Diagnostics Center — Full E2E Playwright Test Suite
// URL: https://mlab.sgsoftech.in
// Generated: 2026-07-30
// ============================================================

const BASE_URL = 'https://mlab.sgsoftech.in';
const LAB_CODE = 'DEMO2026';
const USER_ID = 'Adminuser';
const PASSWORD = 'Admin@1234';

// ─────────────────────────────────────────────────────────────
// HELPER: Login
// ─────────────────────────────────────────────────────────────
async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.getByRole('textbox', { name: 'Enter your lab code' }).fill(LAB_CODE);
  await page.getByRole('textbox', { name: 'Enter your user ID' }).fill(USER_ID);
  await page.getByRole('textbox', { name: 'Enter your password' }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign In' }).click();
  await page.waitForURL(`${BASE_URL}/dashboard`);
}

// ─────────────────────────────────────────────────────────────
// SUITE 1: Authentication
// ─────────────────────────────────────────────────────────────
test.describe('Suite 01 — Authentication', () => {

  test('TC-AUTH-01: Login page renders all required elements', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.getByRole('textbox', { name: 'Enter your lab code' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Enter your user ID' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Enter your password' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
    await expect(page.getByText('reCAPTCHA v3')).toBeVisible();
    await expect(page.getByText('Account lockout after 5 failed attempts')).toBeVisible();
  });

  test('TC-AUTH-02: Successful login with valid credentials redirects to dashboard', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(`${BASE_URL}/dashboard`);
    await expect(page.getByRole('heading', { name: /Good (Morning|Afternoon|Evening), Admin/ })).toBeVisible();
  });

  test('TC-AUTH-03: Login fails with invalid credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByRole('textbox', { name: 'Enter your lab code' }).fill('WRONG');
    await page.getByRole('textbox', { name: 'Enter your user ID' }).fill('wronguser');
    await page.getByRole('textbox', { name: 'Enter your password' }).fill('WrongPass@999');
    await page.getByRole('button', { name: 'Sign In' }).click();
    // Should remain on login page
    await expect(page).toHaveURL(`${BASE_URL}/login`);
  });

  test('TC-AUTH-04: Password visibility toggle works', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    const passwordInput = page.getByRole('textbox', { name: 'Enter your password' });
    await passwordInput.fill('TestPassword');
    const toggleBtn = page.locator('button').filter({ has: page.locator('svg') }).last();
    await toggleBtn.click();
    // After toggle, input type should be text
    await expect(passwordInput).toHaveAttribute('type', 'text');
  });

  test('TC-AUTH-05: User profile dropdown shows Sign Out and Settings', async ({ page }) => {
    await login(page);
    await page.getByRole('button', { name: /Admin User Demo Lab/ }).click();
    await expect(page.getByRole('button', { name: 'Profile & Settings' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();
  });

  test('TC-AUTH-06: Sign Out redirects to login page', async ({ page }) => {
    await login(page);
    await page.getByRole('button', { name: /Admin User Demo Lab/ }).click();
    await page.getByRole('button', { name: 'Sign Out' }).click();
    await expect(page).toHaveURL(`${BASE_URL}/login`);
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 2: Dashboard
// ─────────────────────────────────────────────────────────────
test.describe('Suite 02 — Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('TC-DASH-01: Dashboard KPI cards render (even if zero)', async ({ page }) => {
    await expect(page.getByText("Today's Entries")).toBeVisible();
    await expect(page.getByText("Today's Revenue")).toBeVisible();
    await expect(page.getByText('Pending Readings')).toBeVisible();
    await expect(page.getByText('Total Patients Today')).toBeVisible();
  });

  // BUG B1: Dashboard API returns 403 — KPI values should not always be zero after login
  test('TC-DASH-02: [BUG-B1] Dashboard API should return 200 not 403', async ({ page }) => {
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/dashboard')),
      page.goto(`${BASE_URL}/dashboard`),
    ]);
    expect(response.status()).toBe(200); // Currently returns 403 — BUG
  });

  // BUG B2: auth/me returns 401 after login
  test('TC-DASH-03: [BUG-B2] /api/auth/me should return 200 after successful login', async ({ page }) => {
    const [response] = await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/api/auth/me')),
      page.goto(`${BASE_URL}/dashboard`),
    ]);
    expect(response.status()).toBe(200); // Currently returns 401 — BUG
  });

  test('TC-DASH-04: Top Tests and Revenue Split widgets render', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Top Tests' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Revenue Split' })).toBeVisible();
  });

  test('TC-DASH-05: Recent Entries table has correct columns', async ({ page }) => {
    await expect(page.getByRole('columnheader', { name: 'Voucher No' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Patient' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Date' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Amount' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();
  });

  test('TC-DASH-06: Sidebar navigation renders all menu items', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Patient Entry' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Sample Collections' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Readings' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Receipt Entry' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Payment Entry' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Journal Entry' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Inventory' })).toBeVisible();
  });

  test('TC-DASH-07: Collapse sidebar button works', async ({ page }) => {
    const collapseBtn = page.getByRole('button', { name: 'Collapse sidebar' });
    await expect(collapseBtn).toBeVisible();
    await collapseBtn.click();
    // Sidebar should be collapsed (verify by checking logo text is hidden)
    await expect(page.getByRole('heading', { name: 'MLab', level: 1 }).first()).toBeHidden();
  });

  // BUG B6: Global search bar has no result/navigation
  test('TC-DASH-08: [BUG-B6] Global search should navigate or show results on Enter', async ({ page }) => {
    const searchBar = page.getByRole('textbox', { name: 'Search patients, tests, entries...' });
    await searchBar.fill('Rajesh');
    await page.keyboard.press('Enter');
    // Should navigate or show results — currently does nothing (BUG)
    const url = page.url();
    expect(url).toContain('search'); // Will fail until fixed
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 3: Patient Master
// ─────────────────────────────────────────────────────────────
test.describe('Suite 03 — Patient Master', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/patients`);
  });

  test('TC-PAT-01: Patients page renders with search and New Patient button', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Patients' })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /Search patients by name/ })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Patient' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Export' })).toBeVisible();
  });

  test('TC-PAT-02: New patient form has all required fields', async ({ page }) => {
    await page.getByRole('button', { name: 'New Patient' }).click();
    await expect(page.getByRole('textbox', { name: 'Patient full name' })).toBeVisible();
    await expect(page.getByRole('spinbutton')).toBeVisible(); // Age
    await expect(page.getByRole('textbox', { name: 'Mobile number' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'WhatsApp number' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'email@example.com' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Full address' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'City' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Any relevant medical history' })).toBeVisible();
  });

  test('TC-PAT-03: Create a new patient with all fields', async ({ page }) => {
    await page.getByRole('button', { name: 'New Patient' }).click();
    const ts = Date.now();
    const name = `E2E Patient ${ts}`;
    await page.getByRole('textbox', { name: 'Patient full name' }).fill(name);
    await page.getByRole('combobox').nth(1).selectOption('Mr');
    await page.getByRole('spinbutton').fill('28');
    await page.getByRole('combobox').nth(4).selectOption('O+');
    await page.getByRole('textbox', { name: 'Mobile number' }).fill('9876500001');
    await page.getByRole('textbox', { name: 'email@example.com' }).fill(`e2e${ts}@test.com`);
    await page.getByRole('textbox', { name: 'City' }).fill('Mumbai');
    await page.getByRole('button', { name: 'Save' }).nth(1).click();
    // Verify search bar shows new patient
    await expect(page.getByRole('combobox', { name: /Search patients by name/ })).toHaveValue(name);
  });

  // BUG B3: Gender field disabled on pre-loaded forms
  test('TC-PAT-04: [BUG-B3] Gender dropdown should be editable when opening existing patient', async ({ page }) => {
    // Assumes Rajesh Kumar exists
    await page.getByRole('combobox', { name: /Search patients by name/ }).fill('Rajesh');
    await page.getByRole('option', { name: /Rajesh Kumar/ }).first().click();
    const genderSelect = page.getByRole('combobox').filter({ hasText: /Male|Female|Other/ });
    await expect(genderSelect).toBeEnabled(); // Currently FAILS — Gender is disabled (BUG)
  });

  test('TC-PAT-05: Title dropdown auto-sets gender correctly', async ({ page }) => {
    await page.getByRole('button', { name: 'New Patient' }).click();
    await page.getByRole('combobox').nth(1).selectOption('Mrs');
    const genderSelect = page.getByRole('combobox').nth(2);
    await expect(genderSelect).toHaveValue('Female');
  });

  test('TC-PAT-06: Age unit dropdown has Years, Months, Days', async ({ page }) => {
    await page.getByRole('button', { name: 'New Patient' }).click();
    const ageUnit = page.getByRole('combobox').nth(3);
    await expect(ageUnit.locator('option')).toHaveCount(3);
  });

  test('TC-PAT-07: Blood group dropdown has all 8 types + Select', async ({ page }) => {
    await page.getByRole('button', { name: 'New Patient' }).click();
    const bg = page.getByRole('combobox').nth(4);
    await expect(bg.locator('option')).toHaveCount(9); // Select + 8 groups
  });

  test('TC-PAT-08: Cancel button clears form', async ({ page }) => {
    await page.getByRole('button', { name: 'New Patient' }).click();
    await page.getByRole('textbox', { name: 'Patient full name' }).fill('Cancel Test');
    await page.getByRole('button', { name: 'Cancel' }).first().click();
    // The New Patient button should reappear
    await expect(page.getByRole('button', { name: 'New Patient' })).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 4: Doctor Master
// ─────────────────────────────────────────────────────────────
test.describe('Suite 04 — Doctor Master', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/doctors`);
  });

  test('TC-DOC-01: Doctors page renders correctly', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Doctors' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Doctor' })).toBeVisible();
  });

  test('TC-DOC-02: Create doctor with all required fields', async ({ page }) => {
    await page.getByRole('button', { name: 'New Doctor' }).click();
    const ts = Date.now();
    await page.getByRole('textbox', { name: 'Doctor name' }).fill(`Dr E2E Test ${ts}`);
    await page.getByRole('combobox').nth(2).selectOption('Internal');
    await page.getByRole('textbox', { name: 'e.g. MBBS, MD' }).fill('MBBS');
    await page.getByRole('textbox', { name: 'e.g. Cardiology' }).fill('General Medicine');
    await page.getByRole('textbox', { name: 'Mobile' }).fill('9800000001');
    await page.getByRole('spinbutton').first().fill('300');
    await page.getByRole('spinbutton').nth(1).fill('5');
    await page.getByRole('button', { name: 'Save' }).click();
    // Should see doctor in search
    await expect(page.getByRole('combobox', { name: /Search doctors/ })).toHaveValue(new RegExp(`Dr E2E Test ${ts}`));
  });

  test('TC-DOC-03: Doctor auto-code is generated in format ANI001', async ({ page }) => {
    // Verify ANI001 exists from initial test
    await page.getByRole('combobox', { name: /Search doctors/ }).fill('Anil');
    await expect(page.getByRole('option', { name: /ANI001/ })).toBeVisible();
  });

  test('TC-DOC-04: Signature image upload UI renders', async ({ page }) => {
    await page.getByRole('button', { name: 'New Doctor' }).click();
    await expect(page.getByRole('button', { name: 'Choose File' })).toBeVisible();
    await expect(page.getByText('JPG, PNG, BMP or GIF')).toBeVisible();
  });

  test('TC-DOC-05: Doctor type options are Referral, Internal, Both', async ({ page }) => {
    await page.getByRole('button', { name: 'New Doctor' }).click();
    const typeSelect = page.getByRole('combobox').nth(2);
    await expect(typeSelect.locator('option[value="Referral"]')).toHaveCount(1);
    await expect(typeSelect.locator('option[value="Internal"]')).toHaveCount(1);
    await expect(typeSelect.locator('option[value="Both"]')).toHaveCount(1);
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 5: Account Master
// ─────────────────────────────────────────────────────────────
test.describe('Suite 05 — Account Master', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/accounts`);
  });

  test('TC-ACC-01: Accounts page shows type filter buttons', async ({ page }) => {
    await expect(page.getByText('Customers')).toBeVisible();
    await expect(page.getByText('Suppliers')).toBeVisible();
    await expect(page.getByText('Banks')).toBeVisible();
    await expect(page.getByText('Cash')).toBeVisible();
  });

  test('TC-ACC-02: MediSupply Pvt Ltd supplier exists (created during gap-fix)', async ({ page }) => {
    await page.getByRole('textbox', { name: /Search by name/ }).fill('MediSupply');
    await expect(page.getByText('MediSupply Pvt Ltd')).toBeVisible();
    await expect(page.getByText('SUPP0001')).toBeVisible();
  });

  test('TC-ACC-03: Create a new supplier account with all fields', async ({ page }) => {
    await page.getByRole('button', { name: 'Add Account' }).click();
    await page.getByRole('button', { name: 'Suppliers', exact: true }).click();
    const ts = Date.now();
    const name = `E2E Supplier ${ts}`;
    await page.getByRole('textbox', { name: 'e.g., MediSupply Co.' }).fill(name);
    await page.getByRole('textbox', { name: 'Mobile number' }).fill('9800000002');
    await page.getByRole('textbox', { name: 'City' }).fill('Delhi');
    await page.getByRole('combobox').selectOption('Current Liabilities');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await expect(page.getByText(name)).toBeVisible();
  });

  test('TC-ACC-04: Account types Customer, Supplier, Bank, Cash are all selectable', async ({ page }) => {
    await page.getByRole('button', { name: 'Add Account' }).click();
    await expect(page.getByRole('button', { name: 'Customers' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Suppliers', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Banks' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cash' })).toBeVisible();
  });

  test('TC-ACC-05: Account group dropdown has all ledger groups', async ({ page }) => {
    await page.getByRole('button', { name: 'Add Account' }).click();
    const grp = page.getByRole('combobox');
    const opts = await grp.locator('option').allTextContents();
    expect(opts).toContain('Current Assets');
    expect(opts).toContain('Current Liabilities');
    expect(opts).toContain('Laboratory Income');
    expect(opts).toContain('Laboratory Expenses');
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 6: Patient Entry (Lab Registration)
// ─────────────────────────────────────────────────────────────
test.describe('Suite 06 — Patient Entry', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/lab-entries`);
  });

  test('TC-ENTRY-01: Lab entries page renders with New Entry button', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Patient Entry' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Entry' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Export' })).toBeVisible();
  });

  test('TC-ENTRY-02: New Entry form has all required fields', async ({ page }) => {
    await expect(page.getByRole('combobox', { name: /Search patient by name/ })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /Search doctor by name/ })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /Search company/ })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /Search test by name/ })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /Search health packages/ })).toBeVisible();
    await expect(page.getByRole('spinbutton')).toBeVisible(); // Overall Discount %
  });

  test('TC-ENTRY-03: Patient search returns correct results', async ({ page }) => {
    const patientSearch = page.getByRole('combobox', { name: /Search patient by name/ });
    await patientSearch.fill('Rajesh');
    await expect(page.getByRole('option', { name: /Rajesh Kumar/ })).toBeVisible();
  });

  test('TC-ENTRY-04: Doctor search returns correct results', async ({ page }) => {
    const doctorSearch = page.getByRole('combobox', { name: /Search doctor by name/ });
    await doctorSearch.fill('Anil');
    await expect(page.getByRole('option', { name: /Anil Sharma/ })).toBeVisible();
  });

  test('TC-ENTRY-05: Test search finds existing tests', async ({ page }) => {
    const testSearch = page.getByRole('combobox', { name: /Search test by name, code/ });
    await testSearch.fill('Hemoglobin');
    await expect(page.getByRole('option', { name: /Hemoglobin/ })).toBeVisible();
  });

  test('TC-ENTRY-06: Create complete lab entry with patient, doctor, tests', async ({ page }) => {
    // Select patient
    await page.getByRole('combobox', { name: /Search patient by name/ }).fill('Rajesh');
    await page.getByRole('option', { name: /Rajesh Kumar/ }).first().click();
    // Select doctor
    await page.getByRole('combobox', { name: /Search doctor by name/ }).fill('Anil');
    await page.getByRole('option', { name: /Anil Sharma/ }).first().click();
    // Select company
    await page.getByRole('button', { name: 'Show all items' }).nth(2).click();
    await page.getByRole('option', { name: /General Patient/ }).click();
    // Add test
    await page.getByRole('combobox', { name: /Search test by name/ }).fill('Hemoglobin');
    await page.getByRole('option', { name: /Hemoglobin/ }).first().click();
    // Save
    await page.getByRole('button', { name: 'Save' }).last().click();
    // Verify voucher created
    await expect(page.getByText(/PE26G/)).toBeVisible();
  });

  test('TC-ENTRY-07: Gross, Net, Balance amounts are auto-calculated', async ({ page }) => {
    // After adding tests, verify auto-calculation fields appear
    await page.getByRole('combobox', { name: /Search patient by name/ }).fill('Rajesh');
    await page.getByRole('option', { name: /Rajesh Kumar/ }).first().click();
    await page.getByRole('button', { name: 'Show all items' }).nth(2).click();
    await page.getByRole('option', { name: /General Patient/ }).click();
    await page.getByRole('combobox', { name: /Search test by name/ }).fill('Hemoglobin');
    await page.getByRole('option', { name: /Hemoglobin/ }).first().click();
    await page.getByRole('button', { name: 'Save' }).last().click();
    await expect(page.getByText('Gross Amount')).toBeVisible();
    await expect(page.getByText('Net Amount')).toBeVisible();
    await expect(page.getByText('Balance')).toBeVisible();
  });

  test('TC-ENTRY-08: Export button is visible on entries list', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Export' })).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 7: Sample Collection
// ─────────────────────────────────────────────────────────────
test.describe('Suite 07 — Sample Collection', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/samples`);
  });

  test('TC-SAMP-01: Sample collection page renders all status tabs', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Pending/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Collected/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /In Testing/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Completed/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Rejected/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /STAT/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Expired/ })).toBeVisible();
  });

  test('TC-SAMP-02: Pending samples are listed when clicking Pending tab', async ({ page }) => {
    await page.getByRole('button', { name: /Pending/ }).click();
    // At least one group should be visible
    await expect(page.locator('[role="button"]').filter({ hasText: /PE26G/ })).toBeVisible();
  });

  test('TC-SAMP-03: Batch Collect wizard has patient verification steps', async ({ page }) => {
    await page.getByRole('button', { name: /Pending/ }).click();
    // Click Batch Collect on any entry
    const batchBtn = page.getByRole('button', { name: 'Batch Collect' }).first();
    await batchBtn.click();
    await expect(page.getByText('Step 1: Auto-Verify Patient Identifiers')).toBeVisible();
    await expect(page.getByText('Step 2: Manual Verification')).toBeVisible();
  });

  test('TC-SAMP-04: Batch Collect button is disabled until all verification steps done', async ({ page }) => {
    await page.getByRole('button', { name: /Pending/ }).click();
    const batchBtn = page.getByRole('button', { name: 'Batch Collect' }).first();
    await batchBtn.click();
    const collectBtn = page.getByRole('button', { name: /Collect \d+ Sample/ });
    await expect(collectBtn).toBeDisabled();
  });

  test('TC-SAMP-05: CLSI draw order is shown in batch collect wizard', async ({ page }) => {
    await page.getByRole('button', { name: /Pending/ }).click();
    const batchBtn = page.getByRole('button', { name: 'Batch Collect' }).first();
    await batchBtn.click();
    await expect(page.getByText('CLSI Draw Order')).toBeVisible();
  });

  test('TC-SAMP-06: Board view is accessible', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Board' })).toBeVisible();
    await page.getByRole('button', { name: 'Board' }).click();
  });

  test('TC-SAMP-07: Stock button is accessible', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Stock' })).toBeVisible();
  });

  test('TC-SAMP-08: Search by entry ID works', async ({ page }) => {
    await page.getByRole('textbox', { name: 'Search by Entry ID or Barcode' }).fill('PE26G300001');
    await page.getByRole('button', { name: 'Search' }).click();
    await expect(page.getByText(/PE26G300001/)).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 8: Readings
// ─────────────────────────────────────────────────────────────
test.describe('Suite 08 — Readings', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('TC-READ-01: Readings page renders from direct URL', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings`);
    await expect(page.getByRole('heading', { name: 'Readings' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Reading' })).toBeVisible();
  });

  test('TC-READ-02: Readings page loads correctly with entry pre-selected', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    await expect(page.getByText('PE26G300001')).toBeVisible();
    await expect(page.getByText(/2 tests/)).toBeVisible();
  });

  test('TC-READ-03: Tests are grouped by department', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    await expect(page.getByRole('heading', { name: 'Pathology' })).toBeVisible();
  });

  test('TC-READ-04: Normal range is displayed for each reading test', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    await expect(page.getByText(/Normal: 13\.0/)).toBeVisible();
  });

  test('TC-READ-05: Result entry field accepts numeric values', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    const resultField = page.getByRole('textbox', { name: 'Enter result...' }).first();
    await resultField.fill('15.2');
    await expect(resultField).toHaveValue('15.2');
  });

  test('TC-READ-06: AI Suggestion button is present', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    await expect(page.getByRole('button', { name: 'Get AI Suggestion' })).toBeVisible();
  });

  test('TC-READ-07: Overall Remarks field is present and editable', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    const remarks = page.getByRole('textbox', { name: /Type your remarks/ });
    await expect(remarks).toBeVisible();
    await remarks.fill('Test remark');
    await expect(remarks).toHaveValue('Test remark');
  });

  test('TC-READ-08: Save Department button is present per department section', async ({ page }) => {
    await page.goto(`${BASE_URL}/readings?entryVrNo=PE26G300001`);
    await expect(page.getByRole('button', { name: 'Save Department' })).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 9: Receipt Entry
// ─────────────────────────────────────────────────────────────
test.describe('Suite 09 — Receipt Entry', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/receipt-entry`);
  });

  test('TC-REC-01: Receipt entry page renders correctly', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'New Receipt Entry' })).toBeVisible();
    await expect(page.getByRole('combobox', { name: /Search patient entry/ })).toBeVisible();
  });

  test('TC-REC-02: All payment mode options are available', async ({ page }) => {
    const typeSelect = page.getByRole('combobox').nth(1);
    const options = await typeSelect.locator('option').allTextContents();
    expect(options).toContain('Cash');
    expect(options).toContain('Cheque');
    expect(options).toContain('UPI');
    expect(options).toContain('Card');
    expect(options).toContain('RTGS');
    expect(options).toContain('NEFT');
  });

  test('TC-REC-03: Linking lab entry auto-fills party and amount', async ({ page }) => {
    const refSearch = page.getByRole('combobox', { name: /Search patient entry/ });
    await refSearch.fill('PE26G300001');
    await page.getByRole('option', { name: /PE26G300001.*Rajesh Kumar/ }).click();
    // Amount should be auto-populated (₹160)
    const amountField = page.getByRole('spinbutton');
    await expect(amountField).toHaveValue('160');
  });

  test('TC-REC-04: Outstanding vouchers section shows balance', async ({ page }) => {
    const refSearch = page.getByRole('combobox', { name: /Search patient entry/ });
    await refSearch.fill('PE26G300001');
    await page.getByRole('option', { name: /PE26G300001/ }).click();
    await expect(page.getByRole('heading', { name: 'Outstanding Vouchers' })).toBeVisible();
    await expect(page.getByText(/₹160\.00/)).toBeVisible();
  });

  test('TC-REC-05: RC26G300001 receipt exists in search results', async ({ page }) => {
    await page.getByRole('button', { name: 'Show all items' }).first().click();
    await expect(page.getByRole('option', { name: /RC26G300001/ })).toBeVisible();
  });

  test('TC-REC-06: Both bank and cash accounts are selectable', async ({ page }) => {
    const accountSelect = page.getByRole('combobox').nth(2);
    const options = await accountSelect.locator('option').allTextContents();
    expect(options.some(o => o.includes('BANK01'))).toBeTruthy();
    expect(options.some(o => o.includes('CASH01'))).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 10: Payment Entry
// ─────────────────────────────────────────────────────────────
test.describe('Suite 10 — Payment Entry', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/payment-entry`);
  });

  test('TC-PAY-01: Payment entry page renders correctly', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'New Payment Entry' })).toBeVisible();
  });

  test('TC-PAY-02: MediSupply Pvt Ltd appears in supplier search', async ({ page }) => {
    await page.getByRole('combobox', { name: /Search supplier/ }).fill('Medi');
    await expect(page.getByRole('option', { name: /MediSupply Pvt Ltd/ })).toBeVisible();
  });

  test('TC-PAY-03: PY26G300001 payment exists in search results', async ({ page }) => {
    await page.getByRole('button', { name: 'Show all items' }).first().click();
    await expect(page.getByRole('option', { name: /PY26G300001/ })).toBeVisible();
  });

  test('TC-PAY-04: Create new payment to supplier', async ({ page }) => {
    await page.getByRole('combobox', { name: /Search supplier/ }).fill('Medi');
    await page.getByRole('option', { name: /MediSupply Pvt Ltd/ }).click();
    await page.getByRole('textbox', { name: 'Description' }).fill('E2E Test Payment');
    await page.getByRole('spinbutton').fill('100');
    await page.getByRole('button', { name: 'Save' }).click();
    await page.getByRole('button', { name: 'Show all items' }).first().click();
    const options = await page.getByRole('listbox').textContent();
    expect(options).toContain('E2E Test Payment');
  });

  test('TC-PAY-05: All payment modes are available', async ({ page }) => {
    const typeSelect = page.getByRole('combobox').first();
    const options = await typeSelect.locator('option').allTextContents();
    expect(options).toContain('Cash');
    expect(options).toContain('UPI');
    expect(options).toContain('NEFT');
    expect(options).toContain('RTGS');
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 11: Journal Entry
// ─────────────────────────────────────────────────────────────
test.describe('Suite 11 — Journal Entry', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/journal-entry`);
  });

  test('TC-JNL-01: Journal entry page renders with 2 default lines', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'New Journal Entry' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add Line' })).toBeVisible();
    const rows = await page.getByRole('row').count();
    expect(rows).toBeGreaterThanOrEqual(3); // Header + 2 data rows
  });

  test('TC-JNL-02: JR26G300001 journal entry exists', async ({ page }) => {
    await page.getByRole('button', { name: 'Show all items' }).first().click();
    await expect(page.getByRole('option', { name: /JR26G300001/ })).toBeVisible();
  });

  test('TC-JNL-03: Debit/Credit balance validation works', async ({ page }) => {
    // Select accounts and enter amounts
    await page.getByRole('button', { name: 'Show all items' }).nth(1).click();
    await page.getByRole('option', { name: /CASH01/ }).click();
    await page.getByRole('spinbutton').first().fill('500');
    await page.getByRole('button', { name: 'Show all items' }).nth(2).click();
    await page.getByRole('option', { name: /BANK01/ }).click();
    await page.getByRole('spinbutton').nth(3).fill('500');
    // Check balance indicator shows ✓
    await expect(page.getByText('✓')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save Journal Entry' })).toBeEnabled();
  });

  test('TC-JNL-04: Swap Debit/Credit button works on each line', async ({ page }) => {
    const swapBtn = page.getByRole('button', { name: 'Swap Debit ↔ Credit' }).first();
    await expect(swapBtn).toBeVisible();
    await swapBtn.click();
  });

  test('TC-JNL-05: Add Line button inserts new journal line', async ({ page }) => {
    const before = await page.getByRole('row').count();
    await page.getByRole('button', { name: 'Add Line' }).click();
    const after = await page.getByRole('row').count();
    expect(after).toBe(before + 1);
  });

  // BUG B8: Journal saves as Draft with no Post button
  test('TC-JNL-06: [BUG-B8] Journal entry should have a Post/Approve button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Post|Approve|Finalize/ })).toBeVisible(); // FAILS — BUG
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 12: Inventory
// ─────────────────────────────────────────────────────────────
test.describe('Suite 12 — Inventory', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/inventory`);
  });

  test('TC-INV-01: Inventory page has Overview, Items, Purchases, Usage, Stock tabs', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Overview' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Items' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Purchases' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Usage' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Stock' })).toBeVisible();
  });

  test('TC-INV-02: EDTA Tubes 5ml item exists with stock 10', async ({ page }) => {
    await page.getByRole('button', { name: 'Items' }).click();
    await expect(page.getByText('EDTA Tubes 5ml')).toBeVisible();
    await expect(page.getByText('10 Box')).toBeVisible();
    await expect(page.getByText('OK')).toBeVisible();
  });

  test('TC-INV-03: Purchase PUR-20260730-001 exists in purchases list', async ({ page }) => {
    await page.getByRole('button', { name: 'Purchases' }).click();
    await expect(page.getByText('PUR-20260730-001')).toBeVisible();
    await expect(page.getByText('MediSupply Pvt Ltd')).toBeVisible();
    await expect(page.getByText('₹4,500')).toBeVisible();
  });

  test('TC-INV-04: Add new inventory item with all fields', async ({ page }) => {
    await page.getByRole('button', { name: 'Items' }).click();
    await page.getByRole('button', { name: 'Add Item' }).click();
    const ts = Date.now();
    await page.getByRole('textbox', { name: /e.g., Cotton Rolls/ }).fill(`Test Item ${ts}`);
    await page.locator('textarea').fill('Test description');
    await page.getByRole('combobox').nth(1).selectOption('Reagents');
    await page.getByRole('combobox').nth(2).selectOption('Bottle');
    await page.getByRole('spinbutton').first().fill('200');
    await page.getByRole('button', { name: 'Create' }).click();
    await expect(page.getByText(`Test Item ${ts}`)).toBeVisible();
  });

  test('TC-INV-05: New purchase with MediSupply supplier can be created', async ({ page }) => {
    await page.getByRole('button', { name: 'Purchases' }).click();
    await page.getByRole('button', { name: 'New Purchase' }).click();
    await page.getByRole('combobox').first().selectOption('MediSupply Pvt Ltd');
    await expect(page.getByRole('combobox').first()).toHaveValue('MediSupply Pvt Ltd');
  });

  test('TC-INV-06: Item categories include all 6 options', async ({ page }) => {
    await page.getByRole('button', { name: 'Items' }).click();
    await page.getByRole('button', { name: 'Add Item' }).click();
    const catSelect = page.getByRole('combobox').nth(1);
    const opts = await catSelect.locator('option').allTextContents();
    expect(opts).toContain('Consumables');
    expect(opts).toContain('Reagents');
    expect(opts).toContain('Containers');
    expect(opts).toContain('General');
    expect(opts).toContain('Chemicals');
    expect(opts).toContain('Other');
  });

  test('TC-INV-07: Minimum stock alert is enforced with visual OK/WARNING status', async ({ page }) => {
    await page.getByRole('button', { name: 'Items' }).click();
    await expect(page.getByText('OK')).toBeVisible(); // Stock 10 > Min 5 = OK
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 13: Tests Master
// ─────────────────────────────────────────────────────────────
test.describe('Suite 13 — Tests Master', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/tests`);
  });

  test('TC-TEST-01: Tests page renders with 4 test type buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Reading/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Formula/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Formatted/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Group/ })).toBeVisible();
  });

  test('TC-TEST-02: Reading test form has reference range fields', async ({ page }) => {
    await expect(page.getByRole('textbox', { name: 'e.g. 13.0' })).toBeVisible(); // Male Min
    await expect(page.getByRole('textbox', { name: 'e.g. 17.0' })).toBeVisible(); // Male Max
    await expect(page.getByRole('textbox', { name: 'e.g. 12.0' })).toBeVisible(); // Female Min
    await expect(page.getByRole('textbox', { name: 'e.g. 15.0' })).toBeVisible(); // Female Max
    await expect(page.getByRole('textbox', { name: 'Panic low value' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Panic high value' })).toBeVisible();
  });

  test('TC-TEST-03: Duplicate test name is rejected with error', async ({ page }) => {
    // Hemoglobin already exists
    await page.getByRole('button', { name: 'New Test' }).click();
    await page.getByRole('textbox', { name: 'e.g. Hemoglobin' }).fill('Hemoglobin');
    await page.getByRole('combobox').nth(1).selectOption('Pathology (DEPT001)');
    await page.getByRole('textbox', { name: 'e.g. g/dL, mg/dL' }).fill('g/dL');
    await page.getByRole('button', { name: 'Save' }).nth(1).click();
    await expect(page.getByText(/already exists/)).toBeVisible();
  });

  test('TC-TEST-04: Department dropdown has all 8 departments', async ({ page }) => {
    const deptSelect = page.getByRole('combobox').nth(1);
    const opts = await deptSelect.locator('option').allTextContents();
    expect(opts.some(o => o.includes('Pathology'))).toBeTruthy();
    expect(opts.some(o => o.includes('Radiology'))).toBeTruthy();
    expect(opts.some(o => o.includes('Microbiology'))).toBeTruthy();
    expect(opts.some(o => o.includes('Blood Bank'))).toBeTruthy();
    expect(opts.some(o => o.includes('Cardiology'))).toBeTruthy();
  });

  test('TC-TEST-05: Specimen type dropdown has all specimen options', async ({ page }) => {
    const specimenSelect = page.getByRole('combobox').nth(4);
    const opts = await specimenSelect.locator('option').allTextContents();
    expect(opts).toContain('Blood');
    expect(opts).toContain('Urine');
    expect(opts).toContain('Serum');
    expect(opts).toContain('Plasma');
    expect(opts).toContain('Stool');
  });

  test('TC-TEST-06: Sample collection section has fasting/light/mixing checkboxes', async ({ page }) => {
    await expect(page.getByRole('checkbox', { name: 'Requires Fasting' })).toBeVisible();
    await expect(page.getByRole('checkbox', { name: 'Protect from Light' })).toBeVisible();
    await expect(page.getByRole('checkbox', { name: 'Requires Mixing/Inversion' })).toBeVisible();
  });

  test('TC-TEST-07: Print on New Page and Add to Quick List checkboxes are present', async ({ page }) => {
    await expect(page.getByRole('checkbox', { name: 'Print on New Page' })).toBeVisible();
    await expect(page.getByRole('checkbox', { name: 'Add to Quick List' })).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 14: General Master
// ─────────────────────────────────────────────────────────────
test.describe('Suite 14 — General Master', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/general-master`);
  });

  test('TC-GM-01: General Master shows stats: 8 Depts, 32 Categories, 83 Sub-Categories', async ({ page }) => {
    await expect(page.getByText('8')).toBeVisible();
    await expect(page.getByText('Departments')).toBeVisible();
    await expect(page.getByText('32')).toBeVisible();
    await expect(page.getByText('Categories')).toBeVisible();
    await expect(page.getByText('83')).toBeVisible();
    await expect(page.getByText('Sub-Categories')).toBeVisible();
  });

  test('TC-GM-02: All 8 departments are listed', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Pathology' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Radiology' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Microbiology' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Blood Bank' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Cardiology' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Pulmonology' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Neurology' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Endoscopy' })).toBeVisible();
  });

  test('TC-GM-03: Deactivate/Activate toggle is present for each department', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Deactivate Pathology' })).toBeVisible();
  });

  test('TC-GM-04: Departments, Categories, Sub-Categories tabs switch correctly', async ({ page }) => {
    await page.getByRole('button', { name: /Categories/ }).first().click();
    await expect(page.getByText(/Hematology|Biochemistry|Serology/)).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 15: System Modules
// ─────────────────────────────────────────────────────────────
test.describe('Suite 15 — System Modules', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('TC-SYS-01: Report Templates page renders with New Template button', async ({ page }) => {
    await page.goto(`${BASE_URL}/report-templates`);
    await expect(page.getByRole('heading', { name: 'Report Templates' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Template' })).toBeVisible();
  });

  test('TC-SYS-02: Analyzers page renders with New Analyzer and Pending Results buttons', async ({ page }) => {
    await page.goto(`${BASE_URL}/analyzers`);
    await expect(page.getByRole('heading', { name: 'Analyzers / Machines' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Analyzer' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Pending Results' })).toBeVisible();
  });

  test('TC-SYS-03: Admin Panel shows user management with adminuser listed', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin`);
    await expect(page.getByText('adminuser')).toBeVisible();
    await expect(page.getByText('Admin User')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Add User' })).toBeVisible();
  });

  test('TC-SYS-04: Admin Panel has User Management, Active Sessions, Lab Settings tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin`);
    await expect(page.getByRole('button', { name: 'User Management' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Active Sessions' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Lab Settings' })).toBeVisible();
  });

  test('TC-SYS-05: Menu Rights page shows 4 built-in roles', async ({ page }) => {
    await page.goto(`${BASE_URL}/permissions`);
    await expect(page.getByRole('button', { name: /Admin.*Full access/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Standard.*Create, edit/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /Limited.*View only/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /User.*View and print/ })).toBeVisible();
  });

  test('TC-SYS-06: Menu Rights shows all 7 Main menu permission rows', async ({ page }) => {
    await page.goto(`${BASE_URL}/permissions`);
    await expect(page.getByText('Patient Entry')).toBeVisible();
    await expect(page.getByText('Sample Collections')).toBeVisible();
    await expect(page.getByText('Readings')).toBeVisible();
    await expect(page.getByText('Receipt Entry')).toBeVisible();
    await expect(page.getByText('Payment Entry')).toBeVisible();
    await expect(page.getByText('Journal Entry')).toBeVisible();
    await expect(page.getByText('Inventory')).toBeVisible();
  });

  test('TC-SYS-07: Each module has View, Create, Edit, Delete, Print, Export permissions', async ({ page }) => {
    await page.goto(`${BASE_URL}/permissions`);
    // Check first module row has all permission buttons
    const firstModuleRow = page.locator('generic').filter({ hasText: 'Patient Entry' }).first();
    await expect(firstModuleRow.getByRole('button', { name: 'View' })).toBeVisible();
    await expect(firstModuleRow.getByRole('button', { name: 'Create' })).toBeVisible();
    await expect(firstModuleRow.getByRole('button', { name: 'Delete' })).toBeVisible();
    await expect(firstModuleRow.getByRole('button', { name: 'Print' })).toBeVisible();
  });

  test('TC-SYS-08: Settings page has Profile, Password, My Modules, Notifications tabs', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await expect(page.getByRole('button', { name: 'Profile' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Password' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'My Modules' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Notifications' })).toBeVisible();
  });

  test('TC-SYS-09: Settings Profile tab shows user info', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    await expect(page.getByText('Admin User')).toBeVisible();
    await expect(page.getByText('Administrator')).toBeVisible();
    await expect(page.getByText('Demo Lab')).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 16: Rates & Packages Masters
// ─────────────────────────────────────────────────────────────
test.describe('Suite 16 — Rates & Packages', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('TC-RATE-01: Rates page shows 159 tests without rates', async ({ page }) => {
    await page.goto(`${BASE_URL}/rates`);
    await expect(page.getByText('159 tests without rates')).toBeVisible();
  });

  test('TC-RATE-02: Rates page has Add Rate, Copy Rates, Bulk Update buttons', async ({ page }) => {
    await page.goto(`${BASE_URL}/rates`);
    await expect(page.getByRole('button', { name: 'Add Rate' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Copy Rates' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Bulk Update' })).toBeVisible();
  });

  test('TC-PKG-01: Packages page renders', async ({ page }) => {
    await page.goto(`${BASE_URL}/packages`);
    await expect(page).toHaveURL(`${BASE_URL}/packages`);
  });

  test('TC-APT-01: Appointments page shows stats and table', async ({ page }) => {
    await page.goto(`${BASE_URL}/appointments`);
    await expect(page.getByRole('heading', { name: 'Appointments' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Patient' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Doctor' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();
  });
});

// ─────────────────────────────────────────────────────────────
// SUITE 17: Bug Regression Tests
// ─────────────────────────────────────────────────────────────
test.describe('Suite 17 — Bug Regression', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  // BUG B1: Dashboard 403
  test('TC-BUG-B1: Dashboard /api/dashboard returns 200', async ({ page }) => {
    const responses: number[] = [];
    page.on('response', resp => {
      if (resp.url().includes('/api/dashboard')) responses.push(resp.status());
    });
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);
    expect(responses).not.toContain(403);
    expect(responses).toContain(200);
  });

  // BUG B2: auth/me 401
  test('TC-BUG-B2: /api/auth/me returns 200 after login', async ({ page }) => {
    const responses: number[] = [];
    page.on('response', resp => {
      if (resp.url().includes('/api/auth/me')) responses.push(resp.status());
    });
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);
    expect(responses).not.toContain(401);
    expect(responses).toContain(200);
  });

  // BUG B3: Gender field disabled
  test('TC-BUG-B3: Gender field should be editable on pre-loaded patient form', async ({ page }) => {
    await page.goto(`${BASE_URL}/patients`);
    await page.getByRole('combobox', { name: /Search patients by name/ }).fill('Rajesh');
    await page.getByRole('option', { name: /Rajesh Kumar/ }).first().click();
    const genderSelect = page.locator('select').filter({ hasText: /Male|Female|Other/ });
    await expect(genderSelect).toBeEnabled();
  });

  // BUG B6: Global search non-functional
  test('TC-BUG-B6: Global search bar navigates or shows results', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await page.getByRole('textbox', { name: 'Search patients, tests, entries...' }).fill('Rajesh');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1000);
    const url = page.url();
    const hasResults = await page.getByText(/Rajesh Kumar/).count() > 0;
    expect(url.includes('search') || hasResults).toBeTruthy();
  });

  // BUG B7: CSP blocking beacon.min.js
  test('TC-BUG-B7: Cloudflare beacon script should not be blocked by CSP', async ({ page }) => {
    const cspViolations: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('cloudflareinsights')) {
        cspViolations.push(msg.text());
      }
    });
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForTimeout(2000);
    expect(cspViolations).toHaveLength(0);
  });

  // BUG B8: Journal Draft mode — no Post button
  test('TC-BUG-B8: Journal entry has Post/Approve button to finalize from Draft', async ({ page }) => {
    await page.goto(`${BASE_URL}/journal-entry`);
    await page.getByRole('button', { name: 'Show all items' }).first().click();
    await page.getByRole('option', { name: /JR26G300001/ }).click();
    await expect(page.getByRole('button', { name: /Post|Approve|Finalize/ })).toBeVisible();
  });
});
