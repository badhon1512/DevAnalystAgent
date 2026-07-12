# Order Fulfillment and Customer Promise Policy

Document owner: Operations
Department: Fulfillment
Version: 2026.1
Effective date: 2026-01-01

## Purpose

This policy defines how teams should make customer availability promises, prioritize fulfillment, handle stock shortages, manage substitutions, and communicate delays. It connects inventory data, warehouse execution, customer service decisions, and purchasing escalation.

The policy applies to online, retail, and business-to-business orders. It should be used when answering questions about whether stock can be promised, when orders should be delayed, and how customer commitments should be prioritized.

## Availability Promise Rule

Customer-facing availability should be based on available sellable stock, not total physical stock. Reserved, quarantined, damaged, defective, in-transit, inspection-pending, and supplier-claim stock should not be promised as immediately available.

If the system only provides stock on hand and reorder point, the assistant or staff member should avoid claiming exact available-to-promise quantity. The correct wording is that stock-on-hand exists, but reserved, quarantined, or damaged quantities are not visible in the current data.

## Same-Day Fulfillment

Same-day fulfillment may be promised only when the item is available in the fulfillment warehouse, the order is received before the local cutoff, no fraud or payment hold exists, and the warehouse is not under operational hold.

Priority should be given to paid customer orders over internal transfers, samples, and speculative replenishment moves. Business-to-business orders with contractual service commitments may outrank ordinary retail orders when the contract requires it.

## Shortage Handling

When available stock is not enough to fulfill all demand, teams should prioritize orders using:

- Contractual customer commitment.
- Order age.
- Customer value.
- Margin or revenue impact.
- Product criticality.
- Availability of substitute SKUs.
- Expected replenishment date.
- Whether the customer already experienced a previous delay.

Staff should not split limited stock randomly. The decision should be documented when customer impact is material.

## Substitution Rules

Substitutions require customer approval unless a contract or marketplace rule explicitly allows equivalent substitutions. A substitute should match essential product function, quality tier, compatibility, and customer requirement.

Do not substitute a lower-quality item without customer consent. If the substitute is more expensive and the substitution is caused by company error or stockout, team lead approval may allow price match. If the customer voluntarily upgrades, the customer pays the difference.

Substitution is not allowed for personalized, regulated, compliance-critical, or compatibility-sensitive products unless the customer explicitly approves the exact replacement.

## Backorder and Delay Communication

When an order cannot ship on time, customer service should communicate the delay reason, expected next update, available options, and whether cancellation is allowed.

Acceptable customer options include wait for replenishment, partial shipment, substitution, warehouse transfer, store credit, refund, or cancellation. The team should not promise a replenishment date unless it is supported by purchasing or supplier information.

If supplier lead time is unknown, the message should say that timing is pending supplier confirmation.

## Warehouse Transfer Rules

Warehouse transfer may be used when another warehouse has excess available stock and transfer time is shorter than supplier replenishment. The source warehouse must remain above reorder point unless operations leadership approves the exception.

Transfers for strategic customers, high-margin orders, launch products, or stockout recovery should be prioritized over convenience transfers.

## Cancellation Rules

Customers may cancel unshipped orders unless the product is personalized, special order, already packed, already handed to carrier, or subject to contract restrictions. If cancellation happens after picking but before shipment, warehouse must release reserved stock back to available inventory after verification.

Cancelled orders should not be counted as shipped demand. Analytics should separate cancellation from return activity.

## Fulfillment Error Handling

Fulfillment errors include wrong item shipped, wrong quantity shipped, duplicate shipment, missing accessory, damaged packaging caused during handling, and shipment sent to incorrect destination due to internal error.

When the company caused the error, customer service should prioritize correction through replacement shipment, prepaid return label, refund, or expedited exchange depending on customer preference and inventory availability.

Shipping fees should be refunded when the fulfillment error caused the return or delay.

## Agent Guidance

When answering fulfillment promise questions, the assistant should use SQL tools for product, warehouse, inventory, sales, and returns data. It should cite this policy for customer promise, shortage prioritization, substitution, delay communication, and transfer rules. If the current database cannot distinguish available, reserved, damaged, quarantined, or in-transit stock, the assistant should state that limitation clearly.
