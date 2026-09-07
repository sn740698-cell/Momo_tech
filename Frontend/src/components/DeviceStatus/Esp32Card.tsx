import React, { useState } from 'react';
import { DeviceTelemetry, MomoExpression, MomoAnimation } from '../../types/momo';
import { momoSocket } from '../../services/websocket';

interface Esp32CardProps {
  device?: DeviceTelemetry | null;
  currentExpression?: MomoExpression;
  currentAnimation?: MomoAnimation;
}

export const Esp32Card: React.FC<Esp32CardProps> = ({
  device,
  currentExpression = 'normal',
  currentAnimation = 'none',
}) => {
  const [panAngle, setPanAngle] = useState(90);
  const [tiltAngle, setTiltAngle] = useState(90);

  const isOnline = device?.status === 'online';

  const sendTestCommand = (expr: MomoExpression, anim: MomoAnimation, led: string = 'blink') => {
    momoSocket.sendDeviceCommand(expr, anim, led);
  };

  const handleManualServo = (pan: number, tilt: number) => {
    setPanAngle(pan);
    setTiltAngle(tilt);
    momoSocket.send({
      type: 'device_command',
      expression: currentExpression,
      animation: 'none',
      servo: { pan, tilt, action: 'hold' },
    });
  };

  return (
    <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-md space-y-6">
      {/* Header with Connection Pill */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-slate-100">ESP32 Physical MOMO (Robotic Body)</h3>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold uppercase flex items-center gap-1.5 border ${
                isOnline
                  ? 'bg-emerald-950 text-emerald-400 border-emerald-800/60'
                  : 'bg-rose-950 text-rose-400 border-rose-800/60'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'}`}
              />
              {isOnline ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Synchronizes SSD1306 OLED, SG90 pan/tilt servos, status LED, and interactive pushbutton.
          </p>
        </div>

        <div className="text-right font-mono text-xs text-slate-400">
          <div>ID: {device?.device_id || 'momo-01'}</div>
          <div className="text-[11px] text-slate-500">
            {device?.connection_type === 'usb_serial'
              ? `USB-C Serial (${device.port || 'COM'})`
              : 'Wi-Fi WebSocket'}
          </div>
        </div>
      </div>

      {/* Simulated OLED & Actuator Dashboard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Simulated SSD1306 OLED Screen */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center">
          <span className="text-[11px] font-mono text-slate-400 uppercase mb-2">
            Physical OLED Display (128x64)
          </span>
          <div className="w-48 h-24 rounded-lg bg-black border-2 border-emerald-500/40 p-2 flex flex-col items-center justify-center font-mono text-emerald-400 text-lg shadow-[0_0_15px_rgba(16,185,129,0.2)]">
            <span className="text-2xl font-bold tracking-wider">
              {currentExpression === 'happy'
                ? '( ^ ᴗ ^ )'
                : currentExpression === 'thinking'
                ? '( • ᴗ • ? )'
                : currentExpression === 'excited'
                ? '( ★ ᴗ ★ )'
                : currentExpression === 'sleepy'
                ? '( - ᴗ - )'
                : currentExpression === 'confused'
                ? '( • _ • ? )'
                : currentExpression === 'sad'
                ? '( v _ v )'
                : '( ● ᴗ ● )'}
            </span>
            <span className="text-[10px] text-emerald-600 mt-2 uppercase tracking-widest">
              OLED MIRROR: {currentExpression}
            </span>
          </div>
        </div>

        {/* Pan / Tilt Servo Gauges */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <span className="text-[11px] font-mono text-slate-400 uppercase block">
            SG90 Pan / Tilt Servo Angles
          </span>

          <div>
            <div className="flex justify-between text-xs font-mono text-slate-300 mb-1">
              <span>Pan Angle (Horizontal)</span>
              <span>{panAngle}°</span>
            </div>
            <input
              type="range"
              min="30"
              max="150"
              value={panAngle}
              onChange={(e) => handleManualServo(Number(e.target.value), tiltAngle)}
              className="w-full accent-emerald-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs font-mono text-slate-300 mb-1">
              <span>Tilt Angle (Vertical)</span>
              <span>{tiltAngle}°</span>
            </div>
            <input
              type="range"
              min="45"
              max="135"
              value={tiltAngle}
              onChange={(e) => handleManualServo(panAngle, Number(e.target.value))}
              className="w-full accent-emerald-500"
            />
          </div>
        </div>
      </div>

      {/* Manual Hardware Animation Testers */}
      <div>
        <span className="text-xs font-medium text-slate-400 block mb-2 font-mono uppercase">
          Hardware Motion Allowlist Testers:
        </span>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => sendTestCommand('happy', 'nod', 'blink')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-all border border-slate-700"
          >
            Nod Head
          </button>
          <button
            onClick={() => sendTestCommand('thinking', 'tilt_left', 'pulsing')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-all border border-slate-700"
          >
            Tilt Left
          </button>
          <button
            onClick={() => sendTestCommand('playful', 'tilt_right', 'pulsing')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-all border border-slate-700"
          >
            Tilt Right
          </button>
          <button
            onClick={() => sendTestCommand('excited', 'celebrate', 'blink')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-all border border-slate-700"
          >
            Celebrate (Wobble)
          </button>
          <button
            onClick={() => sendTestCommand('sleepy', 'none', 'off')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-all border border-slate-700"
          >
            Sleep Mode
          </button>
        </div>
      </div>
    </div>
  );
};
