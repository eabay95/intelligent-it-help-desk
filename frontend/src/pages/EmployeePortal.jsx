import { useState } from "react";
import TicketMetadata from "../components/TicketMetadata";
import { apiRequest } from "../services/api";
import { useTickets } from "./useTickets";

export default function EmployeePortal() {
  const { tickets, loading, error, refresh } = useTickets();
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [ticketId, setTicketId] = useState(null);

  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const title = values.get("title").trim();
    const description = values.get("description").trim();
    setTicketId(null);
    if (!title || !description || title.length > 160 || description.length > 5000) {
      setSubmitError("Enter a title (1–160 characters) and a description (1–5,000 characters).");
      return;
    }
    setSubmitting(true);
    setSubmitError("");
    try {
      const ticket = await apiRequest("/tickets", {
        method: "POST",
        body: JSON.stringify({
          title, description,
          impact: values.get("impact") || null,
          urgency: values.get("urgency") || null,
        }),
      });
      form.reset();
      setTicketId(ticket.id);
      refresh(ticket);
    } catch (error) {
      setSubmitError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <h1>Employee Portal</h1>
      <p>Submit and track your IT support requests.</p>

      <section className="panel">
        <h2>Submit a ticket</h2>
        <form onSubmit={submit}>
          <fieldset disabled={submitting}>
            <label>Title<input name="title" required maxLength={160} /></label>
            <label>Description<textarea name="description" required maxLength={5000} rows={5} /></label>
            <div className="control-row">
              <label>Impact (optional)
                <select name="impact">
                  <option value="">Not specified</option>
                  <option>Individual</option><option>Team</option><option>Organization</option>
                </select>
              </label>
              <label>Urgency (optional)
                <select name="urgency">
                  <option value="">Not specified</option>
                  <option>Routine</option><option>Blocked</option>
                </select>
              </label>
            </div>
            <button>{submitting ? "Submitting…" : "Submit ticket"}</button>
          </fieldset>
        </form>
        {submitError && <p role="alert">{submitError}</p>}
        {ticketId !== null && <p role="status">Ticket #{ticketId} was submitted.</p>}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Your tickets</h2>
          <button type="button" onClick={() => refresh()} disabled={loading}>Refresh tickets</button>
        </div>
        {loading && <p role="status">Loading tickets…</p>}
        {error && <p role="alert">Could not load tickets. {error}</p>}
        {!loading && !error && tickets.length === 0 && <p>No tickets submitted yet.</p>}
        <ul className="ticket-list">
          {tickets.map((ticket) => (
            <li key={ticket.id}>
              <h3>#{ticket.id} {ticket.title}</h3>
              <TicketMetadata ticket={ticket} showTeam />
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
