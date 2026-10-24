
"""Dependency-aware dynamic workflow execution with LangGraph."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from tools.document_search import search_documents
from tools.report_generation import generate_report
from tools.ticket_analysis import analyze_tickets


ALLOWED_TOOLS = {
    "ticket_analysis",
    "document_search",
    "report_generation",
}

# These tools must have run successfully before report generation.
REPORT_REQUIRED_INPUTS = {
    "ticket_analysis",
    "document_search",
}


class WorkflowState(TypedDict, total=False):
    task: str
    plan: dict[str, Any]
    ticket_analysis: dict[str, Any]
    document_results: list[dict[str, Any]]
    report: dict[str, Any]
    execution_log: list[dict[str, str]]


def validate_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate step structure, tool names, duplicates, and dependencies."""

    if not isinstance(plan, dict):
        raise ValueError("Plan must be a JSON object.")

    steps = plan.get("steps")

    if not isinstance(steps, list) or not 1 <= len(steps) <= 6:
        raise ValueError("Plan must contain between 1 and 6 steps.")

    validated = []
    seen_tools = set()

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Step {index} must be an object.")

        tool = step.get("tool")

        if tool not in ALLOWED_TOOLS:
            raise ValueError(
                f"Step {index} requests an unsupported tool: {tool!r}"
            )

        if tool in seen_tools:
            raise ValueError(
                f"Duplicate tool '{tool}' is not allowed in this version."
            )

        title = step.get("title")
        description = step.get("description")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Step {index} needs a title.")

        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Step {index} needs a description.")

        validated.append({
            "step": index,
            "title": title.strip()[:200],
            "description": description.strip()[:1000],
            "tool": tool,
        })

        seen_tools.add(tool)

    # If a report is requested, ensure both data-producing tools
    # appear before it in the plan.
    if "report_generation" in seen_tools:
        report_index = next(
            i for i, step in enumerate(validated)
            if step["tool"] == "report_generation"
        )

        tools_before_report = {
            step["tool"] for step in validated[:report_index]
        }

        missing = REPORT_REQUIRED_INPUTS - tools_before_report

        if missing:
            raise ValueError(
                "report_generation requires these earlier steps: "
                + ", ".join(sorted(missing))
            )

    return validated


def _log_step(
    state: WorkflowState,
    tool: str,
    message: str,
) -> list[dict[str, str]]:
    """Append a completed tool execution to the log."""

    log = list(state.get("execution_log", []))
    log.append({
        "step": tool,
        "status": "completed",
        "message": message,
    })
    return log


def _ticket_analysis_node(state: WorkflowState) -> dict[str, Any]:
    result = analyze_tickets()

    return {
        "ticket_analysis": result,
        "execution_log": _log_step(
            state,
            "ticket_analysis",
            f"Analyzed {result['total_tickets']} tickets; "
            f"found {result['urgent_count']} high/critical tickets.",
        ),
    }


def _document_search_node(state: WorkflowState) -> dict[str, Any]:
    queries = [state["task"]]
    analysis = state.get("ticket_analysis", {})

    for ticket in analysis.get("urgent_tickets", []):
        query = " ".join(
            str(ticket.get(field, ""))
            for field in ("subject", "description")
        ).strip()

        if query and query not in queries:
            queries.append(query)

    documents_by_id = {}

    for query in queries:
        for document in search_documents(query, limit=3):
            document_id = document["id"]
            existing = documents_by_id.get(document_id)

            if (
                existing is None
                or document.get("similarity_score", 0)
                > existing.get("similarity_score", 0)
            ):
                documents_by_id[document_id] = document

    documents = sorted(
        documents_by_id.values(),
        key=lambda item: item.get("similarity_score", 0),
        reverse=True,
    )

    return {
        "document_results": documents,
        "execution_log": _log_step(
            state,
            "document_search",
            f"Retrieved {len(documents)} relevant documents.",
        ),
    }


def _report_generation_node(state: WorkflowState) -> dict[str, Any]:
    analysis = state.get("ticket_analysis")
    documents = state.get("document_results")

    # Fail explicitly rather than generating a misleading report.
    if analysis is None or documents is None:
        raise ValueError(
            "Report generation requires ticket analysis and document "
            "search results. Validate the plan dependencies first."
        )

    report = generate_report(analysis, documents)

    return {
        "report": report,
        "execution_log": _log_step(
            state,
            "report_generation",
            "Generated the incident report.",
        ),
    }


TOOL_HANDLERS = {
    "ticket_analysis": _ticket_analysis_node,
    "document_search": _document_search_node,
    "report_generation": _report_generation_node,
}


def run_workflow(task: str, plan: dict[str, Any]) -> dict[str, Any]:
    """Build a LangGraph from the validated plan and run it sequentially."""

    steps = validate_plan(plan)

    builder = StateGraph(WorkflowState)
    node_names = []

    for index, step in enumerate(steps):
        tool = step["tool"]
        node_name = f"planned_step_{index + 1}_{tool}"
        handler = TOOL_HANDLERS[tool]

        def execute_node(
            state: WorkflowState,
            *,
            handler=handler,
            step=step,
        ) -> dict[str, Any]:
            result = handler(state)
            log = list(result.get(
                "execution_log",
                state.get("execution_log", []),
            ))

            log[-1] = {
                **log[-1],
                "title": step["title"],
                "description": step["description"],
            }

            result["execution_log"] = log
            return result

        builder.add_node(node_name, execute_node)
        node_names.append(node_name)

    builder.add_edge(START, node_names[0])

    for current, following in zip(node_names, node_names[1:]):
        builder.add_edge(current, following)

    builder.add_edge(node_names[-1], END)

    graph = builder.compile()

    result = graph.invoke({
        "task": task,
        "plan": plan,
        "execution_log": [],
    })

    return {
        "task": task,
        "plan": plan,
        "execution_log": result.get("execution_log", []),
        "ticket_analysis": result.get("ticket_analysis", {}),
        "document_results": result.get("document_results", []),
        "report": result.get("report", {}),
    }
