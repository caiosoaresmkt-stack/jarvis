/**
 * Camada de tradução em tempo de execução (PT-BR).
 *
 * O projeto upstream não possui i18n: os textos estão fixos em inglês nos
 * componentes. Em vez de reescrever dezenas de arquivos, esta camada traduz o
 * DOM a partir de um dicionário (pt-BR.json) gerado em tools/i18n.
 *
 *  - Só altera `nodeValue` de nós de texto e alguns atributos (placeholder,
 *    title, aria-label, alt) — nunca remove/recria nós, então o React segue
 *    funcionando normalmente.
 *  - Ignora conteúdo digitado/gerado (mensagens do chat, código, textarea).
 *  - Idioma: padrão pt-BR. Use ?lang=en (ou localStorage openjarvis-lang=en)
 *    para voltar ao inglês original.
 */
import dictionary from './pt-BR.json';

const STORAGE_KEY = 'openjarvis-lang';
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA', 'NOSCRIPT', 'KBD']);
const SKIP_SELECTOR = '[data-no-i18n], .katex, [contenteditable="true"]';
const ATTRS = ['placeholder', 'title', 'aria-label', 'alt'] as const;

type Pattern = { re: RegExp; out: string; weight: number };

const exact = new Map<string, string>();
const patterns: Pattern[] = [];

function norm(s: string): string {
  return s.replace(/\s+/g, ' ').trim();
}

for (const [en, pt] of Object.entries(dictionary as Record<string, string>)) {
  const key = norm(en);
  if (key.includes('{}')) {
    const parts = key.split('{}').map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    patterns.push({ re: new RegExp('^' + parts.join('(.*?)') + '$', 's'), out: pt, weight: key.replace(/\{\}/g, '').length });
  } else {
    exact.set(key, pt);
  }
}
patterns.sort((a, b) => b.weight - a.weight);

export function translate(raw: string): string | null {
  const key = norm(raw);
  if (!key || !/[A-Za-z]{2}/.test(key)) return null;
  const hit = exact.get(key);
  if (hit !== undefined) return hit;
  for (const p of patterns) {
    const m = p.re.exec(key);
    if (m) {
      let n = 0;
      return p.out.replace(/\{(\d*)\}/g, (_x, idx: string) => m[idx ? Number(idx) : ++n] ?? '');
    }
  }
  return null;
}

function skipped(el: Element | null): boolean {
  for (let e: Element | null = el; e; e = e.parentElement) {
    if (SKIP_TAGS.has(e.tagName)) return true;
  }
  return !!el?.closest(SKIP_SELECTOR);
}

function doText(node: Text): void {
  const parent = node.parentElement;
  if (!parent || skipped(parent)) return;
  const value = node.nodeValue ?? '';
  const out = translate(value);
  if (out === null) return;
  const lead = /^\s*/.exec(value)![0];
  const trail = /\s*$/.exec(value)![0];
  const next = lead + out + trail;
  if (next !== value) node.nodeValue = next;
}

function doAttrs(el: Element): void {
  // placeholder/title de <textarea> e <input> devem ser traduzidos; só o
  // *conteúdo* (texto digitado) é ignorado em doText().
  if (el.tagName !== 'TEXTAREA' && skipped(el)) return;
  if (el.closest(SKIP_SELECTOR)) return;
  for (const a of ATTRS) {
    const v = el.getAttribute(a);
    if (!v) continue;
    const out = translate(v);
    if (out !== null && out !== v) el.setAttribute(a, out);
  }
}

function walk(root: Node): void {
  if (root.nodeType === Node.TEXT_NODE) {
    doText(root as Text);
    return;
  }
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  const el = root as Element;
  doAttrs(el); // atributos (placeholder/title) valem até para <textarea>
  if (SKIP_TAGS.has(el.tagName)) return;
  const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) doText(n as Text);
    else doAttrs(n as Element);
  }
}

export function currentLanguage(): 'pt-BR' | 'en' {
  try {
    const q = new URLSearchParams(window.location.search).get('lang');
    if (q) {
      localStorage.setItem(STORAGE_KEY, q.toLowerCase().startsWith('en') ? 'en' : 'pt-BR');
    }
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'pt-BR';
  } catch {
    return 'pt-BR';
  }
}

export function initI18n(): void {
  if (typeof document === 'undefined' || currentLanguage() !== 'pt-BR') return;
  document.documentElement.lang = 'pt-BR';

  let queue = new Set<Node>();
  let scheduled = false;
  const flush = () => {
    scheduled = false;
    const batch = queue;
    queue = new Set();
    obs.disconnect();
    try {
      batch.forEach((n) => {
        if (n.isConnected) walk(n);
      });
    } finally {
      obs.observe(document.body, OPTS);
    }
  };
  const OPTS: MutationObserverInit = {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: [...ATTRS],
  };
  const obs = new MutationObserver((records) => {
    for (const r of records) {
      if (r.type === 'childList') r.addedNodes.forEach((n) => queue.add(n));
      else if (r.type === 'characterData') queue.add(r.target);
      else queue.add(r.target);
    }
    if (!scheduled) {
      scheduled = true;
      queueMicrotask(flush);
    }
  });

  const start = () => {
    walk(document.body);
    obs.observe(document.body, OPTS);
  };
  if (document.body) start();
  else document.addEventListener('DOMContentLoaded', start, { once: true });
}
