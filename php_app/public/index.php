<?php
declare(strict_types=1);

use Saldo\SaldoGenerator;

error_reporting(E_ALL);
ini_set('display_errors', '1');

require __DIR__ . '/../vendor/autoload.php';

$dataDir   = realpath(__DIR__ . '/../../data') ?: (__DIR__ . '/../../data');
$template  = $dataDir . '/template_saldo.xlsx';
$helper    = $dataDir . '/pomocka_saldo.xlsx';
$logoPath  = $dataDir . '/logo.png';

function read_bytes_or_fail(string $path): string {
    if (!is_file($path)) throw new RuntimeException("Súbor sa nenašiel: {$path}");
    $bytes = @file_get_contents($path);
    if ($bytes === false) throw new RuntimeException("Nepodarilo sa načítať: {$path}");
    return $bytes;
}
function sanitize_filename(string $s): string {
    $s = trim($s);
    $s = preg_replace('/[^\p{L}\p{N}\-_\.]+/u', '_', $s) ?? 'saldo';
    $s = preg_replace('/_+/', '_', $s) ?? $s;
    return $s === '' ? 'saldo' : $s;
}

$err = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $hdrMeno = $_POST['meno']  ?? '';
        $hdrSap  = $_POST['sap']   ?? '';
        $hdrUcet = $_POST['ucet']  ?? '';
        $hdrSpol = 'SWAN a.s.'; // fixné
        $theme   = $_POST['theme'] ?? 'blue';
        $output  = ($_POST['format'] ?? 'xlsx') === 'pdf' ? 'pdf' : 'xlsx';

        if ($hdrMeno === '' || $hdrSap === '' || $hdrUcet === '') {
            throw new RuntimeException('Vyplň Meno, SAP ID aj Zmluvný účet.');
        }

        $templateBytes = read_bytes_or_fail($template);
        $helperBytes   = read_bytes_or_fail($helper);

        if (empty($_FILES['src1']['tmp_name']) || !is_uploaded_file($_FILES['src1']['tmp_name'])) {
            throw new RuntimeException('Nahraj súbor Vstup 1 (pohyby).');
        }
        $src1Bytes = file_get_contents($_FILES['src1']['tmp_name']);

        if (empty($_FILES['src2']['tmp_name']) || !is_uploaded_file($_FILES['src2']['tmp_name'])) {
            throw new RuntimeException('Nahraj súbor Vstup 2 (väzby).');
        }
        $src2Bytes = file_get_contents($_FILES['src2']['tmp_name']);

        $logoBytes = is_file($logoPath) ? file_get_contents($logoPath) : null;

        $gen = new SaldoGenerator();
        $binary = $gen->generate(
            $templateBytes,
            $helperBytes,
            $src1Bytes,
            $src2Bytes,
            $hdrMeno,
            $hdrSap,
            $hdrUcet,
            $hdrSpol,
            $theme,
            $logoBytes,
            $output
        );

        $fnameBase = sanitize_filename($hdrMeno) . '_saldo';
        if ($output === 'pdf') {
            header('Content-Type: application/pdf');
            header('Content-Disposition: attachment; filename="'.$fnameBase.'.pdf"');
        } else {
            header('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            header('Content-Disposition: attachment; filename="'.$fnameBase.'.xlsx"');
        }
        header('Cache-Control: no-store');
        echo $binary;
        exit;

    } catch (Throwable $e) {
        $err = $e->getMessage();
    }
}
?>
<!doctype html>
<html lang="sk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saldo – generátor</title>
<style>
    :root { --c1:#0f172a; --c2:#334155; --bg:#f8fafc; --br:#e2e8f0; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; background: var(--bg); color: var(--c1); }
    .card { background:#fff; border:1px solid var(--br); border-radius:12px; padding:20px; max-width:920px; }
    h1 { margin:0 0 12px; font-size:22px; }
    .row { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    .row-3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
    label { display:block; font-size:12px; color:var(--c2); margin-bottom:6px; }
    input[type="text"], select, input[type="file"] { width:100%; padding:10px; border:1px solid var(--br); border-radius:8px; background:#fff; }
    .hint { font-size:12px; color:#64748b; }
    .error { background:#fef2f2; color:#991b1b; border:1px solid #fecaca; padding:10px 12px; border-radius:8px; margin-bottom:12px; }
    .btn { display:inline-block; padding:10px 14px; border-radius:10px; border:1px solid #0891b2; background:#06b6d4; color:#fff; font-weight:600; cursor:pointer; }
    .btn:disabled { opacity:0.5; cursor:not-allowed; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    .mt { margin-top:16px; }
    /* --- visual tuning --- */
    .row{ gap:20px; align-items:start; }
    input[type="text"], select, input[type="file"]{ box-sizing:border-box; line-height:1.25; border:1px solid #cbd5e1; }
    input[type="text"]::placeholder{ color:#9ca3af; opacity:1; }
    input[type="text"]:focus{ outline:none; border-color:#22d3ee; box-shadow:0 0 0 2px rgba(34,211,238,0.25); }
    @media (max-width: 820px){ .row, .row-3{ grid-template-columns:1fr; } }

    /* --- compact inputs final --- */
    input[type="text"], select, input[type="file"]{padding:6px 8px; font-size:14px; border:1px solid #cbd5e1; border-radius:6px;}
    input[type="text"]::placeholder{ color:#9ca3af; font-style:italic; opacity:1; }
    .row{ gap:18px; }

    /* --- final placeholder tuning --- */
    input[type="text"], select, input[type="file"]{padding:6px 8px; font-size:14px; border:1px solid #cbd5e1; border-radius:6px;}
    input[type="text"]::placeholder{ color:#9ca3af; font-style:italic; opacity:1; }
    .row{ gap:18px; }

</style>
</head>
<body>
<div class="card">
    <h1>Saldo – generátor</h1>
    <?php if ($err): ?>
        <div class="error">⚠️ <?= htmlspecialchars($err, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') ?></div>
    <?php endif; ?>
    <form method="post" enctype="multipart/form-data" autocomplete="off">
        <div class="row">
            <div>
                <label>Meno zákazníka</label>
                <input type="text" name="meno" required placeholder="napr. Jozef Mrkvička" value="<?= isset($_POST["meno"]) ? htmlspecialchars($_POST["meno"], ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") : "" ?>"
                       placeholder="Ján Novák"
                       value="<?= isset($_POST['meno']) ? htmlspecialchars($_POST['meno'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') : '' ?>">
            </div>
            <div>
                <label>SAP ID</label>
                <input type="text" name="sap" required placeholder="napr. 1088898" value="<?= isset($_POST["sap"]) ? htmlspecialchars($_POST["sap"], ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") : "" ?>"
                       placeholder="1088898"
                       value="<?= isset($_POST['sap']) ? htmlspecialchars($_POST['sap'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') : '' ?>">
            </div>
        </div>
        <div class="row mt">
            <div>
                <label>Zmluvný účet</label>
                <input type="text" name="ucet" required placeholder="napr. 7770128621" value="<?= isset($_POST["ucet"]) ? htmlspecialchars($_POST["ucet"], ENT_QUOTES | ENT_SUBSTITUTE, "UTF-8") : "" ?>"
                       placeholder="7770128621"
                       value="<?= isset($_POST['ucet']) ? htmlspecialchars($_POST['ucet'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') : '' ?>">
            </div>
        </div>

        <div class="row mt">
            <div>
                <label>Vstup 1 (pohyby) • XLSX</label>
                <input type="file" name="src1" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required>
                <div class="hint">Obsahuje: Číslo dokladu, Dátum zadania, Dátum účtovania, Splatnosť netto, Označenie pôvodu, Čiastka…</div>
            </div>
            <div>
                <label>Vstup 2 (väzby) • XLSX</label>
                <input type="file" name="src2" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required>
                <div class="hint">Obsahuje: Číslo dokladu, Doplnková referencia (s VBRK prefixom)…</div>
            </div>
        </div>

        <div class="row-3 mt">
            <div>
                <label>Téma</label>
                <select name="theme">
                    <option value="blue" <?= (($_POST['theme'] ?? '')==='blue') ? 'selected' : '' ?>>Blue</option>
                    <option value="gray" <?= (($_POST['theme'] ?? '')==='gray') ? 'selected' : '' ?>>Gray</option>
                    <option value="warm" <?= (($_POST['theme'] ?? '')==='warm') ? 'selected' : '' ?>>Warm</option>
                </select>
            </div>
            <div>
                <label>Formát výstupu</label>
                <select name="format">
                    <option value="xlsx" <?= (($_POST['format'] ?? '')!=='pdf') ? 'selected' : '' ?>>XLSX</option>
                    <option value="pdf"  <?= (($_POST['format'] ?? '')==='pdf')  ? 'selected' : '' ?>>PDF</option>
                </select>
            </div>
            <div>
                <label>Šablóny</label>
                <div class="hint">Načítava: <code>data/template_saldo.xlsx</code>, <code>data/pomocka_saldo.xlsx</code>, logo <code>data/logo.png</code></div>
            </div>
        </div>

        <div class="mt">
            <button class="btn" type="submit">Generovať saldo</button>
        </div>
    </form>
</div>

<script>
/* UX: placeholder sa skryje pri fokuse a vráti na blur */
document.querySelectorAll('input[type="text"][placeholder]').forEach(function(el){
  el.addEventListener('focus', function(){
    if (!this.dataset.ph) this.dataset.ph = this.getAttribute('placeholder') || '';
    this.setAttribute('placeholder','');
  });
  el.addEventListener('blur', function(){
    this.setAttribute('placeholder', this.dataset.ph || '');
  });
});
</script>
</body>
</html>
