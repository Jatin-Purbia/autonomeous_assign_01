"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "./api";
import type { ServerMessage, SimEvent, SimState } from "./types";

const WS_URL = API_URL.replace(/^http/, "ws") + "/ws/simulation";
const MAX_HISTORY = 600;
const MAX_EVENTS = 1500;

export type SimStream = {
  state: SimState | null;
  history: Record<number, SimState>; // latest snapshot seen per timestep (for the timeline scrubber)
  events: SimEvent[];
  running: boolean;
  speed: number;
  strategy: string;
  connected: boolean;
  error: string | null;
  send: (cmd: string, value?: number) => void;
  push: (msg: ServerMessage) => void; // feed a state received through REST
  clearError: () => void;
};

/** Live simulation stream over WebSocket with automatic reconnect. */
export function useSimulationStream(): SimStream {
  const [state, setState] = useState<SimState | null>(null);
  const [history, setHistory] = useState<Record<number, SimState>>({});
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [strategy, setStrategy] = useState("local");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastEventIndex = useRef(-1);
  const prevRef = useRef<SimState | null>(null);

  const apply = useCallback((msg: ServerMessage) => {
    if (msg.type === "error") {
      setError(msg.message);
      return;
    }
    const s = msg.state;
    const prev = prevRef.current;
    const wasReset =
      !!prev && (s.time < prev.time || s.scenario.id !== prev.scenario.id || s.events_total < prev.events_total);
    prevRef.current = s;
    if (wasReset) {
      lastEventIndex.current = -1;
      setEvents([]);
    }
    setState(s);
    setHistory((h) => {
      const next = wasReset ? { [s.time]: s } : { ...h, [s.time]: s };
      const keys = Object.keys(next).map(Number).sort((a, b) => a - b);
      if (keys.length > MAX_HISTORY) for (const k of keys.slice(0, keys.length - MAX_HISTORY)) delete next[k];
      return next;
    });
    if (msg.events?.length) {
      setEvents((prev) => {
        const fresh = msg.events!.filter((e) => e.index > lastEventIndex.current);
        if (!fresh.length) return prev;
        lastEventIndex.current = fresh[fresh.length - 1].index;
        return [...prev, ...fresh].slice(-MAX_EVENTS);
      });
    }
    setRunning(msg.running);
    setSpeed(msg.speed);
    setStrategy(msg.strategy);
  }, []);

  useEffect(() => {
    let closed = false;
    let timer: ReturnType<typeof setTimeout>;
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => apply(JSON.parse(e.data) as ServerMessage);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) timer = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      wsRef.current?.close();
    };
  }, [apply]);

  const send = useCallback((cmd: string, value?: number) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ cmd, value }));
  }, []);

  return { state, history, events, running, speed, strategy, connected, error, send, push: apply, clearError: () => setError(null) };
}
