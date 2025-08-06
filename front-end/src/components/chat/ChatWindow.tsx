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

// Helper function to normalize timestamps to consistent format
const normalizeTimestamp = (timestamp: string | undefined): string => {
  if (!timestamp) return new Date().toISOString();
  
  // Parse the timestamp and convert to local ISO string
  const date = new Date(timestamp);
  return date.toISOString();
};

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
  const [connectedUsers, setConnectedUsers] = useState<Set<string>>(new Set());
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  // WebSocket connection with error handling and reconnection
  const {
    isConnected,
    isConnecting,
    sendMessage: sendWebSocketMessage,
    sendBinaryMessage: sendWebSocketBinaryMessage,
    reconnect
  } = useWebSocket(roomId, {
    onMessage: handleWebSocketMessage,
    onBinaryMessage: handleWebSocketBinaryMessage,
    onError: handleWebSocketError,
    onConnect: () => {
      debugLog('ChatWindow: Connected to chat room:', roomId);
      setConnectionError(null);
    },
    onDisconnect: () => {
      debugLog('ChatWindow: Disconnected from chat room:', roomId);
    },
    autoReconnect: true
  });

  // Handle WebSocket messages
  function handleWebSocketMessage(data: WebSocketMessage) {
    debugLog('Received WebSocket message:', data);

    if (data.type === 'connection_established') {
      // Handle welcome message with connected users list
      if (data.room_info && typeof data.room_info === 'object' && data.room_info !== null &&
        'connected_users' in data.room_info && Array.isArray(data.room_info.connected_users)) {
        setConnectedUsers(new Set(data.room_info.connected_users as string[]));
        debugLog('Connected users updated from welcome message:', data.room_info.connected_users);
      }
    } else if (data.type === 'message_confirmation') {
      // Handle delivery confirmation
      const messageId = typeof data.message_id === 'string' ? data.message_id : '';
      const status = data.status === 'delivered' ? 'delivered' : 'failed';

      setMessages(prev => prev.map(msg => {
        if ('id' in msg && 'from' in msg && msg.id === messageId && msg.from === currentUser) {
          return { ...msg, status };
        }
        return msg;
      }));
    } else if (data.type === 'typing') {
      if (typeof data.user_id === 'string' && data.user_id !== currentUser) {
        setIsOtherUserTyping(Boolean(data.isTyping));
      }
    } else if (data.type === 'message' || data.type === 'text') {
      const message: Message = {
        id: typeof data.id === 'string' ? data.id : '',
        from: (typeof data.from === 'string' ? data.from : typeof data.user_id === 'string' ? data.user_id : ''),
        to: (typeof data.to === 'string' ? data.to : otherUser),
        text: (typeof data.text === 'string' ? data.text : typeof data.content === 'string' ? data.content : ''),
        lang: (typeof data.lang === 'string' ? data.lang : 'en'),
        timestamp: (typeof data.timestamp === 'string' ? new Date(data.timestamp).toISOString() : new Date().toISOString()),
        status: 'sent'
      };

      // If this is from another user, add it to messages
      if (message.from !== currentUser) {
        setMessages(prev => [...prev, message]);
      } else {
        // If this is our own message echoed back, update the existing message with server timestamp
        setMessages(prev => prev.map(msg =>
          'id' in msg && 'from' in msg && msg.id === message.id && msg.from === currentUser
            ? { ...msg, timestamp: message.timestamp, status: 'sent' as const }
            : msg
        ));
      }
    } else if (data.type === 'voice') {
      // Handle voice message from JSON (with hex-encoded audio data)
      if (typeof data.audio_data === 'string' && typeof data.user_id === 'string' && data.user_id !== currentUser) {
        try {
          const audioData = new Uint8Array(
            data.audio_data.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
          ).buffer;

          // Create voice message with conditional status
          const baseVoiceMessage = {
            id: typeof data.id === 'string' ? data.id : '',
            from: data.user_id,
            to: otherUser,
            type: 'voice' as const,
            audioData,
            duration: typeof data.duration === 'number' ? data.duration : undefined,
            timestamp: typeof data.timestamp === 'string' ? data.timestamp : new Date().toISOString()
          };

          // If this is from another user, add it without status
          if (baseVoiceMessage.from !== currentUser) {
            setMessages(prev => [...prev, baseVoiceMessage]);
          } else {
            // If this is our own message echoed back, include status and update existing message
            const voiceMessage: VoiceMessage = { ...baseVoiceMessage, status: 'sent' as const };
            setMessages(prev => prev.map(msg =>
              'id' in msg && 'from' in msg && msg.id === voiceMessage.id && msg.from === currentUser
                ? { ...msg, timestamp: voiceMessage.timestamp, status: 'sent' as const }
                : msg
            ));
          }
        } catch (error) {
          console.error('Error processing voice message:', error);
        }
      }
    } else if (data.type === 'user_join') {
      // Handle user join notifications
      const userId = typeof data.user_id === 'string' ? data.user_id : 'Unknown User';
      setConnectedUsers(prev => new Set([...prev, userId]));

      const systemMessage: SystemMessage = {
        type: 'system',
        content: `${userId} joined the chat`,
        timestamp: typeof data.timestamp === 'string' ? data.timestamp : new Date().toISOString()
      };

      setMessages(prev => [...prev, systemMessage]);
    } else if (data.type === 'user_leave') {
      // Handle user leave notifications
      const userId = typeof data.user_id === 'string' ? data.user_id : 'Unknown User';
      setConnectedUsers(prev => {
        const newSet = new Set(prev);
        newSet.delete(userId);
        return newSet;
      });

      const systemMessage: SystemMessage = {
        type: 'system',
        content: `${userId} left the chat`,
        timestamp: typeof data.timestamp === 'string' ? data.timestamp : new Date().toISOString()
      };

      setMessages(prev => [...prev, systemMessage]);
    } else if (data.type === 'error') {
      // Handle backend error messages
      setConnectionError({
        code: typeof data.error_code === 'string' ? data.error_code : 'UNKNOWN_ERROR',
        message: typeof data.message === 'string' ? data.message : 'An unknown error occurred',
        timestamp: new Date().toISOString()
      });
    }
  }

  // Handle WebSocket binary messages (voice data)
  function handleWebSocketBinaryMessage(data: ArrayBuffer) {
    debugLog('Received WebSocket binary message:', data.byteLength, 'bytes');

    // Create voice message from binary data
    const voiceMessage: VoiceMessage = {
      id: generateMessageId(),
      from: otherUser, // Assume it's from the other user since we don't send binary to ourselves
      to: currentUser,
      type: 'voice',
      audioData: data,
      duration: undefined, // Will be set when audio loads
      timestamp: new Date().toISOString()
      // No status field for received messages
    };

    setMessages(prev => [...prev, voiceMessage]);
  }

  // Handle WebSocket errors
  function handleWebSocketError(error: WebSocketError) {
    debugLog('WebSocket error:', error);
    setConnectionError(error);
  }



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

  const generateMessageId = () => {
    return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  };

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

    const messageId = generateMessageId();
    const message: Message = {
      id: messageId,
      from: currentUser,
      to: otherUser,
      text,
      lang: 'en',
      timestamp: new Date().toISOString(), // Temporary timestamp, will be replaced by server timestamp
      status: 'sending'
    };

    // Add message with sending status
    setMessages(prev => [...prev, message]);

    // Send to WebSocket using the backend's expected format (no timestamp - server will generate)
    const success = sendWebSocketMessage({
      id: messageId,
      type: 'text',
      content: text
    });

    if (!success) {
      // Update status to failed immediately if WebSocket send failed
      setMessages(prev => prev.map(msg =>
        'id' in msg && 'from' in msg && msg.id === messageId && msg.from === currentUser
          ? { ...msg, status: 'failed' as const }
          : msg
      ));
    }
    // Note: Status will be updated to 'delivered' or 'failed' when confirmation is received
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

      const messageId = generateMessageId();
      // Create voice message for UI
      const voiceMessage: VoiceMessage = {
        id: messageId,
        from: currentUser,
        to: otherUser,
        type: 'voice',
        audioData: arrayBuffer,
        timestamp: new Date().toISOString(), // Temporary timestamp, will be replaced by server timestamp
        status: 'sending'
      };

      // Add message with sending status
      setMessages(prev => [...prev, voiceMessage]);

      // Send binary data via WebSocket
      const success = sendWebSocketBinaryMessage && sendWebSocketBinaryMessage(arrayBuffer);

      if (!success) {
        // Update status to failed immediately if WebSocket send failed
        setMessages(prev => prev.map(msg =>
          'id' in msg && 'from' in msg && msg.id === messageId && msg.from === currentUser
            ? { ...msg, status: 'failed' as const }
            : msg
        ));
      }
      // Note: Status will be updated to 'delivered' or 'failed' when confirmation is received
    } catch (error) {
      console.error('Error sending voice message:', error);
      setConnectionError({
        code: 'VOICE_SEND_FAILED',
        message: 'Failed to send voice message',
        timestamp: new Date().toISOString()
      });
    }
  };

  const retryMessage = (failedMessage: Message | VoiceMessage) => {
    if (!isConnected) {
      debugLog('Cannot retry message: WebSocket is not connected');
      return;
    }

    // Update message status to sending
    setMessages(prev => prev.map(msg =>
      'id' in msg && 'from' in msg && msg.id === failedMessage.id && msg.from === currentUser
        ? { ...msg, status: 'sending' as const }
        : msg
    ));

    if ('type' in failedMessage && failedMessage.type === 'voice') {
      // Retry voice message
      const success = sendWebSocketBinaryMessage && sendWebSocketBinaryMessage(failedMessage.audioData);
      if (!success) {
        setMessages(prev => prev.map(msg =>
          'id' in msg && 'from' in msg && msg.id === failedMessage.id && msg.from === currentUser
            ? { ...msg, status: 'failed' as const }
            : msg
        ));
      }
    } else {
      // Retry text message
      const textMessage = failedMessage as Message;
      const success = sendWebSocketMessage({
        id: textMessage.id,
        type: 'text',
        user_id: currentUser,
        room_id: roomId,
        content: textMessage.text || ''
      });

      if (!success) {
        setMessages(prev => prev.map(msg =>
          'id' in msg && 'from' in msg && msg.id === failedMessage.id && msg.from === currentUser
            ? { ...msg, status: 'failed' as const }
            : msg
        ));
      }
    }
  };

  const handleTyping = (typing: boolean) => {
    if (!isConnected) return;

    setIsTyping(typing);

    sendWebSocketMessage({
      type: 'typing',
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
            <div className="flex-1">
              <span>Connection Error: {connectionError.message}</span>
              {connectionError.code === 'CONNECTION_LIMIT_EXCEEDED' && (
                <div className="text-xs mt-1 text-muted-foreground">
                  Too many connections from your location. Please close other chat tabs or wait a moment before trying again.
                </div>
              )}
            </div>
            {connectionError.code !== 'CONNECTION_LIMIT_EXCEEDED' &&
              connectionError.code !== 'RECONNECTION_STOPPED' && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={reconnect}
                  className="ml-auto h-6 px-2 text-xs"
                >
                  Reconnect
                </Button>
              )}
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
              : `${message.timestamp}-${'from' in message ? message.from : 'unknown'}`;

            const isCurrentUser = 'from' in message ? message.from === currentUser : false;

            return (
              <MessageBubble
                key={messageKey}
                message={message}
                isCurrentUser={isCurrentUser}
                showTimestamp={showTimestamp}
                onRetry={isCurrentUser ? retryMessage : undefined}
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