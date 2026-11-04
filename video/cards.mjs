// Renders the video's cards and caption panels as PNGs (this ffmpeg build has no text filters).
//   node video/cards.mjs video/out/cards.json
// cards.json is written by video/cut.py. Uses playwright-core from the author's other project, as the
// brief says; any playwright-core install works: set PLAYWRIGHT_CORE to its folder.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const core = process.env.PLAYWRIGHT_CORE || `${process.env.HOME}/Desktop/chog-choir-film/`;
const { chromium } = createRequire(core.endsWith('/') ? core : core + '/')('playwright-core');
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const dir = path.dirname(process.argv[2]) + '/cards';
fs.mkdirSync(dir, { recursive: true });

const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
const base = `
  *{box-sizing:border-box;margin:0}
  html,body{width:1920px;height:1080px;overflow:hidden}
  body{font-family:-apple-system,"Helvetica Neue",Helvetica,Arial,sans-serif;color:#f4f1ea;background:var(--bg,#0b0b0c)}
  .accent{color:#e8a23a}
  .mono{font-family:Menlo,Consolas,monospace}
`;
const page = (body, transparent = false) => `<!doctype html><meta charset=utf-8><style>${base}${transparent ? 'body{background:transparent}' : ''}</style><body>${body}`;

const full = (inner) => `<div style="height:1080px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 160px">${inner}</div>`;

const cards = {
  title: full(`<div style="font-size:150px;font-weight:700;letter-spacing:-3px">Issue Desk</div>
    <div style="font-size:52px;margin-top:28px;color:#cfcabf">You decide. Agents do the reading.</div>
    <div class="mono" style="font-size:30px;margin-top:70px;color:#8e897d">built on Switch</div>`),
  counts: full(`<div style="font-size:44px;color:#8e897d;margin-bottom:40px">${esc(spec.counts.source)}</div>
    <div style="font-size:120px;font-weight:700;line-height:1.15"><span class="accent">${esc(spec.counts.issues)}</span> issues. <span class="accent">${esc(spec.counts.comments)}</span> comments.</div>
    <div style="font-size:84px;margin-top:20px;color:#cfcabf">One maintainer.</div>
    <div style="font-size:30px;margin-top:70px;color:#8e897d">${esc(spec.counts.note)}</div>`),
  github: full(`<div style="font-size:40px;color:#8e897d">GitHub, your private sandbox</div>
    <div style="font-size:84px;font-weight:700;margin:26px 0">Issue #${esc(spec.github.issue)}: <span class="accent">${esc(spec.github.before)} → ${esc(spec.github.after)}</span> comments</div>
    <div class="mono" style="font-size:30px;max-width:1500px;line-height:1.5;color:#cfcabf;text-align:left;white-space:pre-wrap;border-left:6px solid #e8a23a;padding-left:30px">${esc(spec.github.head)}</div>
    <div style="font-size:36px;margin-top:50px">Posted only after the maintainer pressed the approval card.</div>`),
  end: full(`<div style="font-size:92px;font-weight:700;line-height:1.2">Clone it, point it at a practice repo.</div>
    <div style="font-size:60px;margin-top:20px;color:#cfcabf">Nothing is written until you approve it.</div>
    <div class="mono" style="font-size:44px;margin-top:80px" >${esc(spec.end.repo)}</div>
    <div style="font-size:34px;margin-top:70px;color:#8e897d">${esc(spec.end.measured)}</div>
    <div class="mono" style="font-size:28px;margin-top:60px;color:#8e897d">Switch · WeMakeDevs · DevTools Academy</div>`),
};
const opaque = new Set(Object.keys(cards));

const panelHtml = (p) => `<div style="position:absolute;left:1400px;top:40px;width:480px;height:1000px;background:#141416;border:1px solid #2a2a2e;border-radius:18px;padding:44px 40px;display:flex;flex-direction:column">
    <div class="mono" style="font-size:24px;color:#8e897d">${esc(p.step)}</div>
    <div style="font-size:50px;line-height:1.25;font-weight:650;margin-top:24px">${esc(p.caption)}</div>
    <div style="flex:1"></div>
    ${p.detail ? `<div style="font-size:28px;line-height:1.4;color:#cfcabf;margin-bottom:34px">${esc(p.detail)}</div>` : ''}
    <div style="border-top:1px solid #2a2a2e;padding-top:26px">
      <div class="mono" style="font-size:22px;color:#8e897d">typing and approving</div>
      <div class="accent" style="font-size:58px;font-weight:700">${esc(p.yourTime)}</div>
    </div></div>`;
const speedHtml = (label) => `<div class="mono" style="position:absolute;left:880px;top:50px;background:#e8a23a;color:#0b0b0c;font-size:28px;font-weight:700;padding:8px 18px;border-radius:10px">${esc(label)}</div>`;

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const shot = async (html, file, transparent) => {
  const p = await ctx.newPage();
  await p.setContent(html);
  await p.screenshot({ path: `${dir}/${file}.png`, omitBackground: transparent });
  await p.close();
};
for (const name of opaque) await shot(page(cards[name]), name, false);
for (const p of spec.panels) await shot(page(panelHtml(p), true), p.file, true);
for (const s of spec.speeds) await shot(page(speedHtml(s.label), true), s.file, true);
for (const s of spec.stills || []) {
  const img = 'data:image/png;base64,' + fs.readFileSync(s.src).toString('base64');
  await shot(page(`<div style="height:1080px;display:flex;flex-direction:column;align-items:center;justify-content:center">
    <img src="${img}" style="height:900px;border-radius:14px;border:1px solid #2a2a2e">
    <div style="font-size:40px;margin-top:34px;color:#f4f1ea">${esc(s.caption)}</div></div>`), s.file, false);
}
await browser.close();
console.log(`rendered ${opaque.size + spec.panels.length + spec.speeds.length + (spec.stills || []).length} images in ${dir}`);
