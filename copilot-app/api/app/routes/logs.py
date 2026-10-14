"""API routes for inspecting live application logs and interactive log viewer."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from app.core.logging import clear_log_buffer, get_recent_logs

router = APIRouter(prefix="/logs", tags=["logs"])


class LogItem(BaseModel):
    id: int
    timestamp: str
    level: str
    logger: str
    message: str
    request_id: str | None = None


class LogsResponse(BaseModel):
    total: int
    logs: list[LogItem]


@router.get("", response_model=LogsResponse)
async def list_logs(
    limit: int = Query(default=100, ge=1, le=500, description="Max log items to return"),
    level: str = Query(
        default="DEBUG", description="Minimum log level: DEBUG, INFO, WARNING, ERROR"
    ),
    search: str | None = Query(default=None, description="Search term in message or logger"),
    request_id: str | None = Query(default=None, description="Filter by correlation request ID"),
    format: Literal["json", "text"] = Query(default="json", description="Output format"),
) -> LogsResponse | PlainTextResponse:
    """Retrieve filtered recent logs recorded in memory."""
    logs = get_recent_logs(limit=limit, min_level=level, search=search, request_id=request_id)

    if format == "text":
        lines: list[str] = []
        for entry in logs:
            req = f" [{entry['request_id']}]" if entry.get("request_id") else ""
            lines.append(
                f"{entry['timestamp']} {entry['level']:<7} [{entry['logger']}]{req}: {entry['message']}"
            )
        return PlainTextResponse("\n".join(lines), media_type="text/plain; charset=utf-8")

    return LogsResponse(total=len(logs), logs=[LogItem(**entry) for entry in logs])


@router.delete("", status_code=status.HTTP_200_OK)
async def clear_logs() -> dict[str, bool]:
    """Clear all in-memory logs."""
    clear_log_buffer()
    return {"cleared": True}


@router.get("/view", response_class=HTMLResponse)
async def view_logs_html() -> HTMLResponse:
    """Live interactive HTML log viewer."""
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Copilot API · Live Log Viewer</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            bg: '#0f172a',
            surface: '#1e293b',
            border: '#334155'
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #0f172a; color: #f8fafc; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #1e293b; }
    ::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
  </style>
</head>
<body class="p-4 md:p-6 min-h-screen flex flex-col">
  <header class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border">
    <div class="flex items-center gap-3">
      <div class="h-3.5 w-3.5 rounded-full bg-emerald-500 animate-pulse"></div>
      <h1 class="text-xl font-bold tracking-tight text-white">Copilot API Logs</h1>
      <span id="log-count" class="text-xs bg-slate-800 border border-slate-700 text-slate-400 px-2.5 py-0.5 rounded-full font-sans">0 events</span>
    </div>

    <div class="flex flex-wrap items-center gap-2 text-sm font-sans">
      <div class="relative">
        <input id="search-input" type="text" placeholder="Filter logs (e.g. chat, error)..."
          class="bg-surface border border-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-500 w-48 md:w-64" />
      </div>

      <select id="level-select" class="bg-surface border border-border rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-emerald-500">
        <option value="DEBUG">Level: ALL (Debug)</option>
        <option value="INFO" selected>Level: INFO &amp; up</option>
        <option value="WARNING">Level: WARNING &amp; up</option>
        <option value="ERROR">Level: ERROR only</option>
      </select>

      <label class="flex items-center gap-1.5 text-xs text-slate-300 bg-surface border border-border px-3 py-1.5 rounded-lg cursor-pointer select-none">
        <input type="checkbox" id="auto-refresh" checked class="rounded accent-emerald-500 cursor-pointer">
        <span>Auto-refresh (2s)</span>
      </label>

      <button id="refresh-btn" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-border transition">
        Refresh
      </button>

      <button id="clear-btn" class="bg-rose-950/60 hover:bg-rose-900 text-rose-300 text-xs px-3 py-1.5 rounded-lg border border-rose-800/60 transition">
        Clear
      </button>

      <button id="copy-btn" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-border transition">
        Copy
      </button>
    </div>
  </header>

  <main class="flex-1 mt-4 rounded-xl border border-border bg-slate-950/70 p-3 overflow-x-auto overflow-y-auto max-h-[calc(100vh-140px)] text-xs leading-relaxed" id="logs-container">
    <div id="logs-list" class="space-y-1">
      <div class="text-slate-500 py-8 text-center font-sans">Loading logs...</div>
    </div>
  </main>

  <script>
    let timer = null;
    let currentLogs = [];

    const levelColors = {
      DEBUG: 'text-sky-400 border-sky-900/60 bg-sky-950/30',
      INFO: 'text-emerald-400 border-emerald-900/60 bg-emerald-950/30',
      WARNING: 'text-amber-400 border-amber-900/60 bg-amber-950/30',
      WARN: 'text-amber-400 border-amber-900/60 bg-amber-950/30',
      ERROR: 'text-rose-400 border-rose-900/60 bg-rose-950/40 font-semibold',
      CRITICAL: 'text-red-300 border-red-700 bg-red-900/50 font-bold'
    };

    function escapeHtml(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    async function fetchLogs() {
      const level = document.getElementById('level-select').value;
      const search = document.getElementById('search-input').value.trim();
      const params = new URLSearchParams({ limit: '200', level });
      if (search) params.append('search', search);

      try {
        const res = await fetch(`/api/logs?${params.toString()}`);
        if (!res.ok) return;
        const data = await res.json();
        currentLogs = data.logs;
        renderLogs(currentLogs);
        document.getElementById('log-count').innerText = `${currentLogs.length} events`;
      } catch (err) {
        console.error('Failed to fetch logs:', err);
      }
    }

    function renderLogs(logs) {
      const list = document.getElementById('logs-list');
      if (!logs.length) {
        list.innerHTML = '<div class="text-slate-500 py-8 text-center font-sans">No matching logs found. Send requests to the API to see live logs!</div>';
        return;
      }

      list.innerHTML = logs.map(item => {
        const time = item.timestamp.split('T')[1]?.split('.')[0] || item.timestamp;
        const badgeClass = levelColors[item.level] || 'text-slate-400 border-slate-700 bg-slate-800';
        const reqBadge = item.request_id ? `<span class="px-1.5 py-0.2 text-[10px] rounded bg-slate-800/80 border border-slate-700/60 text-indigo-300 font-mono">${escapeHtml(item.request_id)}</span>` : '';
        return `
          <div class="flex items-start gap-2 py-0.5 hover:bg-slate-900/80 px-2 rounded group transition">
            <span class="text-slate-500 select-none shrink-0 font-mono text-[11px]">${time}</span>
            <span class="px-1.5 py-0.2 rounded border text-[10px] shrink-0 uppercase tracking-wider ${badgeClass}">${item.level}</span>
            <span class="text-slate-400 shrink-0 font-medium text-[11px]">[${escapeHtml(item.logger)}]</span>
            ${reqBadge}
            <span class="text-slate-200 break-all select-text font-mono">${escapeHtml(item.message)}</span>
          </div>
        `;
      }).join('');
    }

    function setupAutoRefresh() {
      if (timer) clearInterval(timer);
      const isAuto = document.getElementById('auto-refresh').checked;
      if (isAuto) {
        timer = setInterval(fetchLogs, 2000);
      }
    }

    document.getElementById('auto-refresh').addEventListener('change', setupAutoRefresh);
    document.getElementById('refresh-btn').addEventListener('click', fetchLogs);
    document.getElementById('level-select').addEventListener('change', fetchLogs);
    document.getElementById('search-input').addEventListener('input', () => {
      clearTimeout(window._searchTimeout);
      window._searchTimeout = setTimeout(fetchLogs, 250);
    });

    document.getElementById('clear-btn').addEventListener('click', async () => {
      if (!confirm('Clear all logs in memory?')) return;
      await fetch('/api/logs', { method: 'DELETE' });
      fetchLogs();
    });

    document.getElementById('copy-btn').addEventListener('click', () => {
      const text = currentLogs.map(l => `${l.timestamp} [${l.level}] [${l.logger}] ${l.request_id ? `[${l.request_id}] ` : ''}${l.message}`).join('\\n');
      navigator.clipboard.writeText(text);
      alert('Copied ' + currentLogs.length + ' log entries to clipboard!');
    });

    fetchLogs();
    setupAutoRefresh();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
