import React, { useState } from 'react';
import { ProcessedDocument, FinancialInsight } from '../../types/momo';
import { uploadDocument, uploadRawText } from '../../services/api';

interface DocumentUploaderProps {
  documents: ProcessedDocument[];
  onDocumentProcessed: (doc: ProcessedDocument, insight?: FinancialInsight) => void;
  onSelectDocument: (doc: ProcessedDocument) => void;
}

export const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  documents,
  onDocumentProcessed,
  onSelectDocument,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [filename, setFilename] = useState('invoice.txt');
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    try {
      const res = await uploadDocument(file);
      onDocumentProcessed(res.document, res.financial_insight);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handlePasteSubmit = async () => {
    if (!pastedText.trim()) return;

    setIsUploading(true);
    setError(null);
    try {
      const res = await uploadRawText(pastedText.trim(), filename);
      onDocumentProcessed(res.document, res.financial_insight);
      setPastedText('');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Zone */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md shadow-xl">
        <h3 className="text-base font-semibold text-slate-200 mb-1">
          Document & Invoice Ingestion Pipeline
        </h3>
        <p className="text-xs text-slate-400 mb-4">
          Upload PDF or text invoices. MOMO segments sentences with BERT, extracts financial data deterministically, and indexes chunks into ChromaDB via DistilBERT.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* File Picker */}
          <div className="border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-xl p-6 flex flex-col items-center justify-center text-center transition-all bg-slate-950/40">
            <span className="text-3xl mb-2">📄</span>
            <span className="text-sm font-medium text-slate-300 mb-1">Upload File</span>
            <span className="text-xs text-slate-500 mb-3">PDF, TXT, MD, CSV</span>
            <label className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-md shadow-emerald-900/40 transition-all">
              {isUploading ? 'Processing...' : 'Browse Computer'}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.txt,.md,.json,.csv"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
            </label>
          </div>

          {/* Paste Raw Invoice Text */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">Or Paste Invoice Text:</span>
              <input
                type="text"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                placeholder="Filename..."
                className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-0.5 w-32 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <textarea
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="e.g. Invoice #INV-1042&#10;Total: ₹48,500&#10;Amount Paid: ₹20,000&#10;Due Date: 2026-09-15..."
              rows={4}
              disabled={isUploading}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-emerald-500 resize-none font-mono"
            />
            <button
              onClick={handlePasteSubmit}
              disabled={!pastedText.trim() || isUploading}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-medium self-end transition-all disabled:opacity-50"
            >
              Process Pasted Text
            </button>
          </div>
        </div>
      </div>

      {/* Ingested Document List */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md shadow-xl">
        <h3 className="text-base font-semibold text-slate-200 mb-3 flex items-center justify-between">
          <span>Processed Documents ({documents.length})</span>
          <span className="text-xs font-mono text-emerald-400 font-normal">ChromaDB Indexed</span>
        </h3>

        {documents.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs font-mono">
            No documents processed yet. Upload an invoice above to begin!
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {documents.map((doc) => (
              <div
                key={doc.document_id}
                onClick={() => onSelectDocument(doc)}
                className="py-3 flex items-center justify-between hover:bg-slate-800/40 px-3 rounded-xl cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300 font-mono text-xs">
                    {doc.document_type === 'invoice' ? '🧾' : '📑'}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-slate-200">{doc.filename}</div>
                    <div className="text-xs text-slate-500 flex items-center gap-2 font-mono">
                      <span>ID: {doc.document_id}</span>
                      <span>•</span>
                      <span>{doc.chunks.length} chunks</span>
                      {doc.metadata?.invoice_number && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-400">Inv: {doc.metadata.invoice_number}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                    {doc.processing_status}
                  </span>
                  <span className="text-slate-400 text-sm">→</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
