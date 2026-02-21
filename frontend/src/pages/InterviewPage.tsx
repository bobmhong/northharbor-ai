import { useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import ChatInput from "../components/interview/ChatInput";
import ChatMessage from "../components/interview/ChatMessage";
import { useInterviewStore } from "../stores/interviewStore";
import { api } from "../api/client";

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
    if (!sessionId) {
      startNewInterview();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function startNewInterview() {
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
      if (!sessionId) return;
      addMessage("user", message);
      setLoading(true);
      try {
        const res = await api.respond(sessionId, message);
        addMessage("assistant", res.message);
        if (res.interview_complete) setComplete(true);
      } catch (err) {
        addMessage("assistant", "Something went wrong. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [sessionId, addMessage, setLoading, setComplete],
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
