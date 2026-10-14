// Captures the kestrel studio site for the launch video, deterministically.
//
//   (cd site && python3 -m http.server 8765) &
//   node capture/shoot.mjs            # -> assets/captures/*.png, assets/captures/rects.json, brand/brand.json
//
// Stills at 2x so they stay sharp at 1080 wide. The hero's film is paused on a fixed frame and its
// on-page rectangle is recorded, so the video can lay the real film over it, playing, crisp.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = join(dirname(fileURLToPath(import.meta.url)), '..');
const URL = process.env.SITE_URL || 'http://localhost:8765/?static';
const OUT = join(HERE, 'assets/captures');
mkdirSync(OUT, { recursive: true });
mkdirSync(join(HERE, 'brand'), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
await page.goto(URL, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
// freeze everything that moves: entrance animations done, orbs and playhead still, film on frame 15.5 s
await page.addStyleTag({ content: '*,*::before,*::after{animation-play-state:paused!important} .rise{opacity:1!important;transform:none!important} .playhead{left:38%!important}' });
await page.evaluate(async () => {
  const v = document.getElementById('demo'); v.pause(); v.currentTime = 15.5;
  await new Promise(r => v.addEventListener('seeked', r, { once: true }));
});
await page.waitForTimeout(400);

const rect = sel => page.evaluate(s => { const r = document.querySelector(s).getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, w: r.width, h: r.height }; }, sel);
const rects = { viewport: { w: 1440, h: 900 }, scale: 2 };

// 1. hero, first screen
await page.screenshot({ path: join(OUT, 'hero.png') });
rects.film = await rect('#demo');
rects.studio = await rect('.studio');
rects.h1 = await rect('.hero h1');
rects.badge = await rect('.preview .badge');
rects.sound = await rect('#sound');

// 2. sections as element shots (2x)
for (const [name, sel] of [['flow', '.flow'], ['features', '.features'], ['speed', '.speed'], ['prompts', '.prompts'], ['licence', '.licence'], ['nav', 'nav.top']]) {
  await page.locator(sel).scrollIntoViewIfNeeded();
  await page.waitForTimeout(150);
  await page.locator(sel).screenshot({ path: join(OUT, `${name}.png`), omitBackground: false });
  rects[name] = await rect(sel);
}
// a feature card on its own and the swatch row, for the "takes your look" beat
await page.locator('.card').first().screenshot({ path: join(OUT, 'card-look.png') });

// 3. brand.json — the site's own design tokens, read from the live page (skill §1)
const brand = await page.evaluate(() => {
  const cs = getComputedStyle(document.documentElement);
  const v = n => cs.getPropertyValue(n).trim();
  const h1 = getComputedStyle(document.querySelector('.hero h1'));
  const em = getComputedStyle(document.querySelector('.hero h1 .serif'));
  const body = getComputedStyle(document.body);
  return {
    source: location.origin,
    palette: { background: v('--bg'), ink: v('--ink'), ink2: v('--ink-2'), muted: v('--ink-3'),
               accent: v('--rufous'), accent2: v('--amber'), counter: v('--slate'), cream: v('--cream') },
    gradient: v('--accent-grad'),
    type: { display: h1.fontFamily.split(',')[0].replaceAll('"', ''), displayWeight: h1.fontWeight,
            accent: em.fontFamily.split(',')[0].replaceAll('"', ''), accentStyle: em.fontStyle,
            body: body.fontFamily.split(',')[0].replaceAll('"', ''), mono: v('--mono').split(',')[0].replaceAll('"', '') },
    glass: { fill: [v('--glass-fill'), v('--glass-fill-2')], edge: v('--glass-edge'), highlight: v('--glass-highlight'),
             blur: v('--glass-blur'), radius: v('--glass-radius') },
  };
});
writeFileSync(join(HERE, 'brand/brand.json'), JSON.stringify(brand, null, 1));
writeFileSync(join(OUT, 'rects.json'), JSON.stringify(rects, null, 1));
await browser.close();
console.log('captures:', Object.keys(rects).join(', '));
console.log(JSON.stringify(brand.palette));
