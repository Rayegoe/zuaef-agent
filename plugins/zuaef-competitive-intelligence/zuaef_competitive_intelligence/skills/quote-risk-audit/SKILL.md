---
name: quote-risk-audit
description: "Bicycle/e-bike OEM quote profit audit. Use when the user brings an RFQ, quote sheet, BOM or cost sheet and needs a quote-risk judgment: role confirmation, material intake, BOM extraction, evidence status, anomaly checks, Floor/Safe/Target pricing, CBU vs CKD, no-go conditions and a boss-readable report."
---

# Quote Risk Audit - Bicycle / E-bike Quote Profit Audit

> Turn quote material into a risk judgment a business owner can act on.

## Core Beliefs

```text
A quote is not a cost sheet; a quote is a trade decision.
A quote is never a single number; it is a set of conditions.
```

## Execution Flow (9 steps)

### Step 0: Confirm our role

This is the premise of the whole cost model. Skipping it invalidates everything downstream.

Decide whether the customer's price sheet is our **selling price** or our **purchasing cost**:

| Role | Meaning | Cost model | Signals |
|---|---|---|---|
| Factory | we build | decompose BOM into cost | the price sheet is ours; "Dear Supplier" |
| Trader | we buy and resell | supplier price = purchase cost | the customer brings someone else's sheet |
| Unclear | cannot decide | **stop and ask** | contradictory or missing signals |

**Iron rule: when unsure, ask the owner or sales. Do not guess, do not default. If no answer is available, mark the report BLOCKED.**

### Step 1: Collect materials

Confirm at minimum: customer email, product spec, BOM or supplier quote, target market, order quantity.
Mark what is missing; never invent it. Default Incoterm FOB (marked assumed); default payment 30%+70% (marked assumed).

### Step 2: Extract order facts

Product type, quantity, target market, Incoterm, lead time, payment expectation, certification requirements, customization.
**Quantity and target market must be right** - everything downstream depends on them.

### Step 3: Extract BOM / cost items

Per item: part name, spec, quantity, unit price, currency. **Keep the source of every cost item** (which file, which line).
Reconcile the claimed total. Costs the supplier did not quote (certification, packaging, duty) are listed as missing - **never filled with 0**.
Arithmetic (deterministic, no mental math): use the deployment's pricing tool if one is composed; otherwise compute explicitly from the formulas below and show every input, marking the result as model-computed.

### Step 4: Mark evidence status

Each cost item carries one status that decides whether it enters the calculation:

| Status | Enters calculation? |
|---|---|
| `confirmed` | yes, into Floor (direct supplier/customer evidence) |
| `estimated` | yes, into Safe (reasoned estimate) |
| `assumed` | yes, into Target (assumption, owner named) |
| `missing` | no (list the gap) |
| `conflicting` | no (two sources disagree) |
| `stale` | no (out of date) |

**Iron rule: missing / conflicting / stale never enter cost calculations.**

### Step 5: Cost and compliance anomaly checks

Compare each cost item against a baseline table **when the deployment provides one**; if no baseline is available, state "baseline comparison unavailable in this deployment" and list which items could not be checked - never fabricate a baseline verdict.

- Every cost item carries a `source_ref`; an item without a source is flagged as potential hallucination.
- Clearly-below-baseline items are suspects: omitted scope, unit error, or a one-off fee spread as unit cost.
- BOM arithmetic: itemized sum vs claimed total (2% tolerance), no negative costs, no zero quantities, consistent currency.
- Compliance: check market x product-type requirements; above threshold is an immediate no-go trigger.
- Anti-dumping (EU / China origin / rate above 30%): evaluate CKD/SKD options.
- Geo match: the price sheet's source market must match the customer's target market; a mismatch (e.g. AU sheet to EU customer) means double freight - mark BLOCKED.

Anomalies are marked `conflicting` (cost) or raised as no-go triggers (compliance).

### Step 6: Compute Floor / Safe / Target

```text
Floor Price  = Confirmed / (1 - margin)
Safe Price   = (Confirmed + Estimated + financial overlay) / (1 - margin)
Target Quote = Safe Price / (1 - discount)
```

Default target gross margin 18% (assumed). Default financial overlay: FX 2% + warranty 3% + payment 1.5% = 6.5%.

When costs conflict, compute two versions - optimistic (trust supplier) and realistic (use baseline) - and recommend the realistic one. CKD/SKD break-even and direction come from the same formulas or the deployment's tool; **CKD duty rates are never hardcoded** - mark "requires customs confirmation".

### Step 7: No-go triggers and quote conditions

No-go triggers: compliance above threshold (hard), Floor Price above the customer's target (accepting loses money), key cost missing and not estimable, infeasible lead time (soft).
Quote conditions to attach when accepting: certification at cost, lead time counted from complete material, price validity window.

**Iron rule: give a definite recommendation; do not hand the owner a multiple-choice question.** If two cost scenarios are possible, resolve with a conditional ("quote $X; if the supplier confirms Y, it drops to $Z").

### Step 8: Produce the owner-readable report

Fixed order:
1. Quote conclusion (one sentence + three prices + recommendation)
2. Cost floor (table, anomalies flagged)
3. Risk chain (four scenarios of how margin is consumed)
4. No-go triggers
5. Quote conditions
6. Information still needed from the customer
7. Next actions

Plain language. The owner does not care about schema, JSON or technical notation.
Persist the report through the deployment's report tool when one is composed
(ZUAEF competitive-intelligence: `save_work_product(kind='report')`, then
`render_report`). Otherwise deliver it in the reply and say it was not persisted.

## Usage Notes

1. Inputs: customer email / PDF / Excel / images supplied by the user.
2. Reference samples (when the deployment ships them): `examples/CASE-103-report.md` (CIF quote with missing certification), `examples/CASE-105-ckd-report.md` (CBU vs CKD).
3. Deterministic pricing / BOM arithmetic belongs to a deployment tool. This skill supplies the process, the formulas and the evidence discipline; it does not supply execution.

## Prohibited

- **Do not fabricate data** - missing stays missing.
- **Do not skip Step 0** - role unclear means BLOCKED.
- **Do not hand the owner a menu of options** - give a definite recommendation.
- **Do not hardcode CKD duty** - mark it as requiring customs confirmation.
- **Do not blur evidence status** - missing / conflicting / stale stay out of cost math.
