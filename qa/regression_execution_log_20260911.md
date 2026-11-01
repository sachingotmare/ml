# MLab Regression Execution Log — 2026-09-11

## Environment
- URL: https://mlab.sgsoftech.in
- User: demo2026 admin
- Scope: smoke + critical data-entry regression across MAIN, MASTERS, REPORTS, SYSTEM menus.

## End-to-end transactions executed

### 1) Test master creation
- Module: `/tests`
- Record created: **QAAU001**
- Name: **QA AUTO GLUCOSE PROFILE 20260911**
- Result: Saved successfully and opened in read-only mode.

### 2) Doctor master creation
- Module: `/doctors`
- Record created: **DRQ001**
- Name: **Dr QA Regression 20260911**
- Result: Saved successfully and opened in read-only mode.

### 3) Patient entry creation
- Module: `/lab-entries`
- Entry created: **PE26I110001**
- Patient: DEMO
- Ref Doctor: A . KUSHWAHA
- Test: QAAU001
- Discount: 5%
- Net observed: 237.5
- Result: Saved successfully; status pending.

### 4) Reading entry save
- Module: `/readings?entryVrNo=PE26I110001`
- Value entered: 95
- Suggestion: Within normal limits.
- Result: Saved=1 and status shown as Normal.

### 5) Receipt posting
- Module: `/receipt-entry`
- Receipt created: **RC26I110001**
- Reference voucher: PE26I110001
- Mode: Cash
- Account: CASH01
- Amount: 237.5
- Result: Posted successfully; printable receipt visible and balance reduced to zero.

## Additional module navigation checks

### MAIN
- `/samples`: loaded; dashboard visible, no samples listed for current filter.
- `/payment-entry`: loaded with voucher/account fields.
- `/journal-entry`: loaded with journal lines grid.
- `/inventory`: loaded UI but API errors observed (see defects).
- `/appointments`: loaded; new appointment form visible.

### MASTERS
- `/patients`: loaded patient form and listing.
- `/accounts`: loaded account master and stats.
- `/general-master`: loaded department/category/sub-category stats and list.
- `/rates`: loaded rate master with coverage metrics.
- `/packages`: loaded package management page.

### REPORTS
- `/reports/laboratory`: loaded report selector and metadata panel.

### SYSTEM
- `/settings`: loaded profile/password/modules tabs.
- `/admin`: loaded user management/active sessions/lab settings tabs.
- `/permissions`: loaded role permissions matrix.

## Defects / observations
1. **Inventory API failure**
   - Page: `/inventory`
   - Error: `500` on `/api/inventory/dashboard` (seen twice)
   - Impact: dashboard data may be unavailable.

2. **Doctor header duplication pattern**
   - Created record shows title and name in a way that can appear as duplicated prefix (e.g., "Dr Dr ...") depending on entered name.
   - Impact: display/usability formatting issue.

3. **Numeric field append behavior (earlier test form observation)**
   - Some numeric controls (e.g., TAT/stability fields) appeared to concatenate values unexpectedly during edit flow.
   - Impact: potential data-entry confusion.

## Overall status
- Critical E2E transaction chain (master → entry → reading → receipt): **PASS**.
- Cross-menu page load smoke coverage: **PASS with one backend defect** (Inventory 500).
- Recommended next step: execute and mark all 184 field-level cases from `mlab_e2e_execution_sheet.csv` as Pass/Fail/Blocked with evidence IDs.

## Follow-up deep execution (same day)

### 1) Company master (Accounts) — data entry tested
- Module: `/accounts`
- Created record: **QA COMPANY 0911**
- Observed code: **QAC001**
- Entered fields: name, phone, mobile, email, GSTIN, address, city, opening balance, account group.
- Validation outcome: save worked; Customers count increased from **9** to **10**; search returned created account.

### 2) Rate master — data entry tested
- Module: `/rates`
- Created corporate rate for:
   - Test: **QAAU001**
   - Company: **QA COMPANY 0911 (QAC001)**
   - Rate: **₹275.00**
- Validation outcome: new rate row visible; coverage moved from **1787/1788** to **1788/1788**; active/client counters incremented.

### 3) Menu rights / role rights — interactive permissions tested
- Module: `/permissions`
- Actions: opened role matrix, changed permission level controls, invoked save.
- Validation outcome: rights matrix and role cards are interactive; save action triggers without frontend exception.

### 4) User creation (Admin panel) — attempted and failed
- Module: `/admin`
- Attempted values: `qauser0911`, `QA User 0911`, password and contact values filled.
- Result: modal stayed open and user row was not persisted in grid.
- Defect candidate: **BUG-ADMIN-USER-001**.

### 5) Appointment creation — attempted and failed
- Module: `/appointments`
- Selected patient/doctor/company and filled time/reason.
- Result: after save attempt, grid still showed **No appointments found**.
- Defect candidate: **BUG-APP-SAVE-001**.

### 6) Reports execution limits
- Module: `/reports/laboratory`
- Result: report selector present, but no consumable metadata/report definition exposed to proceed with filter/preview/export scenarios.
- Status: blocked pending report metadata availability.
