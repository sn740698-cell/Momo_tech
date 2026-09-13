import React, { useState, useEffect, useRef } from 'react';
import { MomoAvatar } from './components/MomoAvatar/MomoAvatar';
import { ChatWindow } from './components/Chat/ChatWindow';
import { Esp32Card } from './components/DeviceStatus/Esp32Card';
import { TopologyMap } from './components/SystemStatus/TopologyMap';
import { PrivacyToggles } from './components/Privacy/PrivacyToggles';
import { VisionCard } from './components/Vision/VisionCard';

import {
  ChatMessage,
  MomoExpression,
  MomoAnimation,
  SystemStatus,
  DeviceTelemetry,
  VisionTelemetry,
} from './types/momo';

import {
  fetchSystemStatus,
  fetchOllamaModels,
  fetchDevices,
  sendApiChatMessage,
  launchGameAutomation,
  fetchGameMotivation,
} from './services/api';

import { momoSocket } from './services/websocket';
import { voiceEngine } from './services/voice';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'chat' | 'settings'>('dashboard');

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
  const [visionTelemetry, setVisionTelemetry] = useState<VisionTelemetry | null>(null);

  // Polite Game Break Modal State
  const [showGameModal, setShowGameModal] = useState<boolean>(false);
  const [selectedGame, setSelectedGame] = useState<string>('2048');
  const [gamePromptMessage, setGamePromptMessage] = useState<string>(
    "You've been working hard! Let's play a game, I will open it for you."
  );

  // Safety refs for chat turn tracking
  const currentPendingTurnRef = useRef<string | null>(null);

  // Chat History
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      role: 'assistant',
      content: "👋 Hey there! I'm MOMO, your local-first companion robot. I perceive your facial expressions and fatigue through the camera next to my OLED eyes, and I'm right here to support your work and make you smile!",
      expression: 'happy',
      animation: 'wave',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  // Helper to handle incoming assistant turns
  const handleAssistantTurn = (payload: any) => {
    setIsThinking(false);
    currentPendingTurnRef.current = null;

    if (payload.expression) setExpression(payload.expression);
    if (payload.animation) setAnimation(payload.animation);

    if (payload.message) {
      const newMsg: ChatMessage = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: payload.message,
        expression: payload.expression || 'normal',
        animation: payload.animation || 'none',
        thinking: payload.thinking,
        model: payload.model,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, newMsg]);

      if (payload.speak !== false) {
        voiceEngine.speak(payload.message);
      }
    }
  };

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
      handleAssistantTurn(payload);

      // If this is a proactive fatigue alert, also pop up the gentle game break modal
      if (payload.source === 'proactive_monitor' || payload.proactive_event) {
        setGamePromptMessage(payload.message || "Let's play a game, I will open it for you.");
        setShowGameModal(true);
      }
    });

    const unsubThinking = momoSocket.on('momo_thinking', (payload: any) => {
      setIsThinking(Boolean(payload.is_thinking));
    });

    const unsubDevice = momoSocket.on('device_status', (payload: any) => {
      setDevice(payload);
    });

    const unsubVision = momoSocket.on('vision_telemetry', (payload: any) => {
      if (payload?.telemetry) {
        setVisionTelemetry(payload.telemetry);
        // If fatigue detected and modal not already dismissed, prompt gently
        if (payload.telemetry.fatigue_detected && !showGameModal) {
          setGamePromptMessage("You've been working continuously! Let's play a quick game, I will open it for you.");
        }
      }
    });

    // 4. Fetch initial REST diagnostics & periodic polling
    refreshSystemStatus();
    const statusInterval = setInterval(() => {
      refreshSystemStatus();
    }, 5000);

    const visionPollInterval = setInterval(() => {
      momoSocket.send({ type: 'poll_vision' });
    }, 3500);

    fetchDevices().then((devs) => {
      if (devs.length > 0) setDevice(devs[0]);
    }).catch(() => {});

    return () => {
      clearInterval(statusInterval);
      clearInterval(visionPollInterval);
      unsubVoice();
      unsubMsg();
      unsubThinking();
      unsubDevice();
      unsubVision();
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

  const handleSendMessage = async (text: string) => {
    const turnId = `turn_${Date.now()}`;
    currentPendingTurnRef.current = turnId;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsThinking(true);
    setExpression('thinking');

    // Send via WebSocket if connected
    const socketSent = momoSocket.sendChatMessage(text, 'default', selectedModel);

    if (!socketSent) {
      console.warn("[MOMO-WS] Socket not open, dispatching immediately to REST /api/chat/");
      try {
        const restResp = await sendApiChatMessage(text, selectedModel);
        if (currentPendingTurnRef.current === turnId && restResp) {
          handleAssistantTurn(restResp);
        }
      } catch (restErr) {
        console.error("REST immediate send error:", restErr);
        if (currentPendingTurnRef.current === turnId) {
          setIsThinking(false);
          setExpression('confused');
          setMessages((prev) => [
            ...prev,
            {
              id: `err_${Date.now()}`,
              role: 'assistant',
              content: "I'm having trouble reaching the local AI engine. Please ensure Ollama is running and try again!",
              expression: 'confused',
              animation: 'shake',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            },
          ]);
        }
      }
      return;
    }

    // Fallback: If socket sent but no response arrives within 6 seconds, trigger REST
    const fallbackTimer = setTimeout(async () => {
      if (currentPendingTurnRef.current === turnId) {
        console.warn("[MOMO-WS] Response timeout on WebSocket, falling back to REST /api/chat/");
        try {
          const restResp = await sendApiChatMessage(text, selectedModel);
          if (currentPendingTurnRef.current === turnId && restResp) {
            handleAssistantTurn(restResp);
          }
        } catch (restErr) {
          console.error("REST fallback error:", restErr);
          if (currentPendingTurnRef.current === turnId) {
            setIsThinking(false);
            setExpression('confused');
            setMessages((prev) => [
              ...prev,
              {
                id: `err_${Date.now()}`,
                role: 'assistant',
                content: "I'm having trouble reaching the local AI engine. Please ensure Ollama is running and try again!",
                expression: 'confused',
                animation: 'shake',
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              },
            ]);
          }
        }
      }
    }, 6000);

    // Final safety timer (30s)
    setTimeout(() => {
      if (currentPendingTurnRef.current === turnId) {
        setIsThinking(false);
        setExpression('normal');
        currentPendingTurnRef.current = null;
      }
    }, 30000);
  };

  const handleClearChat = async () => {
    try {
      momoSocket.send({ type: 'clear_chat', session_id: 'default' });
      await fetch('/api/chat/clear/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: 'default' }),
      });
    } catch (e) {
      console.warn("Clear chat error:", e);
    }
    setMessages([
      {
        id: `clear_${Date.now()}`,
        role: 'assistant',
        content: "✨ Conversation cleared! Memory and previous topics have been refreshed. What would you like to explore next?",
        expression: 'happy',
        animation: 'nod',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
    ]);
  };

  // Launch game via desktop automation & PyAutoGUI
  const handleAcceptGameBreak = async () => {
    setShowGameModal(false);
    setExpression('excited');
    setAnimation('celebrate');
    momoSocket.sendDeviceCommand('excited', 'celebrate');

    // 1. Motivational announcement
    try {
      const mot = await fetchGameMotivation(selectedGame);
      const motText = `🎮 Let's play ${selectedGame}! ${mot.motivation}`;
      const motMsg: ChatMessage = {
        id: `mot_${Date.now()}`,
        role: 'assistant',
        content: motText,
        expression: 'excited',
        animation: 'celebrate',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, motMsg]);
      voiceEngine.speak(motText);
    } catch (e) {
      console.warn("Could not fetch motivation:", e);
    }

    // 2. Launch game automation (PyAutoGUI + Playwright)
    try {
      await launchGameAutomation(selectedGame);
    } catch (e) {
      console.error("Failed to launch game automation:", e);
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
                Local-First AI Companion
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

          {/* Voice Output Pill */}
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

      {/* Navigation Tabs Bar (Simplified: Dashboard, AI Chatbot, System & Privacy) */}
      <nav className="bg-slate-900/40 border-b border-slate-800/60 px-6 py-2 flex gap-1.5">
        {[
          { id: 'dashboard', label: 'Dashboard', icon: '⚡' },
          { id: 'chat', label: 'AI Chatbot', icon: '🤖' },
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

              {/* Right: Quick Chat Window */}
              <div className="lg:col-span-2 space-y-6">
                <div className="h-[460px]">
                  <ChatWindow
                    messages={messages}
                    onSendMessage={handleSendMessage}
                    onClearChat={handleClearChat}
                    isThinking={isThinking}
                    selectedModel={selectedModel}
                    onModelChange={setSelectedModel}
                    availableModels={availableModels}
                  />
                </div>
              </div>
            </div>

            {/* Bottom: ESP32 Hardware Card & Vision Card with Live Camera Preview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Esp32Card
                device={device}
                currentExpression={expression}
                currentAnimation={animation}
              />
              <VisionCard
                telemetry={visionTelemetry}
                onTriggerGameBreak={() => setShowGameModal(true)}
              />
            </div>
          </div>
        )}

        {/* TAB 2: FULL-HEIGHT CHAT */}
        {activeTab === 'chat' && (
          <div className="h-[calc(100vh-180px)]">
            <ChatWindow
              messages={messages}
              onSendMessage={handleSendMessage}
              onClearChat={handleClearChat}
              isThinking={isThinking}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              availableModels={availableModels}
            />
          </div>
        )}

        {/* TAB 3: SETTINGS & PRIVACY */}
        {activeTab === 'settings' && (
          <div className="space-y-6">
            <TopologyMap status={systemStatus} />
            <PrivacyToggles />
          </div>
        )}
      </main>

      {/* Polite Game Break Dialog (Never interrupts intense focus abruptly) */}
      {showGameModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4 animate-in fade-in zoom-in duration-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-2xl shadow-lg shadow-indigo-900/40">
                🎮
              </div>
              <div>
                <h3 className="font-bold text-base text-white">Momo's Game Break</h3>
                <span className="text-xs text-emerald-400 font-mono">Mindful Recharging</span>
              </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">
              {gamePromptMessage}
            </p>

            {/* Select Game */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-slate-400 uppercase tracking-wider block">
                Choose a Game
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: '2048', name: '2048', icon: '🔢' },
                  { id: 'pacman', name: 'Pacman', icon: '🟡' },
                  { id: 'wordle', name: 'Wordle', icon: '🟩' },
                ].map((g) => (
                  <button
                    key={g.id}
                    onClick={() => setSelectedGame(g.id)}
                    className={`p-2.5 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1 transition-all ${
                      selectedGame === g.id
                        ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300 shadow-md'
                        : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <span className="text-lg">{g.icon}</span>
                    <span>{g.name}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <p>✨ Momo will use PyAutoGUI & Playwright to center the game canvas on screen.</p>
              <p>🗣️ Momo will cheer you on with voice motivation as you play!</p>
            </div>

            {/* Modal Actions */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                onClick={() => setShowGameModal(false)}
                className="py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
              >
                Keep Working / Later
              </button>
              <button
                onClick={handleAcceptGameBreak}
                className="py-2.5 px-4 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-500 hover:to-indigo-500 text-white shadow-lg shadow-emerald-900/40 transition-all font-bold"
              >
                🎮 Let's Play!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
