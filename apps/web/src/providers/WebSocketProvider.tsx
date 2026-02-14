"use client";

import {
  type ReactNode,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";
import type { Socket } from "socket.io-client";
import {
  type ConnectionState,
  type SocketState,
  agentSocket,
  connectAll,
  disconnectAll,
  eventsSocket,
  getSocketState,
  onStateChange,
  terminalSocket,
} from "@/lib/websocket-client";

// ---------------------------------------------------------------------------
// Context value
// ---------------------------------------------------------------------------

export interface WebSocketContextValue {
  /** Per-namespace connection state. */
  state: SocketState;
  /** Terminal namespace socket. */
  terminal: Socket;
  /** Agent namespace socket. */
  agent: Socket;
  /** General events namespace socket. */
  events: Socket;
  /** Whether all sockets are connected. */
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

// ---------------------------------------------------------------------------
// External store adapter for useSyncExternalStore
// ---------------------------------------------------------------------------

let cachedState: SocketState = getSocketState();

function subscribe(callback: () => void): () => void {
  return onStateChange((next) => {
    cachedState = next;
    callback();
  });
}

function getSnapshot(): SocketState {
  return cachedState;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const state = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  // Connect on mount, disconnect on unmount.
  useEffect(() => {
    connectAll();
    return () => {
      disconnectAll();
    };
  }, []);

  const value = useMemo<WebSocketContextValue>(
    () => ({
      state,
      terminal: terminalSocket,
      agent: agentSocket,
      events: eventsSocket,
      isConnected:
        state.terminal === "connected" &&
        state.agent === "connected" &&
        state.events === "connected",
    }),
    [state],
  );

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWebSocket(): WebSocketContextValue {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return ctx;
}

/** Convenience hook returning a single namespace's connection state. */
export function useSocketState(ns: keyof SocketState): ConnectionState {
  const { state } = useWebSocket();
  return state[ns];
}
