import { useState, useEffect, useRef, useCallback } from "react";
import { PipelineStage, INITIAL_DEMO_STAGES } from "./types";

interface UseMockPipelineOptions {
  autoStart?: boolean;
  query?: string;
  onComplete?: () => void;
}

export function useMockPipeline({
  autoStart = true,
  query,
  onComplete,
}: UseMockPipelineOptions = {}) {
  const [stages, setStages] = useState<PipelineStage[]>(() =>
    INITIAL_DEMO_STAGES.map((s) => ({ ...s }))
  );
  const [isRunning, setIsRunning] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [activeStageId, setActiveStageId] = useState<string | null>(null);

  const timersRef = useRef<NodeJS.Timeout[]>([]);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const clearAllTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const setStep = useCallback((step: number) => {
    setStages(
      INITIAL_DEMO_STAGES.map((stage, idx) => ({
        ...stage,
        status: idx < step ? "completed" : idx === step ? "running" : "pending",
        message: idx === step ? stage.supportingStatus : null,
      }))
    );
  }, []);

  const runSimulation = useCallback(() => {
    clearAllTimers();
    setIsRunning(true);
    setIsCompleted(false);

    // Step 0: Stage 1 running
    setActiveStageId(INITIAL_DEMO_STAGES[0]?.id ?? "query-expansion");
    setStep(0);

    // Step 1: Stage 2 running
    const t1 = setTimeout(() => {
      setActiveStageId(INITIAL_DEMO_STAGES[1]?.id ?? "academic-search");
      setStep(1);
    }, 1600);

    // Step 2: Stage 3 running
    const t2 = setTimeout(() => {
      setActiveStageId(INITIAL_DEMO_STAGES[2]?.id ?? "relevance-screening");
      setStep(2);
    }, 3500);

    // Step 3: All completed
    const t3 = setTimeout(() => {
      setActiveStageId(null);
      setIsRunning(false);
      setIsCompleted(true);
      setStages(INITIAL_DEMO_STAGES.map((s) => ({ ...s, status: "completed", message: null })));
      onCompleteRef.current?.();
    }, 5400);

    timersRef.current = [t1, t2, t3];
  }, [clearAllTimers, setStep]);

  const resetPipeline = useCallback(() => {
    clearAllTimers();
    setIsRunning(false);
    setIsCompleted(false);
    setActiveStageId(null);
    setStages(INITIAL_DEMO_STAGES.map((s) => ({ ...s })));
  }, [clearAllTimers]);

  useEffect(() => {
    if (autoStart) {
      runSimulation();
    }
    return clearAllTimers;
  }, [autoStart, query, runSimulation, clearAllTimers]);

  return {
    stages,
    isRunning,
    isCompleted,
    activeStageId,
    restartPipeline: runSimulation,
    resetPipeline,
    isMock: true,
  };
}
