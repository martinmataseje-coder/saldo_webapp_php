# Saldo PHP aplikácia

Táto zložka obsahuje objektovú PHP implementáciu generátora saldo reportov pôvodne dostupného v súbore `saldo_core.py`. Aplikácia je samostatná – stačí ju nasadiť na PHP web server (Apache/Nginx + PHP-FPM) a nainštalovať závislosti cez Composer.

## Štruktúra

```
php_app/
├── composer.json           # definícia závislostí (PhpSpreadsheet, Dompdf)
├── public/
│   └── index.php           # jednoduché webové UI na nahratie vstupov a spustenie generátora
├── src/
│   └── SaldoGenerator.php  # preportovaná logika zo súboru saldo_core.py
└── README.md
```

## Inštalácia

1. Na serveri s PHP 8.1+ spustite:
   ```bash
   cd php_app
   composer install
   ```
   Tým sa nainštalujú knižnice [PhpSpreadsheet](https://phpspreadsheet.readthedocs.io) (úprava Excelu) a [Dompdf](https://github.com/dompdf/dompdf) (render PDF).

2. Nasmerujte web server na adresár `php_app/public`. Napr. v prípade PHP built-in servera:
   ```bash
   php -S 0.0.0.0:8080 -t public
   ```

### Gitpod rýchly štart

Ak nemáte PHP lokálne, môžete použiť pripravený Gitpod workspace:

1. Prihláste sa na [gitpod.io](https://gitpod.io), na hlavnej obrazovke kliknite na **New Workspace** a do poľa *Repository URL* vložte adresu tohto repozitára. Tú získate tak, že si v inom okne otvoríte GitHub/GitLab a skopírujete URL z adresného riadka (napr. `https://github.com/vaša-organizácia/saldo_webapp`). Potvrďte tlačidlom **Create**. Prípadne otvorite novú kartu s adresou `https://gitpod.io/#<URL_na_repo>`, kde `<URL_na_repo>` nahradíte skutočnou URL repozitára.
2. Po spustení workspace-u Gitpod načíta konfiguráciu zo súboru [`.gitpod.yml`](../.gitpod.yml), automaticky vykoná `composer install` a rozbehne zabudovaný PHP server na porte `8080`.
3. V pravom hornom rohu Gitpodu sa objaví oznámenie o dostupnom porte – kliknite na **Open Browser** alebo **Open Preview** a zobrazí sa samotná aplikácia pripravená na testovanie.

> 💡 Ak Gitpod vypíše hlášku *"Because there are no projects to choose from, auto-start was disabled"*, jednoducho kliknite na **New Workspace**, doplňte URL repozitára a pokračujte podľa krokov vyššie.

## Použitie

1. Otvorte aplikáciu v prehliadači a nahrajte dva XLSX súbory – **Pohyby** (`src1.xlsx`) a **Väzby** (`src2.xlsx`). Šablóna (`TEMPLATE_saldo.XLSX`) aj pomôcka (`pomocka k saldo (vlookup).XLSX`) sa načítajú automaticky zo zložky `data/`. Logo je voliteľné.
2. Vyplňte hlavičku reportu (meno, SAP ID, zmluvný účet).
3. Zvoľte farebnú tému a výstupný formát (XLSX alebo PDF).
4. Kliknite na **Generovať report** – prehliadač okamžite stiahne vytvorený súbor.

Generovaný výstup zodpovedá spracovaniu v pôvodnej Python aplikácii vrátane mapovania typov dokladov, dopĺňania čísel faktúr, výpočtu bežiaceho zostatku a vloženia loga.
