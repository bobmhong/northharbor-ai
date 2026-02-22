import { useRef, useState, useEffect, type FormEvent, useMemo } from "react";
import Typeahead from "../ui/Typeahead";
import { getStatesForAutocomplete, getCitiesForState } from "../../data/locations";
import { validateField } from "../../utils/fieldValidation";

type InputMode = "text" | "open_text" | "state" | "city" | "income" | "legacy" | "balance" | "spending" | "percentage" | "success_rate" | "claiming_age" | "employer_plan" | "employer_match" | "employee_contribution" | "ss_benefit" | "retirement_age";

const INCOME_SUGGESTIONS = [
  { value: "25000", label: "$25,000" },
  { value: "35000", label: "$35,000" },
  { value: "50000", label: "$50,000" },
  { value: "75000", label: "$75,000" },
  { value: "100000", label: "$100,000" },
  { value: "125000", label: "$125,000" },
  { value: "150000", label: "$150,000" },
  { value: "200000", label: "$200,000" },
  { value: "250000", label: "$250,000" },
  { value: "300000", label: "$300,000" },
  { value: "400000", label: "$400,000" },
  { value: "500000", label: "$500,000" },
  { value: "750000", label: "$750,000" },
  { value: "1000000", label: "$1,000,000" },
];

const LEGACY_SUGGESTIONS = [
  { value: "0", label: "$0 (no legacy goal)" },
  { value: "50000", label: "$50,000" },
  { value: "100000", label: "$100,000" },
  { value: "250000", label: "$250,000" },
  { value: "500000", label: "$500,000" },
  { value: "750000", label: "$750,000" },
  { value: "1000000", label: "$1,000,000" },
  { value: "2000000", label: "$2,000,000" },
  { value: "5000000", label: "$5,000,000" },
];

const BALANCE_SUGGESTIONS = [
  { value: "0", label: "$0 (just starting)" },
  { value: "10000", label: "$10,000" },
  { value: "25000", label: "$25,000" },
  { value: "50000", label: "$50,000" },
  { value: "100000", label: "$100,000" },
  { value: "250000", label: "$250,000" },
  { value: "500000", label: "$500,000" },
  { value: "750000", label: "$750,000" },
  { value: "1000000", label: "$1,000,000" },
  { value: "1500000", label: "$1,500,000" },
  { value: "2000000", label: "$2,000,000" },
  { value: "3000000", label: "$3,000,000" },
  { value: "5000000", label: "$5,000,000" },
  { value: "7500000", label: "$7,500,000" },
  { value: "10000000", label: "$10,000,000" },
];

const SPENDING_SUGGESTIONS = [
  { value: "2000", label: "$2,000/month" },
  { value: "3000", label: "$3,000/month" },
  { value: "4000", label: "$4,000/month" },
  { value: "5000", label: "$5,000/month" },
  { value: "6000", label: "$6,000/month" },
  { value: "7500", label: "$7,500/month" },
  { value: "10000", label: "$10,000/month" },
  { value: "15000", label: "$15,000/month" },
  { value: "20000", label: "$20,000/month" },
  { value: "30000", label: "$30,000/month" },
];

const SS_BENEFIT_SUGGESTIONS = [
  { value: "500", label: "$500/month" },
  { value: "1000", label: "$1,000/month" },
  { value: "1500", label: "$1,500/month" },
  { value: "2000", label: "$2,000/month" },
  { value: "2500", label: "$2,500/month" },
  { value: "3000", label: "$3,000/month" },
  { value: "3500", label: "$3,500/month" },
  { value: "4000", label: "$4,000/month" },
  { value: "4500", label: "$4,500/month" },
  { value: "5000", label: "$5,000/month" },
];

interface EditingState {
  index: number;
  originalContent: string;
  precedingQuestion?: string;
  precedingFieldPath?: string;
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

function extractConfirmationValue(message?: string): string | undefined {
  if (!message) return undefined;
  // Handles messages like: "I have your planning horizon age as 95. Can you confirm?"
  const match = message.match(/\bas\s+([^\n.?!]+)\s*\.\s*Can you confirm\??/i);
  if (!match) return undefined;
  return match[1].trim();
}

function parseNumericValue(raw?: string): number | undefined {
  if (!raw) return undefined;
  const num = parseFloat(raw.replace(/[%,$,\s]/g, ""));
  if (isNaN(num)) return undefined;
  return num;
}

function getFullRetirementAge(birthYear?: number): number {
  if (!birthYear || birthYear <= 0) return 67;
  if (birthYear <= 1937) return 65;
  if (birthYear === 1938) return 65 + 2 / 12;
  if (birthYear === 1939) return 65 + 4 / 12;
  if (birthYear === 1940) return 65 + 6 / 12;
  if (birthYear === 1941) return 65 + 8 / 12;
  if (birthYear === 1942) return 65 + 10 / 12;
  if (birthYear <= 1954) return 66;
  if (birthYear === 1955) return 66 + 2 / 12;
  if (birthYear === 1956) return 66 + 4 / 12;
  if (birthYear === 1957) return 66 + 6 / 12;
  if (birthYear === 1958) return 66 + 8 / 12;
  if (birthYear === 1959) return 66 + 10 / 12;
  return 67;
}

function formatFraLabel(fra: number): string {
  const years = Math.floor(fra);
  const months = Math.round((fra - years) * 12);
  if (months <= 0) return `${years}`;
  return `${years} years ${months} months`;
}

function estimateBenefitPercentAtAge(claimAge: number, fra: number): number {
  if (claimAge < fra) {
    return Math.max(70, 100 - (fra - claimAge) * 6.67);
  }
  if (claimAge > fra) {
    return Math.min(124, 100 + (claimAge - fra) * 8);
  }
  return 100;
}

function getBenefitBarWidthClass(percentOfMax: number): string {
  const pct = Math.max(0, Math.min(100, percentOfMax));
  if (pct >= 95) return "w-full";
  if (pct >= 85) return "w-11/12";
  if (pct >= 75) return "w-10/12";
  if (pct >= 65) return "w-8/12";
  if (pct >= 55) return "w-7/12";
  if (pct >= 45) return "w-6/12";
  if (pct >= 35) return "w-5/12";
  if (pct >= 25) return "w-4/12";
  if (pct >= 15) return "w-3/12";
  if (pct >= 5) return "w-2/12";
  return "w-1/12";
}

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  lastAssistantMessage?: string;
  currentTargetField?: string;
  currentTargetValue?: string;
  clientBirthYearValue?: string;
  conversationContext?: string;
  editing?: EditingState | null;
  onCancelEdit?: () => void;
  onSubmitEdit?: (index: number, newContent: string) => void;
  onSkipToAnalysis?: () => void;
}

function detectInputMode(message?: string, context?: string, targetField?: string): { mode: InputMode; stateContext?: string } {
  // Prefer backend-declared target field over text heuristics.
  switch (targetField) {
    case "location.state":
      return { mode: "state" };
    case "location.city":
      return { mode: "city" };
    case "income.current_gross_annual":
      return { mode: "income" };
    case "retirement_philosophy.legacy_goal_total_real":
      return { mode: "legacy" };
    case "accounts.retirement_balance":
      return { mode: "balance" };
    case "spending.retirement_monthly_real":
      return { mode: "spending" };
    case "client.retirement_window":
      return { mode: "retirement_age" };
    case "retirement_philosophy.success_probability_target":
    case "monte_carlo.required_success_rate":
      return { mode: "success_rate" };
    case "social_security.combined_at_67_monthly":
    case "social_security.combined_at_70_monthly":
      return { mode: "ss_benefit" };
    case "social_security.claiming_preference":
      return { mode: "claiming_age" };
    case "accounts.has_employer_plan":
      return { mode: "employer_plan" };
    case "accounts.employer_match_percent":
      return { mode: "employer_match" };
    case "accounts.employee_contribution_percent":
      return { mode: "employee_contribution" };
    case "accounts.savings_rate_percent":
      return { mode: "percentage" };
    case "additional_considerations":
      return { mode: "open_text" };
    default:
      break;
  }

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

  // Social Security benefit amount detection
  if (lastSentence.includes("social security benefit") || (lastSentence.includes("social security") && lastSentence.includes("monthly")) ||
      lastSentence.match(/benefit at age\s+\d+/) || lastSentence.includes("expected benefit") ||
      (lastSentence.includes("social security") && (lastSentence.includes("67") || lastSentence.includes("70")) && !lastSentence.includes("claim"))) {
    return { mode: "ss_benefit" };
  }

  // Social Security claiming age detection
  if (text.includes("claim social security") || text.includes("claiming social security") ||
      text.includes("start claiming social security") || text.includes("claiming age") ||
      (text.includes("social security") && text.includes("62") && text.includes("70"))) {
    return { mode: "claiming_age" };
  }
  
  // Employer plan detection (yes/no question)
  if (lastSentence.includes("employer offer") || lastSentence.includes("employer retirement") ||
      lastSentence.includes("401(k)") || lastSentence.includes("401k") ||
      lastSentence.includes("employer savings plan") || lastSentence.includes("workplace retirement") ||
      (lastSentence.includes("employer") && lastSentence.includes("plan"))) {
    return { mode: "employer_plan" };
  }
  
  // Employer match detection (specific percentage about match)
  // Check full text since questions may span multiple sentences
  if (text.includes("employer match") || text.includes("company match") ||
      text.includes("matching contribution") || text.includes("does your employer match") ||
      text.includes("what percentage does your employer") ||
      (text.includes("match") && text.includes("contributions"))) {
    return { mode: "employer_match" };
  }
  
  // Employee contribution detection (how much YOU contribute to employer plan)
  // Check full text since the question may have multiple sentences with match context
  if (text.includes("do you contribute") || text.includes("your contribution") ||
      text.includes("contribute to your retirement plan") || 
      text.includes("employee contribution") ||
      text.includes("captures the full match") ||
      (text.includes("percentage of your income") && text.includes("contribute"))) {
    return { mode: "employee_contribution" };
  }
  
  // Percentage/savings rate detection - general savings rate
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
  
  // Retirement age detection
  if (lastSentence.includes("retirement age") || (lastSentence.includes("retire") && lastSentence.includes("age")) ||
      lastSentence.includes("when would you like to retire") || lastSentence.includes("plan to retire") ||
      (lastSentence.includes("aiming for") && lastSentence.includes("retire"))) {
    return { mode: "retirement_age" };
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
  currentTargetField,
  currentTargetValue,
  clientBirthYearValue,
  conversationContext,
  editing,
  onCancelEdit,
  onSubmitEdit,
  onSkipToAnalysis,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [retireAgeMin, setRetireAgeMin] = useState(65);
  const [retireAgeMax, setRetireAgeMax] = useState(67);
  const [claimTipOpen, setClaimTipOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const claimTipRef = useRef<HTMLDivElement>(null);
  
  const prevDisabledRef = useRef(disabled);
  const prevModeRef = useRef<InputMode | null>(null);
  
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
  const modeTargetField = editing?.precedingFieldPath ?? currentTargetField;
  
  const { mode, stateContext } = useMemo(
    () => detectInputMode(modeMessage, conversationContext, modeTargetField),
    [modeMessage, conversationContext, modeTargetField]
  );

  const defaultSuccessRate = useMemo(() => {
    // Use existing value for this field if available, otherwise default to 95%
    const raw = (currentTargetValue || "").trim();
    if (!raw) return "95";

    const numeric = parseFloat(raw.replace(/[%,$,\s]/g, ""));
    if (!isNaN(numeric)) {
      // If value is stored as ratio (e.g., 0.95), convert to percentage
      const asPercent = numeric <= 1 ? numeric * 100 : numeric;
      const clamped = Math.max(60, Math.min(99, Math.round(asPercent)));
      return String(clamped);
    }
    return "95";
  }, [currentTargetValue]);
  const hasSavedSuccessRate = Boolean((currentTargetValue || "").trim());
  const birthYearNum = useMemo(() => {
    const parsed = parseNumericValue(clientBirthYearValue);
    if (!parsed) return undefined;
    return Math.round(parsed);
  }, [clientBirthYearValue]);
  const fra = useMemo(() => getFullRetirementAge(birthYearNum), [birthYearNum]);
  const defaultClaimingAge = useMemo(() => {
    const existing = parseNumericValue(currentTargetValue);
    const base = existing ? Math.round(existing) : Math.round(fra);
    return String(Math.max(62, Math.min(70, base)));
  }, [currentTargetValue, fra]);

  // Set defaults when entering mode-specific controls; avoid re-seeding while staying on same mode.
  useEffect(() => {
    if (editing) return;

    const prevMode = prevModeRef.current;
    const modeChanged = prevMode !== mode;

    if (!modeChanged) {
      return;
    }

    // Clear stale numeric defaults when moving from slider controls to plain text.
    const cameFromSlider =
      prevMode === "percentage" ||
      prevMode === "success_rate" ||
      prevMode === "claiming_age" ||
      prevMode === "employer_match" ||
      prevMode === "employee_contribution" ||
      prevMode === "retirement_age";
    if (cameFromSlider && mode === "text") {
      setValue("");
    }

    if (mode === "retirement_age") {
      const raw = (currentTargetValue || "").trim();
      const rangeMatch = raw.match(/(\d{2})\D+(\d{2})/);
      if (rangeMatch) {
        setRetireAgeMin(Math.max(50, Math.min(80, parseInt(rangeMatch[1], 10))));
        setRetireAgeMax(Math.max(50, Math.min(80, parseInt(rangeMatch[2], 10))));
      } else {
        const single = parseNumericValue(raw);
        if (single && single >= 50 && single <= 80) {
          setRetireAgeMin(Math.round(single));
          setRetireAgeMax(Math.round(single));
        } else {
          setRetireAgeMin(65);
          setRetireAgeMax(67);
        }
      }
    } else if (mode === "percentage") {
      setValue("6");
    } else if (mode === "success_rate") {
      setValue(defaultSuccessRate);
    } else if (mode === "claiming_age") {
      setValue(defaultClaimingAge);
    } else if (mode === "text") {
      const confirmValue = extractConfirmationValue(lastAssistantMessage);
      if (confirmValue) {
        setValue(stripMonetaryFormatting(confirmValue));
      }
    }
  }, [mode, editing, defaultSuccessRate, defaultClaimingAge, lastAssistantMessage]);

  useEffect(() => {
    prevModeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    if (!claimTipOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (!claimTipRef.current) return;
      if (!claimTipRef.current.contains(e.target as Node)) {
        setClaimTipOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [claimTipOpen]);

  // Handle Escape key to cancel editing
  useEffect(() => {
    if (!editing) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && onCancelEdit) {
        e.preventDefault();
        onCancelEdit();
      }
    };
    
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [editing, onCancelEdit]);

  useEffect(() => {
    if (validationError) setValidationError(null);
  }, [value]);

  // Handle Enter key to submit default values for slider/button modes
  useEffect(() => {
    // Only handle for modes that don't have a standard form submit
    const enterModes = ["employer_plan", "employer_match", "employee_contribution", "percentage", "success_rate", "claiming_age", "retirement_age"];
    if (!enterModes.includes(mode)) return;
    if (disabled) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is in a number input (let them type)
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" && (target as HTMLInputElement).type === "number") {
        // For number inputs, Enter should submit
        if (e.key !== "Enter") return;
      } else if (e.key !== "Enter") {
        return;
      }
      
      e.preventDefault();
      
      // Get the default/current value based on mode
      let submitValue = "";
      if (mode === "employer_plan") {
        submitValue = "Yes"; // Default to Yes for employer plan
      } else if (mode === "employer_match") {
        submitValue = `${value || "3"}%`;
      } else if (mode === "employee_contribution") {
        submitValue = `${value || "6"}%`;
      } else if (mode === "percentage") {
        submitValue = `${value || "6"}%`;
      } else if (mode === "success_rate") {
        submitValue = `${value || defaultSuccessRate}%`;
      } else if (mode === "claiming_age") {
        submitValue = `${value || defaultClaimingAge}`;
      } else if (mode === "retirement_age") {
        submitValue = retireAgeMin === retireAgeMax
          ? `${retireAgeMin}`
          : `${retireAgeMin} to ${retireAgeMax}`;
      }
      
      if (editing && onSubmitEdit) {
        onSubmitEdit(editing.index, submitValue);
      } else {
        onSend(submitValue);
      }
      setValue("");
    };
    
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [mode, value, disabled, editing, onSubmitEdit, onSend, defaultSuccessRate, defaultClaimingAge]);

  const stateOptions = useMemo(() => getStatesForAutocomplete(), []);
  const cityOptions = useMemo(
    () => (stateContext ? getCitiesForState(stateContext) : []),
    [stateContext]
  );

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    if (currentTargetField && mode !== "open_text") {
      const result = validateField(currentTargetField, trimmed);
      if (!result.valid) {
        setValidationError(result.error ?? "Invalid input");
        return;
      }
      setValidationError(null);
    }
    
    if (editing && onSubmitEdit) {
      onSubmitEdit(editing.index, trimmed);
      setValue("");
      return;
    }
    
    const isMoneyMode = mode === "income" || mode === "legacy" || mode === "balance" || mode === "spending" || mode === "ss_benefit";
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
    const isMoneyMode = mode === "income" || mode === "legacy" || mode === "balance" || mode === "spending" || mode === "ss_benefit";
    const formattedValue = isMoneyMode ? formatDollarValue(selectedValue) : selectedValue;
    if (editing && onSubmitEdit) {
      onSubmitEdit(editing.index, formattedValue);
    } else {
      onSend(formattedValue);
    }
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

  if (mode === "ss_benefit") {
    return (
      <div>
        {editingHeader}
        <form onSubmit={handleSubmit} className="flex gap-2 sm:gap-3">
          <div className="flex-1">
            <Typeahead
              options={SS_BENEFIT_SUGGESTIONS}
              value={value}
              onChange={setValue}
              onSelect={handleTypeaheadSelect}
              placeholder="Enter monthly benefit or select..."
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

  if (mode === "retirement_age") {
    const isSingleAge = retireAgeMin === retireAgeMax;
    const displayLabel = isSingleAge
      ? `Age ${retireAgeMin}`
      : `Ages ${retireAgeMin} – ${retireAgeMax}`;

    const handleMinChange = (v: number) => {
      const clamped = Math.max(50, Math.min(80, v));
      setRetireAgeMin(clamped);
      if (clamped > retireAgeMax) setRetireAgeMax(clamped);
    };
    const handleMaxChange = (v: number) => {
      const clamped = Math.max(50, Math.min(80, v));
      setRetireAgeMax(clamped);
      if (clamped < retireAgeMin) setRetireAgeMin(clamped);
    };

    const submitRetirementAge = () => {
      if (disabled) return;
      const submitValue = isSingleAge
        ? `${retireAgeMin}`
        : `${retireAgeMin} to ${retireAgeMax}`;
      if (editing && onSubmitEdit) {
        onSubmitEdit(editing.index, submitValue);
      } else {
        onSend(submitValue);
      }
    };

    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          <div className="text-center">
            <span className="text-2xl font-bold text-harbor-700">{displayLabel}</span>
          </div>
          <div className="text-center text-xs text-sage-600">
            {isSingleAge
              ? "Drag the sliders apart to set a range, or pick a single target age."
              : `A ${retireAgeMax - retireAgeMin}-year window gives you flexibility on timing.`}
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <label htmlFor="retire-age-min" className="text-xs text-sage-600 w-14 text-right shrink-0">Earliest</label>
              <input
                id="retire-age-min"
                type="range"
                min="50"
                max="80"
                value={retireAgeMin}
                onChange={(e) => handleMinChange(parseInt(e.target.value, 10))}
                disabled={disabled}
                className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
                aria-label="Earliest retirement age"
              />
              <input
                type="number"
                min="50"
                max="80"
                value={retireAgeMin}
                onChange={(e) => handleMinChange(parseInt(e.target.value, 10) || 50)}
                disabled={disabled}
                className="input-field w-16 text-center text-sm"
                aria-label="Earliest retirement age value"
              />
            </div>
            <div className="flex items-center gap-3">
              <label htmlFor="retire-age-max" className="text-xs text-sage-600 w-14 text-right shrink-0">Latest</label>
              <input
                id="retire-age-max"
                type="range"
                min="50"
                max="80"
                value={retireAgeMax}
                onChange={(e) => handleMaxChange(parseInt(e.target.value, 10))}
                disabled={disabled}
                className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
                aria-label="Latest retirement age"
              />
              <input
                type="number"
                min="50"
                max="80"
                value={retireAgeMax}
                onChange={(e) => handleMaxChange(parseInt(e.target.value, 10) || 50)}
                disabled={disabled}
                className="input-field w-16 text-center text-sm"
                aria-label="Latest retirement age value"
              />
            </div>
          </div>
          <div className="flex justify-between text-xs text-sage-500 px-[4.75rem]">
            <span>50</span>
            <span>65</span>
            <span>80</span>
          </div>
          <div className="flex gap-2 sm:gap-3">
            {cancelButton}
            <button
              type="button"
              onClick={submitRetirementAge}
              disabled={editing ? disabled : disabled}
              className={editing ? "btn-primary flex-1" : "btn-primary w-full"}
            >
              {submitButtonText}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "success_rate") {
    const defaultRate = parseInt(defaultSuccessRate, 10) || 95;
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
            {isDefault && !editing && !hasSavedSuccessRate && (
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
            <div className="flex items-center gap-2 min-w-[96px]">
              <input
                ref={inputRef}
                type="number"
                min="60"
                max="99"
                value={value || String(defaultRate)}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-20 text-center"
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
                  onSubmitEdit(editing.index, `${value || String(defaultRate)}%`);
                } else {
                  onSend(`${value || String(defaultRate)}%`);
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

  if (mode === "claiming_age") {
    const defaultAge = parseInt(defaultClaimingAge, 10) || 67;
    const ageValue = value ? parseInt(value, 10) : defaultAge;
    const displayAge = isNaN(ageValue) ? defaultAge : Math.max(62, Math.min(70, ageValue));
    const ageTicks = [62, 63, 64, 65, 66, 67, 68, 69, 70];

    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          <div className="text-center">
            <span className="text-2xl font-bold text-harbor-700">Age {displayAge}</span>
          </div>
          <div className="rounded-lg border border-sage-200 bg-sage-50 px-3 py-2 text-center text-xs text-sage-700">
            Full retirement age (FRA): <span className="font-semibold text-harbor-700">{formatFraLabel(fra)}</span>
          </div>
          <div className="relative flex items-center justify-center">
            <div ref={claimTipRef} className="group relative inline-flex items-center">
              <button
                type="button"
                onClick={() => setClaimTipOpen((open) => !open)}
                className="inline-flex items-center gap-1 rounded-full border border-sage-300 bg-white px-3 py-1 text-xs font-medium text-sage-700 hover:bg-sage-50 focus:outline-none focus:ring-2 focus:ring-harbor-300"
                aria-label="Show Social Security claim age benefit tip"
                title="Tip: see how claim age affects benefits"
              >
                <svg className="h-3.5 w-3.5 text-harbor-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Tip: claim age impact
              </button>
              <div className={`absolute bottom-full left-1/2 z-30 mb-2 w-[320px] -translate-x-1/2 rounded-lg border border-sage-200 bg-white p-3 shadow-elevated ${claimTipOpen ? "block" : "hidden group-hover:block group-focus-within:block"}`}>
                <p className="mb-2 text-xs font-medium text-sage-700">
                  Estimated monthly benefit impact (relative to FRA = 100%)
                </p>
                <div className="space-y-1.5">
                  {ageTicks.map((age) => {
                    const pct = Math.round(estimateBenefitPercentAtAge(age, fra));
                    const isSelected = age === displayAge;
                    const widthClass = getBenefitBarWidthClass((pct / 124) * 100);
                    return (
                      <div key={age} className="flex items-center gap-2">
                        <span className={`w-8 text-xs ${isSelected ? "font-semibold text-harbor-700" : "text-sage-600"}`}>
                          {age}
                        </span>
                        <div className="h-2 flex-1 rounded bg-sage-100">
                          <div
                            className={`h-2 rounded ${widthClass} ${isSelected ? "bg-harbor-500" : "bg-sage-300"}`}
                          />
                        </div>
                        <span className={`w-12 text-right text-xs ${isSelected ? "font-semibold text-harbor-700" : "text-sage-600"}`}>
                          {pct}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="62"
              max="70"
              value={displayAge}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
              aria-label="Social Security claiming age slider"
              title="Social Security claiming age"
            />
            <div className="flex items-center gap-2 min-w-[96px]">
              <input
                ref={inputRef}
                type="number"
                min="62"
                max="70"
                value={value || String(defaultAge)}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-20 text-center"
                autoFocus
                aria-label="Claiming age value"
                title="Enter claiming age"
              />
            </div>
          </div>
          <div className="flex justify-between text-xs text-sage-500">
            <span>62</span>
            <span>FRA {Math.round(fra)}</span>
            <span>70</span>
          </div>
          <div className="flex gap-2 sm:gap-3">
            {cancelButton}
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                const submitVal = value || String(defaultAge);
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, submitVal);
                } else {
                  onSend(submitVal);
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

  if (mode === "employer_plan") {
    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          <div className="flex gap-3 justify-center">
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, "Yes");
                } else {
                  onSend("Yes");
                }
              }}
              disabled={disabled}
              className="btn-primary px-8"
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, "No");
                } else {
                  onSend("No");
                }
              }}
              disabled={disabled}
              className="btn-ghost px-8 border border-sage-300"
            >
              No
            </button>
          </div>
          {cancelButton && (
            <div className="flex justify-center">
              {cancelButton}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (mode === "employer_match") {
    const defaultMatch = 3;
    const matchValue = value ? parseInt(value, 10) : defaultMatch;
    const displayMatch = isNaN(matchValue) ? defaultMatch : Math.max(0, Math.min(10, matchValue));
    
    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          <div className="text-center">
            <span className="text-2xl font-bold text-harbor-700">{displayMatch}%</span>
          </div>
          <div className="text-center text-xs text-sage-600">
            Common match: 3% (50% of 6%) or 6% (dollar-for-dollar up to 6%)
          </div>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0"
              max="10"
              step="0.5"
              value={displayMatch}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
              aria-label="Employer match slider"
              title="Employer match percentage"
            />
            <div className="flex items-center gap-2 min-w-[96px]">
              <input
                ref={inputRef}
                type="number"
                min="0"
                max="10"
                step="0.5"
                value={value || "3"}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-20 text-center"
                autoFocus
                aria-label="Match percentage value"
                title="Enter match percentage"
              />
              <span className="text-harbor-700 font-medium">%</span>
            </div>
          </div>
          <div className="flex justify-between text-xs text-sage-500">
            <span>0%</span>
            <span>5%</span>
            <span>10%</span>
          </div>
          <div className="flex gap-2 sm:gap-3">
            {cancelButton}
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, `${value || "3"}%`);
                } else {
                  onSend(`${value || "3"}%`);
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

  if (mode === "employee_contribution") {
    // Try to extract employer match from conversation context for guidance
    const matchFromContext = conversationContext?.match(/(\d+(?:\.\d+)?)\s*%?\s*(?:match|matching)/i);
    const employerMatch = matchFromContext ? parseFloat(matchFromContext[1]) : null;
    
    // Calculate minimum to get full match (typically need to contribute enough to get full match)
    // Common scenarios: 50% match up to 6% = need 6% to get 3% match, or 100% match up to 3% = need 3% to get 3%
    const minForFullMatch = employerMatch ? Math.ceil(employerMatch * 2) : null;
    
    // Default to the recommended minimum to capture full match, or 6% if no match info
    const defaultContrib = minForFullMatch || 6;
    const contribValue = value ? parseInt(value, 10) : defaultContrib;
    const displayContrib = isNaN(contribValue) ? defaultContrib : Math.max(0, Math.min(50, contribValue));
    const isGettingFullMatch = minForFullMatch ? displayContrib >= minForFullMatch : true;
    
    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          <div className="text-center">
            <span className="text-2xl font-bold text-harbor-700">{displayContrib}%</span>
          </div>
          {/* Match guidance */}
          {employerMatch && (
            <div className={`text-center text-sm px-3 py-2 rounded-lg ${
              isGettingFullMatch 
                ? "bg-emerald-50 text-emerald-700" 
                : "bg-amber-50 text-amber-700"
            }`}>
              {isGettingFullMatch ? (
                <span className="flex items-center justify-center gap-1.5">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  You're capturing the full employer match
                </span>
              ) : (
                <span className="flex items-center justify-center gap-1.5">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Contribute at least {minForFullMatch}% to capture your full match
                </span>
              )}
            </div>
          )}
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0"
              max="50"
              value={displayContrib}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              className="flex-1 h-2 bg-sage-200 rounded-lg appearance-none cursor-pointer accent-harbor-500"
              aria-label="Contribution slider"
              title="Your contribution percentage"
            />
            <div className="flex items-center gap-2 min-w-[96px]">
              <input
                ref={inputRef}
                type="number"
                min="0"
                max="100"
                value={value || String(defaultContrib)}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-20 text-center"
                autoFocus
                aria-label="Contribution percentage value"
                title="Enter contribution percentage"
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
                const submitVal = value || String(defaultContrib);
                if (editing && onSubmitEdit) {
                  onSubmitEdit(editing.index, `${submitVal}%`);
                } else {
                  onSend(`${submitVal}%`);
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
            <div className="flex items-center gap-2 min-w-[96px]">
              <input
                ref={inputRef}
                type="number"
                min="0"
                max="100"
                value={value || "6"}
                onChange={(e) => setValue(e.target.value)}
                disabled={disabled}
                className="input-field w-20 text-center"
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

  if (mode === "open_text") {
    return (
      <div>
        {editingHeader}
        <div className="space-y-3">
          <textarea
            ref={inputRef as any}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={disabled}
            placeholder="Describe any upcoming events, plans, or circumstances that could affect your finances..."
            className="input-field w-full min-h-[100px] resize-y"
            autoFocus
            rows={4}
          />
          <div className="flex gap-2 sm:gap-3">
            {cancelButton}
            <button
              type="button"
              onClick={() => {
                if (disabled || !value.trim()) return;
                onSend(value.trim());
                setValue("");
              }}
              disabled={disabled || !value.trim()}
              className="btn-primary flex-1"
            >
              Send
            </button>
            <button
              type="button"
              onClick={() => {
                if (disabled) return;
                onSend("nothing else");
                setValue("");
              }}
              disabled={disabled}
              className="btn-ghost border border-sage-300"
            >
              Nothing else
            </button>
            {onSkipToAnalysis && (
              <button
                type="button"
                onClick={() => {
                  if (disabled) return;
                  onSkipToAnalysis();
                }}
                disabled={disabled}
                className="btn-ghost border border-emerald-300 text-emerald-700 hover:bg-emerald-50"
              >
                Run Analysis
              </button>
            )}
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
      {validationError && (
        <p className="mt-1 text-xs text-red-600">{validationError}</p>
      )}
    </div>
  );
}
