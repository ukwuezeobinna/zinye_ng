# Browser Test Checklist — zinye_ng Nigeria Compliance

Run this after every deployment. Check each box as you verify it.

**Site URL:** `https://yoursite.zinye.com`  
**Login:** Accounts Manager or System Manager role required for most tests.

---

## Setup Verification

- [ ] **Custom Fields exist on Company**
  - Go to: Accounting → Company → [your company]
  - Scroll past "Country" — the **Nigeria Compliance** section should appear
  - Fields visible: TIN, RC Number, VAT Registration Number, Registered State, State IRS Code, ITF Liable

- [ ] **Custom Fields exist on Employee**
  - Go to: HR → Employee → [any employee]
  - Scroll to **Nigeria Compliance** section
  - Fields visible: Employee TIN, NHF Number, RSA PIN, Pension Fund Administrator, Exempted from NHF

- [ ] **Custom Fields exist on Supplier**
  - Go to: Buying → Supplier → [any supplier]
  - Fields visible: TIN, RC Number, WHT Category

- [ ] **Custom Fields exist on Customer**
  - Go to: Selling → Customer → [any customer]
  - Fields visible: TIN, RC Number

- [ ] **NG Employee Standard salary structure exists**
  - Go to: Payroll → Salary Structure → search "NG Employee Standard"
  - Open it — verify Earnings and Deductions tabs have the NG components

- [ ] **Nigeria Payroll Settings exists**
  - Search "Nigeria Payroll Settings" in the top bar
  - Should open showing Pension (8%/10%), NHF (2.5%), etc.

- [ ] **NRS E-Invoice Settings exists**
  - Search "NRS E-Invoice Settings" in the top bar
  - Should open (even if Enabled = Off)

- [ ] **NRS ATRS Settings exists**
  - Search "NRS ATRS Settings" in the top bar
  - Should open

---

## PAYE Test

**Prerequisite:** At least one submitted Salary Slip exists.

- [ ] Open a **Salary Slip** (Payroll → Salary Slip → any submitted slip)
- [ ] In the **Deductions** table, find **NG - PAYE Tax**
- [ ] Confirm the amount is non-zero (unless employee earns ≤ ₦70k/month)
- [ ] Manual check: gross_pay × 12 → apply bands → ÷ 12 = expected monthly PAYE

**Minimum wage employee test (if available):**
- [ ] Open a salary slip for an employee earning ≤ ₦70,000/month
- [ ] Confirm **NG - PAYE Tax** amount = ₦0.00

---

## WHT Auto-Fill Test

- [ ] Go to: Buying → Purchase Invoice → **New**
- [ ] Select a **Supplier** that has a WHT Category set (e.g., "Professional / Consultancy Fees")
- [ ] After selecting supplier: scroll to **Withholding Tax** section
- [ ] Confirm **WHT Applicable** is ticked automatically
- [ ] Confirm **WHT Rate (%)** is auto-filled (e.g., 10% for Professional fees)
- [ ] Change supplier to one with no WHT Category
- [ ] Confirm WHT Applicable unchecks and Rate clears to 0

**WHT Journal Entry test:**
- [ ] Fill out the Purchase Invoice fully (add items, set supplier address, etc.)
- [ ] Verify WHT Amount shows a non-zero computed value
- [ ] Submit the invoice
- [ ] Confirm a green alert "WHT Journal Entry [PINV-ACC-xxxx] created for ₦..." appears
- [ ] Go to Accounting → Journal Entry → search for the JE linked to this invoice
- [ ] Confirm Dr Accounts Payable / Cr WHT Payable structure

---

## WHT Schedule Report Test

- [ ] Go to Reports → Nigeria WHT Schedule (or search in top bar)
- [ ] Set Company and date range covering the test invoice above
- [ ] Click Refresh
- [ ] Confirm the submitted invoice appears with correct supplier TIN, WHT rate, WHT amount, and linked JE

---

## VAT Return Report Test

- [ ] Go to Reports → Nigeria VAT Return
- [ ] Set Company and date range
- [ ] Click Refresh
- [ ] Output VAT section should list Sales Invoices with VAT charges
- [ ] Customer TIN column should show TIN for any customers where TIN is set
- [ ] Output VAT Total row should appear (bold)
- [ ] Enable "Include Purchase VAT" filter → Input VAT section appears + VAT Payable row

---

## PAYE Schedule Report Test

- [ ] Go to Reports → Nigeria PAYE Schedule
- [ ] Set Company, Month, Year
- [ ] Click Refresh
- [ ] Each row should show: Employee, Employee TIN, RSA PIN, Gross Pay, PAYE Tax, Net Pay
- [ ] Employee TIN column pulls from the ng_tin field (not blank if TIN was set on Employee)

---

## Pension Schedule Report Test

- [ ] Go to Reports → Nigeria Pension Schedule
- [ ] Set Company, Month, Year
- [ ] Click Refresh
- [ ] Each row: Employee, RSA PIN, PFA, Employee Contribution (8%), Employer Contribution (10%), Total

---

## E-Invoice Settings Test

- [ ] Search "NRS E-Invoice Settings"
- [ ] Confirm the form loads without error
- [ ] Confirm Sandbox URL and Production URL fields are pre-filled
- [ ] (If credentials available) Set Environment = Sandbox, fill Client ID / Secret / API Key
- [ ] Save — confirm no error

---

## NRS ATRS Log Test

- [ ] Go to NRS ATRS Log list (search in top bar)
- [ ] If any POS Invoices have been submitted since ATRS was enabled, records should appear here
- [ ] Each record should show: Document (POS Invoice name), Status, Payment Code (if Submitted), Submitted At

---

## Error Log Sanity Check

- [ ] Go to: Tools → Error Log
- [ ] Filter by App = zinye_ng (or search "Nigeria" / "ATRS" / "PAYE")
- [ ] There should be no unexpected errors

---

## Post-Checklist Actions

If any item fails:
1. Note the exact DocType, field, and error message
2. Check Error Log for details
3. For field-related issues: run `bench --site [site] migrate` and retest
4. For PAYE/salary issues: verify the salary structure assignment on the employee
