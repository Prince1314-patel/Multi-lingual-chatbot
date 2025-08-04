import { cn } from "@/lib/utils";

interface TypingIndicatorProps {
  userName: string;
  isVisible: boolean;
}

export const TypingIndicator = ({ userName, isVisible }: TypingIndicatorProps) => {
  if (!isVisible) return null;

  return (
    <div className="flex items-center gap-2 mb-4 mr-auto max-w-[70%]">
      <div className="bg-message-other border rounded-2xl rounded-bl-sm px-4 py-2">
        <div className="flex items-center gap-1">
          <span className="text-sm text-message-other-foreground">{userName} is typing</span>
          <div className="flex gap-0.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className={cn(
                  "w-1 h-1 bg-typing rounded-full animate-bounce",
                  `animation-delay-${i * 150}`
                )}
                style={{
                  animationDelay: `${i * 0.15}s`,
                  animationDuration: '1.4s'
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};