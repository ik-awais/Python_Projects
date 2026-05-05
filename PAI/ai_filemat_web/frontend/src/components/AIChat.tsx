import React, { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface AIChatProps {
  files?: any[];
  onIntentDetected?: (intent: any) => void;
}

const AIChat: React.FC<AIChatProps> = ({ files = [], onIntentDetected }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<'checking' | 'ready' | 'error'>('checking');
  const [aiProvider, setAiProvider] = useState<string>('gemini');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    checkAIStatus();
  }, []);

  const checkAIStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/ai/status');
      const data = await response.json();
      
      if (data.ready) {
        setAiStatus('ready');
        setAiProvider(data.provider);
      } else {
        setAiStatus('error');
      }
    } catch (error) {
      setAiStatus('error');
    }
  };

  const configureAI = async (provider: string, apiKey: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/ai/configure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          api_key: apiKey,
        }),
      });

      const result = await response.json();
      
      if (result.success) {
        setAiStatus('ready');
        setAiProvider(provider);
        return true;
      } else {
        setAiStatus('error');
        return false;
      }
    } catch (error) {
      setAiStatus('error');
      return false;
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Build context from files
      const context = files.length > 0 
        ? `You have ${files.length} file(s) loaded: ${files.map(f => f.name).join(', ')}`
        : '';

      const response = await fetch('http://localhost:8000/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          context,
          provider: aiProvider,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: result.data.response,
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMessage]);
      } else {
        throw new Error('Failed to get AI response');
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sorry, I encountered an error. Please check your AI configuration.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const parseIntent = async (message: string) => {
    try {
      const response = await fetch('http://localhost:8000/api/ai/parse-intent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          provider: aiProvider,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        onIntentDetected?.(result.data.intent);
      }
    } catch (error) {
      console.error('Intent parsing failed:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getStatusColor = () => {
    switch (aiStatus) {
      case 'ready': return 'text-green-600 dark:text-green-400';
      case 'error': return 'text-red-600 dark:text-red-400';
      default: return 'text-yellow-600 dark:text-yellow-400';
    }
  };

  const getStatusText = () => {
    switch (aiStatus) {
      case 'ready': return `AI Connected (${aiProvider})`;
      case 'error': return 'AI Not Configured';
      default: return 'Checking AI Status...';
    }
  };

  const getStatusIcon = () => {
    switch (aiStatus) {
      case 'ready': return '✅';
      case 'error': return '❌';
      default: return '⏳';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Assistant</h2>
            <div className="flex items-center space-x-2 text-sm">
              <span className={getStatusColor()}>
                {getStatusIcon()} {getStatusText()}
              </span>
            </div>
          </div>
          {aiStatus === 'error' && (
            <button
              onClick={checkAIStatus}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mb-4">
              <span className="text-white text-2xl">AI</span>
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Hello! I'm your AI FileMat assistant
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              I can help you process, analyze, and convert your files using natural language.
            </p>
            <div className="text-left max-w-md mx-auto">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Try asking me:</p>
              <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <li>• "Convert my PDF to Word document"</li>
                <li>• "Split this PDF into individual pages"</li>
                <li>• "What's in this spreadsheet?"</li>
                <li>• "Analyze this image for me"</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p className="text-xs mt-1 opacity-70">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 dark:bg-gray-700 px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              aiStatus === 'ready' 
                ? "Ask me anything about your files..." 
                : "Configure AI to start chatting..."
            }
            disabled={aiStatus !== 'ready' || isLoading}
            className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 dark:text-white disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={aiStatus !== 'ready' || isLoading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
        
        {files.length > 0 && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            📎 {files.length} file{files.length !== 1 ? 's' : ''} loaded
          </div>
        )}
      </div>
    </div>
  );
};

export default AIChat;
