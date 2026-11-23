import assert from "node:assert/strict";
import { after, afterEach, before, beforeEach, test } from "node:test";
import { JSDOM } from "jsdom";
import { act, createElement } from "react";
import { createServer } from "vite";

const originalFetch = globalThis.fetch;
const dom = new JSDOM('<div id="root"></div>', { url: "http://localhost:5173/" });
const body = dom.window.document.body;
const example = {
  id: 42,
  title: "VPN keeps dropping",
  description: "The VPN disconnects every few minutes.",
  requester_id: "employee-test-id",
  category: "Network",
  priority: "Medium",
  recommended_team: "Network Support",
  status: "Open",
  classification_source: "model",
  updated_at: "2026-01-01T12:00:00Z",
};

let server;
let root;
let createRoot;
let EmployeePortal;
let TechnicianDashboard;
let App;
let auth;
let apiRequest;
let session;
let onAuthChange;
const employee = { id: "employee-test-id", full_name: "Test Employee", role: "employee" };
const technician = { id: "technician-test-id", full_name: "Test Technician", role: "technician" };

function useSession(profile, token = profile?.id) {
  session = profile ? { user: { id: profile.id, email: "test@example.test" }, access_token: token } : null;
  onAuthChange?.(session ? "SIGNED_IN" : "SIGNED_OUT", session);
}

before(async () => {
  process.env.VITE_SUPABASE_URL = "https://auth.example.test";
  process.env.VITE_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_testing_isolated_fixture";
  process.env.VITE_API_BASE_URL = "http://localhost:8000";
  Object.assign(globalThis, {
    window: dom.window,
    document: dom.window.document,
    FormData: dom.window.FormData,
    IS_REACT_ACT_ENVIRONMENT: true,
  });
  ({ createRoot } = await import("react-dom/client"));
  server = await createServer({ server: { middlewareMode: true, ws: false }, appType: "custom" });
  ({ default: EmployeePortal } = await server.ssrLoadModule("/src/pages/EmployeePortal.jsx"));
  ({ default: TechnicianDashboard } = await server.ssrLoadModule("/src/pages/TechnicianDashboard.jsx"));
  ({ default: App } = await server.ssrLoadModule("/src/App.jsx"));
  const { getSupabase } = await server.ssrLoadModule("/src/services/supabase.js");
  ({ apiRequest } = await server.ssrLoadModule("/src/services/api.js"));
  auth = getSupabase().auth;
});

beforeEach(() => {
  dom.window.history.replaceState({}, "", "/");
  root = createRoot(document.getElementById("root"));
  auth.getSession = async () => ({ data: { session } });
  auth.refreshSession = async () => ({ data: { session: null } });
  auth.onAuthStateChange = (callback) => {
    onAuthChange = callback;
    queueMicrotask(() => onAuthChange === callback && callback("INITIAL_SESSION", session));
    return { data: { subscription: { unsubscribe: () => { onAuthChange = undefined; } } } };
  };
  auth.signOut = async () => { useSession(null); return {}; };
  auth.signInWithPassword = async () => { throw new Error("Unexpected login request"); };
  auth.signUp = async () => { throw new Error("Unexpected registration request"); };
  auth.resetPasswordForEmail = async () => { throw new Error("Unexpected password reset request"); };
  auth.updateUser = async () => { throw new Error("Unexpected password update"); };
  useSession(employee);
});

afterEach(async () => {
  await act(async () => { root.unmount(); });
  globalThis.fetch = originalFetch;
});

after(async () => {
  await auth?.dispose();
  await server?.close();
  dom.window.close();
});

function response(data, status = 200) {
  return Response.json(data, { status });
}

async function render(Component) {
  await act(async () => { root.render(createElement(Component)); });
}

async function submit(form) {
  await act(async () => {
    form.dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
  });
}

async function click(element) {
  assert.ok(element, "Expected a clickable element");
  await act(async () => {
    element.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }));
  });
}

async function eventually(check) {
  const deadline = Date.now() + 5000;
  do {
    if (check()) return;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 25)); });
  } while (Date.now() < deadline);
  assert.ok(check(), "Expected the UI to update");
}

test("employee form rejects whitespace and keeps required fields and length limits", async () => {
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push([new URL(url).pathname, options.method]);
    return response([]);
  };
  await render(EmployeePortal);
  const form = body.querySelector("form");
  assert.equal(form.elements.title.required, true);
  assert.equal(form.elements.title.maxLength, 160);
  assert.equal(form.elements.description.maxLength, 5000);
  form.elements.title.value = " ";
  form.elements.description.value = example.description;
  await submit(form);
  assert.match(body.querySelector('[role="alert"]').textContent, /Enter a title/);
  assert.deepEqual(requests, [["/tickets", undefined]]);
});

test("employee submits a ticket and sees its ID and classification in the ticket list", async () => {
  let tickets = [];
  globalThis.fetch = async (url, options) => {
    const endpoint = new URL(url);
    assert.equal(endpoint.pathname, "/tickets");
    if (options.method === "POST") {
      assert.deepEqual(JSON.parse(options.body), {
        title: example.title, description: example.description, impact: null, urgency: null,
      });
      tickets = [example];
      return response(example, 201);
    }
    assert.equal(endpoint.searchParams.has("requester_id"), false);
    assert.equal(options.headers.get("Authorization"), `Bearer ${employee.id}`);
    return response(tickets);
  };
  await render(EmployeePortal);
  const form = body.querySelector("form");
  form.elements.title.value = `  ${example.title}  `;
  form.elements.description.value = example.description;
  await submit(form);
  assert.match(body.textContent, /Ticket #42 was submitted/);
  const ticket = body.querySelector(".ticket-list li");
  for (const value of [example.title, "Open", "Network", "Medium", "Network Support"]) {
    assert.ok(ticket.textContent.includes(value));
  }
  assert.equal(form.elements.title.value, "");
});

test("ticket loading and API errors are visible, with refresh available", async () => {
  let complete;
  globalThis.fetch = () => new Promise((resolve) => { complete = resolve; });
  await render(EmployeePortal);
  assert.match(body.querySelector('[role="status"]').textContent, /Loading tickets/);
  assert.equal(body.querySelector(".section-heading button").disabled, true);
  await act(() => complete(response({ detail: "Ticket storage is unavailable." }, 503)));
  assert.match(body.querySelector('[role="alert"]').textContent, /Ticket storage is unavailable/);
  globalThis.fetch = async () => response([example]);
  await click(body.querySelector(".section-heading button"));
  assert.equal(body.querySelector('[role="alert"]'), null);
  assert.match(body.querySelector(".ticket-list").textContent, /VPN keeps dropping/);
});

test("an unsuccessful submission displays the API error and preserves the draft", async () => {
  globalThis.fetch = async (_url, options) => options.method === "POST"
    ? response({ detail: "Ticket storage is unavailable." }, 503)
    : response([]);
  await render(EmployeePortal);
  const form = body.querySelector("form");
  form.elements.title.value = example.title;
  form.elements.description.value = example.description;
  await submit(form);
  assert.match(body.querySelector('[role="alert"]').textContent, /Ticket storage is unavailable/);
  assert.equal(form.elements.title.value, example.title);
  assert.equal(form.elements.description.value, example.description);
  assert.doesNotMatch(body.textContent, /was submitted/);
});

test("technician filters tickets and saves status, category, and priority overrides", async () => {
  let ticket = example;
  globalThis.fetch = async (url, options) => {
    if (options.method === "PATCH") {
      assert.equal(new URL(url).pathname, "/tickets/42");
      assert.deepEqual(JSON.parse(options.body), {
        status: "Resolved", category: "Hardware", priority: "High",
      });
      ticket = {
        ...ticket, status: "Resolved", category: "Hardware", priority: "High",
        recommended_team: "Hardware Support", updated_at: "2026-01-01T12:01:00Z",
      };
      return response(ticket);
    }
    return response([ticket]);
  };
  await render(TechnicianDashboard);
  const [filter] = body.querySelectorAll(".control-row select");
  await act(() => {
    filter.value = "Resolved";
    filter.dispatchEvent(new window.Event("change", { bubbles: true }));
  });
  assert.match(body.textContent, /No matching tickets/);
  await act(() => {
    filter.value = "";
    filter.dispatchEvent(new window.Event("change", { bubbles: true }));
  });
  await click(body.querySelector(".ticket-link"));
  assert.match(body.querySelectorAll("h2")[1].textContent, /Ticket #42/);
  const form = body.querySelector("form");
  form.elements.status.value = "Resolved";
  form.elements.category.value = "Hardware";
  form.elements.priority.value = "High";
  await submit(form);
  assert.match(body.querySelector(".ticket-list").textContent, /Resolved.*Hardware.*High.*Hardware Support/);
  assert.match(body.textContent, /Ticket #42 was updated/);
});

test("restores an employee session and denies navigation to the technician route", async () => {
  dom.window.history.replaceState({}, "", "/technician");
  globalThis.fetch = async (url) => response(new URL(url).pathname === "/auth/me" ? employee : []);
  await render(App);
  await eventually(() => body.querySelector("h1")?.textContent === "Employee Portal");
  assert.equal(window.location.pathname, "/");
  assert.equal(body.querySelector('a[href="/technician"]'), null);
});

test("redirects unauthenticated users and displays invalid login credentials", async () => {
  useSession(null);
  globalThis.fetch = () => { throw new Error("Unexpected unauthenticated API call"); };
  auth.signInWithPassword = async () => ({ error: { code: "invalid_credentials" } });
  await render(App);
  await eventually(() => window.location.pathname === "/login");
  const form = body.querySelector("form");
  form.elements.email.value = "test@example.test";
  form.elements.password.value = "wrongpassword";
  await submit(form);
  assert.match(body.querySelector('[role="alert"]').textContent, /Invalid login credentials/);
  assert.equal(form.elements.email.matches(":disabled"), false);
  assert.equal(form.elements.password.matches(":disabled"), false);
});

test("login inputs stay editable during a failed profile check and a retry restores the portal", async () => {
  dom.window.history.replaceState({}, "", "/login");
  let profileRequests = 0;
  let complete;
  globalThis.fetch = (url) => {
    if (new URL(url).pathname !== "/auth/me") return Promise.resolve(response([]));
    profileRequests += 1;
    return new Promise((resolve, reject) => { complete = { resolve, reject }; });
  };
  await render(App);
  const form = body.querySelector("form");
  assert.match(body.querySelector('[role="status"]').textContent, /Checking your session/);
  for (const name of ["email", "password"]) {
    const input = form.elements[name];
    assert.equal(input.matches(":disabled"), false);
    input.focus();
    assert.equal(document.activeElement, input);
  }
  form.elements.email.value = "different@example.test";
  form.elements.password.value = "example-password";
  await act(async () => { complete.reject(new TypeError("Failed to fetch")); });
  assert.match(body.querySelector('[role="alert"]').textContent, /Could not reach the Help Desk API/);
  assert.equal(form.elements.email.matches(":disabled"), false);
  assert.equal(form.elements.email.value, "different@example.test");
  assert.equal(form.elements.password.matches(":disabled"), false);
  const retry = [...body.querySelectorAll("button")].find((button) => button.textContent === "Retry profile check");
  await click(retry);
  assert.equal(profileRequests, 2);
  assert.equal(retry.disabled, true);
  assert.equal(form.elements.password.matches(":disabled"), false);
  await act(async () => { complete.resolve(response(employee)); });
  await eventually(() => body.querySelector("h1")?.textContent === "Employee Portal");
});

test("a rejected restored session refreshes once and leaves the sign-in form usable", async () => {
  let refreshes = 0;
  let requests = 0;
  auth.refreshSession = async () => {
    refreshes += 1;
    useSession(employee, "refreshed-but-rejected");
    return { data: { session } };
  };
  globalThis.fetch = async () => { requests += 1; return response({}, 401); };
  await render(App);
  await eventually(() => window.location.pathname === "/login");
  assert.equal(refreshes, 1);
  assert.equal(requests, 2);
  assert.equal(session, null);
  assert.equal(body.querySelector('[name="email"]').matches(":disabled"), false);
});

test("a profile denial does not prevent a new login attempt", async () => {
  dom.window.history.replaceState({}, "", "/login");
  let authenticatedAgain = false;
  auth.signInWithPassword = async () => {
    authenticatedAgain = true;
    return { data: { session } };
  };
  globalThis.fetch = async (url) => {
    if (new URL(url).pathname !== "/auth/me") return response([]);
    return authenticatedAgain ? response(employee) : response({ detail: "Profile access denied." }, 403);
  };
  await render(App);
  assert.match(body.querySelector('[role="alert"]').textContent, /Profile access denied/);
  const form = body.querySelector("form");
  form.elements.email.value = "employee@example.test";
  form.elements.password.value = "example-password";
  await submit(form);
  await eventually(() => body.querySelector("h1")?.textContent === "Employee Portal");
});

test("registration validates confirmation and sends only full name as metadata", async () => {
  useSession(null);
  dom.window.history.replaceState({}, "", "/register");
  let request;
  auth.signUp = async (payload) => {
    request = payload;
    return { data: { session: null } };
  };
  await render(App);
  const form = body.querySelector("form");
  form.elements.full_name.value = " Test Employee ";
  form.elements.email.value = "test@example.test";
  form.elements.password.value = "example-password";
  form.elements.confirm.value = "mismatch";
  await submit(form);
  assert.match(body.querySelector('[role="alert"]').textContent, /confirm the same password/);
  assert.equal(request, undefined);
  form.elements.confirm.value = "example-password";
  await submit(form);
  assert.deepEqual(request.options.data, { full_name: "Test Employee" });
  assert.equal(request.options.emailRedirectTo, "http://localhost:5173/login");
  assert.match(body.textContent, /Check your email/);
});

test("requests password recovery and updates the password from an authenticated recovery session", async () => {
  useSession(null);
  dom.window.history.replaceState({}, "", "/forgot-password");
  auth.resetPasswordForEmail = async (email, options) => {
    assert.equal(email, "test@example.test");
    assert.equal(options.redirectTo, "http://localhost:5173/reset-password");
    return {};
  };
  await render(App);
  const form = body.querySelector("form");
  form.elements.email.value = "test@example.test";
  await submit(form);
  assert.match(body.textContent, /password reset link/);
  auth.updateUser = async ({ password }) => {
    assert.equal(password, "new-example-password");
    return {};
  };
  globalThis.fetch = async () => response(employee);
  await act(async () => {
    useSession(employee);
    root.unmount();
  });
  dom.window.history.replaceState({}, "", "/reset-password");
  root = createRoot(document.getElementById("root"));
  await render(App);
  const resetForm = body.querySelector("form");
  resetForm.elements.password.value = "new-example-password";
  resetForm.elements.confirm.value = "new-example-password";
  await submit(resetForm);
  assert.match(body.textContent, /Password updated/);
});

test("employees and technicians sign in, sign out, and resolve a ticket across sessions", async () => {
  useSession(null);
  let ticket;
  auth.signInWithPassword = async ({ email }) => {
    useSession(email.startsWith("tech") ? technician : employee);
    return { data: { session } };
  };
  globalThis.fetch = async (url, options) => {
    const path = new URL(url).pathname;
    const actor = options.headers.get("Authorization") === `Bearer ${technician.id}` ? technician : employee;
    if (path === "/auth/me") return response(actor);
    if (options.method === "POST") {
      assert.equal(actor, employee);
      ticket = example;
      return response(ticket, 201);
    }
    if (options.method === "PATCH") {
      assert.equal(actor, technician);
      ticket = { ...ticket, ...JSON.parse(options.body), updated_at: "2026-01-01T12:01:00Z" };
      return response(ticket);
    }
    return response(ticket ? [ticket] : []);
  };
  async function login(email, heading) {
    await eventually(() => window.location.pathname === "/login");
    const form = body.querySelector("form");
    form.elements.email.value = email;
    form.elements.password.value = "example-password";
    await submit(form);
    await eventually(() => body.querySelector("h1")?.textContent === heading);
  }
  await render(App);
  await login("employee@example.test", "Employee Portal");
  const ticketForm = body.querySelector("form");
  ticketForm.elements.title.value = example.title;
  ticketForm.elements.description.value = example.description;
  await submit(ticketForm);
  assert.match(body.textContent, /Ticket #42 was submitted/);
  await click(body.querySelector("nav button"));
  await login("tech@example.test", "Technician Dashboard");
  assert.equal(window.location.pathname, "/technician");
  await click(body.querySelector(".ticket-link"));
  const updateForm = body.querySelector("form");
  updateForm.elements.status.value = "Resolved";
  await submit(updateForm);
  assert.match(body.textContent, /Ticket #42 was updated/);
  await click(body.querySelector("nav button"));
  await login("employee@example.test", "Employee Portal");
  assert.match(body.querySelector(".ticket-list").textContent, /Resolved/);
});

test("API refreshes an expired token and preserves the session on a 403", async () => {
  auth.refreshSession = async () => {
    useSession(employee, "refreshed-token");
    return { data: { session } };
  };
  globalThis.fetch = async (_url, options) => (
    options.headers.get("Authorization") === "Bearer refreshed-token"
      ? response([], 200)
      : response({}, 401)
  );
  assert.deepEqual(await apiRequest("/tickets"), []);
  globalThis.fetch = async () => response({ detail: "Technician access is required." }, 403);
  await assert.rejects(apiRequest("/tickets/42"), /Technician access is required/);
  assert.equal(session.access_token, "refreshed-token");
});

test("API clears the session when a refreshed token is also rejected", async () => {
  auth.refreshSession = async () => {
    useSession(employee, "also-invalid");
    return { data: { session } };
  };
  globalThis.fetch = async () => response({}, 401);
  await assert.rejects(apiRequest("/tickets"), /session expired/);
  assert.equal(session, null);
});

test("API distinguishes network failures and server errors without exposing internal details", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(apiRequest("/auth/me"), /Could not reach the Help Desk API/);
  globalThis.fetch = async () => response({ detail: "internal database stack trace" }, 500);
  await assert.rejects(
    apiRequest("/auth/me"),
    (error) => /server error/.test(error.message) && !error.message.includes("stack trace"),
  );
  auth.getSession = async () => ({
    data: { session: null }, error: { name: "AuthRetryableFetchError" },
  });
  await assert.rejects(apiRequest("/auth/me"), /Could not reach Supabase Auth/);
});

