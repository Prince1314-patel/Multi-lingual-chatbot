import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatWindow } from '../ChatWindow';

// Mock the useWebSocket hook
const mockSendMessage = vi.fn();
const mockSendBinaryMessage = vi.fn();
const mockReconnect = vi.fn();

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: true,
    isConnecting: false,
    error: null,
    sendMessage: mockSendMessage,
    sendBinaryMessage: mockSendBinaryMessage,
    reconnect: mockReconnect
  }))
}));

// Mock MediaRecorder
class MockMediaRecorder {
  static isTypeSupported = vi.fn(() => true);
  
  ondataavailable: ((event: any) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  state: string = 'inactive';
  
  constructor(stream: MediaStream, options?: any) {
    // Mock constructor
  }
  
  start() {
    this.state = 'recording';
    // Simulate data available after a short delay
    setTimeout(() => {
      if (this.ondataavailable) {
        this.ondataavailable({
          data: new Blob(['mock audio data'], { type: 'audio/webm;codecs=opus' })
        });
      }
    }, 100);
  }
  
  stop() {
    this.state = 'inactive';
    if (this.onstop) {
      this.onstop();
    }
  }
}

// Mock getUserMedia
const mockGetUserMedia = vi.fn();

// Mock MediaStream
class MockMediaStream {
  getTracks() {
    return [{ stop: vi.fn() }];
  }
}

// Mock HTMLAudioElement
class MockAudioElement {
  src: string = '';
  currentTime: number = 0;
  duration: number = 30;
  paused: boolean = true;
  
  addEventListener = vi.fn();
  removeEventListener = vi.fn();
  play = vi.fn().mockResolvedValue(undefined);
  pause = vi.fn();
  
  triggerEvent(eventType: string) {
    const listeners = this.addEventListener.mock.calls
      .filter(call => call[0] === eventType)
      .map(call => call[1]);
    
    listeners.forEach(listener => listener());
  }
}

// Mock URL methods
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
const mockRevokeObjectURL = vi.fn();

describe('Voice Message Integration', () => {
  let mockAudio: MockAudioElement;

  beforeEach(() => {
    // Setup all mocks
    global.MediaRecorder = MockMediaRecorder as any;
    global.navigator.mediaDevices = {
      getUserMedia: mockGetUserMedia
    } as any;
    
    mockAudio = new MockAudioElement();
    global.HTMLAudioElement = vi.fn(() => mockAudio) as any;
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;
    
    mockGetUserMedia.mockResolvedValue(new MockMediaStream());
    
    // Clear all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('completes full voice message recording and sending flow', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    // Find and click the microphone button
    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    // Verify microphone access was requested
    expect(mockGetUserMedia).toHaveBeenCalledWith({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100
      }
    });

    // Wait for recording to start
    await waitFor(() => {
      expect(screen.getByText('Recording... Click the stop button when finished')).toBeInTheDocument();
    });

    // Stop recording
    const stopButton = screen.getByRole('button', { name: /stop recording/i });
    await user.click(stopButton);

    // Wait for voice message to be sent
    await waitFor(() => {
      expect(mockSendBinaryMessage).toHaveBeenCalledWith(
        expect.any(ArrayBuffer)
      );
    });

    // Verify voice message appears in chat
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });
  });

  it('handles voice message reception and playback', async () => {
    const user = userEvent.setup();
    
    const { rerender } = render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    // Simulate receiving a voice message via WebSocket
    const mockUseWebSocket = await import('@/hooks/useWebSocket');
    const mockOptions = (mockUseWebSocket.useWebSocket as any).mock.calls[0][1];
    
    // Simulate binary message received
    const mockAudioData = new ArrayBuffer(1024);
    mockOptions.onBinaryMessage(mockAudioData);

    // Wait for voice message to appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });

    // Click play button
    const playButton = screen.getByRole('button', { name: /play/i });
    await user.click(playButton);

    // Verify audio play was called
    expect(mockAudio.play).toHaveBeenCalled();
  });

  it('handles microphone permission denied gracefully', async () => {
    const user = userEvent.setup();
    mockGetUserMedia.mockRejectedValue(new DOMException('Permission denied', 'NotAllowedError'));
    
    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByText(/microphone access denied/i)).toBeInTheDocument();
    });

    // Verify no binary message was sent
    expect(mockSendBinaryMessage).not.toHaveBeenCalled();
  });

  it('handles recording errors gracefully', async () => {
    const user = userEvent.setup();
    
    // Mock MediaRecorder to throw error
    const mockMediaRecorderError = class extends MockMediaRecorder {
      start() {
        super.start();
        setTimeout(() => {
          if (this.onerror) {
            this.onerror(new Event('error'));
          }
        }, 50);
      }
    };
    
    global.MediaRecorder = mockMediaRecorderError as any;
    
    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByText(/recording failed/i)).toBeInTheDocument();
    });

    // Verify no binary message was sent
    expect(mockSendBinaryMessage).not.toHaveBeenCalled();
  });

  it('disables voice recording when WebSocket is disconnected', () => {
    // Mock disconnected state
    const mockUseWebSocket = vi.mocked(await import('@/hooks/useWebSocket'));
    mockUseWebSocket.useWebSocket.mockReturnValue({
      isConnected: false,
      isConnecting: false,
      error: null,
      sendMessage: mockSendMessage,
      sendBinaryMessage: mockSendBinaryMessage,
      connect: vi.fn(),
      disconnect: vi.fn(),
      reconnect: mockReconnect
    });

    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    expect(micButton).toBeDisabled();
  });

  it('shows voice message status correctly', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    // Record and send voice message
    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByText('Recording... Click the stop button when finished')).toBeInTheDocument();
    });

    const stopButton = screen.getByRole('button', { name: /stop recording/i });
    await user.click(stopButton);

    // Wait for voice message to appear with sending status
    await waitFor(() => {
      const voiceMessage = screen.getByRole('button', { name: /play/i }).closest('[class*="mb-4"]');
      expect(voiceMessage).toBeInTheDocument();
    });

    // Verify binary message was sent
    expect(mockSendBinaryMessage).toHaveBeenCalledWith(expect.any(ArrayBuffer));
  });

  it('handles voice message playback errors gracefully', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    // Simulate receiving a voice message
    const mockUseWebSocket = await import('@/hooks/useWebSocket');
    const mockOptions = (mockUseWebSocket.useWebSocket as any).mock.calls[0][1];
    
    const mockAudioData = new ArrayBuffer(1024);
    mockOptions.onBinaryMessage(mockAudioData);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
    });

    // Mock audio play to reject
    mockAudio.play.mockRejectedValue(new Error('Playback failed'));

    const playButton = screen.getByRole('button', { name: /play/i });
    await user.click(playButton);

    // Should handle error gracefully without crashing
    expect(playButton).toBeInTheDocument();
  });

  it('supports multiple voice messages in conversation', async () => {
    const user = userEvent.setup();
    
    render(
      <ChatWindow
        roomId="test-room"
        currentUser="user1"
        otherUser="user2"
      />
    );

    // Send first voice message
    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /stop recording/i })).toBeInTheDocument();
    });

    const stopButton = screen.getByRole('button', { name: /stop recording/i });
    await user.click(stopButton);

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /play/i })).toHaveLength(1);
    });

    // Simulate receiving another voice message
    const mockUseWebSocket = await import('@/hooks/useWebSocket');
    const mockOptions = (mockUseWebSocket.useWebSocket as any).mock.calls[0][1];
    
    const mockAudioData = new ArrayBuffer(2048);
    mockOptions.onBinaryMessage(mockAudioData);

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /play/i })).toHaveLength(2);
    });

    // Verify both voice messages are playable
    const playButtons = screen.getAllByRole('button', { name: /play/i });
    expect(playButtons).toHaveLength(2);
  });
});