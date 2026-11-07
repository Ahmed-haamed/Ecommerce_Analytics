# Discussion notes

## Opening and business context · 30 seconds

Management needs a joined view of sales, product profit, customer behavior and fulfillment. The extract contains 420 unique customers, 1,350 unique orders and product lines covering 1 January–27 September 2026. I built a reproducible pipeline and a dashboard that connects the tables at their proper grain.

## Methodology and key decisions · 45 seconds

I removed 8 exact customer duplicates, 12 order duplicates and 15 item duplicates. Identical item lines might represent legitimate repeated lines because there is no line ID. Their supplied sales total EGP 4,375.19 across all statuses, so obtaining a source line ID is a priority. This total is a duplicate sensitivity measure, not an estimate of missing revenue.

Nineteen invalid numeric lines affect 18 orders. Instead of silently repairing prices or treating partial orders as complete, I excluded those entire orders from financial calculations and retained them for operational counts. Ten of the affected orders are Delivered. The financial baseline therefore covers 1,049 of 1,059 delivered orders, or 99.1%.

I aggregated item values by Order_ID before merging into orders. Primary keys and foreign keys pass validation. Shipping totals remain at one row per order. Missing city, segment and payment labels become Unknown. Missing shipping fees remain unknown. Delivery averages use the 1,043 of 1,059 delivered orders with valid dates.

## Findings · 90 seconds

1. Delivered merchandise sales total EGP 551,169.35, with EGP 144,784.21 product profit and a 26.27% margin. AOV is EGP 525.42 across the 1,049 financially complete orders. Product profit excludes operating costs, refund adjustments and shipping.
2. Kitchenware and Drinkware generate 47.46% of delivered sales and 47.43% of product profit. Frying Pan leads individual products with EGP 70,541.30 sales and EGP 19,030.14 profit. Interpretation is that stock availability in these lines deserves investigation. Sales alone cannot establish unmet demand.
3. July has the highest delivered sales, EGP 73,807.03. August is down 19.56%, driven arithmetically by eligible order count falling from 131 to 122 and AOV falling from EGP 563.41 to EGP 486.65. This decomposition does not establish the underlying cause. September ends on the 27th and should not be compared as a complete month.
4. Social Commerce has the highest AOV at EGP 565.98 across 146 financially complete delivered orders. Its returned-or-cancelled share is 34/194 = 17.53%, versus 37/357 = 10.36% for Mobile App. These are descriptive snapshot shares, with channel mix and open orders affecting interpretation.
5. Returning customers have AOV EGP 548.23 compared with VIP at EGP 500.99. Observed repeat purchasing among delivered-order customers is 317/394 = 80.46%. Of customers labeled New, 79.5% have at least two delivered orders in this window. Supplied labels therefore need interpretation before campaign targeting.

## Prioritized recommendations · 60 seconds

1. **Data owner, first week.** Validate the 18 affected orders and request a unique item-line ID. Resolve ambiguous duplicate lines before finalizing commercial reporting. Success measure is audited financial coverage and reconciliation to the source system. Current limitation is that source invoices and correction history are unavailable.
2. **Merchandising team, next test cycle.** Audit stock availability for Kitchenware and Drinkware, then test a small Frying Pan/Thermal Flask placement or cross-sell experiment. The two categories contribute 47.46% of sales. Use a randomized comparison where feasible, measure incremental product profit per exposed customer and monitor returns. Inventory, traffic and conversion data are required before committing inventory or spend.
3. **Channel operations, next test cycle.** Investigate Social Commerce cancellation/return reasons and test an order-confirmation or product-description improvement. Its 17.53% combined share exceeds Mobile App's 10.36%, despite a higher AOV. Track matured-order return/cancellation rates and contribution after intervention cost. Channel differences may reflect product/customer mix, so compare matched cohorts or randomize within channel.

## Dashboard demonstration · 30 seconds

Start on Delivered and the full date range. Filter channel, city or segment and show the changing financial coverage. Open Products & customers to explain category contributions and repeat-rate denominators. Open Operations to compare the status mix across all statuses in the selected scope. Open the report and presentation separately from the outputs folder. Both summarize the full period.

The sales waterfall in Overview compares two complete calendar months within the date range, starting with July and August for the full extract. Each intermediate step is a category's sales difference, and the ending total reconciles to the second month. A month with no matching sales contributes zero. Partial months are omitted from the comparison selectors.

In Products & customers, click the sales sunburst to explore category and product contributions. The product bubble chart compares sales with product margin, with bubble area representing units sold. Its dotted reference line is the weighted margin of the selected products. The category filter updates both charts and the detail table. All commercial charts honor the selected order statuses, so non-delivered values must be interpreted as recorded merchandise values.

## Viva and discussion prompts

- **Most important quality issue?** Invalid item inputs and ambiguous duplicates can distort order totals. Explain quarantine, full-order exclusion and the item-line ID request.
- **Which KPI answers the profit question?** Total product profit alongside weighted product margin. Averaging row margins would weight small and large lines equally. Net business profit requires additional costs.
- **Why these charts?** Monthly lines show sequence, bars compare magnitude and stacked proportions compare status mix. The delivery sunburst shows the order mix within each channel or segment and lets the viewer click into a group. The bubble chart compares counts at each delivery duration, with bubble area representing order volume. Both use delivered orders with valid dates. Hover details provide exact counts and within-group shares. Partial months and small group denominators can mislead.
- **Strongest finding?** Product contribution is directly reconcilable to valid line totals. It supports investigating availability, with demand and inventory evidence still needed.
- **Why no forecast or causal claim?** Nine months including a partial month provide limited seasonal history. No campaign assignment or controls establish causes. A future forecast needs a longer validated history and holdout evaluation.
- **What would you improve with one more day?** Resolve the 18 orders, confirm item identities, obtain event-level order status history and inventory/return reasons, then define matured cohorts and experiment success thresholds with the business.
- **How do customer segments relate to repeat behavior?** They are supplied static labels. Observed repeat purchase uses distinct orders in this extract and changes with filters. It does not establish retention or lifetime value.
- **What would change the recommendation?** If inventory is already abundant or acquisition costs erase the observed product profit, prioritize a different test. If channel differences disappear after mix adjustment, investigate the relevant products or cohorts instead.

## Source and scope

All numerical findings derive from the supplied customers_raw.csv, orders_raw.csv and order_items_raw.csv through analysis.py. The business questions and required controls come from Ecommerce_Customer_Orders_Student_Project.pdf, pages 1–3. The business is unnamed and the extract's production provenance is not documented. Interpret results within this supplied dataset.
