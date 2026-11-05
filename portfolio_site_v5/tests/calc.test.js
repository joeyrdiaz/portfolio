// Run: node tests/calc.test.js  (no dependencies). Loads the calculator block straight from index.html.
const fs = require("fs"), path = require("path"), assert = require("assert");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
const src = html.split("/* CALC START */")[1].split("/* CALC END */")[0];
const m = { exports: {} }; new Function("module", src)(m);
const { quoteLeak, bucketFor, DEMO_BUCKETS } = m.exports;
const candidates = [
  path.join(__dirname, "..", "demo_numbers.json"),
  "/workspace/portfolio_generator/demo_outputs/demo_numbers.json",
];
const demoPath = candidates.find((p) => fs.existsSync(p));
if (!demoPath) throw new Error("demo_numbers.json not found");
const demo = JSON.parse(fs.readFileSync(demoPath, "utf8"));
let pass = 0; const t = (name, fn) => { fn(); pass++; console.log("ok", pass, name); };
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) < eps, a + " != " + b);
t("buckets match demo_numbers.json", () => { for (const [b, v] of Object.entries(demo.close_rate_by_response_bucket)) near(DEMO_BUCKETS[b], v.close_rate); });
t("bucket boundaries", () => { assert.strictEqual(bucketFor(0), "<=15m"); assert.strictEqual(bucketFor(0.25), "<=15m"); assert.strictEqual(bucketFor(0.26), "15 to 60m"); assert.strictEqual(bucketFor(4), "1 to 4h"); assert.strictEqual(bucketFor(24), "4 to 24h"); assert.strictEqual(bucketFor(24.1), ">24h"); });
t("demo defaults worked example", () => { const r = quoteLeak(94, 1921, 38.6, 2.9); const mod = 0.386 * 0.5631 / 0.421; near(r.modeled, mod); near(r.extraJobs, 94 * (mod - 0.386)); near(r.monthly, 94 * (mod - 0.386) * 1921); near(r.annual, r.monthly * 12); });
t("within 15 minutes means no gap", () => { const r = quoteLeak(100, 1000, 30, 0.2); assert.ok(r.ok && r.noGap); near(r.monthly, 0); });
t("cap at 95%", () => { const r = quoteLeak(100, 1000, 90, 48); near(r.modeled, 0.95); near(r.extraJobs, 5); near(r.monthly, 5000); });
t("over 24h uses slowest bucket", () => { const r = quoteLeak(50, 500, 20, 30); near(r.modeled, 0.2 * 0.5631 / 0.1905); });
t("empty inputs give inline errors", () => { const r = quoteLeak("", "", "", ""); assert.ok(!r.ok); assert.deepStrictEqual(Object.keys(r.errors).sort(), ["close", "hours", "leads", "ticket"]); });
t("zero and negative rejected", () => { const r = quoteLeak(0, -5, 0, -1); assert.ok(!r.ok && r.errors.leads && r.errors.ticket && r.errors.close && r.errors.hours); });
t("out of range rejected", () => { const r = quoteLeak(10, 10, 96, 73); assert.ok(!r.ok && r.errors.close && r.errors.hours && !r.errors.leads); });
t("non numeric text rejected", () => { assert.ok(!quoteLeak("abc", 1, 1, 1).ok); });
t("string numbers from inputs accepted", () => { near(quoteLeak("94", "1921", "38.6", "2.9").monthly, quoteLeak(94, 1921, 38.6, 2.9).monthly); });
t("reproducible across 1000 runs", () => { const a = JSON.stringify(quoteLeak(94, 1921, 38.6, 2.9)); for (let i = 0; i < 1000; i++) assert.strictEqual(JSON.stringify(quoteLeak(94, 1921, 38.6, 2.9)), a); });
t("exact bucket edges", () => {
  assert.strictEqual(bucketFor(1), "15 to 60m");
  assert.strictEqual(bucketFor(1.01), "1 to 4h");
  assert.strictEqual(bucketFor(4), "1 to 4h");
  assert.strictEqual(bucketFor(4.01), "4 to 24h");
  assert.strictEqual(bucketFor(24), "4 to 24h");
  assert.strictEqual(bucketFor(72), ">24h");
});
t("zero hours is within 15 minutes and shows no gap", () => {
  const r = quoteLeak(12, 400, 40, 0);
  assert.strictEqual(r.bucket, "<=15m");
  assert.ok(r.noGap);
  near(r.modeled, 0.4);
  near(r.monthly, 0);
  near(r.annual, 0);
});
t("top of each input range is accepted", () => {
  const r = quoteLeak(100000, 1000000, 95, 72);
  assert.ok(r.ok);
  near(r.modeled, 0.95);
  assert.ok(r.noGap);
  near(r.monthly, 0);
});
t("just past each cap is rejected", () => {
  assert.ok(quoteLeak(100001, 10, 10, 1).errors.leads);
  assert.ok(quoteLeak(10, 1000001, 10, 1).errors.ticket);
  assert.ok(quoteLeak(10, 10, 95.01, 1).errors.close);
  assert.ok(quoteLeak(10, 10, 10, 72.01).errors.hours);
  assert.ok(!quoteLeak(100000, 1000000, 95, 72).errors);
});
t("null and undefined rejected", () => {
  const r = quoteLeak(null, undefined, null, undefined);
  assert.ok(!r.ok);
  assert.deepStrictEqual(Object.keys(r.errors).sort(), ["close", "hours", "leads", "ticket"]);
});
t("modeled never drops below current and yearly is monthly times 12", () => {
  for (const h of [0, 0.25, 0.26, 1, 2.9, 4, 8, 24, 24.1, 72]) {
    for (const c of [1, 10, 35, 38.6, 50, 90, 95]) {
      const r = quoteLeak(10, 100, c, h);
      assert.ok(r.ok, JSON.stringify(r));
      assert.ok(r.modeled + 1e-12 >= c / 100);
      assert.ok(r.modeled <= 0.95 + 1e-12);
      near(r.extraJobs, 10 * (r.modeled - c / 100));
      near(r.monthly, r.extraJobs * 100);
      near(r.annual, r.monthly * 12);
      if (r.noGap) near(r.monthly, 0);
    }
  }
});
t("fast bucket ratio is 1 so modeled equals current", () => {
  const r = quoteLeak(80, 250, 22, 0.1);
  near(r.ratio, 1);
  near(r.modeled, 0.22);
});
t("whitespace around numbers is accepted", () => {
  near(quoteLeak(" 94 ", " 1921 ", " 38.6 ", " 2.9 ").monthly, quoteLeak(94, 1921, 38.6, 2.9).monthly);
});
console.log(`\n${pass} tests passed`);
