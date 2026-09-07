import React, { useState, useEffect } from 'react';
import { MomoAvatar } from './components/MomoAvatar/MomoAvatar';
import { ChatWindow } from './components/Chat/ChatWindow';
import { DocumentUploader } from './components/Documents/DocumentUploader';
import { InvoiceCard } from './components/Finance/InvoiceCard';
import { MessageDrafter } from './components/Texting/MessageDrafter';
import { Esp32Card } from './components/DeviceStatus/Esp32Card';
import { TopologyMap } from './components/SystemStatus/TopologyMap';
import { PrivacyToggles } from './components/Privacy/PrivacyToggles';

import {
  ChatMessage,
  MomoExpression,
  MomoAnimation,
  SystemStatus,
  ProcessedDocument,
  FinancialInsight,
  DeviceTelemetry,
} from './types/momo';

import {
  fetchSystemStatus,
  fetchOllamaModels,
  fetchDocuments,
  fetchDevices,
} from './services/api';

import { momoSocket } from './services/websocket';
import { voiceEngine } from './services/voice';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'chat' | 'documents' | 'finance' | 'settings'>('dashboard');

  // Live MOMO Emotional State
  const [expression, setExpression] = useState<MomoExpression>('normal');
  const [animation, setAnimation] = useState<MomoAnimation>('none');
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(voiceEngine.isVoiceEnabled());

  // System & Model Telemetry
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0');
  const [device, setDevice] = useState<DeviceTelemetry | null>(null);

  // Chat History
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      role: 'assistant',
      content: "👋 Hey there! I'm MOMO, your local-first physical AI companion. My brain runs locally on your laptop, and my physical body runs on the ESP32 via USB-C or Wi-Fi. How can I help you today?",
      expression: 'happy',
      animation: 'wave',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  // Documents & Finance State
  const [documents, setDocuments] = useState<ProcessedDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<ProcessedDocument | null>(null);
  const [activeInsight, setActiveInsight] = useState<FinancialInsight | null>({
    invoice_number: 'INV-1042',
    invoice_total: 48500,
    amount_paid: 20000,
    balance_due: 28500,
    currency: 'INR',
    due_date: '2026-09-15',
    payment_status: 'partially_paid',
    confidence: 1.0,
    notes: 'Sample verified invoice pre-loaded for testing.',
  });

  // Initialize Services & WebSocket
  useEffect(() => {
    // 1. Connect WebSocket
    momoSocket.connect();

    // 2. Track speech engine speaking state
    const unsubVoice = voiceEngine.onSpeakingChange((speaking) => {
      setIsSpeaking(speaking);
    });

    // 3. Listen to WebSocket events
    const unsubMsg = momoSocket.on('momo_response', (payload: any) => {
      setIsThinking(false);
      if (payload.expression) setExpression(payload.expression);
      if (payload.animation) setAnimation(payload.animation);

      if (payload.message) {
        const newMsg: ChatMessage = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: payload.message,
          expression: payload.expression,
          animation: payload.animation,
          thinking: payload.thinking,
          model: payload.model,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, newMsg]);

        // Synthesize text to voice output automatically
        if (payload.speak !== false) {
          voiceEngine.speak(payload.message);
        }
      }
    });

    const unsubThinking = momoSocket.on('momo_thinking', (payload: any) => {
      setIsThinking(Boolean(payload.is_thinking));
    });

    const unsubDevice = momoSocket.on('device_status', (payload: any) => {
      setDevice(payload);
    });

    // 4. Fetch initial REST diagnostics & periodic polling every 5s
    refreshSystemStatus();
    const statusInterval = setInterval(() => {
      refreshSystemStatus();
    }, 5000);

    fetchDocuments().then(setDocuments).catch(() => {});
    fetchDevices().then((devs) => {
      if (devs.length > 0) setDevice(devs[0]);
    }).catch(() => {});

    return () => {
      clearInterval(statusInterval);
      unsubVoice();
      unsubMsg();
      unsubThinking();
      unsubDevice();
      voiceEngine.stop();
    };
  }, []);

  const refreshSystemStatus = () => {
    fetchSystemStatus().then(setSystemStatus).catch(() => {});
    fetchOllamaModels().then((models) => {
      const llamaModels = models.filter((m) => m.toLowerCase().includes('llama'));
      const active = llamaModels.length > 0 ? llamaModels : ['hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0'];
      setAvailableModels(active);
      setSelectedModel((current) => {
        if (current && active.includes(current)) return current;
        return active[0];
      });
    }).catch(() => {});
  };

  const handleSendMessage = (text: string) => {
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsThinking(true);
    setExpression('thinking');

    // 90-second client-side safety timer so UI is never stuck on thinking
    setTimeout(() => {
      setIsThinking((current) => {
        if (current) {
          console.warn("Client safety timer: reset thinking state after 90s.");
          setExpression('normal');
          return false;
        }
        return false;
      });
    }, 90000);

    // Send via persistent WebSocket with user's selected fast model
    momoSocket.sendChatMessage(text, 'default', selectedModel);
  };

  const handleDocumentProcessed = (doc: ProcessedDocument, insight?: FinancialInsight) => {
    setDocuments((prev) => [doc, ...prev]);
    setSelectedDocument(doc);
    if (insight) {
      setActiveInsight(insight);
      setActiveTab('finance');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Header */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-emerald-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-emerald-900/30">
            M
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
              <span>MOMO</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono font-normal">
                Local-First AI
              </span>
            </h1>
            <span className="text-[11px] text-slate-400 font-mono">
              Laptop Brain • ESP32 Body ({selectedModel})
            </span>
          </div>
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-2.5">
          {/* Ollama Pill */}
          <button
            onClick={refreshSystemStatus}
            className={`px-3 py-1 rounded-full text-xs font-mono flex items-center gap-1.5 border transition-all ${
              systemStatus?.ollama
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                : 'bg-rose-950/60 border-rose-800 text-rose-400'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${systemStatus?.ollama ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'}`} />
            <span>{systemStatus?.ollama ? 'Ollama Online' : 'Ollama Offline'}</span>
          </button>

          {/* Backend Pill */}
          <div className="px-3 py-1 rounded-full text-xs font-mono bg-slate-800/80 border border-slate-700 text-slate-300 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Django ASGI</span>
          </div>

          {/* ESP32 Hardware Pill */}
          <div className={`px-3 py-1 rounded-full text-xs font-mono border flex items-center gap-1.5 ${
            systemStatus?.esp32 || device?.status === 'online'
              ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
              : 'bg-slate-800 border-slate-700 text-slate-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${systemStatus?.esp32 || device?.status === 'online' ? 'bg-emerald-400' : 'bg-slate-500'}`} />
            <span>{device?.connection_type === 'usb_serial' ? 'ESP32 (USB-C)' : 'ESP32 (Physical)'}</span>
          </div>

          {/* Voice Output Quick Pill */}
          <button
            onClick={() => setVoiceEnabled(voiceEngine.toggleVoice())}
            title={voiceEnabled ? "Voice output enabled (click to mute)" : "Voice output muted (click to enable)"}
            className={`px-3 py-1 rounded-full text-xs font-mono border flex items-center gap-1.5 transition-all ${
              voiceEnabled
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400 hover:bg-emerald-900/60'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <span>{voiceEnabled ? '🔊 Voice' : '🔇 Muted'}</span>
            {isSpeaking && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />}
          </button>
        </div>
      </header>

      {/* Navigation Tabs Bar */}
      <nav className="bg-slate-900/40 border-b border-slate-800/60 px-6 py-2 flex gap-1.5">
        {[
          { id: 'dashboard', label: 'Dashboard', icon: '⚡' },
          { id: 'chat', label: 'AI Chatbot', icon: '🤖' },
          { id: 'documents', label: 'Documents & Invoices', icon: '📄' },
          { id: 'finance', label: 'Finance & Texting', icon: '💰' },
          { id: 'settings', label: 'System & Privacy', icon: '⚙️' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === tab.id
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* Main Content Body */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6">
        {/* TAB 1: DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
              {/* Left: Interactive Avatar */}
              <div className="lg:col-span-1 p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-md flex flex-col items-center justify-center">
                <span className="text-xs font-mono uppercase text-slate-400 mb-4 tracking-wider">
                  Digital MOMO Avatar
                </span>
                <MomoAvatar
                  expression={expression}
                  animation={animation}
                  isThinking={isThinking}
                  isSpeaking={isSpeaking}
                  size={240}
                  interactive={true}
                  onExpressionChange={(exp) => {
                    setExpression(exp);
                    momoSocket.sendDeviceCommand(exp, 'none');
                  }}
                />
              </div>

              {/* Right: Quick Chat & Status Overview */}
              <div className="lg:col-span-2 space-y-6">
                <div className="h-[460px]">
                  <ChatWindow
                    messages={messages}
                    onSendMessage={handleSendMessage}
                    isThinking={isThinking}
                    selectedModel={selectedModel}
                    onModelChange={setSelectedModel}
                    availableModels={availableModels}
                  />
                </div>
              </div>
            </div>

            {/* Bottom: Hardware Status Card */}
            <Esp32Card
              device={device}
              currentExpression={expression}
              currentAnimation={animation}
            />
          </div>
        )}

        {/* TAB 2: CHAT */}
        {activeTab === 'chat' && (
          <div className="h-[calc(100vh-180px)]">
            <ChatWindow
              messages={messages}
              onSendMessage={handleSendMessage}
              isThinking={isThinking}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              availableModels={availableModels}
            />
          </div>
        )}

        {/* TAB 3: DOCUMENTS */}
        {activeTab === 'documents' && (
          <DocumentUploader
            documents={documents}
            onDocumentProcessed={handleDocumentProcessed}
            onSelectDocument={(doc) => setSelectedDocument(doc)}
          />
        )}

        {/* TAB 4: FINANCE & TEXTING */}
        {activeTab === 'finance' && (
          <div className="space-y-6">
            {activeInsight ? (
              <InvoiceCard
                insight={activeInsight}
                onDraftReminder={() => {}}
              />
            ) : (
              <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center text-slate-500 font-mono text-xs">
                No active invoice loaded. Upload an invoice in the Documents tab or chat with MOMO!
              </div>
            )}

            <MessageDrafter initialInsight={activeInsight} />
          </div>
        )}

        {/* TAB 5: SETTINGS & PRIVACY */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <TopologyMap status={systemStatus} />
            <PrivacyToggles />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
