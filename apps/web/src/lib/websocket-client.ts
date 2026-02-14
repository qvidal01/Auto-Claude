/**
 * Socket.IO client setup with auto-reconnect and namespace management.
 *
 * Three namespaces:
 * - /terminal — Terminal I/O streams
 * - /agent    — Agent progress and lifecycle events
 * - /events   — General application events (tasks, projects, etc.)
 *
 * Sockets are initialized outside components with autoConnect:false
 * so the WebSocketProvider controls their lifecycle.
 */

import { type Manager, type Socket, io } from "socket.io-client";
import { SOCKET_URL } from "./cloud-mode";

// ---------------------------------------------------------------------------
// Event type definitions
// ---------------------------------------------------------------------------

/** Terminal namespace events (server → client). */
export interface TerminalServerEvents {
  output: (data: { sessionId: string; data: string }) => void;
  exit: (data: { sessionId: string; code: number }) => void;
  error: (data: { sessionId: string; error: string }) => void;
}

/** Terminal namespace events (client → server). */
export interface TerminalClientEvents {
  input: (data: { sessionId: string; data: string }) => void;
  resize: (data: { sessionId: string; cols: number; rows: number }) => void;
  create: (data: { sessionId: string; cwd?: string }) => void;
  kill: (data: { sessionId: string }) => void;
}

/** Agent namespace events (server → client). */
export interface AgentServerEvents {
  progress: (data: {
    taskId: string;
    subtaskId: string;
    status: string;
    message?: string;
  }) => void;
  started: (data: { taskId: string; agentType: string }) => void;
  completed: (data: { taskId: string; result: string }) => void;
  failed: (data: { taskId: string; error: string }) => void;
  log: (data: { taskId: string; level: string; message: string }) => void;
}

/** Agent namespace events (client → server). */
export interface AgentClientEvents {
  cancel: (data: { taskId: string }) => void;
}

/** General events namespace (server → client). */
export interface EventsServerEvents {
  "task:updated": (data: { taskId: string; status: string }) => void;
  "task:created": (data: { taskId: string }) => void;
  "project:updated": (data: { projectId: string }) => void;
  "settings:changed": (data: { key: string; value: unknown }) => void;
  notification: (data: { level: string; title: string; body?: string }) => void;
}

/** General events namespace (client → server). */
export interface EventsClientEvents {
  subscribe: (data: { channel: string }) => void;
  unsubscribe: (data: { channel: string }) => void;
}

// ---------------------------------------------------------------------------
// Connection state
// ---------------------------------------------------------------------------

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

export interface SocketState {
  terminal: ConnectionState;
  agent: ConnectionState;
  events: ConnectionState;
}

type StateChangeCallback = (state: SocketState) => void;

const stateListeners = new Set<StateChangeCallback>();
const socketState: SocketState = {
  terminal: "disconnected",
  agent: "disconnected",
  events: "disconnected",
};

function updateState(ns: keyof SocketState, state: ConnectionState) {
  socketState[ns] = state;
  const snapshot = { ...socketState };
  for (const cb of stateListeners) {
    cb(snapshot);
  }
}

export function onStateChange(cb: StateChangeCallback): () => void {
  stateListeners.add(cb);
  return () => {
    stateListeners.delete(cb);
  };
}

export function getSocketState(): SocketState {
  return { ...socketState };
}

// ---------------------------------------------------------------------------
// Reconnect configuration
// ---------------------------------------------------------------------------

const RECONNECT_BASE_DELAY = 1_000;
const RECONNECT_MAX_DELAY = 30_000;
const RECONNECT_MAX_ATTEMPTS = Infinity;

// ---------------------------------------------------------------------------
// Socket creation helper
// ---------------------------------------------------------------------------

function createSocket(namespace: string): Socket {
  return io(`${SOCKET_URL}${namespace}`, {
    autoConnect: false,
    transports: ["websocket"],
    reconnection: true,
    reconnectionDelay: RECONNECT_BASE_DELAY,
    reconnectionDelayMax: RECONNECT_MAX_DELAY,
    reconnectionAttempts: RECONNECT_MAX_ATTEMPTS,
  });
}

function bindLifecycle(socket: Socket, ns: keyof SocketState) {
  socket.on("connect", () => updateState(ns, "connected"));
  socket.on("disconnect", () => updateState(ns, "disconnected"));
  socket.on("connect_error", () => updateState(ns, "error"));
  socket.io.on("reconnect_attempt", () => updateState(ns, "connecting"));
  socket.io.on("reconnect", () => updateState(ns, "connected"));
}

// ---------------------------------------------------------------------------
// Namespace sockets (singleton instances)
// ---------------------------------------------------------------------------

export const terminalSocket: Socket<TerminalServerEvents, TerminalClientEvents> =
  createSocket("/terminal") as Socket<TerminalServerEvents, TerminalClientEvents>;

export const agentSocket: Socket<AgentServerEvents, AgentClientEvents> =
  createSocket("/agent") as Socket<AgentServerEvents, AgentClientEvents>;

export const eventsSocket: Socket<EventsServerEvents, EventsClientEvents> =
  createSocket("/events") as Socket<EventsServerEvents, EventsClientEvents>;

bindLifecycle(terminalSocket, "terminal");
bindLifecycle(agentSocket, "agent");
bindLifecycle(eventsSocket, "events");

// ---------------------------------------------------------------------------
// Room helpers
// ---------------------------------------------------------------------------

/** Join a room on the given socket. */
export function joinRoom(socket: Socket, room: string): void {
  socket.emit("join", room);
}

/** Leave a room on the given socket. */
export function leaveRoom(socket: Socket, room: string): void {
  socket.emit("leave", room);
}

// ---------------------------------------------------------------------------
// Lifecycle helpers
// ---------------------------------------------------------------------------

/** Connect all namespace sockets. */
export function connectAll(): void {
  for (const s of [terminalSocket, agentSocket, eventsSocket]) {
    if (!s.connected) {
      updateState(
        s === terminalSocket ? "terminal" : s === agentSocket ? "agent" : "events",
        "connecting",
      );
      s.connect();
    }
  }
}

/** Disconnect all namespace sockets. */
export function disconnectAll(): void {
  for (const s of [terminalSocket, agentSocket, eventsSocket]) {
    if (s.connected) {
      s.disconnect();
    }
  }
}
