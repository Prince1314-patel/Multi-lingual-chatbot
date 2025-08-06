import { Check, CheckCheck, Clock, Play, Pause, Volume2, AlertCircle, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState, useRef, useEffect } from "react";
import { debugLog } from "@/lib/config";

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
    // Handle invalid values
    if (!isFinite(seconds) || isNaN(seconds) || seconds < 0) {
      return '0:00';
    }

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
      const currentAudioTime = audioRef.current.currentTime;
      // Only update if it's a valid number
      if (isFinite(currentAudioTime) && !isNaN(currentAudioTime) && currentAudioTime >= 0) {
        setCurrentTime(currentAudioTime);
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      const audioDuration = audioRef.current.duration;
      debugLog('Audio metadata loaded:', {
        duration: audioDuration,
        readyState: audioRef.current.readyState,
        networkState: audioRef.current.networkState,
        src: audioRef.current.src?.substring(0, 50) + '...'
      });

      // Clear any existing timeout since we got metadata
      if (audioRef.current.dataset.timeoutId) {
        clearTimeout(parseInt(audioRef.current.dataset.timeoutId));
        delete audioRef.current.dataset.timeoutId;
      }

      // Only set duration if it's a valid number
      if (isFinite(audioDuration) && !isNaN(audioDuration) && audioDuration > 0) {
        setDuration(audioDuration);
        debugLog('Valid audio duration set:', audioDuration);
      } else {
        debugLog('Invalid audio duration detected:', audioDuration, 'Will use fallback estimation');
        // Don't set to 0 immediately, let the timeout handle it
      }
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleError = (event?: Event) => {
    const errorDetails = {
      error: audioRef.current?.error,
      errorCode: audioRef.current?.error?.code,
      errorMessage: audioRef.current?.error?.message,
      networkState: audioRef.current?.networkState,
      readyState: audioRef.current?.readyState,
      src: audioRef.current?.src?.substring(0, 50) + '...',
      currentFormat: audioRef.current?.dataset?.audioFormat
    };

    debugLog('Audio error occurred:', errorDetails);

    // If it's a decode error, try to recreate with a different format
    if (audioRef.current?.error?.code === MediaError.MEDIA_ERR_DECODE && 
        'type' in message && message.type === 'voice' && message.audioData) {
      debugLog('Decode error detected, trying alternative format...');
      tryAlternativeFormat();
      return;
    }

    // Try to provide more specific error messages
    let errorMessage = 'Failed to load audio';
    if (audioRef.current?.error) {
      switch (audioRef.current.error.code) {
        case MediaError.MEDIA_ERR_ABORTED:
          errorMessage = 'Audio playback was aborted';
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          errorMessage = 'Network error while loading audio';
          break;
        case MediaError.MEDIA_ERR_DECODE:
          errorMessage = 'Audio format not compatible with this browser';
          break;
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMessage = 'Audio format not supported';
          break;
        default:
          errorMessage = `Audio error: ${audioRef.current.error.message || 'Unknown error'}`;
      }
    }

    setAudioError(errorMessage);
    setIsPlaying(false);
  };

  // Try alternative audio format when decode fails
  const tryAlternativeFormat = () => {
    if (!('type' in message && message.type === 'voice' && message.audioData)) return;
    
    const alternativeFormats = [
      'audio/wav',
      'audio/ogg',
      'audio/mp4',
      'audio/mpeg',
      'audio/webm'
    ];
    
    const currentFormat = audioRef.current?.dataset?.audioFormat || '';
    const nextFormat = alternativeFormats.find(format => format !== currentFormat);
    
    if (nextFormat) {
      debugLog('Trying alternative format:', nextFormat);
      try {
        const alternativeBlob = new Blob([message.audioData], { type: nextFormat });
        const alternativeUrl = URL.createObjectURL(alternativeBlob);
        
        if (audioRef.current) {
          // Clean up old URL
          if (audioRef.current.src) {
            URL.revokeObjectURL(audioRef.current.src);
          }
          
          audioRef.current.src = alternativeUrl;
          audioRef.current.dataset.audioFormat = nextFormat;
          setAudioError(null); // Clear error to try again
        }
      } catch (error) {
        debugLog('Alternative format failed:', error);
        setAudioError('Audio format not compatible with this browser');
      }
    } else {
      setAudioError('No compatible audio format found');
    }
  };

  // Create audio URL for voice messages
  useEffect(() => {
    if ('type' in message && message.type === 'voice' && message.audioData) {
      try {
        // Try different audio MIME types for better browser compatibility
        const audioFormats = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/ogg;codecs=opus',
          'audio/ogg',
          'audio/wav',
          'audio/mp4',
          'audio/mpeg'
        ];

        let blob: Blob;
        let workingFormat = 'audio/webm'; // fallback

        // Try to find a format that works
        for (const format of audioFormats) {
          try {
            blob = new Blob([message.audioData], { type: format });
            workingFormat = format;
            break;
          } catch (error) {
            debugLog('Failed to create blob with format:', format, error);
          }
        }

        // Fallback if all formats fail
        if (!blob!) {
          blob = new Blob([message.audioData], { type: 'audio/webm' });
        }

        debugLog('Using audio format for playback:', workingFormat, 'Size:', blob.size);

        const audioUrl = URL.createObjectURL(blob);

        if (audioRef.current) {
          audioRef.current.src = audioUrl;
          // Reset audio state
          setCurrentTime(0);
          setDuration(0);
          setIsPlaying(false);
          setAudioError(null);

          // Set a timeout to handle cases where metadata never loads properly
          const metadataTimeout = setTimeout(() => {
            if (audioRef.current && (!isFinite(audioRef.current.duration) || audioRef.current.duration === 0)) {
              debugLog('Audio metadata timeout, estimating duration from file size');
              // Rough estimation: assume 32kbps bitrate for voice
              const estimatedDuration = Math.max(1, Math.min(60, message.audioData.byteLength / 4000));
              setDuration(estimatedDuration);
            }
          }, 2000);

          // Store timeout reference for cleanup
          const currentAudio = audioRef.current;
          currentAudio.dataset.timeoutId = metadataTimeout.toString();
          currentAudio.dataset.audioFormat = workingFormat;
        }

        return () => {
          URL.revokeObjectURL(audioUrl);
          // Clear timeout if it exists
          if (audioRef.current?.dataset.timeoutId) {
            clearTimeout(parseInt(audioRef.current.dataset.timeoutId));
          }
        };
      } catch (error) {
        console.error('Error creating audio URL:', error);
        debugLog('Audio data details:', {
          byteLength: message.audioData.byteLength,
          constructor: message.audioData.constructor.name
        });
        setAudioError('Failed to load audio');
      }
    }
  }, [message]);

  // Handle when audio can play through (better for getting duration)
  const handleCanPlayThrough = () => {
    if (audioRef.current) {
      const audioDuration = audioRef.current.duration;
      debugLog('Audio can play through:', {
        duration: audioDuration,
        readyState: audioRef.current.readyState
      });

      if (isFinite(audioDuration) && !isNaN(audioDuration) && audioDuration > 0) {
        setDuration(audioDuration);
        // Clear timeout since we got valid duration
        if (audioRef.current.dataset.timeoutId) {
          clearTimeout(parseInt(audioRef.current.dataset.timeoutId));
          delete audioRef.current.dataset.timeoutId;
        }
      }
    }
  };

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
    audio.addEventListener('canplaythrough', handleCanPlayThrough);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('canplaythrough', handleCanPlayThrough);
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
                    {formatDuration(currentTime)} / {formatDuration(duration)}
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