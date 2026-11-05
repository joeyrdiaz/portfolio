# Home services data and automation portfolio

A one page site for Joey Diaz in Austin TX. It offers data and automation work to home services owners who run on Jobber and QuickBooks. The page is static: `index.html` at the repo root, images in `assets/`, no framework, no build step, no trackers, and no third party fonts. System fonts only. The page does not call the network.

The design is light by default and switches to a dark palette when the visitor's system is set to dark mode. Accent color is a warm orange. Motion is subtle: sections fade up as you scroll, cards lift and show a soft spotlight under the pointer, headline figures count up, the tools strip scrolls slowly and pauses on hover, and the hero snapshot drifts with the pointer. All of that turns off when the visitor asks for reduced motion, and the content is fully visible without JavaScript effects.

`index.html` is already rendered and is the file a host should serve. Copy lives in `tools/template.html`. Demo figures are filled from `demo_numbers.json` by `tools/render.py`. Do not type demo figures into `index.html` by hand.

## Preview locally

Open `index.html` in a browser. It works from a file address as well as from a server.

Or, from this folder, run:

```
python3 -m http.server 43123
```

Then open `http://127.0.0.1:43123`. Press Ctrl+C to stop.

Calculator shortcut for a filled example: `index.html?leads=120&ticket=2500&close=35&hours=8#calculator`

Relative links are used throughout, so the same files work at a project site address such as `https://USERNAME.github.io/REPO/` and at a user site root.

## What is in the repo

* `index.html` is the rendered page.
* `404.html` is the missing page, in the same visual style, light and dark.
* `favicon.svg` is the tab icon.
* `assets/og.png` is the share image (1200 by 630). Its source is `tools/og_template.html`. `tools/render.py` fills it into `tools/og.html`; capture that file at 1200 by 630 to refresh the PNG.
* `demo_numbers.json` is the source for every demo figure on the page.
* `robots.txt` and `.nojekyll` are for GitHub Pages.
* `.github/workflows/pages.yml` deploys the repo root with GitHub Actions. It does nothing until this repo is on your own GitHub account.
* `tools/render.py` rebuilds `index.html`.
* `tools/template.html` is the copy source.
* `tools/check_deploy.py` runs the pre publish checks.
* `tools/shoot.mjs` retakes screenshots with Chrome.
* `tests/calc.test.js` checks the quote leak math. Run it with node. No packages.
* `screenshots/` holds full page captures at 390, 768 and 1280 wide, dark mode captures at 390 and 1280, a filled calculator at 390, and `audit.json` with the layout checks.

## Publish on your own GitHub Pages

Nothing here has been deployed. You publish it yourself.

1. Fill every TODO in the checklist below. Preview the page again and read the copy once.
2. Create a new public repository on your own GitHub account. The default branch should be `main`.
3. Push this project so `index.html` sits at the repository root, next to `assets/`.
4. In the repository open Settings, then Pages. Under Build and deployment, set Source to GitHub Actions. Save if GitHub asks you to.
5. Open the Actions tab. The workflow "Deploy site to GitHub Pages" runs on each push to `main`. If it does not start, use Run workflow.
6. When the run is green, the site address appears on that run and again under Settings, then Pages. A project site looks like `https://USERNAME.github.io/REPO/`.
7. Open that address on your phone. Try the calculator, the menu, and the monthly chart.

GitHub documents the Pages setup here:

https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site

### A custom domain later

1. In Settings, then Pages, type the domain into Custom domain.
2. At your DNS host, add the records GitHub shows. A www name usually wants a CNAME. An apex name usually wants A records.
3. Wait until GitHub reports the certificate, then turn on Enforce HTTPS.
4. In `tools/template.html`, replace both `TODO: canonical URL` values with the final https address. Run `python3 tools/render.py` so `index.html` picks up the change. Search `TODO` again before you push.

### How to roll back

Revert the commit on `main` and push. Actions deploys that earlier set of files. You can also open the github pages environment in the repository and roll back a recent deployment from the list there.

## TODO checklist

The email (joeyrdiaz@gmail.com) and the footer name (Joey Diaz) are filled in, and the LinkedIn line was removed. One placeholder is left.

Search `TODO` in `index.html`. Each placeholder below is also in `tools/template.html`. Edit the template, then run `python3 tools/render.py`, so the next render does not put the placeholder back.

1. `TODO: canonical URL` is the canonical link and the `og:url` value. Replace both with the final https address of the live site. Until then, share images use the relative file `assets/og.png`.

## Refresh demo numbers

Every demo figure and every chart on the page comes from `demo_numbers.json`. There are no chart images: all seven charts are drawn in HTML and SVG by `tools/render.py`, so they stay sharp, follow light and dark mode, and animate in as you scroll. The label on each demo block is exactly: Demo on synthetic data. Not a client result.

1. Replace `demo_numbers.json` with a new file that uses the same fields.
2. From this folder run:

```
python3 tools/render.py
node tests/calc.test.js
python3 tools/check_deploy.py
```

The monthly leads and booked revenue chart, leads by source, and quote value by age read the `monthly_leads_and_booked_revenue`, `leads_by_source` and `awaiting_quote_value_by_age` fields. The renderer stops with an error if monthly leads or leads by source do not add up to `total_leads`. You do not edit those numbers in the HTML.

## Calculator

Modeled close rate = min(95%, current close rate times (demo close rate within 15 minutes / demo close rate for your reply time bucket)).
Extra jobs per month = leads per month times (modeled close rate minus current close rate).
Revenue left on the table per month = extra jobs times average quote value. Per year = that times 12.
Buckets: within 15 minutes, 15 to 60 minutes, 1 to 4 hours, 4 to 24 hours, over 24 hours.
A reply already within 15 minutes shows no gap. The modeled rate never goes below the current rate. Bad inputs show a message under the field. There are no alert popups. Reply hours run from 0 to 72.

The visible note on the tool stays: Estimate tool. Your numbers will differ. The reply time curve comes from synthetic demo data, not real shops.

## Before you publish

1. The demo business is called Demo Company on purpose, so it cannot be mistaken for a real shop. Keep it that way if you change the dataset.
2. Test the live site on a real iPhone. Use the menu, the calculator, and point at the monthly chart.
3. Fill every TODO. Search `TODO` in `index.html` and confirm the placeholders are gone.
4. Read every line of copy once.
5. Run `python3 tools/check_deploy.py` and `node tests/calc.test.js`.

Do not present demo charts as client results. Do not add testimonials, logos, or reviews. Do not name any past employer; the About section stays general on purpose. Do not claim a demo chart was produced inside a client BI tool. The page already says client dashboards look like these views of the data.
