// Focus log for a Playwright capture: what the viewer should look at, and when.
//
// The capture script knows where every element is while it records. This file writes those
// boxes down against the video's clock, so kit/camera.py can frame the recording on them later
// (push in on the reply, pull back for the overview) without guessing from pixels.
//
//   const { focusLog } = require('<kit>/capture.cjs');
//   const page = await ctx.newPage();              // recordVideo starts with the page
//   const log = focusLog(page);                     // so the clock starts here too
//   await log.focus(page.locator('textarea'), 'prompt');
//   log.mark('typed');                              // an event without a box (for kit/waits.py)
//   await log.focus(page.locator('.reply').last(), 'reply', { pad: 12 });
//   await log.follow(page.locator('.reply').last(), 'reply', { ms: 6000 });   // it grows as it streams
//   log.wide('overview');                           // back to the whole recording
//   ...
//   log.save('assets/captures/02-reply.focus.json'); // next to 02-reply.webm
//
// Boxes are in CSS pixels of the viewport. The file also stores the viewport and the video
// size, so camera.py can scale them when recordVideo.size differs from the viewport.
const fs = require('fs');

// Pass { video: { width, height } } when recordVideo.size is not the viewport size.
function focusLog(page, { t0 = Date.now(), video = null } = {}) {
  const viewport = page.viewportSize();
  video = video || viewport;
  const events = [];
  const marks = [];
  const now = () => (Date.now() - t0) / 1000;

  async function box(locator, pad) {
    const b = await locator.boundingBox();
    if (!b) return null;
    // keep the box inside the viewport: what is scrolled off can't be framed
    const x0 = Math.max(0, b.x - pad), y0 = Math.max(0, b.y - pad);
    const x1 = Math.min(viewport.width, b.x + b.width + pad), y1 = Math.min(viewport.height, b.y + b.height + pad);
    if (x1 <= x0 || y1 <= y0) return null;
    return [x0, y0, x1 - x0, y1 - y0].map((v) => Math.round(v * 10) / 10);
  }

  return {
    /** The subject is this element, from now on. */
    async focus(locator, name, { pad = 8 } = {}) {
      const b = await box(locator, pad);
      events.push([now(), name, b]);
      return b;
    },
    /** Sample the element's box every *every* ms for *ms* ms (text that streams in, a list that grows). */
    async follow(locator, name, { ms = 3000, every = 500, pad = 8 } = {}) {
      const end = Date.now() + ms;
      let last = null;
      while (Date.now() < end) {
        const b = await box(locator, pad);
        if (b && JSON.stringify(b) !== JSON.stringify(last)) { events.push([now(), name, b]); last = b; }
        await page.waitForTimeout(every);
      }
    },
    /** No single subject: show the whole recording. */
    wide(name = 'wide') { events.push([now(), name, null]); },
    /** A named moment without a box (typed, reply arrived, result shown). */
    mark(name) { marks.push([now(), name]); },
    data() { return { viewport: [viewport.width, viewport.height], video: [video.width, video.height], events, marks }; },
    save(path) { fs.writeFileSync(path, JSON.stringify(this.data(), null, 1)); },
  };
}

module.exports = { focusLog };
