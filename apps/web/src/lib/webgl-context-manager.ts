/**
 * WebGL Context Manager
 *
 * Manages WebGL context lifecycle with LRU eviction to prevent
 * browser WebGL context exhaustion (typically 8-16 limit).
 *
 * Adapted from the Electron app's context manager for web usage.
 */

import { WebglAddon } from '@xterm/addon-webgl';
import type { Terminal } from '@xterm/xterm';

// ---------------------------------------------------------------------------
// WebGL utility helpers (inlined for web — no Electron dependency)
// ---------------------------------------------------------------------------

function supportsWebGL2(): boolean {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    return gl !== null;
  } catch {
    return false;
  }
}

function isSafari(): boolean {
  try {
    const ua = navigator.userAgent.toLowerCase();
    return ua.includes('safari') && !ua.includes('chrome') && !ua.includes('chromium');
  } catch {
    return false;
  }
}

function getMaxWebGLContexts(): number {
  let max = 8;
  try {
    const ua = navigator.userAgent.toLowerCase();
    if (ua.includes('chrome') || ua.includes('chromium')) {
      max = 16;
    } else if (ua.includes('firefox')) {
      max = 32;
    }
  } catch {
    // fallback
  }
  return max;
}

// ---------------------------------------------------------------------------
// Manager
// ---------------------------------------------------------------------------

class WebGLContextManager {
  private static instance: WebGLContextManager;
  private readonly MAX_CONTEXTS: number;
  private activeContexts = new Map<string, WebglAddon>();
  private terminals = new Map<string, Terminal>();
  private contextQueue: string[] = []; // LRU tracking
  readonly isSupported: boolean;

  private constructor() {
    const safariDetected = isSafari();
    this.isSupported = !safariDetected && supportsWebGL2();
    this.MAX_CONTEXTS = Math.min(getMaxWebGLContexts(), 8);
  }

  static getInstance(): WebGLContextManager {
    if (!WebGLContextManager.instance) {
      WebGLContextManager.instance = new WebGLContextManager();
    }
    return WebGLContextManager.instance;
  }

  /** Register a terminal for WebGL management. */
  register(terminalId: string, xterm: Terminal): void {
    this.terminals.set(terminalId, xterm);
  }

  /** Unregister a terminal (called on terminal close). */
  unregister(terminalId: string): void {
    this.release(terminalId);
    this.terminals.delete(terminalId);
    this.contextQueue = this.contextQueue.filter((id) => id !== terminalId);
  }

  /** Acquire a WebGL context for a terminal (called when visible). */
  acquire(terminalId: string): boolean {
    if (!this.isSupported) return false;

    const xterm = this.terminals.get(terminalId);
    if (!xterm) return false;

    // Already has a context — mark as recently used
    if (this.activeContexts.has(terminalId)) {
      this.contextQueue = this.contextQueue.filter((id) => id !== terminalId);
      this.contextQueue.push(terminalId);
      return true;
    }

    // LRU eviction
    if (this.activeContexts.size >= this.MAX_CONTEXTS) {
      const oldest = this.contextQueue.shift();
      if (oldest) this.release(oldest);
    }

    try {
      const addon = new WebglAddon();

      addon.onContextLoss(() => {
        this.activeContexts.delete(terminalId);
        this.contextQueue = this.contextQueue.filter((id) => id !== terminalId);
      });

      xterm.loadAddon(addon);
      this.activeContexts.set(terminalId, addon);
      this.contextQueue.push(terminalId);
      return true;
    } catch {
      return false; // Falls back to canvas renderer automatically
    }
  }

  /** Release a WebGL context (called when terminal becomes hidden). */
  release(terminalId: string): void {
    const addon = this.activeContexts.get(terminalId);
    if (!addon) return;

    try {
      addon.dispose();
    } catch {
      // Context may already be lost
    }

    this.activeContexts.delete(terminalId);
    this.contextQueue = this.contextQueue.filter((id) => id !== terminalId);
  }

  /** Check if a terminal has an active WebGL context. */
  hasContext(terminalId: string): boolean {
    return this.activeContexts.has(terminalId);
  }

  /** Get statistics for debugging. */
  getStats() {
    return {
      isSupported: this.isSupported,
      maxContexts: this.MAX_CONTEXTS,
      activeContexts: this.activeContexts.size,
      registeredTerminals: this.terminals.size,
      contextQueue: [...this.contextQueue],
    };
  }

  /** Force release all contexts. */
  releaseAll(): void {
    for (const id of Array.from(this.activeContexts.keys())) {
      this.release(id);
    }
  }
}

// Export singleton instance
export const webglContextManager = WebGLContextManager.getInstance();
