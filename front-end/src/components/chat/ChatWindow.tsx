import { useEffect, useRef, useState } from "react";
import { MessageBubble, Message } from "./MessageBubble";
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
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isOtherUserTyping, setIsOtherUserTyping] = useState(false);
  const [connectionError, setConnectionError] = useState<WebSocketError | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // WebSocket connection with error handling and reconnection
  const {
    isConnected,
    isConnecting,
    error: wsError,
    sendMessage: sendWebSocketMessage,
    reconnect
  } = useWebSocket(roomId, {
    onMessage: handleWebSocketMessage,
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
    } else if (data.type === 'message') {
      const message: Message = {
        from: data.from,
        to: data.to,
        text: data.text,
        lang: data.lang || 'en',
        timestamp: data.timestamp,
        status: 'sent'
      };
      
      setMessages(prev => prev.map(msg => 
        msg.timestamp === message.timestamp && msg.from === currentUser 
          ? { ...msg, status: 'sent' as const }
          : msg
      ).concat(message.from !== currentUser ? [message] : []));
    } else if (data.type === 'error') {
      // Handle backend error messages
      setConnectionError({
        code: data.error_code || 'UNKNOWN_ERROR',
        message: data.message || 'An unknown error occurred',
        timestamp: new Date().toISOString()
      });
    }
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

    // Send to WebSocket
    const success = sendWebSocketMessage({
      type: 'message',
      ...message
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
          <p className="text-sm text-muted-foreground">Room: {roomId}</p>
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
            
            return (
              <MessageBubble
                key={`${message.timestamp}-${message.from}`}
                message={message}
                isCurrentUser={message.from === currentUser}
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
        onTyping={handleTyping}
        disabled={!isConnected}
      />
    </div>
  );
};