
from datetime import datetime, timezone


def generate_report(ticket_analysis, document_results):
    """Create a report from actual ticket-analysis and search results."""

    urgent_tickets = ticket_analysis.get("urgent_tickets", [])
    documents = document_results or []

    report_lines = [
        "# AgentFlow AI — Support Incident Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Tickets analyzed: {ticket_analysis.get('total_tickets', 0)}",
        f"- High or critical tickets: {len(urgent_tickets)}",
        f"- Relevant documents retrieved: {len(documents)}",
        "",
        "## Urgent tickets",
    ]

    if urgent_tickets:
        for ticket in urgent_tickets:
            report_lines.extend([
                "",
                f"### {ticket['id']} — {ticket['subject']}",
                f"- Priority: {ticket['priority']}",
                f"- Category: {ticket['category']}",
                f"- Description: {ticket['description']}",
            ])
    else:
        report_lines.append("No high- or critical-priority tickets were found.")

    report_lines.extend(["", "## Retrieved troubleshooting guidance"])

    if documents:
        for document in documents:
            report_lines.extend([
                "",
                f"### {document['id']} — {document['title']}",
                document["solution"],
            ])
    else:
        report_lines.append(
            "No matching knowledge-base documents were found. "
            "Manual investigation is required."
        )

    report_lines.extend([
        "",
        "## Limitations",
        "- Results depend on the supplied ticket data.",
        "- Retrieved guidance must be checked against the actual incident.",
        "- This report does not confirm that any fix was executed.",
    ])

    return {
        "title": "Support Incident Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "markdown": "\n".join(report_lines),
        "ticket_count": ticket_analysis.get("total_tickets", 0),
        "urgent_count": len(urgent_tickets),
        "documents_found": len(documents),
    }
