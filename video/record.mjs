// Records a full Issue Desk run (storyboard rows 3-9) from the Mattermost view embedded in Switch Console.
//
//   node video/record.mjs --issue 11 --good 12 [--out video/out] [--hub desk] [--scope-note "..."]
//
// Needs: Switch Console running with remote debugging on port 9339 and the issue-desk template already created
// (the hub room and the three agents exist), the sandbox seeded (mirror + seed-practice). It types as the
// maintainer, so run it on a fresh hub. Output (git-ignored): frames/*.jpg, frames/frames.json, actions.json.
// Nothing outside the embedded Mattermost view is captured.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { connect } from './cdp.mjs';

const arg = (name, fallback) => { const i = process.argv.indexOf(`--${name}`); return i > -1 ? process.argv[i + 1] : fallback; };
const ISSUE = arg('issue');
const GOOD = arg('good');
const HUB = arg('hub', 'desk');
const FROM = Number(arg('from', 3)); // resume at this storyboard row (needs the earlier rows already recorded in --out)
const OUT = path.resolve(arg('out', new URL('./out/', import.meta.url).pathname));
if (!ISSUE || !GOOD) { console.error('usage: node video/record.mjs --issue N --good PR [--hub desk] [--out dir] [--from ROW]'); process.exit(2); }

const SETTINGS = 'Scope: src/storage/** tests/** docs/**  /  Install: npm ci --ignore-scripts --no-audit --no-fund  /  Tests: node tests/run-history-schema.test.js && node tests/docker-run-history.test.js && node tests/history-backup.test.js';
const EDIT = arg('scope-note', `@scout Set the last three lines of Direction to exactly (one line each): ${SETTINGS} . Keep them off GitHub. Rewrite the body so it stays inside that scope.`);

const REPO = arg('repo', 'JemIIahh/issue-desk-sandbox');
const ghIssue = () => JSON.parse(execFileSync('gh', ['issue', 'view', ISSUE, '--repo', REPO, '--json', 'comments'], { encoding: 'utf8' })).comments;
const github = { issue: ISSUE, before: ghIssue().length };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const now = () => Date.now() / 1000;
const stamp = () => new Date().toLocaleTimeString('en-GB', { timeZone: 'Africa/Lagos' });
const log = (...a) => console.log(`[${stamp()}]`, ...a);

const cdp = await connect('Mattermost');
// every page call gets one retry on a fresh connection, in case Console re-created the view
const ev = async (js) => {
  try { return await cdp.ev(js); } catch (err) {
    log('page call failed, reconnecting:', String(err.message).slice(0, 120));
    await cdp.reconnect();
    return cdp.ev(js);
  }
};
const actions = [];
let hubName = '';
const save = () => fs.writeFileSync(path.join(OUT, 'actions.json'), JSON.stringify({ hub: hubName, issue: ISSUE, github, actions }, null, 1));
const push = (a) => { actions.push(a); save(); };
const frameDir = path.join(OUT, 'frames');
if (FROM > 3) { // resuming: keep what was recorded and add to it
  const saved = JSON.parse(fs.readFileSync(path.join(OUT, 'actions.json'), 'utf8'));
  actions.push(...saved.actions);
  Object.assign(github, saved.github);
  hubName = saved.hub;
} else {
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });
}

// ---- page helpers (run inside Mattermost) ----
const PRE = `
const H={'X-Requested-With':'XMLHttpRequest','Content-Type':'application/json'};
const api=async(p,o={})=>(await fetch('/api/v4'+p,{headers:H,credentials:'include',...o})).json();
const team=location.pathname.split('/')[1];
const chans=async()=>{const ts=await api('/users/me/teams');let o=[];for(const t of ts)o=o.concat(await api('/users/me/teams/'+t.id+'/channels'));return o};
const findCh=async s=>(await chans()).filter(c=>c.name.includes(s)).sort((a,b)=>b.create_at-a.create_at)[0];
`;
const page = (body) => ev(`(async()=>{${PRE}${body}})()`);

async function channelId(sub) {
  const c = await page(`const c=await findCh(${JSON.stringify(sub)}); return c?{id:c.id,name:c.name}:null`);
  if (!c) throw new Error(`no channel matching ${sub}`);
  return c;
}
async function recent(sub, n = 40) {
  return page(`const c=await findCh(${JSON.stringify(sub)});const d=await api('/channels/'+c.id+'/posts?per_page=${n}');
    const ps=d.order.map(i=>d.posts[i]).sort((a,b)=>a.create_at-b.create_at);
    const us=await api('/users/ids',{method:'POST',body:JSON.stringify([...new Set(ps.map(p=>p.user_id))])});const m={};us.forEach(u=>m[u.id]=u.username);
    return ps.map(p=>({id:p.id,root:p.root_id,user:m[p.user_id],msg:p.message,at:p.create_at}))`);
}
async function gotoChannel(sub) {
  const c = await channelId(sub);
  await ev(`window.WebappUtils.browserHistory.push('/'+location.pathname.split('/')[1]+'/channels/${c.name}')`);
  await sleep(1500);
  return c;
}

let lastSayMs = 0; // waits only count posts made after the maintainer last spoke, never older ones

// ---- recorded actions ----
function mark(row, label) { push({ kind: 'mark', row, label, start: now(), end: now() }); log(`ROW ${row}: ${label}`); }

async function typeInto(sel, text, perChar = 55) {
  await ev(`document.querySelector(${JSON.stringify(sel)}).focus()`);
  const paste = text.length > 90; // long lines are pasted, short ones typed at human pace
  const chunks = paste ? [text] : [...text];
  for (const ch of chunks) {
    await ev(`(()=>{const t=document.querySelector(${JSON.stringify(sel)});const set=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;set.call(t,t.value+${JSON.stringify(ch)});t.dispatchEvent(new Event('input',{bubbles:true}))})()`);
    if (!paste) await sleep(perChar * (0.6 + Math.random() * 0.8));
  }
}
async function pressSend(scope) {
  await sleep(500);
  await ev(`document.querySelector(${JSON.stringify(scope + ' [data-testid="SendMessageButton"]')}).click()`);
}

/** The maintainer writes a message in the open channel. Returns when it is sent. */
async function say(row, text) {
  const start = now();
  lastSayMs = Date.now();
  await typeInto('#post_textbox', text);
  await pressSend('#channel_view');
  push({ kind: 'act', row, label: `say: ${text.slice(0, 60)}`, start, end: now() });
  log('say:', text.slice(0, 80));
  await sleep(800);
}

/** Wait until `test(posts)` is true. The interval is logged as a wait so the cut can speed it up. */
async function waitFor(row, label, sub, test, timeoutS = 600) {
  const start = now();
  while (now() - start < timeoutS) {
    let ps;
    try { ps = await recent(sub, 60); } catch (err) { log('read failed, retrying:', String(err.message).slice(0, 100)); await sleep(3000); continue; }
    const fresh = ps.filter((p) => p.at >= lastSayMs - 500);
    if (test(fresh)) { push({ kind: 'wait', row, label, start, end: now() }); log(`done waiting: ${label} (${Math.round(now() - start)}s)`); return fresh; }
    await sleep(4000);
  }
  push({ kind: 'wait', row, label: label + ' (TIMED OUT)', start, end: now() });
  throw new Error(`timed out: ${label}`);
}
// an agent has answered since the maintainer spoke, and then nothing new for `seconds`
const quiet = (seconds) => (ps) => ps.some((p) => p.user !== 'user') && Date.now() - ps.at(-1).at > seconds * 1000;

/** Card ids run on through the room (A1 for scout's comment, A2-A4 for bench's notes), so take the next one not yet answered. */
const answered = new Set();
const openCard = (list) => {
  for (const p of list) {
    const m = p.root && /request `(A\d+)`/.exec(p.msg);
    if (m && !answered.has(m[1])) return { card: m[1], root: p.root };
  }
  return null;
};

/** Open the thread holding the next unanswered approval card and answer it with `choice` (1 = allow once). */
async function answerCard(row, sub, choice = '1') {
  const ps = await waitFor(row, 'approval card', sub, (list) => openCard(list) !== null, 240);
  const { card, root } = openCard(ps);
  const reply = `${card} ${choice}`;
  answered.add(card);
  const opened = await ev(`(()=>{const b=document.querySelector('#post_${root} .ReplyButton');if(b){b.click();return true}return false})()`);
  if (!opened) await ev(`window.WebappUtils.browserHistory.push('/'+location.pathname.split('/')[1]+'/pl/${root}')`);
  await sleep(2500);
  const t0 = now();
  await typeInto('#reply_textbox', reply, 90);
  await pressSend('#rhsContainer');
  push({ kind: 'act', row, label: `approve: ${reply}`, start: t0, end: now() });
  log('approved:', reply);
  await sleep(3000);
  return root;
}

const closeThread = () => ev(`(()=>{const b=document.querySelector('#rhsContainer .sidebar--right__close, #rhsContainer button[aria-label="Close"]');if(b)b.click()})()`);

// ---- the run ----
hubName = (await channelId(HUB)).name;
if (FROM >= 7) for (const p of await recent(`issue-${ISSUE}`, 100)) { const m = /request `(A\d+)`/.exec(p.msg); if (m) answered.add(m[1]); } // cards answered before this run
await gotoChannel(FROM >= 4 && FROM <= 8 ? `issue-${ISSUE}` : HUB);
if (FROM >= 10) await closeThread();
const gapStart = FROM > 3 ? Math.max(...actions.map((a) => a.end)) + 4 : 0;
await cdp.startScreencast(frameDir, { append: FROM > 3 });
if (FROM > 3) push({ kind: 'skip', row: FROM, label: 'recording stopped and resumed: time not shown', start: gapStart, end: now() });
await sleep(2500);

try {
  if (FROM <= 3) {
  mark(3, 'sweep');
  await say(3, '@desk sweep');
  await waitFor(3, 'desk sweeps the repo', HUB, (ps) => ps.some((p) => p.user === 'desk' && /hot issues?/i.test(p.msg)), 240);
  await sleep(2500);
  await say(3, `@desk open ${ISSUE}`);
  await waitFor(3, 'desk opens the room', HUB, (ps) => ps.some((p) => p.user === 'desk' && /opened/i.test(p.msg) && p.msg.includes(`issue-${ISSUE}`)), 400);
  await sleep(2500);
  }

  if (FROM <= 4) {
  mark(4, 'the new room');
  await gotoChannel(`issue-${ISSUE}`);
  await sleep(4000);
  }

  if (FROM <= 5) {
  mark(5, 'scout triage');
  await waitFor(5, 'scout reads every claim', `issue-${ISSUE}`, (ps) => ps.some((p) => p.user === 'scout' && /Direction/.test(p.msg) && /draft/i.test(p.msg)), 600);
  await waitFor(5, 'scout finishes', `issue-${ISSUE}`, quiet(40), 300);
  }

  if (FROM <= 6) {
  mark(6, 'edit and post it');
  await say(6, EDIT);
  await waitFor(6, 'scout updates the Direction', `issue-${ISSUE}`, quiet(40), 400);
  await say(6, '@scout post it');
  await answerCard(6, `issue-${ISSUE}`);
  await waitFor(6, 'comment posted', `issue-${ISSUE}`, (ps) => ps.some((p) => p.user === 'scout' && /posted/i.test(p.msg)), 200);
  await sleep(3000);
  const after = ghIssue();
  github.after = after.length;
  github.head = (after.at(-1)?.body || '').split('\n').filter(Boolean).slice(0, 4).join('\n').slice(0, 420);
  }

  if (FROM <= 7) {
  mark(7, 'bench compares');
  await closeThread();
  await say(7, '@bench compare');
  await waitFor(7, 'bench tests each PR in a sealed box', `issue-${ISSUE}`, (ps) => ps.some((p) => p.user === 'bench' && /recommend/i.test(p.msg)), 2700);
  await sleep(4000);
  }

  if (FROM <= 8) {
  mark(8, 'review notes');
  await say(8, `@bench go with ${GOOD}, draft notes for the others`);
  await waitFor(8, 'bench drafts the notes', `issue-${ISSUE}`, (ps) => ps.some((p) => p.user === 'bench' && /drafts?/i.test(p.msg) && p.at > Date.now() - 600000), 300);
  await sleep(3000);
  await say(8, '@bench post it');
  for (let i = 0; i < 3; i++) await answerCard(8, `issue-${ISSUE}`);
  await sleep(6000);
  }

  if (FROM <= 9) {
  mark(9, 'digest');
  await closeThread();
  await gotoChannel(HUB);
  await sleep(2500);
  await say(9, '@desk digest');
  await waitFor(9, 'desk reads every room', HUB, (ps) => ps.some((p) => p.user === 'desk' && /came in|digest:/i.test(p.msg)), 400);
  await sleep(3000);
  }

  if (FROM <= 10) { // show the whole digest: its top, then its bottom
    const post = (await recent(HUB, 30)).filter((p) => p.user === 'desk' && /came in|digest:/i.test(p.msg)).at(-1);
    if (post) {
      await ev(`(()=>{const e=document.querySelector('#post_${post.id}');if(e)e.scrollIntoView({block:'start',behavior:'smooth'})})()`);
      await sleep(9000);
      await ev(`(()=>{const e=document.querySelector('#post_${post.id}');if(e)e.scrollIntoView({block:'end',behavior:'smooth'})})()`);
      await sleep(7000);
    }
  }
} finally {
  const n = await cdp.stopScreencast(frameDir);
  save();
  log(`saved ${n} frames and ${actions.length} actions to ${OUT}`);
  cdp.close();
}
