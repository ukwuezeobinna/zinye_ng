# Zinye Nigeria Compliance — User Guide

**App:** `zinye_ng` · **Framework:** Frappe / ERPNext v15+  
**Regulation:** Nigeria Tax Act 2025 (Act No. 7, gazetted 26 June 2025, effective 1 Jan 2026)  
**Authority:** Nigeria Revenue Service (NRS, formerly FIRS)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Initial Setup](#2-initial-setup)
3. [PAYE (Pay As You Earn)](#3-paye-pay-as-you-earn)
4. [Pension, NHF, NHIS, NSITF, ITF](#4-pension-nhf-nhis-nsitf-itf)
5. [Withholding Tax (WHT)](#5-withholding-tax-wht)
6. [VAT (Value Added Tax)](#6-vat-value-added-tax)
7. [NRS E-Invoicing (FIRSMBS / MBS)](#7-nrs-e-invoicing-firsmbs--mbs)
8. [NRS ATRS (B2C POS Receipts)](#8-nrs-atrs-b2c-pos-receipts)
9. [Compliance Reports](#9-compliance-reports)
10. [NDPR — Data Subject Requests](#10-ndpr--data-subject-requests)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Overview

`zinye_ng` adds Nigeria statutory compliance to ERPNext. It handles:

| Area | What it does |
|------|-------------|
| **PAYE** | Recomputes payroll tax using the 2025 tax bands automatically on every salary slip |
| **Pension** | 8% employee + 10% employer deduction via salary components (PRA 2014) |
| **NHF / NHIS / NSITF / ITF** | All statutory contributions computed as salary components |
| **WHT** | Auto-fills withholding tax rate on Purchase Invoices; creates Journal Entry on submission |
| **VAT 7.5%** | Pre-configured tax template; VAT Return report included |
| **NRS e-Invoicing** | B2B pre-clearance submission to NRS FIRSMBS (IRN + CSID) |
| **NRS ATRS** | B2C real-time POS receipt fiscalization |
| **NDPR** | Data Subject Request tracking and SLA warnings |

---

## 2. Initial Setup

### 2.1 Company Settings

Go to **Accounting → Company** and open your company record. Scroll to the **Nigeria Compliance** section:

| Field | Description | Required For |
|-------|-------------|--------------|
| TIN (Tax Identification Number) | 12-digit NRS TIN | PAYE, WHT, e-invoice |
| RC Number (CAC) | CAC registration number | e-invoice |
| VAT Registration Number | NRS VAT registration | VAT Return |
| Registered State | State where PAYE is remitted | PAYE schedule |
| State IRS Code | Employer code from your State IRS | PAYE remittance |
| ITF Liable | Tick if you have 5+ employees OR ₦50M+ annual payroll | ITF deduction |

### 2.2 Employee Settings

On each **Employee** record, in the **Nigeria Compliance** section:

| Field | Description |
|-------|-------------|
| Employee TIN | Employee's personal NRS TIN |
| NHF Number | National Housing Fund registration number |
| RSA PIN | PenCom Retirement Savings Account PIN |
| Pension Fund Administrator | Employee's chosen PFA name |
| Exempted from NHF | Tick for employees earning less than ₦3,000/month |

### 2.3 Salary Structure

The app automatically creates **"NG Employee Standard"** salary structure for your company on first `bench migrate`. Assign it to employees via **Payroll → Salary Structure Assignment**.

The structure includes:

**Earnings**
- NG - Basic Salary
- NG - Housing Allowance
- NG - Transport Allowance
- NG - Pensionable Base *(statistical — sum of above three, used for pension calculation)*
- NG - Pension Employer *(statistical — 10% of pensionable base, employer cost)*
- NG - NSITF *(statistical — 1% of gross pay, employer cost)*

**Deductions**
- NG - Pension Employee *(8% of pensionable base)*
- NG - NHF *(2.5% of basic salary)*
- NG - NHIS *(5% of gross pay)*
- NG - PAYE Tax *(computed automatically — see Section 3)*

> **Statistical components** appear on the payroll summary for reporting but do not reduce net pay.

---

## 3. PAYE (Pay As You Earn)

### How It Works

PAYE is computed **automatically** when a Salary Slip is saved. You do not need to enter the tax amount manually.

**Tax Bands (Nigeria Tax Act 2025, s.58 / Fourth Schedule — annual):**

| Annual Taxable Income | Rate |
|----------------------|------|
| First ₦800,000 | 0% |
| Next ₦2,200,000 | 15% |
| Next ₦9,000,000 | 18% |
| Next ₦13,000,000 | 21% |
| Next ₦25,000,000 | 23% |
| Above ₦50,000,000 | 25% |

**Section 30 Deductions** (reduce taxable income before bands are applied):
- Pension (employee contribution)
- NHF contributions
- NHIS contributions
- Home loan interest *(if entered on the salary slip)*
- Life assurance premiums *(if entered)*
- Rent relief: 20% of annual rent paid, capped at ₦500,000

**Minimum Wage Exemption (s.162(1)(t)):** Employees earning ≤ ₦70,000/month pay zero PAYE. The system displays a blue notification when this applies.

### Worked Example

| | Monthly | Annual |
|--|---------|--------|
| Basic Salary | ₦150,000 | ₦1,800,000 |
| Housing Allowance | ₦50,000 | ₦600,000 |
| Transport Allowance | ₦30,000 | ₦360,000 |
| **Gross Pay** | **₦230,000** | **₦2,760,000** |
| Pension Employee (8%) | ₦18,400 | ₦220,800 |
| NHF (2.5% of basic) | ₦3,750 | ₦45,000 |
| **Taxable Income** | | **₦2,494,200** |
| PAYE Computation: | | |
| ₦800,000 @ 0% | | ₦0 |
| ₦1,694,200 @ 15% | | ₦254,130 |
| **Annual PAYE** | | **₦254,130** |
| **Monthly PAYE** | **₦21,177.50** | |

### Viewing PAYE on a Salary Slip

1. Go to **Payroll → Salary Slip**
2. Open any submitted slip
3. The **Deductions** table will show **NG - PAYE Tax** with the computed amount
4. Run the **Nigeria PAYE Schedule** report for the monthly remittance file

---

## 4. Pension, NHF, NHIS, NSITF, ITF

These are all computed as salary components using formulas — ERPNext calculates them during payroll processing.

### Rates

| Contribution | Rate | Base | Who Pays |
|-------------|------|------|----------|
| Pension (Employee) | 8% | Basic + Housing + Transport | Employee |
| Pension (Employer) | 10% | Basic + Housing + Transport | Employer (statistical) |
| NHF | 2.5% | Basic Salary | Employee |
| NHIS | 5% | Gross Pay | Employee |
| NSITF | 1% | Gross Pay | Employer (statistical) |
| ITF | 1% | Annual Payroll | Employer (annual, if liable) |

### Nigeria Payroll Settings

Go to **Payroll → Nigeria Payroll Settings** to view the configured rates. These rates are pre-set to the statutory values but can be adjusted if regulations change.

### Pension Schedule Report

Go to **Reports → Nigeria Pension Schedule**. Filter by:
- Company
- Month / Year

The report shows: Employee, RSA PIN, PFA, Employee Contribution, Employer Contribution, Total. This is the file you send to each PFA.

---

## 5. Withholding Tax (WHT)

### Auto-Fill on Purchase Invoice

When you create a Purchase Invoice and select a **Supplier** who has a WHT Category set on their record:

1. The **Withholding Tax** section expands automatically
2. **WHT Applicable** is ticked
3. **WHT Rate (%)** is filled with the default rate for that category

You can override the rate before saving.

### Setting a Supplier's WHT Category

1. Go to **Buying → Supplier → [your supplier]**
2. In the **Nigeria Compliance** section, set **WHT Category**

| Category | Default Rate |
|----------|-------------|
| Professional / Consultancy Fees | 10% |
| Management / Technical Fees | 10% |
| Construction / Building | 5% |
| Rent / Lease | 10% |
| Royalties | 10% |
| Dividends | 10% |
| Interest (Financial Institution) | 10% |
| Commission / Agency Fees | 10% |
| Contracts (Supply of Goods) | 5% |
| Directors Fees | 10% |

### WHT Journal Entry

When a Purchase Invoice with WHT is **submitted**, the system automatically creates a Journal Entry:

```
Dr  Accounts Payable (Supplier)    WHT Amount
Cr  WHT Payable (Liability)        WHT Amount
```

This reduces the net amount due to the supplier. A green alert confirms the JE number.

> **Prerequisite:** Your Chart of Accounts must include an account named **"WHT Payable"** (Account Type: Payable). If it is missing, a log error is recorded and the JE is skipped.

### WHT Schedule Report

Go to **Reports → Nigeria WHT Schedule**. This lists all WHT deductions for the period — use it for your monthly NRS remittance (due by 21st of following month).

---

## 6. VAT (Value Added Tax)

### Setting Up VAT on Sales Invoices

The app includes a pre-configured **VAT 7.5% (Nigeria)** account. Add it to your **Sales Taxes and Charges Template**:

1. Go to **Accounting → Sales Taxes and Charges Template → New**
2. Add a row: Account = **VAT 7.5% (Nigeria)**, Rate = **7.5**, Type = **On Net Total**
3. Name it **"Nigeria VAT 7.5%"** and set it as default for Nigerian customers

### VAT Return Report

Go to **Reports → Nigeria VAT Return**. Filter by company and date range.

The report shows:
- **Output VAT** — VAT collected on Sales Invoices (with customer TIN for B2B)
- **Input VAT** — VAT paid on Purchase Invoices (claimable if VAT-registered)
- **VAT Payable** — Output minus Input (remit to NRS by 21st of following month)

---

## 7. NRS E-Invoicing (FIRSMBS / MBS)

### What It Does

Every Sales Invoice to a **VAT-registered buyer (B2B)** must be submitted to NRS FIRSMBS for pre-clearance before the invoice is legally valid. The system:

1. On Sales Invoice submission → sends the invoice to NRS in the background
2. NRS validates and returns an **IRN** (Invoice Reference Number) and **CSID** (Cryptographic Stamp Identifier)
3. The IRN and CSID are stored on the Sales Invoice and on a **Nigeria E-Invoice** record

### Configuration

Go to **NRS E-Invoice Settings** (search in the top bar):

| Field | Description |
|-------|-------------|
| Enabled | Turn on/off FIRSMBS submission |
| Environment | Sandbox (for testing) / Production |
| Sandbox API Base URL | Pre-filled; update after confirming from FIRSMBS portal |
| Production API Base URL | Pre-filled; update after confirming from FIRSMBS portal |
| Client ID | OAuth 2.0 client ID from FIRSMBS developer portal |
| Client Secret | OAuth 2.0 client secret (stored encrypted) |
| API Key | Sent as `X-API-Key` header on all requests |

> **Registration:** Register at [https://einvoice.firs.gov.ng](https://einvoice.firs.gov.ng) as a System Integrator to obtain credentials. Contact: community.nrsmbs.com for the developer community.

### Customer Setup for B2B

On each **Customer** record:
- Set **TIN** (Nigeria Compliance section) — invoices to customers with a TIN are treated as B2B and submitted to FIRSMBS
- Set **RC Number** (optional, for the payload)

### Viewing E-Invoice Status

On a submitted **Sales Invoice**, scroll to the **NRS e-Invoice** section:

| Field | Meaning |
|-------|---------|
| IRN | Invoice Reference Number (issued by NRS within 2h of submission) |
| CSID | Cryptographic Stamp Identifier |
| NRS Status | Not Required / Pending / Submitted / Cleared / Failed |

For a full audit trail, go to **Nigeria E-Invoice** list and open the record linked to the invoice. It shows the full JSON payload sent and the NRS response.

### IRN Status Polling

An hourly background job checks NRS for the final status of all **Submitted** e-invoices and updates them to **Cleared** once NRS validates them (NRS has up to 2 hours to validate under the pre-clearance model).

---

## 8. NRS ATRS (B2C POS Receipts)

### What It Does

Every POS Invoice (B2C receipt) must be submitted to **NRS ATRS** (Automated Tax Remittance System) in real-time for fiscalization. The system submits in the background immediately after a POS Invoice is submitted.

### Configuration

Go to **NRS ATRS Settings** (search in the top bar):

| Field | Description |
|-------|-------------|
| Enabled | Turn on/off ATRS submission |
| Environment | Development / Production |
| Client ID | OAuth 2.0 client ID |
| Client Secret | OAuth 2.0 client secret |
| Username | ATRS portal username |
| Password | ATRS portal password |
| VAT Number | Business VAT registration number |
| Business Place | ATRS business place code |
| Business Device | ATRS business device code |

### Viewing ATRS Submission Status

Go to the **NRS ATRS Log** list. Each record shows:

| Field | Description |
|-------|-------------|
| Document | The POS Invoice name |
| Status | Submitted / Failed |
| Payment Code | UID returned by ATRS (proof of fiscalization) |
| Submitted At | Timestamp of successful submission |
| Error Message | Reason for failure (if Status = Failed) |

Failed submissions are **automatically retried daily**. Check the ATRS Log for persistent failures.

---

## 9. Compliance Reports

All reports are accessible from **Reports** in the top navigation, or via **Nigeria** module.

| Report | Purpose | Due Date |
|--------|---------|---------|
| Nigeria PAYE Schedule | Monthly employee PAYE remittance file | 10th of following month |
| Nigeria Pension Schedule | PFA remittance file (PenCom format) | 7 working days after payroll |
| Nigeria WHT Schedule | WHT remittance schedule by supplier | 21st of following month |
| Nigeria VAT Return | Output/Input VAT and VAT Payable | 21st of following month |

### Running a Report

1. Go to **Reports → [Report Name]**
2. Set filters: **Company**, **Month**, **Year** (or **From Date / To Date** for VAT/WHT)
3. Click **Refresh**
4. Use **Export** to download as Excel or CSV for submission

---

## 10. NDPR — Data Subject Requests

The app tracks data subject requests under the **Nigeria Data Protection Regulation (NDPR)**.

### Creating a Request

Go to **Nigeria Data Subject Request → New**:

| Field | Description |
|-------|-------------|
| Requester Name | Full name of the data subject |
| Request Type | Access / Correction / Deletion / Portability / Objection |
| Date Received | Date the request was received |
| Status | Pending → In Progress → Completed / Rejected |

### SLA Warnings

A daily background job sends warnings when requests are approaching or past their SLA deadline (30 days under NDPR). Check your email notifications.

---

## 11. Troubleshooting

### PAYE Not Computing

**Symptom:** NG - PAYE Tax row shows ₦0 or is missing from the Salary Slip.

**Check:**
1. Does the Salary Slip have an **NG - PAYE Tax** row in Deductions? If not, it's not in the salary structure — check the structure assignment.
2. Is the employee earning ≤ ₦70,000/month? If so, PAYE = 0 is correct (minimum wage exemption).
3. Is `gross_pay` populated? If the slip has no earnings rows, gross pay will be 0.

---

### WHT Journal Entry Not Created

**Symptom:** Purchase Invoice submitted but no WHT JE appears.

**Check:**
1. Is **WHT Applicable** ticked on the invoice?
2. Is the **WHT Rate (%)** greater than 0?
3. Does a **WHT Payable** account exist in the company's Chart of Accounts?
4. Check **Error Log** (Tools → Error Log) for "Nigeria WHT" entries.

---

### E-Invoice Status Stuck at "Submitted"

**Symptom:** NRS Status on Sales Invoice remains "Submitted" after 2 hours.

**Check:**
1. Go to **Nigeria E-Invoice** and open the linked record
2. Check the **Response** field — does it contain an error?
3. Check **NRS ATRS Settings** (if using sandbox) — are the credentials correct?
4. The hourly polling job checks status — check **Scheduled Job Log** for "poll_pending_einvoices" errors.

---

### ATRS Submission Failed

**Symptom:** NRS ATRS Log shows Status = Failed.

**Check:**
1. Open the ATRS Log record and read **Error Message**
2. Common causes: invalid credentials, incorrect VAT number/business device code, network timeout
3. Failed submissions are retried automatically the next day
4. To retry manually: go to the ATRS Log record and click **Retry** (if visible)

---

### Custom Fields Not Appearing

**Symptom:** The Nigeria Compliance section does not appear on Company/Employee/Supplier etc.

**Fix:** Run `bench migrate` on your site — this triggers `after_migrate` which calls `create_nigeria_custom_fields()`.

```bash
bench --site yoursite.example.com migrate
```

---

### Running the Test Suite

To verify the compliance calculations on your server:

```bash
# Unit tests — no fixtures required, runs in seconds
bench --site yoursite.example.com run-tests --app zinye_ng \
      --module zinye_ng.nigeria.tests.test_paye

bench --site yoursite.example.com run-tests --app zinye_ng \
      --module zinye_ng.nigeria.tests.test_wht

bench --site yoursite.example.com run-tests --app zinye_ng \
      --module zinye_ng.nigeria.tests.test_salary_slip_hook

# Integration tests — require fixtures and a Nigeria company
bench --site yoursite.example.com run-tests --app zinye_ng \
      --module zinye_ng.nigeria.tests.test_setup
```

---

*Last updated: May 2026 · Nigeria Tax Act 2025 (Act No. 7)*
