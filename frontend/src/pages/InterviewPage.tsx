import { useCallback, useEffect, useMemo, useRef } from "react";
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
  
  // Name - expanded patterns
  if ((q.includes("name") && (q.includes("call you") || q.includes("your name") || q.includes("what's your") || q.includes("what is your"))) ||
      q.includes("may i call you") || q.includes("should i call you") ||
      (q.includes("name") && q.includes("?"))) return "name";
  
  // Location
  if (q.includes("state") && (q.includes("live") || q.includes("reside") || q.includes("located"))) return "state";
  if (q.includes("city") && (q.includes("live") || q.includes("reside") || q.includes("located"))) return "city";
  
  // Age / Birth year
  if (q.includes("retire") && (q.includes("age") || q.includes("when") || q.includes("plan to"))) return "target retirement age";
  if (q.includes("birth year") || q.includes("year were you born") || q.includes("born in")) return "birth year";
  if (q.includes("current age") || q.includes("old are you") || q.includes("your age")) return "age";
  
  // Income
  if (q.includes("income") || q.includes("salary") || q.includes("earn") || q.includes("make per year")) return "annual income";
  
  // Legacy
  if (q.includes("legacy") || q.includes("leave behind") || q.includes("inheritance") || q.includes("estate")) return "legacy goal";
  
  // Balance
  if (q.includes("balance") || q.includes("saved") || q.includes("retirement account") || q.includes("401") || q.includes("ira") || q.includes("savings")) return "retirement balance";
  
  // Spending
  if (q.includes("spend") || q.includes("expenses") || q.includes("monthly") || q.includes("budget")) return "monthly spending";
  
  // Success rate / Monte Carlo
  if (q.includes("success rate") || q.includes("success probability") || 
      q.includes("monte carlo") || q.includes("probability of success") ||
      q.includes("confidence level") || q.includes("plan success")) return "success rate";
  
  // Employer plan (yes/no)
  if (q.includes("employer offer") || q.includes("employer retirement") ||
      (q.includes("401(k)") && q.includes("offer")) || (q.includes("401k") && q.includes("offer")) ||
      (q.includes("employer") && q.includes("plan"))) return "employer plan";
  
  // Employer match
  if (q.includes("employer match") || q.includes("company match") ||
      q.includes("matching contribution") || q.includes("does your employer match") ||
      q.includes("what percentage does your employer")) return "employer match";
  
  // Employee contribution (specific to employer plan)
  if ((q.includes("do you contribute") || q.includes("your contribution")) &&
      (q.includes("retirement plan") || q.includes("401"))) return "contribution rate";
  
  // Savings rate (general)
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
    case "retirement_philosophy.success_probability_target":
    case "monte_carlo.required_success_rate":
      return "success rate";
    default:
      return undefined;
  }
}

function formatCorrectionValue(value: string, fieldName: string): string {
  const trimmed = value.trim();
  
  // Text fields that should never be formatted - return as-is
  const textFields = ["name", "state", "city", "employer plan"];
  if (textFields.includes(fieldName)) {
    return trimmed;
  }
  
  // Percentage fields or values ending in %
  const percentageFields = ["savings rate", "success rate", "employer match", "contribution rate"];
  if (percentageFields.includes(fieldName) || trimmed.match(/^\d+%$/)) {
    const num = parseFloat(trimmed.replace(/%$/, ""));
    if (!isNaN(num)) return `${num}%`;
    return trimmed;
  }
  
  // Monetary fields
  const monetaryFields = ["annual income", "legacy goal", "retirement balance", "monthly spending"];
  if (monetaryFields.includes(fieldName)) {
    const num = parseInt(trimmed.replace(/[$,]/g, ""), 10);
    if (!isNaN(num)) return "$" + num.toLocaleString("en-US");
    return trimmed;
  }
  
  // Age and year fields - just return as-is
  if (fieldName === "age" || fieldName === "target retirement age" || fieldName === "birth year") {
    return trimmed;
  }
  
  // Auto-detect: if value looks like a large number or has $ sign, format as currency
  // But exclude 4-digit years (1900-2100)
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

export default function InterviewPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const planIdParam = searchParams.get("plan_id") ?? undefined;
  const scrollRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const {
    sessionId,
    planId,
    messages,
    isComplete,
    isLoading,
    isResumed,
    editing,
    setSession,
    addMessage,
    setMessages,
    markMessageUpdated,
    setComplete,
    setLoading,
    setResumed,
    setEditing,
    reset,
  } = useInterviewStore();

  useEffect(() => {
    // If we have a session but no messages, we need to reload the history
    // This can happen if the user navigates away and comes back
    const needsReload = !sessionId || (sessionId && messages.length === 0);
    
    if (!needsReload || startInterviewInFlight) {
      return;
    }
    startInterviewInFlight = startNewInterview().finally(() => {
      startInterviewInFlight = null;
    });
  }, [sessionId, planIdParam, messages.length]);

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
    } catch (err) {
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
        
        // Invalidate plan data to refresh header (name, scenario, etc.)
        queryClient.invalidateQueries({ queryKey: ["plan", planId || planIdParam] });
        queryClient.invalidateQueries({ queryKey: ["plans"] });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "";
        if (errorMessage.toLowerCase().includes("session not found")) {
          addMessage(
            "assistant",
            "Your interview session expired after a backend reload. Starting a new session now...",
          );
          try {
            const start = await api.startInterview({ planId: planIdParam });
            setSession(start.session_id, start.plan_id);
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
      // Check if this is an update message - if so, use the original message's context
      const currentMessage = messages[index];
      const searchFromIndex = currentMessage?.originalIndex !== undefined 
        ? currentMessage.originalIndex 
        : index;
      const baseMessage = messages[searchFromIndex];
      
      // Find the preceding assistant message to determine the input mode
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
      // Get the preceding question before clearing editing state
      const precedingQuestion = editing?.precedingQuestion;
      const fieldName =
        fieldLabelFromPath(editing?.precedingFieldPath) ??
        extractFieldName(precedingQuestion);
      const formattedValue = formatCorrectionValue(newContent, fieldName);
      const correctionMessage = buildCorrectionMessage(fieldName, formattedValue);
      
      // Build update label (e.g., "Income update")
      const updateLabel = fieldName === "answer" 
        ? "Update"
        : `${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} update`;
      
      setEditing(null);
      
      // Calculate the index where the new user message will be added
      const newMessageIndex = messages.length;
      
      // Mark the original message as updated, pointing to the new message
      markMessageUpdated(index, newMessageIndex);
      
      // Add user's correction as a new chat bubble with update metadata
      addMessage("user", formattedValue, {
        isUpdate: true,
        updateLabel,
        originalIndex: index,
        fieldPath: messages[index]?.fieldPath,
      });
      addMessage("assistant", correctionMessage);
      
      if (sessionId) {
        setLoading(true);
        try {
          const res = await api.respond(sessionId, `[Correction] My ${fieldName} should be: ${formattedValue}`);
          addMessage("assistant", res.message, { fieldPath: res.target_field ?? undefined });
          if (res.interview_complete) setComplete(true);
          
          // Invalidate plan data to refresh header (name, scenario, etc.)
          queryClient.invalidateQueries({ queryKey: ["plan", planId || planIdParam] });
          queryClient.invalidateQueries({ queryKey: ["plans"] });
        } catch {
          addMessage("assistant", "I've noted your correction. Let's continue.");
        } finally {
          setLoading(false);
        }
      }
    },
    [sessionId, planId, planIdParam, queryClient, editing, messages.length, markMessageUpdated, addMessage, setLoading, setComplete, setEditing]
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

  const inputHeight = editing ? 120 : isComplete ? 140 : 80;

  const scrollToMessage = useCallback((targetIndex: number) => {
    const container = chatContainerRef.current;
    if (!container) return;
    const targetElement = container.querySelector(`[data-message-index="${targetIndex}"]`);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: "smooth", block: "center" });
      // Brief highlight effect
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

  // Compute field labels for each user message based on preceding assistant question
  const fieldLabels = useMemo(() => {
    const labels: Record<number, string> = {};
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].role === "user") {
        if (messages[i].fieldPath) {
          labels[i] = fieldLabelFromPath(messages[i].fieldPath) ?? "answer";
          continue;
        }
        // Find preceding assistant message
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

  return (
    <>
      <div className="mx-auto max-w-2xl flex-1 flex flex-col min-h-0" style={{ paddingBottom: inputHeight }}>
        <div className="flex items-center justify-between gap-4 mb-4 shrink-0">
          <p className="text-sm text-sage-600">
            Tell me about your retirement goals and I'll build a plan.
          </p>
          {isComplete && planId && (
            <button
              className="btn-primary shrink-0"
              onClick={() => navigate(`/dashboard/${planId}`)}
            >
              View Dashboard
            </button>
          )}
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
      </div>

      <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-sm border-t border-sage-200/60 shadow-elevated">
        <div className="mx-auto max-w-2xl px-4 sm:px-6 py-3">
          <ChatInput
            onSend={handleSendWithEditDetection}
            disabled={isLoading || isComplete}
            placeholder={
              isComplete
                ? "Interview complete! View your dashboard."
                : "Type your answer..."
            }
            lastAssistantMessage={lastAssistantMessage}
            currentTargetField={currentTargetField}
            conversationContext={conversationContext}
            editing={editing}
            onCancelEdit={handleCancelEdit}
            onSubmitEdit={handleSubmitEdit}
          />

          {isComplete && (
            <div className="mt-3 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 px-4 py-3">
              <div className="flex items-center justify-center gap-2 text-emerald-700 text-sm">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="font-medium">
                  {isResumed 
                    ? "This plan is complete. Would you like to change any of your answers?" 
                    : "Interview complete! Your plan is ready for analysis."}
                </span>
              </div>
              {isResumed && (
                <p className="mt-2 text-xs text-sage-600 text-center">
                  Click the reply icon next to any of your answers above to make changes.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
