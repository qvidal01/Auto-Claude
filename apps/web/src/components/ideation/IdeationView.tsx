"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Lightbulb, Sparkles, Loader2 } from "lucide-react";
import { useIdeationStore } from "@/stores/ideation-store";
import type {
  Idea,
  IdeationType,
  IdeationStatus,
} from "@/stores/ideation-store";
import { apiClient } from "@/lib/data/api-client";
import { IdeationHeader } from "./IdeationHeader";
import { IdeationFilters } from "./IdeationFilters";
import { IdeaCard } from "./IdeaCard";
import { IdeaDetailPanel } from "./IdeaDetailPanel";
import { GenerationProgress } from "./GenerationProgress";

interface IdeationViewProps {
  projectId: string;
}

export function IdeationView({ projectId }: IdeationViewProps) {
  const { t } = useTranslation("views");
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null);
  const [activeType, setActiveType] = useState<IdeationType | "all">("all");
  const [activeStatus, setActiveStatus] = useState<IdeationStatus | "all">(
    "all",
  );
  const [isLoading, setIsLoading] = useState(false);

  const {
    session,
    isGenerating,
    generationStatus,
    typeStates,
    logs,
    setSession,
    setIsGenerating,
    setGenerationStatus,
    dismissIdea,
    dismissAllIdeas,
    deleteIdea,
    setCurrentProjectId,
    initializeTypeStates,
    setTypeState,
    addIdeasForType,
    addLog,
    clearLogs,
  } = useIdeationStore();

  // Set project context
  useEffect(() => {
    setCurrentProjectId(projectId);
  }, [projectId, setCurrentProjectId]);

  // Fetch existing ideas on mount
  const fetchIdeas = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.getIdeas(projectId);
      if (response.ideas && Array.isArray(response.ideas)) {
        setSession({
          id: `session-${Date.now()}`,
          projectId,
          ideas: response.ideas as Idea[],
          createdAt: new Date(),
          updatedAt: new Date(),
        });
      }
    } catch {
      // Ideas may not exist yet
    } finally {
      setIsLoading(false);
    }
  }, [projectId, setSession]);

  useEffect(() => {
    fetchIdeas();
  }, [fetchIdeas]);

  // Generate ideas
  const handleGenerate = async () => {
    setIsGenerating(true);
    clearLogs();
    setGenerationStatus({
      phase: "analyzing",
      progress: 0,
      message: t("ideation.analyzingProject"),
    });

    const types: IdeationType[] = [
      "code_improvements",
      "ui_ux_improvements",
      "documentation_gaps",
      "security_hardening",
      "performance_optimizations",
      "code_quality",
    ];
    initializeTypeStates(types);

    try {
      const response = await apiClient.generateIdeas(projectId);
      if (response.ideas && Array.isArray(response.ideas)) {
        for (const type of types) {
          const typeIdeas = (response.ideas as Idea[]).filter(
            (i) => i.type === type,
          );
          if (typeIdeas.length > 0) {
            addIdeasForType(type, typeIdeas);
          }
          setTypeState(type, typeIdeas.length > 0 ? "completed" : "failed");
        }
      }
      setGenerationStatus({
        phase: "complete",
        progress: 100,
        message: t("ideation.generateComplete"),
      });
    } catch {
      setGenerationStatus({
        phase: "error",
        progress: 0,
        message: t("ideation.generateError"),
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleConvert = (idea: Idea) => {
    // TODO: integrate with task creation flow
    addLog(`Converting idea "${idea.title}" to task...`);
  };

  const handleDismiss = (idea: Idea) => {
    dismissIdea(idea.id);
    if (selectedIdea?.id === idea.id) {
      setSelectedIdea(null);
    }
  };

  const handleDelete = (ideaId: string) => {
    deleteIdea(ideaId);
    if (selectedIdea?.id === ideaId) {
      setSelectedIdea(null);
    }
  };

  // Filtered ideas
  const ideas = session?.ideas ?? [];
  const filteredIdeas = useMemo(() => {
    return ideas.filter((idea) => {
      if (activeType !== "all" && idea.type !== activeType) return false;
      if (activeStatus !== "all" && idea.status !== activeStatus) return false;
      return true;
    });
  }, [ideas, activeType, activeStatus]);

  // Type counts for filter badges
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const idea of ideas) {
      counts[idea.type] = (counts[idea.type] ?? 0) + 1;
    }
    return counts;
  }, [ideas]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4 text-sm text-muted-foreground">
          {t("ideation.loading")}
        </p>
      </div>
    );
  }

  // Generation in progress
  if (isGenerating) {
    return (
      <GenerationProgress
        typeStates={typeStates}
        logs={logs}
        progress={generationStatus.progress}
        message={generationStatus.message}
      />
    );
  }

  // Empty state
  if (!session || ideas.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Lightbulb className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h2 className="mb-3 text-xl font-semibold">
            {t("ideation.empty.title")}
          </h2>
          <p className="mb-6 text-sm text-muted-foreground">
            {t("ideation.empty.description")}
          </p>
          <button
            className="flex items-center gap-2 mx-auto rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={handleGenerate}
          >
            <Sparkles className="h-4 w-4" />
            {t("ideation.empty.generate")}
          </button>
        </div>
      </div>
    );
  }

  // Main view
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <IdeationHeader
        ideaCount={ideas.length}
        isGenerating={isGenerating}
        onGenerate={handleGenerate}
        onRefresh={fetchIdeas}
        onDismissAll={dismissAllIdeas}
        hasIdeas={ideas.length > 0}
      />

      <div className="pt-4">
        <IdeationFilters
          activeType={activeType}
          activeStatus={activeStatus}
          onTypeChange={setActiveType}
          onStatusChange={setActiveStatus}
          typeCounts={typeCounts}
        />
      </div>

      {/* Ideas grid */}
      <div className="flex-1 overflow-auto p-6">
        {filteredIdeas.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">
              {t("ideation.noMatchingIdeas")}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {filteredIdeas.map((idea) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                isSelected={selectedIdea?.id === idea.id}
                onClick={() => setSelectedIdea(idea)}
                onConvert={handleConvert}
                onDismiss={handleDismiss}
              />
            ))}
          </div>
        )}
      </div>

      {/* Detail panel */}
      {selectedIdea && (
        <IdeaDetailPanel
          idea={selectedIdea}
          onClose={() => setSelectedIdea(null)}
          onConvert={handleConvert}
          onDismiss={handleDismiss}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
