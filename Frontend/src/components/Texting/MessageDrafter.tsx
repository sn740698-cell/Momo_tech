import React, { useState, useEffect } from 'react';
import { FinancialInsight } from '../../types/momo';
import { momoSocket } from '../../services/websocket';

interface MessageDrafterProps {
  initialInsight?: FinancialInsight | null;
}

export const MessageDrafter: React.FC<MessageDrafterProps> = ({ initialInsight }) => {
  const [recipient, setRecipient] = useState('Rahul');
  const [tone, setTone] = useState<'polite' | 'formal' | 'urgent'>('polite');
  const [draft, setDraft] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (initialInsight) {
      generateLocalDraft(initialInsight);
    }
  }, [initialInsight, recipient, tone]);

  const generateLocalDraft = (fi: FinancialInsight) => {
    const symbol = fi.currency === 'INR' ? '₹' : '$';
    let text = '';
    if (tone === 'polite') {
      text = `Hi ${recipient}, this is a gentle reminder that ${symbol}${fi.balance_due.toLocaleString()} remains due on invoice ${fi.invoice_number} (due ${fi.due_date || 'soon'}). Please let us know if you have any questions. Thank you!`;
    } else if (tone === 'formal') {
      text = `Dear ${recipient}, please note that an outstanding balance of ${symbol}${fi.balance_due.toLocaleString()} remains on invoice ${fi.invoice_number}, payable on or before ${fi.due_date || 'the due date'}. Your prompt payment is appreciated.`;
    } else {
      text = `Urgent Notice: The balance of ${symbol}${fi.balance_due.toLocaleString()} on invoice ${fi.invoice_number} is now overdue. Please remit payment immediately to avoid service interruption.`;
    }
    setDraft(text);
  };

  const handleAskMomoToDraft = () => {
    setIsGenerating(true);
    const prompt = `Draft a ${tone} reminder message for ${recipient} about invoice ${initialInsight?.invoice_number || 'INV-1042'} with balance due ₹${initialInsight?.balance_due || 28500}.`;
    momoSocket.sendChatMessage(prompt);

    // Listen for incoming response
    const unsub = momoSocket.on('momo_response', (data) => {
      if (data.draft_text) {
        setDraft(data.draft_text);
      } else if (data.message) {
        setDraft(data.message);
      }
      setIsGenerating(false);
      unsub();
    });

    setTimeout(() => {
      setIsGenerating(false);
      unsub();
    }, 5000);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(draft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-base font-semibold text-slate-100">Texting Agent Message Drafter</h3>
          <p className="text-xs text-slate-400">
            Drafts verified balance-due notifications. You review and approve before copying.
          </p>
        </div>
        <span className="px-2.5 py-1 text-[11px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800 rounded-full">
          User Approval Required
        </span>
      </div>

      {/* Input Parameters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Customer / Recipient Name:</label>
          <input
            type="text"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Message Tone:</label>
          <select
            value={tone}
            onChange={(e: any) => setTone(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
          >
            <option value="polite">Polite & Friendly</option>
            <option value="formal">Formal & Corporate</option>
            <option value="urgent">Urgent & Overdue</option>
          </select>
        </div>
      </div>

      {/* Editable Draft Text Area */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-medium text-slate-400">Generated Message Draft (Editable):</label>
          <button
            onClick={handleAskMomoToDraft}
            disabled={isGenerating}
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors font-mono disabled:opacity-50"
          >
            {isGenerating ? 'MOMO is drafting...' : '✨ Polish with MOMO AI'}
          </button>
        </div>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={4}
          className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500 resize-none font-sans leading-relaxed"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-slate-500 font-mono">
          Strict Policy: MOMO will never send messages externally without your explicit trigger.
        </span>
        <button
          onClick={copyToClipboard}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-emerald-900/40 flex items-center gap-1.5"
        >
          <span>{copied ? '✓ Copied to Clipboard!' : 'Copy Draft'}</span>
        </button>
      </div>
    </div>
  );
};
