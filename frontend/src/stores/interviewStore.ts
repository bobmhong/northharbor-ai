import { create } from "zustand";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface InterviewState {
  sessionId: string | null;
  planId: string | null;
  messages: Message[];
  isComplete: boolean;
  isLoading: boolean;

  setSession: (sessionId: string, planId: string) => void;
  addMessage: (role: "user" | "assistant", content: string) => void;
  setComplete: (complete: boolean) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewState>((set) => ({
  sessionId: null,
  planId: null,
  messages: [],
  isComplete: false,
  isLoading: false,

  setSession: (sessionId, planId) => set({ sessionId, planId }),

  addMessage: (role, content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { role, content, timestamp: new Date().toISOString() },
      ],
    })),

  setComplete: (isComplete) => set({ isComplete }),
  setLoading: (isLoading) => set({ isLoading }),

  reset: () =>
    set({
      sessionId: null,
      planId: null,
      messages: [],
      isComplete: false,
      isLoading: false,
    }),
}));
