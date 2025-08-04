import { Check, CheckCheck, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Message {
  from: string;
  to: string;
  text: string;
  lang: string;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "read";
}

interface MessageBubbleProps {
  message: Message;
  isCurrentUser: boolean;
  showTimestamp?: boolean;
}

export const MessageBubble = ({ message, isCurrentUser, showTimestamp = false }: MessageBubbleProps) => {
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusIcon = () => {
    switch (message.status) {
      case "sending":
        return <Clock className="h-3 w-3 text-message-sending" />;
      case "sent":
        return <Check className="h-3 w-3 text-message-sent" />;
      case "delivered":
      case "read":
        return <CheckCheck className="h-3 w-3 text-message-sent" />;
      default:
        return null;
    }
  };

  return (
    <div className={cn(
      "flex flex-col max-w-[70%] mb-4",
      isCurrentUser ? "ml-auto items-end" : "mr-auto items-start"
    )}>
      <div className={cn(
        "rounded-2xl px-4 py-2 break-words",
        isCurrentUser 
          ? "bg-message-user text-message-user-foreground rounded-br-sm" 
          : "bg-message-other text-message-other-foreground border rounded-bl-sm"
      )}>
        <p className="text-sm">{message.text}</p>
      </div>
      
      <div className={cn(
        "flex items-center gap-1 mt-1 px-1",
        isCurrentUser ? "flex-row-reverse" : "flex-row"
      )}>
        {showTimestamp && (
          <span className="text-xs text-message-timestamp">
            {formatTime(message.timestamp)}
          </span>
        )}
        {isCurrentUser && getStatusIcon()}
      </div>
    </div>
  );
};