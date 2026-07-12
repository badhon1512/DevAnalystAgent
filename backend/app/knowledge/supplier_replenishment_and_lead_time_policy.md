# Supplier Replenishment and Lead Time Policy

Document owner: Supply Planning
Department: Purchasing
Version: 2026.1
Effective date: 2026-01-01

## Purpose

This policy defines how purchasing and supply planning teams should evaluate supplier lead times, reorder urgency, safety stock, replenishment exceptions, supplier performance, and escalation rules. It supports decision making for inventory analysts, warehouse managers, customer operations, and agentic analytics workflows.

The policy is intended to work alongside live database analysis. Product, sales, inventory, warehouse, and return data should be retrieved from operational systems. Policy logic, supplier planning rules, and escalation thresholds should be retrieved from this document or other indexed company documents.

## Core Replenishment Principle

Replenishment decisions should consider more than current stock on hand. The recommended decision uses available stock, reorder point, recent sales velocity, open customer commitments, supplier lead time, inbound purchase orders, return quality, seasonality, and product criticality.

A SKU below reorder point is not automatically an emergency. A SKU above reorder point is not automatically safe. High-velocity products, long-lead-time products, strategic products, and products with committed orders may require action before they reach reorder point.

## Lead Time Definition

Supplier lead time is the expected number of calendar days between purchase order approval and warehouse receipt of sellable inventory. Lead time includes supplier processing, production or picking, export preparation when applicable, carrier transit, customs clearance when applicable, receiving, and putaway.

Planning lead time should be based on actual recent performance whenever available. If actual performance data is unavailable, the approved supplier master value should be used. If neither is available, purchasing must classify the lead time confidence as low and use conservative safety stock.

## Standard Lead Time Bands

Suppliers are classified into lead time bands:

- Local fast supplier: 1 to 3 days.
- Domestic standard supplier: 4 to 7 days.
- Regional supplier: 8 to 14 days.
- International standard supplier: 15 to 35 days.
- International long-lead supplier: more than 35 days.

Lead time band affects reorder urgency. A SKU supplied by an international long-lead supplier should be reviewed earlier than a SKU from a local fast supplier, even when both have the same quantity above reorder point.

## Reorder Trigger Rules

The standard reorder trigger is stock on hand less than or equal to reorder point. However, analysts should use projected stockout date when recent demand is available. Projected stockout date is estimated by dividing available stock by average daily unit sales, then comparing the result to supplier lead time.

If projected days of cover is less than supplier lead time plus three calendar days, replenishment should be reviewed immediately. If projected days of cover is less than supplier lead time, replenishment is urgent. If projected days of cover is less than half of supplier lead time, the issue should be escalated to the purchasing lead.

For example, if a SKU has 40 units available, sells 10 units per day, and has a supplier lead time of 8 days, it has 4 days of cover. Because 4 days is below the 8-day lead time, the SKU is urgent even if the static reorder point has not been reached.

## Safety Stock Guidance

Safety stock protects against demand variation, supplier delay, receiving delay, and quality issues. Safety stock should be higher for high-velocity products, long-lead-time products, volatile demand products, strategic customers, and suppliers with poor on-time delivery.

Safety stock may be reduced for slow-moving products, highly reliable local suppliers, products with acceptable substitutes, clearance products, and products near end of life.

When a product has a high return rate due to defects, returned quantity should not be treated as reliable safety stock until inspection confirms sellable condition. Defective or damaged returns should not reduce replenishment urgency.

## Emergency Replenishment

Emergency replenishment may be used when stockout risk is likely to affect committed orders, strategic customers, high-margin products, launch products, or compliance-critical products. Emergency replenishment options include expedited shipping, partial shipment, alternate supplier, warehouse transfer, substitute recommendation, or temporary allocation hold.

Emergency shipping should not be used automatically for every low-stock SKU. The purchasing lead should compare margin, customer impact, forecast demand, expedited freight cost, and supplier reliability.

Emergency replenishment requires approval when expedited freight cost exceeds 150 EUR, when alternate supplier cost is more than 12 percent above standard cost, or when a purchase order exceeds normal approval limits.

## Supplier Performance Rules

Supplier performance should be reviewed monthly for active suppliers. Important metrics include on-time delivery rate, average delay days, fill rate, defect rate, receiving discrepancy rate, response time, and emergency order support.

A supplier with on-time delivery below 90 percent for two consecutive months should be placed under watch. A supplier with on-time delivery below 80 percent or defect rate above 5 percent should receive corrective action review.

When supplier performance is weak, planning should increase safety stock, order earlier, split orders across suppliers, or identify alternates. Purchasing should not rely on a weak supplier for critical SKUs without an escalation plan.

## Purchase Order Prioritization

When purchasing capacity is limited, prioritize purchase orders using customer impact, projected stockout date, sales velocity, product margin, strategic importance, supplier lead time, and availability of substitutes.

Products with committed customer orders should be prioritized above speculative replenishment. Products with high daily revenue and low days of cover should be prioritized above slow-moving products, unless the slow-moving product is required for a strategic customer or compliance obligation.

## Warehouse Transfer Before Purchase

Before placing an emergency supplier order, purchasing should check whether another warehouse has excess available stock. A warehouse transfer may be preferred when transfer time is shorter than supplier lead time and when the source warehouse will remain above reorder point after transfer.

Transfers should not create a new stockout risk at the source warehouse. If the source warehouse would fall below reorder point, transfer approval must include a clear reason and replenishment plan.

## Returns and Replenishment

Returned goods should influence replenishment only after condition inspection. Unopened and opened-good returns may reduce purchase urgency once they are returned to available inventory. Damaged, defective, quarantined, or unsellable returns should not be counted as sellable supply.

If a product has high sales and high returns, purchasing should coordinate with product management and quality teams before increasing reorder quantities. The issue may be demand quality, product defect, inaccurate product description, packaging failure, or fulfillment error.

## Supplier Claims

Supplier claims should be opened when received goods are short, damaged, defective, incorrectly labeled, or materially different from the purchase order. Claims should include purchase order reference, supplier reference, SKU, expected quantity, received quantity, photos when applicable, inspection notes, and financial impact.

Claim activity should not delay urgent replenishment when customer impact is high. Purchasing may place a replacement order while the supplier claim is under review, but the duplicate supply risk should be documented.

## Approval Thresholds

Purchasing lead approval is required for emergency freight above 150 EUR, alternate supplier cost above 12 percent standard cost, purchase orders above normal approval limit, orders that intentionally exceed 90 days of forecast cover, and replenishment of products under quality review.

Finance approval is required when expedited or alternate sourcing decisions materially reduce margin on committed customer orders. Operations leadership approval is required when a replenishment decision conflicts with quarantine, recall, or compliance guidance.

## Agent Guidance

When answering replenishment questions, the assistant should retrieve this policy for lead-time and escalation rules. It should use SQL tools for live stock, reorder points, sales velocity, products, warehouses, returns, and revenue. It should not invent supplier lead times if they are not present in the database or indexed documents.

For combined analysis, the assistant should separate data evidence from policy evidence. For example, it may say that SQL shows a SKU is below reorder point and that this policy recommends escalation when projected days of cover is below supplier lead time. If supplier lead time is missing, the assistant should state that the policy requires lead time but the available data does not provide it.
