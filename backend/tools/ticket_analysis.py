
from collections import Counter


SAMPLE_TICKETS = [
    {
        "id": "T-101",
        "subject": "Production API is down",
        "description": "All API requests are returning HTTP 503.",
        "priority": "critical",
    },
    {
        "id": "T-102",
        "subject": "Unable to reset password",
        "description": "Password reset email is not arriving.",
        "priority": "medium",
    },
    {
        "id": "T-103",
        "subject": "Payment failures",
        "description": "Several customers cannot complete payments.",
        "priority": "high",
    },
    {
        "id": "T-104",
        "subject": "Dashboard loads slowly",
        "description": "The dashboard takes around 8 seconds to load.",
        "priority": "low",
    },
]


def analyze_tickets(tickets=None):
    """Classify support tickets using their supplied priority."""

    tickets = tickets if tickets is not None else SAMPLE_TICKETS
    urgent = []
    categories = Counter()

    for ticket in tickets:
        priority = ticket.get("priority", "medium").lower()

        if priority not in {"low", "medium", "high", "critical"}:
            priority = "medium"

        subject = ticket.get("subject", "").lower()
        description = ticket.get("description", "").lower()
        text = f"{subject} {description}"

        if any(word in text for word in ["payment", "billing", "invoice"]):
            category = "Payment"
        elif any(word in text for word in ["api", "server", "503", "outage"]):
            category = "Service Availability"
        elif any(word in text for word in ["password", "login", "account"]):
            category = "Account Access"
        else:
            category = "General Support"

        categories[category] += 1

        result = {
            "id": ticket.get("id", "unknown"),
            "subject": ticket.get("subject", "No subject"),
            "priority": priority,
            "category": category,
            "description": ticket.get("description", ""),
        }

        if priority in {"high", "critical"}:
            urgent.append(result)

    return {
        "total_tickets": len(tickets),
        "urgent_count": len(urgent),
        "urgent_tickets": urgent,
        "category_counts": dict(categories),
    }
