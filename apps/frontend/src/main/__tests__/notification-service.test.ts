/**
 * Unit tests for NotificationService
 *
 * Story Reference: Story 5.6 - Implement Checkpoint Notifications
 * Tests notification sending, settings checking, and badge management.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Electron modules before importing notification-service
vi.mock('electron', () => {
  // Create the mock constructor with isSupported attached
  const NotificationMock = Object.assign(
    vi.fn().mockImplementation(function (this: object, opts: { title: string; body: string; silent: boolean }) {
      Object.assign(this, opts);
      return {
        show: vi.fn(),
        on: vi.fn(),
        ...opts
      };
    }),
    { isSupported: () => true }
  );

  return {
    Notification: NotificationMock,
    shell: {
      beep: vi.fn()
    },
    app: {
      dock: {
        setBadge: vi.fn()
      },
      setBadgeCount: vi.fn()
    }
  };
});

// Mock the project-store
vi.mock('../project-store', () => ({
  projectStore: {
    getProjects: vi.fn().mockReturnValue([])
  }
}));

// Mock IPC_CHANNELS
vi.mock('../../shared/constants', () => ({
  IPC_CHANNELS: {
    CHECKPOINT_REACHED: 'checkpoint:reached'
  }
}));

describe('NotificationService', () => {
  let notificationService: typeof import('../notification-service').notificationService;
  let mockNotification: ReturnType<typeof vi.fn>;
  let mockShell: { beep: ReturnType<typeof vi.fn> };
  let mockApp: { dock: { setBadge: ReturnType<typeof vi.fn> }; setBadgeCount: ReturnType<typeof vi.fn> };
  let mockBrowserWindow: { isMinimized: ReturnType<typeof vi.fn>; restore: ReturnType<typeof vi.fn>; focus: ReturnType<typeof vi.fn>; webContents: { send: ReturnType<typeof vi.fn> } };

  beforeEach(async () => {
    vi.resetModules();

    // Re-import after resetting modules
    const electron = await import('electron');
    mockNotification = electron.Notification as unknown as ReturnType<typeof vi.fn>;
    mockShell = electron.shell as unknown as { beep: ReturnType<typeof vi.fn> };
    mockApp = electron.app as unknown as { dock: { setBadge: ReturnType<typeof vi.fn> }; setBadgeCount: ReturnType<typeof vi.fn> };

    // Mock BrowserWindow
    mockBrowserWindow = {
      isMinimized: vi.fn().mockReturnValue(false),
      restore: vi.fn(),
      focus: vi.fn(),
      webContents: {
        send: vi.fn()
      }
    };

    // Import the service
    const module = await import('../notification-service');
    notificationService = module.notificationService;

    // Initialize with mock window getter
    notificationService.initialize(() => mockBrowserWindow as unknown as import('electron').BrowserWindow);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe('initialization', () => {
    it('should initialize with main window getter', () => {
      // The service should be initialized from beforeEach
      expect(notificationService).toBeDefined();
    });
  });

  describe('notifyTaskComplete', () => {
    it('should create notification with correct title and body', async () => {
      // Mock Notification.isSupported
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      notificationService.notifyTaskComplete('Test Task', 'project-1', 'task-1');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Task Complete',
        body: '"Test Task" has completed and is ready for review'
      }));
    });
  });

  describe('notifyTaskFailed', () => {
    it('should create notification with correct title and body', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      notificationService.notifyTaskFailed('Failed Task', 'project-1', 'task-1');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Task Failed',
        body: '"Failed Task" encountered an error'
      }));
    });
  });

  describe('notifyReviewNeeded', () => {
    it('should create notification with correct title and body', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      notificationService.notifyReviewNeeded('Review Task', 'project-1', 'task-1');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Review Needed',
        body: '"Review Task" is ready for your review'
      }));
    });
  });

  describe('notifyTaskEscalated', () => {
    it('should create notification with error summary if provided', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      notificationService.notifyTaskEscalated('Escalated Task', 'project-1', 'task-1', 'Build failed');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Task Needs Attention',
        body: '"Escalated Task" needs attention: Build failed'
      }));
    });

    it('should create notification with default message if no error summary', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      notificationService.notifyTaskEscalated('Escalated Task', 'project-1', 'task-1');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Task Needs Attention',
        body: '"Escalated Task" could not complete and needs your attention'
      }));
    });
  });

  describe('notifyCheckpointReached', () => {
    it('should create notification with checkpoint phase and description', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      const checkpoint = {
        checkpointId: 'cp-1',
        phase: 'Planning',
        description: 'Please review the implementation plan',
        timestamp: new Date().toISOString()
      };

      notificationService.notifyCheckpointReached('task-1', checkpoint, 'project-1');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Checkpoint: Planning',
        body: 'Please review the implementation plan'
      }));
    });

    it('should use default description if none provided', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      const checkpoint = {
        checkpointId: 'cp-1',
        phase: 'Coding',
        timestamp: new Date().toISOString()
      };

      notificationService.notifyCheckpointReached('task-1', checkpoint, 'project-1');

      expect(mockNotification).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Checkpoint: Coding',
        body: 'Your review is needed to continue'
      }));
    });

    it('should set tray badge on macOS', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Mock process.platform for macOS
      const originalPlatform = process.platform;
      Object.defineProperty(process, 'platform', { value: 'darwin' });

      const checkpoint = {
        checkpointId: 'cp-1',
        phase: 'QA',
        timestamp: new Date().toISOString()
      };

      notificationService.notifyCheckpointReached('task-1', checkpoint);

      expect(mockApp.dock.setBadge).toHaveBeenCalledWith('!');

      // Restore platform
      Object.defineProperty(process, 'platform', { value: originalPlatform });
    });

    it('should set badge count on Linux', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Mock process.platform for Linux
      const originalPlatform = process.platform;
      Object.defineProperty(process, 'platform', { value: 'linux' });

      const checkpoint = {
        checkpointId: 'cp-1',
        phase: 'Coding',
        timestamp: new Date().toISOString()
      };

      notificationService.notifyCheckpointReached('task-1', checkpoint);

      expect(mockApp.setBadgeCount).toHaveBeenCalledWith(1);

      // Restore platform
      Object.defineProperty(process, 'platform', { value: originalPlatform });
    });
  });

  describe('clearCheckpointBadge', () => {
    it('should clear tray badge on macOS', async () => {
      // Mock process.platform for macOS
      const originalPlatform = process.platform;
      Object.defineProperty(process, 'platform', { value: 'darwin' });

      notificationService.clearCheckpointBadge();

      expect(mockApp.dock.setBadge).toHaveBeenCalledWith('');

      // Restore platform
      Object.defineProperty(process, 'platform', { value: originalPlatform });
    });

    it('should clear badge count on Linux', async () => {
      // Mock process.platform for Linux
      const originalPlatform = process.platform;
      Object.defineProperty(process, 'platform', { value: 'linux' });

      notificationService.clearCheckpointBadge();

      expect(mockApp.setBadgeCount).toHaveBeenCalledWith(0);

      // Restore platform
      Object.defineProperty(process, 'platform', { value: originalPlatform });
    });
  });

  describe('notification settings', () => {
    it('should play sound when enabled in settings', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Mock project store with sound enabled
      const { projectStore } = await import('../project-store');
      (projectStore.getProjects as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: 'project-1',
          settings: {
            notifications: {
              onTaskComplete: true,
              onTaskFailed: true,
              onReviewNeeded: true,
              onCheckpointReached: true,
              sound: true
            }
          }
        }
      ]);

      notificationService.notifyTaskComplete('Test Task', 'project-1', 'task-1');

      expect(mockShell.beep).toHaveBeenCalled();
    });

    it('should not send notification if type is disabled in settings', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Mock project store with onTaskComplete disabled
      const { projectStore } = await import('../project-store');
      (projectStore.getProjects as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: 'project-1',
          settings: {
            notifications: {
              onTaskComplete: false, // Disabled
              onTaskFailed: true,
              onReviewNeeded: true,
              onCheckpointReached: true,
              sound: false
            }
          }
        }
      ]);

      notificationService.notifyTaskComplete('Test Task', 'project-1', 'task-1');

      expect(mockNotification).not.toHaveBeenCalled();
    });

    it('should not send checkpoint notification if disabled in settings', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Mock project store with onCheckpointReached disabled
      const { projectStore } = await import('../project-store');
      (projectStore.getProjects as ReturnType<typeof vi.fn>).mockReturnValue([
        {
          id: 'project-1',
          settings: {
            notifications: {
              onTaskComplete: true,
              onTaskFailed: true,
              onReviewNeeded: true,
              onCheckpointReached: false, // Disabled
              sound: false
            }
          }
        }
      ]);

      const checkpoint = {
        checkpointId: 'cp-1',
        phase: 'Planning',
        timestamp: new Date().toISOString()
      };

      notificationService.notifyCheckpointReached('task-1', checkpoint, 'project-1');

      expect(mockNotification).not.toHaveBeenCalled();
    });
  });

  describe('notification click handling', () => {
    it('should focus window when notification is clicked', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Track the click handler with type assertion
      const clickHandlerRef: { current: (() => void) | null } = { current: null };
      mockNotification.mockImplementation(function (this: object, opts: { title: string; body: string; silent: boolean }) {
        const instance = {
          show: vi.fn(),
          on: vi.fn((event: string, handler: () => void) => {
            if (event === 'click') {
              clickHandlerRef.current = handler;
            }
          }),
          ...opts
        };
        Object.assign(this, instance);
        return instance;
      });

      notificationService.notifyTaskComplete('Test Task', 'project-1', 'task-1');

      // Simulate click
      if (clickHandlerRef.current) {
        clickHandlerRef.current();
      }

      expect(mockBrowserWindow.focus).toHaveBeenCalled();
    });

    it('should restore window if minimized when notification is clicked', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;
      mockBrowserWindow.isMinimized.mockReturnValue(true);

      // Track the click handler with type assertion
      const clickHandlerRef: { current: (() => void) | null } = { current: null };
      mockNotification.mockImplementation(function (this: object, opts: { title: string; body: string; silent: boolean }) {
        const instance = {
          show: vi.fn(),
          on: vi.fn((event: string, handler: () => void) => {
            if (event === 'click') {
              clickHandlerRef.current = handler;
            }
          }),
          ...opts
        };
        Object.assign(this, instance);
        return instance;
      });

      notificationService.notifyTaskComplete('Test Task', 'project-1', 'task-1');

      // Simulate click
      if (clickHandlerRef.current) {
        clickHandlerRef.current();
      }

      expect(mockBrowserWindow.restore).toHaveBeenCalled();
      expect(mockBrowserWindow.focus).toHaveBeenCalled();
    });

    it('should send IPC event when checkpoint notification is clicked', async () => {
      // Reset projectStore mock to return empty array (use default settings)
      const { projectStore } = await import('../project-store');
      (projectStore.getProjects as ReturnType<typeof vi.fn>).mockReturnValue([]);

      // Track the click handler
      let capturedClickHandler: (() => void) | null = null;

      // Set up mock implementation to capture click handler while preserving isSupported
      const originalIsSupported = (mockNotification as unknown as { isSupported: () => boolean }).isSupported;
      mockNotification.mockImplementation(function (this: object, opts: { title: string; body: string; silent: boolean }) {
        const instance = {
          show: vi.fn(),
          on: vi.fn((event: string, handler: () => void) => {
            if (event === 'click') {
              capturedClickHandler = handler;
            }
          }),
          ...opts
        };
        Object.assign(this, instance);
        return instance;
      });
      // Restore isSupported after mockImplementation
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = originalIsSupported;

      const checkpoint = {
        checkpointId: 'cp-test-123',
        phase: 'Planning',
        description: 'Review implementation plan'
      };

      notificationService.notifyCheckpointReached('task-1', checkpoint, 'project-1');

      // Verify handler was captured
      expect(capturedClickHandler).not.toBeNull();

      // Simulate click
      capturedClickHandler!();

      // Verify window was focused
      expect(mockBrowserWindow.focus).toHaveBeenCalled();

      // Verify IPC event was sent with correct parameters
      expect(mockBrowserWindow.webContents.send).toHaveBeenCalledWith(
        'checkpoint:reached',
        'task-1',
        expect.objectContaining({
          checkpointId: 'cp-test-123',
          phase: 'Planning',
          description: 'Review implementation plan'
        }),
        'project-1'
      );
    });

    it('should not send IPC event for non-checkpoint notifications when clicked', async () => {
      (mockNotification as unknown as { isSupported: () => boolean }).isSupported = () => true;

      // Track the click handler
      const clickHandlerRef: { current: (() => void) | null } = { current: null };
      mockNotification.mockImplementation(function (this: object, opts: { title: string; body: string; silent: boolean }) {
        const instance = {
          show: vi.fn(),
          on: vi.fn((event: string, handler: () => void) => {
            if (event === 'click') {
              clickHandlerRef.current = handler;
            }
          }),
          ...opts
        };
        Object.assign(this, instance);
        return instance;
      });

      // Send a regular task notification (not checkpoint)
      notificationService.notifyTaskComplete('Test Task', 'project-1', 'task-1');

      // Simulate click
      if (clickHandlerRef.current) {
        clickHandlerRef.current();
      }

      // Verify focus happened but no IPC event was sent
      expect(mockBrowserWindow.focus).toHaveBeenCalled();
      expect(mockBrowserWindow.webContents.send).not.toHaveBeenCalled();
    });
  });
});
