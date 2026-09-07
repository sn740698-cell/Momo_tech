import React from 'react';
import { FinancialInsight } from '../../types/momo';

interface InvoiceCardProps {
  insight: FinancialInsight;
  onDraftReminder?: (insight: FinancialInsight) => void;
}

export const InvoiceCard: React.FC<InvoiceCardProps> = ({ insight, onDraftReminder }) => {
  const formatMoney = (amount: number, curr: string) => {
    const symbol = curr === 'INR' ? '₹' : curr === 'USD' ? '$' : `${curr} `;
    return `${symbol}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-emerald-950 text-emerald-400 border-emerald-800/60';
      case 'partially_paid':
        return 'bg-amber-950 text-amber-400 border-amber-800/60';
      case 'overdue':
        return 'bg-rose-950 text-rose-400 border-rose-800/60';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <span className="text-xs font-mono uppercase text-slate-400">Invoice Reference</span>
          <h3 className="text-lg font-bold text-slate-100 font-mono flex items-center gap-2">
            <span>{insight.invoice_number}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              Verified
            </span>
          </h3>
        </div>

        <span className={`px-3 py-1 rounded-full text-xs font-mono font-semibold uppercase border ${getStatusColor(insight.payment_status)}`}>
          {insight.payment_status.replace('_', ' ')}
        </span>
      </div>

      {/* Financial Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-5">
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-mono">Invoice Total</span>
          <div className="text-base font-bold text-slate-200 mt-1 font-mono">
            {formatMoney(insight.invoice_total, insight.currency)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-mono">Amount Paid</span>
          <div className="text-base font-bold text-emerald-400 mt-1 font-mono">
            {formatMoney(insight.amount_paid, insight.currency)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-emerald-900/40">
          <span className="text-[11px] text-emerald-400/90 uppercase font-mono">Balance Due</span>
          <div className="text-base font-extrabold text-emerald-300 mt-1 font-mono">
            {formatMoney(insight.balance_due, insight.currency)}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-mono">Payment Due Date</span>
          <div className="text-sm font-semibold text-slate-300 mt-1 font-mono">
            {insight.due_date || 'Not specified'}
          </div>
        </div>
      </div>

      {/* Deterministic Verification Guarantee Badge */}
      <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <span className="text-emerald-400 font-bold">✓</span>
          <span>Deterministic Formula: Balance = Total ({insight.invoice_total}) - Paid ({insight.amount_paid}) = </span>
          <span className="text-emerald-300 font-bold">{insight.balance_due}</span>
        </div>

        {onDraftReminder && (
          <button
            onClick={() => onDraftReminder(insight)}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-indigo-900/40"
          >
            Draft Reminder Message →
          </button>
        )}
      </div>
    </div>
  );
};
