import { Check, CheckCheck, Clock, Play, Pause, Volume2, AlertCircle, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState, useRef, useEffect } from "react";

export interface Message {
  id?: string;
  from: string;
  to: string;
  text?: string;
  lang: string;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "failed" | "read";
}

export interface VoiceMessage {
  id?: string;
  from: string;
  to: string;
  type: 'voice';
  audioData: ArrayBuffer;
  duration?: number;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "failed" | "read";
}

export interface SystemMessage {
  type: 'system';
  content: string;
  timestamp: string;
}

interface MessageBubbleProps {
  message: Message | VoiceMessage | SystemMessage;
  isCurrentUser?: boolean;
  showTimestamp?: boolean;
  onRetry?: (message: Message | VoiceMessage) => void;
}

export const MessageBubble = ({ message, isCurrentUser = false, showTimestamp = false, onRetry }: MessageBubbleProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusIcon = () => {
    if ('status' in message) {
      switch (message.status) {
        case "sending":
          return <Clock className="h-3 w-3 text-message-sending" data-testid="status-icon" />;
        case "sent":
          return <Check className="h-3 w-3 text-message-sent" data-testid="status-icon" />;
        case "delivered":
        case "read":
          return <CheckCheck className="h-3 w-3 text-message-sent" data-testid="status-icon" />;
        case "failed":
          return (
            <div className="flex items-center gap-1" data-testid="status-icon">
              <AlertCircle className="h-3 w-3 text-destructive" />
              {onRetry && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-background/20"
                  onClick={() => onRetry(message as Message | VoiceMessage)}
                  data-testid="retry-button"
                >
                  <RotateCcw className="h-2 w-2" />
                </Button>
              )}
            </div>
          );
        default:
          return null;
      }
    }
    return null;
  };

  // Voice message playback handlers
  const handlePlayPause = async () => {
    if (!audioRef.current) return;

    try {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        await audioRef.current.play();
      }
    } catch (error) {
      console.error('Error playing audio:', error);
      setAudioError('Failed to play audio');
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleError = () => {
    setAudioError('Failed to load audio');
    setIsPlaying(false);
  };

  // Create audio URL for voice messages
  useEffect(() => {
    if ('type' in message && message.type === 'voice' && message.audioData) {
      try {
        const blob = new Blob([message.audioData], { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(blob);
        
        if (audioRef.current) {
          audioRef.current.src = audioUrl;
        }

        return () => {
          URL.revokeObjectURL(audioUrl);
        };
      } catch (error) {
        console.error('Error creating audio URL:', error);
        setAudioError('Failed to load audio');
      }
    }
  }, [message]);

  // Audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, []);

  // Handle system messages
  if ('type' in message && message.type === 'system') {
    return (
      <div className="flex justify-center mb-4">
        <div className="bg-muted/50 rounded-full px-3 py-1 text-xs text-muted-foreground">
          {message.content}
          {showTimestamp && (
            <span className="ml-2 opacity-70">
              {formatTime(message.timestamp)}
            </span>
          )}
        </div>
      </div>
    );
  }

  // Handle voice messages
  if ('type' in message && message.type === 'voice') {
    const voiceMessage = message as VoiceMessage;
    
    return (
      <div className={cn(
        "flex flex-col max-w-[70%] mb-4",
        isCurrentUser ? "ml-auto items-end" : "mr-auto items-start"
      )}>
        <div className={cn(
          "rounded-2xl px-4 py-3 min-w-[200px]",
          isCurrentUser 
            ? "bg-message-user text-message-user-foreground rounded-br-sm" 
            : "bg-message-other text-message-other-foreground border rounded-bl-sm"
        )}>
          {audioError ? (
            <div className="flex items-center gap-2 text-destructive">
              <Volume2 className="h-4 w-4" />
              <span className="text-sm">{audioError}</span>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Button
                onClick={handlePlayPause}
                size="sm"
                variant="ghost"
                className="h-8 w-8 p-0 hover:bg-background/20"
              >
                {isPlaying ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
              
              <div className="flex-1 flex items-center gap-2">
                <Volume2 className="h-4 w-4" />
                <div className="flex-1">
                  <div className="w-full bg-background/20 rounded-full h-1">
                    <div 
                      className="bg-current h-1 rounded-full transition-all duration-100"
                      style={{ 
                        width: duration > 0 ? `${(currentTime / duration) * 100}%` : '0%' 
                      }}
                    />
                  </div>
                  <div className="text-xs opacity-70 mt-1">
                    {duration > 0 ? formatDuration(currentTime) : '0:00'} / {duration > 0 ? formatDuration(duration) : '0:00'}
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <audio
            ref={audioRef}
            preload="metadata"
            style={{ display: 'none' }}
          />
        </div>
        
        <div className={cn(
          "flex items-center gap-1 mt-1 px-1",
          isCurrentUser ? "flex-row-reverse" : "flex-row"
        )}>
          {showTimestamp && (
            <span className="text-xs text-message-timestamp">
              {formatTime(voiceMessage.timestamp)}
            </span>
          )}
          {isCurrentUser && getStatusIcon()}
        </div>
      </div>
    );
  }

  // Handle regular text messages
  const regularMessage = message as Message;
  
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
        <p className="text-sm">{regularMessage.text}</p>
      </div>
      
      <div className={cn(
        "flex items-center gap-1 mt-1 px-1",
        isCurrentUser ? "flex-row-reverse" : "flex-row"
      )}>
        {showTimestamp && (
          <span className="text-xs text-message-timestamp">
            {formatTime(regularMessage.timestamp)}
          </span>
        )}
        {isCurrentUser && getStatusIcon()}
      </div>
    </div>
  );
};