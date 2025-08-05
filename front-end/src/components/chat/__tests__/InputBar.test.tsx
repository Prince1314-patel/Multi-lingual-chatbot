import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InputBar } from '../InputBar';

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
    }, 10);
  }
  
  stop() {
    this.state = 'inactive';
    setTimeout(() => {
      if (this.onstop) {
        this.onstop();
      }
    }, 10);
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

describe('InputBar', () => {
  const mockOnSendMessage = vi.fn();
  const mockOnSendVoiceMessage = vi.fn();
  const mockOnTyping = vi.fn();

  beforeEach(() => {
    // Setup mocks
    global.MediaRecorder = MockMediaRecorder as any;
    global.navigator.mediaDevices = {
      getUserMedia: mockGetUserMedia
    } as any;
    
    mockGetUserMedia.mockResolvedValue(new MockMediaStream());
    
    // Clear all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders input field and buttons', () => {
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start voice recording/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument();
  });

  it('sends text message when send button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const input = screen.getByPlaceholderText('Type a message...');
    const sendButton = screen.getByRole('button', { name: /send message/i });

    await user.type(input, 'Hello world');
    await user.click(sendButton);

    expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world');
    expect(input).toHaveValue('');
  });

  it('sends text message when Enter key is pressed', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const input = screen.getByPlaceholderText('Type a message...');

    await user.type(input, 'Hello world');
    await user.keyboard('{Enter}');

    expect(mockOnSendMessage).toHaveBeenCalledWith('Hello world');
    expect(input).toHaveValue('');
  });

  it('triggers typing indicator when user types', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const input = screen.getByPlaceholderText('Type a message...');

    await user.type(input, 'H');

    expect(mockOnTyping).toHaveBeenCalledWith(true);
  });

  it('stops typing indicator when input is cleared', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const input = screen.getByPlaceholderText('Type a message...');

    await user.type(input, 'Hello');
    await user.clear(input);

    expect(mockOnTyping).toHaveBeenCalledWith(false);
  });

  it('starts voice recording when mic button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    expect(mockGetUserMedia).toHaveBeenCalledWith({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Recording... Click the stop button when finished')).toBeInTheDocument();
    });
  });

  it('stops recording and sends voice message when stop button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    // Start recording
    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /stop recording/i })).toBeInTheDocument();
    });

    // Stop recording
    const stopButton = screen.getByRole('button', { name: /stop recording/i });
    await user.click(stopButton);

    await waitFor(() => {
      expect(mockOnSendVoiceMessage).toHaveBeenCalledWith(
        expect.any(Blob)
      );
    });
  });

  it('handles microphone access denied error', async () => {
    const user = userEvent.setup();
    mockGetUserMedia.mockRejectedValue(new DOMException('Permission denied', 'NotAllowedError'));
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByText(/microphone access denied/i)).toBeInTheDocument();
    });
  });

  it('handles no microphone found error', async () => {
    const user = userEvent.setup();
    mockGetUserMedia.mockRejectedValue(new DOMException('No microphone found', 'NotFoundError'));
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByText(/no microphone found/i)).toBeInTheDocument();
    });
  });

  it('disables input and buttons when disabled prop is true', () => {
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
        disabled={true}
      />
    );

    expect(screen.getByPlaceholderText('Type a message...')).toBeDisabled();
    expect(screen.getByRole('button', { name: /start voice recording/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /send message/i })).toBeDisabled();
  });

  it('disables text input during recording', async () => {
    const user = userEvent.setup();
    
    render(
      <InputBar
        onSendMessage={mockOnSendMessage}
        onSendVoiceMessage={mockOnSendVoiceMessage}
        onTyping={mockOnTyping}
      />
    );

    const micButton = screen.getByRole('button', { name: /start voice recording/i });
    await user.click(micButton);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Recording...')).toBeDisabled();
    });
  });
});