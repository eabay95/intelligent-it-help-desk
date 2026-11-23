import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";

export const STATUSES = ["Open", "In Progress", "Resolved"];
export const CATEGORIES = ["Network", "Hardware", "Software", "Account Access", "Other", "Unclassified"];
export const PRIORITIES = ["Low", "Medium", "High", "Critical"];

export function useTickets() {
  const [result, setResult] = useState({ tickets: [], error: "", loading: true });
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest("/tickets", { signal: controller.signal }).then(
      (tickets) => {
        if (!controller.signal.aborted) setResult({ tickets, error: "", loading: false });
      },
      (error) => {
        if (!controller.signal.aborted) {
          setResult((current) => ({ ...current, error: error.message, loading: false }));
        }
      },
    );
    return () => controller.abort();
  }, [revision]);

  function refresh(updatedTicket) {
    setResult((current) => {
      const tickets = updatedTicket
        ? [updatedTicket, ...current.tickets.filter(({ id }) => id !== updatedTicket.id)]
            .sort((a, b) => b.id - a.id)
        : current.tickets;
      return { tickets, error: "", loading: true };
    });
    setRevision((current) => current + 1);
  }

  return { ...result, refresh };
}
