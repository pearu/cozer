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
   **https://github.com/pearu/cozer/releases/latest/download/COZER-Setup-Windows.exe**
   *(Soovid valida versiooni? Sirvi https://github.com/pearu/cozer/releases ja
   laadi `.exe` alla jaotisest **Assets**.)*
2. Fail laaditakse sinu **Downloads** (Allalaadimised) kausta. See on suur (mõnisada
   MB), sest sisaldab kõike, mida COZER vajab — sa **ei pea** eraldi paigaldama
   Pythonit, Qt-d ega midagi muud.

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
   Jäta vaikeasukoht, kui sul pole põhjust seda muuta.

---

## 4. Ava COZER

1. Klõpsa Windowsi **Start**-nupul ja kirjuta **COZER**.
2. Klõpsa ilmuval **COZER**i kirjel. (Paigaldaja lisas selle Start-menüüsse.)
3. Esmakäivitus võib võtta paar sekundit. COZERi aken avaneb **General
   Information** (Üldinfo) sakil.

**Logi GitHubi sisse (soovituslik — konto ongi selleks).** Ava COZERis menüü
**Help** → **Sign in to GitHub…** ja järgi lühikest koodiviipa, kasutades 1. sammu
kontot. Kui oled sisse logitud ja COZER peaks kunagi tõrkuma, saab ta ühe klõpsuga
saata veateate — see aitab tõrke kiiresti parandada. Palun hoia COZER sisse logituna.

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

**Hangi uuendus (paigalda uuesti).** *Update available* aknas klõpsa **Update now**. Sinu
veebibrauser laadib alla uusima paigaldusfaili — sama suur fail kui esmasel paigaldusel. Seejärel:
1. **Sulge COZER.**
2. Ava kaust **Downloads** (Allalaadimised) ja tee topeltklõps failil `COZER-Setup-Windows.exe`
   (nagu sammus 3 — klõpsa **More info → Run anyway**, kui Windows hoiatab).
3. Järgi **Next → Install → Finish**. See paigaldab vana versiooni peale.
4. **Käivita COZER** uuesti (samm 4).

Sinu **sündmuste failid jäävad uuendamisel puutumata** — need püsivad seal, kuhu need salvestasid,
programmist eraldi.

*(Kas **Update now** nuppu pole või soovid seda käsitsi teha? Laadi lihtsalt uusim paigaldusfail
alla sama otselingi kaudu nagu sammus 2 ja käivita see.)*

---

## Tõrkeotsing

| Sümptom | Mida teha |
|---|---|
| Sinine aken "Windows protected your PC" | Klõpsa **More info → Run anyway** (vt samm 3). |
| Viirusetõrje blokeerib/eemaldab faili | **Luba / taasta** see ja käivita uuesti. |
| Start-menüüs pole **COZER**i kirjet | Käivita paigaldaja uuesti; või ava paigalduskaust ja tee topeltklõps failil **`cozer-launch.pyw`**. |
| Aken avaneb, aga raport ei õnnestu | Pane **Log** sakil olev teade kirja ja saada see Pearule (või Help → Report a bug kaudu). |
| **Check for updates** ütleb, et ei saa kontrollida | Võib-olla oled võrguühenduseta (vaja on internetti) — proovi hiljem uuesti või laadi uusim paigaldusfail alla sammu 2 lingilt. |

---

*Ingliskeelne [install-windows.md](install-windows.md) on lähtetekst; hoia mõlemad
versioonid sammu võrra sünkroonis.*
