import { useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ChatInput, { detectEditIntent } from "../components/interview/ChatInput";
import ChatMessage from "../components/interview/ChatMessage";
import { useInterviewStore } from "../stores/interviewStore";
import { api } from "../api/client";

let startInterviewInFlight: Promise<void> | null = null;

export default function InterviewPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
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
    updateMessage,
    setComplete,
    setLoading,
    setResumed,
    setEditing,
    reset,
  } = useInterviewStore();

  useEffect(() => {
    if (sessionId || startInterviewInFlight) {
      return;
    }
    startInterviewInFlight = startNewInterview().finally(() => {
      startInterviewInFlight = null;
    });
  }, [sessionId, planIdParam]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function startNewInterview(): Promise<void> {
    reset();
    setLoading(true);
    try {
      const res = await api.startInterview({ planId: planIdParam });
      setSession(res.session_id, res.plan_id);
      
      if (res.is_resumed && res.history.length > 0) {
        const historyMessages = res.history.map((h) => ({
          role: h.role as "user" | "assistant",
          content: h.content,
          timestamp: h.timestamp,
        }));
        setMessages(historyMessages);
        setResumed(true);
        
        addMessage("assistant", res.message);
        
        requestAnimationFrame(() => {
          if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
          }
        });
      } else {
        addMessage("assistant", res.message);
      }
      
      if (res.interview_complete) setComplete(true);
    } catch (err) {
      addMessage("assistant", "Failed to start interview. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const handleSend = useCallback(
    async (message: string) => {
      addMessage("user", message);
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
          addMessage("assistant", start.message);
          if (start.interview_complete) {
            setComplete(true);
          }
          activeSessionId = start.session_id;
        }

        const res = await api.respond(activeSessionId, message);
        addMessage("assistant", res.message);
        if (res.interview_complete) setComplete(true);
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
            addMessage("assistant", start.message);
            const retry = await api.respond(start.session_id, message);
            addMessage("assistant", retry.message);
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
    [sessionId, planIdParam, addMessage, setSession, setLoading, setComplete],
  );

  const handleEditMessage = useCallback(
    (index: number, content: string) => {
      setEditing({ index, originalContent: content });
    },
    [setEditing]
  );

  const handleCancelEdit = useCallback(() => {
    setEditing(null);
  }, [setEditing]);

  const handleSubmitEdit = useCallback(
    async (index: number, newContent: string) => {
      setEditing(null);
      updateMessage(index, newContent);
      
      addMessage("assistant", `Got it, I've noted your updated answer: "${newContent}"`);
      
      if (sessionId) {
        setLoading(true);
        try {
          const res = await api.respond(sessionId, `[Correction] My previous answer should be: ${newContent}`);
          addMessage("assistant", res.message);
          if (res.interview_complete) setComplete(true);
        } catch {
          addMessage("assistant", "I've noted your correction. Let's continue.");
        } finally {
          setLoading(false);
        }
      }
    },
    [sessionId, updateMessage, addMessage, setLoading, setComplete, setEditing]
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
          addMessage("assistant", "I understand you want to update a previous answer. Click the edit icon next to the answer you'd like to change, or tell me the corrected information directly.");
          return;
        }
      }
      handleSend(message);
    },
    [messages, addMessage, handleSend]
  );

  const inputHeight = editing ? 120 : isComplete ? 140 : 80;

  const lastAssistantMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") {
        return messages[i].content;
      }
    }
    return undefined;
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
                  {" "}You can scroll through your previous answers. Click the edit icon on any response to make changes.
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
                  Click the edit icon next to any of your answers above to make changes.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
