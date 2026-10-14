// quick look: full-page stills at desktop and phone width
import { chromium } from 'playwright';
const out = process.argv[2];
const b = await chromium.launch();
for (const [name, w, h] of [['desktop', 1440, 900], ['phone', 390, 844]]) {
  const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  await p.goto('http://localhost:8765/?static');
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${out}/look-${name}.png`, fullPage: true });
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  console.log(name, 'horizontal overflow px:', overflow);
}
await b.close();
