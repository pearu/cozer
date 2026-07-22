# Mis on COZERis uut

*In English / inglise keeles: [whats-new.md](whats-new.md).*

> **Tõlkija märkus (ülevaatuseks).** See on ingliskeelse teksti tõlke mustand. Rakenduse ja
> GitHubi nupunimed on jäetud inglise keelde (**paksus kirjas**), sulgudes eestikeelne selgitus.
> Palun täpsusta sõnastust vajadusel.

See lehekülg selgitab lihtsas keeles, arvutioskust vajamata, mis on COZERis muutunud ja paremaks
läinud. Kõige uuemad märkmed on ülal. Kui tuled vanalt COZERilt, annab lõpus olev **"Vanalt
COZERilt üleminek"** ülevaate suurest pildist.

> **Märkus.** COZER 3 on praegu **väljalaskekandidaat** (release candidate) — seda katsetatakse
> enne lõplikku versiooni. Kui märkad midagi valesti, saada palun veateade (nupp **Report a bug…**
> paremas ülanurgas) — see aitab palju.

---

<!-- Iga uue versiooni ilmumisel lisa siia lühike "## COZER X.Y (kuu aasta)" jaotis,
     uusim üleval, enne "Vanalt COZERilt üleminek" ülevaadet. -->

## COZER 3.0.0rc7 (July 2026)

<!-- release-notes:3.0.0rc7 -->
<!-- TODO(release): eestikeelne tõlge puudub — translate the 3.0.0rc7 section from whats-new.md. Do NOT
     auto-generate; the owner verifies the Estonian. -->

## COZER 3 — kaasaegne COZER (2026)

Esimene kaasaegne versioon. Allolev ülevaade näitab, mis on vana COZERiga võrreldes uut.

---

## Vanalt COZERilt üleminek

Kui korraldasid võistlusi vana COZERiga, siis siin on, mis on teisiti — ja mis on rõõmustavalt
samamoodi.

### Samad reeglid, samad tulemused

- COZER arvestab võistlusi endiselt **U.I.M. ringrajareeglite** järgi ja arvutab tulemused
  **samamoodi** nagu vana programm — numbrid, mille peale sa loodad, on muutumatud.
- Samuti on see viidud kooskõlla **2026. aasta U.I.M. reegliraamatuga**: uuemad tulemuskoodid
  (*Did Not Start* ehk ei startinud, *Did Not Finish* ehk ei lõpetanud, *Disqualified* ehk
  diskvalifitseeritud jne) ja **rahvus ametliku kolmetähelise riigikoodina** (EST, FIN, …).
- Su **vanad võistlusfailid avanevad endiselt** — COZER loeb vanu `.coz`-faile otse.

### Puhtam, kaasaegne aken

- Värske välimus ja lihtne **sakkidega paigutus**: üldinfo, ajavõtu-ekraan, kirjed ja raportid —
  igaüks oma sakil.
- Klasside, osalejate ja sõitude nimekirju on lihtsam lugeda ja muuta.

### Lihtne paigaldada ja ajakohasena hoida

- **Üksainus paigaldusfail** Windowsi jaoks — sa ei pea enam midagi muud käsitsi seadistama; kõik,
  mida COZER vajab, on kaasas. (Vaata [Windowsi paigaldusjuhendit](install-windows.et.md).)
- COZER oskab **ise uuemat versiooni kontrollida** — **Help ▸ Check for updates…** — ja aidata see
  kätte saada. Enam pole vaja uusimat koopiat otsida.

### Paremad raportid

- Eraldi **Nationality** (rahvus) veerg (ametlik riigikood), mis kuvatakse ainult siis, kui see
  võistluse lõikes tegelikult erineb — riigisisene võistlus ei raiska veergu läbivale EST-le. Sama
  kehtib **From** (klubi) veeru kohta.
- **Kvalifikatsiooniraportid** — iga kvalifikatsioonisõidu järel väljapanekuks **Q / DNQ** leht,
  pluss kokkuvõte, kes finaali pääses.
- **Restardi tähistus** sõitude pealkirjades: `1R` restardi ja `1R2` teise restardi korral.
- **Ajasõit on lihtsam.** COZER kasutab automaatselt iga paadi **kiireimat ringiaega** — sa ei pea
  enam teisi ringe käsitsi välja lülitama, et jätta alles ainult parim.
- **Andmed teadetetahvli jaoks.** Iga tulemusleht kannab nüüd *Printed on* (prinditud) templit,
  *Posted at __:__* rida, kuhu kirjutada väljapaneku kellaaeg käsitsi, ja **allkirjaread**
  kohtunike vanemale (OOD / Race Director) ja U.I.M. spordikomissarile — nagu reeglid nõuavad.
- Valikuline säte **"show lap count for all finishers"** (näita kõigi lõpetajate ringide arvu)
  neile raportitele, mis seda vajavad.

### Kui midagi läheb valesti

- Kui COZER satub probleemi, saad **ühe klõpsuga veateate** saata — koos ekraanipildiga — nupu
  **Report a bug…** kaudu paremas ülanurgas. Tasuta **GitHubi** kontoga sisse logides jõuavad need
  teated otse nendeni, kes saavad need parandada.

---

*Ingliskeelne [whats-new.md](whats-new.md) on lähtetekst; hoia mõlemad versioonid sammu võrra
sünkroonis.*
