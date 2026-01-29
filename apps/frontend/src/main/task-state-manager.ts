import type { TaskEventPayload } from './agent/task-event-schema';

export class TaskStateManager {
  private lastSequenceByTask = new Map<string, number>();

  handleTaskEvent(taskId: string, event: TaskEventPayload): TaskEventPayload | null {
    if (!this.isNewSequence(taskId, event.sequence)) {
      return null;
    }
    this.lastSequenceByTask.set(taskId, event.sequence);
    return event;
  }

  setLastSequence(taskId: string, sequence: number): void {
    this.lastSequenceByTask.set(taskId, sequence);
  }

  getLastSequence(taskId: string): number | undefined {
    return this.lastSequenceByTask.get(taskId);
  }

  clearTask(taskId: string): void {
    this.lastSequenceByTask.delete(taskId);
  }

  private isNewSequence(taskId: string, sequence: number): boolean {
    const last = this.lastSequenceByTask.get(taskId);
    return last === undefined || sequence > last;
  }
}

export const taskStateManager = new TaskStateManager();
