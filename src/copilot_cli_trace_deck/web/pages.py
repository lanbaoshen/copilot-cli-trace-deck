from __future__ import annotations

import html
import json
from decimal import Decimal

from ..models import SessionFlowNode, SessionLogEntry, SessionLogSection, SessionPreview, SessionSummary


PAGE_TITLE = "Copilot CLI Trace Deck"
REPOSITORY_URL = "https://github.com/lanbaoshen/copilot-cli-trace-deck"
AUTHOR_URL = "https://github.com/lanbaoshen"


def render_document(page_title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(page_title)}</title>
    <style>
      :root {{
        --bg: #090d14;
        --panel: rgba(255, 255, 255, 0.03);
        --panel-strong: rgba(255, 255, 255, 0.045);
        --line: rgba(255, 255, 255, 0.09);
        --text: #eef3fa;
        --muted: #8f98a8;
        --blue-strong: #1f66e2;
      }}

      * {{
        box-sizing: border-box;
      }}

      html, body {{
        margin: 0;
        min-height: 100%;
      }}

      body {{
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top, rgba(82, 125, 214, 0.07), transparent 36%),
          radial-gradient(circle at 20% 15%, rgba(255, 255, 255, 0.035), transparent 18%),
          linear-gradient(180deg, #0a0f17 0%, var(--bg) 28%, #080c12 100%);
        color: var(--text);
        overflow-x: hidden;
      }}

      body::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        opacity: 0.18;
        background-image:
          linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 255, 255, 0.012) 1px, transparent 1px);
        background-size: 100% 32px, 32px 100%;
        mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9), transparent 82%);
      }}

      a {{
        color: inherit;
      }}

      .page {{
        position: relative;
        min-height: 100vh;
      }}

      .app-shell {{
        display: grid;
        gap: 16px;
      }}

      .shell {{
        width: min(1180px, calc(100% - 48px));
        margin: 0 auto;
      }}

      .site-footer {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-top: auto;
        padding: 16px 4px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.09);
        color: #7f8796;
        font-size: 0.88rem;
        line-height: 1.4;
      }}

      .site-footer-copy {{
        min-width: 0;
      }}

      .site-footer a {{
        color: #b9d0ff;
        text-decoration: none;
      }}

      .site-footer a:hover {{
        text-decoration: underline;
      }}

      .index-page {{
        height: 100vh;
        padding: 18px 0 20px;
        overflow: hidden;
      }}

      .index-shell {{
        height: 100%;
        grid-template-rows: auto minmax(0, 1fr) auto;
        min-height: 0;
      }}

      .index-content {{
        min-height: 0;
        display: flex;
        flex-direction: column;
      }}

      .hero {{
        flex: none;
        text-align: center;
        animation: rise 520ms ease-out both;
      }}

      .index-title {{
        margin: 0;
        font-size: clamp(2.15rem, 3.2vw, 3.2rem);
        line-height: 1.02;
        font-weight: 700;
        letter-spacing: -0.05em;
      }}

      .index-subtitle {{
        margin: 12px 0 0;
        font-size: clamp(0.98rem, 1.35vw, 1.28rem);
        line-height: 1.28;
        color: var(--muted);
        letter-spacing: -0.03em;
      }}

      .session-list {{
        list-style: none;
        padding: 0 8px 0 0;
        margin: 38px auto 0;
        width: min(940px, 100%);
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        overflow-x: hidden;
        scrollbar-width: thin;
        scrollbar-color: rgba(143, 152, 168, 0.45) transparent;
      }}

      .session-list::-webkit-scrollbar {{
        width: 10px;
      }}

      .session-list::-webkit-scrollbar-thumb {{
        background: rgba(143, 152, 168, 0.35);
        border: 3px solid transparent;
        border-radius: 999px;
        background-clip: padding-box;
      }}

      .session-list::-webkit-scrollbar-track {{
        background: transparent;
      }}

      .session-link {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        width: 100%;
        padding: 14px 14px;
        border-radius: 18px;
        text-decoration: none;
        transition: background-color 160ms ease, transform 160ms ease;
        animation: rise 520ms ease-out both;
      }}

      .session-link:hover {{
        background: var(--panel);
        transform: translateY(-1px);
      }}

      .session-main {{
        display: flex;
        align-items: center;
        gap: 14px;
        min-width: 0;
      }}

      .session-copy {{
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }}

      .session-title {{
        margin: 0;
        font-size: clamp(0.96rem, 1.2vw, 1.28rem);
        line-height: 1.18;
        font-weight: 600;
        letter-spacing: -0.035em;
        color: #f0f4fb;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}

      .session-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px 10px;
        color: #8d97a6;
        font-size: 0.84rem;
        line-height: 1.35;
        letter-spacing: -0.015em;
      }}

      .session-meta-item {{
        white-space: nowrap;
      }}

      .icon {{
        flex: none;
        width: 24px;
        height: 24px;
        color: #8d97a6;
      }}

      .badge {{
        flex: none;
        min-width: 76px;
        padding: 8px 14px;
        border-radius: 999px;
        background: linear-gradient(180deg, #3184ff 0%, var(--blue-strong) 100%);
        color: #f8fbff;
        font-size: 0.86rem;
        line-height: 1;
        font-weight: 700;
        letter-spacing: -0.02em;
        text-align: center;
        box-shadow: 0 10px 30px rgba(45, 126, 247, 0.28);
      }}

      .detail-page {{
        padding: 18px 0 22px;
      }}

      .detail-shell {{
        min-height: calc(100vh - 40px);
        grid-template-rows: auto minmax(0, 1fr) auto;
      }}

      .detail-header {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 34px;
        animation: rise 420ms ease-out both;
      }}

      .detail-title-row {{
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
      }}

      .detail-title {{
        margin: 0;
        font-size: clamp(1.5rem, 2vw, 2rem);
        line-height: 1.12;
        font-weight: 700;
        letter-spacing: -0.04em;
      }}

      .detail-meta {{
        margin-top: 10px;
        color: var(--muted);
        font-size: 0.95rem;
        line-height: 1.35;
      }}

      .ghost-link {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 9px 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.02);
        color: var(--muted);
        text-decoration: none;
        font-size: 0.92rem;
        line-height: 1;
        transition: border-color 160ms ease, color 160ms ease, background-color 160ms ease;
      }}

      .ghost-link:hover {{
        color: var(--text);
        border-color: rgba(255, 255, 255, 0.18);
        background: rgba(255, 255, 255, 0.04);
      }}

      .section-title {{
        margin: 0 0 14px;
        font-size: 1.05rem;
        line-height: 1.2;
        font-weight: 700;
        letter-spacing: -0.02em;
      }}

      .detail-grid {{
        display: grid;
        grid-template-columns: minmax(250px, 410px) 1fr;
        gap: 34px 40px;
        align-items: start;
      }}

      .facts {{
        display: grid;
        grid-template-columns: 130px minmax(0, 1fr);
        gap: 10px 18px;
        margin: 0;
      }}

      .fact-label {{
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.35;
        font-weight: 600;
      }}

      .fact-value {{
        margin: 0;
        color: var(--text);
        font-size: 1rem;
        line-height: 1.35;
        font-weight: 600;
      }}

      .summary-block,
      .explore-block {{
        grid-column: 1 / -1;
      }}

      .card-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 18px;
      }}

      .stat-card {{
        min-height: 102px;
        padding: 20px 18px 18px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(9, 13, 20, 0.68);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.015);
      }}

      .stat-label {{
        display: block;
        color: var(--muted);
        font-size: clamp(0.76rem, 0.72rem + 0.18vw, 0.88rem);
        line-height: 1.25;
        font-weight: 600;
        letter-spacing: -0.02em;
        white-space: nowrap;
      }}

      .stat-value {{
        display: block;
        margin-top: 10px;
        font-size: clamp(1.45rem, 1.9vw, 2.1rem);
        line-height: 1;
        letter-spacing: -0.045em;
        font-weight: 400;
        font-variant-numeric: tabular-nums;
        color: var(--text);
      }}

      .billing-note {{
        margin: 16px 0 0;
        color: var(--muted);
        font-size: 0.94rem;
        line-height: 1.5;
      }}

      .model-usage-panel {{
        margin-top: 18px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(9, 13, 20, 0.68);
        overflow: hidden;
      }}

      .model-usage-title {{
        padding: 16px 18px 0;
        color: var(--text);
        font-size: 0.96rem;
        line-height: 1.3;
        font-weight: 600;
      }}

      .model-usage-scroller {{
        overflow-x: auto;
        padding: 12px 18px 18px;
      }}

      .model-usage-table {{
        width: 100%;
        min-width: 760px;
        border-collapse: collapse;
        font-variant-numeric: tabular-nums;
      }}

      .model-usage-table th,
      .model-usage-table td {{
        padding: 12px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        text-align: left;
      }}

      .model-usage-table th {{
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.2;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }}

      .model-usage-table tbody tr:last-child td {{
        border-bottom: 0;
      }}

      .model-usage-table td {{
        color: var(--text);
        font-size: 0.95rem;
        line-height: 1.35;
        font-weight: 500;
      }}

      .model-usage-empty {{
        padding: 16px 18px 18px;
        color: var(--muted);
        font-size: 0.94rem;
        line-height: 1.5;
      }}

      .action-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
      }}

      .action-chip {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.03);
        color: #dbe2ee;
        text-decoration: none;
        font-size: 0.96rem;
        line-height: 1;
        font-weight: 600;
      }}

      .empty-state {{
        padding: 48px 24px;
        text-align: center;
        color: var(--muted);
      }}

      .empty-title {{
        margin: 0;
        color: var(--text);
        font-size: 1.4rem;
        line-height: 1.15;
      }}

      .empty-copy {{
        margin: 12px auto 0;
        max-width: 460px;
        font-size: 1rem;
        line-height: 1.45;
      }}

      @keyframes rise {{
        from {{
          opacity: 0;
          transform: translateY(14px);
        }}

        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}

      @media (max-width: 1280px) {{
        .card-grid {{
          grid-template-columns: repeat(3, minmax(180px, 1fr));
        }}
      }}

      @media (max-width: 920px) {{
        .detail-grid {{
          grid-template-columns: 1fr;
        }}

        .card-grid {{
          grid-template-columns: repeat(2, minmax(180px, 1fr));
        }}
      }}

      @media (max-width: 820px) {{
        .index-page {{
          padding-top: 28px;
        }}

        .session-list {{
          margin-top: 28px;
        }}

        .session-link {{
          padding-inline: 8px;
        }}

        .badge {{
          min-width: 84px;
          padding-inline: 16px;
        }}
      }}

      @media (max-width: 640px) {{
        .shell {{
          width: min(100%, calc(100% - 28px));
        }}

        .site-footer,
        .site-footer {{
          flex-direction: column;
          align-items: stretch;
        }}

        .detail-header {{
          flex-direction: column;
          align-items: stretch;
        }}

        .facts {{
          grid-template-columns: 1fr;
          gap: 4px 0;
        }}

        .session-link {{
          align-items: flex-start;
          gap: 16px;
        }}

        .session-title {{
          white-space: normal;
        }}

        .card-grid {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>{body}</body>
</html>
"""


def build_index_page(session_previews: list[SessionPreview]) -> str:
    items = render_session_list_markup(session_previews)
    body = f"""
    <main class="page index-page">
      <div class="shell app-shell index-shell">
        <section class="index-content">
          <header class="hero">
            <h1 class="index-title">{PAGE_TITLE}</h1>
            <p class="index-subtitle">Select a chat session to debug</p>
          </header>
          <ul class="session-list" id="session-list">{items}
          </ul>
        </section>
        {render_page_footer()}
      </div>

      <script>
        (() => {{
          const sessionList = document.getElementById('session-list');
          let eventSource = null;
          let isPolling = false;
          let lastMarkup = sessionList ? sessionList.innerHTML.trim() : '';

          function parseSessionItems(markup) {{
            const template = document.createElement('template');
            template.innerHTML = '<ul>' + markup + '</ul>';
            return Array.from(template.content.querySelectorAll('li[data-session-id]'));
          }}

          function syncSessionList(markup) {{
            if (!sessionList) {{
              return;
            }}

            const nextItems = parseSessionItems(markup);
            const existingItems = new Map(
              Array.from(sessionList.querySelectorAll('li[data-session-id]')).map((item) => [item.dataset.sessionId || '', item]),
            );

            nextItems.forEach((nextItem, index) => {{
              const sessionId = nextItem.dataset.sessionId || '';
              const currentItem = existingItems.get(sessionId);
              let itemToPlace = nextItem;

              if (currentItem) {{
                existingItems.delete(sessionId);
                if (currentItem.outerHTML === nextItem.outerHTML) {{
                  itemToPlace = currentItem;
                }} else {{
                  currentItem.replaceWith(nextItem);
                }}
              }}

              const currentAtIndex = sessionList.children[index] || null;
              if (itemToPlace !== currentAtIndex) {{
                sessionList.insertBefore(itemToPlace, currentAtIndex);
              }}
            }});

            existingItems.forEach((item) => item.remove());
          }}

          async function refreshIndex() {{
            if (isPolling || document.hidden || !sessionList) {{
              return;
            }}

            isPolling = true;
            try {{
              const response = await fetch('/index.json', {{
                headers: {{ 'Accept': 'application/json' }},
              }});
              if (!response.ok) {{
                return;
              }}

              const payload = await response.json();
              const itemsHtml = typeof payload.itemsHtml === 'string' ? payload.itemsHtml.trim() : '';
              if (itemsHtml === lastMarkup) {{
                return;
              }}

              syncSessionList(itemsHtml);
              lastMarkup = itemsHtml;
            }} catch (_error) {{
              return;
            }} finally {{
              isPolling = false;
            }}
          }}

          function closeIndexStream() {{
            if (!eventSource) {{
              return;
            }}

            eventSource.close();
            eventSource = null;
          }}

          function openIndexStream() {{
            if (eventSource || !sessionList || document.hidden || typeof EventSource !== 'function') {{
              return;
            }}

            eventSource = new EventSource('/index.events');
            eventSource.onmessage = () => {{
              refreshIndex();
            }};
            eventSource.onerror = () => {{
              return;
            }};
          }}

          openIndexStream();
          document.addEventListener('visibilitychange', () => {{
            if (document.hidden) {{
              closeIndexStream();
            }} else {{
              refreshIndex();
              openIndexStream();
            }}
          }});
          window.addEventListener('beforeunload', () => {{
            closeIndexStream();
          }});
        }})();
      </script>
    </main>
    """
    return render_document(PAGE_TITLE, body)


def build_session_page(summary: SessionSummary) -> str:
    title = html.escape(summary.title)
    detail_meta = build_session_detail_meta(summary)
    stat_labels = build_summary_stat_labels(summary)
    body = f"""
    <main class="page detail-page">
      <div class="shell app-shell detail-shell">
        <header class="detail-header">
          <div>
            <div class="detail-title-row">
              {chat_icon()}
              <h1 class="detail-title">{title}</h1>
            </div>
            <div class="detail-meta" id="session-detail-meta">{detail_meta}</div>
          </div>
          <a class="ghost-link" href="/">Back To Sessions</a>
        </header>

        <section class="detail-grid">
          <div>
            <h2 class="section-title">Session Details</h2>
            <dl class="facts">
              <dt class="fact-label">Session Type</dt>
              <dd class="fact-value" id="session-type-value">{html.escape(summary.session_type)}</dd>
              <dt class="fact-label">Location</dt>
              <dd class="fact-value" id="session-location-value">{html.escape(summary.location)}</dd>
              <dt class="fact-label">Status</dt>
              <dd class="fact-value" id="session-status-value">{html.escape(summary.status)}</dd>
              <dt class="fact-label">Created</dt>
              <dd class="fact-value" id="session-created-value">{html.escape(summary.created_label)}</dd>
              <dt class="fact-label">Last Activity</dt>
              <dd class="fact-value" id="session-updated-value">{html.escape(summary.updated_label)}</dd>
            </dl>
          </div>

          <div class="summary-block">
            <h2 class="section-title">Summary</h2>
            <div class="card-grid">
              {render_stat_card('Model Turns', summary.model_turns, value_id='session-model-turns-value')}
              {render_stat_card('Tool Calls', summary.tool_calls, value_id='session-tool-calls-value')}
              {render_stat_card(stat_labels['totalInputLabel'], summary.total_input_tokens, value_id='session-total-input-value', label_id='session-total-input-label')}
              {render_stat_card('Total Output Tokens', summary.total_output_tokens, value_id='session-total-output-value')}
              {render_stat_card(stat_labels['totalCachedInputLabel'], summary.total_cached_input_tokens, value_id='session-total-cached-input-value', label_id='session-total-cached-input-label')}
              {render_stat_card(stat_labels['totalCacheWriteLabel'], summary.total_cache_write_tokens, value_id='session-total-cache-write-value', label_id='session-total-cache-write-label')}
              {render_stat_card('Total Tokens', summary.total_tokens, value_id='session-total-tokens-value')}
              {render_stat_card('Estimated AI Credits', format_ai_credits(summary.estimated_ai_credits), value_id='session-estimated-ai-credits-value')}
              {render_stat_card('Estimated Cost (USD)', format_currency(summary.estimated_cost_usd), value_id='session-estimated-cost-usd-value')}
              {render_stat_card('Errors', summary.error_count, value_id='session-error-count-value')}
            </div>
            <p class="billing-note" id="session-billing-note">{html.escape(summary.billing_note)}</p>
            <div class="model-usage-panel" id="session-model-usage-breakdown">
              {render_model_usage_breakdown(summary)}
            </div>
          </div>

          <div class="explore-block">
            <h2 class="section-title">Explore Trace Data</h2>
            <div class="action-row">
              {render_action_chip('View Logs', f'/sessions/{summary.session_id}/logs')}
              {render_action_chip('Agent Flow Chart', f'/sessions/{summary.session_id}/flow')}
            </div>
          </div>
        </section>
        {render_page_footer()}
      </div>

      <script>
        (() => {{
          const sessionId = {json.dumps(summary.session_id)};
          let eventSource = null;
          let isPolling = false;

          function setText(id, value) {{
            const node = document.getElementById(id);
            if (node) {{
              node.textContent = value;
            }}
          }}

          function setHTML(id, value) {{
            const node = document.getElementById(id);
            if (node) {{
              node.innerHTML = value;
            }}
          }}

          async function refreshSummary() {{
            if (isPolling || document.hidden) {{
              return;
            }}

            isPolling = true;
            try {{
              const response = await fetch('/sessions/' + encodeURIComponent(sessionId) + '/summary.json', {{
                headers: {{ 'Accept': 'application/json' }},
              }});
              if (!response.ok) {{
                return;
              }}

              const summary = await response.json();
              setText('session-detail-meta', summary.detailMeta || '');
              setText('session-type-value', summary.sessionType || '');
              setText('session-location-value', summary.location || '');
              setText('session-status-value', summary.status || '');
              setText('session-created-value', summary.createdLabel || '');
              setText('session-updated-value', summary.updatedLabel || '');
              setText('session-total-input-label', summary.totalInputLabel || 'Total Input Tokens');
              setText('session-total-cached-input-label', summary.totalCachedInputLabel || 'Total Cached Input Tokens');
              setText('session-total-cache-write-label', summary.totalCacheWriteLabel || 'Total Cache Write Tokens');
              setText('session-model-turns-value', summary.modelTurns || '0');
              setText('session-tool-calls-value', summary.toolCalls || '0');
              setText('session-total-input-value', summary.totalInputTokens || '0');
              setText('session-total-output-value', summary.totalOutputTokens || '0');
              setText('session-total-cached-input-value', summary.totalCachedInputTokens || '0');
              setText('session-total-cache-write-value', summary.totalCacheWriteTokens || '0');
              setText('session-total-tokens-value', summary.totalTokens || '0');
              setText('session-estimated-ai-credits-value', summary.estimatedAiCredits || '-');
              setText('session-estimated-cost-usd-value', summary.estimatedCostUsd || '-');
              setText('session-error-count-value', summary.errorCount || '0');
              setText('session-billing-note', summary.billingNote || '');
              setHTML('session-model-usage-breakdown', summary.modelUsageBreakdownHtml || '');
            }} catch (_error) {{
              return;
            }} finally {{
              isPolling = false;
            }}
          }}

          function closeSummaryStream() {{
            if (!eventSource) {{
              return;
            }}

            eventSource.close();
            eventSource = null;
          }}

          function openSummaryStream() {{
            if (eventSource || document.hidden || typeof EventSource !== 'function') {{
              return;
            }}

            eventSource = new EventSource('/sessions/' + encodeURIComponent(sessionId) + '/summary.events');
            eventSource.onmessage = () => {{
              refreshSummary();
            }};
            eventSource.onerror = () => {{
              return;
            }};
          }}

          openSummaryStream();
          document.addEventListener('visibilitychange', () => {{
            if (document.hidden) {{
              closeSummaryStream();
            }} else {{
              refreshSummary();
              openSummaryStream();
            }}
          }});
          window.addEventListener('beforeunload', () => {{
            closeSummaryStream();
          }});
        }})();
      </script>
    </main>
    """
    return render_document(f"{summary.title} - {PAGE_TITLE}", body)


def build_flow_page(summary: SessionSummary, flow_nodes: list[SessionFlowNode]) -> str:
    nodes_markup = "\n".join(render_flow_node(summary.session_id, node) for node in flow_nodes) or render_empty_flow_state()
    body = f"""
    <style>
      .flow-page {{
        min-height: 100vh;
        padding: 18px 0 20px;
      }}

      .flow-shell {{
        min-height: calc(100vh - 38px);
        grid-template-rows: auto minmax(0, 1fr) auto;
      }}

      .flow-content {{
        min-height: 0;
        display: grid;
        grid-template-rows: auto auto minmax(0, 1fr);
        gap: 18px;
      }}

      .flow-header {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 18px;
      }}

      .flow-kicker {{
        color: #7f8796;
        font-size: 0.82rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }}

      .flow-title {{
        margin: 8px 0 0;
        font-size: clamp(2rem, 4vw, 3rem);
        line-height: 0.96;
        letter-spacing: -0.06em;
      }}

      .flow-subtitle {{
        max-width: 760px;
        margin: 10px 0 0;
        color: #9ea6b6;
        font-size: 0.98rem;
        line-height: 1.6;
      }}

      .flow-summary-bar {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }}

      .flow-summary-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.09);
        background: rgba(255, 255, 255, 0.03);
        color: #a8b0bf;
        font-size: 0.84rem;
      }}

      .flow-summary-pill strong {{
        color: #eef3fa;
        font-weight: 600;
      }}

      .flow-board {{
        position: relative;
        min-height: 0;
        padding: 18px 0 24px;
      }}

      .flow-board::before {{
        content: "";
        position: absolute;
        top: 0;
        bottom: 0;
        left: 50%;
        width: 1px;
        transform: translateX(-50%);
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(163, 175, 197, 0.28), rgba(255, 255, 255, 0.04));
      }}

      .flow-rail {{
        position: relative;
        z-index: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 18px;
      }}

      .flow-step {{
        position: relative;
        display: flex;
        justify-content: center;
        width: 100%;
      }}

      .flow-step::before,
      .flow-step::after {{
        content: "";
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
      }}

      .flow-step::before {{
        top: -18px;
        width: 1px;
        height: 18px;
        background: rgba(176, 188, 207, 0.34);
      }}

      .flow-step::after {{
        top: -6px;
        width: 10px;
        height: 10px;
        border-right: 1.5px solid rgba(176, 188, 207, 0.66);
        border-bottom: 1.5px solid rgba(176, 188, 207, 0.66);
        transform: translateX(-50%) rotate(45deg);
        background: var(--bg);
      }}

      .flow-step:first-child::before,
      .flow-step:first-child::after {{
        display: none;
      }}

      .flow-card {{
        position: relative;
        width: min(100%, 560px);
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(16, 22, 33, 0.88);
        box-shadow: 0 18px 36px rgba(0, 0, 0, 0.26), inset 0 1px 0 rgba(255, 255, 255, 0.04);
      }}

      .flow-link {{
        display: block;
        width: min(100%, 560px);
        color: inherit;
        text-decoration: none;
      }}

      .flow-link .flow-card {{
        width: 100%;
      }}

      .flow-link:hover .flow-card,
      .flow-link:focus-visible .flow-card {{
        transform: translateY(-1px);
        border-color: rgba(255, 255, 255, 0.18);
        box-shadow: 0 22px 42px rgba(0, 0, 0, 0.34), inset 0 0 0 1px rgba(255, 255, 255, 0.04);
      }}

      .flow-link:focus-visible {{
        outline: none;
      }}

      .flow-card::before,
      .flow-card::after {{
        content: "";
        position: absolute;
        inset: 0;
        border-radius: inherit;
        pointer-events: none;
      }}

      .flow-card::before {{
        border: 1px solid rgba(255, 255, 255, 0.04);
      }}

      .flow-card.is-group {{
        width: min(100%, 420px);
        background: rgba(20, 25, 37, 0.94);
      }}

      .flow-card.is-group::after {{
        inset: auto 10px -7px 10px;
        height: 14px;
        border-radius: 0 0 12px 12px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02));
        opacity: 0.7;
      }}

      .flow-card.is-user {{
        width: min(100%, 700px);
        border-color: rgba(73, 127, 255, 0.65);
        background: linear-gradient(180deg, rgba(11, 30, 67, 0.95), rgba(9, 19, 41, 0.95));
        box-shadow: 0 18px 36px rgba(7, 18, 38, 0.42), inset 0 0 0 1px rgba(107, 157, 255, 0.14);
      }}

      .flow-card.is-model {{
        width: min(100%, 540px);
        border-color: rgba(73, 127, 255, 0.54);
        background: linear-gradient(180deg, rgba(11, 30, 67, 0.88), rgba(10, 19, 41, 0.92));
      }}

      .flow-card.is-response {{
        width: min(100%, 640px);
        background: rgba(18, 22, 30, 0.94);
      }}

      .flow-card.is-tool,
      .flow-card.is-skill {{
        width: min(100%, 370px);
        border-color: rgba(108, 221, 164, 0.62);
        background: linear-gradient(180deg, rgba(10, 43, 31, 0.96), rgba(11, 31, 25, 0.94));
      }}

      .flow-card.is-error {{
        border-color: rgba(239, 97, 97, 0.58);
        background: linear-gradient(180deg, rgba(67, 18, 18, 0.94), rgba(38, 12, 12, 0.96));
      }}

      .flow-card.is-agent,
      .flow-card.is-state {{
        width: min(100%, 420px);
        background: rgba(24, 28, 37, 0.94);
      }}

      .flow-card-top {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 14px;
      }}

      .flow-card-title-wrap {{
        min-width: 0;
      }}

      .flow-card-title {{
        margin: 0;
        color: #f1f5fb;
        font-size: 1.06rem;
        line-height: 1.15;
        font-weight: 700;
        letter-spacing: -0.03em;
      }}

      .flow-card-subtitle {{
        margin-top: 4px;
        color: #a6afbe;
        font-size: 0.82rem;
        line-height: 1.4;
      }}

      .flow-card-pill {{
        flex: none;
        display: inline-flex;
        align-items: center;
        padding: 5px 8px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.05);
        color: #d2d9e4;
        font-size: 0.76rem;
        line-height: 1;
        white-space: nowrap;
      }}

      .flow-card-body {{
        margin-top: 10px;
        color: #edf2fa;
        font-size: 0.98rem;
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
      }}

      .flow-card-meta {{
        margin-top: 10px;
        color: #8790a0;
        font-size: 0.78rem;
        line-height: 1.4;
        font-family: "SFMono-Regular", "Menlo", monospace;
      }}

      .flow-card.is-user .flow-card-subtitle,
      .flow-card.is-model .flow-card-subtitle {{
        color: #bfd1ff;
      }}

      .flow-card.is-tool .flow-card-subtitle,
      .flow-card.is-skill .flow-card-subtitle {{
        color: #b8eed0;
      }}

      .flow-card.is-error .flow-card-subtitle {{
        color: #ffb9b9;
      }}

      .flow-empty {{
        width: min(100%, 560px);
        padding: 28px 30px;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.03);
        text-align: center;
        color: #a2abbb;
      }}

      .flow-empty strong {{
        display: block;
        margin-bottom: 8px;
        color: #eef3fa;
        font-size: 1rem;
      }}

      @media (max-width: 780px) {{
        .shell.flow-shell {{
          width: min(100%, calc(100% - 24px));
        }}

        .flow-header {{
          flex-direction: column;
        }}

        .flow-board::before {{
          left: 24px;
          transform: none;
        }}

        .flow-rail {{
          align-items: stretch;
        }}

        .flow-step {{
          justify-content: flex-start;
          padding-left: 48px;
        }}

        .flow-step::before,
        .flow-step::after {{
          left: 24px;
          transform: none;
        }}

        .flow-step::after {{
          transform: rotate(45deg);
        }}

        .flow-card {{
          width: 100%;
        }}
      }}
    </style>
    <main class="page flow-page">
      <div class="shell app-shell flow-shell">
        <div class="flow-content">
          <header class="flow-header">
            <div>
              <div class="flow-kicker">Trace View</div>
              <h1 class="flow-title">Agent Flow Chart</h1>
              <p class="flow-subtitle">A reconstructed vertical execution graph for {html.escape(summary.title)}. The chart compresses raw session events into user prompts, model turns, tool calls, skill loads, and state transitions.</p>
            </div>
            <a class="ghost-link" href="/sessions/{summary.session_id}">Back To Summary</a>
          </header>

          <div class="flow-summary-bar">
            <span class="flow-summary-pill"><strong id="flow-node-count-value">{len(flow_nodes)}</strong> flow nodes</span>
            <span class="flow-summary-pill"><strong id="flow-model-name-value">{html.escape(summary.model_name)}</strong> active model</span>
            <span class="flow-summary-pill"><strong id="flow-tool-calls-value">{summary.tool_calls}</strong> tool calls</span>
            <span class="flow-summary-pill"><strong id="flow-error-count-value">{summary.error_count}</strong> errors</span>
          </div>

          <section class="flow-board">
            <div class="flow-rail" id="flow-rail">{nodes_markup}
            </div>
          </section>
        </div>
        {render_page_footer()}
      </div>

      <script>
        (() => {{
          const sessionId = {json.dumps(summary.session_id)};
          const flowRail = document.getElementById('flow-rail');
          let eventSource = null;
          let isPolling = false;

          function setText(id, value) {{
            const node = document.getElementById(id);
            if (node) {{
              node.textContent = value;
            }}
          }}

          function createNodeFromMarkup(markup) {{
            const template = document.createElement('template');
            template.innerHTML = markup.trim();
            return template.content.firstElementChild;
          }}

          function currentMaxFlowIndex() {{
            const nodes = Array.from(document.querySelectorAll('[data-flow-index]'));
            return nodes.reduce((maxIndex, node) => Math.max(maxIndex, Number(node.dataset.flowIndex || '-1')), -1);
          }}

          function shouldFollowTail() {{
            const remaining = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
            return remaining < 160;
          }}

          async function refreshFlow() {{
            if (isPolling || document.hidden || !flowRail) {{
              return;
            }}

            isPolling = true;
            try {{
              const response = await fetch('/sessions/' + encodeURIComponent(sessionId) + '/flow.json?after=' + String(currentMaxFlowIndex()), {{
                headers: {{ 'Accept': 'application/json' }},
              }});
              if (!response.ok) {{
                return;
              }}

              const payload = await response.json();
              const nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
              setText('flow-node-count-value', String(payload.nodeCount || 0));
              setText('flow-model-name-value', payload.modelName || 'Unknown');
              setText('flow-tool-calls-value', String(payload.toolCalls || 0));
              setText('flow-error-count-value', String(payload.errorCount || 0));

              if (!nodes.length) {{
                return;
              }}

              const followTail = shouldFollowTail();
              const emptyState = flowRail.querySelector('.flow-empty');
              if (emptyState) {{
                emptyState.remove();
              }}

              let newestNode = null;
              nodes.forEach((node) => {{
                const flowNode = createNodeFromMarkup(node.html || '');
                if (!flowNode) {{
                  return;
                }}
                flowRail.appendChild(flowNode);
                newestNode = flowNode;
              }});

              if (followTail && newestNode) {{
                newestNode.scrollIntoView({{ block: 'end' }});
              }}
            }} catch (_error) {{
              return;
            }} finally {{
              isPolling = false;
            }}
          }}

          function closeFlowStream() {{
            if (!eventSource) {{
              return;
            }}

            eventSource.close();
            eventSource = null;
          }}

          function openFlowStream() {{
            if (eventSource || !flowRail || document.hidden || typeof EventSource !== 'function') {{
              return;
            }}

            eventSource = new EventSource('/sessions/' + encodeURIComponent(sessionId) + '/flow.events');
            eventSource.onmessage = () => {{
              refreshFlow();
            }};
            eventSource.onerror = () => {{
              return;
            }};
          }}

          openFlowStream();
          document.addEventListener('visibilitychange', () => {{
            if (document.hidden) {{
              closeFlowStream();
            }} else {{
              refreshFlow();
              openFlowStream();
            }}
          }});
          window.addEventListener('beforeunload', () => {{
            closeFlowStream();
          }});
        }})();
      </script>
    </main>
    """
    return render_document(f"{summary.title} Flow - {PAGE_TITLE}", body)


def build_logs_page(summary: SessionSummary, log_entries: list[SessionLogEntry]) -> str:
    rows = "\n".join(render_log_row(entry, selected=index == 0) for index, entry in enumerate(log_entries))
    templates = "\n".join(render_log_detail_template(entry) for entry in log_entries)
    initial_detail = render_log_detail(log_entries[0]) if log_entries else render_empty_log_detail()
    body = f"""
    <style>
      .logs-page {{
        height: 100vh;
        padding: 18px 0 0;
        overflow: hidden;
      }}

      .logs-shell {{
        height: 100%;
        display: grid;
        grid-template-rows: minmax(0, 1fr) auto;
        gap: 14px;
        min-height: 0;
      }}

      .logs-content {{
        display: grid;
        grid-template-rows: auto auto minmax(0, 1fr);
        gap: 14px;
        min-height: 0;
        overflow: hidden;
      }}

      .logs-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        min-height: 0;
      }}

      .logs-toolbar {{
        display: flex;
        align-items: center;
        gap: 12px;
        min-height: 0;
      }}

      .logs-filter {{
        position: relative;
        flex: 1;
        max-width: 640px;
      }}

      .logs-filter-meta {{
        display: inline-flex;
        align-items: center;
        min-width: 104px;
        padding: 0 12px;
        height: 42px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.03);
        color: #96a0af;
        font-size: 0.88rem;
        line-height: 1;
        letter-spacing: -0.01em;
      }}

      .logs-filter input {{
        width: 100%;
        height: 42px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(7, 10, 16, 0.74);
        color: #e9edf4;
        padding: 0 44px 0 14px;
        outline: none;
        font: inherit;
      }}

      .logs-filter input::placeholder {{
        color: #7f8796;
      }}

      .logs-filter svg {{
        position: absolute;
        right: 14px;
        top: 50%;
        width: 16px;
        height: 16px;
        transform: translateY(-50%);
        color: #7f8796;
      }}

      .logs-main {{
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
        gap: 16px;
        min-height: 0;
        overflow: hidden;
      }}

      .logs-list-panel,
      .logs-detail-panel {{
        min-height: 0;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        background: rgba(7, 10, 16, 0.86);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
        overflow: hidden;
      }}

      .logs-table {{
        height: 100%;
        display: grid;
        grid-template-rows: auto auto minmax(0, 1fr);
        min-height: 0;
      }}

      .logs-table-head,
      .log-row {{
        display: grid;
        grid-template-columns: 174px 224px minmax(0, 1fr);
        gap: 18px;
        align-items: center;
      }}

      .logs-table-head {{
        padding: 14px 20px 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        color: #99a1af;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }}

      .logs-table-body {{
        min-height: 0;
        overflow: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(153, 161, 175, 0.3) transparent;
      }}

      .logs-table-body::-webkit-scrollbar,
      .logs-detail-body::-webkit-scrollbar {{
        width: 10px;
      }}

      .logs-table-body::-webkit-scrollbar-thumb,
      .logs-detail-body::-webkit-scrollbar-thumb {{
        background: rgba(153, 161, 175, 0.28);
        border: 3px solid transparent;
        border-radius: 999px;
        background-clip: padding-box;
      }}

      .log-row {{
        width: 100%;
        border: 0;
        padding: 12px 20px;
        text-align: left;
        background: transparent;
        color: inherit;
        cursor: pointer;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        transition: background-color 140ms ease, border-color 140ms ease;
      }}

      .log-row:hover {{
        background: rgba(255, 255, 255, 0.035);
      }}

      .log-row:focus-visible {{
        outline: none;
        background: rgba(255, 255, 255, 0.05);
        box-shadow: inset 2px 0 0 #4d88f7, 0 0 0 1px rgba(77, 136, 247, 0.26);
      }}

      .log-row.is-active {{
        background: linear-gradient(90deg, rgba(50, 95, 182, 0.22), rgba(50, 95, 182, 0.06));
        box-shadow: inset 2px 0 0 #4d88f7;
      }}

      .log-row.is-error:not(.is-active) {{
        background: linear-gradient(90deg, rgba(198, 70, 70, 0.14), rgba(198, 70, 70, 0.03));
        box-shadow: inset 2px 0 0 rgba(239, 97, 97, 0.78);
      }}

      .log-row.is-error.is-active {{
        background: linear-gradient(90deg, rgba(198, 70, 70, 0.22), rgba(198, 70, 70, 0.06));
        box-shadow: inset 2px 0 0 #ef6161;
      }}

      .log-row.is-error .log-name {{
        color: #ffb4b4;
      }}

      .log-row.is-error .log-details {{
        color: #e2a1a1;
      }}

      .log-created {{
        color: #9aa3b2;
        font-size: 0.95rem;
        white-space: nowrap;
      }}

      .log-name {{
        color: #edf2fa;
        font-size: 1rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}

      .log-details {{
        color: #c7ceda;
        font-size: 0.96rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}

      .logs-detail-body {{
        height: 100%;
        overflow: auto;
        padding: 18px 18px 22px;
      }}

      .log-detail-top {{
        padding-bottom: 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      }}

      .log-detail-kicker {{
        color: #8c95a5;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }}

      .log-detail-title {{
        margin: 10px 0 0;
        font-size: 1.36rem;
        line-height: 1.1;
        font-weight: 700;
        letter-spacing: -0.035em;
      }}

      .log-detail-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 12px;
        color: #9da6b5;
        font-size: 0.9rem;
      }}

      .log-detail-badge {{
        display: inline-flex;
        align-items: center;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(77, 136, 247, 0.14);
        color: #b7d0ff;
      }}

      .log-detail-badge.is-error {{
        background: rgba(198, 70, 70, 0.16);
        color: #ffb8b8;
        box-shadow: inset 0 0 0 1px rgba(239, 97, 97, 0.24);
      }}

      .log-detail-summary {{
        margin: 12px 0 0;
        color: #dbe2ee;
        font-size: 0.96rem;
        line-height: 1.45;
      }}

      .log-section {{
        margin-top: 16px;
      }}

      .log-section-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 8px;
      }}

      .log-section-title {{
        margin: 0;
        color: #f1f5fb;
        font-size: 0.95rem;
        font-weight: 600;
      }}

      .log-section-copy {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.03);
        color: #aeb7c7;
        font-size: 0.8rem;
        line-height: 1;
        cursor: pointer;
        transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
      }}

      .log-section-copy:hover {{
        color: #f1f5fb;
        border-color: rgba(255, 255, 255, 0.16);
        background: rgba(255, 255, 255, 0.06);
      }}

      .log-section-copy.is-copied {{
        color: #d8f7d6;
        border-color: rgba(118, 204, 110, 0.28);
        background: rgba(118, 204, 110, 0.12);
      }}

      .log-section-body {{
        margin: 0;
        padding: 14px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.07);
        background: rgba(255, 255, 255, 0.025);
        color: #cdd5e1;
        font-size: 0.88rem;
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
        overflow-wrap: anywhere;
      }}

      .logs-empty {{
        padding: 28px 24px;
        color: #8f98a8;
      }}

      .logs-empty strong {{
        display: block;
        margin-bottom: 8px;
        color: #edf2fa;
        font-size: 1rem;
      }}

      .logs-list-empty {{
        display: none;
        padding: 28px 24px;
        color: #8f98a8;
      }}

      .logs-list-empty.is-visible {{
        display: block;
      }}

      mark.log-highlight {{
        padding: 0 0.16em;
        border-radius: 0.28em;
        background: rgba(255, 214, 102, 0.2);
        color: #fff4cc;
        box-shadow: inset 0 0 0 1px rgba(255, 214, 102, 0.18);
      }}

      .logs-templates {{
        display: none;
      }}

      @media (max-width: 1180px) {{
        .logs-table-head,
        .log-row {{
          grid-template-columns: 154px 190px minmax(0, 1fr);
        }}
      }}

      @media (max-width: 820px) {{
        .logs-toolbar {{
          flex-wrap: wrap;
        }}
      }}
    </style>
    <main class="page logs-page">
      <div class="shell app-shell logs-shell">
        <div class="logs-content">
          <header class="logs-header">
            <div class="detail-title-row">
              {chat_icon()}
              <div>
                <h1 class="detail-title">Agent Debug Logs</h1>
                <div class="detail-meta">{html.escape(summary.title)} &nbsp;&middot;&nbsp; Real-time trace from Copilot CLI session events</div>
              </div>
            </div>
            <a class="ghost-link" href="/sessions/{summary.session_id}">Back To Summary</a>
          </header>

          <div class="logs-toolbar">
            <label class="logs-filter" aria-label="Filter logs">
              <input id="log-filter" type="text" placeholder="Filter (e.g. text, tool name, event type)">
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
                <path d="M2 3.25h12l-4.7 5.28v3.54L6.7 13V8.53L2 3.25Z" />
              </svg>
            </label>
            <div class="logs-filter-meta" id="log-filter-meta">{len(log_entries)} events</div>
          </div>

          <section class="logs-main">
            <section class="logs-list-panel">
              <div class="logs-table">
                <div class="logs-table-head">
                  <span>Created</span>
                  <span>Name</span>
                  <span>Details</span>
                </div>
                <div class="logs-list-empty" id="log-list-empty">
                  <strong>No matching events</strong>
                  Try another keyword to inspect this session trace.
                </div>
                <div class="logs-table-body" id="log-list">{rows or render_empty_log_list()}
                </div>
              </div>
            </section>

            <aside class="logs-detail-panel">
              <div class="logs-detail-body" id="log-detail">{initial_detail}
              </div>
            </aside>
          </section>
        </div>
        {render_page_footer()}
      </div>

      <div class="logs-templates" aria-hidden="true">
        <template id="log-empty-template">{render_empty_log_detail()}</template>
        {templates}
      </div>

      <script>
        (() => {{
          const rows = Array.from(document.querySelectorAll('.log-row'));
          const sessionId = {json.dumps(summary.session_id)};
          const detailRoot = document.getElementById('log-detail');
          const logList = document.getElementById('log-list');
          const filterInput = document.getElementById('log-filter');
          const filterMeta = document.getElementById('log-filter-meta');
          const listEmptyState = document.getElementById('log-list-empty');
          const emptyTemplate = document.getElementById('log-empty-template');
          const templatesRoot = document.querySelector('.logs-templates');
          let eventSource = null;
          let isPolling = false;

          function escapeHtml(value) {{
            return value
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#39;');
          }}

          function escapeRegExp(value) {{
            return value.replace(/[][\\^$.*+?(){{}}|]/g, '\\$&');
          }}

          function highlightText(value, query) {{
            const escapedValue = escapeHtml(value);
            if (!query) {{
              return escapedValue;
            }}

            const pattern = new RegExp('(' + escapeRegExp(query) + ')', 'ig');
            return escapedValue.replace(pattern, '<mark class="log-highlight">$1</mark>');
          }}

          function applyRowHighlight(row, query) {{
            const created = row.querySelector('.log-created');
            const name = row.querySelector('.log-name');
            const details = row.querySelector('.log-details');

            if (created) {{
              created.innerHTML = highlightText(row.dataset.created || '', query);
            }}
            if (name) {{
              name.innerHTML = highlightText(row.dataset.name || '', query);
            }}
            if (details) {{
              details.innerHTML = highlightText(row.dataset.details || '', query);
            }}
          }}

          function restoreDetailForRow(row) {{
            if (!row) {{
              detailRoot.innerHTML = emptyTemplate ? emptyTemplate.innerHTML : '';
              return;
            }}

            const template = document.getElementById('log-detail-template-' + row.dataset.logIndex);
            detailRoot.innerHTML = template ? template.innerHTML : '';
          }}

          function applyDetailHighlight(query) {{
            const activeRow = rows.find((row) => row.classList.contains('is-active') && !row.hidden) || null;
            restoreDetailForRow(activeRow);
            if (!query || !activeRow) {{
              return;
            }}

            const selectors = [
              '.log-detail-title',
              '.log-detail-summary',
              '.log-section-body',
              '.log-detail-badge',
              '.log-section-title',
            ];

            selectors.forEach((selector) => {{
              detailRoot.querySelectorAll(selector).forEach((node) => {{
                node.innerHTML = highlightText(node.textContent || '', query);
              }});
            }});
          }}

          function visibleRows() {{
            return rows.filter((row) => !row.hidden);
          }}

          function firstVisibleRow() {{
            return visibleRows()[0] || null;
          }}

          function updateListEmptyState() {{
            if (!listEmptyState) {{
              return;
            }}

            listEmptyState.classList.toggle('is-visible', visibleRows().length === 0);
          }}

          function updateFilterMeta() {{
            if (!filterMeta) {{
              return;
            }}

            const currentVisibleRows = visibleRows();
            const activeIndex = currentVisibleRows.findIndex((row) => row.classList.contains('is-active'));
            const current = activeIndex >= 0 ? activeIndex + 1 : 0;
            filterMeta.textContent = String(current) + ' / ' + String(currentVisibleRows.length) + ' matches';
          }}

          function selectRow(row) {{
            rows.forEach((item) => item.classList.toggle('is-active', item === row));
            if (!row) {{
              restoreDetailForRow(null);
              updateListEmptyState();
              updateFilterMeta();
              return;
            }}

            restoreDetailForRow(row);
            applyDetailHighlight(filterInput ? filterInput.value.trim() : '');
            updateListEmptyState();
            updateFilterMeta();
            window.location.hash = 'log-' + row.dataset.logIndex;
          }}

          function moveSelection(offset) {{
            const currentVisibleRows = visibleRows();
            if (!currentVisibleRows.length) {{
              return;
            }}

            const activeIndex = currentVisibleRows.findIndex((row) => row.classList.contains('is-active'));
            const nextIndex = activeIndex >= 0
              ? (activeIndex + offset + currentVisibleRows.length) % currentVisibleRows.length
              : 0;
            const nextRow = currentVisibleRows[nextIndex];
            selectRow(nextRow);
            nextRow.focus();
            nextRow.scrollIntoView({{ block: 'nearest' }});
          }}

          function revealRow(row) {{
            if (!row) {{
              return;
            }}

            row.focus();
            row.scrollIntoView({{ block: 'nearest' }});
          }}

          function bindRow(row) {{
            row.addEventListener('click', () => selectRow(row));
            row.addEventListener('keydown', (event) => {{
              if (event.key === 'ArrowDown') {{
                event.preventDefault();
                moveSelection(1);
              }}
              if (event.key === 'ArrowUp') {{
                event.preventDefault();
                moveSelection(-1);
              }}
            }});
          }}

          function createNodeFromMarkup(markup) {{
            const template = document.createElement('template');
            template.innerHTML = markup.trim();
            return template.content.firstElementChild;
          }}

          function currentMaxLogIndex() {{
            return rows.reduce((maxIndex, row) => Math.max(maxIndex, Number(row.dataset.logIndex || '-1')), -1);
          }}

          function shouldFollowTail() {{
            const query = filterInput ? filterInput.value.trim() : '';
            if (query) {{
              return false;
            }}

            const activeRow = rows.find((row) => row.classList.contains('is-active')) || null;
            if (!activeRow) {{
              return true;
            }}

            return rows.length > 0 && rows[rows.length - 1] === activeRow;
          }}

          function appendLogEntry(entry) {{
            if (!logList || !templatesRoot) {{
              return null;
            }}

            const rowNode = createNodeFromMarkup(entry.rowHtml || '');
            const templateNode = createNodeFromMarkup(entry.detailTemplateHtml || '');
            if (!rowNode || !templateNode) {{
              return null;
            }}

            logList.appendChild(rowNode);
            templatesRoot.appendChild(templateNode);
            rows.push(rowNode);
            bindRow(rowNode);
            return rowNode;
          }}

          async function refreshLogs() {{
            if (isPolling || document.hidden) {{
              return;
            }}

            isPolling = true;
            try {{
              const response = await fetch('/sessions/' + encodeURIComponent(sessionId) + '/logs.json?after=' + String(currentMaxLogIndex()), {{
                headers: {{
                  'Accept': 'application/json',
                }},
              }});

              if (!response.ok) {{
                return;
              }}

              const payload = await response.json();
              const entries = Array.isArray(payload.entries) ? payload.entries : [];
              if (!entries.length) {{
                return;
              }}

              const followTail = shouldFollowTail();
              const query = filterInput ? filterInput.value.trim() : '';
              let newestRow = null;
              entries.forEach((entry) => {{
                const appendedRow = appendLogEntry(entry);
                if (appendedRow) {{
                  newestRow = appendedRow;
                }}
              }});

              rows.forEach((row) => {{
                row.hidden = !row.dataset.search.includes(query.toLowerCase());
                applyRowHighlight(row, query);
              }});

              if (followTail && newestRow && !newestRow.hidden) {{
                selectRow(newestRow);
                revealRow(newestRow);
                return;
              }}

              applyDetailHighlight(query);
              updateListEmptyState();
              updateFilterMeta();
            }} catch (_error) {{
              return;
            }} finally {{
              isPolling = false;
            }}
          }}

          rows.forEach((row) => bindRow(row));

          detailRoot.addEventListener('click', async (event) => {{
            const button = event.target.closest('.log-section-copy');
            if (!button) {{
              return;
            }}

            const section = button.closest('.log-section');
            const contentNode = section ? section.querySelector('.log-section-body') : null;
            if (!contentNode) {{
              return;
            }}

            const originalLabel = button.dataset.label || 'Copy';
            try {{
              await navigator.clipboard.writeText(contentNode.textContent || '');
              button.textContent = 'Copied';
              button.classList.add('is-copied');
            }} catch (_error) {{
              button.textContent = 'Failed';
            }}

            window.setTimeout(() => {{
              button.textContent = originalLabel;
              button.classList.remove('is-copied');
            }}, 1200);
          }});

          if (filterInput) {{
            filterInput.addEventListener('input', () => {{
              const query = filterInput.value.trim();
              const normalizedQuery = query.toLowerCase();

              rows.forEach((row) => {{
                row.hidden = !row.dataset.search.includes(normalizedQuery);
                applyRowHighlight(row, query);
              }});

              updateListEmptyState();

              const activeVisible = rows.find((row) => row.classList.contains('is-active') && !row.hidden);
              if (!activeVisible) {{
                selectRow(firstVisibleRow());
                return;
              }}

              applyDetailHighlight(query);
              updateFilterMeta();
            }});

            filterInput.addEventListener('keydown', (event) => {{
              if (event.key === 'ArrowDown') {{
                event.preventDefault();
                moveSelection(1);
              }}
              if (event.key === 'ArrowUp') {{
                event.preventDefault();
                moveSelection(-1);
              }}
            }});
          }}

          const hashMatch = window.location.hash.match(/^#log-([0-9]+)$/);
          if (hashMatch) {{
            const rowFromHash = document.querySelector('.log-row[data-log-index="' + hashMatch[1] + '"]');
            if (rowFromHash) {{
              selectRow(rowFromHash);
              revealRow(rowFromHash);
              return;
            }}
          }}

          selectRow(document.querySelector('.log-row.is-active') || firstVisibleRow());
          rows.forEach((row) => applyRowHighlight(row, ''));
          updateListEmptyState();
          updateFilterMeta();

          function closeLogsStream() {{
            if (!eventSource) {{
              return;
            }}

            eventSource.close();
            eventSource = null;
          }}

          function openLogsStream() {{
            if (eventSource || document.hidden || typeof EventSource !== 'function') {{
              return;
            }}

            eventSource = new EventSource('/sessions/' + encodeURIComponent(sessionId) + '/logs.events');
            eventSource.onmessage = () => {{
              refreshLogs();
            }};
            eventSource.onerror = () => {{
              return;
            }};
          }}

          openLogsStream();
          document.addEventListener('visibilitychange', () => {{
            if (document.hidden) {{
              closeLogsStream();
            }} else {{
              refreshLogs();
              openLogsStream();
            }}
          }});
          window.addEventListener('beforeunload', () => {{
            closeLogsStream();
          }});
        }})();
      </script>
    </main>
    """
    return render_document(f"{summary.title} Logs - {PAGE_TITLE}", body)


def build_logs_feed_payload(log_entries: list[SessionLogEntry], after_index: int = -1) -> dict[str, object]:
    entries = [entry for entry in log_entries if entry.index > after_index]
    return {
        "entries": [
            {
                "index": entry.index,
                "rowHtml": render_log_row(entry),
                "detailTemplateHtml": render_log_detail_template(entry),
            }
            for entry in entries
        ]
    }


def build_missing_session_page(session_id: str) -> str:
    body = f"""
    <main class="page detail-page">
      <div class="shell app-shell detail-shell">
        <div class="empty-state">
          <h1 class="empty-title">Session not found</h1>
          <p class="empty-copy">No readable Copilot CLI session metadata was found for <strong>{html.escape(session_id)}</strong>.</p>
          <p class="empty-copy"><a class="ghost-link" href="/">Back To Sessions</a></p>
        </div>
        {render_page_footer()}
      </div>
    </main>
    """
    return render_document(PAGE_TITLE, body)


def render_page_footer() -> str:
    return f"""
        <footer class="site-footer">
          <div class="site-footer-copy">
            Powered by <a href="{html.escape(REPOSITORY_URL, quote=True)}" target="_blank" rel="noreferrer">Copilot CLI Trace Deck</a><br>
            by <a href="{html.escape(AUTHOR_URL, quote=True)}" target="_blank" rel="noreferrer">Lanbao Shen</a>
          </div>
        </footer>"""


def build_index_feed_payload(session_previews: list[SessionPreview]) -> dict[str, object]:
    return {
        "count": len(session_previews),
        "itemsHtml": render_session_list_markup(session_previews),
    }


def render_session_list_markup(session_previews: list[SessionPreview]) -> str:
    return "\n".join(render_session_item(session) for session in session_previews)


def build_session_preview_meta(session: SessionPreview) -> str:
    items: list[str] = []
    if session.repository:
        items.append(session.repository)
    if session.branch:
        items.append(session.branch)
    if session.model_name:
        items.append(session.model_name)

    if session.updated_label:
        items.append(f"Updated {session.updated_label}")

    return "".join(f'<span class="session-meta-item">{html.escape(item)}</span>' for item in items)


def render_session_item(session: SessionPreview) -> str:
    title = html.escape(session.title)
    badge = '<span class="badge">Active</span>' if session.is_active else ""
    meta = build_session_preview_meta(session)
    return f"""
          <li data-session-id="{html.escape(session.session_id, quote=True)}">
            <a class="session-link" href="/sessions/{session.session_id}" aria-label="Open {title}">
              <div class="session-main">
                {chat_icon()}
                <div class="session-copy">
                  <p class="session-title">{title}</p>
                  <div class="session-meta">{meta}</div>
                </div>
              </div>
              {badge}
            </a>
          </li>"""


def build_summary_stat_labels(summary: SessionSummary) -> dict[str, str]:
    if summary.status == "Active":
        return {
            "totalInputLabel": "Input Tokens (Finalized)",
            "totalCachedInputLabel": "Cached Input (Finalized)",
            "totalCacheWriteLabel": "Cache Write (Finalized)",
        }
    return {
        "totalInputLabel": "Total Input Tokens",
        "totalCachedInputLabel": "Total Cached Input Tokens",
        "totalCacheWriteLabel": "Total Cache Write Tokens",
    }


def render_stat_card(label: str, value: int | str, value_id: str | None = None, label_id: str | None = None) -> str:
  return render_live_stat_card(label, value, value_id=value_id, label_id=label_id)


def render_live_stat_card(label: str, value: int | str, value_id: str | None = None, label_id: str | None = None) -> str:
    label_id_attr = f' id="{html.escape(label_id, quote=True)}"' if label_id else ''
    value_id_attr = f' id="{html.escape(value_id, quote=True)}"' if value_id else ''
    return f"""
              <article class="stat-card">
                <span class="stat-label"{label_id_attr}>{html.escape(label)}</span>
                <span class="stat-value"{value_id_attr}>{html.escape(format_stat_value(value))}</span>
              </article>"""


def render_action_chip(label: str, href: str = "#") -> str:
    return f'<a class="action-chip" href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'


def render_flow_node(session_id: str, node: SessionFlowNode) -> str:
    kind_class = f"is-{node.kind}"
    status_class = "is-error" if node.status == "error" else ""
    pill = f'+{node.count - 1} more' if node.kind == 'group' and node.count > 1 else ''
    pill_markup = f'<span class="flow-card-pill">{html.escape(pill)}</span>' if pill else ''
    meta_markup = f'<div class="flow-card-meta">{html.escape(node.meta)}</div>' if node.meta else ''
    card_markup = f"""
                <div class="flow-card {kind_class} {status_class}">
                  <div class="flow-card-top">
                    <div class="flow-card-title-wrap">
                      <h2 class="flow-card-title">{html.escape(node.title)}</h2>
                      <div class="flow-card-subtitle">{html.escape(node.subtitle)}</div>
                    </div>
                    {pill_markup}
                  </div>
                  <div class="flow-card-body">{html.escape(node.detail)}</div>
                  {meta_markup}
                </div>"""
    if node.log_index is not None:
        return f"""
              <article class="flow-step" data-flow-index="{node.index}">
                <a class="flow-link" href="/sessions/{html.escape(session_id, quote=True)}/logs#log-{node.log_index}" aria-label="Open {html.escape(node.title)} in logs">
                  {card_markup}
                </a>
              </article>"""
    return f"""
              <article class="flow-step" data-flow-index="{node.index}">
                {card_markup}
              </article>"""


def render_empty_flow_state() -> str:
    return """
              <div class="flow-empty">
                <strong>No flow nodes available</strong>
                This session does not have enough structured events to reconstruct an agent flow chart yet.
              </div>"""


def build_session_snapshot_payload(summary: SessionSummary) -> dict[str, str]:
  stat_labels = build_summary_stat_labels(summary)
  return {
    "detailMeta": build_session_detail_meta(summary),
    "sessionType": summary.session_type,
    "location": summary.location,
    "status": summary.status,
    "createdLabel": summary.created_label,
    "updatedLabel": summary.updated_label,
    "totalInputLabel": stat_labels["totalInputLabel"],
    "totalCachedInputLabel": stat_labels["totalCachedInputLabel"],
    "totalCacheWriteLabel": stat_labels["totalCacheWriteLabel"],
    "modelTurns": format_number(summary.model_turns),
    "toolCalls": format_number(summary.tool_calls),
    "totalInputTokens": format_number(summary.total_input_tokens),
    "totalOutputTokens": format_number(summary.total_output_tokens),
    "totalCachedInputTokens": format_number(summary.total_cached_input_tokens),
    "totalCacheWriteTokens": format_number(summary.total_cache_write_tokens),
    "totalTokens": format_number(summary.total_tokens),
    "estimatedAiCredits": format_ai_credits(summary.estimated_ai_credits),
    "estimatedCostUsd": format_currency(summary.estimated_cost_usd),
    "billingNote": summary.billing_note,
    "modelUsageBreakdownHtml": render_model_usage_breakdown(summary),
    "errorCount": format_number(summary.error_count),
  }


def build_flow_feed_payload(session_id: str, summary: SessionSummary, flow_nodes: list[SessionFlowNode], after_index: int = -1) -> dict[str, object]:
  nodes = [node for node in flow_nodes if node.index > after_index]
  return {
    "nodeCount": len(flow_nodes),
    "modelName": summary.model_name,
    "toolCalls": summary.tool_calls,
    "errorCount": summary.error_count,
    "nodes": [
      {
        "index": node.index,
        "html": render_flow_node(session_id, node),
      }
      for node in nodes
    ],
  }


def render_log_row(entry: SessionLogEntry, selected: bool = False) -> str:
    classes = "log-row is-error" if entry.is_error else "log-row"
    if selected:
        classes += " is-active"
    section_search = " ".join(f"{section.title} {section.content}" for section in entry.sections)
    search_value = " ".join([entry.created_label, entry.name, entry.event_type, entry.details, section_search]).lower()
    return f"""
                <button class="{classes}" type="button" data-log-index="{entry.index}" data-error="{'true' if entry.is_error else 'false'}" data-event-type="{html.escape(entry.event_type, quote=True)}" data-search="{html.escape(search_value, quote=True)}" data-created="{html.escape(entry.created_label, quote=True)}" data-name="{html.escape(entry.name, quote=True)}" data-details="{html.escape(entry.details, quote=True)}">
                  <span class="log-created">{html.escape(entry.created_label)}</span>
                  <span class="log-name">{html.escape(entry.name)}</span>
                  <span class="log-details">{html.escape(entry.details)}</span>
                </button>"""


def render_log_detail_template(entry: SessionLogEntry) -> str:
    return f'<template id="log-detail-template-{entry.index}">{render_log_detail(entry)}</template>'


def render_log_detail(entry: SessionLogEntry) -> str:
    sections = "\n".join(render_log_section(section) for section in entry.sections)
    badge_class = "log-detail-badge is-error" if entry.is_error else "log-detail-badge"
    return f"""
            <div class="log-detail-top">
              <div class="log-detail-kicker">Event Inspector</div>
              <h2 class="log-detail-title">{html.escape(entry.name)}</h2>
              <div class="log-detail-meta">
                <span class="{badge_class}">{html.escape(entry.event_type)}</span>
                <span>{html.escape(entry.created_label)}</span>
              </div>
              <p class="log-detail-summary">{html.escape(entry.details)}</p>
            </div>
            {sections}
    """


def render_log_section(section: SessionLogSection) -> str:
    return f"""
            <section class="log-section">
              <div class="log-section-header">
                <h3 class="log-section-title">{html.escape(section.title)}</h3>
                <button class="log-section-copy" type="button" data-label="Copy">Copy</button>
              </div>
              <pre class="log-section-body">{html.escape(section.content)}</pre>
            </section>"""


def render_empty_log_detail() -> str:
    return """
            <div class="logs-empty">
              <strong>No log selected</strong>
              Refine the filter or choose another event from the list.
            </div>"""


def render_empty_log_list() -> str:
    return """
                <div class="logs-empty">
                  <strong>No events found</strong>
                  This session does not have readable debug log events yet.
                </div>"""


def build_session_detail_meta(summary: SessionSummary) -> str:
    label = "Models" if len(summary.model_usages) > 1 else "Model"
    return f"{label}: {summary.models_used_label or 'Unknown'} · Repository: {summary.repository or '-'} · Branch: {summary.branch or '-'}"


def chat_icon() -> str:
    return """<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M6.25 5.25h11.5A2.25 2.25 0 0 1 20 7.5v7A2.25 2.25 0 0 1 17.75 16.75H11l-3.9 3.23c-.72.6-1.85.08-1.85-.86v-2.37A2.25 2.25 0 0 1 3 14.5v-7a2.25 2.25 0 0 1 2.25-2.25Z" />
                </svg>"""


def format_number(value: int) -> str:
    return f"{value:,}"


def format_stat_value(value: int | str) -> str:
    return format_number(value) if isinstance(value, int) else value


def format_currency(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"${value.quantize(Decimal('0.000001')):,.6f}".rstrip("0").rstrip(".")


def format_ai_credits(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{value.quantize(Decimal('0.0001')):,.4f}".rstrip("0").rstrip(".")


def render_model_usage_breakdown(summary: SessionSummary) -> str:
    if not summary.model_usages:
        return '<div class="model-usage-empty">No per-model usage metrics available yet.</div>'

    rows = "\n".join(
        f"""
                  <tr>
                    <td>{html.escape(item.model_name)}</td>
                    <td>{format_number(item.input_tokens)}</td>
                    <td>{format_number(item.cached_input_tokens)}</td>
                    <td>{format_number(item.cache_write_tokens)}</td>
                    <td>{format_number(item.output_tokens)}</td>
                    <td>{format_number(item.total_tokens)}</td>
                    <td>{html.escape(format_currency(item.estimated_cost_usd))}</td>
                  </tr>"""
        for item in summary.model_usages
    )
    return f"""
              <div class="model-usage-title">Model Usage Breakdown</div>
              <div class="model-usage-scroller">
                <table class="model-usage-table">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Input</th>
                      <th>Cached Input</th>
                      <th>Cache Write</th>
                      <th>Output</th>
                      <th>Total</th>
                      <th>Est. USD</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows}
                  </tbody>
                </table>
              </div>"""
