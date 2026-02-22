import { useEffect, useRef, useState, useMemo } from "react";
import { cn } from "../../lib/utils";

interface TypeaheadOption {
  value: string;
  label: string;
}

interface TypeaheadProps {
  options: TypeaheadOption[];
  value: string;
  onChange: (value: string) => void;
  onSelect: (value: string) => void;
  placeholder?: string;
  allowCustom?: boolean;
  customLabel?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}

export default function Typeahead({
  options,
  value,
  onChange,
  onSelect,
  placeholder = "Type to search...",
  allowCustom = false,
  customLabel = "Use custom value",
  disabled = false,
  autoFocus = false,
}: TypeaheadProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const listboxIdRef = useRef(`typeahead-listbox-${Math.random().toString(36).slice(2, 10)}`);

  const filteredOptions = useMemo(() => 
    options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(value.toLowerCase()) ||
        opt.value.toLowerCase().includes(value.toLowerCase())
    ),
    [options, value]
  );

  const autocompleteMatch = useMemo(() => {
    if (!value.trim()) return null;
    const lowerValue = value.toLowerCase();
    const match = options.find(
      (opt) => opt.label.toLowerCase().startsWith(lowerValue)
    );
    return match || null;
  }, [options, value]);

  const showCustomOption =
    allowCustom &&
    value.trim() !== "" &&
    !filteredOptions.some(
      (opt) => opt.value.toLowerCase() === value.trim().toLowerCase()
    );

  const totalOptions = filteredOptions.length + (showCustomOption ? 1 : 0);

  useEffect(() => {
    setHighlightedIndex(0);
  }, [value]);

  const prevDisabledRef = useRef(disabled);
  
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  useEffect(() => {
    if (prevDisabledRef.current && !disabled && inputRef.current) {
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
    prevDisabledRef.current = disabled;
  }, [disabled]);

  useEffect(() => {
    if (isOpen && listRef.current) {
      const highlighted = listRef.current.children[highlightedIndex] as HTMLElement;
      if (highlighted) {
        highlighted.scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightedIndex, isOpen]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!isOpen && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setIsOpen(true);
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) => Math.min(prev + 1, totalOptions - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (isOpen && totalOptions > 0) {
          if (showCustomOption && highlightedIndex === filteredOptions.length) {
            onSelect(value.trim());
          } else if (filteredOptions[highlightedIndex]) {
            onSelect(filteredOptions[highlightedIndex].value);
          }
          setIsOpen(false);
        } else if (value.trim()) {
          onSelect(value.trim());
        }
        break;
      case "Escape":
        setIsOpen(false);
        break;
      case "Tab":
        if (autocompleteMatch && value.trim()) {
          e.preventDefault();
          onChange(autocompleteMatch.label);
          setIsOpen(true);
        } else {
          setIsOpen(false);
        }
        break;
    }
  }

  function handleOptionClick(optionValue: string) {
    onSelect(optionValue);
    setIsOpen(false);
    inputRef.current?.focus();
  }

  const ghostText = autocompleteMatch && value.trim() 
    ? autocompleteMatch.label.slice(value.length) 
    : "";

  return (
    <div className="relative w-full">
      <div className="relative">
        {ghostText && (
          <div 
            className="absolute inset-0 flex items-center pointer-events-none px-4 py-3"
            aria-hidden="true"
          >
            <span className="invisible">{value}</span>
            <span className="text-sage-400">{ghostText}</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onBlur={() => {
            setTimeout(() => setIsOpen(false), 150);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="input-field w-full bg-transparent relative"
          autoComplete="off"
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          aria-controls={isOpen && totalOptions > 0 ? listboxIdRef.current : undefined}
        />
      </div>

      {ghostText && value.trim() && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-sage-400 pointer-events-none">
          Tab to complete
        </div>
      )}

      {isOpen && totalOptions > 0 && (
        <ul
          id={listboxIdRef.current}
          ref={listRef}
          className="absolute z-50 bottom-full mb-2 max-h-40 w-full overflow-auto rounded-xl border border-sage-200 bg-white py-1 shadow-elevated"
          role="listbox"
        >
          {filteredOptions.map((option, index) => (
            <li
              key={option.value}
              role="option"
              aria-selected={index === highlightedIndex}
              className={cn(
                "cursor-pointer px-4 py-2.5 text-sm transition-colors",
                index === highlightedIndex
                  ? "bg-harbor-50 text-harbor-700"
                  : "text-harbor-900 hover:bg-sage-50"
              )}
              onMouseEnter={() => setHighlightedIndex(index)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleOptionClick(option.value)}
            >
              <HighlightMatch text={option.label} query={value} />
            </li>
          ))}

          {showCustomOption && (
            <li
              role="option"
              aria-selected={highlightedIndex === filteredOptions.length}
              className={cn(
                "cursor-pointer px-4 py-2.5 text-sm border-t border-sage-100 transition-colors",
                highlightedIndex === filteredOptions.length
                  ? "bg-harbor-50 text-harbor-700"
                  : "text-sage-600 hover:bg-sage-50"
              )}
              onMouseEnter={() => setHighlightedIndex(filteredOptions.length)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => handleOptionClick(value.trim())}
            >
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                {customLabel}: <span className="font-medium text-harbor-700">"{value.trim()}"</span>
              </span>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function HighlightMatch({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;

  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const index = lowerText.indexOf(lowerQuery);

  if (index === -1) return <>{text}</>;

  return (
    <>
      {text.slice(0, index)}
      <span className="font-semibold text-harbor-600 bg-harbor-100 rounded px-0.5">
        {text.slice(index, index + query.length)}
      </span>
      {text.slice(index + query.length)}
    </>
  );
}
