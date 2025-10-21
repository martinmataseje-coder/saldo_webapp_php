<?php

declare(strict_types=1);

require __DIR__ . '/../vendor/autoload.php';

use Saldo\SaldoGenerator;

$themes = [
    'blue' => 'Modrá (default)',
    'gray' => 'Sivá',
    'warm' => 'Teplá',
];

$outputFormats = [
    'xlsx' => 'Excel (.xlsx)',
    'pdf' => 'PDF',
];

$error = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $requiredFiles = [
            'template' => 'Šablóna (template.xlsx)',
            'helper' => 'Pomôcka (helper.xlsx)',
            'movements' => 'Pohyby (src1.xlsx)',
            'references' => 'Väzby (src2.xlsx)',
        ];

        $fileContents = [];
        foreach ($requiredFiles as $key => $label) {
            if (!isset($_FILES[$key]) || !is_uploaded_file($_FILES[$key]['tmp_name'])) {
                throw new RuntimeException("Chýba súbor: {$label}");
            }
            $fileContents[$key] = file_get_contents($_FILES[$key]['tmp_name']);
            if ($fileContents[$key] === false) {
                throw new RuntimeException("Nepodarilo sa načítať súbor: {$label}");
            }
        }

        $logoBytes = null;
        if (!empty($_FILES['logo']['tmp_name']) && is_uploaded_file($_FILES['logo']['tmp_name'])) {
            $logoBytes = file_get_contents($_FILES['logo']['tmp_name']) ?: null;
        }

        $hdrMeno = trim($_POST['hdr_meno'] ?? '');
        $hdrSap = trim($_POST['hdr_sap'] ?? '');
        $hdrUcet = trim($_POST['hdr_ucet'] ?? '');
        $hdrSpol = trim($_POST['hdr_spol'] ?? 'SWAN a.s.');
        $theme = $_POST['theme'] ?? 'blue';
        $output = $_POST['output'] ?? 'xlsx';

        if ($hdrMeno === '' || $hdrSap === '' || $hdrUcet === '') {
            throw new RuntimeException('Vyplňte prosím polia Meno, SAP ID a Zmluvný účet.');
        }

        if (!array_key_exists($theme, $themes)) {
            $theme = 'blue';
        }
        if (!array_key_exists($output, $outputFormats)) {
            $output = 'xlsx';
        }

        $generator = new SaldoGenerator();
        $binary = $generator->generate(
            $fileContents['template'],
            $fileContents['helper'],
            $fileContents['movements'],
            $fileContents['references'],
            $hdrMeno,
            $hdrSap,
            $hdrUcet,
            $hdrSpol === '' ? 'SWAN a.s.' : $hdrSpol,
            $theme,
            $logoBytes,
            $output
        );

        $filenameBase = 'saldo_report_' . date('Ymd_His');
        if ($output === 'pdf') {
            header('Content-Type: application/pdf');
            header('Content-Disposition: attachment; filename="' . $filenameBase . '.pdf"');
        } else {
            header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            header('Content-Disposition: attachment; filename="' . $filenameBase . '.xlsx"');
        }
        header('Content-Length: ' . strlen($binary));
        echo $binary;
        exit;
    } catch (Throwable $ex) {
        $error = $ex->getMessage();
    }
}

function h(?string $value): string
{
    return htmlspecialchars($value ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

?><!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="utf-8" />
    <title>Saldo – PHP verzia</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px auto; max-width: 900px; line-height: 1.4; }
        h1 { margin-bottom: 0.2em; }
        form { background: #f8fafc; padding: 24px; border-radius: 8px; border: 1px solid #cbd5e1; }
        fieldset { border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 20px; padding: 16px; }
        legend { font-weight: bold; padding: 0 8px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; }
        input[type="text"], select, input[type="file"] { width: 100%; padding: 8px; border: 1px solid #94a3b8; border-radius: 6px; box-sizing: border-box; }
        input[type="file"] { padding: 6px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }
        .actions { text-align: right; }
        button { background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 16px; cursor: pointer; }
        button:hover { background: #1d4ed8; }
        .error { background: #fee2e2; border: 1px solid #fca5a5; color: #b91c1c; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
        .note { font-size: 0.9em; color: #475569; }
    </style>
</head>
<body>
    <h1>Saldo report – PHP verzia</h1>
    <p class="note">Nahrajte excelové podklady a zvoľte formát exportu. Výsledkom bude totožný XLSX alebo PDF report ako v pôvodnej Python aplikácii.</p>

    <?php if ($error !== null): ?>
        <div class="error"><?= h($error) ?></div>
    <?php endif; ?>

    <form method="post" enctype="multipart/form-data">
        <fieldset>
            <legend>Vstupné súbory</legend>
            <label>Šablóna (template.xlsx)
                <input type="file" name="template" accept=".xlsx" required />
            </label>
            <label>Pomôcka (helper.xlsx)
                <input type="file" name="helper" accept=".xlsx" required />
            </label>
            <label>Pohyby (src1.xlsx)
                <input type="file" name="movements" accept=".xlsx" required />
            </label>
            <label>Väzby (src2.xlsx)
                <input type="file" name="references" accept=".xlsx" required />
            </label>
            <label>Logo (voliteľné, PNG/JPG)
                <input type="file" name="logo" accept="image/png,image/jpeg,image/gif" />
            </label>
        </fieldset>

        <fieldset>
            <legend>Hlavička reportu</legend>
            <div class="grid">
                <label>Meno
                    <input type="text" name="hdr_meno" value="<?= h($_POST['hdr_meno'] ?? '') ?>" required />
                </label>
                <label>SAP ID
                    <input type="text" name="hdr_sap" value="<?= h($_POST['hdr_sap'] ?? '') ?>" required />
                </label>
                <label>Zmluvný účet
                    <input type="text" name="hdr_ucet" value="<?= h($_POST['hdr_ucet'] ?? '') ?>" required />
                </label>
                <label>Spoločnosť
                    <input type="text" name="hdr_spol" value="<?= h($_POST['hdr_spol'] ?? 'SWAN a.s.') ?>" />
                </label>
            </div>
        </fieldset>

        <fieldset>
            <legend>Nastavenia výstupu</legend>
            <div class="grid">
                <label>Téma
                    <select name="theme">
                        <?php foreach ($themes as $value => $label): ?>
                            <option value="<?= h($value) ?>" <?= ($value === ($_POST['theme'] ?? 'blue')) ? 'selected' : '' ?>><?= h($label) ?></option>
                        <?php endforeach; ?>
                    </select>
                </label>
                <label>Formát výstupu
                    <select name="output">
                        <?php foreach ($outputFormats as $value => $label): ?>
                            <option value="<?= h($value) ?>" <?= ($value === ($_POST['output'] ?? 'xlsx')) ? 'selected' : '' ?>><?= h($label) ?></option>
                        <?php endforeach; ?>
                    </select>
                </label>
            </div>
        </fieldset>

        <div class="actions">
            <button type="submit">Generovať report</button>
        </div>
    </form>
</body>
</html>
