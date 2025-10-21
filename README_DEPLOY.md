
# Saldo_1 – webový generátor (Streamlit)

## Lokálny beh
```
pip install -r requirements.txt
streamlit run app_streamlit.py
```
Otvor sa URL (napr. http://localhost:8501), nahraj 4 Excely, vyplň polia a klikni "Generovať".

## Ako získať zdrojové súbory
- **Git klonovanie:**
  ```bash
  git clone <URL_na_repo>
  cd saldo_webapp
  ```
  Nahradením `<URL_na_repo>` konkrétnou Git URL si stiahnete celý projekt vrátane priečinka `php_app/`.
- **Stiahnutie ZIP archívu:**
  Ak máte repozitár hostený na GitHub/GitLabe, v rozhraní kliknite na tlačidlo **Code** → **Download ZIP**. Archiv rozbaľte a získate všetky súbory.
- **Kópie zo servera:**
  Na serveri, kde už repozitár beží, môžete použiť `scp` alebo `rsync` a stiahnuť celý adresár `saldo_webapp` na lokálny počítač:
  ```bash
  scp -r user@server:/cesta/k/saldo_webapp .
  ```

## Docker
```
docker build -t saldo-app .
docker run -p 8501:8501 saldo-app
```
Potom otvor http://localhost:8501

## Nasadenie
- **Streamlit Cloud**: nová app, prepoj Git repo, vyber `app_streamlit.py` a pridaj `requirements.txt`.
- **Hugging Face Spaces**: vytvor Space (Streamlit), nahraj tieto súbory, definuj `requirements.txt`.
- **VPS**: spusti Docker príkazy vyššie a daj nad to reverzný proxy (napr. Nginx) na vlastnej doméne.

---

## Samostatná PHP aplikácia

Repozitár obsahuje aj kompletne portovanú PHP verziu v adresári [`php_app/`](php_app/). Ide o samostatnú aplikáciu nezávislú od
Streamlit rozhrania.

### Rýchly štart

```bash
cd php_app
composer install
php -S 0.0.0.0:8080 -t public
```

Potom otvor prehliadač na adrese `http://localhost:8080` a nahraj rovnaké Excel podklady ako v pôvodnej aplikácii.

### Gitpod (bez lokálneho PHP)

Ak máte iba účet na [gitpod.io](https://gitpod.io) a nechcete inštalovať PHP lokálne:

1. Prihláste sa na [gitpod.io](https://gitpod.io) a na úvodnej obrazovke kliknite na **New Workspace**. V inom okne si otvorte svoj Git hosting (GitHub, GitLab…) a skopírujte kompletnú adresu repozitára – je to URL z adresného riadka prehliadača, napr. `https://github.com/vaša-organizácia/saldo_webapp`. Túto adresu vložte do poľa *Repository URL* a potvrďte tlačidlom **Create**. Ak chcete workspace otvoriť ešte rýchlejšie, vložte túto adresu priamo za prefix `https://gitpod.io/#` (napr. `https://gitpod.io/#https://github.com/vaša-organizácia/saldo_webapp`) a otvorte ju v novej karte.
2. Workspace sa spustí, Gitpod načíta konfiguráciu zo súboru [`.gitpod.yml`](.gitpod.yml), automaticky spustí `composer install` v `php_app/` a rozbehne zabudovaný PHP server na porte `8080`.
3. Po inicializácii sa v pravom hornom rohu Gitpodu zobrazí oznámenie o dostupnom porte. Kliknite na **Open Preview** (zabudovaný panel) alebo **Open Browser** (nová karta) a zobrazí sa rozhranie aplikácie.
4. V prehliadači workspace-u otestujte generovanie rovnako ako pri lokálnom behu – nahrajte XLSX súbory, vyplňte údaje a kliknite na **Generovať report**. Súbory sa stiahnu priamo cez Gitpod rozhranie.

> 💡 Ak Gitpod zobrazí hlásenie *"Because there are no projects to choose from, auto-start was disabled"*, kliknite na **New Workspace**, vložte URL repozitára a pokračujte podľa krokov vyššie – ide len o upozornenie, že je potrebné adresu repozitára zadať ručne.

Port je nakonfigurovaný ako verejný, takže môžete zdieľať náhľad aj kolegom v rámci firmy, prípadne nastaviť v Gitpode súkromnú viditeľnosť podľa potreby.

### Štruktúra

- `php_app/src/SaldoGenerator.php` – port logiky zo `saldo_core.py` postavený na PhpSpreadsheet a Dompdf.
- `php_app/public/index.php` – jednoduché HTML UI (bez závislosti na frameworku) pre nahratie súborov a spustenie generovania.
- `php_app/README.md` – podrobný opis inštalácie, štruktúry a používania PHP verzie.
