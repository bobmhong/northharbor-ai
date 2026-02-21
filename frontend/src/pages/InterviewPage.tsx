import { useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import ChatInput from "../components/interview/ChatInput";
import ChatMessage from "../components/interview/ChatMessage";
import { useInterviewStore } from "../stores/interviewStore";
import { api } from "../api/client";

let startInterviewInFlight: Promise<void> | null = null;

export default function InterviewPage() {
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);
  const {
    sessionId,
    planId,
    messages,
    isComplete,
    isLoading,
    setSession,
    addMessage,
    setComplete,
    setLoading,
    reset,
  } = useInterviewStore();

  useEffect(() => {
    if (sessionId || startInterviewInFlight) {
      return;
    }
    startInterviewInFlight = startNewInterview().finally(() => {
      startInterviewInFlight = null;
    });
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function startNewInterview(): Promise<void> {
    reset();
    setLoading(true);
    try {
      const res = await api.startInterview();
      setSession(res.session_id, res.plan_id);
      addMessage("assistant", res.message);
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
          const start = await api.startInterview();
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
            const start = await api.startInterview();
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
    [sessionId, addMessage, setSession, setLoading, setComplete],
  );

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Interview Wizard
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Tell me about your retirement goals and I'll build a plan.
          </p>
        </div>
        {isComplete && planId && (
          <button
            className="btn-primary"
            onClick={() => navigate(`/dashboard/${planId}`)}
          >
            View Dashboard
          </button>
        )}
      </div>

      <div className="card mb-4 flex min-h-[400px] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-2">
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} content={msg.content} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-500">
                Thinking...
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </div>

      <ChatInput
        onSend={handleSend}
        disabled={isLoading || isComplete}
        placeholder={
          isComplete
            ? "Interview complete! View your dashboard."
            : "Type your answer..."
        }
      />

      {isComplete && (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 text-center text-sm text-green-800">
          Interview complete! Your plan is ready for analysis.
        </div>
      )}
    </div>
  );
}
