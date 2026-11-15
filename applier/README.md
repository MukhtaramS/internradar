# Applier: apply from the site or Telegram

Pick internships on the InternRadar site (phone or laptop) and press **Send**, or reply
`submit J42` to a job in your Telegram chat. A Claude Code session on your Mac tailors your CV,
fills the application and submits it, or stops for your review first. You follow every
application's status on the site.

```
InternRadar site (any device)  ──┐                                    your Mac
  My jobs: tick, Send            ├─▶ private GitHub repo  ◀── checks every minute ──  Claude Code + Chrome
  Profile & CV                   │   profile.json, resume/,                            tailors, fills, submits
Telegram: "submit J42"  ─────────┘   applications.json      ◀── statuses, review files ─┘
```

Your profile, CV and applications live in a **private** GitHub repo (`internradar-private`),
which only you can see. The site reads and writes it with a token you create; your Mac's job
folder is a clone of it.

## On the site

- **Profile & CV** (the person icon at the top): connect your private repo once per device, fill
  in your details and upload your CV (Word `.docx` or Overleaf `.zip`; a PDF works but can't be
  tailored). It's saved as `profile.json` in the AutoInternship format, so the skill and the
  AutoInternship extension read it as is. You can import an extension backup too.
- **My jobs**: tick jobs, choose **Submit directly** or **Let me review first**, press **Send**.
  Each row then shows Queued → Working on it → Submitted, Ready for review, or Needs you (with the
  reason). Ready for review opens the tailored CV and every answer entered, with **Submit** and
  **Cancel**.
- Starred jobs and statuses are shared between your devices through the same repo.

**The token:** on GitHub, create a fine-grained token with access to only the private repo and
**Contents: Read and write**. Paste it into Profile on each device. It stays in that browser's
storage and is only sent to GitHub. Pages under the same `<you>.github.io` address share that
storage, so only use it there if all of those sites are yours.

## From Telegram

```
GitHub Actions, hourly (free)            your Telegram                 your Mac
  new jobs  ──────────────────────▶  J42 · Optiver                ──▶  Claude Code + Chrome
                                     Software Engineer Intern           tailors your CV, fills the form,
                                     Reply "submit J42"                 submits, logs it in tracker.xlsx
                                  ◀──────────────────────────────────  ✅ J42 submitted 14:32 (+ CV)
```

- **Finding and sending jobs** runs on GitHub, as before, and costs nothing.
- **Applying** runs in Claude Code on your Mac with your Claude plan (Pro or higher), using the
  [AutoInternship](https://github.com/pqthangv/AutoInternshipClaude) skills and the Claude in
  Chrome extension. A waiting session uses no tokens; each application does.
- **Your Mac must be on** with the session running and Chrome open for the applying itself.
  Requests from the site wait in the queue until it is; Telegram messages sent while it's off
  may not arrive, so send them again.
- Telegram for Claude Code ([Channels](https://code.claude.com/docs/en/channels)) is a research
  preview, so its commands may change.

| Send | What happens |
|---|---|
| `submit J42` or `submit J42 J45 J51` | Applies and **submits**, no questions asked. You get ✅ with the confirmation and the CV used, or ⚠️ with what it needs from you. |
| `fill J42` | Fills everything and stops before Submit; review it on the site (or in Chrome). |
| `skip J42` | Marks it skipped in your tracker. |
| `status` | Summary of your applications. |

A submitted application can't be taken back, so only send `submit` for jobs you're sure about.
At most two applications per company per day; extras wait for the next day.

**When it stops and asks you:** a sign-in or account, a CAPTCHA, a question your profile doesn't
answer, or anything other than a normal application. It never types passwords. Sign in to
Workday, Google, Apple, Amazon and Meta careers in Chrome yourself once, and stay signed in.

## Set up (about 20 minutes, once)

1. **Run the setup script** from the internradar folder:

   ```bash
   applier/setup.sh
   ```

   It installs the AutoInternship skills and their Python packages, creates
   `~/InternRadar-applier`, creates your private repo `internradar-private` (with the GitHub CLI)
   and links the folder to it. It tells you if Claude Code, [Bun](https://bun.sh), git or `gh` is
   missing.

2. **Profile and CV:** on the site open Profile, connect the private repo with your token, fill
   in the form and upload your CV. Your CV may be longer than a page; each application gets a
   tailored one-page version.

3. **Create your bot.** In Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`
   and copy the token. Use a new bot just for this, not the one that posts to public channels.

4. **Connect it to Claude Code.** Run `claude`, then:

   ```
   /plugin install telegram@claude-plugins-official
   /telegram:configure <bot token>
   ```

   Quit Claude Code.

5. **Start the applier:**

   ```bash
   applier/start.sh
   ```

   Send your bot any message. It answers with a pairing code. In the Claude Code window run
   `/telegram:access pair <code>`, then `/telegram:access policy allowlist` so only you can use it.

6. **Let InternRadar message you.** Get your numeric Telegram id from
   [@userinfobot](https://t.me/userinfobot). In the GitHub repo, open Settings → Secrets and
   variables → Actions and add `TELEGRAM_ME_BOT_TOKEN` (the bot token) and `TELEGRAM_CHAT_ME`
   (your id). To get only some jobs, add a filter to the "Telegram, me" entry in
   [`config/notify.yaml`](../config/notify.yaml), for example
   `filter: [{countries: [CH]}, {cities: [London]}]`.

7. **Chrome.** Install [Claude in Chrome](https://code.claude.com/docs/en/chrome) and sign in with
   your Claude account. Install the
   [AutoInternship extension](https://chromewebstore.google.com/detail/autointernship/cdfkbdkmandhnmaejaknimdhepipbpin),
   fill in its profile once, click **Download backup** and save it as
   `~/InternRadar-applier/profile.json`.

8. **Try it** with one job you'd apply to anyway: `fill J..` first, check the result in Chrome,
   then use `submit`.

## Running it unattended

Claude Code asks permission the first time it runs a script, edits a file or uses a site. While
you're away a question like that pauses the session until you answer at the Mac. Two ways to
handle it:

- **Recommended:** do your first one or two applications at the Mac and answer each prompt with
  "Yes, and don't ask again". Those answers are saved for this folder, so later runs don't stop.
  In the Claude in Chrome extension, allow the careers sites you use.
- **Everything allowed:** `applier/start.sh --dangerously-skip-permissions` skips the prompts
  entirely. Claude can then run any command in this session without asking, so only use it if
  you're comfortable with that.

The Telegram allowlist matters here: anyone on it can tell this session what to do. Keep it to
your own account.

## Files in the job-search folder

| File | What it is |
|---|---|
| `CLAUDE.md` | The applier's instructions (from `applier/CLAUDE.md`; edit to change its behaviour) |
| `resume/` | Your master CV, uploaded on the site |
| `profile.json` | Your answers, edited on the site, shared with the AutoInternship extension |
| `applications.json` | What you asked for on the site or in Telegram, and each one's status |
| `myjobs.json` | Your starred jobs, shared between devices |
| `reviews/` | Tailored CV and filled answers of applications waiting for your review |
| `.applier/applications.py` | The queue watcher and status script the session uses |
| `tracker.xlsx` | Every application and its status (made by the skill) |
| `Applications/` | One folder per application: the posting, the CV sent, the cover letter, what was entered |
| `jobs.txt` | Jobs held for later (for example the two-per-company limit) |
