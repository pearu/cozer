# Installing COZER on Windows

*Eesti keeles / in Estonian: [install-windows.et.md](install-windows.et.md).*

This guide walks you through installing **COZER** on a Windows PC, start to
finish. No programming knowledge is required. It takes about 15 minutes.

You will:
1. Create a free **GitHub** account — you sign in to COZER with it so the app can
   send error reports, which helps get problems fixed quickly.
2. Download the COZER installer.
3. Run the installer.
4. Start COZER and sign in to GitHub.

> **Note.** GitHub's and Windows' screens change from time to time, so a button
> may sit in a slightly different place than described. The *steps* stay the same.
> This guide was written for Windows 10/11. (Last updated: 2026-07-21.)

---

## 1. Create a free GitHub account

Skip this step if you already have a GitHub account — just sign in instead.

1. Open a web browser and go to **https://github.com/signup**.
2. Enter your **email address** and click **Continue**.
3. Create a **password** and click **Continue**.
4. Choose a **username** (the name others see; letters, numbers, and hyphens) and
   click **Continue**.
5. Answer whether you want product updates (either is fine), then solve the little
   **puzzle** that proves you are human.
6. Click **Create account**.
7. GitHub emails you a **launch/verification code**. Open your email, copy the code,
   and type it in. The **Free** plan is all you need — no payment.

You now have a GitHub account. Keep the username and password handy.

---

## 2. Download the COZER installer

1. Click this **direct download** link — it always fetches the newest COZER
   Windows installer, and needs no GitHub account:
   **https://github.com/pearu/cozer/releases/latest/download/COZER-Setup-Windows.exe**
   *(Prefer to pick a version? Browse https://github.com/pearu/cozer/releases and
   download the `.exe` under **Assets**.)*
2. It downloads to your **Downloads** folder. It is large (a few hundred MB)
   because it bundles everything COZER needs — you do **not** install Python, Qt,
   or anything else separately.

> The link always fetches the newest published release. If it doesn't download, a new release
> may be building right then — wait a minute and try again, or ask Pearu.

---

## 3. Run the installer

1. Open your **Downloads** folder and **double-click** the `COZER-Setup-….exe`.
2. Windows may show a blue box: **"Windows protected your PC"** (this appears for
   apps that are not from a big commercial vendor — it is expected here). Click
   **More info**, then **Run anyway**.
   - If Windows asks *"Do you want to allow this app to make changes?"*, click **Yes**.
   - If your antivirus quarantines the file, choose **Allow** / **Keep**.
3. Follow the installer: **Next → Install → Finish**. Accept the default location
   unless you have a reason to change it.

---

## 4. Start COZER

1. Click the Windows **Start** button and type **COZER**.
2. Click the **COZER** entry that appears. (The installer added it to the Start menu.)
3. The first start can take a few seconds. The COZER window opens on the
   **General Information** tab.

**Sign in to GitHub (recommended — this is what the account is for).** In COZER,
open the **Help** menu → **Sign in to GitHub…** and follow the short code prompt,
using the account from step 1. Once signed in, if COZER ever hits a problem it can
send an error report with a single click — which helps get it fixed quickly.
Please keep COZER signed in.

---

## 5. Check that it works

- The COZER window opens without errors.
- Open an event file (**File → Open…**) or start a new one, go to the **Reports**
  tab, pick a report, and click **View** — a PDF should open. This confirms the
  report engine (which uses several bundled libraries) is working.

---

## 6. Keeping COZER up to date

COZER can tell you when a newer version is out and help you get it.

**See which version you have.** In COZER, open the **Help** menu → **About cozer…** — the
version (for example `3.0.0rc2`) is shown at the top.

**Check for a newer version.** Open the **Help** menu → **Check for updates…**. COZER asks
GitHub and tells you either:
- *"cozer … is up to date"* — you already have the newest version; or
- *"A newer version is available"* — with the new version number and a short summary of what
  changed (click **Show Details** to read it).

**Get the update (upgrade).** In the *update available* box, click **Update now**. Your web
browser downloads the newest installer — the same large file as the first install. Then:
1. **Close COZER.**
2. Open your **Downloads** folder and **double-click** `COZER-Setup-Windows.exe` (as in step 3 —
   click **More info → Run anyway** if Windows warns).
3. Follow **Next → Install → Finish**. It installs over the old version.
4. **Start COZER** again (step 4).

Your **event files are not touched** by an update — they stay wherever you saved them, separate
from the program.

*(No **Update now** button, or prefer to do it by hand? Just download the newest installer from
the same direct link as in step 2 and run it.)*

---

## Troubleshooting

| Symptom | What to do |
|---|---|
| "Windows protected your PC" blue box | Click **More info → Run anyway** (see step 3). |
| Antivirus blocks/removes the file | **Allow / restore** it, then run again. |
| No **COZER** entry in Start menu | Re-run the installer; or open the install folder and double-click **`cozer-launch.pyw`**. |
| Window opens but a report fails | Note the message in the **Log** tab and send it to Pearu (or via Help → Report a bug). |
| **Check for updates** says it can't check | You may be offline (it needs the internet) — try again later, or download the newest installer from the step 2 link. |

---

*This English guide is the source text; keep it and the Estonian translation
(`install-windows.et.md`) a step in sync.*
