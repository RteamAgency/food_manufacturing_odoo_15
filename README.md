# food_manufacturing_odoo_15

Custom addons for an Odoo 15 Enterprise food-manufacturing deployment. Used as a git submodule on Odoo.sh.

## Modules (16)

| Module | Version | License | App | Notes |
|---|---|---|---|---|
| `aznut_stock` | 15.0.0.9 | AGPL-3 | yes | Stock picking customization (quality + expiry) |
| `aznut_sale_margin` | 15.0.0.1 | AGPL-3 | no (auto) | Sale margin extensions |
| `aznut_sale` | 15.0.0.16 | AGPL-3 | no | Sale + CRM + accounting reports glue |
| `aznut_mrp` | 15.0.0.82 | AGPL-3 | yes | Core MRP customization (workorder, quality, attendance) |
| `aznut_calculator` | 15.0.0.50 | AGPL-3 | yes | Product calculator + GPT chat (needs `openai`, `emoji`) |
| `aznut_calculator_sign_quote` | 16.0.0.21 | AGPL-3 | yes | Calculator + portal sign-quote flow |
| `aznut_complaint_claim` | 15.0.0.2 | AGPL-3 | yes | Complaints, claims, recalls |
| `aznut_dashboard_ceo` | 15.0.0.0.1 | AGPL-3 | yes | CEO dashboard (Chart.js) |
| `aznut_hr` | 15.0.0.1 | AGPL-3 | yes | HR employee customization |
| `aznut_maintenance` | 15.0.0.0.2 | AGPL-3 | yes | Maintenance customization + recurrence |
| `aznut_mrp_quality_video` | 15.0.0.1 | AGPL-3 | yes | Quality video upload to Google Drive / OneDrive |
| `aznut_portal` | 15.0.0.2 | AGPL-3 | yes | Portal customization (Zoom integration, sign quote) |
| `aznut_purchase` | 15.0.0.7 | AGPL-3 | no | Purchase customization |
| `aznut_quality_control` | 15.0.0.1 | AGPL-3 | yes | Quality control customization |
| `list_view_sticky_header` | 15.0.1.0.1 | LGPL-3 | no | Generic sticky header for list views |
| `stock_no_negative` | - | - | no | OCA-style: prevent negative stock |

Original author: SmartTek Solutions and Services. License: AGPL-3 (LGPL-3 for `list_view_sticky_header`).

## Install order

```
aznut_stock
aznut_sale_margin (auto-installs with sale + sale_margin)
aznut_sale
aznut_mrp                   <- depends on aznut_sale, aznut_sale_margin, mrp_account_enterprise, quality_control_worksheet
aznut_calculator            <- depends on aznut_mrp + sale_project + quality_mrp
aznut_calculator_sign_quote <- depends on aznut_calculator + aznut_sale + website_sale
aznut_dashboard_ceo
aznut_hr
aznut_purchase
aznut_mrp_quality_video
aznut_portal                <- depends on aznut_mrp + aznut_calculator_sign_quote
aznut_complaint_claim       <- standalone (sign + mrp + product_expiry)
aznut_maintenance           <- standalone (mrp_maintenance)
aznut_quality_control       <- standalone (quality_control)
list_view_sticky_header     <- standalone
stock_no_negative           <- standalone
```

## Required Odoo 15 Enterprise modules

`mrp_workorder`, `mrp_account_enterprise`, `mrp_maintenance`, `quality_control`, `quality_control_worksheet`, `quality_mrp`, `account_reports`, `sign`.

## Python dependencies

```
openai
emoji
```

See `requirements.txt`. Odoo.sh installs it automatically when this repo is mounted as a submodule.

## Usage as Odoo.sh submodule

```bash
git submodule add git@github.com:RteamAgency/food_manufacturing_odoo_15.git food_manufacturing_odoo_15
git commit -am "Add food_manufacturing_odoo_15 submodule"
git push
```

Odoo.sh auto-extends `addons-path` with the submodule root.
