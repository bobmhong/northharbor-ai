import { create } from "zustand";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface EditingState {
  index: number;
  originalContent: string;
}

interface InterviewState {
  sessionId: string | null;
  planId: string | null;
  messages: Message[];
  isComplete: boolean;
  isLoading: boolean;
  isResumed: boolean;
  editing: EditingState | null;

  setSession: (sessionId: string, planId: string) => void;
  addMessage: (role: "user" | "assistant", content: string) => void;
  setMessages: (messages: Message[]) => void;
  updateMessage: (index: number, content: string) => void;
  setComplete: (complete: boolean) => void;
  setLoading: (loading: boolean) => void;
  setResumed: (resumed: boolean) => void;
  setEditing: (editing: EditingState | null) => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewState>((set) => ({
  sessionId: null,
  planId: null,
  messages: [],
  isComplete: false,
  isLoading: false,
  isResumed: false,
  editing: null,

  setSession: (sessionId, planId) => set({ sessionId, planId }),

  addMessage: (role, content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { role, content, timestamp: new Date().toISOString() },
      ],
    })),

  setMessages: (messages) => set({ messages }),

  updateMessage: (index, content) =>
    set((state) => ({
      messages: state.messages.map((msg, i) =>
        i === index ? { ...msg, content, timestamp: new Date().toISOString() } : msg
      ),
    })),

  setComplete: (isComplete) => set({ isComplete }),
  setLoading: (isLoading) => set({ isLoading }),
  setResumed: (isResumed) => set({ isResumed }),
  setEditing: (editing) => set({ editing }),

  reset: () =>
    set({
      sessionId: null,
      planId: null,
      messages: [],
      isComplete: false,
      isLoading: false,
      isResumed: false,
      editing: null,
    }),
}));
