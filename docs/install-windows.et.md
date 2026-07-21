# COZERi paigaldamine Windowsi

*In English / inglise keeles: [install-windows.md](install-windows.md).*

> **Tõlkija märkus (ülevaatuseks).** See on ingliskeelse juhendi tõlke mustand.
> GitHubi liides on ingliskeelne, seega on GitHubi nupunimed jäetud inglise keelde
> (**paksus kirjas**). Windowsi nupunimed sõltuvad süsteemi keelest — allpool on
> eestikeelne variant ja sulgudes ingliskeelne. Palun täpsusta terminid vajadusel.

See juhend aitab paigaldada **COZERi** Windowsi arvutisse, algusest lõpuni.
Programmeerimisoskust pole vaja. Aega kulub umbes 15 minutit.

Sa teed järgmist:
1. Lood tasuta **GitHubi** konto — sellega logid COZERisse sisse, et rakendus
   saaks saata veateateid, mis aitavad probleeme kiiresti lahendada.
2. Laadid alla COZERi paigaldusfaili.
3. Käivitad paigaldusfaili.
4. Avad COZERi ja logid GitHubi sisse.

> **Märkus.** GitHubi ja Windowsi ekraanid muutuvad aeg-ajalt, seega võib mõni
> nupp olla veidi teises kohas, kui siin kirjeldatud. *Sammud* jäävad samaks.
> See juhend on kirjutatud Windows 10/11 jaoks. (Viimati uuendatud: 2026-07-21.)

---

## 1. Loo tasuta GitHubi konto

Kui sul on juba GitHubi konto, jäta see samm vahele — logi lihtsalt sisse.

1. Ava veebibrauser ja mine aadressile **https://github.com/signup**.
2. Sisesta oma **e-posti aadress** ja klõpsa **Continue**.
3. Loo **parool** ja klõpsa **Continue**.
4. Vali **kasutajanimi** (nimi, mida teised näevad; tähed, numbrid ja sidekriipsud)
   ja klõpsa **Continue**.
5. Vasta, kas soovid tooteuudiseid (kumbki sobib), seejärel lahenda väike
   **mõistatus** (puzzle), mis kinnitab, et oled inimene.
6. Klõpsa **Create account**.
7. GitHub saadab sulle e-kirjaga **kinnituskoodi**. Ava e-post, kopeeri kood ja
   sisesta see. Piisab **tasuta** paketist (Free) — maksma ei pea.

Nüüd on sul GitHubi konto olemas. Hoia kasutajanimi ja parool käepärast.

---

## 2. Laadi alla COZERi paigaldusfail

1. Klõpsa sellel **otselingil** — see laadib alati alla uusima COZERi Windowsi
   paigaldusfaili ega vaja GitHubi kontot:
   **https://github.com/pearu/cozer/releases/download/windows-installer/COZER-Setup-Windows.exe**
   *(Soovid valida versiooni? Sirvi https://github.com/pearu/cozer/releases ja
   laadi `.exe` alla jaotisest **Assets**.)*
2. Fail laaditakse sinu **Downloads** (Allalaadimised) kausta. See on suur (mõnisada
   MB), sest sisaldab Pythonit, Qt-d ja WeasyPrinti — neid **ei pea** eraldi paigaldama.
   COZER ise laaditakse alla paigaldamise ajal (vt märkust 3. sammus), just seepärast ei
   vaja COZERi hilisemad uuendused enam uut paigaldusfaili.

> Link laadib alati alla uusima avaldatud väljalaske. Kui allalaadimine ei õnnestu, võib parasjagu
> valmida uus väljalase — oota minut ja proovi uuesti või küsi Pearult.

---

## 3. Käivita paigaldusfail

1. Ava kaust **Downloads** ja tee topeltklõps failil `COZER-Setup-….exe`.
2. Windows võib näidata sinist akent **"Windows protected your PC"** (Windows
   kaitses su arvutit) — see ilmub rakendustele, mis pole suurelt tarnijalt, ja on
   siin ootuspärane. Klõpsa **More info** (Rohkem teavet), seejärel **Run anyway**
   (Käivita ikkagi).
   - Kui Windows küsib *"Do you want to allow this app to make changes?"* (Kas
     lubada sellel rakendusel muudatusi teha?), klõpsa **Yes** (Jah).
   - Kui viirusetõrje faili blokeerib, vali **Allow / Keep** (Luba / Säilita).
3. Järgi paigaldajat: **Next → Install → Finish** (Edasi → Paigalda → Lõpeta).
   Jäta vaikeasukoht, kui sul pole põhjust seda muuta. (COZER paigaldatakse kausta
   nimega `cozer-<kuupäev>` — nt `cozer-2026.07` — nii et uuem paigaldusfail ei lähe
   vanema paigaldusega vastuollu.)

> **Hoia paigaldamise ajal internetiühendus.** Paigaldaja laadib **Install** (Paigalda)
> sammu ajal alla uusima COZERi. Kui pead paigaldama ilma internetita, pane COZERi
> wheel-fail (`cozer-…-py3-none-any.whl`, küsi Pearult) **paigaldusfailiga samasse kausta**
> enne käivitamist — siis kasutab paigaldaja seda. Kui internetti pole ega ka sellist faili,
> teatab paigaldaja, et ei saanud lõpetada — käivita see uuesti, kui oled võrgus.

---

## 4. Ava COZER

1. Klõpsa Windowsi **Start**-nupul ja kirjuta **COZER**.
2. Klõpsa ilmuval **COZER**i kirjel. (Paigaldaja lisas selle Start-menüüsse.)
3. Esmakäivitus võib võtta paar sekundit. COZERi aken avaneb **General
   Information** (Üldinfo) sakil.

**Logi GitHubi sisse (soovituslik — konto ongi selleks).** Klõpsa COZERi akna **paremas
ülanurgas** nupul **Sign in to GitHub…** ja järgi lühikest koodiviipa, kasutades 1. sammu
kontot. Kui oled sisse logitud (nupp näitab siis su nime) ja COZER peaks kunagi tõrkuma,
saab ta ühe klõpsuga saata veateate — see aitab tõrke kiiresti parandada. Palun hoia COZER
sisse logituna.

---

## 5. Kontrolli, et kõik töötab

- COZERi aken avaneb ilma vigadeta.
- Ava sündmuse fail (**File → Open…**) või alusta uut, mine **Reports** sakile,
  vali raport ja klõpsa **View** — peaks avanema PDF. See kinnitab, et raportimootor
  (mis kasutab mitut komplekti kuuluvat teeki) töötab.

---

## 6. Hoia COZER ajakohasena

COZER oskab öelda, kui on saadaval uuem versioon, ja aidata see kätte saada.

**Vaata, milline versioon sul on.** Ava COZERis menüü **Help** → **About cozer…** — versioon
(näiteks `3.0.0rc2`) on näidatud ülal.

**Kontrolli, kas on uuem versioon.** Ava menüü **Help** → **Check for updates…**. COZER küsib
GitHubist ja ütleb kas:
- *"cozer … is up to date"* (cozer … on ajakohane) — sul on juba uusim versioon; või
- *"A newer version is available"* (saadaval on uuem versioon) — koos uue versiooni numbri ja
  lühikese ülevaatega muudatustest (klõpsa **Show Details**, et seda lugeda).

**Hangi uuendus.** *Update available* aknas klõpsa **Update now**. COZER laadib ja paigaldab
uuenduse **sinu eest, taustal** — ilma suure failita ja ilma brauserita — ning palub siis **COZER
taaskäivitada**. Sulge COZER ja ava uuesti — nüüd on sul uus versioon. Sinu **sündmuste failid
jäävad puutumata** — need püsivad seal, kuhu need salvestasid.

**Kui kunagi on vaja täielikku uuestipaigaldust** — näiteks kui COZERi kaasapandud osad muutuvad
või kui **Update now** annab veateate — laadi selle asemel alla uusim paigaldusfail: klõpsa samas
aknas **Open release page** (või kasuta sammu 2 otselinki) ja käivita paigaldusfail nagu esmasel
paigaldusel (sammud 2–3). See paigaldab vana versiooni peale.

---

## Tõrkeotsing

| Sümptom | Mida teha |
|---|---|
| Sinine aken "Windows protected your PC" | Klõpsa **More info → Run anyway** (vt samm 3). |
| Viirusetõrje blokeerib/eemaldab faili | **Luba / taasta** see ja käivita uuesti. |
| Start-menüüs pole **COZER**i kirjet | Käivita paigaldaja uuesti; või ava paigalduskaust ja tee topeltklõps failil **`cozer-launch.pyw`**. |
| Aken avaneb, aga raport ei õnnestu | Pane **Log** sakil olev teade kirja ja saada see Pearule (või **Report a bug…** nupu kaudu paremas ülanurgas). |
| **Check for updates** ütleb, et ei saa kontrollida | Võib-olla oled võrguühenduseta (vaja on internetti) — proovi hiljem uuesti või laadi uusim paigaldusfail alla sammu 2 lingilt. |

---

*Ingliskeelne [install-windows.md](install-windows.md) on lähtetekst; hoia mõlemad
versioonid sammu võrra sünkroonis.*
