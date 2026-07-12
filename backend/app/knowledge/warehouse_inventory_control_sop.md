# Warehouse Inventory Control SOP

Document owner: Warehouse Operations
Department: Warehouse
Version: 2026.1
Effective date: 2026-01-01

## Purpose

This standard operating procedure defines how warehouse teams receive stock, count inventory, classify stock status, handle low-stock risk, investigate discrepancies, and coordinate with the purchasing and customer operations teams. The procedure is intended to keep inventory data reliable enough for automated analytics, replenishment recommendations, customer promises, and agent-assisted decision making.

Inventory accuracy is a business-critical control. ProductAI and other operational systems can only make useful recommendations when warehouse transactions are recorded quickly and consistently. Staff should treat inventory events as operational records, not after-the-fact notes.

## Scope

This SOP applies to all warehouse locations, including central distribution warehouses, regional warehouses, retail backrooms, and temporary overflow storage. It applies to finished goods, returned goods, quarantined goods, damaged goods, and reserved stock.

The procedure does not replace legal compliance requirements for regulated products, hazardous goods, or controlled items. When compliance-specific procedures exist, those procedures take priority.

## Inventory Status Definitions

Available stock is inventory that is physically present, sellable, and eligible for allocation to customer orders. Reserved stock is inventory committed to existing orders, internal transfers, samples, or approved business holds. Quarantined stock is inventory that must not be sold until inspection, compliance review, quality review, or management release is complete.

Damaged stock is inventory with visible damage, suspected damage, incomplete packaging, missing accessories, or quality concerns. Defective stock is inventory that failed functional inspection or was returned due to product failure. In-transit stock is inventory that has shipped from a supplier or warehouse but has not yet been received into the destination warehouse.

Only available stock should be used when answering whether a product can be sold immediately. Reserved, quarantined, damaged, defective, and in-transit quantities may be useful for planning but should not be represented as immediately sellable.

## Receiving Procedure

Inbound shipments must be checked against purchase order or transfer documentation before stock is made available. Receiving staff should verify supplier, shipment reference, SKU, quantity, visible damage, and packaging condition.

If the received quantity matches the expected quantity and no damage is visible, stock may be received into available inventory after SKU validation. If there is a mismatch, staff must record the actual quantity and open a receiving discrepancy note. The discrepancy note should include expected quantity, received quantity, shipment reference, supplier or origin warehouse, and any visible evidence.

Damaged cartons should be photographed when possible. Staff should separate damaged units from clean units and avoid receiving damaged units into available inventory. When only outer packaging is damaged and inner product packaging is intact, a supervisor may approve available inventory after inspection.

Late receiving updates create inaccurate low-stock alerts. All normal inbound shipments should be recorded within one business day of physical arrival. Critical replenishment shipments should be recorded within four business hours.

## Putaway Procedure

After receiving, products must be placed in the correct bin, shelf, zone, or staging area. High-velocity products should be placed in pick-efficient locations when capacity allows. Heavy or fragile products must follow handling requirements defined by warehouse safety guidance.

The system location should match the physical location before the item becomes available for picking. If the warehouse uses temporary staging, the staging location must be recorded. Staff should not move products between locations without updating the system or following the batch move process.

## Cycle Counting

Cycle counts are used to maintain inventory accuracy without shutting down operations. High-value products, high-velocity products, and products with frequent discrepancies should be counted more often than slow-moving products.

Recommended count frequency:

- A-class products: weekly.
- B-class products: monthly.
- C-class products: quarterly.
- Products with open discrepancy investigations: as directed by supervisor.
- Products with stockout risk or negative availability: immediate count.

Counts should be blind where possible. Staff should count physical units before checking system quantity. If the count differs from system quantity, a recount by another staff member is required before adjustment.

## Adjustment Rules

Inventory adjustments require a reason code. Accepted reason codes include cycle count correction, receiving correction, pick short, found stock, damaged stock, return inspection, supplier shortage, internal transfer correction, and system migration correction.

Adjustments above 20 units or above 500 EUR inventory value require supervisor approval. Repeated adjustments for the same SKU and warehouse should trigger a root-cause investigation. Common causes include mispicks, unrecorded transfers, receiving errors, damaged stock not moved out of available inventory, duplicate SKUs, barcode errors, and theft.

Staff must not use inventory adjustment as a shortcut for normal receiving, return processing, order cancellation, or warehouse transfer workflows.

## Low-Stock Handling

A product is considered low stock when available stock is less than or equal to its reorder point. Low-stock alerts should be reviewed daily for active SKUs. The warehouse team should verify low-stock counts for critical products before purchasing decisions are finalized.

When low-stock risk is detected, staff should check available quantity, reserved quantity, inbound quantity, recent sales velocity, pending returns, and known supplier lead time. If the product is high velocity and supplier lead time is longer than seven days, the risk should be escalated to purchasing.

If stock is physically available but not visible in the system, staff must correct the inventory record before customer-facing teams promise availability. If stock is visible in the system but cannot be found physically, the SKU should be placed on temporary allocation hold until the discrepancy is resolved.

## Stockout Prevention

The warehouse team should communicate early when operational signals suggest stockout risk. Important signals include failed picks, repeated substitution requests, backorder growth, delayed inbound shipments, supplier short shipments, and cycle counts below system quantity.

Products with strong sales velocity and stock below reorder point should receive priority receiving and putaway when replenishment arrives. If multiple urgent shipments arrive at the same time, priority should be based on customer impact, margin, committed orders, and supplier lead time.

## Returns Handling

Returned items must not be placed into available inventory until inspected. The return condition should be recorded as unopened, opened-good, damaged, defective, or unsellable. Unopened products may return to available stock after visual inspection. Opened-good products require accessory and packaging checks. Damaged, defective, and unsellable products must be routed to quarantine, supplier claim, repair, refurbishment, or write-off.

When return volume is unusually high for a SKU, warehouse staff should report the pattern to customer operations and product management. A return rate above 8 percent over a 30-day period should trigger review when at least 20 units were sold.

## Picking Accuracy

Pickers must verify SKU, quantity, and location before confirming a pick. Barcode scanning should be used when available. Manual confirmation should be used only when scanning is unavailable and must follow the local exception procedure.

Mispicks should be recorded as operational incidents. Repeated mispicks for the same SKU may indicate confusing packaging, poor bin labeling, duplicate locations, or product master data issues.

## Quarantine Procedure

Quarantined inventory must be physically separated from available inventory. The quarantine location should be clearly marked. Quarantined goods should include a reason code and review owner. No quarantined item may be shipped, transferred, or returned to available stock without documented release.

Common quarantine reasons include suspected defect, damaged packaging, regulatory review, supplier dispute, fraud investigation, recalled product, and unknown provenance.

## Reconciliation and Reporting

Warehouse managers should review inventory discrepancy reports weekly. The review should include high-value adjustments, repeated discrepancies by SKU, negative inventory events, stockout incidents, receiving discrepancies, and quarantine aging.

Discrepancies older than seven business days should be escalated. Quarantined stock older than 30 days should be reviewed for disposal, supplier claim, refurbishment, or release.

## Agent Guidance

When answering inventory-control questions, the assistant should cite this SOP for operational rules and use SQL tools for live quantities, reorder points, sales velocity, warehouse names, product records, and returns data. The assistant should distinguish available stock from quarantined, reserved, damaged, defective, or in-transit stock when that information is available. If the database does not contain a required status field, the assistant should say so instead of pretending the data exists.
