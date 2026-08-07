# Company Overview and Operating Model

Document owner: Strategy and Operations
Department: Executive
Version: 2026.1
Effective date: 2026-01-01

## Purpose

This document describes what TraceStock AI sells, where it operates, how the
commercial and operational sides of the business fit together, and which
definitions are considered authoritative when different systems disagree. It is
the starting point for anyone, human or agent, who needs context before
interpreting sales, inventory, returns, or branch performance data.

## Business Summary

TraceStock AI is a European consumer electronics and lifestyle retailer
operating a mixed physical and digital model. The company buys finished goods
from a supplier base, holds them across four distribution sites in Germany, and
sells them through four channels. Revenue is recorded in euros. The company does
not manufacture its own products and does not operate outside the euro area.

The commercial strategy rests on three ideas. First, a deliberately narrow
catalogue, so that depth of stock matters more than breadth of assortment.
Second, a strong seasonal tilt, because a meaningful share of the catalogue is
weather-sensitive. Third, operational transparency, meaning every number shown
to a customer or a manager must be traceable to a recorded transaction.

## Distribution Network

The company operates four sites. Each has a distinct role, and they are not
interchangeable.

| Site | City | Primary role | Notes |
|---|---|---|---|
| Berlin Hub | Berlin | Central hub and overflow | Largest site; absorbs overflow from other sites |
| Frankfurt DC | Frankfurt | Distribution centre | Main inbound receiving point for imported goods |
| Hamburg Warehouse | Hamburg | Northern coverage | Serves northern regions and coastal demand |
| Munich Fulfillment | Munich | Southern fulfilment | Highest share of direct-to-customer picking |

Stock is held per site, not pooled. A product being available nationally does
not mean it is available at a given site, and availability questions must always
be answered per site unless the question is explicitly about total stock.

## Sales Channels

Four channels are recorded. They differ in margin, return behaviour, and
customer expectations, so channel should never be ignored when comparing
performance.

- **online:** the company's own storefront. Highest volume, moderate margin,
  moderate return rate. Customers expect next-day or two-day delivery.
- **retail:** physical branch sales. Lower return rates because customers
  inspect goods before purchase. Margin is higher but volume is capped by
  footfall.
- **marketplace:** third-party platforms. Highest volume variance and the
  highest return rate. Marketplace fees compress margin significantly, so
  marketplace revenue is not comparable to online revenue at face value.
- **b2b:** business customers buying in quantity. Lowest return rate, lowest
  margin percentage, largest average order value. Payment terms differ from
  consumer channels.

When a report compares channels without adjusting for these differences, the
comparison should be labelled as gross revenue rather than profitability.

## Product Categories

The catalogue is organised into ten categories. Five are weather-sensitive and
five are broadly stable through the year. This split drives most of the
company's planning behaviour.

**Weather-sensitive**

- Air Conditioners
- Space Heaters
- Rain Jackets
- Sunscreen
- Running Shoes

**Stable**

- Laptops
- Smartphones
- Headphones
- Coffee Machines
- Office Chairs

Weather-sensitive categories can move by several multiples of their baseline in
a single week. Stable categories move with promotions, product launches, and
general consumer demand rather than with conditions outside. Any forecast,
stock recommendation, or performance explanation that treats these two groups
identically is considered incomplete.

## Authoritative Definitions

When systems or people disagree, these definitions win.

**Revenue** is the recorded sale value in euros at the point the sale is written
to the sales record, excluding later refunds. Revenue is never restated
retrospectively when a return occurs; returns are reported separately.

**Units sold** is the recorded quantity on the sale, not the number of order
lines and not the number of orders.

**Stock on hand** is the physical count recorded at a site, including units that
are reserved but not yet dispatched. It excludes quarantined stock and excludes
units in inbound transit.

**Reorder point** is the stock level at or below which replenishment should be
triggered for that product at that site. It is set per product per site and is
not a company-wide constant.

**Low stock** means stock on hand is at or below the reorder point. It does not
mean zero, and it does not by itself mean the product is unavailable.

**Return rate** is returned units divided by sold units over the same period. It
is expressed against units, never against revenue, unless the report explicitly
says otherwise.

## Fiscal and Reporting Calendar

The fiscal year matches the calendar year. Reporting periods are calendar
months. Weekly operational reviews run on Mondays and cover the preceding seven
days. Quarterly business reviews cover calendar quarters.

Comparisons described as "versus previous period" mean the immediately preceding
period of equal length, not the same period in the prior year. Year-on-year
comparisons must be labelled explicitly as such, because the company's seasonal
categories make period-on-period and year-on-year comparisons tell very
different stories.

## Core Operating Metrics

The following are reviewed weekly and are the metrics most often asked about.

- Revenue for the trailing 30 days, with the change against the preceding 30 days
- Units sold across all channels
- Count of SKUs at or below reorder point, by site
- Return rate in units, with the leading return reasons
- Stock coverage per site, expressed as stock on hand against reorder point

A site whose coverage falls below 80 percent, or which has eight or more SKUs at
or below reorder point, is treated as high risk. Between 80 and 130 percent
coverage, or three to seven low-stock SKUs, is treated as medium risk. Anything
better is low risk.

## Escalation Ownership

- Stock and replenishment questions are owned by Supply Planning.
- Customer-facing policy questions are owned by Customer Operations.
- Physical stock accuracy is owned by Warehouse Operations.
- Product defects and safety concerns are owned by Quality.
- Pricing and margin decisions are owned by Commercial.

Any question that crosses two of these areas defaults to the owner of the
customer-visible outcome.

## Document Control

| Field | Value |
|---|---|
| Version | 2026.1 |
| Effective date | 2026-01-01 |
| Last reviewed | 2026-01-01 |
| Next review due | 2027-01-01 |
| Owner | Strategy and Operations |
| Approved by | Managing Director |
| Classification | Internal |

This document is reviewed annually, and sooner if a change in law, supplier
arrangement, or operating practice makes part of it inaccurate. The version
published internally is the controlled copy; printed copies are uncontrolled.
Proposed changes go to the document owner.
