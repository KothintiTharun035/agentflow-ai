
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pydantic import BaseModel, Field

from tools.rag_answer import answer_with_rag
from workflow import run_workflow, validate_plan


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


app = FastAPI(
    title="AgentFlow AI",
    description=(
        "AI task planning, validated LangGraph execution, "
        "semantic retrieval, and support incident reporting."
    ),
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    task: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The task for AgentFlow AI.",
    )


def generate_task_plan(task: str) -> dict:
    """Ask Gemini for a plan, then validate its structure and tools."""

    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Check backend/.env.",
        )

    prompt = f"""
You are the task planner for AgentFlow AI.

Create a practical plan for the user's task.

Available tools:
- ticket_analysis: Analyze the existing sample support tickets.
- document_search: Retrieve relevant knowledge-base documents using
  semantic vector search.
- report_generation: Generate a report from the available ticket
  analysis and retrieved documents.

Return ONLY valid JSON in this structure:
{{
  "task_summary": "short summary",
  "steps": [
    {{
      "step": 1,
      "title": "step title",
      "description": "what this step will do",
      "tool": "document_search"
    }}
  ],
  "risks": ["risk or limitation"]
}}

Rules:
- Produce 2 to 6 steps.
- Use only the exact tool names listed above.
- Choose tools that are relevant to the user's task.
- Order the steps logically.
- Use report_generation when a report is requested.
- Do not claim that any action has already been executed.
- Return JSON without Markdown fences.

User task:
{task}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        plan = json.loads(response.text)

        if not isinstance(plan, dict):
            raise ValueError("Gemini must return a JSON object.")

        summary = plan.get("task_summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("The plan is missing task_summary.")

        # Enforce the same allowlist used by the executor.
        validated_steps = validate_plan(plan)
        plan["steps"] = validated_steps

        risks = plan.get("risks", [])
        if not isinstance(risks, list) or not all(
            isinstance(risk, str) for risk in risks
        ):
            raise ValueError("Plan risks must be a list of strings.")

        plan["risks"] = risks[:10]

        return plan

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI planning or validation failed: {str(exc)[:300]}",
        ) from exc


@app.get("/")
def home():
    return {
        "message": "Welcome to AgentFlow AI API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "AgentFlow AI",
        "gemini_configured": client is not None,
    }


@app.post("/api/plan")
def plan_task(request: TaskRequest):
    plan = generate_task_plan(request.task)
    return {
        "status": "success",
        "plan": plan,
    }


@app.post("/api/execute")
def execute_task(request: TaskRequest):
    # Generate and validate a fresh plan for this execution.
    plan = generate_task_plan(request.task)

    try:
        result = run_workflow(
            task=request.task,
            plan=plan,
        )

        return {
            "status": "success",
            "task": request.task,
            "plan": result["plan"],
            "execution_log": result["execution_log"],
            "report": result["report"],
            "documents": result["document_results"],
            "ticket_analysis": result["ticket_analysis"],
        }

    except Exception as exc:
        # Keep internal exception details out of API responses.
        print(f"Workflow execution error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Workflow execution failed. Check the backend logs.",
        ) from exc


@app.post("/api/answer")
def answer_question(request: TaskRequest):
    try:
        return {
            "status": "success",
            **answer_with_rag(request.task),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(f"RAG answer error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="RAG answer generation failed. Check the backend logs.",
        ) from exc
