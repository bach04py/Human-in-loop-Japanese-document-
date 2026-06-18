'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  FileText,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from 'lucide-react';
import { apiService, ChatMessage, StoredDocument } from '../../lib/api';

function documentLabel(doc: StoredDocument): string {
  const company = doc.data?.company;
  const invoiceId = doc.data?.invoice_id;
  const parts: string[] = [doc.document_id];
  if (typeof company === 'string' && company.trim()) parts.push(company);
  else if (typeof invoiceId === 'string' && invoiceId.trim()) parts.push(invoiceId);
  return parts.join(' · ');
}

export default function ChatPage() {
  const [documents, setDocuments] = useState<StoredDocument[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  const selectedDoc = documents.find((d) => d.document_id === selectedId);

  const loadDocuments = async () => {
    setLoadingDocs(true);
    setError(null);
    try {
      const docs = await apiService.listExtractedDocuments();
      setDocuments(docs);
      if (docs.length > 0 && !docs.some((d) => d.document_id === selectedId)) {
        setSelectedId(docs[0].document_id);
      }
    } catch {
      setError('Could not load extracted documents. Is the backend running?');
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Reset the conversation whenever the user picks a different document.
  useEffect(() => {
    setMessages([]);
    setError(null);
  }, [selectedId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, sending]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || !selectedId || sending) return;

    const userMessage: ChatMessage = { role: 'user', content: trimmed };
    const history = messages;
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setSending(true);
    setError(null);

    try {
      const res = await apiService.chatWithDocument(selectedId, trimmed, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);
    } catch {
      setError('The chat request failed. Check the backend and local LLM (Ollama).');
      setMessages((prev) => prev.slice(0, -1));
      setInput(trimmed);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-1 min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* SIDEBAR */}
      <aside className="w-72 bg-slate-900/50 backdrop-blur-xl border-r border-slate-800 flex flex-col shrink-0">
        <div className="h-16 px-6 border-b border-slate-800/80 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <Bot className="w-4 h-4 text-indigo-100" />
          </div>
          <div>
            <h1 className="font-bold text-sm leading-tight text-white">Document Chat</h1>
            <span className="text-[10px] text-indigo-400 font-medium tracking-wide">QWEN2.5 ASSISTANT</span>
          </div>
        </div>

        <div className="p-4 border-b border-slate-800/80">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to workspace
          </Link>
        </div>

        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <span className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">
            Extracted Documents
          </span>
          <button
            onClick={loadDocuments}
            className="text-slate-500 hover:text-slate-200 transition-colors"
            title="Refresh list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingDocs ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="flex-1 overflow-auto px-2 pb-4 space-y-1">
          {loadingDocs ? (
            <p className="px-3 py-2 text-xs text-slate-500">Loading…</p>
          ) : documents.length === 0 ? (
            <p className="px-3 py-2 text-xs text-slate-500 leading-relaxed">
              No extracted documents yet. Run the pipeline on a document in the workspace first.
            </p>
          ) : (
            documents.map((doc) => (
              <button
                key={doc.document_id}
                onClick={() => setSelectedId(doc.document_id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                  selectedId === doc.document_id
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 shrink-0 text-indigo-400" />
                  <span className="truncate font-mono text-[11px]">{doc.document_id}</span>
                </div>
                {typeof doc.data?.company === 'string' && (
                  <span className="block truncate text-[11px] text-slate-500 mt-0.5 pl-5.5">
                    {doc.data.company as string}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      </aside>

      {/* MAIN CHAT */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="h-16 px-6 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/30">
          <div className="min-w-0">
            <h2 className="font-semibold text-sm text-white truncate">
              {selectedDoc ? documentLabel(selectedDoc) : 'Select a document to start'}
            </h2>
            {selectedDoc?.summary && (
              <p className="text-[11px] text-slate-500 truncate">{selectedDoc.summary}</p>
            )}
          </div>
          <span className="flex items-center gap-1.5 text-[11px] text-slate-500 shrink-0 ml-4">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> qwen2.5
          </span>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500">
              <Bot className="w-10 h-10 mb-3 text-slate-700" />
              <p className="text-sm max-w-sm leading-relaxed">
                {selectedDoc
                  ? 'Ask anything about this document — e.g. "What is the total amount?" or "請求書番号は？"'
                  : 'Pick an extracted document from the left to begin chatting.'}
              </p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-600/40 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-indigo-300" />
                </div>
              )}
              <div
                className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-sm'
                    : 'bg-slate-800 text-slate-100 rounded-bl-sm'
                }`}
              >
                {msg.content}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-slate-300" />
                </div>
              )}
            </div>
          ))}

          {sending && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-600/40 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-indigo-300" />
              </div>
              <div className="bg-slate-800 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" />
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="px-6 py-2 text-xs text-rose-400 bg-rose-950/30 border-t border-rose-900/40">
            {error}
          </div>
        )}

        <div className="border-t border-slate-800/80 p-4 bg-slate-900/30">
          <div className="flex items-end gap-3 max-w-3xl mx-auto">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedId ? 'Ask about this document…' : 'Select a document first'}
              disabled={!selectedId || sending}
              rows={1}
              className="flex-1 resize-none rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-600 disabled:opacity-50 max-h-40"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || !selectedId || sending}
              className="h-11 w-11 shrink-0 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 flex items-center justify-center transition-colors"
              title="Send"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </div>
          <p className="text-[10px] text-slate-600 text-center mt-2">
            Answers are grounded in the selected document&apos;s extracted JSON. Press Enter to send, Shift+Enter for a new line.
          </p>
        </div>
      </main>
    </div>
  );
}
