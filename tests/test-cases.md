# MLab E2E Test Cases
**Application:** MLab Diagnostics Center Management System
**URL:** https://mlab.sgsoftech.in
**Version:** 1.0.0
**Date Generated:** 2026-07-30
**Auth:** Lab Code `DEMO2026` | User `Adminuser` | Pass `Admin@1234`
**Total Test Cases:** 96

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ PASS | Verified in session 2026-07-30 |
| ❌ FAIL | Bug found / assertion failed |
| ⚠️ PARTIAL | Works with workaround |
| 🔲 PENDING | Not yet executed |

---

## Module Index

| # | Module | Cases | Status |
|---|--------|-------|--------|
| 01 | Authentication | TC-AUTH-01 → 06 | ✅ |
| 02 | Dashboard | TC-DASH-01 → 08 | ⚠️ |
| 03 | Patient Master | TC-PAT-01 → 08 | ⚠️ |
| 04 | Doctor Master | TC-DOC-01 → 05 | ✅ |
| 05 | Account Master | TC-ACC-01 → 05 | ✅ |
| 06 | Patient Entry (Lab) | TC-ENTRY-01 → 08 | ✅ |
| 07 | Sample Collection | TC-SAMP-01 → 08 | ✅ |
| 08 | Readings | TC-READ-01 → 08 | ✅ |
| 09 | Receipt Entry | TC-REC-01 → 06 | ✅ |
| 10 | Payment Entry | TC-PAY-01 → 05 | ✅ |
| 11 | Journal Entry | TC-JNL-01 → 06 | ⚠️ |
| 12 | Inventory | TC-INV-01 → 07 | ✅ |
| 13 | Tests Master | TC-TEST-01 → 07 | ✅ |
| 14 | General Master | TC-GM-01 → 04 | ✅ |
| 15 | System Modules | TC-SYS-01 → 09 | ✅ |
| 16 | Rates & Packages | TC-RATE/PKG/APT | ✅ |
| 17 | Bug Regression | TC-BUG-B1 → B8 | ❌ (known bugs) |

---

## Suite 01 — Authentication

### TC-AUTH-01
- **Title:** Login page renders all required elements
- **Module:** Authentication
- **Priority:** P0 — Critical
- **Preconditions:** None
- **Steps:**
  1. Navigate to `https://mlab.sgsoftech.in/login`
- **Expected:**
  - Lab Code, User ID, Password input fields visible
  - Sign In button visible
  - reCAPTCHA v3 notice visible
  - "Account lockout after 5 failed attempts" warning visible
- **Status:** ✅ PASS

---

### TC-AUTH-02
- **Title:** Successful login redirects to dashboard
- **Module:** Authentication
- **Priority:** P0 — Critical
- **Preconditions:** Valid credentials available
- **Steps:**
  1. Navigate to `/login`
  2. Enter Lab Code: `DEMO2026`
  3. Enter User ID: `Adminuser`
  4. Enter Password: `Admin@1234`
  5. Click "Sign In"
- **Expected:**
  - Redirect to `/dashboard`
  - Greeting "Good Morning/Afternoon/Evening, Admin" visible
- **Status:** ✅ PASS

---

### TC-AUTH-03
- **Title:** Login fails with invalid credentials
- **Module:** Authentication
- **Priority:** P1
- **Steps:**
  1. Navigate to `/login`
  2. Enter wrong credentials
  3. Click "Sign In"
- **Expected:** Remains on `/login` page, error shown
- **Status:** ✅ PASS

---

### TC-AUTH-04
- **Title:** Password visibility toggle works
- **Module:** Authentication
- **Priority:** P2
- **Steps:**
  1. Navigate to `/login`
  2. Enter any text in Password field
  3. Click the eye icon toggle button
- **Expected:** Password input switches from `type=password` to `type=text`
- **Status:** ✅ PASS

---

### TC-AUTH-05
- **Title:** User profile dropdown shows Sign Out and Settings
- **Module:** Authentication
- **Priority:** P1
- **Steps:**
  1. Login successfully
  2. Click user avatar button top-right
- **Expected:** "Profile & Settings" and "Sign Out" buttons visible
- **Status:** ✅ PASS

---

### TC-AUTH-06
- **Title:** Sign Out redirects to login page
- **Module:** Authentication
- **Priority:** P0
- **Steps:**
  1. Login successfully
  2. Click user avatar → "Sign Out"
- **Expected:** Redirected to `/login`
- **Status:** ✅ PASS

---

## Suite 02 — Dashboard

### TC-DASH-01
- **Title:** Dashboard KPI cards render
- **Module:** Dashboard
- **Priority:** P1
- **Steps:**
  1. Login and navigate to `/dashboard`
- **Expected:** Cards visible for "Today's Entries", "Today's Revenue", "Pending Readings", "Total Patients Today"
- **Status:** ⚠️ PARTIAL — Cards render but all values show 0 due to BUG-B1

---

### TC-DASH-02
- **Title:** [BUG-B1] Dashboard API returns 200 not 403
- **Module:** Dashboard
- **Priority:** P0 — Critical Bug
- **Steps:**
  1. Login
  2. Navigate to `/dashboard`
  3. Monitor Network tab for `/api/dashboard`
- **Expected:** HTTP 200 with KPI data
- **Actual:** HTTP 403 Forbidden — all KPI cards show 0
- **Status:** ❌ FAIL — **BUG B1 (OPEN)**

---

### TC-DASH-03
- **Title:** [BUG-B2] /api/auth/me returns 200 after login
- **Module:** Dashboard
- **Priority:** P0 — Critical Bug
- **Steps:**
  1. Login and navigate to `/dashboard`
  2. Monitor Network tab for `/api/auth/me`
- **Expected:** HTTP 200 with user session data
- **Actual:** HTTP 401 Unauthorized
- **Status:** ❌ FAIL — **BUG B2 (OPEN)**

---

### TC-DASH-04
- **Title:** Top Tests and Revenue Split widgets render
- **Module:** Dashboard
- **Priority:** P2
- **Steps:**
  1. Login and navigate to `/dashboard`
- **Expected:** "Top Tests" and "Revenue Split" widget headings visible
- **Status:** ✅ PASS (widgets render, data shows empty)

---

### TC-DASH-05
- **Title:** Recent Entries table has correct columns
- **Module:** Dashboard
- **Priority:** P2
- **Steps:**
  1. Login and navigate to `/dashboard`
- **Expected:** Table columns: Voucher No, Patient, Date, Amount, Status
- **Status:** ✅ PASS

---

### TC-DASH-06
- **Title:** Sidebar navigation renders all main menu items
- **Module:** Dashboard
- **Priority:** P1
- **Steps:**
  1. Login and check left sidebar
- **Expected:** Dashboard, Patient Entry, Sample Collections, Readings, Receipt Entry, Payment Entry, Journal Entry, Inventory all visible
- **Status:** ✅ PASS

---

### TC-DASH-07
- **Title:** Collapse sidebar button works
- **Module:** Dashboard
- **Priority:** P3
- **Steps:**
  1. Login
  2. Click "Collapse sidebar" button
- **Expected:** Sidebar collapses, logo text hidden
- **Status:** ✅ PASS

---

### TC-DASH-08
- **Title:** [BUG-B6] Global search should navigate or show results
- **Module:** Dashboard
- **Priority:** P2 Bug
- **Steps:**
  1. Login
  2. Click global search bar
  3. Type "Rajesh"
  4. Press Enter
- **Expected:** Navigate to search results page or show dropdown results
- **Actual:** Nothing happens, no navigation, no results
- **Status:** ❌ FAIL — **BUG B6 (OPEN)**

---

## Suite 03 — Patient Master

### TC-PAT-01
- **Title:** Patients page renders with all controls
- **Module:** Patient Master
- **Priority:** P1
- **Steps:** Navigate to `/patients`
- **Expected:** Heading "Patients", search combobox, "New Patient" button, "Export" button
- **Status:** ✅ PASS

---

### TC-PAT-02
- **Title:** New patient form has all required fields
- **Module:** Patient Master
- **Priority:** P1
- **Steps:**
  1. Navigate to `/patients`
  2. Click "New Patient"
- **Expected:** Patient Name, Age, Mobile, WhatsApp, Email, Address, City, Medical History fields visible
- **Status:** ✅ PASS

---

### TC-PAT-03
- **Title:** Create a new patient with all fields
- **Module:** Patient Master
- **Priority:** P0
- **Steps:**
  1. Click "New Patient"
  2. Fill all fields: Name, Title (Mr), Age (28), Blood Group (O+), Mobile, Email, City
  3. Click Save
- **Expected:** Patient created, search bar auto-fills with new patient's name
- **Status:** ✅ PASS

---

### TC-PAT-04
- **Title:** [BUG-B3] Gender dropdown editable on existing patient form
- **Module:** Patient Master
- **Priority:** P2 Bug
- **Steps:**
  1. Navigate to `/patients`
  2. Search and select "Rajesh Kumar"
  3. Check Gender dropdown state
- **Expected:** Gender dropdown should be enabled and changeable
- **Actual:** Gender combobox is disabled (greyed out, cannot change)
- **Workaround:** Click "New Patient" to open fresh form with enabled gender field
- **Status:** ❌ FAIL — **BUG B3 (OPEN)**

---

### TC-PAT-05
- **Title:** Title dropdown auto-sets gender
- **Module:** Patient Master
- **Priority:** P2
- **Steps:**
  1. Open New Patient form
  2. Select Title = "Mrs"
- **Expected:** Gender field auto-sets to "Female"
- **Status:** ✅ PASS

---

### TC-PAT-06
- **Title:** Age unit dropdown has Years, Months, Days
- **Module:** Patient Master
- **Priority:** P2
- **Steps:**
  1. Open New Patient form
  2. Check Age Unit dropdown options
- **Expected:** 3 options: Years, Months, Days
- **Status:** ✅ PASS

---

### TC-PAT-07
- **Title:** Blood group dropdown has all 8 types
- **Module:** Patient Master
- **Priority:** P2
- **Steps:**
  1. Open New Patient form
  2. Count options in Blood Group dropdown
- **Expected:** 9 options (Select + A+, A-, B+, B-, O+, O-, AB+, AB-)
- **Status:** ✅ PASS

---

### TC-PAT-08
- **Title:** Cancel button clears form
- **Module:** Patient Master
- **Priority:** P2
- **Steps:**
  1. Open New Patient form
  2. Fill in some data
  3. Click Cancel
- **Expected:** Form clears, "New Patient" button reappears
- **Status:** ✅ PASS

---

## Suite 04 — Doctor Master

### TC-DOC-01
- **Title:** Doctors page renders correctly
- **Module:** Doctor Master
- **Priority:** P1
- **Steps:** Navigate to `/doctors`
- **Expected:** Heading "Doctors", "New Doctor" button visible
- **Status:** ✅ PASS

---

### TC-DOC-02
- **Title:** Create doctor with all fields
- **Module:** Doctor Master
- **Priority:** P0
- **Steps:**
  1. Click "New Doctor"
  2. Fill: Name, Type (Internal), Qualifications, Specialization, Mobile, Consultation Fee (300), Commission (5%)
  3. Save
- **Expected:** Doctor created, appears in search; auto-code generated
- **Status:** ✅ PASS (Created ANI001 — Anil Sharma in session)

---

### TC-DOC-03
- **Title:** Doctor auto-code generated in correct format
- **Module:** Doctor Master
- **Priority:** P2
- **Steps:**
  1. Create doctor named "Anil Sharma"
  2. Check generated code
- **Expected:** Code format: First-3-letters + 3-digit-sequence e.g. ANI001
- **Status:** ✅ PASS

---

### TC-DOC-04
- **Title:** Signature image upload UI renders
- **Module:** Doctor Master
- **Priority:** P3
- **Steps:**
  1. Click "New Doctor"
  2. Check signature upload section
- **Expected:** "Choose File" button and "JPG, PNG, BMP or GIF" text visible
- **Status:** ✅ PASS

---

### TC-DOC-05
- **Title:** Doctor type options are correct
- **Module:** Doctor Master
- **Priority:** P2
- **Steps:**
  1. Click "New Doctor"
  2. Check Type dropdown
- **Expected:** Options: Referral, Internal, Both
- **Status:** ✅ PASS

---

## Suite 05 — Account Master

### TC-ACC-01
- **Title:** Accounts page shows account type filter buttons
- **Module:** Account Master
- **Priority:** P1
- **Steps:** Navigate to `/accounts`
- **Expected:** Customers, Suppliers, Banks, Cash buttons visible
- **Status:** ✅ PASS

---

### TC-ACC-02
- **Title:** SUPP0001 MediSupply Pvt Ltd exists (created during gap-fix)
- **Module:** Account Master
- **Priority:** P0 — Prerequisite
- **Steps:**
  1. Navigate to `/accounts`
  2. Search for "MediSupply"
- **Expected:** Account "MediSupply Pvt Ltd" with code SUPP0001 visible under Suppliers
- **Status:** ✅ PASS (Created on 2026-07-30 to fix gaps B4/B5)

---

### TC-ACC-03
- **Title:** Create a new supplier account
- **Module:** Account Master
- **Priority:** P1
- **Steps:**
  1. Click "Add Account"
  2. Select "Suppliers" type
  3. Fill: Name, Mobile, City, Group (Current Liabilities)
  4. Click "Create Account"
- **Expected:** New account appears in Suppliers list
- **Status:** ✅ PASS

---

### TC-ACC-04
- **Title:** All four account types selectable in Add Account form
- **Module:** Account Master
- **Priority:** P2
- **Steps:**
  1. Click "Add Account"
  2. Try selecting Customers, Suppliers, Banks, Cash
- **Expected:** All 4 type buttons respond correctly
- **Status:** ✅ PASS

---

### TC-ACC-05
- **Title:** Account Group dropdown has all ledger groups
- **Module:** Account Master
- **Priority:** P2
- **Steps:**
  1. Click "Add Account"
  2. Check Group dropdown
- **Expected:** Includes Current Assets, Current Liabilities, Laboratory Income, Laboratory Expenses
- **Status:** ✅ PASS

---

## Suite 06 — Patient Entry (Lab Registration)

### TC-ENTRY-01
- **Title:** Lab entries page renders correctly
- **Module:** Patient Entry
- **Priority:** P1
- **Steps:** Navigate to `/lab-entries`
- **Expected:** Heading "Patient Entry", "New Entry" and "Export" buttons
- **Status:** ✅ PASS

---

### TC-ENTRY-02
- **Title:** New Entry form has all required fields
- **Module:** Patient Entry
- **Priority:** P1
- **Steps:** Navigate to `/lab-entries` (New Entry loads by default)
- **Expected:** Patient search, Doctor search, Company search, Test search, Package search, Discount % field all visible
- **Status:** ✅ PASS

---

### TC-ENTRY-03
- **Title:** Patient search returns results
- **Module:** Patient Entry
- **Priority:** P0
- **Steps:**
  1. Navigate to `/lab-entries`
  2. Type "Rajesh" in Patient search
- **Expected:** "Rajesh Kumar" appears in dropdown
- **Status:** ✅ PASS

---

### TC-ENTRY-04
- **Title:** Doctor search returns results
- **Module:** Patient Entry
- **Priority:** P0
- **Steps:**
  1. Navigate to `/lab-entries`
  2. Type "Anil" in Doctor search
- **Expected:** "Anil Sharma" appears in dropdown
- **Status:** ✅ PASS

---

### TC-ENTRY-05
- **Title:** Test search finds tests
- **Module:** Patient Entry
- **Priority:** P0
- **Steps:**
  1. Navigate to `/lab-entries`
  2. Type "Hemoglobin" in Test search
- **Expected:** "Hemoglobin" test appears in dropdown
- **Status:** ✅ PASS

---

### TC-ENTRY-06
- **Title:** Create complete lab entry
- **Module:** Patient Entry
- **Priority:** P0
- **Steps:**
  1. Select patient: Rajesh Kumar
  2. Select doctor: Anil Sharma
  3. Select company: General Patient
  4. Add test: Hemoglobin
  5. Click Save
- **Expected:** Voucher created with number PE26G######
- **Status:** ✅ PASS (PE26G300001 created in session)

---

### TC-ENTRY-07
- **Title:** Gross/Net/Balance auto-calculated
- **Module:** Patient Entry
- **Priority:** P1
- **Steps:**
  1. Create entry with tests
  2. Check calculation section after save
- **Expected:** Gross Amount, Net Amount, Balance fields visible and calculated
- **Status:** ✅ PASS

---

### TC-ENTRY-08
- **Title:** Export button visible on entries list
- **Module:** Patient Entry
- **Priority:** P3
- **Steps:** Navigate to `/lab-entries`, check top bar
- **Expected:** "Export" button visible
- **Status:** ✅ PASS

---

## Suite 07 — Sample Collection

### TC-SAMP-01
- **Title:** All status filter tabs render
- **Module:** Sample Collection
- **Priority:** P1
- **Steps:** Navigate to `/samples`
- **Expected:** Pending, Collected, In Testing, Completed, Rejected, STAT, Expired tab buttons visible
- **Status:** ✅ PASS

---

### TC-SAMP-02
- **Title:** Pending samples listed
- **Module:** Sample Collection
- **Priority:** P1
- **Steps:**
  1. Navigate to `/samples`
  2. Click "Pending" tab
- **Expected:** PE26G entries listed
- **Status:** ✅ PASS

---

### TC-SAMP-03
- **Title:** Batch Collect wizard shows Step 1 and Step 2
- **Module:** Sample Collection
- **Priority:** P1
- **Steps:**
  1. Click "Pending" tab
  2. Click "Batch Collect" on any entry
- **Expected:** Step 1: Auto-Verify Patient Identifiers and Step 2: Manual Verification visible
- **Status:** ✅ PASS

---

### TC-SAMP-04
- **Title:** Batch Collect button disabled until verification complete
- **Module:** Sample Collection
- **Priority:** P2
- **Steps:**
  1. Open Batch Collect wizard
  2. Check Collect N Samples button state before completing steps
- **Expected:** Button is disabled
- **Status:** ✅ PASS

---

### TC-SAMP-05
- **Title:** CLSI draw order shown in batch collect
- **Module:** Sample Collection
- **Priority:** P2
- **Steps:**
  1. Open Batch Collect wizard
- **Expected:** "CLSI Draw Order" section visible
- **Status:** ✅ PASS

---

### TC-SAMP-06
- **Title:** Board view accessible
- **Module:** Sample Collection
- **Priority:** P2
- **Steps:** Click "Board" button
- **Expected:** Board/kanban view renders without error
- **Status:** ✅ PASS

---

### TC-SAMP-07
- **Title:** Stock button accessible
- **Module:** Sample Collection
- **Priority:** P2
- **Steps:** Check "Stock" button visibility
- **Expected:** Button visible in header area
- **Status:** ✅ PASS

---

### TC-SAMP-08
- **Title:** Search by Entry ID works
- **Module:** Sample Collection
- **Priority:** P1
- **Steps:**
  1. Enter "PE26G300001" in search field
  2. Click Search
- **Expected:** PE26G300001 entry appears
- **Status:** ✅ PASS

---

## Suite 08 — Readings

### TC-READ-01
- **Title:** Readings page renders from URL
- **Module:** Readings
- **Priority:** P1
- **Steps:** Navigate to `/readings`
- **Expected:** Heading "Readings", "New Reading" button
- **Status:** ✅ PASS

---

### TC-READ-02
- **Title:** Entry pre-selection via URL query param
- **Module:** Readings
- **Priority:** P1
- **Steps:** Navigate to `/readings?entryVrNo=PE26G300001`
- **Expected:** PE26G300001 loaded, test count shown
- **Status:** ✅ PASS

---

### TC-READ-03
- **Title:** Tests grouped by department
- **Module:** Readings
- **Priority:** P2
- **Steps:** Open PE26G300001 readings
- **Expected:** "Pathology" department heading visible
- **Status:** ✅ PASS

---

### TC-READ-04
- **Title:** Normal range displayed per test
- **Module:** Readings
- **Priority:** P2
- **Steps:** Open readings for PE26G300001
- **Expected:** "Normal: 13.0 – 17.0" or similar range shown
- **Status:** ✅ PASS

---

### TC-READ-05
- **Title:** Result field accepts numeric input
- **Module:** Readings
- **Priority:** P0
- **Steps:**
  1. Open readings
  2. Enter "15.2" in first result field
- **Expected:** Field accepts and retains "15.2"
- **Status:** ✅ PASS

---

### TC-READ-06
- **Title:** AI Suggestion button present
- **Module:** Readings
- **Priority:** P3
- **Steps:** Open readings for any entry
- **Expected:** "Get AI Suggestion" button visible
- **Status:** ✅ PASS

---

### TC-READ-07
- **Title:** Overall Remarks field editable
- **Module:** Readings
- **Priority:** P2
- **Steps:**
  1. Open readings
  2. Enter text in "Overall Remarks" field
- **Expected:** Text accepted and shown
- **Status:** ✅ PASS

---

### TC-READ-08
- **Title:** Save Department button present per section
- **Module:** Readings
- **Priority:** P1
- **Steps:** Open readings with results in Pathology dept
- **Expected:** "Save Department" button visible per department
- **Status:** ✅ PASS

---

## Suite 09 — Receipt Entry

### TC-REC-01
- **Title:** Receipt entry page renders
- **Module:** Receipt Entry
- **Priority:** P1
- **Steps:** Navigate to `/receipt-entry`
- **Expected:** "New Receipt Entry" heading, patient entry search visible
- **Status:** ✅ PASS

---

### TC-REC-02
- **Title:** All payment modes available
- **Module:** Receipt Entry
- **Priority:** P1
- **Steps:** Check Type dropdown options
- **Expected:** Cash, Cheque, UPI, Card, RTGS, NEFT all present
- **Status:** ✅ PASS

---

### TC-REC-03
- **Title:** Linking entry auto-fills amount
- **Module:** Receipt Entry
- **Priority:** P0
- **Steps:**
  1. Search and select PE26G300001 entry
- **Expected:** Amount auto-populated as ₹160
- **Status:** ✅ PASS

---

### TC-REC-04
- **Title:** Outstanding vouchers section shows balance
- **Module:** Receipt Entry
- **Priority:** P1
- **Steps:** Link PE26G300001
- **Expected:** "Outstanding Vouchers" section visible with ₹160 balance
- **Status:** ✅ PASS

---

### TC-REC-05
- **Title:** RC26G300001 receipt exists
- **Module:** Receipt Entry
- **Priority:** P1
- **Steps:** Click "Show all items" in receipt search
- **Expected:** RC26G300001 visible in dropdown
- **Status:** ✅ PASS

---

### TC-REC-06
- **Title:** Bank and Cash accounts selectable
- **Module:** Receipt Entry
- **Priority:** P1
- **Steps:** Check account dropdown options
- **Expected:** BANK01 and CASH01 both available
- **Status:** ✅ PASS

---

## Suite 10 — Payment Entry

### TC-PAY-01
- **Title:** Payment entry page renders
- **Module:** Payment Entry
- **Priority:** P1
- **Steps:** Navigate to `/payment-entry`
- **Expected:** "New Payment Entry" heading visible
- **Status:** ✅ PASS (after SUPP0001 was created)

---

### TC-PAY-02
- **Title:** MediSupply Pvt Ltd appears in supplier search
- **Module:** Payment Entry
- **Priority:** P0 — Prerequisite: SUPP0001 must exist
- **Steps:**
  1. Navigate to `/payment-entry`
  2. Type "Medi" in supplier search
- **Expected:** "MediSupply Pvt Ltd" in dropdown
- **Status:** ✅ PASS

---

### TC-PAY-03
- **Title:** PY26G300001 payment exists
- **Module:** Payment Entry
- **Priority:** P1
- **Steps:** Show all items in payment dropdown
- **Expected:** PY26G300001 (₹4,500 cash to MediSupply) visible
- **Status:** ✅ PASS

---

### TC-PAY-04
- **Title:** Create payment to supplier
- **Module:** Payment Entry
- **Priority:** P0
- **Steps:**
  1. Select supplier: MediSupply Pvt Ltd
  2. Enter description and amount
  3. Save
- **Expected:** Payment voucher created (PY26G######)
- **Status:** ✅ PASS (PY26G300001 = ₹4,500 cash payment)

---

### TC-PAY-05
- **Title:** All payment modes available
- **Module:** Payment Entry
- **Priority:** P1
- **Steps:** Check payment type dropdown options
- **Expected:** Cash, UPI, NEFT, RTGS all present
- **Status:** ✅ PASS

---

## Suite 11 — Journal Entry

### TC-JNL-01
- **Title:** Journal entry page renders with 2 default lines
- **Module:** Journal Entry
- **Priority:** P1
- **Steps:** Navigate to `/journal-entry`
- **Expected:** "New Journal Entry" heading, Add Line button, 2+ default rows
- **Status:** ✅ PASS

---

### TC-JNL-02
- **Title:** JR26G300001 journal entry exists
- **Module:** Journal Entry
- **Priority:** P1
- **Steps:** Show all items in journal dropdown
- **Expected:** JR26G300001 visible
- **Status:** ✅ PASS

---

### TC-JNL-03
- **Title:** Debit/Credit balance validation
- **Module:** Journal Entry
- **Priority:** P1
- **Steps:**
  1. Select accounts for both lines
  2. Enter equal debit/credit amounts (500 each)
- **Expected:** Balance indicator shows ✓ green, Save button enabled
- **Status:** ✅ PASS

---

### TC-JNL-04
- **Title:** Swap Debit/Credit button works
- **Module:** Journal Entry
- **Priority:** P3
- **Steps:** Click "Swap Debit ↔ Credit" on any line
- **Expected:** Debit and Credit values swap
- **Status:** ✅ PASS

---

### TC-JNL-05
- **Title:** Add Line inserts new row
- **Module:** Journal Entry
- **Priority:** P2
- **Steps:**
  1. Note current row count
  2. Click "Add Line"
- **Expected:** Row count increases by 1
- **Status:** ✅ PASS

---

### TC-JNL-06
- **Title:** [BUG-B8] Journal should have Post/Approve button
- **Module:** Journal Entry
- **Priority:** P2 Bug
- **Steps:**
  1. Load existing journal JR26G300001
  2. Check for Post/Approve/Finalize button
- **Expected:** Button to finalize journal from Draft status
- **Actual:** Only "Save Journal Entry" — no posting workflow
- **Status:** ❌ FAIL — **BUG B8 (OPEN)**

---

## Suite 12 — Inventory

### TC-INV-01
- **Title:** All inventory tabs visible
- **Module:** Inventory
- **Priority:** P1
- **Steps:** Navigate to `/inventory`
- **Expected:** Overview, Items, Purchases, Usage, Stock tabs visible
- **Status:** ✅ PASS

---

### TC-INV-02
- **Title:** EDTA Tubes 5ml has stock 10 — status OK
- **Module:** Inventory
- **Priority:** P0 — Verify gap fix
- **Steps:**
  1. Navigate to `/inventory`
  2. Click Items tab
- **Expected:** "EDTA Tubes 5ml" row shows "10 Box" and "OK" status
- **Status:** ✅ PASS (Stock added via PUR-20260730-001)

---

### TC-INV-03
- **Title:** Purchase PUR-20260730-001 exists
- **Module:** Inventory
- **Priority:** P0 — Verify gap fix
- **Steps:**
  1. Click Purchases tab
- **Expected:** PUR-20260730-001 from MediSupply Pvt Ltd for ₹4,500 visible
- **Status:** ✅ PASS

---

### TC-INV-04
- **Title:** Create new inventory item
- **Module:** Inventory
- **Priority:** P1
- **Steps:**
  1. Click Items → Add Item
  2. Fill: Name, Description, Category (Reagents), Unit (Bottle), Min Stock (200)
  3. Create
- **Expected:** New item appears in Items list
- **Status:** ✅ PASS

---

### TC-INV-05
- **Title:** New purchase uses SUPP0001 supplier
- **Module:** Inventory
- **Priority:** P0 — Verify gap fix
- **Steps:**
  1. Click Purchases → New Purchase
  2. Select supplier MediSupply Pvt Ltd
- **Expected:** Supplier selection works, form continues
- **Status:** ✅ PASS

---

### TC-INV-06
- **Title:** Category dropdown has 6 options
- **Module:** Inventory
- **Priority:** P2
- **Steps:** Add Item → check Category dropdown
- **Expected:** Consumables, Reagents, Containers, General, Chemicals, Other
- **Status:** ✅ PASS

---

### TC-INV-07
- **Title:** Minimum stock alert shown as OK/WARNING
- **Module:** Inventory
- **Priority:** P2
- **Steps:** Check Items tab with existing item
- **Expected:** "OK" badge when current stock > min, "WARNING" when below
- **Status:** ✅ PASS (EDTA Tubes: 10 Box / Min 5 → OK)

---

## Suite 13 — Tests Master

### TC-TEST-01
- **Title:** Tests page shows 4 test type buttons
- **Module:** Tests Master
- **Priority:** P1
- **Steps:** Navigate to `/tests`
- **Expected:** Reading, Formula, Formatted, Group buttons visible
- **Status:** ✅ PASS

---

### TC-TEST-02
- **Title:** Reading test form has reference range fields
- **Module:** Tests Master
- **Priority:** P1
- **Steps:** Open new test of type Reading
- **Expected:** Male Min/Max, Female Min/Max, Panic Low/High fields visible
- **Status:** ✅ PASS

---

### TC-TEST-03
- **Title:** Duplicate test name rejected
- **Module:** Tests Master
- **Priority:** P1
- **Steps:**
  1. Create test with name "Hemoglobin" (already exists)
  2. Save
- **Expected:** Error "already exists" shown
- **Status:** ✅ PASS

---

### TC-TEST-04
- **Title:** Department dropdown has all 8 departments
- **Module:** Tests Master
- **Priority:** P2
- **Steps:** Open new test, check Department dropdown
- **Expected:** Pathology, Radiology, Microbiology, Blood Bank, Cardiology, Pulmonology, Neurology, Endoscopy
- **Status:** ✅ PASS

---

### TC-TEST-05
- **Title:** Specimen dropdown has all types
- **Module:** Tests Master
- **Priority:** P2
- **Steps:** Open new test, check Specimen dropdown
- **Expected:** Blood, Urine, Serum, Plasma, Stool at minimum
- **Status:** ✅ PASS

---

### TC-TEST-06
- **Title:** Collection requirement checkboxes present
- **Module:** Tests Master
- **Priority:** P2
- **Steps:** Open new test, check sample collection section
- **Expected:** "Requires Fasting", "Protect from Light", "Requires Mixing/Inversion" checkboxes
- **Status:** ✅ PASS

---

### TC-TEST-07
- **Title:** Print and Quick List checkboxes present
- **Module:** Tests Master
- **Priority:** P3
- **Steps:** Open new test form
- **Expected:** "Print on New Page" and "Add to Quick List" checkboxes visible
- **Status:** ✅ PASS

---

## Suite 14 — General Master

### TC-GM-01
- **Title:** General Master shows stats
- **Module:** General Master
- **Priority:** P2
- **Steps:** Navigate to `/general-master`
- **Expected:** Shows 8 Departments, 32 Categories, 83 Sub-Categories
- **Status:** ✅ PASS

---

### TC-GM-02
- **Title:** All 8 departments listed
- **Module:** General Master
- **Priority:** P1
- **Steps:** Navigate to `/general-master`
- **Expected:** Pathology, Radiology, Microbiology, Blood Bank, Cardiology, Pulmonology, Neurology, Endoscopy
- **Status:** ✅ PASS

---

### TC-GM-03
- **Title:** Deactivate toggle present per department
- **Module:** General Master
- **Priority:** P2
- **Steps:** Check Pathology row
- **Expected:** "Deactivate Pathology" button visible
- **Status:** ✅ PASS

---

### TC-GM-04
- **Title:** Categories tab shows test categories
- **Module:** General Master
- **Priority:** P2
- **Steps:** Switch to Categories tab
- **Expected:** Hematology, Biochemistry, Serology (or similar) visible
- **Status:** ✅ PASS

---

## Suite 15 — System Modules

### TC-SYS-01
- **Title:** Report Templates page renders
- **Module:** System
- **Priority:** P1
- **Steps:** Navigate to `/report-templates`
- **Expected:** "Report Templates" heading, "New Template" button
- **Status:** ✅ PASS

---

### TC-SYS-02
- **Title:** Analyzers page renders
- **Module:** System
- **Priority:** P1
- **Steps:** Navigate to `/analyzers`
- **Expected:** "Analyzers / Machines" heading, "New Analyzer" and "Pending Results" buttons
- **Status:** ✅ PASS

---

### TC-SYS-03
- **Title:** Admin Panel shows user management
- **Module:** System
- **Priority:** P1
- **Steps:** Navigate to `/admin`
- **Expected:** "adminuser" listed, "Add User" button visible
- **Status:** ✅ PASS

---

### TC-SYS-04
- **Title:** Admin Panel tabs
- **Module:** System
- **Priority:** P2
- **Steps:** Navigate to `/admin`, check tabs
- **Expected:** User Management, Active Sessions, Lab Settings tabs
- **Status:** ✅ PASS

---

### TC-SYS-05
- **Title:** Menu Rights shows 4 built-in roles
- **Module:** System
- **Priority:** P2
- **Steps:** Navigate to `/permissions`
- **Expected:** Admin (Full access), Standard (Create, edit), Limited (View only), User (View and print) roles
- **Status:** ✅ PASS

---

### TC-SYS-06
- **Title:** All 7 main modules in permissions matrix
- **Module:** System
- **Priority:** P2
- **Steps:** Navigate to `/permissions`, scan permission rows
- **Expected:** Patient Entry, Sample Collections, Readings, Receipt Entry, Payment Entry, Journal Entry, Inventory
- **Status:** ✅ PASS

---

### TC-SYS-07
- **Title:** Each module has 6 permission types
- **Module:** System
- **Priority:** P2
- **Steps:** Check any module row in permissions matrix
- **Expected:** View, Create, Edit, Delete, Print, Export toggles
- **Status:** ✅ PASS

---

### TC-SYS-08
- **Title:** Settings page has 4 tabs
- **Module:** System
- **Priority:** P2
- **Steps:** Navigate to `/settings`, check tabs
- **Expected:** Profile, Password, My Modules, Notifications
- **Status:** ✅ PASS

---

### TC-SYS-09
- **Title:** Settings Profile shows correct user info
- **Module:** System
- **Priority:** P2
- **Steps:** Navigate to `/settings` → Profile tab
- **Expected:** "Admin User", "Administrator", "Demo Lab" visible
- **Status:** ✅ PASS

---

## Suite 16 — Rates & Packages

### TC-RATE-01
- **Title:** Rates page shows 159 tests without rates warning
- **Module:** Rates
- **Priority:** P2
- **Steps:** Navigate to `/rates`
- **Expected:** "159 tests without rates" indicator
- **Status:** ✅ PASS

---

### TC-RATE-02
- **Title:** Rates page has bulk management buttons
- **Module:** Rates
- **Priority:** P2
- **Steps:** Navigate to `/rates`, check top bar
- **Expected:** Add Rate, Copy Rates, Bulk Update buttons visible
- **Status:** ✅ PASS

---

### TC-PKG-01
- **Title:** Packages page renders
- **Module:** Packages
- **Priority:** P2
- **Steps:** Navigate to `/packages`
- **Expected:** Page loads without error
- **Status:** ✅ PASS

---

### TC-APT-01
- **Title:** Appointments page with stats and table
- **Module:** Appointments
- **Priority:** P2
- **Steps:** Navigate to `/appointments`
- **Expected:** Heading "Appointments", table with Patient, Doctor, Status columns
- **Status:** ✅ PASS

---

## Suite 17 — Bug Regression

> **Note:** All bugs in this suite are currently OPEN as of 2026-07-30. Re-run to track resolution.

### TC-BUG-B1
- **Title:** Dashboard API 403 regression
- **Bug ID:** B1
- **Priority:** P0 — Critical
- **Reproduction:**
  1. Login successfully
  2. Open browser dev tools → Network tab
  3. Navigate to `/dashboard`
  4. Find request to `/api/dashboard`
- **Expected:** HTTP 200 with KPI data
- **Actual:** HTTP 403 Forbidden
- **Impact:** All dashboard KPIs show 0; no operational metrics visible
- **Status:** ❌ OPEN

---

### TC-BUG-B2
- **Title:** auth/me 401 after login regression
- **Bug ID:** B2
- **Priority:** P0 — Critical
- **Reproduction:**
  1. Login successfully
  2. Monitor Network for `/api/auth/me`
- **Expected:** 200 with session/user data
- **Actual:** 401 Unauthorized
- **Impact:** Session validation likely broken; may affect all protected routes
- **Status:** ❌ OPEN

---

### TC-BUG-B3
- **Title:** Gender field disabled on loaded patient form
- **Bug ID:** B3
- **Priority:** P2
- **Reproduction:**
  1. Navigate to `/patients`
  2. Search and select any existing patient
  3. Check Gender dropdown state
- **Expected:** Gender dropdown enabled and editable
- **Actual:** Gender `<select>` element has `disabled` attribute
- **Workaround:** Click "New Patient" for fresh form; Gender enabled in new-patient mode
- **Status:** ❌ OPEN

---

### TC-BUG-B4 (FIXED)
- **Title:** No supplier account — Payment Entry blocked
- **Bug ID:** B4
- **Priority:** P0 — Critical (was blocking)
- **Fix Applied:** Created SUPP0001 MediSupply Pvt Ltd on 2026-07-30
- **Verification:** PY26G300001 payment created successfully after fix
- **Status:** ✅ FIXED

---

### TC-BUG-B5 (FIXED)
- **Title:** No supplier account — Inventory Purchase blocked
- **Bug ID:** B5
- **Priority:** P0 — Critical (was blocking)
- **Fix Applied:** Used SUPP0001 to create PUR-20260730-001 (10× EDTA Tubes)
- **Verification:** Stock updated to 10 Box with OK status
- **Status:** ✅ FIXED

---

### TC-BUG-B6
- **Title:** Global search bar non-functional
- **Bug ID:** B6
- **Priority:** P2
- **Reproduction:**
  1. Login, click global search in header
  2. Type "Rajesh"
  3. Press Enter
- **Expected:** Navigate to search results or show live dropdown
- **Actual:** No action taken, cursor stays in field
- **Impact:** Users cannot search across modules from header
- **Status:** ❌ OPEN

---

### TC-BUG-B7
- **Title:** CSP blocks Cloudflare beacon.min.js
- **Bug ID:** B7
- **Priority:** P3
- **Reproduction:**
  1. Navigate to any page
  2. Open browser console
  3. Look for CSP violations
- **Expected:** No CSP violations
- **Actual:** Console error: Content Security Policy directive `script-src` blocks `beacon.min.js`
- **Impact:** Cloudflare analytics not reporting; cosmetic console noise
- **Status:** ❌ OPEN

---

### TC-BUG-B8
- **Title:** Journal Entry has no Post/Approve workflow
- **Bug ID:** B8
- **Priority:** P2
- **Reproduction:**
  1. Navigate to `/journal-entry`
  2. Load JR26G300001 or create new journal
  3. Check for Post/Approve/Finalize button
- **Expected:** Saved journals can be Posted to make them permanent
- **Actual:** Only "Save as Draft" functionality; no way to finalize entries
- **Impact:** Accounting workflow incomplete; no audit trail distinction between draft and posted
- **Status:** ❌ OPEN

---

## Data Created in E2E Session

| Entity | Code/ID | Details |
|--------|---------|---------|
| Patient | 202607300001 | Rajesh Kumar, Male, 35Y, O+ |
| Doctor | ANI001 | Anil Sharma, Internal, MBBS, ₹300 fee |
| Supplier | SUPP0001 | MediSupply Pvt Ltd, Bangalore |
| Lab Entry | PE26G300001 | Rajesh Kumar + Hemoglobin + Platelet Count |
| Receipt | RC26G300001 | ₹160 Cash for PE26G300001 |
| Payment | PY26G300001 | ₹4,500 Cash to MediSupply |
| Journal | JR26G300001 | CASH01 Dr ₹500, BANK01 Cr ₹500 |
| Inventory Item | INV-0001 | EDTA Tubes 5ml, Box, Min 5 |
| Purchase | PUR-20260730-001 | 10× EDTA Tubes 5ml, ₹4,500 from SUPP0001 |

---

## Running the Playwright Test Suite

```bash
# Install dependencies
cd C:\GitRepo\ml
npm init -y
npm install --save-dev @playwright/test
npx playwright install

# Run all tests
npx playwright test tests/mlab.e2e.spec.ts

# Run specific suite
npx playwright test --grep "Suite 01"

# Run bug regression only
npx playwright test --grep "Suite 17"

# Run with headed browser (visible)
npx playwright test --headed

# Generate HTML report
npx playwright test --reporter=html
npx playwright show-report
```

---

*Test cases last updated: 2026-07-30 | Executed by: GitHub Copilot E2E Session*
