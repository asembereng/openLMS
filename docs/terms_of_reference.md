# Terms of Reference

## Add-On: Loyalty & Referral Module

### Project: A&F Laundry Services
**Revision Date:** 2025-07-03

---

### 1. Purpose
Introduce a configurable, rule-based Loyalty & Referral Module that is tightly integrated with Orders, Customers, POS, Expenses, and Reporting. The module must let an Admin create rules that award points, coupons, discounts, tier upgrades, or free services based on:

- **Order count** (e.g., every 5 orders)
- **Order frequency** (e.g., 3 orders in 30 days)
- **Spend amount** (e.g., GMD 2,000 lifetime or rolling window)
- **Successful referrals** (new customer completes first paid order)

---

### 2. Non-Functional Goals
| Goal           | Detail                                                                 |
|----------------|-------------------------------------------------------------------------|
| **Configurable** | All rules & rewards editable in Django admin (or a dedicated “Loyalty Settings” UI). |
| **Real-time**   | Rules evaluated immediately after `Order.save()`.                     |
| **Auditable**   | Points / coupons logged with user + timestamp.                        |
| **Extensible**  | JSON-based rule schema so future triggers (e.g., birthday) need no migrations. |
| **Low Coupling**| Module lives in `loyalty` Django app; interacts via well-defined service layer. |

---

### 3. Functional Requirements
#### 3.1 Rule Management (Admin)
CRUD interface for `LoyaltyRule` objects.

**Rule fields:**
- `name` — string
- `trigger_type` — enum {ORDER_COUNT, FREQUENCY, SPEND, REFERRAL}
- `config` — JSON (schema below)
- `reward` — JSON (schema below)
- `is_active` — bool
- `created_at`, `updated_at`

**Soft-delete only** (keep past orders valid).

#### 3.1.1 Trigger JSON Schema (examples)
```jsonc
// Order Count
{ "threshold": 5 }                 // 5th order rewards
// Frequency
{ "n_orders": 3, "n_days": 30 }    // 3 orders within 30 days
// Spend
{ "amount": 2000, "window_days": 0 } // lifetime if 0
// Referral
{ "minimum_order_value": 300, "cap_monthly": 1000 }
```

#### 3.1.2 Reward JSON Schema (examples)
```jsonc
// Points
{ "type": "POINTS", "amount": 100 }
// Discount coupon
{ "type": "COUPON", "percent": 10, "expires_days": 60 }
// Free service
{ "type": "FREE_SERVICE", "service_id": 1, "max_pieces": 12 }
// Tier upgrade
{ "type": "TIER_UPGRADE", "tier": "Gold", "duration_days": 365 }
```

#### 3.2 Referral Flow
- Each Customer auto-gets `referral_code` (8-char).
- POS form accepts referral code or QR scan.
- When the referee’s first paid order ≥ config `minimum_order_value` is saved:
  - Create `Referral` row (linking referrer & referee).
  - Grant reward(s) per rule (to referrer, referee, or both).
  - Enforce monthly point/coupon cap.

#### 3.3 Customer-Facing Earn & Redeem
- POS displays current points balance & tier when a customer is selected.
- “Redeem” button lists eligible coupons / free services; cashier selects one to apply.
- Redemption adjusts `points_balance` and inserts appropriate zero-price line item or discount.

#### 3.4 Reporting Additions
| Report             | New Columns / Views                                              |
|--------------------|------------------------------------------------------------------|
| **Daily Sales**    | Points earned / redeemed per order.                             |
| **Monthly Profitability** | Loyalty liability (unredeemed points × redemption rate).         |
| **Loyalty Dashboard** | - Points liability summary<br>- Top referrers leaderboard<br>- Tier distribution pie. |

---

### 4. Data Model Add-Ons
```python
# loyalty/models.py
class LoyaltyAccount(models.Model):
    customer      = models.OneToOneField(Customer, on_delete=models.CASCADE)
    points_balance = models.IntegerField(default=0)
    tier          = models.CharField(max_length=20, default="Standard")
    tier_expiry   = models.DateField(null=True, blank=True)

class LoyaltyTransaction(models.Model):
    account       = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE)
    order         = models.ForeignKey(Order, null=True, blank=True,
                                      on_delete=models.SET_NULL)
    points_change = models.IntegerField()
    description   = models.TextField()
    created_at    = models.DateTimeField(auto_now_add=True)

class LoyaltyRule(models.Model):
    name        = models.CharField(max_length=50)
    trigger_type= models.CharField(max_length=20, choices=RULE_TYPES)
    config      = models.JSONField()
    reward      = models.JSONField()
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

class Referral(models.Model):
    code        = models.CharField(max_length=8, unique=True)
    referrer    = models.ForeignKey(Customer, related_name="sent_referrals",
                                    on_delete=models.CASCADE)
    referee     = models.ForeignKey(Customer, related_name="received_referral",
                                    on_delete=models.CASCADE)
    order       = models.ForeignKey(Order, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    reward_granted = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
```

---

### 5. Integration Points
| Event               | Action                                                                 |
|---------------------|----------------------------------------------------------------------|
| `post_save(Order)`  | Call `LoyaltyService.evaluate(order)` to:<br>• Run active rules → create `LoyaltyTransactions`.<br>• Update `LoyaltyAccount.points_balance` & tier.<br>• Handle referral rewards. |
| `Customer.create()` | Generate `referral_code`; create `LoyaltyAccount`.                   |
| POS UI              | Fetch `/api/loyalty/{customer_id}/summary` to show balance & tier; PATCH `/api/loyalty/redeem/` to apply reward. |
| Reports             | Extend ORM queries or use pandas to include loyalty metrics.         |

---

### 6. API Changes (DRF)
- `GET /api/loyalty/{customer_id}/summary`
- `POST /api/loyalty/rules/` (admin)
- `PATCH /api/loyalty/redeem/` → body: `{ "order_id": 123, "reward_id": 45 }`

---

### 7. Testing & QA
- **Unit tests** – rule evaluation, points maths, referral caps.
- **Integration tests** – full POS flow with referral redemption.
- **E2E** – Playwright: cashier redeems points, report shows liability drop.
- **Security** – ensure referral self-abuse prevented (unique phone/email).
- **Performance** – evaluate rules < 100 ms for 500 active rules.

---

### 8. Deployment & Migration
| Step | Detail                                                                 |
|------|------------------------------------------------------------------------|
| 1    | New `loyalty` app + migrations (`makemigrations loyalty`).             |
| 2    | Seed default rules via fixture `loyalty_seed.json`.                    |
| 3    | Add Celery beat task to expire points & tiers nightly.                 |
| 4    | Update backup script to include new tables.                            |

---

### 9. Acceptance Criteria
- Rules editable without code and applied in real-time.
- Points balance, tier, and referral flow demo’d in staging.
- Reports show loyalty metrics with ≤ 1 s load time on 50 k orders.
- ≥ 90 % test coverage for new app; all pipelines green.
- Business stakeholder sign-off on loyalty scenarios checklist.

---

### 10. Recommended Copilot Model
As a GitHub Copilot Pro (paid) user, select GPT-4o (or “GPT-4 Turbo”) inside Copilot Chat for the best reasoning and JSON/schema completion.

In VS Code → Copilot Chat → gear icon → “Model: GPT-4-Turbo”.

---

### Commit Plan for Dev
1. Create feature branch `feature/loyalty-module`.
2. Add this ToR update ➜ `/docs/terms_of_reference.md`.
3. Use Copilot Chat (GPT-4o) to scaffold `loyalty/models.py`, `loyalty/services.py`, migrations, tests, and admin forms following the spec.
4. Open PR, request review, merge, deploy to staging, run UAT.
