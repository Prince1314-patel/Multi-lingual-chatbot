import { useState, KeyboardEvent, useRef, useCallback } from "react";
import { Send, Mic, MicOff, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface InputBarProps {
  onSendMessage: (message: string) => void;
  onSendVoiceMessage: (audioBlob: Blob) => void;
  onTyping: (isTyping: boolean) => void;
  disabled?: boolean;
}

export const InputBar = ({ onSendMessage, onSendVoiceMessage, onTyping, disabled = false }: InputBarProps) => {
  const [message, setMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage("");
      setIsTyping(false);
      onTyping(false);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (value: string) => {
    setMessage(value);
    
    // Handle typing indicator
    if (value.trim() && !isTyping) {
      setIsTyping(true);
      onTyping(true);
    } else if (!value.trim() && isTyping) {
      setIsTyping(false);
      onTyping(false);
    }
  };

  const startRecording = useCallback(async () => {
    try {
      setRecordingError(null);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      // Create MediaRecorder with webm format (supported by backend)
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm;codecs=opus' });
        
        // Send voice message if we have audio data
        if (audioBlob.size > 0) {
          onSendVoiceMessage(audioBlob);
        }
        
        // Clean up
        stream.getTracks().forEach(track => track.stop());
        audioChunksRef.current = [];
      };
      
      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        setRecordingError('Recording failed. Please try again.');
        setIsRecording(false);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      
    } catch (error) {
      console.error('Error starting recording:', error);
      let errorMessage = 'Failed to start recording.';
      
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Microphone access denied. Please allow microphone access and try again.';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No microphone found. Please connect a microphone and try again.';
        } else if (error.name === 'NotSupportedError') {
          errorMessage = 'Voice recording is not supported in this browser.';
        }
      } else if (error instanceof DOMException) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'Microphone access denied. Please allow microphone access and try again.';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'No microphone found. Please connect a microphone and try again.';
        } else if (error.name === 'NotSupportedError') {
          errorMessage = 'Voice recording is not supported in this browser.';
        }
      }
      
      setRecordingError(errorMessage);
      setIsRecording(false);
    }
  }, [onSendVoiceMessage]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  return (
    <div className="flex flex-col gap-2 p-4 bg-background border-t">
      {recordingError && (
        <div className="text-sm text-destructive bg-destructive/10 p-2 rounded">
          {recordingError}
        </div>
      )}
      
      <div className="flex items-center gap-2">
        <Input
          value={message}
          onChange={(e) => handleInputChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={isRecording ? "Recording..." : "Type a message..."}
          disabled={disabled || isRecording}
          className="flex-1"
        />
        
        {/* Voice recording button */}
        <Button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled}
          size="icon"
          variant={isRecording ? "destructive" : "outline"}
          className="shrink-0"
          title={isRecording ? "Stop recording" : "Start voice recording"}
        >
          {isRecording ? (
            <Square className="h-4 w-4" />
          ) : (
            <Mic className="h-4 w-4" />
          )}
        </Button>
        
        {/* Send text message button */}
        <Button
          onClick={handleSend}
          disabled={!message.trim() || disabled || isRecording}
          size="icon"
          className="shrink-0"
          title="Send message"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      
      {isRecording && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
          Recording... Click the stop button when finished
        </div>
      )}
    </div>
  );
};