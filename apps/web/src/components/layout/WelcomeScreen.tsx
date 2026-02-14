"use client";

import { Sparkles, ArrowRight } from "lucide-react";

export function WelcomeScreen() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mb-6 flex justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <Sparkles className="h-8 w-8 text-primary" />
          </div>
        </div>
        <h1 className="mb-3 text-2xl font-bold">Welcome to Auto Claude</h1>
        <p className="mb-8 text-muted-foreground">
          Get started by connecting a project. Auto Claude will help you manage
          tasks, generate roadmaps, review code, and more.
        </p>
        <div className="space-y-3">
          <button className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            Connect a Project
            <ArrowRight className="h-4 w-4" />
          </button>
          <p className="text-xs text-muted-foreground">
            Point Auto Claude at a local project directory to get started.
          </p>
        </div>
      </div>
    </div>
  );
}
