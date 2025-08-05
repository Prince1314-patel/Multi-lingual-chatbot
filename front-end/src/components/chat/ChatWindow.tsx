import { useEffect, useRef, useState } from "react";
import { MessageBubble, Message, VoiceMessage, SystemMessage } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { InputBar } from "./InputBar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Wifi, WifiOff, RefreshCw, AlertCircle } from "lucide-react";
import { useWebSocket, WebSocketMessage, WebSocketError } from "@/hooks/useWebSocket";
import { debugLog } from "@/lib/config";

interface ChatWindowProps {
  roomId: string;
  currentUser: string;
  otherUser: string;
}



export const ChatWindow = ({ roomId, currentUser, otherUser }: ChatWindowProps) => {
  const [messages, setMessages] = useState<(Message | VoiceMessage | SystemMessage)[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isOtherUserTyping, setIsOtherUserTyping] = useState(false);
  const [connectionError, setConnectionError] = useState<WebSocketError | null>(null);
  const [connectedUsers, setConnectedUsers] = useState<Set<string>>(new Set([currentUser]));
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // WebSocket connection with error handling and reconnection
  const {
    isConnected,
    isConnecting,
    error: wsError,
    sendMessage: sendWebSocketMessage,
    sendBinaryMessage: sendWebSocketBinaryMessage,
    reconnect
  } = useWebSocket(roomId, {
    onMessage: handleWebSocketMessage,
    onBinaryMessage: handleWebSocketBinaryMessage,
    onError: handleWebSocketError,
    onConnect: () => {
      debugLog('Connected to chat room:', roomId);
      setConnectionError(null);
    },
    onDisconnect: () => {
      debugLog('Disconnected from chat room:', roomId);
    },
    autoReconnect: true
  });

  // Handle WebSocket messages
  function handleWebSocketMessage(data: WebSocketMessage) {
    debugLog('Received WebSocket message:', data);
    
    if (data.type === 'typing') {
      if (data.from !== currentUser) {
        setIsOtherUserTyping(data.isTyping);
      }
    } else if (data.type === 'message' || data.type === 'text') {
      const message: Message = {
        from: data.from || data.user_id,
        to: data.to || otherUser,
        text: data.text || data.content,
        lang: data.lang || 'en',
        timestamp: data.timestamp,
        status: 'sent'
      };
      
      setMessages(prev => prev.map(msg => 
        msg.timestamp === message.timestamp && msg.from === currentUser 
          ? { ...msg, status: 'sent' as const }
          : msg
      ).concat(message.from !== currentUser ? [message] : []));
    } else if (data.type === 'voice') {
      // Handle voice message from JSON (with hex-encoded audio data)
      if (data.audio_data && data.user_id !== currentUser) {
        try {
          const audioData = new Uint8Array(
            data.audio_data.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
          ).buffer;
          
          const voiceMessage: VoiceMessage = {
            from: data.user_id,
            to: otherUser,
            type: 'voice',
            audioData,
            duration: data.duration,
            timestamp: data.timestamp,
            status: 'sent'
          };
          
          setMessages(prev => [...prev, voiceMessage]);
        } catch (error) {
          console.error('Error processing voice message:', error);
        }
      }
    } else if (data.type === 'user_join') {
      // Handle user join notifications
      const userId = data.user_id;
      if (userId !== currentUser) {
        setConnectedUsers(prev => new Set([...prev, userId]));
        
        const systemMessage: SystemMessage = {
          type: 'system',
          content: `${userId} joined the chat`,
          timestamp: data.timestamp || new Date().toISOString()
        };
        
        setMessages(prev => [...prev, systemMessage]);
      }
    } else if (data.type === 'user_leave') {
      // Handle user leave notifications
      const userId = data.user_id;
      if (userId !== currentUser) {
        setConnectedUsers(prev => {
          const newSet = new Set(prev);
          newSet.delete(userId);
          return newSet;
        });
        
        const systemMessage: SystemMessage = {
          type: 'system',
          content: `${userId} left the chat`,
          timestamp: data.timestamp || new Date().toISOString()
        };
        
        setMessages(prev => [...prev, systemMessage]);
      }
    } else if (data.type === 'error') {
      // Handle backend error messages
      setConnectionError({
        code: data.error_code || 'UNKNOWN_ERROR',
        message: data.message || 'An unknown error occurred',
        timestamp: new Date().toISOString()
      });
    }
  }

  // Handle WebSocket binary messages (voice data)
  function handleWebSocketBinaryMessage(data: ArrayBuffer) {
    debugLog('Received WebSocket binary message:', data.byteLength, 'bytes');
    
    // Create voice message from binary data
    const voiceMessage: VoiceMessage = {
      from: otherUser, // Assume it's from the other user since we don't send binary to ourselves
      to: currentUser,
      type: 'voice',
      audioData: data,
      timestamp: new Date().toISOString(),
      status: 'sent'
    };
    
    setMessages(prev => [...prev, voiceMessage]);
  }

  // Handle WebSocket errors
  function handleWebSocketError(error: WebSocketError) {
    debugLog('WebSocket error:', error);
    setConnectionError(error);
  }

  // Placeholder function for future AI translation
  const translateMessage = async (message: string, targetLang: string): Promise<string> => {
    // TODO: Implement AI translation
    return message;
  };

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  };

  // Cleanup typing timeout on unmount
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOtherUserTyping]);

  const sendMessage = (text: string) => {
    if (!isConnected) {
      debugLog('Cannot send message: WebSocket is not connected');
      setConnectionError({
        code: 'NOT_CONNECTED',
        message: 'Cannot send message: Not connected to server',
        timestamp: new Date().toISOString()
      });
      return;
    }

    const message: Message = {
      from: currentUser,
      to: otherUser,
      text,
      lang: 'en',
      timestamp: new Date().toISOString(),
      status: 'sending'
    };

    // Add message with sending status
    setMessages(prev => [...prev, message]);

    // Send to WebSocket using the backend's expected format
    const success = sendWebSocketMessage({
      type: 'text',
      user_id: currentUser,
      room_id: roomId,
      content: text
    });

    if (success) {
      // Update status to sent (optimistic update)
      setTimeout(() => {
        setMessages(prev => prev.map(msg => 
          msg.timestamp === message.timestamp && msg.from === currentUser
            ? { ...msg, status: 'sent' as const }
            : msg
        ));
      }, 500);
    } else {
      // Update status to failed
      setMessages(prev => prev.map(msg => 
        msg.timestamp === message.timestamp && msg.from === currentUser
          ? { ...msg, status: 'failed' as const }
          : msg
      ));
    }
  };

  const sendVoiceMessage = async (audioBlob: Blob) => {
    if (!isConnected) {
      debugLog('Cannot send voice message: WebSocket is not connected');
      setConnectionError({
        code: 'NOT_CONNECTED',
        message: 'Cannot send voice message: Not connected to server',
        timestamp: new Date().toISOString()
      });
      return;
    }

    try {
      // Convert blob to ArrayBuffer
      const arrayBuffer = await audioBlob.arrayBuffer();
      
      // Create voice message for UI
      const voiceMessage: VoiceMessage = {
        from: currentUser,
        to: otherUser,
        type: 'voice',
        audioData: arrayBuffer,
        timestamp: new Date().toISOString(),
        status: 'sending'
      };

      // Add message with sending status
      setMessages(prev => [...prev, voiceMessage]);

      // Send binary data via WebSocket
      const success = sendWebSocketBinaryMessage && sendWebSocketBinaryMessage(arrayBuffer);

      if (success) {
        // Update status to sent (optimistic update)
        setTimeout(() => {
          setMessages(prev => prev.map(msg => 
            msg.timestamp === voiceMessage.timestamp && msg.from === currentUser
              ? { ...msg, status: 'sent' as const }
              : msg
          ));
        }, 500);
      } else {
        // Update status to failed
        setMessages(prev => prev.map(msg => 
          msg.timestamp === voiceMessage.timestamp && msg.from === currentUser
            ? { ...msg, status: 'failed' as const }
            : msg
        ));
      }
    } catch (error) {
      console.error('Error sending voice message:', error);
      setConnectionError({
        code: 'VOICE_SEND_FAILED',
        message: 'Failed to send voice message',
        timestamp: new Date().toISOString()
      });
    }
  };

  const handleTyping = (typing: boolean) => {
    if (!isConnected) return;

    setIsTyping(typing);
    
    sendWebSocketMessage({
      type: 'typing',
      from: currentUser,
      to: otherUser,
      isTyping: typing
    });

    // Clear typing after 3 seconds of inactivity
    if (typing) {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      typingTimeoutRef.current = setTimeout(() => {
        handleTyping(false);
      }, 3000);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-chat-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-chat-sidebar border-b">
        <div>
          <h1 className="text-lg font-semibold">{otherUser}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Room: {roomId}</span>
            <span>•</span>
            <span>{connectedUsers.size} user{connectedUsers.size !== 1 ? 's' : ''} online</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {connectionError && (
            <Button
              variant="outline"
              size="sm"
              onClick={reconnect}
              className="gap-1 text-xs"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          )}
          <Badge 
            variant={isConnected ? "default" : isConnecting ? "secondary" : "destructive"} 
            className="gap-1"
          >
            {isConnected ? (
              <Wifi className="h-3 w-3" />
            ) : isConnecting ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            {isConnected ? "Connected" : isConnecting ? "Connecting..." : "Disconnected"}
          </Badge>
        </div>
      </div>

      {/* Connection Error Banner */}
      {connectionError && (
        <div className="bg-destructive/10 border-b border-destructive/20 p-3">
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span>Connection Error: {connectionError.message}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={reconnect}
              className="ml-auto h-6 px-2 text-xs"
            >
              Reconnect
            </Button>
          </div>
        </div>
      )}

      {/* Messages */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        <div className="space-y-1">
          {messages.map((message, index) => {
            const showTimestamp = index === 0 || 
              new Date(messages[index - 1]?.timestamp).getTime() < new Date(message.timestamp).getTime() - 300000; // 5 minutes
            
            const messageKey = 'type' in message && message.type === 'system' 
              ? `system-${message.timestamp}` 
              : `${message.timestamp}-${(message as Message).from}`;
            
            const isCurrentUser = 'from' in message ? message.from === currentUser : false;
            
            return (
              <MessageBubble
                key={messageKey}
                message={message}
                isCurrentUser={isCurrentUser}
                showTimestamp={showTimestamp}
              />
            );
          })}
          
          <TypingIndicator 
            userName={otherUser} 
            isVisible={isOtherUserTyping}
          />
        </div>
      </ScrollArea>

      {/* Input */}
      <InputBar
        onSendMessage={sendMessage}
        onSendVoiceMessage={sendVoiceMessage}
        onTyping={handleTyping}
        disabled={!isConnected}
      />
    </div>
  );
};