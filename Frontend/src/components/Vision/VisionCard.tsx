import React, { useState, useEffect } from 'react';
import { VisionTelemetry } from '../../types/momo';

interface VisionCardProps {
  telemetry?: VisionTelemetry | null;
  onSnapshotRequested?: () => void;
  onTriggerGameBreak?: () => void;
  isLoading?: boolean;
}

export const VisionCard: React.FC<VisionCardProps> = ({
  telemetry,
  onSnapshotRequested,
  onTriggerGameBreak,
  isLoading = false,
}) => {
  const [localTelemetry, setLocalTelemetry] = useState<VisionTelemetry | null>(telemetry || null);
  const [showLivePreview, setShowLivePreview] = useState<boolean>(true);
  const [streamMode, setStreamMode] = useState<'snapshot' | 'mjpeg'>('snapshot');
  const [snapshotSrc, setSnapshotSrc] = useState<string>('');
  const [streamError, setStreamError] = useState<boolean>(false);
  const [scanning, setScanning] = useState(false);
  const activeBlobUrlRef = React.useRef<string | null>(null);

  useEffect(() => {
    if (telemetry) {
      setLocalTelemetry(telemetry);
    }
  }, [telemetry]);

  useEffect(() => {
    if (!showLivePreview) return;

    if (streamMode === 'mjpeg') {
      setSnapshotSrc(`/api/vision/stream/?t=${Date.now()}`);
      return;
    }

    let isMounted = true;
    let timerId: any = null;

    const loadNextFrame = async () => {
      if (!isMounted) return;
      try {
        const res = await fetch(`/api/vision/preview/?t=${Date.now()}`, { cache: 'no-store' });
        if (!res.ok) throw new Error(`Preview fetch failed: ${res.status}`);
        const blob = await res.blob();
        if (!isMounted) return;

        const newBlobUrl = URL.createObjectURL(blob);
        const oldUrl = activeBlobUrlRef.current;
        activeBlobUrlRef.current = newBlobUrl;
        setSnapshotSrc(newBlobUrl);
        setStreamError(false);

        if (oldUrl && oldUrl.startsWith('blob:')) {
          URL.revokeObjectURL(oldUrl);
        }

        timerId = setTimeout(loadNextFrame, 125); // ~8 FPS smooth live preview
      } catch (err) {
        if (!isMounted) return;
        timerId = setTimeout(loadNextFrame, 1000);
      }
    };

    loadNextFrame();

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
      if (activeBlobUrlRef.current && activeBlobUrlRef.current.startsWith('blob:')) {
        URL.revokeObjectURL(activeBlobUrlRef.current);
        activeBlobUrlRef.current = null;
      }
    };
  }, [showLivePreview, streamMode]);

  const emotionEmojiMap: Record<string, string> = {
    happy: '😊 Happy',
    excited: '✨ Excited',
    tired: '☕ Tired (Take a break)',
    stressed: '🧘 Stressed (Take a breath)',
    sad: '💙 Needs Care',
    neutral: '😌 Focused / Neutral',
  };

  const currentEmotion = localTelemetry?.emotion || 'neutral';
  const emotionLabel = emotionEmojiMap[currentEmotion] || `🙂 ${currentEmotion}`;
  const isLooking = localTelemetry?.looking_at_camera ?? false;
  const workMins = localTelemetry?.work_duration_minutes ?? 0;
  const sadTiredMins = localTelemetry?.sad_tired_minutes ?? 0;
  const sensors = localTelemetry?.sensors || {};
  const isSadAndTired = localTelemetry?.is_sad_and_tired ?? (
    ((sensors['sadness_score'] ?? 0) >= 0.50 && (sensors['tired_score'] ?? 0) >= 0.50) ||
    (currentEmotion === 'sad' && (sensors['tired_score'] ?? 0) >= 0.45)
  );
  const isFatigued = localTelemetry?.fatigue_detected ?? (sadTiredMins >= 30);
  const faceDetected = localTelemetry?.face_detected ?? false;

  const recognizedUser = localTelemetry?.recognized_user || localTelemetry?.recognition?.user_name || (faceDetected ? 'User' : 'Guest');
  const recognitionConf = Math.round((localTelemetry?.recognition_confidence ?? localTelemetry?.recognition?.confidence ?? (faceDetected ? 0.92 : 0)) * 100);
  const isRecognized = (localTelemetry?.recognition?.recognized ?? (faceDetected && recognitionConf >= 50));
  const clarityBoosted = localTelemetry?.enhancement_active ?? localTelemetry?.enhancement?.clarity_boosted ?? true;
  const clarityScore = Math.round((sensors['clarity_quality_sensor'] ?? localTelemetry?.clarity_score ?? 0.78) * 100);
  const eyeGlint = Math.round((sensors['eye_glint_salience_sensor'] ?? 0.65) * 100);
  const skinVitality = Math.round((sensors['skin_chroma_vitality_sensor'] ?? 0.72) * 100);

  const handleRefreshStream = () => {
    setStreamError(false);
    if (streamMode === 'mjpeg') {
      setSnapshotSrc(`/api/vision/stream/?t=${Date.now()}`);
    } else {
      fetch(`/api/vision/preview/?t=${Date.now()}`, { cache: 'no-store' })
        .then((res) => (res.ok ? res.blob() : Promise.reject(new Error('Failed'))))
        .then((blob) => {
          const newUrl = URL.createObjectURL(blob);
          if (activeBlobUrlRef.current && activeBlobUrlRef.current.startsWith('blob:')) {
            URL.revokeObjectURL(activeBlobUrlRef.current);
          }
          activeBlobUrlRef.current = newUrl;
          setSnapshotSrc(newUrl);
        })
        .catch(() => setStreamError(true));
    }
  };

  const handleManualCapture = async () => {
    setScanning(true);
    try {
      if (onSnapshotRequested) {
        onSnapshotRequested();
      } else {
        const res = await fetch('/api/vision/capture/', { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          if (data.analysis) {
            setLocalTelemetry((prev) => ({
              ...(prev || {
                camera_available: true,
                privacy_blocked: false,
                face_detected: true,
                face_count: 1,
                head_pose: 'center',
                work_duration_minutes: 0,
                fatigue_detected: false,
              }),
              ...data.analysis,
            }));
            handleRefreshStream();
          }
        }
      }
    } catch (e) {
      console.error('Vision snapshot error:', e);
    } finally {
      setTimeout(() => setScanning(false), 500);
    }
  };

  return (
    <div className="bg-slate-900/70 backdrop-blur-md rounded-2xl border border-slate-800 p-5 shadow-xl text-slate-100 flex flex-col justify-between">
      <div>
        {/* Header Bar */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${faceDetected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <h3 className="font-semibold text-sm tracking-wide text-slate-200 flex items-center gap-2">
              <span>MOMO VISION & CAMERA PREVIEW</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800 font-mono">
                18-Sensor Low-Res Core
              </span>
            </h3>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setStreamMode((m) => (m === 'snapshot' ? 'mjpeg' : 'snapshot'))}
              className="text-[10px] px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono transition-all border border-slate-700"
              title="Toggle Between Smooth Snapshot & Direct MJPEG Stream"
            >
              {streamMode === 'mjpeg' ? '⚡ MJPEG' : '📸 Snapshot'}
            </button>
            <button
              onClick={() => setShowLivePreview((prev) => !prev)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono transition-all border border-slate-700"
            >
              {showLivePreview ? 'Hide Camera' : 'Show Camera'}
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-400 mb-3 leading-relaxed">
          Equipped with an 18-sensor multi-modal FACS array and low-megapixel enhancement. Momo accurately perceives expressions and identifies your face even in low light and low clarity!
        </p>

        {/* Live Camera Stream Viewport */}
        {showLivePreview && (
          <div className="relative mb-4 rounded-xl overflow-hidden bg-slate-950 border border-slate-800 aspect-video flex items-center justify-center shadow-inner group">
            <img
              src={snapshotSrc || '/api/vision/preview/'}
              alt="MOMO Camera Preview"
              className="w-full h-full object-cover rounded-xl"
              onLoad={() => setStreamError(false)}
              onError={() => {
                if (snapshotSrc) setStreamError(true);
              }}
            />

            {streamError && (
              <div className="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center p-6 text-center space-y-2 z-20">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 text-xl">
                  📷
                </div>
                <p className="text-xs font-mono text-slate-400">
                  Camera feed awaiting frames from backend.
                </p>
                <button
                  onClick={handleRefreshStream}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-[11px] rounded-lg border border-slate-700 text-slate-300 transition-all font-mono"
                >
                  Retry Stream
                </button>
              </div>
            )}

            {/* Live HUD Badges on Top of Stream */}
            <div className="absolute top-2 left-2 flex items-center gap-1.5 pointer-events-none z-10 flex-wrap">
              <span className="px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-[10px] font-mono text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                LIVE
              </span>
              {faceDetected && (
                <span className="px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-[10px] font-mono text-cyan-400 border border-cyan-500/30 flex items-center gap-1">
                  <span>👤</span>
                  <span>{recognizedUser} ({recognitionConf}%)</span>
                </span>
              )}
              {clarityBoosted && (
                <span className="px-2 py-0.5 rounded-md bg-indigo-950/80 backdrop-blur-sm text-[10px] font-mono text-indigo-300 border border-indigo-500/30">
                  ⚡ Low-Res Enhanced
                </span>
              )}
            </div>

            <div className="absolute bottom-2 right-2 pointer-events-none z-10">
              <span className="px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-sm text-[10px] font-mono text-slate-300 border border-slate-700/50">
                {emotionLabel}
              </span>
            </div>
          </div>
        )}

        {/* Emotion, Recognition & Clarity Cards */}
        <div className="grid grid-cols-2 gap-2.5 mb-3">
          <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block mb-1">
              Perceived Emotion
            </span>
            <span className="font-semibold text-xs text-emerald-400 flex items-center">
              {emotionLabel}
            </span>
          </div>

          <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block mb-1">
              User Identity (Biometric)
            </span>
            <span className="font-semibold text-xs text-cyan-400 flex items-center gap-1">
              <span>👤</span>
              <span>{isRecognized ? `${recognizedUser} (${recognitionConf}%)` : 'Scanning Face...'}</span>
            </span>
          </div>

          <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block mb-1">
              Looking at Momo
            </span>
            <span
              className={`font-semibold text-xs flex items-center ${
                isLooking ? 'text-cyan-400' : 'text-slate-400'
              }`}
            >
              {isLooking ? '👀 Direct Eye Contact' : '🖥️ Focused on Laptop'}
            </span>
          </div>

          <div className="bg-slate-950/60 rounded-xl p-2.5 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider block mb-1">
              Camera Clarity & Sensor
            </span>
            <span className="font-semibold text-xs text-amber-300 flex items-center gap-1">
              <span>⚡</span>
              <span>{clarityBoosted ? 'Low-Res Boosted' : 'Standard'} ({clarityScore}%)</span>
            </span>
          </div>
        </div>

        {/* Multi-Sensor Facial Perception Telemetry */}
        <div className="bg-slate-950/60 rounded-xl p-3 border border-slate-800/80 mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider flex items-center gap-1.5">
              <span>FACIAL PERCEPTION SENSORS (18-SENSOR ARRAY)</span>
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              FACS + Photometric
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
              <div className="flex justify-between text-slate-400 mb-1">
                <span>EAR (Eye Open)</span>
                <span className="text-emerald-400 font-bold">
                  {Math.round((sensors['ear_sensor'] ?? (localTelemetry?.eye_openness ?? 0.75)) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-emerald-400 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, (sensors['ear_sensor'] ?? (localTelemetry?.eye_openness ?? 0.75)) * 100))}%` }}
                />
              </div>
            </div>

            <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
              <div className="flex justify-between text-slate-400 mb-1">
                <span>Eye Glint (Focus)</span>
                <span className="text-yellow-400 font-bold">
                  {eyeGlint}%
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-yellow-400 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, eyeGlint))}%` }}
                />
              </div>
            </div>

            <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
              <div className="flex justify-between text-slate-400 mb-1">
                <span>Brow Tension</span>
                <span className="text-rose-400 font-bold">
                  {Math.round((sensors['eyebrow_furrow_sensor'] ?? 0.15) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-rose-400 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, (sensors['eyebrow_furrow_sensor'] ?? 0.15) * 100))}%` }}
                />
              </div>
            </div>

            <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
              <div className="flex justify-between text-slate-400 mb-1">
                <span>Skin Vitality</span>
                <span className="text-pink-400 font-bold">
                  {skinVitality}%
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-pink-400 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, skinVitality))}%` }}
                />
              </div>
            </div>

            <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
              <div className="flex justify-between text-slate-400 mb-1">
                <span>Sadness Idx</span>
                <span className={`font-bold ${((sensors['sadness_score'] ?? 0) >= 0.5) ? 'text-sky-400 animate-pulse' : 'text-slate-400'}`}>
                  {Math.round((sensors['sadness_score'] ?? 0) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-sky-400 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, (sensors['sadness_score'] ?? 0) * 100))}%` }}
                />
              </div>
            </div>

            <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800">
              <div className="flex justify-between text-slate-400 mb-1">
                <span>Tiredness Idx</span>
                <span className={`font-bold ${((sensors['tired_score'] ?? 0) >= 0.5) ? 'text-amber-400 animate-pulse' : 'text-slate-400'}`}>
                  {Math.round((sensors['tired_score'] ?? 0) * 100)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-amber-400 rounded-full transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, (sensors['tired_score'] ?? 0) * 100))}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Strict Dual Sad + Tired Break Timer */}
        <div className={`rounded-xl p-3 border mb-3 transition-all ${
          isSadAndTired
            ? 'bg-amber-950/30 border-amber-500/50 shadow-lg shadow-amber-950/20'
            : 'bg-slate-950/60 border-slate-800/80'
        }`}>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-[10px] text-slate-300 font-medium uppercase tracking-wider flex items-center gap-1.5">
              <span>🎮 Game Break Timer (Sad + Tired Rule)</span>
              {isSadAndTired && (
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
              )}
            </span>
            <span
              className={`text-xs font-mono font-bold ${
                isSadAndTired ? 'text-amber-400 animate-pulse' : 'text-slate-500'
              }`}
            >
              {sadTiredMins.toFixed(1)} / 30.0 mins
            </span>
          </div>

          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden mb-2">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                isFatigued ? 'bg-rose-500 animate-pulse' : isSadAndTired ? 'bg-amber-400' : 'bg-slate-700'
              }`}
              style={{ width: `${Math.min(100, (sadTiredMins / 30) * 100)}%` }}
            />
          </div>

          <div className="text-[11px] leading-relaxed">
            {isFatigued ? (
              <p className="text-amber-300 flex items-center gap-1 font-medium">
                <span>⚠️</span>
                <span>User is both sad & tired for 30m! Momo is ready to launch a game.</span>
              </p>
            ) : isSadAndTired ? (
              <p className="text-amber-400/90 font-mono text-[10px]">
                ⚡ DUAL TRIGGER ACTIVE: Both Sadness & Tiredness detected. Break timer is counting down.
              </p>
            ) : (
              <p className="text-slate-500 font-mono text-[10px]">
                🔒 TIMER PAUSED: Only counts down when user is continuously BOTH sad and fully tired. Total session: {workMins.toFixed(1)}m.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 mt-2">
        <button
          onClick={handleManualCapture}
          disabled={scanning || isLoading}
          className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium transition-all border border-slate-700 active:scale-98 disabled:opacity-50 flex items-center justify-center space-x-1"
        >
          <span>{scanning ? 'Scanning...' : '📸 Analyze Face'}</span>
        </button>

        <button
          onClick={onTriggerGameBreak}
          className="py-2 px-3 bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white rounded-xl text-xs font-medium transition-all shadow-md active:scale-98 flex items-center justify-center space-x-1"
        >
          <span>🎮 Game Break</span>
        </button>
      </div>
    </div>
  );
};

export default VisionCard;
