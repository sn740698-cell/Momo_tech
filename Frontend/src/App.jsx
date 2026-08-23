import { useState, useEffect, useRef } from 'react'

function App() {
  const [activeTab, setActiveTab] = useState('chat') // 'chat' | 'health'
  
  // Backend & Ollama Telemetry
  const [backendStatus, setBackendStatus] = useState({
    loading: true,
    online: false,
    data: null,
    error: null,
    latency: null,
  })

  const [ollamaStatus, setOllamaStatus] = useState({
    loading: true,
    online: false,
    version: null,
    models: [],
    modelNames: [],
    error: null,
  })

  // Chat State
  const [selectedModel, setSelectedModel] = useState('qwen3:4b')
  const [customModelInput, setCustomModelInput] = useState('')
  const [isCustomModel, setIsCustomModel] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('You are MOMO AI, a helpful, precise, and friendly assistant powered by a local LLM.')
  const [showSettings, setShowSettings] = useState(false)
  const [streamMode, setStreamMode] = useState(true)
  const [temperature, setTemperature] = useState(0.7)

  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "👋 Hello! I am your local AI Chatbot running in MOMO. I'm connected to your local Ollama instance and ready to chat using **qwen3:4b** or any other local model you have installed. What would you like to explore today?",
      thinking: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [copiedId, setCopiedId] = useState(null)
  const abortControllerRef = useRef(null)
  const chatBottomRef = useRef(null)
  const textareaRef = useRef(null)

  // API Message Test State (Tab 2)
  const [apiTestInput, setApiTestInput] = useState('')
  const [isSendingApiTest, setIsSendingApiTest] = useState(false)
  const [apiHistory, setApiHistory] = useState([])

  // Fetch Backend Health
  const checkBackendHealth = async () => {
    setBackendStatus((prev) => ({ ...prev, loading: true, error: null }))
    const startTime = performance.now()
    try {
      const response = await fetch('/api/status/')
      const endTime = performance.now()
      const latencyMs = Math.round(endTime - startTime)

      if (!response.ok) {
        throw new Error(`Server returned HTTP status ${response.status}`)
      }

      const data = await response.json()
      setBackendStatus({
        loading: false,
        online: true,
        data: data,
        error: null,
        latency: latencyMs,
      })
    } catch (err) {
      setBackendStatus({
        loading: false,
        online: false,
        data: null,
        error: err.message || 'Unable to connect to Django server',
        latency: null,
      })
    }
  }

  // Fetch Ollama Status
  const checkOllamaHealth = async () => {
    setOllamaStatus((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const response = await fetch('/api/ollama/status/')
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.error || `HTTP ${response.status}`)
      }
      const data = await response.json()
      const models = data.models || []
      const names = data.model_names || []

      setOllamaStatus({
        loading: false,
        online: data.status === 'online',
        version: data.version || 'unknown',
        models: models,
        modelNames: names,
        error: null,
      })

      // Default to qwen3:4b if available
      if (names.includes('qwen3:4b')) {
        setSelectedModel('qwen3:4b')
      } else if (names.length > 0 && !isCustomModel) {
        setSelectedModel(names[0])
      }
    } catch (err) {
      setOllamaStatus({
        loading: false,
        online: false,
        version: null,
        models: [],
        modelNames: [],
        error: err.message || 'Ollama is unreachable on localhost:11434',
      })
    }
  }

  useEffect(() => {
    checkBackendHealth()
    checkOllamaHealth()
  }, [])

  // Auto scroll chat
  useEffect(() => {
    if (activeTab === 'chat') {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isGenerating, activeTab])

  // Handle Send Chat Message
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault()
    const trimmed = inputMessage.trim()
    if (!trimmed || isGenerating) return

    const activeModelName = isCustomModel && customModelInput.trim() ? customModelInput.trim() : selectedModel
    const userTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMsg = {
      id: 'usr_' + Date.now(),
      role: 'user',
      content: trimmed,
      timestamp: userTimestamp,
    }

    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInputMessage('')
    setIsGenerating(true)

    // Setup assistant placeholder
    const assistantId = 'ast_' + Date.now()
    const assistantTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        thinking: '',
        model: activeModelName,
        timestamp: assistantTimestamp,
        isStreaming: true,
      },
    ])

    const chatPayloadMessages = nextMessages
      .filter((m) => m.id !== 'welcome')
      .map((m) => ({
        role: m.role,
        content: m.content,
      }))

    abortControllerRef.current = new AbortController()

    try {
      if (streamMode) {
        // Streaming request
        const response = await fetch('/api/chat/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: activeModelName,
            messages: chatPayloadMessages,
            system_prompt: systemPrompt,
            stream: true,
            temperature: parseFloat(temperature),
          }),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          const errJson = await response.json().catch(() => ({}))
          throw new Error(errJson.error || errJson.message || `Server error (HTTP ${response.status})`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let accumulatedContent = ''
        let accumulatedThinking = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const parsed = JSON.parse(line.slice(6))
                if (parsed.error) {
                  throw new Error(parsed.error)
                }
                if (parsed.thinking) {
                  accumulatedThinking += parsed.thinking
                }
                if (parsed.content) {
                  accumulatedContent += parsed.content
                }
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? {
                          ...msg,
                          content: accumulatedContent,
                          thinking: accumulatedThinking,
                        }
                      : msg
                  )
                )
              } catch (parseErr) {
                if (parseErr.message && !parseErr.message.includes('JSON')) {
                  throw parseErr
                }
              }
            }
          }
        }

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId ? { ...msg, isStreaming: false } : msg
          )
        )
      } else {
        // Non-streaming batch request
        const response = await fetch('/api/chat/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: activeModelName,
            messages: chatPayloadMessages,
            system_prompt: systemPrompt,
            stream: false,
            temperature: parseFloat(temperature),
          }),
          signal: abortControllerRef.current.signal,
        })

        const resData = await response.json()
        if (!response.ok || resData.status === 'error' || resData.status === 'model_not_found' || resData.status === 'offline') {
          throw new Error(resData.error || resData.message || resData.hint || `HTTP ${response.status}`)
        }

        const content = resData.content || resData.message?.content || 'No response content received.'
        const thinking = resData.thinking || resData.message?.thinking || ''
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: content, thinking: thinking, isStreaming: false }
              : msg
          )
        )
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: (msg.content || '') + ' _[Response stopped by user]_', isStreaming: false }
              : msg
          )
        )
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: `⚠️ **Error generating response**:\n${err.message}\n\n*Tip: If '${activeModelName}' is not found, run \`ollama run ${activeModelName}\` in your terminal.*`,
                  error: true,
                  isStreaming: false,
                }
              : msg
          )
        )
      }
    } finally {
      setIsGenerating(false)
      abortControllerRef.current = null
    }
  }

  // Stop Generation
  const handleStopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  // Clear Chat
  const handleClearChat = () => {
    if (window.confirm('Are you sure you want to clear this conversation?')) {
      setMessages([
        {
          id: 'welcome_' + Date.now(),
          role: 'assistant',
          content: "Conversation cleared. Ready for a new topic! Ask me anything.",
          thinking: '',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ])
    }
  }

  // Copy text to clipboard
  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Quick Starter Prompts
  const starterPrompts = [
    "🚀 Tell me about yourself and your capabilities.",
    "🐍 Write a Python function to check palindrome strings.",
    "⚡ Explain how Django and React communicate via REST APIs.",
    "💡 Give me 3 creative project ideas using local LLMs.",
  ]

  // Send Preset in Chat
  const handleSendPrompt = (promptText) => {
    setInputMessage(promptText)
    textareaRef.current?.focus()
  }

  // Handle Send in API Tester Tab
  const handleSendApiTest = async (e) => {
    if (e) e.preventDefault()
    if (!apiTestInput.trim() || isSendingApiTest) return

    setIsSendingApiTest(true)
    const textToSend = apiTestInput.trim()
    const timestamp = new Date().toLocaleTimeString()

    try {
      const response = await fetch('/api/message/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: textToSend }),
      })

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`)
      }

      const resData = await response.json()
      setApiHistory((prev) => [
        {
          id: Date.now(),
          type: 'success',
          time: timestamp,
          sent: textToSend,
          received: resData.response || resData.message || JSON.stringify(resData),
        },
        ...prev,
      ])
      setApiTestInput('')
    } catch (err) {
      setApiHistory((prev) => [
        {
          id: Date.now(),
          type: 'error',
          time: timestamp,
          sent: textToSend,
          received: `Error: ${err.message}`,
        },
        ...prev,
      ])
    } finally {
      setIsSendingApiTest(false)
    }
  }

  // Simple Markdown-style Text Formatter for Bot Messages
  const renderFormattedContent = (content) => {
    if (!content) return null

    // Split by code blocks ```...```
    const parts = content.split(/(```[\s\S]*?```)/g)

    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3).trim().split('\n')
        const firstLine = lines[0].trim()
        const isLang = /^[a-zA-Z0-9_-]+$/.test(firstLine)
        const lang = isLang ? firstLine : ''
        const code = isLang ? lines.slice(1).join('\n') : lines.join('\n')
        const codeBlockId = `code_${index}_${Math.random()}`

        return (
          <div key={index} className="my-3 rounded-xl overflow-hidden border border-slate-700/80 bg-slate-950/90 shadow-md">
            <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-slate-800 text-[11px] text-slate-400 font-mono">
              <span className="font-semibold text-indigo-400 uppercase">{lang || 'CODE'}</span>
              <button
                onClick={() => handleCopy(code, codeBlockId)}
                className="flex items-center gap-1 hover:text-white transition px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-750 cursor-pointer"
              >
                {copiedId === codeBlockId ? '✓ Copied' : 'Copy code'}
              </button>
            </div>
            <pre className="p-3.5 overflow-x-auto text-xs font-mono text-emerald-300 selection:bg-indigo-700">
              <code>{code}</code>
            </pre>
          </div>
        )
      }

      // Format bold, inline code, and line breaks
      const paragraphs = part.split('\n\n')
      return (
        <div key={index} className="space-y-2">
          {paragraphs.map((para, pIdx) => {
            if (!para.trim()) return null

            const lines = para.split('\n').map((line, lIdx) => {
              const inlineFormatted = line
                .split(/(\*\*.*?\*\*|`.*?`)/g)
                .map((segment, sIdx) => {
                  if (segment.startsWith('**') && segment.endsWith('**')) {
                    return <strong key={sIdx} className="font-bold text-white">{segment.slice(2, -2)}</strong>
                  }
                  if (segment.startsWith('`') && segment.endsWith('`')) {
                    return (
                      <code key={sIdx} className="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-[11px] border border-slate-700/60">
                        {segment.slice(1, -1)}
                      </code>
                    )
                  }
                  return segment
                })

              return (
                <span key={lIdx} className="block leading-relaxed">
                  {inlineFormatted}
                </span>
              )
            })

            return <p key={pIdx}>{lines}</p>
          })}
        </div>
      )
    })
  }

  const activeModelDisplay = isCustomModel && customModelInput.trim() ? customModelInput.trim() : selectedModel

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col items-center selection:bg-indigo-500 selection:text-white">
      {/* Top Header */}
      <header className="w-full max-w-5xl px-4 pt-4 pb-3 flex flex-col md:flex-row items-center justify-between gap-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-emerald-400 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-indigo-500/20">
            M
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black tracking-tight text-white">MOMO AI</h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                Ollama &bull; {activeModelDisplay}
              </span>
            </div>
            <p className="text-xs text-slate-400">Local LLM Chatbot &bull; React + Django REST</p>
          </div>
        </div>

        {/* Status Indicators & Navigation Tabs */}
        <div className="flex items-center flex-wrap gap-2">
          {/* Ollama Status Pill */}
          <div
            onClick={checkOllamaHealth}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-semibold cursor-pointer transition ${
              ollamaStatus.loading
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                : ollamaStatus.online
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shadow-sm shadow-emerald-500/20'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
            title="Click to recheck Ollama status"
          >
            <span className={`relative flex h-2 w-2`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                ollamaStatus.loading ? 'bg-amber-400' : ollamaStatus.online ? 'bg-emerald-400' : 'bg-rose-400'
              }`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${
                ollamaStatus.loading ? 'bg-amber-500' : ollamaStatus.online ? 'bg-emerald-500' : 'bg-rose-500'
              }`}></span>
            </span>
            <span>
              {ollamaStatus.loading
                ? 'Checking Ollama...'
                : ollamaStatus.online
                ? `Ollama v${ollamaStatus.version}`
                : 'Ollama Offline'}
            </span>
          </div>

          {/* Django Backend Status Pill */}
          <div
            onClick={checkBackendHealth}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-semibold cursor-pointer transition ${
              backendStatus.loading
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                : backendStatus.online
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
            title="Click to ping Django backend"
          >
            <span className={`h-2 w-2 rounded-full ${
              backendStatus.loading ? 'bg-amber-400' : backendStatus.online ? 'bg-emerald-400' : 'bg-rose-400'
            }`}></span>
            <span>
              {backendStatus.loading
                ? 'Ping Django...'
                : backendStatus.online
                ? `Django (${backendStatus.latency}ms)`
                : 'Django Offline'}
            </span>
          </div>

          {/* Tab Switcher Buttons */}
          <div className="flex bg-slate-800 p-0.5 rounded-xl border border-slate-700/60 ml-1">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'chat'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>🤖 Chatbot</span>
            </button>
            <button
              onClick={() => setActiveTab('health')}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'health'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>⚡ API Console</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="w-full max-w-5xl flex-1 flex flex-col px-4 py-4">
        {/* ===================== TAB 1: AI CHATBOT ===================== */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col bg-slate-800/40 border border-slate-700/60 rounded-2xl shadow-2xl backdrop-blur-md overflow-hidden min-h-[580px]">
            {/* Chat Subheader & Model Selector */}
            <div className="px-4 py-2.5 bg-slate-800/80 border-b border-slate-700/60 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-slate-300 flex items-center gap-1">
                  <span>🧠 Model:</span>
                </span>

                {isCustomModel ? (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={customModelInput}
                      onChange={(e) => setCustomModelInput(e.target.value)}
                      placeholder="e.g. qwen3:4b, llama3..."
                      className="bg-slate-900 border border-indigo-500/60 rounded-lg px-2.5 py-1 text-xs text-white outline-none w-36 font-mono"
                    />
                    <button
                      onClick={() => setIsCustomModel(false)}
                      className="text-[11px] text-slate-400 hover:text-slate-200 underline cursor-pointer"
                    >
                      Presets
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <select
                      value={selectedModel}
                      onChange={(e) => {
                        if (e.target.value === '__custom__') {
                          setIsCustomModel(true)
                          setCustomModelInput(selectedModel)
                        } else {
                          setSelectedModel(e.target.value)
                        }
                      }}
                      className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 font-mono outline-none cursor-pointer focus:border-indigo-500"
                    >
                      <option value="qwen3:4b">qwen3:4b (Installed)</option>
                      {ollamaStatus.modelNames
                        .filter((name) => name !== 'qwen3:4b')
                        .map((name) => (
                          <option key={name} value={name}>
                            {name}
                          </option>
                        ))}
                      <option value="__custom__">+ Enter custom model name...</option>
                    </select>
                  </div>
                )}

                {/* Stream Mode Toggle */}
                <button
                  onClick={() => setStreamMode(!streamMode)}
                  className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium transition cursor-pointer flex items-center gap-1 ${
                    streamMode
                      ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-300'
                      : 'bg-slate-900 border-slate-700 text-slate-400'
                  }`}
                  title="Toggle streaming token-by-token vs full response"
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${streamMode ? 'bg-indigo-400 animate-pulse' : 'bg-slate-500'}`} />
                  {streamMode ? 'Stream: ON' : 'Stream: OFF'}
                </button>
              </div>

              {/* Action Buttons: System Prompt, Clear Chat */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className={`px-2.5 py-1 rounded-lg border text-[11px] transition cursor-pointer flex items-center gap-1 ${
                    showSettings
                      ? 'bg-slate-700 border-slate-600 text-white'
                      : 'bg-slate-900 border-slate-700/60 text-slate-300 hover:bg-slate-750'
                  }`}
                >
                  ⚙️ System Prompt
                </button>
                <button
                  onClick={handleClearChat}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700/60 text-[11px] text-slate-300 hover:text-rose-300 hover:border-rose-700/50 transition cursor-pointer"
                  title="Clear conversation"
                >
                  🗑️ Clear
                </button>
              </div>
            </div>

            {/* System Prompt Drawer (Collapsible) */}
            {showSettings && (
              <div className="p-3 bg-slate-900/90 border-b border-slate-700/70 flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Custom System Instructions &amp; Persona:</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-400">Temp:</span>
                    <input
                      type="range"
                      min="0.1"
                      max="1.5"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(e.target.value)}
                      className="w-20 accent-indigo-500 cursor-pointer"
                    />
                    <span className="text-[11px] font-mono text-indigo-300 w-6">{temperature}</span>
                  </div>
                </div>
                <textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  rows={2}
                  placeholder="Enter system prompt for the model..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {/* Chat Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[520px] custom-scrollbar">
              {messages.map((msg) => {
                const isUser = msg.role === 'user'
                return (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {/* Bot Avatar */}
                    {!isUser && (
                      <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center text-white font-bold text-xs shadow-md shrink-0 mt-0.5">
                        🤖
                      </div>
                    )}

                    <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 text-xs transition ${
                      isUser
                        ? 'bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-tr-sm shadow-md shadow-indigo-600/20'
                        : msg.error
                        ? 'bg-rose-950/40 border border-rose-800/60 text-rose-200 rounded-tl-sm'
                        : 'bg-slate-900/90 border border-slate-700/70 text-slate-200 rounded-tl-sm shadow-lg'
                    }`}>
                      {/* Message Header */}
                      <div className="flex items-center justify-between gap-3 text-[11px] opacity-70 mb-2 border-b border-white/10 pb-1">
                        <span className="font-semibold flex items-center gap-1">
                          {isUser ? 'You' : msg.model ? `MOMO AI (${msg.model})` : 'MOMO AI'}
                        </span>
                        <div className="flex items-center gap-2 font-mono">
                          <span>{msg.timestamp}</span>
                          {!isUser && (msg.content || msg.thinking) && (
                            <button
                              onClick={() => handleCopy(msg.content, msg.id)}
                              className="hover:text-white transition cursor-pointer"
                              title="Copy message"
                            >
                              {copiedId === msg.id ? '✓ Copied' : '📋'}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Optional Reasoning / Thinking process block for Qwen3 */}
                      {!isUser && msg.thinking && (
                        <details className="mb-3 rounded-xl bg-slate-950/70 border border-indigo-900/40 overflow-hidden group">
                          <summary className="px-3 py-1.5 text-[11px] text-indigo-300 font-mono cursor-pointer select-none hover:bg-indigo-950/30 flex items-center gap-1.5">
                            <span>💭 Thought Process ({msg.thinking.split(/\s+/).length} words)</span>
                          </summary>
                          <div className="p-3 text-[11px] text-slate-400 font-mono leading-relaxed border-t border-indigo-950/40 whitespace-pre-wrap max-h-48 overflow-y-auto custom-scrollbar">
                            {msg.thinking}
                          </div>
                        </details>
                      )}

                      {/* Content */}
                      <div className="chat-content leading-relaxed">
                        {isUser ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : msg.content ? (
                          <>
                            {renderFormattedContent(msg.content)}
                            {msg.isStreaming && <span className="typing-cursor" />}
                          </>
                        ) : msg.isStreaming && msg.thinking ? (
                          <div className="flex items-center gap-2 text-indigo-300 py-1">
                            <span className="inline-block animate-spin h-3.5 w-3.5 border-2 border-indigo-400 border-t-transparent rounded-full" />
                            <span className="italic animate-pulse">Reasoning thoughts...</span>
                            <span className="typing-cursor" />
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-indigo-300 py-1">
                            <span className="inline-block animate-spin h-3.5 w-3.5 border-2 border-indigo-400 border-t-transparent rounded-full" />
                            <span className="italic animate-pulse">Thinking with {activeModelDisplay}...</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* User Avatar */}
                    {isUser && (
                      <div className="h-8 w-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200 font-bold text-xs shadow-md shrink-0 mt-0.5">
                        👤
                      </div>
                    )}
                  </div>
                )
              })}
              <div ref={chatBottomRef} />
            </div>

            {/* Quick Starter Prompts (if chat has 1 message) */}
            {messages.length <= 1 && (
              <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-900/40">
                <div className="text-[11px] text-slate-400 mb-1.5 font-medium flex items-center gap-1">
                  <span>💡 Try asking:</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {starterPrompts.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendPrompt(prompt)}
                      className="text-left text-[11px] p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/40 text-slate-300 hover:text-white transition cursor-pointer truncate"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat Input Bar */}
            <div className="p-3 bg-slate-900/95 border-t border-slate-700/60">
              <form onSubmit={handleSendMessage} className="flex gap-2 items-end">
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    placeholder={`Message ${activeModelDisplay}... (Enter to send, Shift+Enter for newline)`}
                    rows={1}
                    disabled={isGenerating}
                    style={{ minHeight: '44px', maxHeight: '140px' }}
                    className="w-full bg-slate-950 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 outline-none resize-none transition disabled:opacity-50"
                  />
                </div>

                {isGenerating ? (
                  <button
                    type="button"
                    onClick={handleStopGenerating}
                    className="h-11 px-4 bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-white rounded-xl text-xs font-semibold shadow-lg shadow-rose-600/30 transition cursor-pointer flex items-center gap-1.5 shrink-0"
                  >
                    <span className="h-2 w-2 rounded-sm bg-white" />
                    Stop
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={!inputMessage.trim()}
                    className="h-11 px-5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 active:from-indigo-700 active:to-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 transition cursor-pointer flex items-center gap-1.5 shrink-0"
                  >
                    <span>Send</span>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </button>
                )}
              </form>
            </div>
          </div>
        )}

        {/* ===================== TAB 2: SYSTEM HEALTH & API TESTER ===================== */}
        {activeTab === 'health' && (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 flex-1">
            {/* Architecture & Server Info (Left Column) */}
            <section className="md:col-span-5 flex flex-col gap-6">
              {/* Architecture Card */}
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-xl backdrop-blur-sm">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  Fullstack Topology
                </h2>
                
                <div className="space-y-3">
                  {/* React 19 */}
                  <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-700/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 font-bold text-xs">
                        React 19
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-white">Frontend Client</div>
                        <div className="text-[11px] text-slate-400">Vite Dev Server</div>
                      </div>
                    </div>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                      :5173
                    </span>
                  </div>

                  <div className="flex justify-center text-slate-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                    </svg>
                  </div>

                  {/* Django */}
                  <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-700/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 font-bold text-xs">
                        Django
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-white">Backend Gateway</div>
                        <div className="text-[11px] text-slate-400">REST API + Streaming</div>
                      </div>
                    </div>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-slate-700">
                      :8000
                    </span>
                  </div>

                  <div className="flex justify-center text-slate-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                    </svg>
                  </div>

                  {/* Ollama Local LLM */}
                  <div className="p-3 bg-slate-900/80 rounded-xl border border-slate-700/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 font-bold text-xs">
                        Ollama
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-white">Local LLM Engine</div>
                        <div className="text-[11px] text-slate-400">{activeModelDisplay}</div>
                      </div>
                    </div>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-purple-300 border border-slate-700">
                      :11434
                    </span>
                  </div>
                </div>
              </div>

              {/* Ollama & Models Info */}
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-xl backdrop-blur-sm">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Ollama Models
                  </span>
                  <button
                    onClick={checkOllamaHealth}
                    className="text-[11px] text-indigo-400 hover:underline cursor-pointer"
                  >
                    Refresh
                  </button>
                </h2>

                {ollamaStatus.loading ? (
                  <div className="text-xs text-slate-400 py-3 text-center animate-pulse">
                    Scanning Ollama models...
                  </div>
                ) : ollamaStatus.online ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-700/40">
                      <span className="text-slate-400">Ollama Version:</span>
                      <span className="font-semibold text-slate-200">v{ollamaStatus.version}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-700/40">
                      <span className="text-slate-400">Installed Models:</span>
                      <span className="font-semibold text-indigo-300">{ollamaStatus.models.length} model(s)</span>
                    </div>
                    <div className="pt-2">
                      <span className="text-slate-400 block mb-1 text-[11px]">Detected Models:</span>
                      <div className="space-y-1 max-h-32 overflow-y-auto custom-scrollbar">
                        {ollamaStatus.models.map((m, idx) => (
                          <div
                            key={idx}
                            onClick={() => {
                              setSelectedModel(m.name)
                              setIsCustomModel(false)
                              setActiveTab('chat')
                            }}
                            className="p-2 rounded-lg bg-slate-900/80 hover:bg-slate-750 border border-slate-700/40 flex items-center justify-between cursor-pointer transition"
                          >
                            <span className="font-mono font-semibold text-slate-200">{m.name}</span>
                            <span className="text-[10px] text-slate-400">
                              {m.size ? `${(m.size / 1e9).toFixed(1)} GB` : 'local'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-rose-950/30 border border-rose-800/40 rounded-xl text-xs text-rose-300">
                    <p className="font-semibold mb-1">Ollama Not Running</p>
                    <p className="text-[11px] text-slate-400">
                      Start Ollama Desktop or run <code className="bg-slate-900 px-1 py-0.5 rounded text-indigo-300">ollama serve</code> in your terminal.
                    </p>
                  </div>
                )}
              </div>
            </section>

            {/* Live API Payload Test Console (Right Column) */}
            <section className="md:col-span-7 flex flex-col gap-6">
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-xl backdrop-blur-sm">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
                  <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Live REST API Payload Test
                </h2>

                <form onSubmit={handleSendApiTest} className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                      Send Payload to Django Backend:
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={apiTestInput}
                        onChange={(e) => setApiTestInput(e.target.value)}
                        placeholder="Type a message to test Django endpoint..."
                        className="flex-1 bg-slate-900 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 outline-none transition"
                      />
                      <button
                        type="submit"
                        disabled={isSendingApiTest || !apiTestInput.trim()}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 transition cursor-pointer flex items-center gap-1.5"
                      >
                        {isSendingApiTest ? (
                          <span className="inline-block animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                        ) : (
                          'Send'
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Quick Presets */}
                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    <span className="text-[11px] text-slate-400 mr-1">Presets:</span>
                    {[
                      'Hello Django! 🚀',
                      'Ping from React ⚛️',
                      'Ollama + Qwen check 🧠',
                    ].map((preset) => (
                      <button
                        key={preset}
                        type="button"
                        onClick={() => setApiTestInput(preset)}
                        className="text-[11px] px-2 py-0.5 rounded-md bg-slate-700/50 hover:bg-slate-700 text-slate-300 border border-slate-700 transition cursor-pointer"
                      >
                        {preset}
                      </button>
                    ))}
                  </div>
                </form>
              </div>

              {/* Activity Log Card */}
              <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 shadow-xl backdrop-blur-sm flex-1 flex flex-col min-h-[220px]">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    REST Response Log
                  </h2>
                  {apiHistory.length > 0 && (
                    <button
                      onClick={() => setApiHistory([])}
                      className="text-[11px] text-slate-400 hover:text-slate-200 transition cursor-pointer"
                    >
                      Clear log
                    </button>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto max-h-[260px] space-y-2 pr-1 custom-scrollbar">
                  {apiHistory.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 text-xs">
                      <svg className="w-8 h-8 mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                      No messages sent yet. Send a payload above to test live two-way communication!
                    </div>
                  ) : (
                    apiHistory.map((item) => (
                      <div
                        key={item.id}
                        className={`p-3 rounded-xl border text-xs transition ${
                          item.type === 'success'
                            ? 'bg-slate-900/90 border-slate-700/60'
                            : 'bg-rose-950/20 border-rose-800/40'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                          <span className="font-semibold text-indigo-300">Sent: "{item.sent}"</span>
                          <span className="font-mono">{item.time}</span>
                        </div>
                        <div className={`mt-1 font-mono text-[11px] ${item.type === 'success' ? 'text-emerald-300' : 'text-rose-400'}`}>
                          ↳ {item.received}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </section>
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer className="w-full max-w-5xl px-4 py-3 border-t border-slate-800/80 text-center text-xs text-slate-500 flex flex-col md:flex-row items-center justify-between gap-2">
        <span>MOMO Local AI Platform &bull; React 19 + Django 6.1 + Ollama (Qwen)</span>
        <span className="font-mono text-[11px] text-slate-400">Launcher: <code className="text-indigo-400 font-bold">start.bat</code></span>
      </footer>
    </div>
  )
}

export default App