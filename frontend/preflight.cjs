/* Capture representative rendered states for accessibility and design review. */
const { chromium } = require('@playwright/test');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const snapshots = [];
  for (const viewport of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
    const page = await browser.newPage({ viewport });
    await page.goto('http://127.0.0.1:5173/login');
    await page.waitForLoadState('networkidle');
    const tree = await page.locator('body').ariaSnapshot();
    const styles = await page.evaluate(() => ({ font: getComputedStyle(document.body).fontFamily, background: getComputedStyle(document.body).backgroundColor }));
    snapshots.push(JSON.stringify({ viewport, tree, styles, html: await page.content() }, null, 2));
    await page.screenshot({ path: `preflight-${viewport.width}.png`, fullPage: true });
    await page.close();
  }
  fs.writeFileSync('preflight.txt', snapshots.join('\n\n'), 'utf8');
  await browser.close();
})().catch((error) => { console.error(error); process.exitCode = 1; });
