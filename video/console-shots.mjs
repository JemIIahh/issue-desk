// Stills of the Switch Console for the video (Console running with remote debugging on port 9339).
//   node video/console-shots.mjs <issue-room-name> [out-dir]     e.g. issue-11-verified-backup-restore
import { createRequire } from 'node:module';
import path from 'node:path';

const room = process.argv[2];
const out = path.resolve(process.argv[3] || new URL('./out/', import.meta.url).pathname);
if (!room) { console.error('usage: node video/console-shots.mjs <issue-room-name> [out-dir]'); process.exit(2); }
const core = process.env.PLAYWRIGHT_CORE || `${process.env.HOME}/Desktop/chog-choir-film/`;
const { chromium } = createRequire(core.endsWith('/') ? core : core + '/')('playwright-core');
const browser = await chromium.connectOverCDP('http://127.0.0.1:9339');
const page = browser.contexts()[0].pages()[0];
const click = async (text) => { await page.getByText(text, { exact: true }).first().click({ timeout: 8000 }); await page.waitForTimeout(1500); };
// Only the main pane is captured (no sidebar), and the rooms page is cut off above the group of unused rooms.
const size = await page.evaluate(() => ({ w: window.innerWidth, h: window.innerHeight }));
const SIDEBAR = 394;
const TOP = 64; // below the title bar, whose room name is cut off on the left
const pane = { x: SIDEBAR, y: TOP, width: size.w - SIDEBAR, height: size.h - TOP };
await click('Your Rooms');
const unused = await page.getByText('No messaging app', { exact: true }).first().boundingBox().catch(() => null);
await page.screenshot({ path: `${out}/console-rooms.png`, clip: unused ? { ...pane, height: Math.max(200, unused.y - 12 - TOP) } : pane });
await click('#' + room);
await click('Configuration');
await page.screenshot({ path: `${out}/console-room.png`, clip: pane });
await click('Chat');
console.log('saved console-rooms.png and console-room.png in', out);
await browser.close();
