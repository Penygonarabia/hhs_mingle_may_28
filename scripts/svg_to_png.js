// Rasterises an SVG to a transparent PNG, using the Chrome that puppeteer-core
// already drives -- this machine has no ImageMagick, rsvg-convert or Inkscape,
// and Chrome renders SVG exactly as the browsers that will display the result.
//
//     node scripts/svg_to_png.js <in.svg> <out.png>
//
// ICON_SIZE is the logical size in CSS pixels (default 140, the size Odoo's
// module icons are authored at) and ICON_SCALE the device pixel ratio (default
// 2), so the default writes a 280x280 file that stays sharp on a retina
// screen. The SVG's own width/height are overridden by ICON_SIZE, so a source
// of any size rasterises to the size asked for.
//
// Its first use was the Database Studio module icon: Odoo's Apps list reads
// static/description/icon.png and falls back to base's grey cube when that
// file is missing, however good the module's icon.svg is. Regenerate with:
//
//     ICON_SIZE=140 node scripts/svg_to_png.js \
//       database_studio/static/description/icon.svg \
//       database_studio/static/description/icon.png
//
// An installed module keeps the icon path recorded when its manifest was last
// scanned, and manifests are cached for the life of the server process, so a
// newly added icon.png needs a restart followed by Update Apps List before it
// replaces the fallback.

const puppeteer = require("puppeteer-core");
const fs = require("fs");

const CHROME = process.env.CHROME_PATH ||
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [svgPath, pngPath] = process.argv.slice(2);
const SIZE = Number(process.env.ICON_SIZE || 140);
const SCALE = Number(process.env.ICON_SCALE || 2);

if (!svgPath || !pngPath) {
    console.error("usage: node scripts/svg_to_png.js <in.svg> <out.png>");
    process.exit(2);
}

(async () => {
    const svg = fs.readFileSync(svgPath, "utf8");
    const browser = await puppeteer.launch({
        executablePath: CHROME,
        headless: "new",
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: SIZE, height: SIZE, deviceScaleFactor: SCALE });
        // The wrapper exists to kill the default body margin and to pin the
        // SVG to the requested size; omitBackground then keeps whatever the
        // artwork leaves uncovered -- rounded corners, say -- transparent.
        await page.setContent(
            `<!doctype html><style>html,body{margin:0;padding:0;background:transparent}
             svg{display:block;width:${SIZE}px;height:${SIZE}px}</style>${svg}`,
            { waitUntil: "networkidle0" }
        );
        await page.screenshot({ path: pngPath, omitBackground: true });
    } finally {
        await browser.close();
    }
    console.log(`wrote ${pngPath} (${SIZE * SCALE}x${SIZE * SCALE})`);
})().catch((e) => { console.error(e); process.exit(1); });
