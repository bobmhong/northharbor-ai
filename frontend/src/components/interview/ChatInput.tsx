import { useRef, useState, useEffect, type FormEvent, useMemo } from "react";
import Typeahead from "../ui/Typeahead";
import { getStatesForAutocomplete, getCitiesForState } from "../../data/locations";

type InputMode = "text" | "state" | "city" | "income" | "legacy" | "balance" | "spending";

const INCOME_SUGGESTIONS = [
  { value: "50000", label: "$50,000" },
  { value: "75000", label: "$75,000" },
  { value: "100000", label: "$100,000" },
  { value: "125000", label: "$125,000" },
  { value: "150000", label: "$150,000" },
  { value: "175000", label: "$175,000" },
  { value: "200000", label: "$200,000" },
  { value: "250000", label: "$250,000" },
  { value: "300000", label: "$300,000" },
];

const LEGACY_SUGGESTIONS = [
  { value: "0", label: "$0 (no legacy goal)" },
  { value: "100000", label: "$100,000" },
  { value: "250000", label: "$250,000" },
  { value: "500000", label: "$500,000" },
  { value: "750000", label: "$750,000" },
  { value: "1000000", label: "$1,000,000" },
  { value: "2000000", label: "$2,000,000" },
];

const BALANCE_SUGGESTIONS = [
  { value: "50000", label: "$50,000" },
  { value: "100000", label: "$100,000" },
  { value: "250000", label: "$250,000" },
  { value: "500000", label: "$500,000" },
  { value: "750000", label: "$750,000" },
  { value: "1000000", label: "$1,000,000" },
  { value: "1500000", label: "$1,500,000" },
  { value: "2000000", label: "$2,000,000" },
];

const SPENDING_SUGGESTIONS = [
  { value: "3000", label: "$3,000/month" },
  { value: "4000", label: "$4,000/month" },
  { value: "5000", label: "$5,000/month" },
  { value: "6000", label: "$6,000/month" },
  { value: "7500", label: "$7,500/month" },
  { value: "10000", label: "$10,000/month" },
  { value: "12500", label: "$12,500/month" },
  { value: "15000", label: "$15,000/month" },
];

interface EditingState {
  index: number;
  originalContent: string;
}

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  lastAssistantMessage?: string;
  conversationContext?: string;
  editing?: EditingState | null;
  onCancelEdit?: () => void;
  onSubmitEdit?: (index: number, newContent: string) => void;
}

function detectInputMode(message?: string, context?: string): { mode: InputMode; stateContext?: string } {
  const text = (message || "").toLowerCase();
  const fullContext = (context || "").toLowerCase();
  
  if (text.includes("which state") || text.includes("what state") || text.match(/state do you (live|reside)/)) {
    return { mode: "state" };
  }
  
  if (text.includes("which city") || text.includes("what city") || text.match(/city do you (live|reside)/)) {
    const stateMatch = fullContext.match(/(?:in|from|live in|reside in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/);
    return { mode: "city", stateContext: stateMatch?.[1] };
  }
  
  if (text.includes("gross annual income") || text.includes("current income") || text.match(/what is your.+income/)) {
    return { mode: "income" };
  }
  
  if (text.includes("legacy goal") || text.includes("leave behind") || text.includes("amount you'd like to leave")) {
    return { mode: "legacy" };
  }
  
  if (text.includes("retirement account") || text.includes("current balance") || text.match(/balance.+retirement/)) {
    return { mode: "balance" };
  }
  
  if (text.includes("spend per month") || text.includes("monthly spending") || text.match(/expect to spend.+retirement/)) {
    return { mode: "spending" };
  }
  
  return { mode: "text" };
}

const EDIT_INTENT_PATTERNS = [
  /^(change|update|fix|correct|adjust|modify|edit)\s+(my\s+)?(previous\s+)?(answer|response)/i,
  /^(actually|wait|sorry),?\s+(it'?s?|that'?s?|i meant|should be)/i,
  /^(let me|i want to|i need to)\s+(change|update|fix|correct|adjust)/i,
  /^(that was wrong|i made a mistake|correction)/i,
];

export function detectEditIntent(text: string): boolean {
  return EDIT_INTENT_PATTERNS.some(pattern => pattern.test(text.trim()));
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Type your answer...",
  lastAssistantMessage,
  conversationContext,
  editing,
  onCancelEdit,
  onSubmitEdit,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  
  const prevDisabledRef = useRef(disabled);
  
  useEffect(() => {
    if (editing) {
      setValue(editing.originalContent);
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [editing]);

  useEffect(() => {
    if (prevDisabledRef.current && !disabled) {
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
    prevDisabledRef.current = disabled;
  }, [disabled]);
  
  const { mode, stateContext } = useMemo(
    () => detectInputMode(lastAssistantMessage, conversationContext),
    [lastAssistantMessage, conversationContext]
  );

  const stateOptions = useMemo(() => getStatesForAutocomplete(), []);
  const cityOptions = useMemo(
    () => (stateContext ? getCitiesForState(stateContext) : []),
    [stateContext]
  );

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    
    if (editing && onSubmitEdit) {
      onSubmitEdit(editing.index, trimmed);
      setValue("");
      return;
    }
    
    onSend(trimmed);
    setValue("");
    requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
  }

  function handleCancel() {
    setValue("");
    onCancelEdit?.();
  }

  function handleTypeaheadSelect(selectedValue: string) {
    if (disabled) return;
    onSend(selectedValue);
    setValue("");
  }

  if (editing) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-harbor-600">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          <span>Editing your previous answer</span>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={disabled}
            placeholder="Update your answer..."
            className="input-field flex-1 ring-2 ring-harbor-200"
            autoFocus
          />
          <button
            type="button"
            onClick={handleCancel}
            className="btn-ghost shrink-0"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={disabled || !value.trim() || value.trim() === editing.originalContent}
            className="btn-primary shrink-0"
          >
            Update
          </button>
        </form>
      </div>
    );
  }

  if (mode === "state") {
    return (
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Typeahead
            options={stateOptions}
            value={value}
            onChange={setValue}
            onSelect={handleTypeaheadSelect}
            placeholder="Type to search states..."
            allowCustom={false}
            disabled={disabled}
            autoFocus
          />
        </div>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="btn-primary shrink-0"
        >
          Send
        </button>
      </form>
    );
  }

  if (mode === "city") {
    return (
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Typeahead
            options={cityOptions}
            value={value}
            onChange={setValue}
            onSelect={handleTypeaheadSelect}
            placeholder="Type city name..."
            allowCustom={true}
            customLabel="Use this city"
            disabled={disabled}
            autoFocus
          />
        </div>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="btn-primary shrink-0"
        >
          Send
        </button>
      </form>
    );
  }

  if (mode === "income") {
    return (
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Typeahead
            options={INCOME_SUGGESTIONS}
            value={value}
            onChange={setValue}
            onSelect={handleTypeaheadSelect}
            placeholder="Enter amount or select..."
            allowCustom={true}
            customLabel="Use this amount"
            disabled={disabled}
            autoFocus
          />
        </div>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="btn-primary shrink-0"
        >
          Send
        </button>
      </form>
    );
  }

  if (mode === "legacy") {
    return (
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Typeahead
            options={LEGACY_SUGGESTIONS}
            value={value}
            onChange={setValue}
            onSelect={handleTypeaheadSelect}
            placeholder="Enter amount or select (0 for none)..."
            allowCustom={true}
            customLabel="Use this amount"
            disabled={disabled}
            autoFocus
          />
        </div>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="btn-primary shrink-0"
        >
          Send
        </button>
      </form>
    );
  }

  if (mode === "balance") {
    return (
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Typeahead
            options={BALANCE_SUGGESTIONS}
            value={value}
            onChange={setValue}
            onSelect={handleTypeaheadSelect}
            placeholder="Enter balance or select..."
            allowCustom={true}
            customLabel="Use this amount"
            disabled={disabled}
            autoFocus
          />
        </div>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="btn-primary shrink-0"
        >
          Send
        </button>
      </form>
    );
  }

  if (mode === "spending") {
    return (
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <div className="flex-1">
          <Typeahead
            options={SPENDING_SUGGESTIONS}
            value={value}
            onChange={setValue}
            onSelect={handleTypeaheadSelect}
            placeholder="Enter monthly amount or select..."
            allowCustom={true}
            customLabel="Use this amount"
            disabled={disabled}
            autoFocus
          />
        </div>
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="btn-primary shrink-0"
        >
          Send
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="input-field flex-1"
        autoFocus
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="btn-primary shrink-0"
      >
        Send
      </button>
    </form>
  );
}
