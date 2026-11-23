export default function TicketMetadata({ ticket, showTeam = false }) {
  return (
    <dl className="ticket-metadata">
      <div><dt>Status</dt><dd>{ticket.status}</dd></div>
      <div><dt>Category</dt><dd>{ticket.category}</dd></div>
      <div><dt>Priority</dt><dd>{ticket.priority}</dd></div>
      {showTeam && <div><dt>Recommended team</dt><dd>{ticket.recommended_team}</dd></div>}
    </dl>
  );
}
