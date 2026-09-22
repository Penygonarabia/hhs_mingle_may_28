// Re-records the Database Studio walkthrough against the local Odoo instance.
//
// The recording is a real screencast, not a slideshow: Chrome is driven through
// the walkthrough while page.screencast() captures it, so the typing, the
// filtering and the panels opening all move the way they do in use.
//
// A session is needed to record anything, and Odoo marks its session_id cookie
// HttpOnly, so it cannot be lifted out of an already-open tab. This asks the
// local instance for one the same way the repo's other capture scripts do
// (scripts/capture_kpi_tiles.js and friends) -- the local dev login, against
// localhost only. Pass DS_SESSION to skip that and supply your own.
//
// It reads Odoo's own reference tables (res_country, res_currency,
// ir_module_module) rather than anything belonging to the customer whose
// instance is recording: the result is a public page. Everything it runs is a
// SELECT -- nothing is written.
//
//     node scripts/record_database_studio_demo.js      # -> demo.webm
//
// The webm is the master. What the pages actually carry is built from it, and
// none of it is in git (see .gitignore) -- rebuild rather than commit:
//
//   for each of 10/1200/256 (Demo.gif), 8/1000/192 (_Optimized), 6/820/128
//   (_Compact), as fps/width/colors:
//     ffmpeg -i demo.webm -vf "fps=F,scale=W:-1:flags=lanczos,\
//       palettegen=max_colors=C:stats_mode=diff" pal.png
//     ffmpeg -i demo.webm -i pal.png -lavfi "fps=F,scale=W:-1:flags=lanczos[x];\
//       [x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
//       -loop 0 out.gif
//
//     ffmpeg -i demo.webm -c:v libx264 -pix_fmt yuv420p -crf 23 \
//       -movflags +faststart Database_Studio_Demo.mp4
//
// Then drop the three GIFs and the mp4 into database_studio/static/description/
// (and Demo.gif + the mp4 into docs/), and replace the single
// `data:image/gif;base64,...` URI in each page that inlines one: _Compact in
// static/description/index.html, _Optimized in
// docs/Database_Studio_Documentation.html. docs/..._WithAGif.html links the
// GIF as a sibling file and needs no re-embedding.

const puppeteer = require("puppeteer-core");
const path = require("path");

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const BASE = process.env.DS_BASE || "http://localhost:8069";
const OUT = process.env.DS_OUT || path.join(process.cwd(), "demo.webm");
// The window is sized so the Analyser's own box fills the frame without a
// wide empty margin under the results once the panels are collapsed.
const WIDTH = Number(process.env.DS_WIDTH || 1440);
const HEIGHT = Number(process.env.DS_HEIGHT || 780);
const DB = process.env.DS_DB || "dbprod";
const LOGIN = process.env.DS_LOGIN || "admin";
const PASSWORD = process.env.DS_PASSWORD || "admin";

// Same call the repo's existing capture scripts make, to the same local host.
function authenticate() {
    const http = require("http");
    const url = new URL(BASE);
    const body = JSON.stringify({
        jsonrpc: "2.0",
        params: { db: DB, login: LOGIN, password: PASSWORD },
    });
    return new Promise((resolve, reject) => {
        const req = http.request({
            hostname: url.hostname,
            port: url.port || 80,
            path: "/web/session/authenticate",
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(body),
            },
        }, (res) => {
            let session = "";
            for (const raw of res.headers["set-cookie"] || []) {
                const m = raw.match(/session_id=([^;]+)/);
                if (m) session = m[1];
            }
            let payload = "";
            res.on("data", (c) => { payload += c; });
            res.on("end", () => {
                const parsed = JSON.parse(payload || "{}");
                if (parsed.error) return reject(new Error(parsed.error.data && parsed.error.data.message || "login failed"));
                if (!session) return reject(new Error("no session_id returned"));
                resolve(session);
            });
        });
        req.on("error", reject);
        req.write(body);
        req.end();
    });
}

// The walkthrough ends up on a public store listing, so it reads Odoo's own
// reference tables rather than anything belonging to the customer whose
// instance is doing the recording. Every row shown here ships with Odoo.
const TABLE = process.env.DS_TABLE || "res_country";
const SCRIPT_SQL = `-- Three statements, one Execute: each reports in its own panel
SELECT id, code, name FROM res_country ORDER BY code LIMIT 8;

SELECT count(*) AS currencies FROM res_currency;

SELECT state, count(*) FROM ir_module_module GROUP BY state ORDER BY 2 DESC;`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
    const session = process.env.DS_SESSION || await authenticate();
    const browser = await puppeteer.launch({
        executablePath: CHROME,
        headless: "new",
        args: ["--no-sandbox", "--disable-setuid-sandbox", `--window-size=${WIDTH},${HEIGHT}`,
               "--hide-scrollbars", "--force-device-scale-factor=1"],
    });
    const page = await browser.newPage();
    await page.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: 1 });
    await page.setCookie({ name: "session_id", value: session, domain: "localhost", path: "/" });

    await page.goto(BASE + "/web", { waitUntil: "networkidle2", timeout: 60000 });
    // The Analyser is a client action; reach it the way a user does, from the
    // Database Studio menu, so the recording opens on the app itself.
    await page.waitForSelector(".sqlms-root, .o_main_navbar", { timeout: 60000 });
    if (!(await page.$(".sqlms-root"))) {
        await page.evaluate(() => {
            const link = [...document.querySelectorAll("a, button, .o_app")]
                .find((e) => (e.textContent || "").trim().startsWith("Database Studio"));
            if (link) link.click();
        });
        await page.waitForSelector(".sqlms-root", { timeout: 60000 });
    }
    await page.waitForSelector(".sqlms-textarea", { timeout: 60000 });
    await sleep(1200);

    // Frame the module, not the instance. Everything identifying the database
    // this is recorded on -- the customer's logo and app menu down the left,
    // the themed top bar with their signed-in user and unread counts -- lives
    // outside the Analyser, so the capture is the Analyser's own box and
    // nothing else. Nothing is hidden or restyled: it is the same screen,
    // framed on the subject. DS_NOCROP=1 records the full window instead.
    let crop;
    if (!process.env.DS_NOCROP) {
        const box = await page.evaluate(() => {
            const r = document.querySelector(".sqlms-root").getBoundingClientRect();
            return {
                x: Math.max(0, Math.round(r.left)),
                y: Math.max(0, Math.round(r.top)),
                w: Math.round(r.width),
                h: Math.round(r.height),
                vw: window.innerWidth,
                vh: window.innerHeight,
            };
        });
        if (box.w > 400 && box.h > 300) {
            // Even dimensions keep the encoders happy.
            crop = {
                x: box.x,
                y: box.y,
                width: Math.min(box.w, box.vw - box.x) & ~1,
                height: Math.min(box.h, box.vh - box.y) & ~1,
            };
            console.log("cropping to", JSON.stringify(crop));
        }
    }
    const recorder = await page.screencast(crop ? { path: OUT, crop } : { path: OUT });
    const step = async (ms = 900) => sleep(ms);

    try {
        await step(1200);

        // 1. Explorer: filter the sidebar down to one table.
        const search = await page.$(".sqlms-sidebar input, .sqlms-root input[placeholder*='Search']");
        if (search) {
            await search.click();
            await page.keyboard.type(TABLE, { delay: 110 });
            await step(1400);
        }

        // 2. Pick that table, so the Fields tab has columns to show rather
        //    than its "click a table" placeholder.
        await page.evaluate((name) => {
            const row = [...document.querySelectorAll(".sqlms-root .sqlms-obj, .sqlms-root li, .sqlms-root .sqlms-item, .sqlms-root label, .sqlms-root span")]
                .find((e) => (e.textContent || "").trim() === name && e.offsetParent);
            if (row) row.click();
        }, TABLE);
        await step(1600);

        // 3. Inspect its columns.
        await page.evaluate(() => {
            const tab = [...document.querySelectorAll(".sqlms-root button, .sqlms-root .nav-link, .sqlms-tab")]
                .find((e) => (e.textContent || "").trim() === "Fields");
            if (tab) tab.click();
        });
        await step(2200);

        // 4. Back to the editor. Picking a table in the sidebar drops a
        //    starter SELECT into it, so Clear puts us on a blank page before
        //    the script is typed.
        await page.evaluate(() => {
            const tab = [...document.querySelectorAll(".sqlms-root button, .sqlms-root .nav-link, .sqlms-tab")]
                .find((e) => (e.textContent || "").trim() === "Query");
            if (tab) tab.click();
        });
        await step(1100);
        await page.evaluate(() => {
            const btn = [...document.querySelectorAll(".sqlms-root button")]
                .find((b) => (b.textContent || "").trim() === "Clear");
            if (btn) btn.click();
        });
        await step(900);

        // 5. Type the script, letting the highlighting keep up. The
        //    autocomplete opens as identifiers are typed -- which is worth
        //    showing -- but Enter with the list open accepts a suggestion
        //    instead of breaking the line, so it is dismissed first.
        const ta = await page.$(".sqlms-textarea");
        await ta.click();
        const lines = SCRIPT_SQL.split("\n");
        for (let i = 0; i < lines.length; i++) {
            await page.keyboard.type(lines[i], { delay: 22 });
            await page.keyboard.press("Escape");
            if (i < lines.length - 1) {
                await page.keyboard.press("Enter");
            }
        }
        await page.keyboard.press("Escape");
        await step(1400);

        // 6. Select the lot and run it.
        await page.evaluate(() => {
            const el = document.querySelector(".sqlms-textarea");
            el.focus();
            el.setSelectionRange(0, el.value.length);
        });
        await step(700);
        await page.evaluate(() => {
            // Nothing floating over the grid when the results arrive.
            const ac = document.querySelector(".sqlms-autocomplete");
            if (ac) ac.remove();
            const btn = [...document.querySelectorAll(".sqlms-root button")]
                .find((b) => (b.textContent || "").trim().startsWith("Execute"));
            if (btn) btn.click();
        });
        await page.waitForSelector(".sqlms-resultset", { timeout: 60000 });
        await step(2600);

        // 7. The panels. Real clicks on the real controls, and the state is
        //    read back after each one so a silently missed click shows up in
        //    the log instead of in the finished GIF.
        const panelState = async (label) => {
            const st = await page.evaluate(() => ({
                bars: document.querySelectorAll(".sqlms-resultbar").length,
                bodies: document.querySelectorAll(".sqlms-resultbody").length,
            }));
            console.log(label, JSON.stringify(st));
            return st;
        };
        await page.evaluate(() => {
            const r = document.querySelector(".sqlms-results");
            if (r) r.scrollTop = 0;
        });
        await step(1200);
        await panelState("after execute:");

        const collapseAll = await page.evaluateHandle(() =>
            [...document.querySelectorAll(".sqlms-resultsbar button")]
                .find((b) => /Collapse all/.test(b.textContent || "")));
        await collapseAll.asElement().click();
        await step(2400);
        await panelState("after collapse all:");

        const bars = await page.$$(".sqlms-resultbar");
        if (bars[0]) {
            await bars[0].click();
            await step(2600);
            await panelState("after expanding panel 1:");
        }
        // A beat of nothing at the end, so the last state is on screen long
        // enough to survive the encode and the GIF's loop point.
        await step(2500);
    } finally {
        await recorder.stop();
        await browser.close();
    }
    console.log("recorded ->", OUT);
}

main().catch((e) => { console.error(e); process.exit(1); });
