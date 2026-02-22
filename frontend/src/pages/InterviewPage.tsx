import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import ChatInput, { detectEditIntent } from "../components/interview/ChatInput";
import ChatMessage from "../components/interview/ChatMessage";
import { useInterviewStore } from "../stores/interviewStore";
import { api } from "../api/client";

let startInterviewInFlight: Promise<void> | null = null;

function extractFieldName(question: string | undefined): string {
  if (!question) return "answer";
  const q = question.toLowerCase();
  
  if ((q.includes("name") && (q.includes("call you") || q.includes("your name") || q.includes("what's your") || q.includes("what is your"))) ||
      q.includes("may i call you") || q.includes("should i call you") ||
      (q.includes("name") && q.includes("?"))) return "name";
  
  if (q.includes("state") && (q.includes("live") || q.includes("reside") || q.includes("located"))) return "state";
  if (q.includes("city") && (q.includes("live") || q.includes("reside") || q.includes("located"))) return "city";
  
  if (q.includes("retire") && (q.includes("age") || q.includes("when") || q.includes("plan to"))) return "target retirement age";
  if (q.includes("birth year") || q.includes("year were you born") || q.includes("born in")) return "birth year";
  if (q.includes("current age") || q.includes("old are you") || q.includes("your age")) return "age";
  
  if (q.includes("income") || q.includes("salary") || q.includes("earn") || q.includes("make per year")) return "annual income";
  
  if (q.includes("legacy") || q.includes("leave behind") || q.includes("inheritance") || q.includes("estate")) return "legacy goal";
  
  if (q.includes("balance") || q.includes("saved") || q.includes("retirement account") || q.includes("401") || q.includes("ira") || q.includes("savings")) return "retirement balance";
  
  if (q.includes("spend") || q.includes("expenses") || q.includes("monthly") || q.includes("budget")) return "monthly spending";
  
  if (q.includes("success rate") || q.includes("success probability") || 
      q.includes("monte carlo") || q.includes("probability of success") ||
      q.includes("confidence level") || q.includes("plan success")) return "success rate";

  if (q.includes("claim social security") || q.includes("claiming social security") ||
      q.includes("start claiming social security") || q.includes("claiming age")) {
    return "Social Security claiming age";
  }
  
  if (q.includes("employer offer") || q.includes("employer retirement") ||
      (q.includes("401(k)") && q.includes("offer")) || (q.includes("401k") && q.includes("offer")) ||
      (q.includes("employer") && q.includes("plan"))) return "employer plan";
  
  if (q.includes("employer match") || q.includes("company match") ||
      q.includes("matching contribution") || q.includes("does your employer match") ||
      q.includes("what percentage does your employer")) return "employer match";
  
  if ((q.includes("do you contribute") || q.includes("your contribution")) &&
      (q.includes("retirement plan") || q.includes("401"))) return "contribution rate";
  
  if (q.includes("savings rate") || q.includes("percentage") || q.includes("% of your income") || 
      q.includes("contribute") || q.includes("saving")) return "savings rate";
  
  return "answer";
}

function fieldLabelFromPath(fieldPath?: string | null): string | undefined {
  switch (fieldPath) {
    case "client.name":
      return "name";
    case "client.birth_year":
      return "birth year";
    case "location.state":
      return "state";
    case "location.city":
      return "city";
    case "income.current_gross_annual":
      return "annual income";
    case "retirement_philosophy.legacy_goal_total_real":
      return "legacy goal";
    case "accounts.retirement_balance":
      return "retirement balance";
    case "accounts.has_employer_plan":
      return "employer plan";
    case "accounts.employer_match_percent":
      return "employer match";
    case "accounts.employee_contribution_percent":
      return "contribution rate";
    case "accounts.savings_rate_percent":
      return "savings rate";
    case "spending.retirement_monthly_real":
      return "monthly spending";
    case "social_security.claiming_preference":
      return "Social Security claiming age";
    case "retirement_philosophy.success_probability_target":
    case "monte_carlo.required_success_rate":
      return "success rate";
    default:
      return undefined;
  }
}

function formatCorrectionValue(value: string, fieldName: string): string {
  const trimmed = value.trim();
  
  const textFields = ["name", "state", "city", "employer plan"];
  if (textFields.includes(fieldName)) {
    return trimmed;
  }
  
  const percentageFields = ["savings rate", "success rate", "employer match", "contribution rate"];
  if (percentageFields.includes(fieldName) || trimmed.match(/^\d+%$/)) {
    const num = parseFloat(trimmed.replace(/%$/, ""));
    if (!isNaN(num)) return `${num}%`;
    return trimmed;
  }
  
  const monetaryFields = ["annual income", "legacy goal", "retirement balance", "monthly spending"];
  if (monetaryFields.includes(fieldName)) {
    const num = parseInt(trimmed.replace(/[$,]/g, ""), 10);
    if (!isNaN(num)) return "$" + num.toLocaleString("en-US");
    return trimmed;
  }
  
  if (
    fieldName === "age" ||
    fieldName === "target retirement age" ||
    fieldName === "birth year" ||
    fieldName === "Social Security claiming age"
  ) {
    return trimmed;
  }
  
  const numericValue = trimmed.replace(/[$,]/g, "");
  if (numericValue.match(/^\d+$/)) {
    const num = parseInt(numericValue, 10);
    const isLikelyYear = num >= 1900 && num <= 2100 && numericValue.length === 4;
    if (!isNaN(num) && !isLikelyYear && (trimmed.startsWith("$") || num >= 1000)) {
      return "$" + num.toLocaleString("en-US");
    }
  }
  
  return trimmed;
}

function buildCorrectionMessage(fieldName: string, formattedValue: string): string {
  const field = fieldName === "answer" ? "response" : fieldName;
  return `Got it! I've updated your ${field} to ${formattedValue}.`;
}

function parseRawFieldValue(fieldPath: string, displayValue: string): unknown {
  const trimmed = displayValue.trim();

  const booleanFields = ["accounts.has_employer_plan"];
  if (booleanFields.includes(fieldPath)) {
    const lower = trimmed.toLowerCase();
    if (["yes", "true", "1"].includes(lower)) return true;
    if (["no", "false", "0"].includes(lower)) return false;
    return trimmed;
  }

  const integerFields = [
    "income.current_gross_annual",
    "retirement_philosophy.legacy_goal_total_real",
    "accounts.retirement_balance",
    "spending.retirement_monthly_real",
    "client.birth_year",
  ];
  if (integerFields.includes(fieldPath)) {
    const num = parseInt(trimmed.replace(/[$,%]/g, "").replace(/,/g, ""), 10);
    if (!isNaN(num)) return num;
  }

  const floatFields = [
    "accounts.employer_match_percent",
    "accounts.employee_contribution_percent",
    "accounts.savings_rate_percent",
    "retirement_philosophy.success_probability_target",
    "monte_carlo.required_success_rate",
  ];
  if (floatFields.includes(fieldPath)) {
    const num = parseFloat(trimmed.replace(/%$/, ""));
    if (!isNaN(num)) return num / 100;
  }

  const numericValue = trimmed.replace(/[$,]/g, "");
  if (/^\d+(\.\d+)?$/.test(numericValue)) {
    return parseFloat(numericValue);
  }

  return trimmed;
}

export default function InterviewPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const planIdParam = searchParams.get("plan_id") ?? undefined;
  const scrollRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputPanelRef = useRef<HTMLDivElement>(null);
  const [inputCollapsed, setInputCollapsed] = useState(false);
  const [inputPanelHeight, setInputPanelHeight] = useState(96);
  const {
    sessionId,
    planId,
    messages,
    isComplete,
    isLoading,
    isResumed,
    editing,
    phase,
    setSession,
    addMessage,
    setMessages,
    markMessageUpdated,
    setComplete,
    setLoading,
    setResumed,
    setEditing,
    setPhase,
    reset,
  } = useInterviewStore();

  useEffect(() => {
    const staleSession = !planIdParam && !!planId;
    const needsReload = !sessionId || (sessionId && messages.length === 0) || staleSession;
    
    if (!needsReload || startInterviewInFlight) {
      return;
    }
    startInterviewInFlight = startNewInterview().finally(() => {
      startInterviewInFlight = null;
    });
  }, [sessionId, planId, planIdParam, messages.length]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function startNewInterview(): Promise<void> {
    reset();
    setLoading(true);
    try {
      const res = await api.startInterview({ planId: planIdParam });
      setSession(res.session_id, res.plan_id);
      
      if (!planIdParam && res.plan_id) {
        setSearchParams({ plan_id: res.plan_id }, { replace: true });
      }
      
      if (res.is_resumed && res.history.length > 0) {
        const historyMessages = res.history.map((h) => ({
          role: h.role as "user" | "assistant",
          content: h.content,
          timestamp: h.timestamp,
        }));
        setMessages(historyMessages);
        setResumed(true);
        
        addMessage("assistant", res.message, { fieldPath: res.target_field ?? undefined });
        
        requestAnimationFrame(() => {
          if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
          }
        });
      } else {
        addMessage("assistant", res.message, { fieldPath: res.target_field ?? undefined });
      }
      
      if (res.interview_complete) setComplete(true);
    } catch (err: unknown) {
      const is404 =
        err instanceof Error &&
        (err.message.includes("404") || err.message.includes("not found"));
      if (is404 && planIdParam) {
        setSearchParams({}, { replace: true });
        try {
          const retry = await api.startInterview({});
          setSession(retry.session_id, retry.plan_id);
          setSearchParams({ plan_id: retry.plan_id }, { replace: true });
          addMessage("assistant", retry.message, {
            fieldPath: retry.target_field ?? undefined,
          });
          if (retry.interview_complete) setComplete(true);
          return;
        } catch {
          // fall through to generic error
        }
      }
      addMessage("assistant", "Failed to start interview. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const currentTargetField = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") {
        return messages[i].fieldPath;
      }
    }
    return undefined;
  }, [messages]);

  const currentTargetValue = useMemo(() => {
    if (!currentTargetField) return undefined;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user" && messages[i].fieldPath === currentTargetField) {
        return messages[i].content;
      }
    }
    return undefined;
  }, [messages, currentTargetField]);

  const latestBirthYearValue = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user" && messages[i].fieldPath === "client.birth_year") {
        return messages[i].content;
      }
    }
    return undefined;
  }, [messages]);

  const handleSend = useCallback(
    async (message: string) => {
      addMessage("user", message, { fieldPath: currentTargetField ?? undefined });
      setLoading(true);
      try {
        let activeSessionId = sessionId;
        if (!activeSessionId) {
          addMessage(
            "assistant",
            "I need to start a new interview session first. One moment...",
          );
          const start = await api.startInterview({ planId: planIdParam });
          setSession(start.session_id, start.plan_id);
          addMessage("assistant", start.message, { fieldPath: start.target_field ?? undefined });
          if (start.interview_complete) {
            setComplete(true);
          }
          activeSessionId = start.session_id;
        }

        const res = await api.respond(activeSessionId, message);
        addMessage("assistant", res.message, { fieldPath: res.target_field ?? undefined });
        if (res.interview_complete) setComplete(true);
        
        queryClient.invalidateQueries({ queryKey: ["plan", planId || planIdParam] });
        queryClient.invalidateQueries({ queryKey: ["plans"] });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "";
        const isSessionLost =
          errorMessage.toLowerCase().includes("session not found") ||
          errorMessage.includes("404") ||
          errorMessage.toLowerCase().includes("not found");
        if (isSessionLost) {
          addMessage(
            "assistant",
            "Your interview session expired after a backend reload. Starting a new session now...",
          );
          try {
            let start = await api.startInterview({ planId: planIdParam }).catch(async () => {
              setSearchParams({}, { replace: true });
              return api.startInterview({});
            });
            setSession(start.session_id, start.plan_id);
            setSearchParams({ plan_id: start.plan_id }, { replace: true });
            addMessage("assistant", start.message, { fieldPath: start.target_field ?? undefined });
            const retry = await api.respond(start.session_id, message);
            addMessage("assistant", retry.message, { fieldPath: retry.target_field ?? undefined });
            if (retry.interview_complete) setComplete(true);
            return;
          } catch {
            addMessage(
              "assistant",
              "I couldn't recover your session automatically. Please refresh and try again.",
            );
            return;
          }
        }
        addMessage(
          "assistant",
          "Something went wrong while sending your answer. Please try again.",
        );
      } finally {
        setLoading(false);
      }
    },
    [sessionId, planIdParam, addMessage, setSession, setLoading, setComplete, currentTargetField],
  );

  const handleEditMessage = useCallback(
    (index: number, content: string) => {
      setInputCollapsed(false);
      const currentMessage = messages[index];
      const searchFromIndex = currentMessage?.originalIndex !== undefined 
        ? currentMessage.originalIndex 
        : index;
      const baseMessage = messages[searchFromIndex];
      
      let precedingQuestion: string | undefined;
      let precedingFieldPath: string | undefined;
      for (let i = searchFromIndex - 1; i >= 0; i--) {
        if (messages[i]?.role === "assistant") {
          precedingQuestion = messages[i].content;
          precedingFieldPath = messages[i].fieldPath;
          break;
        }
      }
      setEditing({
        index,
        originalContent: content,
        precedingQuestion,
        precedingFieldPath: baseMessage?.fieldPath ?? precedingFieldPath,
      });
    },
    [setEditing, messages]
  );

  const handleCancelEdit = useCallback(() => {
    setEditing(null);
  }, [setEditing]);

  const handleSubmitEdit = useCallback(
    async (index: number, newContent: string) => {
      const precedingQuestion = editing?.precedingQuestion;
      const fieldPath = editing?.precedingFieldPath ?? messages[index]?.fieldPath;
      const fieldName =
        fieldLabelFromPath(fieldPath) ??
        extractFieldName(precedingQuestion);
      const formattedValue = formatCorrectionValue(newContent, fieldName);
      const correctionMessage = buildCorrectionMessage(fieldName, formattedValue);
      
      const updateLabel = fieldName === "answer" 
        ? "Update"
        : `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} update`;
      
      setEditing(null);
      
      const newMessageIndex = messages.length;
      
      markMessageUpdated(index, newMessageIndex);
      
      addMessage("user", formattedValue, {
        isUpdate: true,
        updateLabel,
        originalIndex: index,
        fieldPath: messages[index]?.fieldPath,
      });
      addMessage("assistant", correctionMessage);
      
      const activePlanId = planId || planIdParam;
      if (activePlanId && fieldPath) {
        setLoading(true);
        try {
          const rawValue = parseRawFieldValue(fieldPath, newContent);
          await api.updatePlanFields(activePlanId, [{ path: fieldPath, value: rawValue }]);
          queryClient.invalidateQueries({ queryKey: ["plan", activePlanId] });
          queryClient.invalidateQueries({ queryKey: ["plans"] });

          if (sessionId && !isComplete) {
            const res = await api.respond(sessionId, `[Updated ${fieldName}]`);
            addMessage("assistant", res.message, { fieldPath: res.target_field ?? undefined });
            if (res.interview_complete) {
              setComplete(true);
              setPhase("ready_for_analysis");
            }
          }
        } catch {
          addMessage("assistant", "I had trouble saving that update. Please try again.");
        } finally {
          setLoading(false);
        }
      } else if (sessionId) {
        setLoading(true);
        try {
          const res = await api.respond(sessionId, `[Correction] My ${fieldName} should be: ${formattedValue}`);
          addMessage("assistant", res.message, { fieldPath: res.target_field ?? undefined });
          if (res.interview_complete) {
            setComplete(true);
            setPhase("ready_for_analysis");
          }
          queryClient.invalidateQueries({ queryKey: ["plan", activePlanId] });
          queryClient.invalidateQueries({ queryKey: ["plans"] });
        } catch {
          addMessage("assistant", "I've noted your correction. Let's continue.");
        } finally {
          setLoading(false);
        }
      }
    },
    [sessionId, planId, planIdParam, queryClient, editing, messages, markMessageUpdated, addMessage, setLoading, setComplete, setEditing, setPhase, isComplete]
  );

  const handleSendWithEditDetection = useCallback(
    async (message: string) => {
      if (detectEditIntent(message)) {
        let lastUserIndex = -1;
        for (let i = messages.length - 1; i >= 0; i--) {
          if (messages[i].role === "user") {
            lastUserIndex = i;
            break;
          }
        }
        if (lastUserIndex !== -1) {
          addMessage("user", message);
          addMessage("assistant", "I understand you want to update a previous answer. Click the reply icon next to the answer you'd like to change, or tell me the corrected information directly.");
          return;
        }
      }
      handleSend(message);
    },
    [messages, addMessage, handleSend]
  );

  const showInput = phase !== "ready_for_analysis" || editing !== null;
  const inputHeight = !showInput ? 0 : inputCollapsed ? 64 : Math.max(80, inputPanelHeight + 12);

  useEffect(() => {
    if (!inputPanelRef.current || inputCollapsed || !showInput) {
      return;
    }
    const element = inputPanelRef.current;
    const observer = new ResizeObserver(() => {
      setInputPanelHeight(element.offsetHeight);
    });
    observer.observe(element);
    setInputPanelHeight(element.offsetHeight);
    return () => observer.disconnect();
  }, [inputCollapsed, editing, isComplete, currentTargetField, showInput]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (editing) return;
      if (inputCollapsed) return;
      setInputCollapsed(true);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [editing, inputCollapsed]);

  const scrollToMessage = useCallback((targetIndex: number) => {
    const container = chatContainerRef.current;
    if (!container) return;
    const targetElement = container.querySelector(`[data-message-index="${targetIndex}"]`);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: "smooth", block: "center" });
      targetElement.classList.add("ring-2", "ring-harbor-400", "ring-offset-2");
      setTimeout(() => {
        targetElement.classList.remove("ring-2", "ring-harbor-400", "ring-offset-2");
      }, 1500);
    }
  }, []);

  const lastAssistantMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") {
        return messages[i].content;
      }
    }
    return undefined;
  }, [messages]);

  const fieldLabels = useMemo(() => {
    const labels: Record<number, string> = {};
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].role === "user") {
        if (messages[i].fieldPath) {
          labels[i] = fieldLabelFromPath(messages[i].fieldPath) ?? "answer";
          continue;
        }
        let precedingQuestion: string | undefined;
        for (let j = i - 1; j >= 0; j--) {
          if (messages[j].role === "assistant") {
            precedingQuestion = messages[j].content;
            break;
          }
        }
        labels[i] = extractFieldName(precedingQuestion);
      }
    }
    return labels;
  }, [messages]);

  const conversationContext = useMemo(() => {
    return messages
      .slice(-6)
      .map((m) => m.content)
      .join(" ");
  }, [messages]);

  useEffect(() => {
    if (isComplete && phase === "interviewing") {
      setPhase("ready_for_analysis");
    }
  }, [isComplete, phase, setPhase]);

  const activePlanId = planId || planIdParam;

  return (
    <>
      <div className="mx-auto max-w-2xl flex-1 flex flex-col min-h-0" style={{ paddingBottom: phase === "ready_for_analysis" && !editing ? undefined : inputHeight }}>
        <div className="flex items-center justify-between gap-4 mb-4 shrink-0">
          <p className="text-sm text-sage-600">
            Tell me about your retirement goals and I'll build a plan.
          </p>
        </div>

        <div className="card-elevated flex-1 flex flex-col min-h-0 overflow-hidden">
          {isResumed && (
            <div className="shrink-0 border-b border-sage-200/60 bg-gradient-to-r from-harbor-50 to-sage-50 px-4 py-3">
              <div className="flex items-center gap-2 text-harbor-700 text-sm">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  <span className="font-medium">This is your current plan.</span>
                  {" "}You can scroll through your previous answers. Click the reply icon on any response to make changes.
                </span>
              </div>
            </div>
          )}
          <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage 
                key={i} 
                role={msg.role} 
                content={msg.content}
                timestamp={msg.timestamp}
                messageIndex={i}
                onEdit={handleEditMessage}
                isEditing={editing?.index === i}
                updatedByIndex={msg.updatedByIndex}
                isUpdate={msg.isUpdate}
                updateLabel={msg.updateLabel}
                fieldLabel={fieldLabels[i]}
                onScrollToMessage={scrollToMessage}
              />
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl bg-sage-100 px-4 py-3 text-sm text-sage-600">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Thinking...
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </div>

        {phase === "ready_for_analysis" && !editing && (
          <div className="mt-4 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 px-5 py-5">
            <div className="flex items-center justify-center gap-2 text-emerald-700 text-sm mb-3">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-semibold">
                {isResumed
                  ? "All information collected. Ready to run your analysis."
                  : "Interview complete! Ready to generate your projections."}
              </span>
            </div>
            {isResumed && (
              <p className="mb-4 text-xs text-sage-600 text-center">
                You can also click the reply icon on any answer above to make changes first.
              </p>
            )}
            <div className="flex justify-center gap-3">
              <button
                className="btn-ghost flex items-center gap-2"
                onClick={() => activePlanId && navigate(`/review/${activePlanId}`)}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                Review Responses
              </button>
              <button
                className="btn-primary flex items-center gap-2"
                onClick={() => activePlanId && navigate(`/dashboard/${activePlanId}?autorun=true`)}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Run Analysis
              </button>
            </div>
          </div>
        )}
      </div>

      {showInput && (
        <>
          {inputCollapsed ? (
            <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-sm border-t border-sage-200/60 shadow-elevated">
              <div className="mx-auto max-w-2xl px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3">
                <span className="text-xs text-sage-600">
                  Input hidden. Press Escape while typing to hide.
                </span>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setInputCollapsed(false)}
                >
                  Show input
                </button>
              </div>
            </div>
          ) : (
            <div
              ref={inputPanelRef}
              className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-sm border-t border-sage-200/60 shadow-elevated"
            >
              <div className="mx-auto max-w-2xl px-4 sm:px-6 py-3">
                <ChatInput
                  onSend={handleSendWithEditDetection}
                  disabled={isLoading || (isComplete && !editing)}
                  placeholder={
                    isComplete
                      ? "Click the reply icon on any answer to make changes."
                      : "Type your answer..."
                  }
                  lastAssistantMessage={lastAssistantMessage}
                  currentTargetField={currentTargetField}
                  currentTargetValue={currentTargetValue}
                  clientBirthYearValue={latestBirthYearValue}
                  conversationContext={conversationContext}
                  editing={editing}
                  onCancelEdit={handleCancelEdit}
                  onSubmitEdit={handleSubmitEdit}
                />
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
