import { useState } from "react";
import TicketMetadata from "../components/TicketMetadata";
import { apiRequest } from "../services/api";
import { CATEGORIES, PRIORITIES, STATUSES, useTickets } from "./useTickets";

const fields = [
  { key: "status", label: "Status", options: STATUSES },
  { key: "category", label: "Category", options: CATEGORIES },
  { key: "priority", label: "Priority", options: PRIORITIES },
];

function TicketEditor({ ticket, onSaved }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function save(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const changes = Object.fromEntries(
      fields.map(({ key }) => [key, form.get(key)]).filter(([key, value]) => value !== ticket[key]),
    );
    setError("");
    if (Object.keys(changes).length === 0) return;
    setSaving(true);
    try {
      const updated = await apiRequest(`/tickets/${ticket.id}`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      onSaved(updated);
    } catch (error) {
      setError(error.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save}>
      <fieldset disabled={saving}>
        <legend>Edit ticket</legend>
        <div className="control-row">
          {fields.map(({ key, label, options }) => (
            <label key={key}>{label}
              <select name={key} defaultValue={ticket[key]}>
                {options.map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
          ))}
        </div>
        <button>{saving ? "Saving…" : "Save changes"}</button>
      </fieldset>
      {error && <p role="alert">Could not update ticket. {error}</p>}
    </form>
  );
}

export default function TechnicianDashboard() {
  const { tickets, loading, error, refresh } = useTickets();
  const [filters, setFilters] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [savedId, setSavedId] = useState(null);
  const visibleTickets = tickets.filter((ticket) => (
    fields.every(({ key }) => !filters[key] || filters[key] === ticket[key])
  ));
  const selected = tickets.find((ticket) => ticket.id === selectedId);

  return (
    <main className="page">
      <h1>Technician Dashboard</h1>
      <p>Review, route, and resolve support tickets.</p>
      <section className="panel">
        <div className="section-heading">
          <h2>Support tickets</h2>
          <button type="button" onClick={() => refresh()} disabled={loading}>Refresh tickets</button>
        </div>
        <div className="control-row">
          {fields.map(({ key, label, options }) => (
            <label key={key}>Filter by {label.toLowerCase()}
              <select value={filters[key] || ""} onChange={(event) => {
                setFilters({ ...filters, [key]: event.target.value });
              }}>
                <option value="">All</option>
                {options.map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
          ))}
        </div>
        {loading && <p role="status">Loading tickets…</p>}
        {error && <p role="alert">Could not load tickets. {error}</p>}
        {!loading && !error && visibleTickets.length === 0 && <p>No matching tickets.</p>}
        <ul className="ticket-list">
          {visibleTickets.map((ticket) => (
            <li key={ticket.id}>
              <button type="button" className="ticket-link" onClick={() => {
                setSelectedId(ticket.id);
                setSavedId(null);
              }}>#{ticket.id} {ticket.title}</button>
              <p className="ticket-description">{ticket.description}</p>
              <TicketMetadata ticket={ticket} showTeam />
            </li>
          ))}
        </ul>
      </section>
      {selected && (
        <section className="panel">
          <div className="section-heading">
            <h2>Ticket #{selected.id} · {selected.title}</h2>
            <button type="button" onClick={() => setSelectedId(null)}>Close details</button>
          </div>
          <p className="ticket-description">{selected.description}</p>
          <TicketMetadata ticket={selected} showTeam />
          <p>Requester {selected.requester_id ?? "Unassigned historical ticket"} · Classification {selected.classification_source}</p>
          {selected.classification_confidence != null && (
            <p>Model confidence {Math.round(selected.classification_confidence * 100)}%</p>
          )}
          <TicketEditor key={`${selected.id}-${selected.updated_at}`} ticket={selected} onSaved={(updated) => {
            setSavedId(updated.id);
            refresh(updated);
          }} />
          {savedId === selected.id && <p role="status">Ticket #{savedId} was updated.</p>}
        </section>
      )}
    </main>
  );
}
