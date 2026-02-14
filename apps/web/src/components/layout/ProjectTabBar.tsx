"use client";

import { useState } from "react";
import { X, Plus } from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useProjectStore } from "@/stores/project-store";
import { useTranslation } from "react-i18next";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Project } from "@auto-claude/types";

interface SortableTabProps {
  project: Project;
  isActive: boolean;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
}

function SortableTab({ project, isActive, onSelect, onClose }: SortableTabProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: project.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={cn(
        "group flex items-center gap-2 border-r border-border px-4 py-2 text-sm cursor-pointer transition-colors min-w-0",
        isActive
          ? "bg-background text-foreground"
          : "bg-card/50 text-muted-foreground hover:bg-accent/50"
      )}
      onClick={() => onSelect(project.id)}
    >
      <div className="w-1.5 h-4 rounded-full bg-muted-foreground/30 shrink-0" />
      <span className="truncate max-w-[150px]">{project.name}</span>
      <button
        className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 hover:bg-accent rounded-sm p-0.5"
        onClick={(e) => {
          e.stopPropagation();
          onClose(project.id);
        }}
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

function TabOverlay({ project }: { project: Project }) {
  return (
    <div className="flex items-center gap-2 border border-border rounded-md bg-background px-4 py-2 text-sm shadow-lg">
      <div className="w-1.5 h-4 rounded-full bg-muted-foreground/30 shrink-0" />
      <span className="truncate max-w-[150px]">{project.name}</span>
    </div>
  );
}

export function ProjectTabBar() {
  const projects = useProjectStore((s) => s.projects);
  const openProjectIds = useProjectStore((s) => s.openProjectIds);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const setActiveProject = useProjectStore((s) => s.setActiveProject);
  const closeProjectTab = useProjectStore((s) => s.closeProjectTab);
  const reorderTabs = useProjectStore((s) => s.reorderTabs);
  const { t } = useTranslation("layout");

  const [activeDragProject, setActiveDragProject] = useState<Project | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const projectTabs = openProjectIds
    .map((id) => projects.find((p) => p.id === id))
    .filter((p): p is Project => p !== undefined);

  if (projectTabs.length === 0) return null;

  const handleDragStart = (event: DragStartEvent) => {
    const project = projectTabs.find((p) => p.id === event.active.id);
    setActiveDragProject(project ?? null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragProject(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = openProjectIds.indexOf(active.id as string);
    const newIndex = openProjectIds.indexOf(over.id as string);
    if (oldIndex !== -1 && newIndex !== -1) {
      reorderTabs(oldIndex, newIndex);
    }
  };

  return (
    <div className="flex items-center border-b border-border bg-card/50">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex flex-1 items-center overflow-x-auto">
          <SortableContext
            items={projectTabs.map((p) => p.id)}
            strategy={horizontalListSortingStrategy}
          >
            {projectTabs.map((project) => (
              <SortableTab
                key={project.id}
                project={project}
                isActive={project.id === activeProjectId}
                onSelect={setActiveProject}
                onClose={closeProjectTab}
              />
            ))}
          </SortableContext>
        </div>
        <DragOverlay>
          {activeDragProject ? <TabOverlay project={activeDragProject} /> : null}
        </DragOverlay>
      </DndContext>
      <button
        className="flex h-full items-center px-3 text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
        aria-label={t("projectTabBar.addProject")}
      >
        <Plus className="h-4 w-4" />
      </button>
    </div>
  );
}
