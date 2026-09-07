import React from 'react';
import { SystemStatus } from '../../types/momo';

interface TopologyMapProps {
  status: SystemStatus | null;
}

export const TopologyMap: React.FC<TopologyMapProps> = ({ status }) => {
  const nodes = [
    { name: 'React Frontend', online: true, role: 'UI & Avatar Mirror', icon: '💻' },
    { name: 'Django ASGI Core', online: status?.backend ?? true, role: 'Channels & REST', icon: '⚙️' },
    { name: 'LangGraph Supervisors', online: status?.langgraph ?? true, role: 'Multi-Agent Orchestrator', icon: '🧠' },
    { name: 'Ollama LLM Engine', online: status?.ollama ?? false, role: 'Generative Reasoning', icon: '🦙' },
    { name: 'BERT Analysis', online: status?.bert ?? true, role: 'Sentence Contextual NLP', icon: '🔬' },
    { name: 'DistilBERT Embeddings', online: status?.distilbert ?? true, role: 'Dense Semantic Vectors', icon: '📐' },
    { name: 'ChromaDB Vector Store', online: status?.chromadb ?? true, role: 'Local Document Retrieval', icon: '📚' },
    { name: 'ESP32 Physical Body', online: status?.esp32 ?? false, role: 'OLED / Servos / LED', icon: '🤖' },
  ];

  const gpuInfo = status?.gpu_telemetry;

  return (
    <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-md space-y-6">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-base font-semibold text-slate-100">Full-Stack MOMO System Topology</h3>
          <p className="text-xs text-slate-400">
            Real-time status of all orchestration layers, local ML models, and hardware companions.
          </p>
        </div>
        <span className="text-xs font-mono text-emerald-400 bg-emerald-950 px-2.5 py-1 rounded-full border border-emerald-800">
          Local-First Architecture
        </span>
      </div>

      {/* Grid of System Nodes */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {nodes.map((n, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xl">{n.icon}</span>
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  n.online ? 'bg-emerald-400 animate-ping' : 'bg-rose-500'
                }`}
              />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">{n.name}</div>
              <div className="text-[10px] font-mono text-slate-400">{n.role}</div>
            </div>
          </div>
        ))}
      </div>

      {/* GPU / VRAM Telemetry Card */}
      {gpuInfo && (
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <span>⚡</span>
              <span>GPU Telemetry ({gpuInfo.device_name || 'NVIDIA RTX 2050'})</span>
            </span>
            <span className="text-emerald-400 font-bold">
              {gpuInfo.cuda_available ? 'CUDA Accelerated' : 'CPU Fallback'}
            </span>
          </div>

          {gpuInfo.total_mb && gpuInfo.total_mb > 0 && (
            <div>
              <div className="flex justify-between text-[11px] font-mono text-slate-400 mb-1">
                <span>VRAM Usage</span>
                <span>
                  {gpuInfo.allocated_mb} MB / {gpuInfo.total_mb} MB (Free: {gpuInfo.free_mb} MB)
                </span>
              </div>
              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, (gpuInfo.allocated_mb! / gpuInfo.total_mb!) * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
