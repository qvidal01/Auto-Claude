'use client';

import { useEffect, useRef, useCallback } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { SerializeAddon } from '@xterm/addon-serialize';
import { terminalSocket } from '@/lib/websocket-client';
import { DEFAULT_TERMINAL_THEME } from '@/lib/terminal-theme';
import { webglContextManager } from '@/lib/webgl-context-manager';
import '@xterm/xterm/css/xterm.css';

interface TerminalPanelProps {
  sessionId: string;
  onResize?: (cols: number, rows: number) => void;
}

/**
 * Terminal panel with xterm.js integration.
 *
 * IMPORTANT: This component must NEVER be statically imported.
 * Always use next/dynamic with { ssr: false }.
 *
 * @example
 * const TerminalPanel = dynamic(
 *   () => import('@/components/terminal/TerminalPanel').then(m => m.TerminalPanel),
 *   { ssr: false }
 * );
 */
export function TerminalPanel({ sessionId, onResize }: TerminalPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const isDisposedRef = useRef(false);

  const fit = useCallback(() => {
    if (isDisposedRef.current || !fitAddonRef.current || !xtermRef.current) return;
    try {
      fitAddonRef.current.fit();
    } catch {
      // Container may not be visible
    }
  }, []);

  // Initialize xterm
  useEffect(() => {
    if (!containerRef.current || xtermRef.current) return;
    isDisposedRef.current = false;

    const xterm = new XTerm({
      cursorBlink: true,
      cursorStyle: 'bar',
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, monospace",
      lineHeight: 1.2,
      theme: DEFAULT_TERMINAL_THEME,
      allowProposedApi: true,
      scrollback: 10_000,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon((_event, uri) => {
      window.open(uri, '_blank', 'noopener,noreferrer');
    });
    const serializeAddon = new SerializeAddon();

    xterm.loadAddon(fitAddon);
    xterm.loadAddon(webLinksAddon);
    xterm.loadAddon(serializeAddon);
    xterm.open(containerRef.current);

    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    // WebGL acceleration with fallback to canvas
    webglContextManager.register(sessionId, xterm);
    webglContextManager.acquire(sessionId);

    // Initial fit
    requestAnimationFrame(() => {
      if (!isDisposedRef.current) fit();
    });

    // Send input to backend via Socket.IO
    const dataDisposable = xterm.onData((data) => {
      terminalSocket.emit('input', { sessionId, data });
    });

    // Notify backend on resize
    const resizeDisposable = xterm.onResize(({ cols, rows }) => {
      terminalSocket.emit('resize', { sessionId, cols, rows });
      onResize?.(cols, rows);
    });

    return () => {
      isDisposedRef.current = true;
      dataDisposable.dispose();
      resizeDisposable.dispose();
      webglContextManager.unregister(sessionId);
      xterm.dispose();
      xtermRef.current = null;
      fitAddonRef.current = null;
    };
  }, [sessionId, fit, onResize]);

  // Listen for output from backend via Socket.IO
  useEffect(() => {
    const handleOutput = (data: { sessionId: string; data: string }) => {
      if (data.sessionId === sessionId && xtermRef.current && !isDisposedRef.current) {
        xtermRef.current.write(data.data);
      }
    };

    terminalSocket.on('output', handleOutput);
    return () => {
      terminalSocket.off('output', handleOutput);
    };
  }, [sessionId]);

  // Resize observer for container size changes
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      if (!isDisposedRef.current) fit();
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, [fit]);

  return (
    <div
      ref={containerRef}
      className="h-full w-full"
      style={{ backgroundColor: DEFAULT_TERMINAL_THEME.background }}
    />
  );
}
