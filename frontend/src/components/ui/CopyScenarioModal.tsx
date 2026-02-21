import { useEffect, useRef, useState } from "react";
import { cn } from "../../lib/utils";

interface CopyScenarioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (scenarioName: string) => void;
  existingNames: string[];
  defaultName?: string;
  isPending?: boolean;
}

export default function CopyScenarioModal({
  isOpen,
  onClose,
  onConfirm,
  existingNames,
  defaultName = "",
  isPending = false,
}: CopyScenarioModalProps) {
  const [name, setName] = useState(defaultName);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setName(defaultName);
      setError(null);
      requestAnimationFrame(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      });
    }
  }, [isOpen, defaultName]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isOpen && !isPending) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isPending, onClose]);

  function validateName(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    
    const normalizedInput = trimmed.toLowerCase();
    const isDuplicate = existingNames.some(
      (existing) => existing.toLowerCase() === normalizedInput
    );
    
    if (isDuplicate) {
      return `A scenario named "${trimmed}" already exists. Please choose a different name.`;
    }
    
    return null;
  }

  function handleNameChange(value: string) {
    setName(value);
    setError(validateName(value));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validateName(name);
    if (validationError) {
      setError(validationError);
      return;
    }
    onConfirm(name.trim());
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-harbor-900/50 backdrop-blur-sm"
        onClick={isPending ? undefined : onClose}
      />
      
      <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-elevated">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-harbor-100">
            <svg className="h-5 w-5 text-harbor-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-harbor-900">Copy Scenario</h3>
            <p className="text-sm text-sage-600">Create a copy with a new name</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="scenario-name" className="mb-1.5 block text-sm font-medium text-harbor-700">
              Scenario Name
            </label>
            <input
              ref={inputRef}
              id="scenario-name"
              type="text"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              disabled={isPending}
              placeholder="Enter a unique scenario name..."
              className={cn(
                "input-field w-full",
                error && "border-red-300 focus:border-red-400 focus:ring-red-100"
              )}
              autoComplete="off"
            />
            {error && (
              <p className="mt-1.5 flex items-center gap-1.5 text-sm text-red-600">
                <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                {error}
              </p>
            )}
            <p className="mt-1.5 text-xs text-sage-500">
              Leave empty to auto-generate a name based on the original.
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="btn-ghost"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || !!error}
              className="btn-primary"
            >
              {isPending ? (
                <span className="flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Copying...
                </span>
              ) : (
                "Copy Scenario"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
