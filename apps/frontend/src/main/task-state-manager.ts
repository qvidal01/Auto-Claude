import { createActor } from 'xstate';
import type { ActorRefFrom } from 'xstate';
import type { BrowserWindow } from 'electron';
import type { TaskEventPayload } from './agent/task-event-schema';
import type { Project, Task, TaskStatus, ReviewReason } from '../shared/types';
import { taskMachine, type TaskEvent } from '../shared/state-machines';
import { IPC_CHANNELS } from '../shared/constants';
import { safeSendToRenderer } from './ipc-handlers/utils';
import { getPlanPath, persistPlanStatusAndReasonSync } from './ipc-handlers/task/plan-file-utils';
import { findTaskWorktree } from './worktree-paths';
import { getSpecsDir, AUTO_BUILD_PATHS } from '../shared/constants';
import { existsSync } from 'fs';
import path from 'path';

type TaskActor = ActorRefFrom<typeof taskMachine>;

interface TaskContextEntry {
  task: Task;
  project: Project;
}

const TERMINAL_EVENTS = new Set<string>([
  'QA_PASSED',
  'PLANNING_FAILED',
  'CODING_FAILED',
  'QA_MAX_ITERATIONS',
  'QA_AGENT_ERROR',
  'ALL_SUBTASKS_DONE'
]);

export class TaskStateManager {
  private actors = new Map<string, TaskActor>();
  private lastSequenceByTask = new Map<string, number>();
  private lastStateByTask = new Map<string, string>();
  private taskContextById = new Map<string, TaskContextEntry>();
  private terminalEventSeen = new Set<string>();
  private getMainWindow: (() => BrowserWindow | null) | null = null;

  configure(getMainWindow: () => BrowserWindow | null): void {
    this.getMainWindow = getMainWindow;
  }

  handleTaskEvent(taskId: string, event: TaskEventPayload, task: Task, project: Project): boolean {
    if (!this.isNewSequence(taskId, event.sequence)) {
      return false;
    }
    this.setTaskContext(taskId, task, project);
    this.lastSequenceByTask.set(taskId, event.sequence);

    if (TERMINAL_EVENTS.has(event.type)) {
      this.terminalEventSeen.add(taskId);
    }

    const actor = this.getOrCreateActor(taskId);
    actor.send(event as TaskEvent);
    return true;
  }

  handleProcessExited(
    taskId: string,
    exitCode: number | null,
    task?: Task,
    project?: Project
  ): void {
    if (task && project) {
      this.setTaskContext(taskId, task, project);
    }
    if (this.terminalEventSeen.has(taskId)) {
      return;
    }
    const actor = this.getOrCreateActor(taskId);
    actor.send({
      type: 'PROCESS_EXITED',
      exitCode: exitCode ?? -1,
      unexpected: true
    } satisfies TaskEvent);
  }

  handleUiEvent(taskId: string, event: TaskEvent, task: Task, project: Project): void {
    this.setTaskContext(taskId, task, project);
    const actor = this.getOrCreateActor(taskId);
    actor.send(event);
  }

  handleManualStatusChange(taskId: string, status: TaskStatus, task: Task, project: Project): boolean {
    switch (status) {
      case 'done':
        this.handleUiEvent(taskId, { type: 'MARK_DONE' }, task, project);
        return true;
      case 'pr_created':
        this.handleUiEvent(
          taskId,
          { type: 'PR_CREATED', prUrl: task.metadata?.prUrl ?? '' },
          task,
          project
        );
        return true;
      case 'in_progress':
        if (task.reviewReason === 'plan_review') {
          this.handleUiEvent(taskId, { type: 'PLAN_APPROVED' }, task, project);
        } else {
          this.handleUiEvent(taskId, { type: 'USER_RESUMED' }, task, project);
        }
        return true;
      case 'backlog':
        this.handleUiEvent(taskId, { type: 'USER_STOPPED', hasPlan: false }, task, project);
        return true;
      default:
        return false;
    }
  }

  setLastSequence(taskId: string, sequence: number): void {
    this.lastSequenceByTask.set(taskId, sequence);
  }

  getLastSequence(taskId: string): number | undefined {
    return this.lastSequenceByTask.get(taskId);
  }

  clearTask(taskId: string): void {
    this.lastSequenceByTask.delete(taskId);
    this.lastStateByTask.delete(taskId);
    this.terminalEventSeen.delete(taskId);
    this.taskContextById.delete(taskId);
    const actor = this.actors.get(taskId);
    if (actor) {
      actor.stop();
      this.actors.delete(taskId);
    }
  }

  private setTaskContext(taskId: string, task: Task, project: Project): void {
    this.taskContextById.set(taskId, { task, project });
  }

  private getOrCreateActor(taskId: string): TaskActor {
    const existing = this.actors.get(taskId);
    if (existing) {
      return existing;
    }

    const contextEntry = this.taskContextById.get(taskId);
    const snapshot = contextEntry
      ? this.buildSnapshotFromTask(contextEntry.task)
      : undefined;
    const actor = snapshot
      ? createActor(taskMachine, { snapshot })
      : createActor(taskMachine);
    actor.subscribe((snapshot) => {
      const stateValue = String(snapshot.value);
      const lastState = this.lastStateByTask.get(taskId);
      if (lastState === stateValue) {
        return;
      }
      this.lastStateByTask.set(taskId, stateValue);

      const contextEntry = this.taskContextById.get(taskId);
      if (!contextEntry) {
        return;
      }
      const { task, project } = contextEntry;
      const { status, reviewReason } = mapStateToLegacy(
        stateValue,
        snapshot.context.reviewReason
      );

      this.persistStatus(task, project, status, reviewReason);
      this.emitStatus(taskId, status, reviewReason, project.id);
    });

    actor.start();
    this.actors.set(taskId, actor);
    return actor;
  }

  private persistStatus(
    task: Task,
    project: Project,
    status: TaskStatus,
    reviewReason?: ReviewReason
  ): void {
    const mainPlanPath = getPlanPath(project, task);
    persistPlanStatusAndReasonSync(mainPlanPath, status, reviewReason, project.id);

    const worktreePath = findTaskWorktree(project.path, task.specId);
    if (!worktreePath) return;

    const specsBaseDir = getSpecsDir(project.autoBuildPath);
    const worktreePlanPath = path.join(
      worktreePath,
      specsBaseDir,
      task.specId,
      AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN
    );
    if (existsSync(worktreePlanPath)) {
      persistPlanStatusAndReasonSync(worktreePlanPath, status, reviewReason, project.id);
    }
  }

  private emitStatus(
    taskId: string,
    status: TaskStatus,
    reviewReason: ReviewReason | undefined,
    projectId?: string
  ): void {
    if (!this.getMainWindow) return;
    safeSendToRenderer(
      this.getMainWindow,
      IPC_CHANNELS.TASK_STATUS_CHANGE,
      taskId,
      status,
      projectId,
      reviewReason
    );
  }

  private isNewSequence(taskId: string, sequence: number): boolean {
    const last = this.lastSequenceByTask.get(taskId);
    return last === undefined || sequence > last;
  }

  private buildSnapshotFromTask(task: Task) {
    const status = task.status;
    const reviewReason = task.reviewReason;
    let stateValue: string = 'backlog';
    let contextReviewReason: ReviewReason | undefined;

    switch (status) {
      case 'in_progress':
        stateValue = 'coding';
        break;
      case 'ai_review':
        stateValue = 'qa_review';
        break;
      case 'human_review':
        stateValue = reviewReason === 'plan_review' ? 'plan_review' : 'human_review';
        contextReviewReason = reviewReason;
        break;
      case 'pr_created':
        stateValue = 'pr_created';
        break;
      case 'done':
        stateValue = 'done';
        break;
      case 'error':
        stateValue = 'error';
        contextReviewReason = reviewReason ?? 'errors';
        break;
      case 'backlog':
      default:
        stateValue = 'backlog';
        break;
    }

    return taskMachine.resolveState({
      value: stateValue,
      context: {
        reviewReason: contextReviewReason
      }
    });
  }
}

export const taskStateManager = new TaskStateManager();

function mapStateToLegacy(
  state: string,
  reviewReason?: ReviewReason
): { status: TaskStatus; reviewReason?: ReviewReason } {
  switch (state) {
    case 'backlog':
      return { status: 'backlog' };
    case 'planning':
    case 'coding':
      return { status: 'in_progress' };
    case 'plan_review':
      return { status: 'human_review', reviewReason: 'plan_review' };
    case 'qa_review':
    case 'qa_fixing':
      return { status: 'ai_review' };
    case 'human_review':
      return { status: 'human_review', reviewReason };
    case 'error':
      return { status: 'human_review', reviewReason: 'errors' };
    case 'creating_pr':
      return { status: 'human_review', reviewReason: 'completed' };
    case 'pr_created':
      return { status: 'pr_created' };
    case 'done':
      return { status: 'done' };
    default:
      return { status: 'backlog' };
  }
}
