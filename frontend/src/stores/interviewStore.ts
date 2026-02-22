import { create } from "zustand";

export type InterviewPhase =
  | "interviewing"
  | "ready_for_analysis";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  fieldPath?: string;
  updatedByIndex?: number;
  isUpdate?: boolean;
  updateLabel?: string;
  originalIndex?: number;
}

interface EditingState {
  index: number;
  originalContent: string;
  precedingQuestion?: string;
  precedingFieldPath?: string;
}

interface InterviewState {
  sessionId: string | null;
  planId: string | null;
  messages: Message[];
  isComplete: boolean;
  isLoading: boolean;
  isResumed: boolean;
  editing: EditingState | null;
  phase: InterviewPhase;
  warnings: Array<{
    rule_id: string;
    fields: string[];
    message: string;
    suggestion: string;
  }>;

  setSession: (sessionId: string, planId: string) => void;
  addMessage: (role: "user" | "assistant", content: string, extra?: Partial<Message>) => void;
  setMessages: (messages: Message[]) => void;
  updateMessage: (index: number, content: string) => void;
  markMessageUpdated: (originalIndex: number, updateIndex: number) => void;
  setComplete: (complete: boolean) => void;
  setLoading: (loading: boolean) => void;
  setResumed: (resumed: boolean) => void;
  setEditing: (editing: EditingState | null) => void;
  setPhase: (phase: InterviewPhase) => void;
  setWarnings: (warnings: Array<{ rule_id: string; fields: string[]; message: string; suggestion: string }>) => void;
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
  phase: "interviewing",
  warnings: [],

  setSession: (sessionId, planId) => set({ sessionId, planId }),

  addMessage: (role, content, extra) =>
    set((state) => ({
      messages: [
        ...state.messages,
        { role, content, timestamp: new Date().toISOString(), ...extra },
      ],
    })),

  setMessages: (messages) => set({ messages }),

  updateMessage: (index, content) =>
    set((state) => ({
      messages: state.messages.map((msg, i) =>
        i === index ? { ...msg, content, timestamp: new Date().toISOString() } : msg
      ),
    })),

  markMessageUpdated: (originalIndex, updateIndex) =>
    set((state) => ({
      messages: state.messages.map((msg, i) =>
        i === originalIndex ? { ...msg, updatedByIndex: updateIndex } : msg
      ),
    })),

  setComplete: (isComplete) => set({ isComplete }),
  setLoading: (isLoading) => set({ isLoading }),
  setResumed: (isResumed) => set({ isResumed }),
  setEditing: (editing) => set({ editing }),
  setPhase: (phase) => set({ phase }),
  setWarnings: (warnings) => set({ warnings }),

  reset: () =>
    set({
      sessionId: null,
      planId: null,
      messages: [],
      isComplete: false,
      isLoading: false,
      isResumed: false,
      editing: null,
      phase: "interviewing",
      warnings: [],
    }),
}));
