import { cn } from "../../lib/utils";

function formatDisplayContent(content: string): string {
  let trimmed = content.trim();
  
  // Handle correction message format - extract just the value for display
  // Matches: "[Correction] My X should be: VALUE" or "My X should be: VALUE"
  const correctionMatch = trimmed.match(/(?:\[Correction\])?\s*My\s+.+?\s+should\s+be:?\s*(.+)$/i);
  if (correctionMatch) {
    trimmed = correctionMatch[1].trim();
  }
  
  // Already formatted with $ sign - ensure commas
  if (trimmed.startsWith("$")) {
    const numPart = trimmed.slice(1).replace(/,/g, "");
    const num = parseFloat(numPart);
    if (!isNaN(num) && isFinite(num)) {
      return "$" + num.toLocaleString("en-US", { maximumFractionDigits: 0 });
    }
    return trimmed;
  }
  
  // Pure number (possibly large amount like retirement balance)
  const numericMatch = trimmed.match(/^[\d,]+$/);
  if (numericMatch) {
    const num = parseInt(trimmed.replace(/,/g, ""), 10);
    // Skip formatting for years (4-digit numbers between 1900-2100)
    const isLikelyYear = num >= 1900 && num <= 2100 && trimmed.length === 4;
    if (!isNaN(num) && num >= 1000 && !isLikelyYear) {
      return "$" + num.toLocaleString("en-US");
    }
  }
  
  // Percentage value
  if (trimmed.match(/^\d+%$/)) {
    return trimmed;
  }
  
  return trimmed;
}

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  messageIndex?: number;
  onEdit?: (index: number, content: string) => void;
  isEditing?: boolean;
  updatedByIndex?: number;
  isUpdate?: boolean;
  updateLabel?: string;
  fieldLabel?: string;
  onScrollToMessage?: (index: number) => void;
}

function formatMessageTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  
  const timeStr = date.toLocaleTimeString([], { 
    hour: "numeric", 
    minute: "2-digit",
    hour12: true 
  });
  
  if (isToday) {
    return timeStr;
  }
  
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();
  
  if (isYesterday) {
    return `Yesterday ${timeStr}`;
  }
  
  const dateStr = date.toLocaleDateString([], { 
    month: "short", 
    day: "numeric" 
  });
  return `${dateStr}, ${timeStr}`;
}

export default function ChatMessage({ 
  role, 
  content, 
  timestamp,
  messageIndex,
  onEdit,
  isEditing,
  updatedByIndex,
  isUpdate,
  updateLabel,
  fieldLabel,
  onScrollToMessage,
}: ChatMessageProps) {
  const canReply = role === "user" && onEdit && messageIndex !== undefined && !updatedByIndex;
  const hasBeenUpdated = updatedByIndex !== undefined;
  
  // Determine which label to show: updateLabel for updates, fieldLabel for regular user messages
  const displayLabel = isUpdate ? updateLabel : (role === "user" ? fieldLabel : undefined);

  return (
    <div
      className={cn(
        "flex w-full group",
        role === "user" ? "justify-end" : "justify-start",
      )}
      data-message-index={messageIndex}
    >
      <div className={cn(
        "flex flex-col max-w-[80%]",
        role === "user" ? "items-end" : "items-start"
      )}>
        {/* Field label for user messages */}
        {displayLabel && displayLabel !== "answer" && (
          <span className="mb-1 text-[10px] font-medium text-sage-500 uppercase tracking-wide">
            {displayLabel}
          </span>
        )}
        <div className="relative flex items-end gap-2">
          <div
            className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-soft",
              role === "user"
                ? "bg-gradient-to-br from-harbor-500 to-harbor-600 text-white"
                : "bg-white text-harbor-800 border border-sage-200/60",
              isEditing && "ring-2 ring-harbor-400 ring-offset-2",
              hasBeenUpdated && role === "user" && "opacity-60"
            )}
          >
            {content.split("\n").map((line, i) => {
              const displayLine = role === "user" ? formatDisplayContent(line) : line;
              return (
                <p key={i} className={i > 0 ? "mt-2" : ""}>
                  {displayLine}
                </p>
              );
            })}
          </div>
          {/* Reply icon - to the right of the bubble */}
          {canReply && (
            <button
              onClick={() => onEdit(messageIndex, content)}
              className={cn(
                "p-1.5 rounded-lg text-sage-400 transition-all duration-200",
                "opacity-0 group-hover:opacity-100",
                "hover:bg-sage-100 hover:text-harbor-600",
                "focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-harbor-300",
                isEditing && "opacity-100 text-harbor-500 bg-harbor-50"
              )}
              title="Update this answer"
              aria-label="Update this answer"
            >
              {/* Reply icon */}
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
              </svg>
            </button>
          )}
          {/* Link icon for updated messages */}
          {hasBeenUpdated && onScrollToMessage && (
            <button
              onClick={() => onScrollToMessage(updatedByIndex)}
              className={cn(
                "p-1.5 rounded-lg text-sage-400 transition-all duration-200",
                "hover:bg-sage-100 hover:text-harbor-600",
                "focus:outline-none focus:ring-2 focus:ring-harbor-300"
              )}
              title="See updated value"
              aria-label="See updated value"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </button>
          )}
        </div>
        {/* Updated indicator */}
        {hasBeenUpdated && (
          <span className="mt-1 text-[10px] text-amber-600 font-medium flex items-center gap-1">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Updated
          </span>
        )}
        {timestamp && !hasBeenUpdated && (
          <span className={cn(
            "mt-1 text-[10px] text-sage-400 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
            role === "user" ? "mr-1" : "ml-1"
          )}>
            {formatMessageTime(timestamp)}
          </span>
        )}
      </div>
    </div>
  );
}
