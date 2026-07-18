# Installing COZER on Windows

This guide walks you through installing **COZER** on a Windows PC, start to
finish. No programming knowledge is required. It takes about 15 minutes.

You will:
1. Create a free **GitHub** account (used to download COZER and, optionally, to
   send error reports from inside the app).
2. Download the COZER installer.
3. Run the installer.
4. Start COZER.

> **Note.** GitHub's and Windows' screens change from time to time, so a button
> may sit in a slightly different place than described. The *steps* stay the same.
> This guide was written for Windows 10/11. (Last updated: 2026-07-18.)

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

1. Sign in to GitHub (top-right **Sign in**), then open the COZER download page:
   **https://github.com/pearu/cozer/releases**
   *(If Pearu sent you a different download link, use that instead.)*
2. Find the newest entry at the top. Under **Assets**, click the file named
   **`COZER-Setup-<version>.exe`** (for example `COZER-Setup-3.0.0.exe`).
3. The file downloads to your **Downloads** folder. It is large (a few hundred MB)
   because it includes everything COZER needs — you do **not** install Python or
   anything else separately.

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

*(Optional) Enable one-click error reporting:* in COZER, open the **Help** menu →
**Sign in to GitHub…** and follow the short code prompt. Then, if COZER ever hits a
problem, it can send a report with one click using the account from step 1.

---

## 5. Check that it works

- The COZER window opens without errors.
- Open an event file (**File → Open…**) or start a new one, go to the **Reports**
  tab, pick a report, and click **View** — a PDF should open. This confirms the
  report engine (which uses several bundled libraries) is working.

---

## Troubleshooting

| Symptom | What to do |
|---|---|
| "Windows protected your PC" blue box | Click **More info → Run anyway** (see step 3). |
| Antivirus blocks/removes the file | **Allow / restore** it, then run again. |
| No **COZER** entry in Start menu | Re-run the installer; or open the install folder and double-click **`cozer-launch.pyw`**. |
| Window opens but a report fails | Note the message in the **Log** tab and send it to Pearu (or via Help → Report a bug). |

---

*This English guide is the source text; an Estonian translation (`install-windows.et.md`)
will follow.*
