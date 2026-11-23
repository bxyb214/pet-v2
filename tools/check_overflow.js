// 逐路由横向溢出检查（打桩 API，免真实账号；Playwright）
// 用法：先 `npx vite --port 5178`（frontend 目录），再 `node tools/check_overflow.js http://localhost:5178`
// 也可带路由参数：node tools/check_overflow.js <BASE> /english/grammar,/english/reading/plan
const { chromium } = require("playwright");

const BASE = process.argv[2] || "http://localhost:5178";
const onlyArg = process.argv[3];

// 路由守卫会解析 JWT 的 exp：假 token 也必须是三段式 JWT 形状，否则被判过期回登录页
const FAKE_JWT = ["e30", Buffer.from(JSON.stringify({ exp: 4102444800 })).toString("base64url"), "x"].join(".");

const USER = {
  user_id: 1, username: "admin", display_name: "admin",
  perms: "speak", is_admin: true, exam: "pet",
  access_token: FAKE_JWT, refresh_token: "r", id: 1,
};
const EMPTY_SYNC = {
  mastery: [], mistakes: [], progress: [],
  plan: { length: 0, days_done: [], reading_length: 0, reading_days_done: [], reading_books: [] },
  custom_words: [], custom_sentences: [],
};

const ROUTES = onlyArg
  ? onlyArg.split(",").map((s) => s.trim()).filter(Boolean)
  : [
      "/english/words/browse", "/english/words/study", "/english/words/plan", "/english/words/mistakes",
      "/english/reading/home", "/english/reading/plan", "/english/reading/add", "/english/reading/mistakes",
      "/english/reading/study/1/1", "/english/reading/quiz/1",
      "/english/grammar", "/english/grammar/1",
      "/english/listening/home", "/english/listening/review", "/english/listening/1/1",
      "/english/speak", "/english/speak/shadow", "/english/speak/talk", "/english/speak/review", "/english/speak/make",
      "/math", "/math/books/yongle-g3", "/math/books/yongle-g3/g3-40", "/math/progress",
      "/settings", "/admin",
    ];
// 路由表与 router/index.ts 同步维护；404 的路由跳过即可（Playwright 会等待 networkidle 失败也不影响溢出判断）

const VPS = [["d", 1440, 900], ["t", 820, 1180], ["m", 390, 844]];

(async () => {
  const browser = await chromium.launch();
  let fail = 0;
  for (const [tag, w, h] of VPS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    await ctx.route("**/api/v1/**", async (r) => {
      const u = r.request().url();
      const j = (o) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(o) });
      if (u.includes("/auth/login") || u.includes("/auth/me")) return j(USER);
      if (u.includes("/sync/pull")) return j({ rev: 1, data: EMPTY_SYNC });
      if (u.includes("/words/custom")) return j([]);
      if (u.includes("/auth/setup")) return j({ initialized: true, allow_claim: false, has_invite: false });
      if (u.includes("/admin/users")) return j([{ id: 1, username: "admin", display_name: "admin", is_admin: true, perms: "speak" }]);
      if (u.includes("/admin/codes")) return j([]);
      if (u.includes("/admin/usage")) return j({ total_cost_milli: 0, users: [] });
      if (u.includes("/admin/cfg")) return j({});
      return j({});
    });
    const page = await ctx.newPage();
    await page.goto(BASE + "/login", { waitUntil: "networkidle" });
    await page.fill('input[placeholder="用户名"]', "admin");
    await page.fill('input[placeholder="密码"]', "mock");
    await page.click('button:has-text("登录")');
    await page.waitForTimeout(1200);

    const bad = [];
    for (const route of ROUTES) {
      await page.goto(BASE + route, { waitUntil: "networkidle" }).catch(() => {});
      await page.waitForTimeout(600);
      const m = await page.evaluate(() => {
        const de = document.documentElement;
        const over = [];
        document.querySelectorAll("main, .page, .card, .stack, table").forEach((el) => {
          const b = el.getBoundingClientRect();
          if (b.right > de.clientWidth + 2) over.push(el.className + ":" + Math.round(b.right));
        });
        return { sw: de.scrollWidth, cw: de.clientWidth, over: over.slice(0, 3) };
      });
      if (m.sw > m.cw + 2) {
        fail += 1;
        bad.push(`${route} 溢出 ${m.sw}>${m.cw} ${JSON.stringify(m.over)}`);
      }
    }
    console.log(`\n=== ${tag} ${w}x${h} ===`);
    console.log(bad.length ? bad.join("\n") : "无横向溢出 ✅");
    await ctx.close();
  }
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
