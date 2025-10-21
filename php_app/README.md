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

## Použitie

1. Otvorte aplikáciu v prehliadači a nahrajte štyri XLSX súbory (template, helper, pohyby, väzby). Logo je voliteľné.
2. Vyplňte hlavičku reportu (meno, SAP ID, zmluvný účet).
3. Zvoľte farebnú tému a výstupný formát (XLSX alebo PDF).
4. Kliknite na **Generovať report** – prehliadač okamžite stiahne vytvorený súbor.

Generovaný výstup zodpovedá spracovaniu v pôvodnej Python aplikácii vrátane mapovania typov dokladov, dopĺňania čísel faktúr, výpočtu bežiaceho zostatku a vloženia loga.
