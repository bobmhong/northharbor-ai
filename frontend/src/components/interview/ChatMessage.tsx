import { cn } from "../../lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
  messageIndex?: number;
  onEdit?: (index: number, content: string) => void;
  isEditing?: boolean;
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
}: ChatMessageProps) {
  const canEdit = role === "user" && onEdit && messageIndex !== undefined;

  return (
    <div
      className={cn(
        "flex w-full group",
        role === "user" ? "justify-end" : "justify-start",
      )}
    >
      <div className={cn(
        "flex flex-col max-w-[80%]",
        role === "user" ? "items-end" : "items-start"
      )}>
        <div className="relative flex items-end gap-2">
          {canEdit && (
            <button
              onClick={() => onEdit(messageIndex, content)}
              className={cn(
                "p-1.5 rounded-lg text-sage-400 transition-all duration-200",
                "opacity-0 group-hover:opacity-100",
                "hover:bg-sage-100 hover:text-harbor-600",
                "focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-harbor-300",
                isEditing && "opacity-100 text-harbor-500 bg-harbor-50"
              )}
              title="Edit this answer"
              aria-label="Edit this answer"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
          )}
          <div
            className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-soft",
              role === "user"
                ? "bg-gradient-to-br from-harbor-500 to-harbor-600 text-white"
                : "bg-white text-harbor-800 border border-sage-200/60",
              isEditing && "ring-2 ring-harbor-400 ring-offset-2"
            )}
          >
            {content.split("\n").map((line, i) => (
              <p key={i} className={i > 0 ? "mt-2" : ""}>
                {line}
              </p>
            ))}
          </div>
        </div>
        {timestamp && (
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
