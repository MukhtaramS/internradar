# InternRadar

Software, AI and quant internships in Europe at the companies that pay best: FAANG, top tech and AI labs, and trading firms. Listings are read straight from each company's careers site several times a day, filtered to real tech and quant roles, and sorted by country and city, including Switzerland and London.

New listings can go to Telegram channels, email, Discord, Slack and Atom/RSS feeds, each with its own filter (for example a Switzerland channel and a Quant channel).

It runs entirely on GitHub: Actions does the scraping, the data lives in the repo, and GitHub Pages hosts the site. No server or database.

## What you get

**Website** (`docs/`, served by GitHub Pages)
- Filters: company type (FAANG, FAANG+, Quant & Trading, Top European Tech), country, city, role, degree, student role type, posted date, company, saved jobs
- One-click presets: 🇨🇭 Switzerland, 🇬🇧 London, Quant & Trading, FAANG, FAANG+, AI/ML, Germany, Netherlands, Ireland, New this week
- Shareable links (filters live in the URL), saved jobs, light and dark theme, works on phones
- Companies page with open listings, how long listings usually stay open, the month most listings appear, and whether each scraper is live
- Alerts page listing every Telegram channel and feed

**Roles kept:** Software, Infrastructure, AI/ML, Data, Quant Research, Quant Trading, Security, Hardware (FPGA, chip design), Mobile, Frontend, QA/Test. Sales, legal, HR, marketing, operations, MBA programmes and similar are dropped.

**Student role types:** internships (including off-cycle and co-op), placements and years in industry, working student (Werkstudent) jobs, and thesis positions.

**Data tagged on every listing:** company type, role, countries and cities, degree named in the title (BS / MS / PhD), season (e.g. "Summer 2027"), posted date, first-seen date.

## Companies

48 companies across three groups, plus 11 European tech companies that are switched off by default. The full list, with how each one is scraped, is in [`config/companies.yaml`](config/companies.yaml).

| Group | Companies |
|---|---|
| FAANG | Google, Meta, Apple, Amazon, Microsoft, Netflix |
| FAANG+ | NVIDIA, OpenAI, Anthropic, Stripe, Databricks, Palantir, Uber, Airbnb, Snowflake, Datadog, Cloudflare, Figma, Coinbase, Bloomberg, Spotify, Waymo, Scale AI, Perplexity, TikTok, Tesla |
| Quant & Trading | Jane Street, Citadel, Citadel Securities, Hudson River Trading, Jump, Optiver, IMC, SIG, Two Sigma, D. E. Shaw, DRW, XTX, G-Research, Tower, Squarepoint, Millennium, Qube RT, Marshall Wace, GSA, Maven, Da Vinci, Flow Traders |
| Top European Tech (off) | Adyen, Monzo, Helsing, N26, DeepL, ElevenLabs, Mistral AI, Wise, Booking.com, Klarna, Revolut |

Not scraped yet (marked `research`, `unknown` or `headless` in the config): Uber, TikTok, Tesla, Citadel, Citadel Securities, Two Sigma, D. E. Shaw, G-Research, Marshall Wace, Maven. These need a custom parser or a headless browser. They appear on the Companies page as "Coming soon".

## How it works

```
GitHub Actions, every hour
  python -m radar.main
    for each company in config/companies.yaml:
      fetch jobs with the adapter for its careers platform   radar/adapters/
      keep student roles in tech or quant                    radar/classify.py
      keep jobs with at least one location in Europe         radar/locations.py
    merge into data/jobs.json                                radar/store.py
      (new jobs added, vanished jobs closed, nothing deleted,
       a company whose scraper failed is left untouched)
    write docs/data/jobs.json and docs/feeds/*.xml           radar/site.py, radar/feeds.py
    send new jobs to every channel in config/notify.yaml     radar/notify/
  commit data/ and docs/
  open a "scraper-health" issue if a company failed
```

The first run stores everything without sending notifications, so channels are not flooded.

## Set it up

1. **Create a GitHub repository** and push this folder to it.
2. **Turn on GitHub Pages:** Settings → Pages → Deploy from a branch → `main`, folder `/docs`.
3. **Site address (optional):** links in notifications and feeds point at your GitHub Pages address automatically. To use a custom domain instead, add a repository variable `SITE_URL` (Settings → Secrets and variables → Actions → Variables).
4. **Run it once:** Actions → Scrape internships → Run workflow. After that it runs on its own.
5. Optionally put the repo link and Telegram channel links in [`docs/site-config.json`](docs/site-config.json) so the site shows them.

### Telegram

1. Message [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.
2. Create a public channel for each feed you want (for example all internships, Switzerland, London, Quant & Trading) and add the bot as an administrator of each one.
3. Add repository secrets: `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ALL`, `TELEGRAM_CHAT_SWITZERLAND`, `TELEGRAM_CHAT_LONDON`, `TELEGRAM_CHAT_QUANT` set to each channel's `@username`.

Channels you don't create are skipped. To add another one (say Germany), add an entry to `config/notify.yaml` with `filter: {countries: [DE]}`, a new secret name, and that secret in `.github/workflows/scrape.yml`.

### Email

Add secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` and `EMAIL_TO` (several addresses separated by commas; they receive it as Bcc). Gmail works with an app password (`smtp.gmail.com`, port 587); Brevo, Mailgun, Resend and Postmark also offer free SMTP. One email is sent per run when there is something new.

Visitors can also get email alerts without you storing anything: the Alerts page explains how to send any feed (for example the Switzerland feed) to their inbox with a free feed-to-email service.

### Discord and Slack

Create an incoming webhook in the channel's settings and add it as `DISCORD_WEBHOOK_URL` or `SLACK_WEBHOOK_URL`.

## Run it locally

Python 3.10 or newer.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python -m radar.main --no-notify
```

Scrape only some companies (useful when fixing one):

```bash
.venv/bin/python -m radar.main Optiver SIG --no-notify
```

Run the tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

View the site:

```bash
python3 -m http.server 8000 --directory docs
```

## Add a company

If it uses Greenhouse, Ashby, Lever, Workday, Eightfold, Phenom or a Jibe site, add an entry to `config/companies.yaml` and you're done:

```yaml
  - name: Example Capital
    category: quant            # faang | faang_plus | quant | europe_tech
    hubs: [London]
    adapter: greenhouse
    token: examplecapital      # from boards.greenhouse.io/examplecapital
    status: verified
```

For a company with its own careers site, write a function in `radar/adapters/custom.py` that returns `Job` objects, and register it under the company name in `radar/adapters/__init__.py`.

## Project layout

```
config/companies.yaml   companies, categories and scraper settings
config/notify.yaml      notification channels and their filters
radar/                  scraper, classifier, store, feeds, notifiers
data/jobs.json          every listing ever seen, with first/last seen and closed dates
data/health.json        result of the last run for each company
docs/                   the website, its data file and the feeds
tests/                  unit tests for locations, classification, store and routing
```
