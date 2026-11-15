# Applier: apply from Telegram

InternRadar sends new internships to your own Telegram chat, each with a code. You reply
`submit J42`, and a Claude Code session on your Mac applies for you and replies when it's done.

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
- **Your Mac must be on** with the session running and Chrome open. Messages you send while it's
  off may not arrive; send them again.
- Telegram for Claude Code ([Channels](https://code.claude.com/docs/en/channels)) is a research
  preview, so its commands may change.

## Commands

| Send | What happens |
|---|---|
| `submit J42` or `submit J42 J45 J51` | Applies and **submits**, no questions asked. You get ✅ with the confirmation and the CV used, or ⚠️ with what it needs from you. |
| `fill J42` | Fills everything but leaves Submit to you in Chrome. |
| `skip J42` | Marks it skipped in your tracker. |
| `status` | Summary of your applications. |

A submitted application can't be taken back, so only send `submit` for jobs you're sure about.
Each job gets at most two applications per company per day; extras wait for the next day.

**When it stops and asks you:** a sign-in or account, a CAPTCHA, a question your profile doesn't
answer, or anything other than a normal application. It never types passwords. Sign in to
Workday, Google, Apple, Amazon and Meta careers in Chrome yourself once, and stay signed in.

## Set up (about 20 minutes, once)

1. **Run the setup script** from the internradar folder:

   ```bash
   applier/setup.sh
   ```

   It installs the AutoInternship skills and their Python packages, and creates
   `~/InternRadar-applier` (pass another folder as the first argument if you like). It tells you if
   Claude Code, [Bun](https://bun.sh) or git is missing.

2. **Add your CV** to `~/InternRadar-applier/resume/`: a Word `.docx`, or your Overleaf project
   (Download → Source, unzipped). It may be longer than a page; each application gets a tailored
   one-page version.

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
| `resume/` | Your master CV |
| `profile.json` | Your standard answers, shared with the AutoInternship extension |
| `tracker.xlsx` | Every application and its status (made by the skill) |
| `Applications/` | One folder per application: the posting, the CV sent, the cover letter, what was entered |
| `jobs.txt` | Jobs held for later (for example the two-per-company limit) |
