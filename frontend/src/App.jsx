
import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [task, setTask] = useState("");
  const [plan, setPlan] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState("");
  const [execution, setExecution] = useState(null);

  async function checkBackend() {
    try {
      const response = await fetch(`${API_URL}/health`);
      if (!response.ok) throw new Error("Health check failed");

      const data = await response.json();
      setBackendStatus(
        data.gemini_configured
          ? "Connected — Gemini configured"
          : "Connected — Gemini API key missing"
      );
      setError("");
    } catch {
      setBackendStatus("");
      setError(
        "Cannot connect to FastAPI. Check whether the backend is running."
      );
    }
  }

  async function prepareTask(event) {
    event.preventDefault();
    setPlan(null);
    setAnswer(null);
    setError("");

    if (task.trim().length < 5) {
      setError("Please enter a task with at least 5 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to generate the AI plan.");
      }

      setPlan(data.plan);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function askAgent(event) {
    event.preventDefault();
    setAnswer(null);
    setPlan(null);
    setError("");

    if (task.trim().length < 5) {
      setError("Please enter a question with at least 5 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to generate the RAG answer.");
      }

      setAnswer(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  
async function executeWorkflow() {
  setExecution(null);
  setPlan(null);
  setAnswer(null);
  setError("");

  if (task.trim().length < 5) {
    setError("Please enter a task with at least 5 characters.");
    return;
  }

  setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Workflow execution failed.");
      }

      setExecution(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }






  return (
    <main className="app">
      <header>
        <p className="eyebrow">AGENTIC AI WORKFLOW AUTOMATION</p>
        <h1>AgentFlow AI</h1>
        <p>
          Plan tasks, search your knowledge base, and generate
          evidence-grounded AI answers.
        </p>
      </header>

      <section className="panel">
        <h2>AI workspace</h2>
        <p>
          Describe a task to plan a workflow, or ask a support
          question to retrieve relevant knowledge and generate an answer.
        </p>

        <form onSubmit={(event) => event.preventDefault()}>
          <label htmlFor="task">Task or support question</label>

          <textarea
            id="task"
            value={task}
            onChange={(event) => setTask(event.target.value)}
            placeholder="Example: Customers cannot complete payments. What should we investigate?"
            rows={5}
            maxLength={2000}
          />

          <div className="actions">
            <button
              type="button"
              onClick={prepareTask}
              disabled={loading}
            >
              {loading ? "Processing..." : "Generate AI plan"}
            </button>

            <button
              type="button"
              onClick={askAgent}
              disabled={loading}
            >
              {loading ? "Processing..." : "Ask knowledge base"}
            </button>

            <button
              type="button"
              className="secondary"
              onClick={checkBackend}
              disabled={loading}
            >
              Test backend
            </button>

            <button
              type="button"
              onClick={executeWorkflow}
              disabled={loading}
            >
              {loading ? "Executing..." : "Execute Workflow"}
            </button>

          </div>
        </form>

        {backendStatus && (
          <p className="success">Backend: {backendStatus}</p>
        )}

        {error && <p className="error">{error}</p>}
      </section>

      {plan && (
        <section className="panel results">
          <p className="eyebrow">GENERATED WORKFLOW</p>
          <h2>{plan.task_summary}</h2>

          <h3>Execution steps</h3>

          <ol className="steps">
            {plan.steps.map((step, index) => (
              <li key={`${step.step}-${index}`}>
                <strong>{step.title}</strong>
                <p>{step.description}</p>
                <span className="tool">Tool: {step.tool}</span>
              </li>
            ))}
          </ol>

          {plan.risks?.length > 0 && (
            <>
              <h3>Risks and limitations</h3>
              <ul>
                {plan.risks.map((risk, index) => (
                  <li key={index}>{risk}</li>
                ))}
              </ul>
            </>
          )}

          <p className="note">
            This is a proposed plan. It has not been executed.
          </p>
        </section>
      )}

      {answer && (
        <section className="panel results">
          <p className="eyebrow">RETRIEVAL-AUGMENTED GENERATION</p>
          <h2>AI answer</h2>

          <p className="question">
            <strong>Question:</strong> {answer.question || task}
          </p>

          <div className="answer-content">
            {answer.answer || "No answer was returned."}
          </div>

          <h3>Source citations</h3>

          {answer.citations?.length > 0 ? (
            <div className="citations">
              {answer.citations.map((citation) => (
                <span className="citation" key={citation}>
                  {citation}
                </span>
              ))}
            </div>
          ) : (
            <p className="note">
              No valid source citations were returned.
            </p>
          )}

          <h3>Retrieved knowledge-base documents</h3>

          {answer.sources?.length > 0 ? (
            <div className="documents">
              {answer.sources.map((source) => (
                <article className="document" key={source.id}>
                  <div className="document-heading">
                    <strong>{source.title}</strong>
                    <span className="citation">{source.id}</span>
                  </div>

                  {typeof source.similarity_score === "number" && (
                    <p className="similarity">
                      Similarity score:{" "}
                      {source.similarity_score.toFixed(4)}
                    </p>
                  )}

                  <p>{source.solution}</p>

                  {source.content && (
                    <details>
                      <summary>View retrieved passage</summary>
                      <p>{source.content}</p>
                    </details>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className="note">No source documents were returned.</p>
          )}

          {answer.limitations?.length > 0 && (
            <>
              <h3>Limitations</h3>
              <ul>
                {answer.limitations.map((limitation, index) => (
                  <li key={index}>{limitation}</li>
                ))}
              </ul>
            </>
          )}

          <p className="note">
            AI-generated answers can be incomplete. Verify the
            retrieved guidance before acting on it.
          </p>
        </section>
      )}

      
{execution && (
  <section className="panel results">
    <p className="eyebrow">LANGGRAPH WORKFLOW</p>
    <h2>Workflow execution results</h2>

    <p>
      <strong>Status:</strong>{" "}
      {execution.status === "success" ? "Completed" : execution.status}
    </p>

    <p>
      <strong>Task:</strong> {execution.task}
    </p>

    <h3>Execution log</h3>

    <ol className="steps">
      {execution.execution_log?.map((item, index) => (
        <li key={`${item.step}-${index}`}>
          <strong>{item.step}</strong>
          <p>{item.message}</p>
          <span className="tool">Status: {item.status}</span>
        </li>
      ))}
    </ol>

    <h3>Ticket analysis</h3>

    <p>
      Total tickets: {execution.ticket_analysis?.total_tickets ?? 0}
    </p>

    <p>
      Urgent tickets: {execution.ticket_analysis?.urgent_count ?? 0}
    </p>

    {execution.ticket_analysis?.urgent_tickets?.length > 0 && (
      <ul>
        {execution.ticket_analysis.urgent_tickets.map((ticket) => (
          <li key={ticket.id}>
            <strong>{ticket.id} — {ticket.subject}</strong>
            <p>
              Priority: {ticket.priority} | Category: {ticket.category}
            </p>
          </li>
        ))}
      </ul>
    )}

    <h3>Retrieved documents</h3>

          {execution.documents?.length > 0 ? (
            <div className="documents">
              {execution.documents.map((doc) => (
                <article className="document" key={doc.id}>
                  <div className="document-heading">
                    <strong>{doc.title}</strong>
                    <span className="citation">{doc.id}</span>
                  </div>

                  {typeof doc.similarity_score === "number" && (
                    <p className="similarity">
                      Similarity: {doc.similarity_score.toFixed(4)}
                    </p>
                  )}

                  <p>{doc.solution}</p>
                </article>
              ))}
            </div>
          ) : (
            <p>No documents were returned.</p>
          )}

          <h3>Incident report</h3>

          {execution.report?.markdown ? (
            <pre className="report-content">
              {execution.report.markdown}
            </pre>
          ) : (
            <p>No report was returned.</p>
          )}
        </section>
      )}



    </main>
  );
}

export default App;
