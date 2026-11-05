"""Fill tools/template.html from demo_numbers.json and write index.html.

Run from the repo root or from anywhere:

    python3 tools/render.py

Every demo figure on the page is computed here. Do not type those numbers
into index.html by hand. Edit the copy in tools/template.html, then re run
this script.
"""
import json
import os
from datetime import date
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get("DEMO_NUMBERS", os.path.join(ROOT, "demo_numbers.json"))
LABEL = "Demo on synthetic data. Not a client result."

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

BUCKET_ORDER = ["<=15m", "15 to 60m", "1 to 4h", "4 to 24h", ">24h"]
BUCKET_AXIS = {
    "<=15m": "Within 15 min",
    "15 to 60m": "15 to 60 min",
    "1 to 4h": "1 to 4 hours",
    "4 to 24h": "4 to 24 hours",
    ">24h": "Over 24 hours",
}
BUCKET_SENTENCE = {
    "<=15m": "a first reply within 15 minutes",
    "15 to 60m": "a first reply from 15 to 60 minutes",
    "1 to 4h": "a first reply from 1 to 4 hours",
    "4 to 24h": "a first reply from 4 to 24 hours",
    ">24h": "a first reply after 24 hours",
}


def pct(v):
    return f"{v * 100:.1f}%"


def money(v):
    return f"${v:,.0f}"


def k_money(v):
    return f"${v / 1000:,.0f}k"


def month_label(value):
    return f"{MONTHS[value.month - 1]} {value.year}"


def bar(width_pct, kind):
    kind_class = f" {kind}" if kind else ""
    return (
        '<div class="bar-clip" aria-hidden="true">'
        '<svg class="bar-svg" viewBox="0 0 100 8" preserveAspectRatio="none" focusable="false">'
        f'<rect class="fill{kind_class}" x="0" y="0" width="{width_pct:.4f}" height="8"></rect>'
        "</svg></div>"
    )


def demo_note():
    return f'<p class="tag-demo">{escape(LABEL)}</p>'


def chart_close(data):
    buckets = data["close_rate_by_response_bucket"]
    missing = [b for b in BUCKET_ORDER if b not in buckets]
    if missing:
        raise SystemExit("demo_numbers.json is missing reply buckets: " + ", ".join(missing))
    rates = {b: buckets[b]["close_rate"] for b in BUCKET_ORDER}
    fast_b = max(rates, key=rates.get)
    slow_b = min(rates, key=rates.get)
    slow_sentence = BUCKET_SENTENCE[slow_b][0].upper() + BUCKET_SENTENCE[slow_b][1:]
    insight = (
        f"In the demo, {BUCKET_SENTENCE[fast_b]} closed at {pct(rates[fast_b])}. "
        f"{slow_sentence} closed at {pct(rates[slow_b])}."
    )
    rows = []
    last = len(BUCKET_ORDER) - 1
    for i, key in enumerate(BUCKET_ORDER):
        rate = rates[key]
        kind = "good" if i == 0 else "bad" if i == last else ""
        count = buckets[key]["n"]
        val_class = " pos" if kind == "good" else " neg" if kind == "bad" else ""
        rows.append(
            '<div class="bar-row">'
            '<div class="bar-top">'
            f'<div class="bar-name">{escape(BUCKET_AXIS[key])}'
            f'<span class="bar-n">{count:,} quotes</span></div>'
            f'<div class="bar-val{val_class}">{pct(rate)}</div>'
            "</div>"
            f"{bar(rate * 100, kind)}"
            "</div>"
        )
    return (
        '<figure class="chart">'
        "<figcaption>Close rate by time to first reply</figcaption>"
        f'{"".join(rows)}'
        f'<p class="insight">{escape(insight)}</p>'
        '<p class="chart-note">Close rate means converted quotes divided by sent quotes. Draft quotes are excluded.</p>'
        f"{demo_note()}"
        "</figure>"
    )


def chart_jobs(data):
    margins = data["margin_by_job_type"]
    tickets = data["avg_ticket_by_job_type"]
    counts = data["jobs_by_job_type"]
    names = list(margins)
    hi = max(names, key=lambda name: margins[name])
    lo = min(names, key=lambda name: margins[name])
    top_ticket = max(names, key=lambda name: tickets[name])
    insight = (
        f"{hi} carries the highest margin at {pct(margins[hi])}, and {lo.lower()} the lowest at {pct(margins[lo])}. "
        f"{top_ticket} has the largest average ticket at {money(tickets[top_ticket])}."
    )
    ordered = sorted(names, key=lambda name: margins[name], reverse=True)
    rows = [
        '<div class="jt jt-head"><span>Job type</span><span>Margin</span><span>Avg ticket</span></div>'
    ]
    for name in ordered:
        kind = "good" if name == hi else "bad" if name == lo else ""
        val_class = " pos" if kind == "good" else " neg" if kind == "bad" else ""
        rows.append(
            '<div class="jt">'
            f'<div class="jt-name">{escape(name)} <span class="jt-n">{counts[name]:,} jobs</span></div>'
            '<div class="jt-margin">'
            f'{bar(margins[name] * 100, kind)}'
            f'<span class="jt-pct{val_class}">{pct(margins[name])}</span>'
            "</div>"
            f'<div class="jt-ticket"><span class="jt-k">Avg ticket</span> {money(tickets[name])}</div>'
            "</div>"
        )
    return (
        '<figure class="chart">'
        "<figcaption>Margin and average ticket by job type</figcaption>"
        f'{"".join(rows)}'
        f'<p class="insight">{escape(insight)}</p>'
        '<p class="chart-note">Margin is the job total minus labor and materials, divided by the job total.</p>'
        f"{demo_note()}"
        "</figure>"
    )


def hero_window(data):
    buckets = data["close_rate_by_response_bucket"]
    rows = []
    last = len(BUCKET_ORDER) - 1
    for i, key in enumerate(BUCKET_ORDER):
        rate = buckets[key]["close_rate"]
        kind = "good" if i == 0 else "bad" if i == last else ""
        val_class = " pos" if kind == "good" else " neg" if kind == "bad" else ""
        rows.append(
            '<div class="mini-row">'
            f'<span class="mini-name">{escape(BUCKET_AXIS[key])}</span>'
            f"{bar(rate * 100, kind)}"
            f'<span class="mini-val{val_class}">{pct(rate)}</span>'
            "</div>"
        )
    kpis = [
        ("Overall close rate", pct(data["close_rate"]), ""),
        ("Median first reply", f'{data["median_response_minutes"] / 60:.1f} hours', ""),
        ("Quotes waiting over 14 days", k_money(data["unconverted_quote_value_over_14_days"]), " neg"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><span class="kpi-k">{escape(k)}</span><span class="kpi-v{cls}">{escape(v)}</span></div>'
        for k, v, cls in kpis
    )
    return (
        '<div class="window-body">'
        f'<div class="kpis">{kpi_html}</div>'
        '<p class="mini-title">Close rate by time to first reply</p>'
        f'<div class="mini">{"".join(rows)}</div>'
        f"{demo_note()}"
        "</div>"
    )


def chart_open(data):
    stale_n = f'{data["unconverted_quotes_over_14_days"]:,}'
    stale_k = k_money(data["unconverted_quote_value_over_14_days"])
    await_pct = pct(data["quotes_awaiting_response_share"])
    unpaid_pct = pct(data["invoices_not_paid_share"])
    insight = (
        f"{await_pct} of demo quotes were still awaiting a response, and {unpaid_pct} of invoices "
        f"were not yet paid. The {stale_n} quotes older than 14 days hold {stale_k}."
    )
    rows = [
        ("Quotes awaiting a response", data["quotes_awaiting_response_share"], "bad"),
        ("Invoices not yet paid", data["invoices_not_paid_share"], ""),
    ]
    bars = []
    for label, share, kind in rows:
        val_class = " neg" if kind == "bad" else ""
        bars.append(
            '<div class="bar-row">'
            '<div class="bar-top">'
            f'<div class="bar-name">{escape(label)}</div>'
            f'<div class="bar-val{val_class}">{pct(share)}</div>'
            "</div>"
            f"{bar(share * 100, kind)}"
            "</div>"
        )
    return (
        '<figure class="chart stacked">'
        "<figcaption>Quotes and invoices still open</figcaption>"
        f'{"".join(bars)}'
        f'<p class="insight">{escape(insight)}</p>'
        f"{demo_note()}"
        "</figure>"
    )


def sr_table(caption, head, rows):
    head_html = "".join(f"<th scope=\"col\">{escape(h)}</th>" for h in head)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    return (
        f'<table class="sr-only"><caption>{escape(caption)}</caption>'
        f"<thead><tr>{head_html}</tr></thead><tbody>{body}</tbody></table>"
    )


def tip_side(i, n):
    if i < 3:
        return " tl"
    if i >= n - 3:
        return " tr"
    return ""


def chart_monthly(data):
    rows = data["monthly_leads_and_booked_revenue"]
    if sum(r["leads"] for r in rows) != data["total_leads"]:
        raise SystemExit("monthly leads do not add up to total_leads")
    n = len(rows)
    labels = [month_label(date.fromisoformat(r["month"] + "-01")) for r in rows]
    short = [f"{MONTHS[int(r['month'][5:]) - 1]} {r['month'][2:4]}" for r in rows]
    lead_top = 160
    rev_top = 150000
    if max(r["leads"] for r in rows) > lead_top or max(r["booked_revenue"] for r in rows) > rev_top:
        raise SystemExit("monthly chart scale is too small for the data")
    busiest = max(range(n), key=lambda i: rows[i]["leads"])
    best = max(range(n), key=lambda i: rows[i]["booked_revenue"])
    total_rev = sum(r["booked_revenue"] for r in rows)
    cols = []
    dots = []
    points = []
    for i, r in enumerate(rows):
        h = r["leads"] / lead_top * 100
        y = r["booked_revenue"] / rev_top * 100
        x = (i + 0.5) / n * 100
        points.append(f"{(i + 0.5) * 10:.2f},{100 - y:.3f}")
        cols.append(
            f'<div class="mcol{tip_side(i, n)}" style="--h:{h:.3f}%;--y:{y:.3f}%;--i:{i}">'
            "<i></i>"
            f'<span class="mtip"><b>{escape(labels[i])}</b>'
            f'<span>{r["leads"]} leads</span><span>{k_money(r["booked_revenue"])} booked</span></span>'
            "</div>"
        )
        dots.append(f'<span style="left:{x:.3f}%;bottom:{y:.3f}%;--i:{i}"></span>')
    ticks = []
    for i in sorted({0, 6, 12, 18, n - 1}):
        side = "first" if i == 0 else "last" if i == n - 1 else "mid" if i == 12 else "minor"
        ticks.append(f'<span class="{side}" style="left:{(i + 0.5) / n * 100:.3f}%">{escape(short[i])}</span>')
    kpis = [
        ("Busiest month", labels[busiest], f'{rows[busiest]["leads"]} leads'),
        ("Best revenue month", labels[best], f'{k_money(rows[best]["booked_revenue"])} booked'),
        ("Booked over 24 months", f"${total_rev / 1e6:.2f}M" if total_rev >= 1e6 else k_money(total_rev), f'{data["total_leads"]:,} leads'),
    ]
    kpi_html = "".join(
        f'<div><span class="mk-k">{escape(k)}</span><b>{escape(v)}</b><span class="mk-s">{escape(s)}</span></div>'
        for k, v, s in kpis
    )
    insight = (
        f"In this demo export, leads peaked in {labels[busiest]} but booked revenue peaked in {labels[best]}. "
        "Revenue swings sharply from month to month and does not simply follow the lead count."
    )
    table = sr_table(
        "Monthly leads and booked revenue",
        ["Month", "Leads", "Booked revenue"],
        [[labels[i], str(r["leads"]), k_money(r["booked_revenue"])] for i, r in enumerate(rows)],
    )
    return (
        '<figure class="chart viz">'
        '<div class="viz-head"><figcaption>Monthly leads and booked revenue</figcaption>'
        '<div class="legend" aria-hidden="true"><span class="lg-bar">Leads</span><span class="lg-line">Booked revenue</span></div></div>'
        f'<div class="mkpis">{kpi_html}</div>'
        '<div class="mplot" aria-hidden="true">'
        '<div class="mgrid"><span style="bottom:100%"><em>160 leads</em><em>$150k</em></span>'
        '<span style="bottom:50%"><em>80</em><em>$75k</em></span><span style="bottom:0"></span></div>'
        f'<div class="mcols">{"".join(cols)}</div>'
        '<svg class="mline" viewBox="0 0 240 100" preserveAspectRatio="none" focusable="false">'
        f'<polyline points="{" ".join(points)}" vector-effect="non-scaling-stroke"></polyline></svg>'
        f'<div class="mdots">{"".join(dots)}</div>'
        "</div>"
        f'<div class="mx" aria-hidden="true">{"".join(ticks)}</div>'
        f"{table}"
        f'<p class="insight">{escape(insight)}</p>'
        f'<p class="chart-note">{escape(data["monthly_definition"])} Point at a month to see its numbers.</p>'
        f"{demo_note()}"
        "</figure>"
    )


def chart_age(data):
    rows = data["awaiting_quote_value_by_age"]
    top = max(r["value"] for r in rows)
    n = len(rows)
    cols = []
    for i, r in enumerate(rows):
        old = i >= 2
        h = r["value"] / top * 100
        cols.append(
            f'<div class="acol{" old" if old else ""}" style="--h:{h:.3f}%;--i:{i}">'
            f'<span class="av">{k_money(r["value"])}</span><i></i></div>'
        )
    labels = "".join(f'<span>{escape(r["age"].replace(" days", ""))}</span>' for r in rows)
    oldest = rows[-1]
    stale_k = k_money(data["unconverted_quote_value_over_14_days"])
    insight = (
        f"In this demo export, quotes {oldest['age'].lower()} old hold {k_money(oldest['value'])} on their own. "
        f"Everything past 14 days adds up to {stale_k} still waiting on a reply."
    )
    table = sr_table(
        "Quote value still awaiting a response, by days since the quote was sent",
        ["Age", "Quote value"],
        [[r["age"], k_money(r["value"])] for r in rows],
    )
    return (
        '<figure class="chart viz">'
        '<div class="viz-head"><figcaption>Quote value still awaiting a response</figcaption>'
        '<div class="legend" aria-hidden="true"><span class="lg-old">Older than 14 days</span><span class="lg-new">14 days or less</span></div></div>'
        f'<div class="aplot" aria-hidden="true" style="--n:{n}">'
        f'<div class="abracket"><span>{stale_k} older than 14 days</span></div>'
        f'{"".join(cols)}'
        "</div>"
        f'<div class="ax" aria-hidden="true" style="--n:{n}">{labels}</div>'
        '<p class="ax-cap" aria-hidden="true">Days since the quote was sent</p>'
        f"{table}"
        f'<p class="insight">{escape(insight)}</p>'
        f"{demo_note()}"
        "</figure>"
    )


def chart_sources(data):
    src = data["leads_by_source"]
    total = sum(src.values())
    if total != data["total_leads"]:
        raise SystemExit("leads by source do not add up to total_leads")
    ordered = sorted(src, key=src.get, reverse=True)
    top = src[ordered[0]]
    rows = []
    for rank, name in enumerate(ordered, 1):
        kind = "accent" if rank == 1 else ""
        rows.append(
            '<div class="src-row">'
            f'<span class="src-rank" aria-hidden="true">{rank:02d}</span>'
            f'<span class="src-name">{escape(name)}</span>'
            f'<span class="src-val">{src[name]:,}<em>{src[name] / total * 100:.0f}%</em></span>'
            f'<div class="src-bar">{bar(src[name] / top * 100, kind)}</div>'
            "</div>"
        )
    two = src[ordered[0]] + src[ordered[1]]
    insight = (
        f"In this demo export, {ordered[0]} and {ordered[1]} bring in {two / total * 100:.0f}% of all leads. "
        f"{ordered[-1]} is the smallest source at {src[ordered[-1]]:,}."
    )
    return (
        '<figure class="chart viz">'
        '<div class="viz-head"><figcaption>Leads by source, 24 months</figcaption>'
        f'<p class="src-total"><b>{total:,}</b> leads</p></div>'
        f'<div class="src">{"".join(rows)}</div>'
        f'<p class="insight">{escape(insight)}</p>'
        '<p class="chart-note">Share is each source divided by all demo leads.</p>'
        f"{demo_note()}"
        "</figure>"
    )


def main():
    with open(SRC, encoding="utf-8") as handle:
        data = json.load(handle)
    start = date.fromisoformat(data["period_start"])
    end = date.fromisoformat(data["as_of"])
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    if months <= 0:
        raise SystemExit("demo period is empty")
    jobs = data["jobs_by_job_type"]
    tickets = data["avg_ticket_by_job_type"]
    margins = data["margin_by_job_type"]
    if set(jobs) != set(tickets) or set(jobs) != set(margins):
        raise SystemExit("job type keys do not match across ticket, margin, and counts")
    avg_ticket = sum(tickets[name] * jobs[name] for name in jobs) / sum(jobs.values())
    low_name = min(margins, key=margins.get)
    high_name = max(margins, key=margins.get)
    buckets = {name: row["close_rate"] for name, row in data["close_rate_by_response_bucket"].items()}
    tokens = {
        "company": escape(data["company"]),
        "cr15": pct(data["close_rate_under_15m"]),
        "cr24": pct(data["close_rate_over_24h"]),
        "cr_all": pct(data["close_rate"]),
        "cr15_w": f'{data["close_rate_under_15m"] * 100:.4f}',
        "cr24_w": f'{data["close_rate_over_24h"] * 100:.4f}',
        "cr_all_w": f'{data["close_rate"] * 100:.4f}',
        "stale_value": k_money(data["unconverted_quote_value_over_14_days"]),
        "stale_n": f'{data["unconverted_quotes_over_14_days"]:,}',
        "n_leads": f'{data["total_leads"]:,}',
        "period": f"{month_label(start)} to {month_label(end)}",
        "median_resp": f'{data["median_response_minutes"] / 60:.1f} hours',
        "margin_low": pct(margins[low_name]),
        "margin_low_type": escape(low_name.lower()),
        "margin_high": pct(margins[high_name]),
        "margin_high_type": escape(high_name.lower()),
        "ticket_repl": money(tickets["Replacement"]),
        "def_leads": str(round(data["total_leads"] / months)),
        "def_ticket": str(round(avg_ticket)),
        "def_close": f'{data["close_rate"] * 100:.1f}',
        "def_hours": f'{data["median_response_minutes"] / 60:.1f}',
        "seed": str(data["seed"]),
        "buckets_js": json.dumps(buckets),
        "chart_close": chart_close(data),
        "chart_jobs": chart_jobs(data),
        "chart_open": chart_open(data),
        "chart_monthly": chart_monthly(data),
        "chart_age": chart_age(data),
        "chart_sources": chart_sources(data),
        "hero_window": hero_window(data),
        "label": escape(LABEL),
    }
    template_path = os.path.join(HERE, "template.html")
    html = open(template_path, encoding="utf-8").read()
    for key in sorted(tokens, key=len, reverse=True):
        html = html.replace("{{" + key + "}}", tokens[key])
    if "{{" in html:
        raise SystemExit("unfilled token remains in index.html")
    lowered = html.lower()
    for name in ("kai" + "ros", "meridian" + "link", "lone " + "star"):
        if name in lowered:
            raise SystemExit("forbidden name in rendered html")
    for bad in ("\u2014", "\u2013"):
        if bad in html:
            raise SystemExit("dash punctuation found in rendered html")
    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(html)
    og = open(os.path.join(HERE, "og_template.html"), encoding="utf-8").read()
    for key in sorted(tokens, key=len, reverse=True):
        og = og.replace("{{" + key + "}}", tokens[key])
    if "{{" in og:
        raise SystemExit("unfilled token remains in og.html")
    with open(os.path.join(HERE, "og.html"), "w", encoding="utf-8") as handle:
        handle.write(og)
    print(json.dumps({
        "wrote": out,
        "source": SRC,
        "defaults": {
            "leads": tokens["def_leads"],
            "ticket": tokens["def_ticket"],
            "close": tokens["def_close"],
            "hours": tokens["def_hours"],
        },
        "close_15m": tokens["cr15"],
        "close_24h": tokens["cr24"],
        "stale": tokens["stale_value"],
        "margin": f'{tokens["margin_low"]} {tokens["margin_low_type"]} to {tokens["margin_high"]} {tokens["margin_high_type"]}',
    }, indent=2))


if __name__ == "__main__":
    main()
