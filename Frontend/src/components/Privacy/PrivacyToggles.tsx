import React, { useState, useEffect } from 'react';
import { PrivacySettings } from '../../types/momo';
import { fetchPrivacySettings, updatePrivacySettings, wipeMemories } from '../../services/api';

export const PrivacyToggles: React.FC = () => {
  const [settings, setSettings] = useState<PrivacySettings>({
    camera_enabled: false,
    microphone_enabled: false,
    memory_enabled: true,
    activity_tracking_enabled: false,
  });
  const [wiped, setWiped] = useState(false);

  useEffect(() => {
    fetchPrivacySettings()
      .then(setSettings)
      .catch((e) => console.error('Failed to load privacy settings', e));
  }, []);

  const handleToggle = async (key: keyof PrivacySettings) => {
    const updated = { ...settings, [key]: !settings[key] };
    setSettings(updated);
    try {
      const saved = await updatePrivacySettings({ [key.replace('_enabled', '')]: updated[key] });
      setSettings(saved);
    } catch (e) {
      console.error('Failed to update setting', e);
    }
  };

  const handleWipe = async () => {
    if (!confirm('Are you sure you want to delete all stored long-term memories? This cannot be undone.')) {
      return;
    }
    try {
      await wipeMemories();
      setWiped(true);
      setTimeout(() => setWiped(false), 3000);
    } catch (e) {
      console.error('Failed to wipe memory', e);
    }
  };

  return (
    <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-md space-y-6">
      <div className="pb-3 border-b border-slate-800">
        <h3 className="text-base font-semibold text-slate-100">Privacy & Permission Controls</h3>
        <p className="text-xs text-slate-400">
          MOMO is local-first. Sensors and memory never activate or upload data without your explicit permission.
        </p>
      </div>

      <div className="space-y-4">
        {/* Memory Toggle */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div>
            <div className="text-sm font-medium text-slate-200">Long-Term Memory</div>
            <div className="text-xs text-slate-400">Allows MOMO to remember preferences and conversation facts locally.</div>
          </div>
          <button
            onClick={() => handleToggle('memory_enabled')}
            className={`w-12 h-6 rounded-full p-1 transition-colors ${
              settings.memory_enabled ? 'bg-emerald-600' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                settings.memory_enabled ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Camera Toggle */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div>
            <div className="text-sm font-medium text-slate-200">Laptop Camera (Vision Perception)</div>
            <div className="text-xs text-slate-400">
              When disabled, the camera is never opened and no vision frames are captured.
            </div>
          </div>
          <button
            onClick={() => handleToggle('camera_enabled')}
            className={`w-12 h-6 rounded-full p-1 transition-colors ${
              settings.camera_enabled ? 'bg-emerald-600' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                settings.camera_enabled ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Microphone Toggle */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div>
            <div className="text-sm font-medium text-slate-200">Microphone (Voice Input)</div>
            <div className="text-xs text-slate-400">
              When disabled, audio capture is completely inhibited. Whisper runs strictly locally.
            </div>
          </div>
          <button
            onClick={() => handleToggle('microphone_enabled')}
            className={`w-12 h-6 rounded-full p-1 transition-colors ${
              settings.microphone_enabled ? 'bg-emerald-600' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                settings.microphone_enabled ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Activity Tracking */}
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950 border border-slate-800">
          <div>
            <div className="text-sm font-medium text-slate-200">Desktop Activity & Idle Metrics</div>
            <div className="text-xs text-slate-400">
              Tracks session length and idle duration. Never logs keystrokes or sensitive window content.
            </div>
          </div>
          <button
            onClick={() => handleToggle('activity_tracking_enabled')}
            className={`w-12 h-6 rounded-full p-1 transition-colors ${
              settings.activity_tracking_enabled ? 'bg-emerald-600' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                settings.activity_tracking_enabled ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Memory Wipe Button */}
      <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-500 font-mono">
          Permanently delete all stored facts and preferences from SQLite:
        </span>
        <button
          onClick={handleWipe}
          className="px-4 py-2 bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700 text-xs font-semibold rounded-xl transition-all"
        >
          {wiped ? '✓ Memories Wiped' : 'Wipe All Memory'}
        </button>
      </div>
    </div>
  );
};
