"""Reusable Lakebase search playground widgets for Databricks notebooks.

Following the user's reusable-widget convention, this module exposes three
notebook-native anywidget widgets for explaining vector, text, and hybrid
search behavior in a Lakebase demo.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

import anywidget
import numpy as np
import traitlets


_SEARCH_ESM = r'''
function render({ model, el }) {
  if (!document.querySelector('link[data-db-fonts]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.dataset.dbFonts = '1';
    link.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap';
    document.head.appendChild(link);
  }

  const style = document.createElement('style');
  style.textContent = `
    .lbsw-root {
      --font-sans: "DM Sans", system-ui, -apple-system, sans-serif;
      --font-mono: "DM Mono", ui-monospace, "SFMono-Regular", monospace;
      --color-lava-600: #FF3621;
      --color-lava-500: #FF5A45;
      --color-lava-700: #DB2B18;
      --color-navy-900: #0B2026;
      --color-navy-800: #1B3A42;
      --color-navy-700: #2C545E;
      --color-oat-medium: #EEEDE9;
      --color-oat-light: #F9F7F4;
      --color-white: #FFFFFF;
      --color-success: #00A972;
      --color-warning: #F2960D;
      --color-error: #E5231F;
      --color-info: #1B73E8;
      --color-text-primary: #0B2026;
      --color-text-secondary: #5F6B6E;
      --color-text-disabled: #A3ABAE;
      --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
      --space-5: 20px; --space-6: 24px; --space-8: 32px;
      --radius-sm: 2px; --radius-md: 4px; --radius-lg: 4px; --radius-full: 2px;
      --shadow-sm: none;
      --shadow-md: 0 1px 3px rgba(11, 32, 38, 0.06);
      --transition-fast: 120ms ease;
      font-family: var(--font-sans);
      font-size: 14px;
      line-height: 1.5;
      color: var(--color-text-primary);
      width: 100%;
      max-width: 100%;
      box-sizing: border-box;
    }
    .lbsw-root *, .lbsw-root *::before, .lbsw-root *::after { box-sizing: border-box; }
    .lbsw-shell {
      background: var(--color-white);
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
      max-height: 560px;
      overflow-y: auto;
      scroll-behavior: smooth;
    }
    .lbsw-shell::-webkit-scrollbar { width: 6px; }
    .lbsw-shell::-webkit-scrollbar-track { background: transparent; }
    .lbsw-shell::-webkit-scrollbar-thumb {
      background: rgba(11, 32, 38, 0.15);
      border-radius: var(--radius-full);
    }
    .lbsw-shell::-webkit-scrollbar-thumb:hover { background: rgba(11, 32, 38, 0.3); }
    .lbsw-header {
      padding: var(--space-5) var(--space-6);
      background: var(--color-navy-900);
      color: var(--color-white);
    }
    .lbsw-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: var(--space-4);
      flex-wrap: wrap;
    }
    .lbsw-title {
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 0;
    }
    .lbsw-subtitle {
      margin-top: 4px;
      color: rgba(255,255,255,0.65);
      font-size: 13px;
      max-width: 780px;
    }
    .lbsw-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      background: rgba(255,255,255,0.10);
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .lbsw-controls {
      padding: var(--space-5) var(--space-6);
      background: var(--color-oat-light);
      border-bottom: 1px solid var(--color-oat-medium);
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));

      gap: var(--space-3);
      align-items: end;
    }
    .lbsw-field { display: flex; flex-direction: column; gap: 4px; }
    .lbsw-span-4 { grid-column: span 4; }
    .lbsw-span-3 { grid-column: span 3; }
    .lbsw-span-2 { grid-column: span 2; }
    .lbsw-span-1 { grid-column: span 1; }
    .lbsw-label {
      font-size: 12px;
      font-weight: 500;
      color: var(--color-text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .lbsw-input {
      width: 100%;
      min-height: 34px;
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-md);
      background: var(--color-white);
      color: var(--color-text-primary);
      padding: 6px 10px;
      font: inherit;
      font-size: 13px;
      transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    }
    .lbsw-input:focus {
      outline: none;
      border-color: var(--color-lava-600);
      box-shadow: 0 0 0 3px rgba(255, 54, 33, 0.10);
    }
    .lbsw-button {
      min-height: 34px;
      border: none;
      border-radius: var(--radius-md);
      background: var(--color-lava-600);
      color: var(--color-white);
      font: inherit;
      font-weight: 600;
      padding: 8px 14px;
      cursor: pointer;
      transition: background var(--transition-fast);
    }
    .lbsw-button:hover { background: var(--color-lava-500); }
    .lbsw-button:active { background: var(--color-lava-700); }
    .lbsw-button:disabled { background: #c9c8c4; cursor: not-allowed; }
    .lbsw-main {
      padding: var(--space-6);
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--space-5);
      align-items: start;
    }
    .lbsw-card {
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-lg);
      background: var(--color-white);
      box-shadow: var(--shadow-sm);
      overflow: hidden;
    }
    .lbsw-card-header {
      padding: 14px 16px;
      border-bottom: 1px solid var(--color-oat-medium);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .lbsw-card-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text-primary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .lbsw-card-subtitle {
      font-size: 12px;
      color: var(--color-text-secondary);
    }
    .lbsw-card-body { padding: 16px; }
    .lbsw-select {
      width: 100%;
      min-height: 34px;
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-md);
      background: var(--color-white);
      color: var(--color-text-primary);
      padding: 6px 10px;
      font: inherit;
      font-size: 13px;
      cursor: pointer;
      transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
      appearance: none;
      -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%235F6B6E' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 10px center;
      padding-right: 28px;
    }
    .lbsw-select:focus {
      outline: none;
      border-color: var(--color-lava-600);
      box-shadow: 0 0 0 3px rgba(255, 54, 33, 0.10);
    }
    .lbsw-vector-preview {
      margin-top: 6px;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--color-text-disabled);
      word-break: break-all;
      line-height: 1.4;
    }
    .lbsw-status { font-size: 13px; color: var(--color-text-secondary); }
    .lbsw-error {
      margin: 16px;
      padding: 12px 14px;
      border-radius: var(--radius-md);
      background: rgba(229, 35, 31, 0.08);
      color: var(--color-error);
      border: 1px solid rgba(229, 35, 31, 0.18);
      white-space: pre-wrap;
    }
    .lbsw-kpis {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .lbsw-kpi {
      padding: 12px;
      border-radius: var(--radius-md);
      background: var(--color-oat-light);
      border: 1px solid var(--color-oat-medium);
    }
    .lbsw-kpi-label {
      font-size: 11px;
      color: var(--color-text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .lbsw-kpi-value {
      margin-top: 4px;
      font-family: var(--font-mono);
      font-size: 14px;
      font-weight: 500;
      color: var(--color-text-primary);
      word-break: break-all;
    }
    .lbsw-code {
      margin-top: 0;
      border-radius: var(--radius-md);
      background: var(--color-navy-900);
      color: #e8f0f2;
      padding: 16px 20px;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.65;
      overflow-x: auto;
      white-space: pre;
    }
    .lbsw-sql-area {
      width: 100%;
      min-height: 120px;
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-md);
      background: var(--color-navy-900);
      color: #e8f0f2;
      padding: 14px 16px;
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.65;
      resize: vertical;
      white-space: pre;
      tab-size: 2;
      overflow: auto;
    }
    .lbsw-sql-area:focus {
      outline: none;
      border-color: var(--color-lava-600);
      box-shadow: 0 0 0 3px rgba(255, 54, 33, 0.10);
    }
    .lbsw-sql-section {
      padding: 0 var(--space-6) var(--space-3);
      margin-top: var(--space-4);
    }
    .lbsw-editor-wrap {
      position: relative;
      border-radius: var(--radius-md);
      overflow: hidden;
    }
    .lbsw-highlight-layer {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      pointer-events: none;
      margin-top: 0;
      overflow: auto;
    }
    .lbsw-editor-wrap .lbsw-sql-area {
      position: relative;
      background: transparent;
      color: transparent;
      caret-color: #e8f0f2;
      z-index: 1;
      border: 1px solid var(--color-oat-medium);
    }
    .lbsw-button-section {
      padding: 0 var(--space-6) var(--space-4);
    }
    .lbsw-button-full {
      width: 100%;
    }
    .lbsw-sql-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .lbsw-sql-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text-primary);
    }
    .lbsw-code .kw { color: #7EC8E3; }
    .lbsw-code .fn { color: #C3E88D; }
    .lbsw-code .str { color: #F78C6C; }
    .lbsw-code .num { color: #F78C6C; }
    .lbsw-code .cmt { color: #6a8a7a; font-style: italic; }
    .lbsw-code .op { color: #89DDFF; }
    .lbsw-code .param { color: #FFCB6B; }
    .lbsw-perf {
      display: inline-flex; align-items: center; gap: 6px;
      margin-left: 12px; font-size: 12px; color: var(--color-text-secondary);
      font-family: var(--font-mono);
    }
    .lbsw-perf-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-success); display: inline-block; }
    .lbsw-empty {
      padding: 28px 20px;
      text-align: center;
      color: var(--color-text-secondary);
      background: var(--color-oat-light);
      border-radius: var(--radius-md);
      border: 1px dashed var(--color-oat-medium);
    }
    .lbsw-scatter {
      width: 100%;
      height: auto;
      display: block;
      background: var(--color-white);
      border-radius: var(--radius-md);
      border: 1px solid var(--color-oat-medium);
      overflow: hidden;
      touch-action: none;
    }
    .lbsw-legend {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      margin-top: 12px;
      font-size: 12px;
      color: var(--color-text-secondary);
    }
    .lbsw-dot {
      width: 8px; height: 8px; border-radius: 2px; display: inline-block; margin-right: 6px;
    }
    .lbsw-results { display: flex; flex-direction: column; gap: 12px; }
    .lbsw-result {
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-md);
      padding: 14px;
      background: var(--color-white);
    }
    .lbsw-result-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }
    .lbsw-result-rank {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--color-text-secondary);
      font-weight: 600;
    }
    .lbsw-result-title {
      margin-top: 2px;
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text-primary);
    }
    .lbsw-result-score {
      font-family: var(--font-mono);
      font-size: 13px;
      color: var(--color-text-secondary);
      white-space: nowrap;
    }
    .lbsw-result-meta {
      margin-top: 10px;
      font-size: 12px;
      color: var(--color-text-secondary);
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
    .lbsw-bar-track {
      margin-top: 10px;
      width: 100%;
      height: 6px;
      border-radius: var(--radius-sm);
      background: var(--color-oat-medium);
      overflow: hidden;
      position: relative;
    }
    .lbsw-bar-fill {
      height: 100%;
      border-radius: var(--radius-sm);
      background: var(--color-lava-600);
    }
    .lbsw-stack {
      display: flex;
      width: 100%;
      height: 12px;
      border-radius: var(--radius-sm);
      overflow: hidden;
      background: var(--color-oat-medium);
      margin-top: 10px;
    }
    .lbsw-stack-vector { background: var(--color-info); }
    .lbsw-stack-text { background: var(--color-warning); }
    .lbsw-inline-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }
    .lbsw-chip {
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: var(--radius-sm);
      background: var(--color-oat-light);
      border: 1px solid var(--color-oat-medium);
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--color-text-secondary);
    }
    /* ── Tabs ── */
    .lbsw-tabs {
      display: flex;
      border-bottom: 2px solid var(--color-oat-medium);
      padding: 0 var(--space-6);
      gap: 0;
    }
    .lbsw-tab {
      padding: 10px 18px;
      font-size: 13px;
      font-weight: 600;
      font-family: inherit;
      color: var(--color-text-secondary);
      cursor: pointer;
      border: none;
      background: none;
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
      transition: color var(--transition-fast), border-color var(--transition-fast);
    }
    .lbsw-tab:hover { color: var(--color-text-primary); }
    .lbsw-tab-active {
      color: var(--color-lava-600);
      border-bottom-color: var(--color-lava-600);
    }
    .lbsw-tab-spacer { flex: 1; }
    .lbsw-tab-badge {
      display: inline-flex;
      align-items: center;
      font-size: 10px;
      font-family: var(--font-mono);
      color: var(--color-text-secondary);
      background: var(--color-oat-medium);
      border-radius: var(--radius-full);
      padding: 2px 8px;
      white-space: nowrap;
      margin-right: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .lbsw-tab-perf {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-family: var(--font-mono);
      color: var(--color-text-secondary);
      padding-right: 4px;
      white-space: nowrap;
    }
    .lbsw-tab-panel { display: none; padding: var(--space-5) var(--space-6); }
    .lbsw-tab-panel-active { display: block; }

    /* ── Results table ── */
    .lbsw-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .lbsw-table th {
      text-align: left;
      padding: 10px 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--color-text-secondary);
      border-bottom: 2px solid var(--color-oat-medium);
      white-space: nowrap;
      position: sticky;
      top: 0;
      background: var(--color-white);
    }
    .lbsw-table td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--color-oat-light);
      color: var(--color-text-primary);
      max-width: 340px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      vertical-align: top;
    }
    .lbsw-table tr:hover td { background: var(--color-oat-light); }
    .lbsw-table .lbsw-mono {
      font-family: var(--font-mono);
      font-size: 12px;
    }
    .lbsw-table-wrap {
      overflow-x: auto;
      border: 1px solid var(--color-oat-medium);
      border-radius: var(--radius-lg);
      background: var(--color-white);
    }

    /* ── Scatter tooltip ── */
    .lbsw-tooltip {
      position: absolute;
      pointer-events: none;
      padding: 5px 10px;
      border-radius: var(--radius-sm);
      background: var(--color-navy-900);
      color: #e8f0f2;
      font-size: 11px;
      font-family: var(--font-mono);
      white-space: nowrap;
      z-index: 10;
      opacity: 0;
      transition: opacity 0.12s;
    }
    .lbsw-tooltip-visible { opacity: 1; }

    .lbsw-formula {
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      background: var(--color-oat-light);
      color: var(--color-navy-900);
      border: 1px solid var(--color-oat-medium);
      font-family: var(--font-mono);
      font-size: 12px;
      margin-bottom: 14px;
    }
    .lbsw-fs-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px; height: 32px;
      border: none;
      border-radius: var(--radius-md);
      background: rgba(255,255,255,0.12);
      color: var(--color-white);
      cursor: pointer;
      transition: background var(--transition-fast);
      flex-shrink: 0;
    }
    .lbsw-fs-btn:hover { background: rgba(255,255,255,0.22); }
    .lbsw-fs-btn:focus-visible {
      outline: 2px solid var(--color-white);
      outline-offset: 2px;
    }
    .lbsw-fs-btn svg {
      width: 16px; height: 16px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .lbsw-shell:fullscreen,
    .lbsw-shell:-webkit-full-screen {
      max-height: none;
      overflow-y: auto;
      border-radius: 0;
      border: none;
      box-shadow: none;
      background: var(--color-white);
    }
    .lbsw-shell:fullscreen .lbsw-main,
    .lbsw-shell:-webkit-full-screen .lbsw-main {
      max-width: 1400px;
      margin: 0 auto;
    }
    @media (max-width: 940px) {
      .lbsw-main { grid-template-columns: 1fr; }
      .lbsw-span-4, .lbsw-span-3, .lbsw-span-2, .lbsw-span-1 { grid-column: span 12; }
      .lbsw-kpis { grid-template-columns: 1fr; }
    }
  `;

  const root = document.createElement('div');
  root.className = 'lbsw-root';
  const shell = document.createElement('div');
  shell.className = 'lbsw-shell';
  root.appendChild(shell);
  el.replaceChildren(style, root);

  const svgExpand = '<svg viewBox="0 0 24 24"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const svgCollapse = '<svg viewBox="0 0 24 24"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';

  const isFs = () => {
    const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
    return fsEl && root.contains(fsEl);
  };
  const syncFsBtn = () => {
    const btn = root.querySelector('.lbsw-fs-btn');
    if (btn) {
      const fs = isFs();
      btn.innerHTML = fs ? svgCollapse : svgExpand;
      btn.title = fs ? 'Exit fullscreen' : 'Fullscreen';
    }
  };
  const toggleFullscreen = () => {
    if (isFs()) {
      (document.exitFullscreen || document.webkitExitFullscreen || (() => {})).call(document);
    } else if (shell.requestFullscreen) {
      shell.requestFullscreen().catch(() => {});
    } else if (shell.webkitRequestFullscreen) {
      shell.webkitRequestFullscreen();
    }
  };
  const onFsChange = () => syncFsBtn();
  document.addEventListener('fullscreenchange', onFsChange);
  document.addEventListener('webkitfullscreenchange', onFsChange);

  const parsePayload = () => {
    try {
      return JSON.parse(model.get('payload_json') || '{}');
    } catch (err) {
      return { parse_error: String(err) };
    }
  };

  const setTrait = (name, value) => {
    model.set(name, value);
    model.save_changes();
  };

  const create = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  };

  const createField = ({ label, type = 'text', value = '', min = null, step = null, onCommit }) => {
    const wrap = create('div', 'lbsw-field');
    const lab = create('label', 'lbsw-label', label);
    const input = create('input', 'lbsw-input');
    input.type = type;
    input.value = value ?? '';
    if (min !== null) input.min = String(min);
    if (step !== null) input.step = String(step);
    input.addEventListener('change', () => onCommit(type === 'number' ? Number(input.value) : input.value));
    wrap.append(lab, input);
    return wrap;
  };

  const createSelect = ({ label, value = '', options = [], onCommit }) => {
    const wrap = create('div', 'lbsw-field');
    const lab = create('label', 'lbsw-label', label);
    const select = create('select', 'lbsw-select');
    const seen = new Set();
    for (const opt of options) {
      const o = create('option');
      const isObj = typeof opt === 'object' && opt !== null;
      const val = isObj ? opt.value : opt;
      const txt = isObj ? (opt.label || opt.value) : opt;
      o.value = val;
      o.textContent = txt;
      if (val === value || val === String(value)) o.selected = true;
      select.append(o);
      seen.add(val);
    }
    if (value && !seen.has(value) && !seen.has(String(value))) {
      const o = create('option');
      o.value = value;
      o.textContent = value;
      o.selected = true;
      select.prepend(o);
    }
    select.addEventListener('change', () => onCommit(select.value));
    wrap.append(lab, select);
    return wrap;
  };

  const toPercent = (value) => `${Math.max(0, Math.min(100, value * 100)).toFixed(1)}%`;

  const renderKpis = (body, payload) => {
    const kpis = payload.kpis || [];
    if (!kpis.length) return;
    const wrap = create('div', 'lbsw-kpis');
    for (const item of kpis) {
      const card = create('div', 'lbsw-kpi');
      card.append(
        create('div', 'lbsw-kpi-label', item.label || ''),
        create('div', 'lbsw-kpi-value', item.value || '')
      );
      wrap.append(card);
    }
    body.append(wrap);
  };

  const renderVectorViz = (body, payload) => {
    const projection = payload.projection || {};
    const points = projection.points || [];
    if (!points.length) {
      body.append(create('div', 'lbsw-empty', 'Run a search to project the query embedding near the indexed documents.'));
      return;
    }

    const width = 520;
    const height = 320;
    const pad = 28;
    const xs = points.map(p => Number(p.x || 0));
    const ys = points.map(p => Number(p.y || 0));
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const scaleX = (x) => pad + ((x - minX) / ((maxX - minX) || 1)) * (width - pad * 2);
    const scaleY = (y) => height - pad - ((y - minY) / ((maxY - minY) || 1)) * (height - pad * 2);

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.setAttribute('class', 'lbsw-scatter');
    svg.style.cursor = 'grab';

    /* Zoomable group wrapping all content */
    const zg = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    let zScale = 1, zTx = 0, zTy = 0;
    const applyZoom = () => zg.setAttribute('transform', `translate(${zTx},${zTy}) scale(${zScale})`);

    /* Grid lines */
    for (const xGuide of [pad, width / 2, width - pad]) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', xGuide); line.setAttribute('x2', xGuide);
      line.setAttribute('y1', pad / 2); line.setAttribute('y2', height - pad / 2);
      line.setAttribute('stroke', '#f0efec'); line.setAttribute('stroke-width', '1');
      zg.appendChild(line);
    }
    for (const yGuide of [pad, height / 2, height - pad]) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', pad / 2); line.setAttribute('x2', width - pad / 2);
      line.setAttribute('y1', yGuide); line.setAttribute('y2', yGuide);
      line.setAttribute('stroke', '#f0efec'); line.setAttribute('stroke-width', '1');
      zg.appendChild(line);
    }

    /* Connection lines from query to returned results */
    const queryPt = points.find(p => p.type === 'query');
    if (queryPt) {
      const qx = scaleX(Number(queryPt.x || 0));
      const qy = scaleY(Number(queryPt.y || 0));
      for (const pt of points) {
        if (pt.highlight && pt.type !== 'query') {
          const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
          line.setAttribute('x1', qx); line.setAttribute('y1', qy);
          line.setAttribute('x2', scaleX(Number(pt.x || 0)));
          line.setAttribute('y2', scaleY(Number(pt.y || 0)));
          line.setAttribute('stroke', '#7C4DFF');
          line.setAttribute('stroke-width', '1.2');
          line.setAttribute('stroke-dasharray', '5,4');
          line.setAttribute('stroke-opacity', '0.45');
          zg.appendChild(line);
        }
      }
    }

    /* Data points + hover tooltip */
    const svgWrap = create('div');
    svgWrap.style.position = 'relative'; svgWrap.style.display = 'inline-block'; svgWrap.style.width = '100%';
    const tip = create('div', 'lbsw-tooltip');
    svgWrap.append(tip);

    for (const point of points) {
      const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      const cx = scaleX(Number(point.x || 0));
      const cy = scaleY(Number(point.y || 0));
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', cx);
      circle.setAttribute('cy', cy);
      circle.setAttribute('r', point.type === 'query' ? '8' : (point.highlight ? '6' : '4.5'));
      circle.setAttribute('fill', point.type === 'query' ? '#FF3621' : (point.highlight ? '#7C4DFF' : '#B7C5CB'));
      circle.setAttribute('stroke', point.type === 'query' ? '#ffffff' : '#ffffff');
      circle.setAttribute('stroke-width', point.type === 'query' ? '2.5' : '1.5');
      circle.style.cursor = 'pointer';
      /* Only permanent label for the query point */
      if (point.type === 'query') {
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', cx + 10); text.setAttribute('y', cy - 8);
        text.setAttribute('font-size', '11');
        text.setAttribute('font-family', 'DM Sans, system-ui, sans-serif');
        text.setAttribute('fill', '#2C545E');
        text.textContent = 'Query';
        group.appendChild(text);
      }
      /* Hover tooltip for all points */
      const label = point.label || '';
      group.addEventListener('mouseenter', (e) => {
        tip.textContent = label;
        tip.classList.add('lbsw-tooltip-visible');
        const rect = svgWrap.getBoundingClientRect();
        tip.style.left = (e.clientX - rect.left + 12) + 'px';
        tip.style.top = (e.clientY - rect.top - 28) + 'px';
      });
      group.addEventListener('mousemove', (e) => {
        const rect = svgWrap.getBoundingClientRect();
        tip.style.left = (e.clientX - rect.left + 12) + 'px';
        tip.style.top = (e.clientY - rect.top - 28) + 'px';
      });
      group.addEventListener('mouseleave', () => tip.classList.remove('lbsw-tooltip-visible'));
      group.appendChild(circle);
      zg.appendChild(group);
    }

    svg.appendChild(zg);
    svgWrap.prepend(svg);

    /* Wheel zoom */
    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = svg.getBoundingClientRect();
      const mx = (e.clientX - rect.left) / rect.width * width;
      const my = (e.clientY - rect.top) / rect.height * height;
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      const newScale = Math.min(Math.max(zScale * factor, 0.5), 12);
      zTx = mx - (mx - zTx) * (newScale / zScale);
      zTy = my - (my - zTy) * (newScale / zScale);
      zScale = newScale;
      applyZoom();
    }, { passive: false });

    /* Drag pan */
    let dragging = false, dragX = 0, dragY = 0;
    svg.addEventListener('pointerdown', (e) => {
      dragging = true; dragX = e.clientX; dragY = e.clientY;
      svg.style.cursor = 'grabbing'; svg.setPointerCapture(e.pointerId);
    });
    svg.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const rect = svg.getBoundingClientRect();
      zTx += (e.clientX - dragX) / rect.width * width;
      zTy += (e.clientY - dragY) / rect.height * height;
      dragX = e.clientX; dragY = e.clientY;
      applyZoom();
    });
    svg.addEventListener('pointerup', () => { dragging = false; svg.style.cursor = 'grab'; });

    /* Double-click reset */
    svg.addEventListener('dblclick', () => { zScale = 1; zTx = 0; zTy = 0; applyZoom(); });

    body.append(svgWrap);

    const legend = create('div', 'lbsw-legend');
    const queryLegend = create('div', null);
    queryLegend.append(create('span', 'lbsw-dot'), document.createTextNode('Query embedding'));
    queryLegend.querySelector('.lbsw-dot').style.background = '#FF3621';
    const topLegend = create('div', null);
    topLegend.append(create('span', 'lbsw-dot'), document.createTextNode('Returned results'));
    topLegend.querySelector('.lbsw-dot').style.background = '#7C4DFF';
    const corpusLegend = create('div', null);
    corpusLegend.append(create('span', 'lbsw-dot'), document.createTextNode('Other indexed documents'));
    corpusLegend.querySelector('.lbsw-dot').style.background = '#B7C5CB';
    legend.append(queryLegend, topLegend, corpusLegend);
    body.append(legend);
  };

  const renderScoreBars = (body, payload) => {
    const rows = payload.results || [];
    if (!rows.length) {
      body.append(create('div', 'lbsw-empty', 'Run a search to compare lexical ranking scores.'));
      return;
    }
    const list = create('div');
    for (const row of rows) {
      const item = create('div', 'lbsw-result');
      const top = create('div', 'lbsw-result-top');
      const titleWrap = create('div');
      titleWrap.append(
        create('div', 'lbsw-result-rank', `Rank ${row.rank}`),
        create('div', 'lbsw-result-title', row.title || '')
      );
      top.append(titleWrap, create('div', 'lbsw-result-score', row.score_label || ''));
      item.append(top);
      if (row.meta && row.meta.length) {
        const meta = create('div', 'lbsw-result-meta');
        for (const value of row.meta) meta.append(create('span', null, value));
        item.append(meta);
      }
      const track = create('div', 'lbsw-bar-track');
      const fill = create('div', 'lbsw-bar-fill');
      fill.style.width = toPercent(Number(row.bar_value || 0));
      track.append(fill);
      item.append(track);
      list.append(item);
    }
    body.append(list);
  };

  const renderHybridBars = (body, payload) => {
    const rows = payload.results || [];
    if (!rows.length) {
      body.append(create('div', 'lbsw-empty', 'Run a search to compare text and vector contributions in the final rank.'));
      return;
    }
    body.append(create('div', 'lbsw-formula', payload.formula || 'RRF score = 1 / (k + vector_rank) + 1 / (k + text_rank)'));
    const list = create('div');
    for (const row of rows) {
      const item = create('div', 'lbsw-result');
      const top = create('div', 'lbsw-result-top');
      const titleWrap = create('div');
      titleWrap.append(
        create('div', 'lbsw-result-rank', `Rank ${row.rank}`),
        create('div', 'lbsw-result-title', row.title || '')
      );
      top.append(titleWrap, create('div', 'lbsw-result-score', row.score_label || ''));
      item.append(top);
      const stack = create('div', 'lbsw-stack');
      const vectorFill = create('div', 'lbsw-stack-vector');
      vectorFill.style.width = toPercent(Number(row.vector_share || 0));
      const textFill = create('div', 'lbsw-stack-text');
      textFill.style.width = toPercent(Number(row.text_share || 0));
      stack.append(vectorFill, textFill);
      item.append(stack);
      const meta = create('div', 'lbsw-result-meta');
      for (const value of (row.meta || [])) meta.append(create('span', null, value));
      item.append(meta);
      list.append(item);
    }
    body.append(list);
    const legend = create('div', 'lbsw-legend');
    const vectorLegend = create('div', null);
    vectorLegend.append(create('span', 'lbsw-dot'), document.createTextNode('Vector contribution'));
    vectorLegend.querySelector('.lbsw-dot').style.background = '#7C4DFF';
    const textLegend = create('div', null);
    textLegend.append(create('span', 'lbsw-dot'), document.createTextNode('Text contribution'));
    textLegend.querySelector('.lbsw-dot').style.background = '#FFB347';
    legend.append(vectorLegend, textLegend);
    body.append(legend);
  };

  const renderResultsColumn = (body, payload) => {
    const rows = payload.results || [];
    if (!rows.length) {
      body.append(create('div', 'lbsw-empty', 'Search results will appear here.'));
      return;
    }
    const wrap = create('div', 'lbsw-results');
    for (const row of rows) {
      const card = create('div', 'lbsw-result');
      const top = create('div', 'lbsw-result-top');
      const titleWrap = create('div');
      titleWrap.append(
        create('div', 'lbsw-result-rank', `Rank ${row.rank}`),
        create('div', 'lbsw-result-title', row.title || '')
      );
      top.append(titleWrap, create('div', 'lbsw-result-score', row.score_label || ''));
      card.append(top);
      if (row.preview) {
        const preview = create('div', 'lbsw-result-meta');
        preview.append(create('span', null, row.preview));
        card.append(preview);
      }
      if (row.embedding_head) {
        card.append(create('div', 'lbsw-vector-preview', row.embedding_head));
      }
      if (row.meta && row.meta.length) {
        const meta = create('div', 'lbsw-result-meta');
        for (const value of row.meta) meta.append(create('span', null, value));
        card.append(meta);
      }
      wrap.append(card);
    }
    body.append(wrap);
  };

  /* ── Results table renderer ── */
  const renderResultsTable = (container, payload, mode) => {
    const rows = payload.results || [];
    if (!rows.length) {
      container.append(create('div', 'lbsw-empty', 'Search results will appear here.'));
      return;
    }
    const trunc = (s, n) => s && s.length > n ? s.slice(0, n) + '…' : (s || '');

    /* Column defs: dynamic from result_columns (custom SQL) or hardcoded per mode */
    const numericKeys = new Set(['id','rank','cosine_distance','bm25_score','rrf_score','dist','score',
      'vector_rrf','text_rrf','vector_rank','text_rank','vector_distance','price','rating']);
    const textKeys = new Set(['title','preview','body','root_category','name','description']);
    let cols;
    if (payload.result_columns && payload.result_columns.length) {
      cols = [{ key: 'rank', label: '#', mono: true }];
      for (const col of payload.result_columns) {
        const isNum = numericKeys.has(col) || (typeof rows[0][col] === 'number');
        const isText = textKeys.has(col) || (typeof rows[0][col] === 'string' && !isNum);
        cols.push({
          key: col,
          label: col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
          mono: isNum,
          max: isText ? 80 : undefined,
        });
      }
    } else if (mode === 'vector') {
      cols = [
        { key: 'rank', label: '#', mono: true },
        { key: 'title', label: 'Title', max: 90 },
        { key: 'score_label', label: 'Distance', mono: true },
      ];
    } else if (mode === 'text') {
      cols = [
        { key: 'rank', label: '#', mono: true },
        { key: 'title', label: 'Title', max: 48 },
        { key: 'preview', label: 'Content', max: 80 },
        { key: 'score_label', label: 'BM25 Score', mono: true },
      ];
    } else {
      cols = [
        { key: 'rank', label: '#', mono: true },
        { key: 'title', label: 'Title', max: 90 },
        { key: 'score_label', label: 'RRF Score', mono: true },
      ];
    }
    /* Append meta columns from first row (standard search only) */
    if (!payload.result_columns && rows[0].meta && rows[0].meta.length) {
      for (let i = 0; i < rows[0].meta.length; i++) {
        const label = (rows[0].meta[i] || '').split(' ')[0] || `Meta ${i+1}`;
        cols.push({ metaIdx: i, label: label.charAt(0).toUpperCase() + label.slice(1), mono: true });
      }
    }

    const wrap = create('div', 'lbsw-table-wrap');
    const table = document.createElement('table');
    table.className = 'lbsw-table';
    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    for (const c of cols) {
      const th = document.createElement('th');
      th.textContent = c.label;
      headRow.append(th);
    }
    thead.append(headRow);
    table.append(thead);

    const tbody = document.createElement('tbody');
    for (const row of rows) {
      const tr = document.createElement('tr');
      for (const c of cols) {
        const td = document.createElement('td');
        if (c.mono) td.classList.add('lbsw-mono');
        let val;
        if (c.metaIdx !== undefined) {
          const raw = (row.meta && row.meta[c.metaIdx]) || '';
          val = raw.includes(' ') ? raw.split(' ').slice(1).join(' ') : raw;
        } else {
          val = String(row[c.key] ?? '');
        }
        td.textContent = c.max ? trunc(val, c.max) : val;
        if (c.max) td.title = row[c.key] || '';
        tr.append(td);
      }
      tbody.append(tr);
    }
    table.append(tbody);
    wrap.append(table);
    container.append(wrap);
  };

  /* ── SQL syntax highlighter ── */
  const highlightSql = (raw) => {
    const esc = (s) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const kw = new Set(['SELECT','FROM','WHERE','ORDER','BY','LIMIT','AS','AND','OR','NOT','NULL',
      'IS','IN','ON','JOIN','LEFT','RIGHT','INNER','OUTER','FULL','CROSS','WITH','OVER','DESC','ASC',
      'CAST','ROUND','COALESCE','RANK','PARTITION','GROUP','HAVING','INSERT','UPDATE','DELETE','CREATE',
      'DROP','INTO','VALUES','SET','BETWEEN','LIKE','DISTINCT','UNION','ALL','EXISTS','CASE','WHEN',
      'THEN','ELSE','END','TRUE','FALSE']);
    const fn = new Set(['ai_query','LEFT','ROUND','CAST','COALESCE','RANK','to_tsvector','to_bm25query','ROUND']);
    return esc(raw).replace(
      /(--[^\n]*)|('(?:[^']|'')*')|(\$[0-9]+)|([0-9]+(?:\.[0-9]+)?)|(<=>|<@>|::|>=|<=|<>|!=|[+\-*\/=<>()])|([A-Za-z_][A-Za-z0-9_]*)/g,
      (m, cmt, str, param, num, op, word) => {
        if (cmt) return `<span class="cmt">${cmt}</span>`;
        if (str) return `<span class="str">${str}</span>`;
        if (param) return `<span class="param">${param}</span>`;
        if (num) return `<span class="num">${num}</span>`;
        if (op) return `<span class="op">${op}</span>`;
        if (word) {
          const up = word.toUpperCase();
          if (kw.has(up)) return `<span class="kw">${word}</span>`;
          if (fn.has(word)) return `<span class="fn">${word}</span>`;
        }
        return m;
      }
    );
  };

  const renderMain = () => {
    const payload = parsePayload();
    const mode = model.get('mode');
    shell.replaceChildren();

    const header = create('div', 'lbsw-header');
    const titleRow = create('div', 'lbsw-title-row');
    const titleWrap = create('div');
    titleWrap.append(
      create('div', 'lbsw-title', model.get('title') || 'Lakebase Search Playground'),
      create('div', 'lbsw-subtitle', model.get('subtitle') || '')
    );
    const headerActions = create('div');
    headerActions.style.cssText = 'display:flex;align-items:center;gap:8px';
    /* mode badge removed */
    const fsBtn = create('button', 'lbsw-fs-btn');
    fsBtn.innerHTML = isFs() ? svgCollapse : svgExpand;
    fsBtn.title = isFs() ? 'Exit fullscreen' : 'Fullscreen';
    fsBtn.addEventListener('click', toggleFullscreen);
    headerActions.append(fsBtn);
    titleRow.append(titleWrap, headerActions);
    header.append(titleRow);
    shell.append(header);

    const controls = create('div', 'lbsw-controls');
    const queryField = createField({
      label: 'Search query', value: model.get('query_text') || '', onCommit: (v) => setTrait('query_text', v)
    });
    queryField.classList.add('lbsw-span-3');
    controls.append(queryField);

    if (mode === 'vector' || mode === 'hybrid') {
      let modelOptions = [];
      try { modelOptions = JSON.parse(model.get('available_models_json') || '[]'); } catch (e) {}
      const embeddingField = modelOptions.length > 0
        ? createSelect({
            label: 'Embedding model',
            value: model.get('embedding_model') || '',
            options: modelOptions,
            onCommit: (v) => setTrait('embedding_model', v),
          })
        : createField({
            label: 'Embedding model', value: model.get('embedding_model') || '', onCommit: (v) => setTrait('embedding_model', v)
          });
      embeddingField.classList.add('lbsw-span-2');
      controls.append(embeddingField);
    }

    if (mode === 'text') {
      const configField = createField({
        label: 'Text config', value: model.get('text_config') || '', onCommit: (v) => setTrait('text_config', v)
      });
      configField.classList.add('lbsw-span-2');
      controls.append(configField);
    }

    if (mode === 'vector' || mode === 'hybrid') {
      const filterField = createField({
        label: 'WHERE filter', value: model.get('pre_filter') || '', onCommit: (v) => setTrait('pre_filter', v)
      });
      filterField.classList.add('lbsw-span-2');
      controls.append(filterField);

      const metricField = createSelect({
        label: 'Distance metric',
        value: model.get('distance_metric') || 'cosine',
        options: [
          { value: 'cosine', label: 'Cosine' },
          { value: 'l2', label: 'L2' },
          { value: 'inner_product', label: 'Inner Product' },
        ],
        onCommit: (v) => setTrait('distance_metric', v),
      });
      metricField.classList.add('lbsw-span-2');
      controls.append(metricField);


    }

    const topKField = createField({
      label: 'Top K', type: 'number', value: model.get('top_k') || 5, min: 1, step: 1, onCommit: (v) => setTrait('top_k', v)
    });
    topKField.classList.add('lbsw-span-1');
    controls.append(topKField);

    if (mode === 'hybrid') {
      const rrfField = createField({
        label: 'RRF k', type: 'number', value: model.get('rrf_k') || 60, min: 1, step: 1, onCommit: (v) => setTrait('rrf_k', v)
      });
      rrfField.classList.add('lbsw-span-1');
      controls.append(rrfField);

      const poolField = createField({
        label: 'Candidate pool', type: 'number', value: model.get('candidate_pool') || 40, min: 1, step: 1, onCommit: (v) => setTrait('candidate_pool', v)
      });
      poolField.classList.add('lbsw-span-2');
      controls.append(poolField);
    }

    /* ── Editable SQL query ── */
    const tbl = model.get('table_name') || 'documents';
    const bm25Idx = (tbl.indexOf('.') > -1 ? tbl.slice(0, tbl.lastIndexOf('.') + 1) : '') + tbl.split('.').pop() + '_body_bm25_idx';
    const tk = model.get('top_k') || 5;
    const pf = (model.get('pre_filter') || '').trim();
    const tc = (model.get('text_config') || 'english').replace(/[^a-z_]/gi, '');
    const rk = model.get('rrf_k') || 60;
    const cp = Math.max(model.get('candidate_pool') || 40, tk, 10);
    const qt = (model.get('query_text') || '').replace(/'/g, "''");
    const em = model.get('embedding_model') || '';
    const metric = model.get('distance_metric') || 'cosine';
    const metricMap = {
      cosine: { op: '<=>', alias: 'cosine_distance' },
      l2: { op: '<->', alias: 'l2_distance' },
      inner_product: { op: '<#>', alias: 'inner_product' },
    };
    const mm = metricMap[metric] || metricMap.cosine;
    let sqlPreview = '';
    if (mode === 'vector') {
      const w = pf ? `\nWHERE ${pf}` : '';
      sqlPreview = `WITH q AS (\n  SELECT ai_query('${em}', '${qt}')::vector AS qv  -- embed inline\n)\nSELECT d.id, d.title, LEFT(d.body, 110) AS preview,\n  d.embedding ${mm.op} q.qv AS ${mm.alias}\nFROM ${tbl} d, q${w}\nORDER BY ${mm.alias}\nLIMIT ${tk}`;
    } else if (mode === 'text') {
      sqlPreview = `WITH q AS (\n  SELECT '${qt}' AS qt  -- query text\n)\nSELECT d.id, d.title, LEFT(d.body, 110) AS preview,\n  d.body_tsv <@> to_bm25query(\n    to_tsvector('${tc}', q.qt), '${bm25Idx}'\n  ) AS bm25_score\nFROM ${tbl} d, q\nORDER BY bm25_score\nLIMIT ${tk}`;
    } else {
      sqlPreview = `WITH q AS (\n  SELECT ai_query('${em}', '${qt}')::vector AS qv,\n         '${qt}' AS qt  -- embed inline\n),\nvector_ranked AS (\n  SELECT id, RANK() OVER (ORDER BY dist) AS rank FROM (\n    SELECT id, d.embedding ${mm.op} q.qv AS dist\n    FROM ${tbl} d, q ORDER BY dist LIMIT ${cp}\n  ) v\n), keyword_ranked AS (\n  SELECT id, RANK() OVER (ORDER BY score) AS rank FROM (\n    SELECT id, d.body_tsv <@> to_bm25query(\n      to_tsvector('english', q.qt), '${bm25Idx}') AS score\n    FROM ${tbl} d, q ORDER BY score LIMIT ${cp}\n  ) k\n)\nSELECT d.id, d.title, LEFT(d.body, 110) AS preview,\n  COALESCE(1.0/(${rk}+v.rank), 0)\n  + COALESCE(1.0/(${rk}+k.rank), 0) AS rrf_score\nFROM ${tbl} d\nLEFT JOIN vector_ranked v ON d.id = v.id\nLEFT JOIN keyword_ranked k ON d.id = k.id\nWHERE v.id IS NOT NULL OR k.id IS NOT NULL\nORDER BY rrf_score DESC, d.id\nLIMIT ${tk}`;
    }

    shell.append(controls);

    /* ── Editable SQL editor with syntax highlighting ── */
    const currentCustom = model.get('custom_sql') || '';
    const displaySql = currentCustom || sqlPreview;

    const sqlSection = create('div', 'lbsw-sql-section');
    const sqlHeader = create('div', 'lbsw-sql-header');
    const perfMs = payload._perf_ms;

    const editorWrap = create('div', 'lbsw-editor-wrap');
    const highlight = create('div', 'lbsw-code lbsw-highlight-layer');
    highlight.innerHTML = highlightSql(displaySql) + '\n';
    const sqlArea = document.createElement('textarea');
    sqlArea.className = 'lbsw-sql-area';
    sqlArea.value = displaySql;
    sqlArea.spellcheck = false;
    sqlArea.rows = Math.min(displaySql.split('\n').length + 1, 20);

    /* Sync scroll between textarea and highlight overlay */
    sqlArea.addEventListener('scroll', () => {
      highlight.scrollTop = sqlArea.scrollTop;
      highlight.scrollLeft = sqlArea.scrollLeft;
    });

    /* On user edit: update highlight + set custom_sql */
    sqlArea.addEventListener('input', () => {
      highlight.innerHTML = highlightSql(sqlArea.value) + '\n';
      setTrait('custom_sql', sqlArea.value);
    });

    editorWrap.append(highlight, sqlArea);
    sqlSection.append(editorWrap);
    shell.append(sqlSection);

    /* ── Search button (full width, below SQL) ── */
    const buttonSection = create('div', 'lbsw-button-section');
    const button = create('button', 'lbsw-button lbsw-button-full', model.get('busy') ? 'Searching…' : 'Search');
    button.disabled = Boolean(model.get('busy'));
    button.addEventListener('click', () => {
      model.set('command', '');  /* reset first so re-setting 'run' always triggers a change */
      setTrait('command', 'run');
    });
    buttonSection.append(button);
    shell.append(buttonSection);

    if (model.get('error')) {
      shell.append(create('div', 'lbsw-error', model.get('error')));
    }

    /* ── Tab bar with timing ── */
    const tabBar = create('div', 'lbsw-tabs');
    const tabResults = create('button', 'lbsw-tab lbsw-tab-active');
    tabResults.textContent = 'Results';
    const tabViz = create('button', 'lbsw-tab');
    tabViz.textContent = 'Visualization';
    tabBar.append(tabResults, tabViz);
    const spacer = create('div', 'lbsw-tab-spacer');
    tabBar.append(spacer);
    /* Show config badges + timing right-aligned */
    if (mode === 'vector' || mode === 'hybrid') {
      const metricBadge = create('span', 'lbsw-tab-badge');
      metricBadge.textContent = (payload._distance_metric || mm.alias).replace('_', ' ');
      tabBar.append(metricBadge);

    }
    if (perfMs != null) {
      const perfBadge = create('span', 'lbsw-tab-perf');
      perfBadge.innerHTML = `<span class="lbsw-perf-dot"></span>${Number(perfMs).toFixed(0)} ms`;
      tabBar.append(perfBadge);
    }
    shell.append(tabBar);

    /* ── Tab panels ── */
    const panelResults = create('div', 'lbsw-tab-panel lbsw-tab-panel-active');
    renderResultsTable(panelResults, payload, mode);
    shell.append(panelResults);

    const panelViz = create('div', 'lbsw-tab-panel');
    if (mode === 'vector') {
      renderVectorViz(panelViz, payload);
    } else if (mode === 'text') {
      renderScoreBars(panelViz, payload);
    } else {
      renderHybridBars(panelViz, payload);
    }
    if (payload.inline_notes && payload.inline_notes.length) {
      const chips = create('div', 'lbsw-inline-list');
      for (const note of payload.inline_notes) chips.append(create('div', 'lbsw-chip', note));
      panelViz.append(chips);
    }
    shell.append(panelViz);

    /* ── Tab switching ── */
    const switchTab = (activeBtn, activePanel, inactiveBtn, inactivePanel) => {
      activeBtn.classList.add('lbsw-tab-active');
      inactiveBtn.classList.remove('lbsw-tab-active');
      activePanel.classList.add('lbsw-tab-panel-active');
      inactivePanel.classList.remove('lbsw-tab-panel-active');
    };
    tabResults.addEventListener('click', () => switchTab(tabResults, panelResults, tabViz, panelViz));
    tabViz.addEventListener('click', () => switchTab(tabViz, panelViz, tabResults, panelResults));
  };

  const observedKeys = ['mode', 'title', 'subtitle', 'query_text', 'embedding_model', 'text_config', 'top_k', 'rrf_k', 'candidate_pool', 'pre_filter', 'table_name', 'distance_metric', 'payload_json', 'busy', 'error', 'status'];
  /* When a parameter input changes, clear custom_sql so the query regenerates from params */
  const paramKeys = new Set(['query_text', 'embedding_model', 'text_config', 'top_k', 'rrf_k', 'candidate_pool', 'pre_filter', 'table_name', 'distance_metric']);
  const onTraitChange = (key) => {
    if (paramKeys.has(key)) model.set('custom_sql', '');
    renderMain();
  };
  for (const key of observedKeys) {
    model.on(`change:${key}`, () => onTraitChange(key));
  }
  renderMain();

  return () => {
    document.removeEventListener('fullscreenchange', onFsChange);
    document.removeEventListener('webkitfullscreenchange', onFsChange);
    if (isFs()) (document.exitFullscreen || document.webkitExitFullscreen || (() => {})).call(document);
    for (const key of observedKeys) {
      model.off(`change:${key}`);
    }
  };
}

export default { render };
'''


class _BaseLakebaseSearchWidget(anywidget.AnyWidget):
    """Base class for Lakebase search playground widgets.

    Constructor parameters (explicit dependencies):
        documents:      list of dicts with keys {id, title, body, embedding}
        fetch_fn:       callable(sql, params, dbname) -> pd.DataFrame
        embed_fn:       callable(query_text, model_name) -> list[float]
        database_name:  Lakebase Postgres database name (e.g. "my_db")
        table_name:     Postgres table name (default "documents")
        auto_run:       run the initial search on instantiation (default True)
    """

    _esm = _SEARCH_ESM

    mode = traitlets.Unicode("vector").tag(sync=True)
    title = traitlets.Unicode("Lakebase Search Playground").tag(sync=True)
    subtitle = traitlets.Unicode("").tag(sync=True)
    query_text = traitlets.Unicode("").tag(sync=True)
    embedding_model = traitlets.Unicode("").tag(sync=True)
    available_models_json = traitlets.Unicode("[]").tag(sync=True)
    text_config = traitlets.Unicode("english").tag(sync=True)
    top_k = traitlets.Int(5).tag(sync=True)
    rrf_k = traitlets.Int(60).tag(sync=True)
    candidate_pool = traitlets.Int(40).tag(sync=True)
    payload_json = traitlets.Unicode("{}").tag(sync=True)
    status = traitlets.Unicode("Ready").tag(sync=True)
    busy = traitlets.Bool(False).tag(sync=True)
    error = traitlets.Unicode("").tag(sync=True)
    pre_filter = traitlets.Unicode("").tag(sync=True)
    table_name = traitlets.Unicode("documents").tag(sync=True)
    custom_sql = traitlets.Unicode("").tag(sync=True)
    command = traitlets.Unicode("").tag(sync=True)
    distance_metric = traitlets.Unicode("cosine").tag(sync=True)

    def __init__(
        self,
        *,
        documents: List[Dict[str, Any]] | None = None,
        fetch_fn: Callable[..., Any] | None = None,
        embed_fn: Callable[[str, str], List[float]] | None = None,
        database_name: str = "",
        auto_run: bool = True,
        **kwargs: Any,
    ) -> None:
        self._documents = documents or []
        self._fetch_fn = fetch_fn
        self._embed_fn = embed_fn
        self._database_name = database_name
        self._auto_run = auto_run
        super().__init__(**kwargs)
        if self._auto_run:
            self._run_search()

    # ── helpers ──────────────────────────────────────────────────────

    def _embedding_head(self, title: str, n: int = 8) -> str:
        for doc in self._documents:
            if doc.get("title") == title:
                values = doc["embedding"][:n]
                return "[" + ", ".join(f"{v:.4f}" for v in values) + ", \u2026]"
        return ""

    @staticmethod
    def _embedding_literal(values: List[float]) -> str:
        return "[" + ", ".join(f"{float(v):.12f}" for v in values) + "]"

    _DISTANCE_OPS = {
        "cosine": ("<=>", "cosine_distance"),
        "l2": ("<->", "l2_distance"),
        "inner_product": ("<#>", "inner_product"),
    }

    def _distance_op(self) -> tuple:
        """Return (operator, alias) for the current distance_metric."""
        return self._DISTANCE_OPS.get(self.distance_metric, ("<=>", "cosine_distance"))

    @staticmethod
    def _safe_text_config(text_config: str) -> str:
        value = (text_config or "english").strip().lower()
        if not re.fullmatch(r"[a-z_]+", value):
            raise ValueError("text_config must contain only lowercase letters and underscores.")
        return value

    @staticmethod
    def _project_vectors_2d(query_embedding, documents):
        matrix = np.array(
            [query_embedding] + [doc["embedding"] for doc in documents],
            dtype=float,
        )
        centered = matrix - matrix.mean(axis=0, keepdims=True)
        _, _, vt = np.linalg.svd(centered, full_matrices=False)
        coords = centered @ vt[:2].T
        if coords.shape[1] == 1:
            coords = np.hstack([coords, np.zeros((coords.shape[0], 1))])
        return coords

    @staticmethod
    def _tokenize(text: str) -> list:
        return re.findall(r"[a-z0-9]+", (text or "").lower())

    # ── params / validation ─────────────────────────────────────────

    def _build_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "query_text": self.query_text.strip(),
            "top_k": int(self.top_k),
        }
        if self.mode in {"vector", "hybrid"}:
            params["embedding_model"] = self.embedding_model.strip()
            params["pre_filter"] = self.pre_filter.strip()
        if self.mode == "text":
            params["text_config"] = self.text_config.strip() or "english"
        if self.mode == "hybrid":
            params["rrf_k"] = int(self.rrf_k)
            params["candidate_pool"] = int(self.candidate_pool)
        return params

    def _validate(self) -> None:
        if not self.query_text.strip():
            raise ValueError("Enter a search query first.")
        if int(self.top_k) <= 0:
            raise ValueError("top_k must be greater than 0.")
        if self.mode in {"vector", "hybrid"}:
            if not self.embedding_model.strip():
                raise ValueError("An embedding model is required.")
            if self._embed_fn is None:
                raise ValueError("embed_fn is required for vector/hybrid search.")
        if self._fetch_fn is None:
            raise ValueError("fetch_fn is required.")
        if not self._database_name:
            raise ValueError("database_name is required.")
        if self.mode == "hybrid":
            if int(self.rrf_k) <= 0:
                raise ValueError("rrf_k must be greater than 0.")
            if int(self.candidate_pool) <= 0:
                raise ValueError("candidate_pool must be greater than 0.")

    # ── search dispatch ─────────────────────────────────────────────

    def _do_search(self, **params: Any) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement _do_search.")

    def _run_custom_sql(self, raw_sql: str) -> Dict[str, Any]:
        """Execute a user-edited SQL query with proper param substitution."""
        import re as _re
        params = self._build_params()
        query_text = params.get("query_text", "")
        embedding_model = params.get("embedding_model", "")

        # Build param values: $1 = embedding vector, $2 = query text
        param_values: list = []
        sql_exec = raw_sql
        if self.mode in ("vector", "hybrid") and self._embed_fn:
            emb = self._embed_fn(query_text, embedding_model)
            lit = self._embedding_literal(emb)
        else:
            lit = None
            emb = []

        # Strip comment lines first, then replace $N placeholders
        exec_lines = [l for l in sql_exec.split("\n") if not l.strip().startswith("--")]
        sql_exec = "\n".join(exec_lines).strip()

        placeholders = sorted(set(_re.findall(r'\$([0-9]+)', sql_exec)), key=int)
        for ph in placeholders:
            n = int(ph)
            if n == 1 and self.mode in ("vector", "hybrid"):
                param_values.append(lit)
            elif n == 1 and self.mode == "text":
                param_values.append(query_text)
            elif n == 2:
                param_values.append(query_text)
            else:
                param_values.append(query_text)
            # Replace ALL occurrences — same param value each time
            count = sql_exec.count(f"${ph}")
            sql_exec = sql_exec.replace(f"${ph}", "%s")
            # Duplicate param for each extra occurrence
            for _ in range(count - 1):
                param_values.append(param_values[-1])

        results = self._fetch_fn(sql_exec, tuple(param_values), dbname=self._database_name)
        records = results.to_dict("records")
        columns = list(results.columns)

        # Build rows with all columns preserved for the table
        rows = []
        for rank, r in enumerate(records, start=1):
            row: Dict[str, Any] = {"rank": rank}
            # Copy all result columns
            for col in columns:
                val = r[col]
                if val is None:
                    row[col] = None
                elif isinstance(val, float):
                    row[col] = round(val, 6)
                elif hasattr(val, 'as_integer_ratio'):  # Decimal, numpy float, etc.
                    row[col] = round(float(val), 6)
                elif isinstance(val, int):
                    row[col] = val
                else:
                    row[col] = str(val) if not isinstance(val, str) else val
            # Standard fields for backward compat
            row.setdefault("title", "")
            row.setdefault("preview", "")
            for score_key in ("cosine_distance", "bm25_score", "rrf_score", "dist", "score"):
                if score_key in r:
                    row["score_label"] = f"{score_key} {float(r[score_key]):.6f}"
                    break
            else:
                row["score_label"] = ""
            rows.append(row)
        return {
            "results": rows,
            "result_columns": columns,
            "left_title": "Custom query results",
            "right_title": "Results",
        }

    def _run_search(self) -> None:
        try:
            self._validate()
            self.busy = True
            self.error = ""
            import time as _t
            _t0 = _t.perf_counter()
            if self.custom_sql.strip():
                payload = self._run_custom_sql(self.custom_sql)
            else:
                payload = self._do_search(**self._build_params())
            _elapsed_ms = (_t.perf_counter() - _t0) * 1000
            payload["_perf_ms"] = round(_elapsed_ms, 1)
            payload.setdefault("results", [])
            payload.setdefault("left_title", "Search explanation")
            payload.setdefault("right_title", "Results")
            # Include search config in payload for UI feedback
            payload["_distance_metric"] = self.distance_metric
            self.payload_json = json.dumps(payload)
            _flags = []
            if self.mode in ("vector", "hybrid"):
                _flags.append(f"metric={self.distance_metric}")
            _flag_str = f" · {' · '.join(_flags)}" if _flags else ""
            self.status = f"Returned {len(payload['results'])} results · {_elapsed_ms:.0f} ms{_flag_str}"
        except Exception as exc:
            self.payload_json = json.dumps({})
            self.error = str(exc)
            self.status = "Search failed"
        finally:
            self.busy = False

    @traitlets.observe("command")
    def _handle_command(self, change: Dict[str, Any]) -> None:
        if change["new"] != "run":
            return
        try:
            self._run_search()
        finally:
            self.command = ""


class VectorSearchWidget(_BaseLakebaseSearchWidget):
    mode = traitlets.Unicode("vector").tag(sync=True)
    title = traitlets.Unicode("Lakebase Search: Vector Search").tag(sync=True)
    subtitle = traitlets.Unicode("").tag(sync=True)

    def _do_search(self, query_text, top_k, embedding_model, pre_filter=""):
        top_k = max(1, min(top_k, len(self._documents)))
        query_emb = self._embed_fn(query_text, embedding_model)
        lit = self._embedding_literal(query_emb)
        tbl = self.table_name
        op, alias = self._distance_op()

        where = f"WHERE {pre_filter}" if pre_filter else ""
        sql_query = (
            f"WITH q AS (\n"
            f"  SELECT ai_query('{embedding_model}', :question)::vector AS qv  -- embed inline\n"
            f")\n"
            f"SELECT d.id, d.title, LEFT(d.body, 110) AS preview,\n"
            f"  d.embedding {op} q.qv AS {alias}\n"
            f"FROM {tbl} d, q\n"
            + (f"WHERE {pre_filter}\n" if pre_filter else "")
            + f"ORDER BY {alias}\nLIMIT {top_k}"
        )
        results = self._fetch_fn(
            f"WITH q AS (SELECT %s::vector AS qv) "
            f"SELECT d.id, d.title, LEFT(d.body, 110) AS preview, "
            f"d.embedding {op} q.qv AS {alias} "
            f"FROM {tbl} d, q {where} ORDER BY {alias} LIMIT %s",
            (lit, top_k),
            dbname=self._database_name,
        )

        top_ids = {int(r["id"]) for r in results.to_dict("records")}

        # ── Limit projection to 50 closest + top_k (not all 10k docs) ──
        query_arr = np.array(query_emb, dtype=float)
        doc_matrix = np.array([d["embedding"] for d in self._documents], dtype=float)
        q_norm = np.linalg.norm(query_arr) + 1e-12
        d_norms = np.linalg.norm(doc_matrix, axis=1) + 1e-12
        cos_dists = 1.0 - (doc_matrix @ query_arr) / (d_norms * q_norm)
        sorted_idx = np.argsort(cos_dists)

        n_nearby = 50
        keep = set(sorted_idx[:n_nearby].tolist())
        for i, doc in enumerate(self._documents):
            if doc["id"] in top_ids:
                keep.add(i)
        keep_sorted = sorted(keep)
        nearby_docs = [self._documents[i] for i in keep_sorted]

        coords = self._project_vectors_2d(query_emb, nearby_docs)

        points = [
            {"label": "Query", "x": float(coords[0, 0]), "y": float(coords[0, 1]),
             "type": "query", "highlight": True}
        ]
        for i, doc in enumerate(nearby_docs, start=1):
            points.append({
                "label": doc["title"],
                "x": float(coords[i, 0]), "y": float(coords[i, 1]),
                "type": "document", "highlight": doc["id"] in top_ids,
            })

        rows = []
        for rank, r in enumerate(results.to_dict("records"), start=1):
            d = float(r[alias])
            rows.append({
                "rank": rank, "title": r["title"], "preview": r["preview"],
                "score_label": f"{alias} {d:.6f}",
                "embedding_head": self._embedding_head(r["title"]),
                "meta": [f"id {int(r['id'])}", f"similarity {1.0 / (1.0 + abs(d)):.3f}"],
            })

        closest = rows[0]["title"] if rows else "None"
        return {
            "left_title": "Projected embedding space",
            "left_subtitle": "2-D PCA projection of query and document embeddings.",
            "right_title": "Nearest semantic neighbors",
            "kpis": [
                {"label": "Embedding model", "value": embedding_model},
                {"label": "Top K", "value": str(top_k)},
                {"label": "Closest match", "value": closest},
            ],
            "projection": {"points": points},
            "results": rows,
            "inline_notes": [
                "Lower distance = closer semantic match.",
                f"Embedding dimension: {len(query_emb)}",
                "Highlighted dots = returned results.",
                *([ f"Pre-filter: {pre_filter}" ] if pre_filter else []),
            ],
            "code_sample": sql_query,
        }


class TextSearchWidget(_BaseLakebaseSearchWidget):
    mode = traitlets.Unicode("text").tag(sync=True)
    title = traitlets.Unicode("Text Search Playground").tag(sync=True)
    subtitle = traitlets.Unicode("").tag(sync=True)

    def _do_search(self, query_text, top_k, text_config):
        top_k = max(1, min(top_k, len(self._documents)))
        text_config = self._safe_text_config(text_config)
        tbl = self.table_name
        bm25_idx = f"{tbl.rsplit('.', 1)[0] + '.' if '.' in tbl else ''}{tbl.split('.')[-1]}_body_bm25_idx"

        sql_query = (
            f"WITH q AS (\n"
            f"  SELECT :question AS qt  -- query text\n"
            f")\n"
            f"SELECT d.id, d.title, LEFT(d.body, 110) AS preview,\n"
            f"  d.body_tsv <@> to_bm25query(\n"
            f"    to_tsvector('{text_config}', q.qt), '{bm25_idx}'\n"
            f"  ) AS bm25_score\n"
            f"FROM {tbl} d, q\n"
            f"ORDER BY bm25_score\nLIMIT {top_k}"
        )
        results = self._fetch_fn(
            f"WITH q AS (SELECT %s AS qt) "
            f"SELECT d.id, d.title, LEFT(d.body, 110) AS preview, "
            f"d.body_tsv <@> to_bm25query("
            f"to_tsvector('{text_config}', q.qt), '{bm25_idx}') AS bm25_score "
            f"FROM {tbl} d, q ORDER BY bm25_score LIMIT %s",
            (query_text, top_k),
            dbname=self._database_name,
        )

        query_tokens = set(self._tokenize(query_text))
        raw = results.to_dict("records")
        scores = [float(r["bm25_score"]) for r in raw] if raw else [0.0]
        mn, mx = min(scores), max(scores)
        span = max(mx - mn, 1e-9)

        rows = []
        for rank, r in enumerate(raw, start=1):
            tokens = set(self._tokenize(r["preview"])) | set(self._tokenize(r["title"]))
            hits = len(query_tokens & tokens)
            bm25 = float(r["bm25_score"])
            rows.append({
                "rank": rank, "title": r["title"], "preview": r["preview"],
                "score_label": f"bm25 {bm25:.6f}",
                "bar_value": float((mx - bm25) / span),
                "embedding_head": self._embedding_head(r["title"]),
                "meta": [f"id {int(r['id'])}", f"token overlaps {hits}"],
            })

        return {
            "left_title": "Lexical score breakdown",
            "left_subtitle": "Relative BM25 strength. Lower scores rank higher.",
            "right_title": "Top lexical matches",
            "kpis": [
                {"label": "Text config", "value": text_config},
                {"label": "Top K", "value": str(top_k)},
                {"label": "Top result", "value": rows[0]["title"] if rows else "None"},
            ],
            "results": rows,
            "inline_notes": [
                "Lexical ranking favors exact tokens and literal phrase overlap.",
                f"Distinct query terms: {len(query_tokens)}",
            ],
            "code_sample": sql_query,
        }


class HybridSearchWidget(_BaseLakebaseSearchWidget):
    mode = traitlets.Unicode("hybrid").tag(sync=True)
    title = traitlets.Unicode("Lakebase Search: Hybrid Search").tag(sync=True)
    subtitle = traitlets.Unicode("").tag(sync=True)

    def _do_search(self, query_text, top_k, embedding_model, rrf_k, candidate_pool, pre_filter=""):
        top_k = max(1, min(top_k, len(self._documents)))
        rrf_k = max(1, rrf_k)
        candidate_pool = max(candidate_pool, top_k, 10)
        query_emb = self._embed_fn(query_text, embedding_model)
        lit = self._embedding_literal(query_emb)
        tbl = self.table_name
        bm25_idx = f"{tbl.rsplit('.', 1)[0] + '.' if '.' in tbl else ''}{tbl.split('.')[-1]}_body_bm25_idx"
        op, _ = self._distance_op()

        sql_query = (
            f"WITH q AS (\n"
            f"  SELECT ai_query('{embedding_model}', :question)::vector AS qv,\n"
            f"         :question AS qt  -- embed inline\n"
            f"),\n"
            f"vector_ranked AS (\n"
            f"  SELECT id, RANK() OVER (ORDER BY dist) AS rank FROM (\n"
            f"    SELECT id, d.embedding {op} q.qv AS dist\n"
            f"    FROM {tbl} d, q ORDER BY dist LIMIT {candidate_pool}\n"
            f"  ) v\n"
            f"), keyword_ranked AS (\n"
            f"  SELECT id, RANK() OVER (ORDER BY score) AS rank FROM (\n"
            f"    SELECT id, d.body_tsv <@> to_bm25query(\n"
            f"      to_tsvector('english', q.qt), '{bm25_idx}') AS score\n"
            f"    FROM {tbl} d, q ORDER BY score LIMIT {candidate_pool}\n"
            f"  ) k\n"
            f")\n"
            f"SELECT d.id, d.title, LEFT(d.body, 110) AS preview,\n"
            f"  COALESCE(1.0/({rrf_k}+v.rank),0) AS vector_rrf,\n"
            f"  COALESCE(1.0/({rrf_k}+k.rank),0) AS text_rrf,\n"
            f"  COALESCE(1.0/({rrf_k}+v.rank),0)\n"
            f"  + COALESCE(1.0/({rrf_k}+k.rank),0) AS rrf_score\n"
            f"FROM {tbl} d\n"
            f"LEFT JOIN vector_ranked v ON d.id = v.id\n"
            f"LEFT JOIN keyword_ranked k ON d.id = k.id\n"
            f"WHERE v.id IS NOT NULL OR k.id IS NOT NULL\n"
            f"ORDER BY rrf_score DESC, d.id\n"
            f"LIMIT {top_k}"
        )
        results = self._fetch_fn(
            f"WITH q AS (SELECT %s::vector AS qv, %s AS qt), "
            f"vector_ranked AS ("
            f"  SELECT id, dist, RANK() OVER (ORDER BY dist) AS rank FROM ("
            f"    SELECT id, d.embedding {op} q.qv AS dist FROM {tbl} d, q ORDER BY dist LIMIT {candidate_pool}"
            f"  ) v"
            f"), keyword_ranked AS ("
            f"  SELECT id, score, RANK() OVER (ORDER BY score) AS rank FROM ("
            f"    SELECT id, d.body_tsv <@> to_bm25query(to_tsvector('english', q.qt), '{bm25_idx}') AS score"
            f"    FROM {tbl} d, q ORDER BY score LIMIT {candidate_pool}"
            f"  ) k"
            f") SELECT d.id, d.title, LEFT(d.body, 110) AS preview,"
            f"  COALESCE(1.0/(%s+v.rank),0) AS vector_rrf,"
            f"  COALESCE(1.0/(%s+k.rank),0) AS text_rrf,"
            f"  v.rank AS vector_rank, k.rank AS text_rank,"
            f"  COALESCE(1.0/(%s+v.rank),0)+COALESCE(1.0/(%s+k.rank),0) AS rrf_score,"
            f"  v.dist AS vector_distance,"
            f"  k.score AS bm25_score"
            f" FROM {tbl} d"
            f" LEFT JOIN vector_ranked v ON d.id=v.id"
            f" LEFT JOIN keyword_ranked k ON d.id=k.id"
            f" WHERE v.id IS NOT NULL OR k.id IS NOT NULL"
            f" ORDER BY rrf_score DESC, d.id LIMIT %s",
            (lit, query_text, rrf_k, rrf_k, rrf_k, rrf_k, top_k),
            dbname=self._database_name,
        )

        rows = []
        for rank, r in enumerate(results.to_dict("records"), start=1):
            v_rrf = float(r["vector_rrf"] or 0)
            t_rrf = float(r["text_rrf"] or 0)
            total = max(v_rrf + t_rrf, 1e-9)
            rows.append({
                "rank": rank, "title": r["title"], "preview": r["preview"],
                "embedding_head": self._embedding_head(r["title"]),
                "score_label": f"rrf {float(r['rrf_score']):.6f}",
                "vector_share": float(v_rrf / total),
                "text_share": float(t_rrf / total),
                "meta": [
                    f"vector rank {int(r['vector_rank'])}" if r.get('vector_rank') is not None and r['vector_rank'] == r['vector_rank'] else "vector rank \u2014",
                    f"text rank {int(r['text_rank'])}" if r.get('text_rank') is not None and r['text_rank'] == r['text_rank'] else "text rank \u2014",
                    f"distance {float(r['vector_distance']):.6f}" if r.get('vector_distance') is not None and r['vector_distance'] == r['vector_distance'] else "distance \u2014",
                    f"bm25 {float(r['bm25_score']):.6f}" if r.get('bm25_score') is not None and r['bm25_score'] == r['bm25_score'] else "bm25 \u2014",
                ],
            })

        return {
            "left_title": "RRF contribution mix",
            "left_subtitle": "Stacked bars show vector vs. lexical share of each result's final rank.",
            "right_title": "Hybrid ranking results",
            "kpis": [
                {"label": "Embedding model", "value": embedding_model},
                {"label": "RRF k", "value": str(rrf_k)},
                {"label": "Top result", "value": rows[0]["title"] if rows else "None"},
            ],
            "results": rows,
            "formula": f"rrf_score = 1/({rrf_k}+vector_rank) + 1/({rrf_k}+text_rank)",
            "inline_notes": [
                f"Candidate pool: {candidate_pool}",
                "RRF mixes reciprocal ranks, not raw scores.",
            ],
            "code_sample": sql_query,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ProductSearchBarWidget — clean e-commerce search bar demo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SEARCH_BAR_ESM = r'''
export function render({ model, el }) {
  if (!document.querySelector('link[data-db-fonts]')) {
    const lk = document.createElement('link'); lk.rel = 'stylesheet'; lk.dataset.dbFonts = '1';
    lk.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap';
    document.head.appendChild(lk);
  }
  const style = document.createElement('style');
  style.textContent = `
    .psb-root {
      --font-sans: "DM Sans", system-ui, sans-serif;
      --font-mono: "DM Mono", ui-monospace, monospace;
      --lava: #FF3621; --lava-h: #FF5A45; --lava-a: #DB2B18;
      --navy: #0B2026; --navy-7: #2C545E;
      --oat: #EEEDE9; --oat-l: #F9F7F4; --white: #FFFFFF;
      --txt: #0B2026; --txt2: #5F6B6E; --txt3: #A3ABAE;
      --r-sm: 4px; --r-md: 8px; --r-lg: 12px; --r-full: 9999px;
      font-family: var(--font-sans); font-size: 14px; color: var(--txt);
      max-width: 100%; width: 100%; min-height: 420px; box-sizing: border-box;
    }
    .psb-root *, .psb-root *::before, .psb-root *::after { box-sizing: border-box; }
    .psb-root:fullscreen, .psb-root:-webkit-full-screen {
      max-width: none; min-height: 100vh; overflow-y: auto;
      background: var(--white); padding-bottom: 32px; border-radius: 0;
    }
    .psb-root:fullscreen .psb-results, .psb-root:-webkit-full-screen .psb-results {
      max-width: 900px; margin: 0 auto;
    }
    .psb-header { text-align: center; padding: 140px 24px 0; position: relative; }
    .psb-fs-btn {
      position: absolute; top: 16px; right: 16px; background: none; border: 1px solid var(--oat);
      border-radius: var(--r-md); width: 32px; height: 32px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      color: var(--txt2); transition: background 80ms, border-color 80ms;
    }
    .psb-fs-btn:hover { background: var(--oat-l); border-color: var(--navy-7); }
    .psb-fs-btn svg { width: 16px; height: 16px; }
    .psb-title { font-size: 22px; font-weight: 700; color: var(--navy); letter-spacing: -0.02em; }
    .psb-sub { font-size: 13px; color: var(--txt2); margin-top: 4px; }
    .psb-bar-wrap { position: relative; max-width: 600px; margin: 20px auto 0; display: flex; gap: 8px; }
    .psb-input {
      flex: 1; min-height: 44px; padding: 10px 16px; border: 1.5px solid var(--oat);
      border-radius: var(--r-lg); font: inherit; font-size: 15px; color: var(--txt);
      background: var(--white); transition: border-color 120ms, box-shadow 120ms;
    }
    .psb-input:focus { outline: none; border-color: var(--lava); box-shadow: 0 0 0 3px rgba(255,54,33,0.1); }
    .psb-input::placeholder { color: var(--txt3); }
    .psb-btn {
      min-height: 44px; padding: 0 20px; border: none; border-radius: var(--r-lg);
      background: var(--lava); color: var(--white); font: inherit; font-weight: 600;
      cursor: pointer; transition: background 120ms; white-space: nowrap;
    }
    .psb-btn:hover { background: var(--lava-h); }
    .psb-btn:active { background: var(--lava-a); }
    .psb-btn:disabled { background: #c9c8c4; cursor: not-allowed; }
    .psb-sug {
      position: absolute; top: 100%; left: 0; right: 132px; margin-top: 4px;
      background: var(--white); border: 1px solid var(--oat); border-radius: var(--r-md);
      box-shadow: 0 8px 24px rgba(11,32,38,0.12); z-index: 10; overflow: hidden; display: none;
    }
    .psb-sug.open { display: block; }
    .psb-sug-item {
      padding: 10px 16px; cursor: pointer; display: flex; justify-content: space-between;
      align-items: center; font-size: 13px; transition: background 80ms;
    }
    .psb-sug-item:hover { background: var(--oat-l); }
    .psb-sug-title { color: var(--txt); font-weight: 500; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; max-width: 380px; }
    .psb-sug-cat { color: var(--txt2); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
    .psb-sug-price { color: var(--lava); font-size: 12px; font-weight: 600; margin-left: auto; padding-left: 8px; }
    .psb-sug-loading {
      padding: 12px 16px; text-align: center; font-size: 12px; color: var(--txt3);
      display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    @keyframes psb-spin { to { transform: rotate(360deg); } }
    .psb-spinner {
      width: 14px; height: 14px; border: 2px solid var(--oat); border-top-color: var(--lava);
      border-radius: 50%; animation: psb-spin 0.6s linear infinite;
    }
    .psb-icon-btn {
      min-height: 44px; width: 44px; border: 1.5px solid var(--oat); border-radius: var(--r-lg);
      background: var(--white); color: var(--txt2); cursor: pointer; flex-shrink: 0; position: relative;
      display: flex; align-items: center; justify-content: center;
      transition: background 120ms, border-color 120ms, color 120ms;
    }
    .psb-icon-btn:hover { background: var(--oat-l); border-color: var(--navy-7); color: var(--txt); }
    .psb-icon-btn.active { border-color: var(--lava); color: var(--lava); }
    .psb-icon-btn svg { width: 18px; height: 18px; }
    .psb-icon-btn .psb-dot {
      position: absolute; top: 5px; right: 5px; width: 7px; height: 7px; border-radius: 50%;
      background: var(--lava); display: none;
    }
    .psb-icon-btn.filtered .psb-dot { display: block; }
    .psb-settings {
      display: none; max-width: 600px; margin: 8px auto 0; padding: 12px 16px;
      background: var(--oat-l); border: 1px solid var(--oat); border-radius: var(--r-lg);
      align-items: center; gap: 12px; flex-wrap: wrap;
    }
    .psb-settings.open { display: flex; }
    .psb-set-label {
      font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em;
      color: var(--txt2);
    }
    .psb-select {
      flex: 1; min-width: 200px; min-height: 36px; padding: 6px 28px 6px 10px;
      border: 1px solid var(--oat); border-radius: var(--r-md); background-color: var(--white);
      color: var(--txt); font: inherit; font-size: 13px; cursor: pointer;
      appearance: none; -webkit-appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%235F6B6E' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 10px center;
    }
    .psb-select:focus { outline: none; border-color: var(--lava); box-shadow: 0 0 0 3px rgba(255,54,33,0.1); }
    .psb-clear {
      border: none; background: none; color: var(--lava); font: inherit; font-size: 12px;
      font-weight: 600; cursor: pointer; padding: 4px 2px;
    }
    .psb-clear:hover { text-decoration: underline; }
    .psb-status { text-align: center; padding: 12px 24px 0; font-size: 13px; color: var(--txt2); }
    .psb-error { text-align: center; padding: 8px 24px; color: #E5231F; font-size: 13px; }
    .psb-results { padding: 0 24px 16px; }
    .psb-card {
      display: flex; gap: 16px; padding: 16px 0; border-bottom: 1px solid var(--oat);
      align-items: flex-start;
    }
    .psb-card:last-child { border-bottom: none; }
    .psb-rank {
      min-width: 28px; height: 28px; border-radius: var(--r-full);
      background: var(--oat-l); color: var(--txt2); font-size: 12px; font-weight: 600;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px;
    }
    .psb-card-body { flex: 1; min-width: 0; }
    .psb-card-title { font-size: 15px; font-weight: 600; color: var(--navy); }
    .psb-card-meta { display: flex; gap: 10px; align-items: center; margin-top: 4px; flex-wrap: wrap; }
    .psb-badge {
      font-size: 10px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;
      padding: 2px 8px; border-radius: var(--r-full); background: var(--oat); color: var(--txt2);
    }
    .psb-price { font-size: 14px; font-weight: 600; color: var(--lava); }
    .psb-rating { font-size: 12px; color: var(--txt2); }
    .psb-rating .star { color: #F2960D; }
    .psb-preview { font-size: 13px; color: var(--txt2); line-height: 1.5; margin-top: 6px;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .psb-card-score { font-family: var(--font-mono); font-size: 11px; color: var(--txt3); white-space: nowrap; margin-top: 2px; }
    .psb-card-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; margin-top: 2px; position: relative; }
    .psb-minibar-wrap { position: relative; cursor: default; }
    .psb-minibar {
      width: 60px; height: 8px; border-radius: 4px; overflow: hidden;
      display: flex; background: var(--oat-l);
    }
    .psb-minibar-vec { background: #1B73E8; height: 100%; transition: width 200ms; }
    .psb-minibar-txt { background: #00A972; height: 100%; transition: width 200ms; }
    .psb-minibar-legend { display: flex; gap: 8px; font-size: 9px; color: var(--txt3); margin-top: 2px; }
    .psb-minibar-legend span::before { content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 2px; margin-right: 3px; vertical-align: middle; }
    .psb-minibar-legend .vec::before { background: #1B73E8; }
    .psb-minibar-legend .txt::before { background: #00A972; }
    .psb-tip {
      display: none; position: absolute; right: 0; top: 100%; margin-top: 6px;
      background: var(--navy); color: #e8f0f2; font-family: var(--font-mono); font-size: 11px;
      padding: 8px 10px; border-radius: var(--r-md); white-space: nowrap; z-index: 20;
      box-shadow: 0 4px 12px rgba(11,32,38,0.25); line-height: 1.6;
    }
    .psb-tip .vec-c { color: #72b4ff; } .psb-tip .txt-c { color: #6ee7b7; }
    .psb-tip .dim { color: #8aa; }
    .psb-minibar-wrap:hover .psb-tip { display: block; }
    .psb-pag { display: flex; justify-content: center; align-items: center; gap: 4px; padding: 16px 24px; }
    .psb-pg {
      min-width: 32px; height: 32px; border: 1px solid var(--oat); border-radius: var(--r-md);
      background: var(--white); color: var(--txt); font: inherit; font-size: 13px;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: background 80ms, border-color 80ms;
    }
    .psb-pg:hover { background: var(--oat-l); border-color: var(--navy-7); }
    .psb-pg.active { background: var(--lava); color: var(--white); border-color: var(--lava); }
    .psb-pg:disabled { opacity: 0.4; cursor: not-allowed; }
  `;
  el.appendChild(style);

  const root = document.createElement('div'); root.className = 'psb-root'; el.appendChild(root);
  const PAGE_SIZE = 10;

  const ce = (tag, cls, txt) => {
    const n = document.createElement(tag); if (cls) n.className = cls;
    if (txt != null) n.textContent = String(txt); return n;
  };

  const header = ce('div', 'psb-header');
  header.append(ce('div', 'psb-title', 'Tech Product Search'));
  header.append(ce('div', 'psb-sub', 'Hybrid search (BM25 + vector) over 10,000 products powered by Lakebase'));
  const svgExpand = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const svgCollapse = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>';
  const isFs = () => { const f = document.fullscreenElement || document.webkitFullscreenElement; return f && root.contains(f); };
  const syncFsBtn = () => { const b = root.querySelector('.psb-fs-btn'); if (b) { b.innerHTML = isFs() ? svgCollapse : svgExpand; b.title = isFs() ? 'Exit fullscreen' : 'Fullscreen'; } };
  const toggleFs = () => {
    if (isFs()) { (document.exitFullscreen || document.webkitExitFullscreen || (() => {})).call(document); }
    else if (root.requestFullscreen) { root.requestFullscreen().catch(() => {}); }
    else if (root.webkitRequestFullscreen) { root.webkitRequestFullscreen(); }
  };
  const onFsChange = () => syncFsBtn();
  document.addEventListener('fullscreenchange', onFsChange);
  document.addEventListener('webkitfullscreenchange', onFsChange);
  const fsBtn = ce('button', 'psb-fs-btn');
  fsBtn.innerHTML = svgExpand; fsBtn.title = 'Fullscreen';
  fsBtn.addEventListener('click', toggleFs);
  header.append(fsBtn);

  root.append(header);

  const barWrap = ce('div', 'psb-bar-wrap');
  const input = document.createElement('input'); input.className = 'psb-input'; input.type = 'text';
  input.placeholder = 'Search products\u2026'; input.value = model.get('query_text') || '';
  const btn = ce('button', 'psb-btn', 'Search');
  const sugBox = ce('div', 'psb-sug');
  const svgCog = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9.4a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
  const cogBtn = ce('button', 'psb-icon-btn');
  cogBtn.innerHTML = svgCog + '<span class="psb-dot"></span>';
  cogBtn.title = 'Search settings';
  barWrap.append(input, cogBtn, btn, sugBox);
  root.append(barWrap);

  /* ── Settings panel: category pre-filter ── */
  const settings = ce('div', 'psb-settings');
  const catSelect = document.createElement('select');
  catSelect.className = 'psb-select';
  const clearBtn = ce('button', 'psb-clear', 'Clear');
  settings.append(ce('span', 'psb-set-label', 'Category'), catSelect, clearBtn);
  root.append(settings);

  const syncCogState = () => {
    cogBtn.classList.toggle('filtered', Boolean(model.get('category_filter')));
    cogBtn.classList.toggle('active', settings.classList.contains('open'));
  };
  const renderCategories = () => {
    let cats = [];
    try { cats = JSON.parse(model.get('categories_json') || '[]'); } catch(e) {}
    const current = model.get('category_filter') || '';
    catSelect.replaceChildren();
    const all = document.createElement('option');
    all.value = ''; all.textContent = 'All categories';
    catSelect.append(all);
    if (!cats.length) {
      const loading = document.createElement('option');
      loading.value = '__loading'; loading.textContent = 'Loading categories\u2026'; loading.disabled = true;
      catSelect.append(loading);
    }
    for (const c of cats) {
      const o = document.createElement('option');
      o.value = c; o.textContent = c;
      catSelect.append(o);
    }
    catSelect.value = current;
    syncCogState();
  };
  const applyCategory = (value) => {
    model.set('category_filter', value);
    model.save_changes();
    syncCogState();
    if (input.value.trim()) doSearch();
  };
  catSelect.addEventListener('change', () => applyCategory(catSelect.value));
  clearBtn.addEventListener('click', () => { catSelect.value = ''; applyCategory(''); });
  cogBtn.addEventListener('click', () => {
    const open = !settings.classList.contains('open');
    settings.classList.toggle('open', open);
    syncCogState();
    const loaded = (model.get('categories_json') || '[]') !== '[]';
    if (open && !loaded) {
      model.set('command', '');
      model.set('command', 'categories');
      model.save_changes();
    }
  });
  model.on('change:categories_json', renderCategories);
  model.on('change:category_filter', renderCategories);
  renderCategories();

  /* ── Server-side suggestions ── */
  let sugDebounce = null;
  const requestSuggestions = (q) => {
    if (!q || q.length < 2) {
      sugBox.replaceChildren(); sugBox.classList.remove('open');
      model.set('suggest_query', ''); model.save_changes(); return;
    }
    sugBox.replaceChildren();
    const loader = ce('div', 'psb-sug-loading');
    loader.append(ce('div', 'psb-spinner'), ce('span', '', 'Searching\u2026'));
    sugBox.append(loader); sugBox.classList.add('open');
    model.set('suggest_query', q); model.save_changes();
  };
  const renderSuggestions = () => {
    if (model.get('suggest_busy')) return;
    let items = [];
    try { items = JSON.parse(model.get('suggestions_json') || '[]'); } catch(e) {}
    sugBox.replaceChildren();
    if (!items.length) { sugBox.classList.remove('open'); return; }
    for (const m of items) {
      const item = ce('div', 'psb-sug-item');
      item.append(ce('span', 'psb-sug-title', m.t));
      if (m.c) item.append(ce('span', 'psb-sug-cat', m.c));
      if (m.p != null) item.append(ce('span', 'psb-sug-price', '$' + Number(m.p).toFixed(2)));
      item.addEventListener('click', () => {
        input.value = m.t; model.set('query_text', m.t); model.save_changes();
        sugBox.classList.remove('open');
      });
      sugBox.append(item);
    }
    sugBox.classList.add('open');
  };
  model.on('change:suggestions_json', renderSuggestions);
  model.on('change:suggest_busy', () => { if (!model.get('suggest_busy')) renderSuggestions(); });
  input.addEventListener('input', () => {
    clearTimeout(sugDebounce);
    sugDebounce = setTimeout(() => requestSuggestions(input.value), 300);
  });
  input.addEventListener('focus', () => { if (input.value.length >= 2) requestSuggestions(input.value); });
  document.addEventListener('click', (e) => { if (!barWrap.contains(e.target)) sugBox.classList.remove('open'); });

  const doSearch = () => {
    sugBox.classList.remove('open');
    model.set('query_text', input.value);
    model.set('command', '');
    model.set('command', 'search');
    model.save_changes();
  };
  btn.addEventListener('click', doSearch);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });

  const statusDiv = ce('div', 'psb-status');
  const errorDiv = ce('div', 'psb-error');
  const resultsDiv = ce('div', 'psb-results');
  const pagDiv = ce('div', 'psb-pag');
  root.append(statusDiv, errorDiv, resultsDiv, pagDiv);

  let currentPage = 0;
  const renderResults = () => {
    resultsDiv.replaceChildren(); pagDiv.replaceChildren();
    statusDiv.textContent = model.get('status') || '';
    const err = model.get('error') || '';
    errorDiv.textContent = err; errorDiv.style.display = err ? '' : 'none';
    btn.textContent = model.get('busy') ? 'Searching\u2026' : 'Search';
    btn.disabled = Boolean(model.get('busy'));

    let rows = [];
    try { rows = JSON.parse(model.get('results_json') || '[]'); } catch(e) {}
    if (!rows.length) return;

    const totalPages = Math.ceil(rows.length / PAGE_SIZE);
    currentPage = Math.max(0, Math.min(currentPage, totalPages - 1));
    const start = currentPage * PAGE_SIZE;
    const pageRows = rows.slice(start, start + PAGE_SIZE);

    for (let i = 0; i < pageRows.length; i++) {
      const r = pageRows[i];
      const card = ce('div', 'psb-card');
      card.append(ce('div', 'psb-rank', start + i + 1));
      const body = ce('div', 'psb-card-body');
      body.append(ce('div', 'psb-card-title', r.title || ''));
      const meta = ce('div', 'psb-card-meta');
      if (r.category) meta.append(ce('span', 'psb-badge', r.category));
      if (r.price != null) meta.append(ce('span', 'psb-price', '$' + Number(r.price).toFixed(2)));
      if (r.rating != null) {
        const rat = ce('span', 'psb-rating');
        const stars = Math.round(r.rating);
        rat.innerHTML = '<span class="star">' + '\u2605'.repeat(stars) + '</span>' + '\u2606'.repeat(5 - stars) + ' ' + Number(r.rating).toFixed(1);
        meta.append(rat);
      }
      body.append(meta);
      if (r.preview) body.append(ce('div', 'psb-preview', r.preview));
      card.append(body);
      /* ── Right column: RRF score + mini bar + tooltip ── */
      const right = ce('div', 'psb-card-right');
      if (r.score != null) right.append(ce('div', 'psb-card-score', 'RRF ' + r.score.toFixed(5)));
      const total = (r.vr || 0) + (r.kr || 0);
      if (total > 0) {
        const vPct = ((r.vr || 0) / total * 100).toFixed(1);
        const kPct = ((r.kr || 0) / total * 100).toFixed(1);
        const wrap = ce('div', 'psb-minibar-wrap');
        const bar = ce('div', 'psb-minibar');
        const vSeg = ce('div', 'psb-minibar-vec'); vSeg.style.width = vPct + '%';
        const kSeg = ce('div', 'psb-minibar-txt'); kSeg.style.width = kPct + '%';
        bar.append(vSeg, kSeg);
        const legend = ce('div', 'psb-minibar-legend');
        legend.innerHTML = '<span class="vec">' + vPct + '%</span><span class="txt">' + kPct + '%</span>';
        const tip = ce('div', 'psb-tip');
        tip.innerHTML =
          '<span class="vec-c">vector</span> <span class="dim">rank ' + (r.vk != null ? r.vk : '\u2014') + ' \u2192 1/(60+' + (r.vk != null ? r.vk : '\u2014') + ') =</span> ' + (r.vr || 0).toFixed(6) + '\n' +
          '<span class="txt-c">bm25  </span> <span class="dim">rank ' + (r.kk != null ? r.kk : '\u2014') + ' \u2192 1/(60+' + (r.kk != null ? r.kk : '\u2014') + ') =</span> ' + (r.kr || 0).toFixed(6) + '\n' +
          '<span class="dim">total =</span> ' + (r.score || 0).toFixed(6);
        wrap.append(bar, legend, tip);
        right.append(wrap);
      }
      card.append(right);
      resultsDiv.append(card);
    }

    if (totalPages <= 1) return;
    const mkPg = (label, page, disabled) => {
      const b = ce('button', 'psb-pg' + (page === currentPage ? ' active' : ''), label);
      b.disabled = disabled;
      if (!disabled) b.addEventListener('click', () => { currentPage = page; renderResults(); });
      return b;
    };
    pagDiv.append(mkPg('\u25C0', currentPage - 1, currentPage === 0));
    for (let p = 0; p < totalPages; p++) {
      if (totalPages > 7 && p > 1 && p < totalPages - 2 && Math.abs(p - currentPage) > 1) {
        if (p === 2 || p === totalPages - 3) pagDiv.append(ce('span', '', '\u2026'));
        continue;
      }
      pagDiv.append(mkPg(String(p + 1), p, false));
    }
    pagDiv.append(mkPg('\u25B6', currentPage + 1, currentPage >= totalPages - 1));
  };

  model.on('change:results_json', () => { currentPage = 0; renderResults(); });
  model.on('change:busy', renderResults);
  model.on('change:error', renderResults);
  model.on('change:status', renderResults);
  renderResults();
}
'''  # end _SEARCH_BAR_ESM


class ProductSearchBarWidget(anywidget.AnyWidget):
    """Clean product search bar with auto-suggestions and paginated hybrid results."""

    _esm = _SEARCH_BAR_ESM

    query_text = traitlets.Unicode("").tag(sync=True)
    category_filter = traitlets.Unicode("").tag(sync=True)
    categories_json = traitlets.Unicode("[]").tag(sync=True)
    suggest_query = traitlets.Unicode("").tag(sync=True)
    suggestions_json = traitlets.Unicode("[]").tag(sync=True)
    suggest_busy = traitlets.Bool(False).tag(sync=True)
    results_json = traitlets.Unicode("[]").tag(sync=True)
    busy = traitlets.Bool(False).tag(sync=True)
    error = traitlets.Unicode("").tag(sync=True)
    status = traitlets.Unicode("").tag(sync=True)
    command = traitlets.Unicode("").tag(sync=True)

    def __init__(
        self,
        *,
        fetch_fn: Callable[..., Any] | None = None,
        embed_fn: Callable[[str, str], List[float]] | None = None,
        database_name: str = "",
        table_name: str = "products",
        embedding_model: str = "databricks-gte-large-en",
        **kwargs: Any,
    ) -> None:
        self._fetch_fn = fetch_fn
        self._embed_fn = embed_fn
        self._database_name = database_name
        self._table_name = table_name
        self._embedding_model = embedding_model
        super().__init__(**kwargs)

    @traitlets.observe("suggest_query")
    def _handle_suggest(self, change: Dict[str, Any]) -> None:
        q = (change["new"] or "").strip()
        if len(q) < 2:
            self.suggestions_json = "[]"
            return
        self.suggest_busy = True
        try:
            tbl = self._table_name
            bm25_idx = f"{tbl.rsplit('.', 1)[0] + '.' if '.' in tbl else ''}{tbl.split('.')[-1]}_body_bm25_idx"
            cat = (self.category_filter or "").strip()
            if len(q) <= 3:
                suggest_sql = f"SELECT title, root_category, price FROM {tbl} WHERE title ILIKE %s"
                params: List[Any] = [f"%{q}%"]
                if cat:
                    suggest_sql += " AND root_category = %s"
                    params.append(cat)
                suggest_sql += " ORDER BY rating DESC LIMIT 7"
            else:
                score_expr = f"body_tsv <@> to_bm25query(to_tsvector('english', %s), '{bm25_idx}')"
                suggest_sql = f"SELECT title, root_category, price FROM {tbl} WHERE {score_expr} IS NOT NULL"
                params = [q]
                if cat:
                    suggest_sql += " AND root_category = %s"
                    params.append(cat)
                suggest_sql += f" ORDER BY {score_expr} LIMIT 7"
                params.append(q)
            df = self._fetch_fn(suggest_sql, tuple(params), dbname=self._database_name)
            items = []
            for r in df.to_dict("records"):
                price = r.get("price")
                items.append({
                    "t": r["title"],
                    "c": r.get("root_category", ""),
                    "p": round(float(price), 2) if price is not None and hasattr(price, 'as_integer_ratio') else (round(float(price), 2) if price is not None else None),
                })
            self.suggestions_json = json.dumps(items)
        except Exception:
            self.suggestions_json = "[]"
        finally:
            self.suggest_busy = False

    @traitlets.observe("command")
    def _handle_command(self, change: Dict[str, Any]) -> None:
        cmd = change["new"]
        if cmd not in ("search", "categories"):
            return
        try:
            if cmd == "search":
                self._do_search()
            else:
                self._load_categories()
        finally:
            self.command = ""

    def _load_categories(self) -> None:
        """Populate the settings panel dropdown with distinct categories."""
        try:
            df = self._fetch_fn(
                f"SELECT DISTINCT root_category FROM {self._table_name} "
                f"WHERE root_category IS NOT NULL AND root_category <> '' ORDER BY 1",
                dbname=self._database_name,
            )
            self.categories_json = json.dumps(
                [str(c) for c in df["root_category"].tolist()]
            )
        except Exception as exc:
            self.error = f"Could not load categories: {exc}"

    def _do_search(self) -> None:
        query = self.query_text.strip()
        if not query:
            self.results_json = "[]"
            self.status = ""
            return
        self.busy = True
        self.error = ""
        try:
            import time as _t
            t0 = _t.perf_counter()
            emb = self._embed_fn(query, self._embedding_model)
            lit = "[" + ",".join(f"{v:.12f}" for v in emb) + "]"
            tbl = self._table_name
            bm25_idx = f"{tbl.rsplit('.', 1)[0] + '.' if '.' in tbl else ''}{tbl.split('.')[-1]}_body_bm25_idx"
            cat = (self.category_filter or "").strip()
            cat_clause = " WHERE d.root_category = %s" if cat else ""
            params: List[Any] = [lit, query] + ([cat] if cat else []) + ([cat] if cat else [])
            results = self._fetch_fn(
                f"WITH q AS (SELECT %s::vector AS qv, %s AS qt), "
                f"vector_ranked AS ("
                f"  SELECT id, RANK() OVER (ORDER BY dist) AS rank FROM ("
                f"    SELECT id, d.embedding <=> q.qv AS dist FROM {tbl} d, q{cat_clause} ORDER BY dist LIMIT 100"
                f"  ) v"
                f"), keyword_ranked AS ("
                f"  SELECT id, RANK() OVER (ORDER BY score) AS rank FROM ("
                f"    SELECT id, d.body_tsv <@> to_bm25query(to_tsvector('english', q.qt), '{bm25_idx}') AS score"
                f"    FROM {tbl} d, q{cat_clause} ORDER BY score LIMIT 100"
                f"  ) k"
                f") SELECT d.id, d.title, d.root_category, d.price, d.rating,"
                f"  LEFT(d.body, 160) AS preview,"
                f"  v.rank AS v_rank, k.rank AS k_rank,"
                f"  COALESCE(1.0/(60+v.rank),0) AS v_rrf,"
                f"  COALESCE(1.0/(60+k.rank),0) AS k_rrf,"
                f"  COALESCE(1.0/(60+v.rank),0)+COALESCE(1.0/(60+k.rank),0) AS rrf_score"
                f" FROM {tbl} d"
                f" LEFT JOIN vector_ranked v ON d.id=v.id"
                f" LEFT JOIN keyword_ranked k ON d.id=k.id"
                f" WHERE v.id IS NOT NULL OR k.id IS NOT NULL"
                f" ORDER BY rrf_score DESC, d.id LIMIT 100",
                tuple(params),
                dbname=self._database_name,
            )
            elapsed = (_t.perf_counter() - t0) * 1000
            rows = []
            for r in results.to_dict("records"):
                price = r.get("price")
                rating = r.get("rating")
                v_rrf = r.get("v_rrf")
                k_rrf = r.get("k_rrf")
                v_rank = r.get("v_rank")
                k_rank = r.get("k_rank")
                rows.append({
                    "title": r["title"],
                    "category": r.get("root_category", ""),
                    "price": round(float(price), 2) if price is not None and hasattr(price, 'as_integer_ratio') else (round(float(price), 2) if price is not None else None),
                    "rating": round(float(rating), 1) if rating is not None and hasattr(rating, 'as_integer_ratio') else (round(float(rating), 1) if rating is not None else None),
                    "preview": r.get("preview", ""),
                    "score": round(float(r["rrf_score"]), 6),
                    "vr": round(float(v_rrf), 6) if v_rrf is not None and v_rrf == v_rrf else 0,
                    "kr": round(float(k_rrf), 6) if k_rrf is not None and k_rrf == k_rrf else 0,
                    "vk": int(v_rank) if v_rank is not None and v_rank == v_rank else None,
                    "kk": int(k_rank) if k_rank is not None and k_rank == k_rank else None,
                })
            self.results_json = json.dumps(rows)
            cat_suffix = f" \u00b7 {cat}" if cat else ""
            self.status = f"{len(rows)} results \u00b7 {elapsed:.0f} ms{cat_suffix}"
        except Exception as exc:
            self.error = str(exc)
            self.status = "Search failed"
        finally:
            self.busy = False
