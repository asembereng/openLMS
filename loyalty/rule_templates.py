# loyalty/rule_templates.py
import json

def get_loyalty_templates():
    """
    Returns a list of loyalty rule templates with all metadata needed for a visual rule editor.
    Each template includes:
      - id, name, description
      - trigger_type (for backend logic)
      - config and reward (as JSON for backend, but not shown to user)
      - explanation and example (for user guidance)
      - fields: list of dicts with label, key, type, default, help, options (for select), required, etc.
      - ui: extra UI hints (e.g. drag-and-drop group, section, icon)
    """
    return [
        {
            "id": "welcome-bonus",
            "name": "Welcome Bonus",
            "description": "Instantly rewards new customers with bonus points on their first order to provide immediate value and encourage sign-ups.",
            "trigger_type": "FIRST_ORDER",
            "config": json.dumps({}, indent=4),
            "reward": json.dumps({"type": "POINTS", "amount": 50}, indent=4),
            "explanation": "This rule gives a one-time bonus to every new customer when they place their first order. No configuration is needed. Just set how many points to award.",
            "example": "A new customer places their first order and instantly receives 50 loyalty points.",
            "fields": [
                {"label": "Points to Award", "key": "amount", "type": "number", "default": 50, "help": "How many points should be given for the welcome bonus?", "required": True}
            ],
            "ui": {"icon": "fa-gift", "color": "#4facfe", "section": "Onboarding"}
        },
        {
            "id": "standard-points",
            "name": "Standard Points-per-Spend",
            "description": "The foundational rule for any loyalty program. Customers earn a set number of points for every unit of currency spent.",
            "trigger_type": "SPEND_BASED",
            "config": json.dumps({"base_currency_amount": 100, "points_to_award": 1}, indent=4),
            "reward": json.dumps({"type": "DYNAMIC_POINTS"}, indent=4),
            "explanation": "Customers earn points based on how much they spend. For example, 1 point for every 100 currency spent. Set the currency amount and points to award.",
            "example": "If a customer spends 500, they earn 5 points.",
            "fields": [
                {"label": "Currency Amount", "key": "base_currency_amount", "type": "number", "default": 100, "help": "How much must a customer spend to earn points? (e.g., 100 = 1 point per 100 spent)", "required": True},
                {"label": "Points to Award", "key": "points_to_award", "type": "number", "default": 1, "help": "How many points are awarded for each currency amount?", "required": True}
            ],
            "ui": {"icon": "fa-coins", "color": "#059669", "section": "Earning"}
        },
        {
            "id": "frequent-visitor",
            "name": "Frequent Visitor Bonus",
            "description": "Encourages repeat business by rewarding customers who visit multiple times within a specific period (e.g., a calendar month).",
            "trigger_type": "ORDER_FREQUENCY",
            "config": json.dumps({"period_days": 30, "order_count": 3}, indent=4),
            "reward": json.dumps({"type": "POINTS", "amount": 150}, indent=4),
            "explanation": "Rewards customers who place a certain number of orders within a set period. Set the period (in days), the order count, and the bonus points.",
            "example": "If a customer places 3 orders in 30 days, they get 150 bonus points.",
            "fields": [
                {"label": "Period (days)", "key": "period_days", "type": "number", "default": 30, "help": "How many days to count orders for this bonus?", "required": True},
                {"label": "Order Count", "key": "order_count", "type": "number", "default": 3, "help": "How many orders must be placed in the period to get the bonus?", "required": True},
                {"label": "Points to Award", "key": "amount", "type": "number", "default": 150, "help": "How many points to give as a bonus?", "required": True}
            ],
            "ui": {"icon": "fa-calendar-check", "color": "#6366f1", "section": "Earning"}
        },
        {
            "id": "refer-a-friend",
            "name": "Refer-a-Friend",
            "description": "Drives new customer acquisition by rewarding both the referrer and the new customer when a referral code is used.",
            "trigger_type": "REFERRAL",
            "config": json.dumps({}, indent=4),
            "reward": json.dumps({"type": "POINTS", "amount": 250, "target": "BOTH"}, indent=4),
            "explanation": "When a customer refers a friend, both get bonus points after the friend's first order. Just set the points to award.",
            "example": "Alice refers Bob. After Bob's first order, both Alice and Bob get 250 points.",
            "fields": [
                {"label": "Points to Award", "key": "amount", "type": "number", "default": 250, "help": "How many points to give to both the referrer and the new customer?", "required": True}
            ],
            "ui": {"icon": "fa-user-friends", "color": "#f59e42", "section": "Referral"}
        },
        {
            "id": "birthday-bonus",
            "name": "Birthday Bonus",
            "description": "Rewards customers with bonus points on their birthday to encourage loyalty and make them feel valued.",
            "trigger_type": "BIRTHDAY",
            "config": json.dumps({}, indent=4),
            "reward": json.dumps({"type": "POINTS", "amount": 100}, indent=4),
            "explanation": "Gives customers a special bonus on their birthday. Just set the points to award.",
            "example": "On their birthday, a customer receives 100 bonus points automatically.",
            "fields": [
                {"label": "Points to Award", "key": "amount", "type": "number", "default": 100, "help": "How many points to give as a birthday gift?", "required": True}
            ],
            "ui": {"icon": "fa-birthday-cake", "color": "#e879f9", "section": "Special"}
        },
    ]
