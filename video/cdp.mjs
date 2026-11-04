// A tiny Chrome DevTools Protocol client for the Mattermost view embedded in Switch Console
// (Console started with remote debugging on 9339). Node 22 has WebSocket built in.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function connect(titleSub = 'Mattermost', port = 9339) {
  let ws = null;
  let id = 0;
  const pending = new Map(); // id -> { resolve, reject, socket }

  async function open() {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const target = list.find((t) => t.type === 'webview' && t.title.includes(titleSub));
    if (!target) throw new Error(`no webview whose title contains "${titleSub}" on port ${port}`);
    const socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener('open', resolve); socket.addEventListener('error', reject); });
    socket.addEventListener('message', (e) => {
      const m = JSON.parse(e.data);
      const p = m.id && pending.get(m.id);
      if (p) { pending.delete(m.id); p.resolve(m); }
    });
    // a dropped connection must fail the calls waiting on it, not leave them hanging forever
    socket.addEventListener('close', () => {
      for (const [i, p] of pending) if (p.socket === socket) { pending.delete(i); p.reject(new Error('CDP connection closed')); }
    });
    ws = socket;
  }
  await open();

  const send = (method, params = {}, timeoutMs = 20000) => new Promise((resolve, reject) => {
    const i = ++id;
    const timer = setTimeout(() => { pending.delete(i); reject(new Error(`CDP ${method} timed out`)); }, timeoutMs);
    pending.set(i, { socket: ws, resolve: (m) => { clearTimeout(timer); resolve(m); }, reject: (e) => { clearTimeout(timer); reject(e); } });
    try { ws.send(JSON.stringify({ id: i, method, params })); } catch (e) { pending.delete(i); clearTimeout(timer); reject(e); }
  });
  const ev = async (js) => {
    const r = await send('Runtime.evaluate', { expression: js, returnByValue: true, awaitPromise: true });
    if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
    return r.result?.result?.value;
  };
  async function reconnect() {
    try { ws?.close(); } catch { /* already closed */ }
    await open();
  }

  // Frames are screenshots of the view taken several times a second; one is saved only when the picture changed,
  // so each frame's timestamp (seconds, wall clock) says how long it stayed on screen. (Chromium's own screencast
  // sends nothing while the Console window is not being painted, so it cannot be used here.)
  const frames = [];
  let polling = false;
  let loop = null;
  const flush = (dir) => fs.writeFileSync(path.join(dir, 'frames.json'), JSON.stringify(frames));
  async function startScreencast(dir, { fps = 8, quality = 82, append = false } = {}) {
    fs.mkdirSync(dir, { recursive: true });
    if (append && fs.existsSync(path.join(dir, 'frames.json'))) frames.push(...JSON.parse(fs.readFileSync(path.join(dir, 'frames.json'), 'utf8')));
    polling = true;
    let last = '';
    loop = (async () => {
      while (polling) {
        const t0 = Date.now();
        try {
          const r = await send('Page.captureScreenshot', { format: 'jpeg', quality });
          if (!r.result?.data) throw new Error(r.error?.message || 'no screenshot data');
          const buf = Buffer.from(r.result.data, 'base64');
          const hash = crypto.createHash('md5').update(buf).digest('hex');
          if (hash !== last) {
            last = hash;
            const n = String(frames.length).padStart(6, '0');
            fs.writeFileSync(path.join(dir, `${n}.jpg`), buf);
            frames.push({ file: `${n}.jpg`, t: Date.now() / 1000 });
            if (frames.length % 25 === 0) flush(dir);
          }
        } catch {
          await sleep(500);
          try { await reconnect(); } catch { /* the target may be gone for a moment; try again next round */ }
        }
        await sleep(Math.max(0, 1000 / fps - (Date.now() - t0)));
      }
    })();
  }
  async function stopScreencast(dir) {
    polling = false;
    await loop;
    flush(dir);
    return frames.length;
  }
  return { send, ev, reconnect, startScreencast, stopScreencast, close: () => ws?.close() };
}
