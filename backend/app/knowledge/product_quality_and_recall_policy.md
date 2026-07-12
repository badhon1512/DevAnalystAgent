# Product Quality and Recall Policy

Document owner: Product Operations
Department: Quality
Version: 2026.1
Effective date: 2026-01-01

## Purpose

This policy defines how product quality issues, defect signals, supplier quality problems, quarantine decisions, customer-impacting defects, and recall-like events should be identified and escalated. It supports customer operations, warehouse operations, purchasing, and analytics workflows.

The policy is designed for situations where returns, complaints, receiving discrepancies, or warehouse inspections indicate that a product may not be safe, reliable, correctly described, or sellable.

## Quality Signal Sources

Quality issues may be detected through customer returns, product reviews, support tickets, warehouse inspections, supplier receiving checks, sales decline, repeated exchanges, carrier damage reports, or manual staff observations.

Operational teams should treat the following as quality signals:

- Return reason includes defective, damaged, not as described, missing parts, safety concern, or repeated failure.
- Product return rate is above 8 percent over 30 days with at least 20 units sold.
- Defect-related return rate is above 3 percent over 30 days with at least 20 units sold.
- Warehouse inspection finds repeated packaging damage for the same SKU.
- Supplier receiving discrepancy repeats for the same SKU or supplier.
- Customer service receives three or more similar complaints for the same SKU within seven days.

Signals should be investigated before assuming the cause. A high return rate may indicate product defect, unclear product description, shipping damage, wrong item fulfillment, poor packaging, or customer expectation mismatch.

## Quarantine Triggers

Warehouse teams must quarantine stock when there is credible risk that available inventory may be defective, unsafe, mislabeled, counterfeit, contaminated, missing critical accessories, or materially different from product data.

Quarantine is required when:

- A recall or safety warning is issued.
- Serial numbers do not match expected product records.
- Multiple units fail the same inspection.
- Supplier shipment includes material discrepancy.
- Returned items show repeated identical defect.
- Packaging or labeling creates compliance risk.
- Product condition cannot be verified.

Quarantined stock must not be sold, transferred, exchanged, or returned to available inventory until the review owner documents a release decision.

## Quality Investigation Workflow

The investigation owner should collect available evidence before deciding corrective action. Evidence may include sales volume, return count, return reasons, defect descriptions, photos, warehouse inspection notes, supplier batch information, purchase order references, customer complaints, and affected warehouses.

The investigation should answer:

- What SKU or product group is affected?
- Which warehouses or channels are affected?
- What customer impact has occurred?
- Is the issue product quality, packaging, fulfillment, carrier damage, or product data?
- Is available inventory safe and sellable?
- Should stock be quarantined, inspected, relabeled, repaired, returned to supplier, or written off?

If evidence is incomplete, the investigation should remain open rather than inventing a root cause.

## Severity Levels

Severity 1 applies when there is potential safety, regulatory, contamination, counterfeit, or recall risk. Stop sale and quarantine are required immediately.

Severity 2 applies when the product may be materially defective or repeatedly failing normal use. Quarantine or controlled release may be required depending on evidence.

Severity 3 applies when the issue affects customer satisfaction but does not create safety or major functionality risk. Examples include unclear instructions, minor cosmetic issues, packaging complaints, or non-critical missing accessories.

Severity 4 applies when the issue is informational or isolated. Monitor and document, but do not quarantine unless further signals appear.

## Recall-Like Actions

The company may perform a formal recall only when required by law, supplier instruction, regulator notice, or executive decision. A recall-like operational hold may still be used before a formal recall decision.

Recall-like actions can include stop sale, customer notification, warehouse quarantine, supplier claim, marketplace listing hold, product page warning, exchange campaign, or disposal instruction.

Executive approval is required before sending customer-wide recall messaging unless legal or compliance teams require immediate notice.

## Supplier Quality Claims

Supplier quality claims should be opened when goods are defective, damaged, short, mislabeled, non-conforming, or materially different from purchase order specification. Claims should include SKU, supplier, purchase order, affected quantity, photos or inspection notes, defect description, customer impact, and requested remedy.

Supplier claim activity should not delay customer recovery when the customer impact is clear. Customer refund or exchange decisions should follow the return policy while supplier recovery is handled separately.

## Release From Quarantine

Stock can be released from quarantine only after the review owner documents the reason. Acceptable release reasons include passed inspection, supplier documentation confirms no issue, affected batch isolated, packaging replaced, label corrected, missing accessory added, or false alarm confirmed.

Released stock must be updated in the inventory system before it is promised to customers.

## Agent Guidance

When answering quality or recall questions, the assistant should use this policy for escalation, quarantine, severity, and investigation rules. It should use SQL tools for live products, sales, returns, warehouses, and inventory data. If the database does not contain complaint, serial, batch, or quarantine fields, the assistant should say that those details are not available from the current data model.
