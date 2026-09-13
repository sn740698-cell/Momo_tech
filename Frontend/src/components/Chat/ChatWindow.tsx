import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../../types/momo';
import { voiceEngine } from '../../services/voice';

interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  onClearChat?: () => void;
  isThinking: boolean;
  selectedModel: string;
  onModelChange: (model: string) => void;
  availableModels: string[];
}

export function cleanDisplayMessage(content: string): string {
  if (!content) return '';
  let text = content.trim();

  // If text starts with '{' or has JSON keys, extract message or strip JSON scaffolding
  if (text.startsWith('{') && (text.includes('"message"') || text.includes('"expression"') || text.includes('"animation"'))) {
    try {
      const parsed = JSON.parse(text);
      if (parsed.message) text = String(parsed.message);
      else if (parsed.content) text = String(parsed.content);
    } catch {
      // Malformed/unclosed JSON regex extraction
      const match = text.match(/"(?:message|content)"\s*:\s*"((?:[^"\\]|\\.)*)/s);
      if (match && match[1]) {
        text = match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
      } else {
        // Strip out JSON keys and braces completely
        text = text
          .replace(/["']?(?:expression|animation|priority|speak)["']?\s*:\s*["']?[^,"\n}]*["']?,?/gi, '')
          .replace(/["']?(?:message|content|response|text)["']?\s*:\s*"?/gi, '')
          .replace(/[{}]/g, '')
          .trim();
      }
    }
  }

  // Strip cutoff disclaimers
  text = text.replace(/as of my (?:current\s+)?knowledge cutoff[.\n]*[.\n]?/gi, '');
  text = text.replace(/my knowledge cutoff is[.\n]*[.\n]?/gi, '');
  text = text.replace(/i (?:do not|don't) have (?:access to )?real-time (?:data|information|updates)[.\n]*[.\n]?/gi, '');

  return text.trim() || 'I am at your service.';
}

const CodeBlock: React.FC<{ language: string; code: string }> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2.5 rounded-xl border border-slate-700/80 bg-slate-950/95 overflow-hidden shadow-xl font-mono text-xs">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900/90 border-b border-slate-800 text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400/80 inline-block" />
          <span className="text-[11px] font-semibold tracking-wider uppercase text-emerald-400">
            {language || 'code'}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition-all active:scale-95 cursor-pointer"
          title="Copy code to clipboard"
        >
          {copied ? (
            <>
              <span className="text-emerald-400 font-bold">✓</span>
              <span className="text-emerald-400 font-medium">Copied!</span>
            </>
          ) : (
            <>
              <span>📋</span>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-emerald-300 whitespace-pre leading-relaxed font-mono select-text text-[13px]">
        <code>{code}</code>
      </pre>
    </div>
  );
};

function renderInlineElements(text: string): React.ReactNode[] {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 mx-0.5 rounded bg-slate-950 border border-slate-700/80 font-mono text-xs text-amber-300 font-medium"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

const FormattedText: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.split('\n');
  return (
    <div className="space-y-1">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        const isBullet = trimmed.startsWith('•') || trimmed.startsWith('- ');
        const content = isBullet ? trimmed.replace(/^[•\-]\s*/, '') : line;
        const rendered = renderInlineElements(content);

        if (isBullet) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-1 py-0.5">
              <span className="text-emerald-400 select-none mt-0.5 font-bold">•</span>
              <span className="flex-1 leading-relaxed">{rendered}</span>
            </div>
          );
        }

        if (trimmed === '') {
          return <div key={idx} className="h-1.5" />;
        }

        return (
          <div key={idx} className="leading-relaxed">
            {rendered}
          </div>
        );
      })}
    </div>
  );
};

export const MessageContent: React.FC<{ content: string }> = ({ content }) => {
  const cleaned = cleanDisplayMessage(content);
  const codeBlockRegex = /```([a-zA-Z0-9_\-+]*)\r?\n([\s\S]*?)```/g;
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(cleaned)) !== null) {
    if (match.index > lastIndex) {
      const textBefore = cleaned.slice(lastIndex, match.index);
      if (textBefore.trim()) {
        elements.push(<FormattedText key={`text-${lastIndex}`} text={textBefore} />);
      }
    }
    const lang = match[1] || 'code';
    const code = match[2];
    elements.push(<CodeBlock key={`code-${match.index}`} language={lang} code={code} />);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < cleaned.length) {
    const remaining = cleaned.slice(lastIndex);
    const unclosedMatch = remaining.match(/^```([a-zA-Z0-9_\-+]*)\r?\n([\s\S]*)$/);
    if (unclosedMatch) {
      elements.push(
        <CodeBlock key={`code-unclosed`} language={unclosedMatch[1] || 'code'} code={unclosedMatch[2]} />
      );
    } else if (remaining.trim()) {
      elements.push(<FormattedText key={`text-${lastIndex}`} text={remaining} />);
    }
  }

  if (elements.length === 0) {
    return <FormattedText text={cleaned} />;
  }

  return <div className="text-sm space-y-1.5">{elements}</div>;
};

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  onSendMessage,
  onClearChat,
  isThinking,
  selectedModel,
  onModelChange,
  availableModels,
}) => {
  const [input, setInput] = useState('');
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(voiceEngine.isVoiceEnabled());
  const [activeSpokenId, setActiveSpokenId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const unsub = voiceEngine.onSpeakingChange((speaking) => {
      if (!speaking) setActiveSpokenId(null);
    });
    return unsub;
  }, []);

  // Removed auto-scroll on send/isThinking per user requirement: viewport remains steady when sending messages

  const handleSend = () => {
    if (!input.trim() || isThinking) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  const copyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const quickPrompts = [
    "What's the status of invoice INV-1042?",
    "Draft a friendly reminder for Rahul's overdue balance.",
    "Hey MOMO, how are you feeling today?",
    "Show me system health and VRAM telemetry.",
  ];

  return (
    <div className="flex flex-col h-full bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Top Controls Bar */}
      <div className="px-4 py-3 bg-slate-800/80 border-b border-slate-700/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-sm font-semibold text-slate-200">MOMO Conversation</span>
        </div>

        {/* Controls: Clear, Voice & Model Selector */}
        <div className="flex items-center gap-2.5">
          {onClearChat && (
            <button
              onClick={onClearChat}
              title="Clear conversation history & reset memory"
              className="px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-1 border border-rose-900/60 bg-rose-950/40 text-rose-300 hover:bg-rose-900/50 hover:border-rose-700 transition-all active:scale-98"
            >
              <span>🗑️ Clear</span>
            </button>
          )}

          <button
            onClick={() => setVoiceEnabled(voiceEngine.toggleVoice())}
            title={voiceEnabled ? "Mute Voice Output" : "Enable Voice Output"}
            className={`px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 border transition-all ${
              voiceEnabled
                ? 'bg-emerald-950/70 border-emerald-700 text-emerald-400 hover:bg-emerald-900/60'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <span>{voiceEnabled ? '🔊 Voice ON' : '🔇 Voice OFF'}</span>
          </button>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Model:</span>
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value)}
              className="bg-slate-900 text-emerald-400 border border-slate-700 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-emerald-500 font-mono"
            >
              {availableModels.length > 0 ? (
                availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))
              ) : (
                <option value="hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0">Llama-3.2-1B (default)</option>
              )}
            </select>
          </div>
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-2xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
            >
              {/* Avatar Icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                  isUser
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-900/40'
                    : 'bg-emerald-600 text-white shadow-md shadow-emerald-900/40'
                }`}
              >
                {isUser ? 'U' : 'M'}
              </div>

              {/* Message Content Bubble */}
              <div
                className={`rounded-2xl px-4 py-3 border transition-all ${
                  isUser
                    ? 'bg-indigo-600/20 border-indigo-500/40 text-slate-100'
                    : 'bg-slate-800/90 border-slate-700 text-slate-200 shadow-md'
                }`}
              >
                {/* Assistant Expression Badge */}
                {!isUser && msg.expression && (
                  <div className="flex items-center gap-2 mb-1.5 pb-1 border-b border-slate-700/60">
                    <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                      face: {msg.expression}
                    </span>
                    {msg.animation && msg.animation !== 'none' && (
                      <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                        servo: {msg.animation}
                      </span>
                    )}
                  </div>
                )}

                {/* Thinking Accordion if provided by Ollama */}
                {msg.thinking && (
                  <div className="mb-2">
                    <button
                      onClick={() =>
                        setExpandedThinking((prev) => ({
                          ...prev,
                          [msg.id]: !prev[msg.id],
                        }))
                      }
                      className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-mono"
                    >
                      <span>{expandedThinking[msg.id] ? '▼' : '▶'}</span>
                      <span>Thought Process ({msg.thinking.length} chars)</span>
                    </button>
                    {expandedThinking[msg.id] && (
                      <div className="mt-1.5 p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-400 whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {msg.thinking}
                      </div>
                    )}
                  </div>
                )}

                {/* Text Body */}
                <div className="leading-relaxed text-sm">
                  <MessageContent content={msg.content} />
                </div>

                {/* Footer timestamp, listen button & copy */}
                <div className="mt-2 flex items-center justify-between gap-4 text-[10px] text-slate-500">
                  <span>{msg.timestamp}</span>
                  <div className="flex items-center gap-2.5">
                    {!isUser && (
                      <button
                        onClick={() => {
                          const toSpeak = cleanDisplayMessage(msg.content);
                          if (activeSpokenId === msg.id) {
                            voiceEngine.stop();
                            setActiveSpokenId(null);
                          } else {
                            setActiveSpokenId(msg.id);
                            voiceEngine.speak(toSpeak, () => setActiveSpokenId(null));
                          }
                        }}
                        className={`transition-colors font-mono flex items-center gap-1 ${
                          activeSpokenId === msg.id
                            ? 'text-rose-400 font-bold'
                            : 'text-emerald-400/90 hover:text-emerald-300'
                        }`}
                        title={activeSpokenId === msg.id ? 'Stop voice playback' : 'Read message aloud'}
                      >
                        <span>{activeSpokenId === msg.id ? '⏹ Stop' : '🔊 Listen'}</span>
                      </button>
                    )}
                    <button
                      onClick={() => copyText(msg.id, cleanDisplayMessage(msg.content))}
                      className="hover:text-slate-300 transition-colors font-mono"
                    >
                      {copiedId === msg.id ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {/* Thinking Indicator */}
        {isThinking && (
          <div className="flex items-center gap-3 text-slate-400 text-xs font-mono">
            <div className="w-8 h-8 rounded-full bg-emerald-600/30 flex items-center justify-center">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            </div>
            <div className="flex gap-1">
              <span className="animate-bounce">MOMO is thinking</span>
              <span className="animate-pulse">...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Quick Prompts Bar */}
      {messages.length <= 2 && (
        <div className="px-4 py-2 flex flex-wrap gap-2 border-t border-slate-800/80 bg-slate-900/40">
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={() => onSendMessage(p)}
              className="text-xs px-3 py-1.5 rounded-xl bg-slate-800/90 text-slate-300 border border-slate-700/60 hover:border-emerald-500/50 hover:text-emerald-300 transition-all text-left"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <div className="p-3 bg-slate-800/80 border-t border-slate-700/80">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputResize}
            onKeyDown={handleKeyDown}
            placeholder="Talk with MOMO (Shift+Enter for new line)..."
            rows={1}
            disabled={isThinking}
            className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-all resize-none max-h-40"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isThinking}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:hover:bg-emerald-600 text-white text-sm font-semibold rounded-xl transition-all shadow-md shadow-emerald-900/40 flex items-center gap-1.5"
          >
            <span>Send</span>
            <span>↵</span>
          </button>
        </div>
      </div>
    </div>
  );
};
