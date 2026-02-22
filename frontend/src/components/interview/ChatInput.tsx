import { useRef, useState, useEffect, type FormEvent, useMemo } from "react";
import Typeahead from "../ui/Typeahead";
import { getStatesForAutocomplete, getCitiesForState } from "../../data/locations";

type InputMode = "text" | "state" | "city" | "income" | "legacy" | "balance" | "spending" | "percentage" | "success_rate";

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
  { value: "2500000", label: "$2,500,000" },
  { value: "3000000", label: "$3,000,000" },
  { value: "4000000", label: "$4,000,000" },
  { value: "5000000", label: "$5,000,000" },
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
  precedingQuestion?: string;
}

function stripMonetaryFormatting(value: string): string {
  let trimmed = value.trim();
  
  // Handle correction message format - extract just the value
  // Matches: "[Correction] My X should be: VALUE" or "My X should be: VALUE"
  const correctionMatch = trimmed.match(/(?:\[Correction\])?\s*My\s+.+?\s+should\s+be:?\s*(.+)$/i);
  if (correctionMatch) {
    trimmed = correctionMatch[1].trim();
  }
  
  // Remove $ and commas from monetary values
  if (trimmed.startsWith("$") || trimmed.match(/^[\d,]+$/)) {
    return trimmed.replace(/[$,]/g, "");
  }
  // Remove % from percentage values
  if (trimmed.match(/^\d+%$/)) {
    return trimmed.replace(/%$/, "");
  }
  return trimmed;
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
  
  // Extract the last sentence/question to focus on what's actually being asked
  // This helps when the message contains acknowledgment + new question
  const sentences = text.split(/[.!]\s+/);
  const lastSentence = sentences[sentences.length - 1] || text;
  
  // Success rate / Monte Carlo detection - check first (specific)
  if (lastSentence.includes("success rate") || lastSentence.includes("success probability") ||
      lastSentence.includes("monte carlo") || lastSentence.includes("probability of success") ||
      lastSentence.includes("confidence level") || lastSentence.includes("plan success") ||
      (lastSentence.includes("success") && lastSentence.includes("%"))) {
    return { mode: "success_rate" };
  }
  
  // Percentage/savings rate detection - check early (common pattern after balance question)
  if (lastSentence.includes("percentage") || lastSentence.includes("savings rate") || 
      lastSentence.includes("% of your income") || lastSentence.match(/what percent/i) ||
      lastSentence.includes("how much do you save") || lastSentence.includes("contribution rate") ||
      lastSentence.includes("percent of your") || lastSentence.includes("saving rate") ||
      (lastSentence.includes("save") && lastSentence.includes("?"))) {
    return { mode: "percentage" };
  }
  
  // State detection - expanded patterns
  if (lastSentence.includes("which state") || lastSentence.includes("what state") || 
      lastSentence.match(/state do you (live|reside)/) || lastSentence.match(/state.+located/) ||
      lastSentence.includes("your state") || (lastSentence.includes("state") && lastSentence.includes("?"))) {
    return { mode: "state" };
  }
  
  // City detection - expanded patterns
  if (lastSentence.includes("which city") || lastSentence.includes("what city") || 
      lastSentence.match(/city do you (live|reside)/) || lastSentence.match(/city.+located/) ||
      lastSentence.includes("your city") || (lastSentence.includes("city") && lastSentence.includes("?"))) {
    const stateMatch = fullContext.match(/(?:in|from|live in|reside in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/);
    return { mode: "city", stateContext: stateMatch?.[1] };
  }
  
  // Income detection - expanded patterns
  if (lastSentence.includes("gross annual income") || lastSentence.includes("current income") || 
      lastSentence.match(/what is your.+income/) || lastSentence.includes("annual income") ||
      lastSentence.includes("yearly income") || lastSentence.includes("how much do you make") ||
      lastSentence.includes("how much do you earn") || (lastSentence.includes("income") && lastSentence.includes("?"))) {
    return { mode: "income" };
  }
  
  // Legacy detection - expanded patterns
  if (lastSentence.includes("legacy goal") || lastSentence.includes("leave behind") || 
      lastSentence.includes("amount you'd like to leave") || lastSentence.includes("inheritance") ||
      lastSentence.includes("estate") || lastSentence.includes("leave to") || 
      (lastSentence.includes("legacy") && lastSentence.includes("?"))) {
    return { mode: "legacy" };
  }
  
  // Balance detection - expanded patterns
  if (lastSentence.includes("retirement account") || lastSentence.includes("current balance") || 
      lastSentence.match(/balance.+retirement/) || lastSentence.includes("saved for retirement") ||
      lastSentence.includes("retirement savings") || lastSentence.includes("401k") || lastSentence.includes("401(k)") ||
      lastSentence.includes("ira") || (lastSentence.includes("balance") && lastSentence.includes("?"))) {
    return { mode: "balance" };
  }
  
  // Spending detection - expanded patterns
  if (lastSentence.includes("spend per month") || lastSentence.includes("monthly spending") || 
      lastSentence.match(/expect to spend.+retirement/) || lastSentence.includes("monthly expenses") ||
      lastSentence.includes("monthly budget") || lastSentence.includes("spend each month") ||
      (lastSentence.includes("spending") && lastSentence.includes("?"))) {
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
      // Strip formatting for numeric values (like Excel edit mode)
      setValue(stripMonetaryFormatting(editing.originalContent));
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
  
  // When editing, use the preceding question to determine mode; otherwise use lastAssistantMessage
  const modeMessage = editing?.precedingQuestion ?? lastAssistantMessage;
  
  const { mode, stateContext } = useMemo(
    () => detectInputMode(modeMessage, conversationContext),
    [modeMessage, conversationContext]
  );

  // Set default value for percentage modes immediately
  useEffect(() => {
    if (mode === "percentage" && !value && !editing) {
      setValue("6");
    }
    if (mode === "success_rate" && !value && !editing) {
      setValue("90");
    }
  }, [mode, value, editing]);

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
    
    const isMoneyMode = mode === "income" || mode === "legacy" || mode === "balance" || mode === "spending";
    const formattedValue = isMoneyMode ? formatDollarValue(trimmed) : trimmed;
    onSend(formattedValue);
    setValue("");
    requestAnimationFrame(() => {
      inputRef.current?.focus();
    });
  }

  function handleCancel() {
    setValue("");
    onCancelEdit?.();
  }

  function formatDollarValue(value: string): string {
    const num = parseInt(value.replace(/[^0-9]/g, ""), 10);
    if (isNaN(num)) return value;
    return "$" + num.toLocaleString("en-US");
  }

  function handleTypeaheadSelect(selectedValue: string) {
    if (disabled) return;
    const isMoneyMode = mode === "income" || mode === "legacy" || mode === "balance" || mode === "spending";
    const formattedValue = isMoneyMode ? formatDollarValue(selectedValue) : selectedValue;
    onSend(formattedValue);
    setValue("");
  }

  const editingHeader = editing ? (
    <div className="flex items-center gap-2 text-sm text-harbor-600 mb-2">
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
      <span>Editing your previous answer</span>
    </div>
  ) : null;

  const submitButtonText = editing ? "Update" : "Send";
  const isSubmitDisabled = editing 
    ? disabled || !value.trim() || value.trim() === editing.originalContent
    : disabled || !value.trim();

  const cancelButton = editing ? (
    <button
      type="button"
      onClick={handleCancel}
      className="btn-ghost shrink-0"
    >
      Cancel
    </button>
  ) : null;

  if (mode === "state") {
    return (
      <div>
        {editingHeader}
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
          {cancelButton}
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="btn-primary shrink-0"
          >
            {submitButtonText}
          </button>
        </form>
      </div>
    );
  }

  if (mode === "city") {
    return (
      <div>
        {editingHeader}
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
          {cancelButton}
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="btn-primary shrink-0"
          >
            {submitButtonText}
          </button>
        </form>
      </div>
    );
  }

  if (mode === "income") {
    return (
      <div>
        {editingHeader}
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
          {cancelButton}
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="btn-primary shrink-0"
          >
            {submitButtonText}
          </button>
        </form>
      </div>
    );
  }

  if (mode === "legacy") {
    return (
      <div>
        {editingHeader}
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
          {cancelButton}
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="btn-primary shrink-0"
          >
            {submitButtonText}
          </button>
        </form>
      </div>
    );
  }

  if (mode === "balance") {
    return (
      <div>
        {editingHeader}
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
          {cancelButton}
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="btn-primary shrink-0"
          >
            {submitButtonText}
          </button>
        </form>
      </div>
    );
  }

  if (mode === "spending") {
    return (
      <div>
        {editingHeader}
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
          {cancelButton}
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="btn-primary shrink-0"
          >
            {submitButtonText}
          </button>
        </form>
      </div>
    );
  }

  if (mode === "success_rate") {
    const defaultRate = 90;
    const rateValue = value ? parseInt(value, 10) : defaultRate;
    const displayRate = isNaN(rateValue) ? defaultRate : Math.max(60, Math.min(99, rateValue));
    const isDefault = !value || value === String(defaultRate);
    
    // Determine risk level based on success rate
    const getRiskInfo = (rate: number): { level: string; description: string; color: string } => {
      if (rate >= 90) {
        return { 
          level: "Very Conservative", 
          description: "High confidence your plan will succeed",
          color: "text-emerald-600"
        };
      } else if (rate >= 80) {
        return { 
          level: "Moderate", 
          description: "Good balance of security and flexibility",
          color: "text-harbor-600"
        };
      } else if (rate >= 70) {
        return { 
          level: "Acceptable", 
          description: "Some risk but still reasonable",
          color: "text-amber-600"
        };
      } else {
        return { 
          level: "Risky", 
          description: "Plan may need significant adjustments",
          color: "text-red-600"
        };
      }
    };
    
    const riskInfo = getRiskInfo(displayRate);
    
    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          {/* Current value display */}
          <div className="text-center">
            <span className="text-2xl font-bold text-harbor-700">{displayRate}%</span>
            {isDefault && !editing && (
              <span className="ml-2 text-xs text-sage-500">(recommended)</span>
            )}
          </div>
          {/* Risk level indicator */}
          <div className="text-center">
            <span className={`font-semibold ${riskInfo.color}`}>{riskInfo.level}</span>
            <p className="text-xs text-sage-600 mt-0.5">{riskInfo.description}</p>
          </div>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="60"
              max="99"
              value={displayRate}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
              aria-label="Success rate slider"
              title="Plan success probability"
            />
            <div className="flex items-center gap-2 min-w-[80px]">
              <input
                ref={inputRef}
                type="number"
                min="60"
                max="99"
                value={value || "90"}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-16 text-center"
                autoFocus
                aria-label="Success rate value"
                title="Enter success rate"
              />
              <span className="text-harbor-700 font-medium">%</span>
            </div>
          </div>
          <div className="flex justify-between text-xs text-sage-500">
            <span>60%</span>
            <span>80%</span>
            <span>99%</span>
          </div>
          <div className="flex gap-2 sm:gap-3">
            {cancelButton}
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, `${value || "90"}%`);
                } else {
                  onSend(`${value || "90"}%`);
                }
                setValue("");
              }}
              disabled={editing ? isSubmitDisabled : disabled}
              className={editing ? "btn-primary flex-1" : "btn-primary w-full"}
            >
              {submitButtonText}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "percentage") {
    const defaultPercent = 6;
    const percentValue = value ? parseInt(value, 10) : defaultPercent;
    const displayPercent = isNaN(percentValue) ? defaultPercent : Math.max(0, Math.min(50, percentValue));
    const isDefault = !value || value === String(defaultPercent);
    
    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          {/* Current value display */}
          <div className="text-center">
            <span className="text-2xl font-bold text-harbor-700">{displayPercent}%</span>
            {isDefault && !editing && (
              <span className="ml-2 text-xs text-sage-500">(recommended)</span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0"
              max="50"
              value={displayPercent}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
              aria-label="Percentage slider"
              title="Savings percentage"
            />
            <div className="flex items-center gap-2 min-w-[80px]">
              <input
                ref={inputRef}
                type="number"
                min="0"
                max="100"
                value={value || "6"}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-16 text-center"
                autoFocus
                aria-label="Percentage value"
                title="Enter percentage"
              />
              <span className="text-harbor-700 font-medium">%</span>
            </div>
          </div>
          <div className="flex justify-between text-xs text-sage-500">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
          </div>
          <div className="flex gap-2 sm:gap-3">
            {cancelButton}
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, `${value || "6"}%`);
                } else {
                  onSend(`${value || "6"}%`);
                }
                setValue("");
              }}
              disabled={editing ? isSubmitDisabled : disabled}
              className={editing ? "btn-primary flex-1" : "btn-primary w-full"}
            >
              {submitButtonText}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {editingHeader}
      <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={editing ? "Update your answer..." : placeholder}
          className={`input-field flex-1 ${editing ? "ring-2 ring-harbor-200" : ""}`}
          autoFocus
        />
        {cancelButton}
        <button
          type="submit"
          disabled={isSubmitDisabled}
          className="btn-primary shrink-0"
        >
          {submitButtonText}
        </button>
      </form>
    </div>
  );
}
