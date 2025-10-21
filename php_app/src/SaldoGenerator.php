<?php

namespace Saldo;

use DateTimeInterface;
use Dompdf\Dompdf;
use Dompdf\Options;
use PhpOffice\PhpSpreadsheet\Cell\Coordinate;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Shared\Date as ExcelDate;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Style\Alignment;
use PhpOffice\PhpSpreadsheet\Style\Border;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Worksheet\Drawing;
use PhpOffice\PhpSpreadsheet\Worksheet\Worksheet;

class SaldoGenerator
{
    private const HEADER_ROW = 9;
    private const DATE_FORMAT = 'dd.mm.yy';

    private const THEMES = [
        'blue' => ['header' => '#25B3AD', 'alt' => '#F9FEFD', 'grid' => '#E2E8F0'],
        'gray' => ['header' => '#4A5568', 'alt' => '#F7F7F7', 'grid' => '#D9D9D9'],
        'warm' => ['header' => '#C6A875', 'alt' => '#FFF9F2', 'grid' => '#EADDC8'],
    ];

    public function generate(
        string $templateBytes,
        string $helperBytes,
        string $src1Bytes,
        string $src2Bytes,
        string $hdrMeno,
        string $hdrSap,
        string $hdrUcet,
        string $hdrSpol = 'SWAN a.s.',
        string $theme = 'blue',
        ?string $logoBytes = null,
        string $output = 'xlsx'
    ): string {
        $spreadsheet = $this->loadSpreadsheetFromString($templateBytes);
        $sheet = $spreadsheet->getSheet(0);

        // ... tu máš všetky spracovania ako predtým (skrátené pre prehľad)
        // Nemusíš nič meniť v logike výpočtov, všetko funguje rovnako

        if ($output === 'pdf') {
            return $this->buildPdf($sheet, $hdrMeno, $hdrSap, $hdrUcet, $hdrSpol, $logoBytes, $theme);
        }

        $writer = IOFactory::createWriter($spreadsheet, 'Xlsx');
        $writer->setPreCalculateFormulas(false);
        ob_start();
        $writer->save('php://output');
        return (string)ob_get_clean();
    }

    private function loadSpreadsheetFromString(string $bytes): Spreadsheet
    {
        $tmp = tempnam(sys_get_temp_dir(), 'saldo');
        file_put_contents($tmp, $bytes);
        $reader = IOFactory::createReader('Xlsx');
        $reader->setReadDataOnly(false);
        $spreadsheet = $reader->load($tmp);
        unlink($tmp);
        return $spreadsheet;
    }

    private function buildPdf(
        Worksheet $sheet,
        string $hdrMeno,
        string $hdrSap,
        string $hdrUcet,
        string $hdrSpol,
        ?string $logoBytes,
        string $theme
    ): string {
        $maxColumnIndex = Coordinate::columnIndexFromString($sheet->getHighestColumn());
        $headers = [];
        for ($c = 1; $c <= $maxColumnIndex; $c++) {
            $headers[$c] = $sheet->getCellByColumnAndRow($c, self::HEADER_ROW)->getValue();
        }

        $cDoc = $this->findColumn($headers, 'Číslo dokladu');
        $cInv = $this->findColumn($headers, 'číslo Faktúry') ?? $this->findColumn($headers, 'Číslo Faktúry');
        $cDz = $this->findColumn($headers, 'Dátum vystavenia / Pripísania platby')
            ?? $this->findColumn($headers, 'Dátum vystavenia/Pripísania platby')
            ?? $this->findColumn($headers, "Dátum vystavenia /\nPripísania platby")
            ?? $this->findColumn($headers, 'Dátum zadania');
        $cDu = $this->findColumn($headers, 'Dátum účtovania');
        $cSn = $this->findColumn($headers, 'Splatnosť netto');
        $cTyp = $this->findColumn($headers, 'Typ dokladu');
        $cAmt = $this->findColumn($headers, 'Čiastka');
        $cBal = $this->findColumn($headers, 'Zostatok');

        $lastRow = $this->lastDataRow($sheet, $cDoc);
        $dataRows = [];
        $running = 0.0;
        for ($r = self::HEADER_ROW + 1; $r <= $lastRow; $r++) {
            $doc = $sheet->getCellByColumnAndRow($cDoc, $r)->getValue();
            $inv = $sheet->getCellByColumnAndRow($cInv, $r)->getValue();
            $dz  = $sheet->getCellByColumnAndRow($cDz,  $r)->getValue();
            $du  = $sheet->getCellByColumnAndRow($cDu,  $r)->getValue();
            $sn  = $sheet->getCellByColumnAndRow($cSn,  $r)->getValue();
            $typ = $sheet->getCellByColumnAndRow($cTyp, $r)->getValue();
            $amtVal = $this->toFloat($sheet->getCellByColumnAndRow($cAmt, $r)->getCalculatedValue());
            $running += $amtVal ?? 0.0;

            $dataRows[] = [
                $doc,
                $this->isInvoice($typ) ? $inv : '',
                $this->formatDate($dz),
                $this->formatDate($du),
                $this->isInvoice($typ) ? $this->formatDate($sn) : '',
                $typ,
                $this->formatMoney($amtVal),
                $this->formatMoney($running),
            ];
        }

        $lastBalCell = $sheet->getCellByColumnAndRow($cBal, $lastRow)->getCalculatedValue();
        $total = $this->formatMoney($this->toFloat($lastBalCell));
        $palette = self::THEMES[$theme] ?? self::THEMES['blue'];

        $logoHtml = '';
        if ($logoBytes) {
            $logoHtml = sprintf(
                '<img src="data:image/png;base64,%s" alt="Logo" style="height:60px;width:60px;object-fit:contain;" />',
                base64_encode($logoBytes)
            );
        }

        $generatedDate = date('d.m.Y');
        $escapedMeno = $this->escapeHtml($hdrMeno);
        $escapedSap  = $this->escapeHtml($hdrSap);
        $escapedUcet = $this->escapeHtml($hdrUcet);
        $escapedSpol = $this->escapeHtml($hdrSpol);

        $rowsHtml = '';
        foreach ($dataRows as $row) {
            $rowsHtml .= '<tr>';
            foreach ($row as $idx => $cell) {
                $classes = '';
                if (in_array($idx, [2, 3, 4], true)) $classes = ' class="text-center"';
                if (in_array($idx, [6, 7], true))    $classes = ' class="text-right"';
                $rowsHtml .= sprintf(
                    '<td%s>%s</td>',
                    $classes,
                    nl2br(htmlspecialchars((string)$cell, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'))
                );
            }
            $rowsHtml .= '</tr>';
        }

        $headersPdf = [
            'Č. dokladu',
            'Č. faktúry',
            "Dátum vystavenia /\nPripísania platby",
            'Dátum účt.',
            'Splatnosť',
            'Typ dokladu',
            'Čiastka',
            'Zostatok',
        ];
        $headerHtml = '';
        foreach ($headersPdf as $text) {
            $headerHtml .= sprintf('<th>%s</th>', nl2br(htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')));
        }

        $html = <<<HTML
<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="utf-8" />
<title>Saldo report</title>
<style>
    body { font-family: DejaVu Sans, sans-serif; font-size: 11px; color: #0f172a; }
    .header { display: grid; grid-template-columns: 60px 1fr; column-gap: 0; align-items: start; }
    .header-text { margin-left: 0; }
    .title { font-size: 18px; font-weight: bold; margin: 0 0 4px 0; }
    .meta { margin: 0; }
    table { border-collapse: collapse; width: 100%; margin-top: 10px; }
    th { background: {$palette['header']}; color: #ffffff; padding: 4px; font-size: 10px; }
    td { padding: 4px; font-size: 9px; border: 1px solid {$palette['grid']}; }
    tr:nth-child(odd) td { background: #ffffff; }
    tr:nth-child(even) td { background: {$palette['alt']}; }
    .text-center { text-align: center; }
    .text-right { text-align: right; }
    tfoot td { background: {$palette['header']}; color: #ffffff; font-weight: bold; }
</style>
</head>
<body>
<div class="header">
    <div>$logoHtml</div>
    <div class="header-text">
        <h1 class="title">Náhľad na fakturačný účet – saldo</h1>
        <p class="meta">Dátum generovania: <strong>{$generatedDate}</strong></p>
        <p class="meta">{$escapedSpol} — <strong>Meno:</strong> {$escapedMeno} • <strong>SAP ID:</strong> {$escapedSap} • <strong>Zmluvný účet:</strong> {$escapedUcet}</p>
    </div>
</div>
<table>
    <thead><tr>{$headerHtml}</tr></thead>
    <tbody>{$rowsHtml}</tbody>
    <tfoot>
        <tr><td colspan="6"></td><td class="text-right">Celková suma</td><td class="text-right">{$this->escapeHtml($total)}</td></tr>
    </tfoot>
</table>
</body>
</html>
HTML;

        $options = new Options();
        $options->set('isRemoteEnabled', true);
        $options->set('defaultFont', 'DejaVu Sans');
        $dompdf = new Dompdf($options);
        $dompdf->loadHtml($html, 'UTF-8');
        $dompdf->setPaper('A4', 'portrait');
        $dompdf->render();
        return $dompdf->output();
    }

    private function escapeHtml(string $value): string
    {
        return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }

    private function findColumn(array $headers, string $name): ?int
    {
        foreach ($headers as $i => $val) {
            if (trim((string)$val) === $name) return $i;
        }
        return null;
    }

    private function lastDataRow(Worksheet $sheet, int $keyColumn): int
    {
        $maxRow = $sheet->getHighestRow();
        $last = self::HEADER_ROW;
        for ($r = self::HEADER_ROW + 1; $r <= $maxRow; $r++) {
            if ($sheet->getCellByColumnAndRow($keyColumn, $r)->getValue() !== null) {
                $last = $r;
            }
        }
        return $last;
    }

    private function toFloat($value): ?float
    {
        if ($value === null || $value === '') return null;
        $s = str_replace([' ', "\u{00A0}", "\xC2\xA0"], '', (string)$value);
        $s = str_replace(',', '.', $s);
        return is_numeric($s) ? (float)$s : null;
    }

    private function formatMoney(?float $value): string
    {
        if ($value === null) return '';
        return number_format($value, 2, ',', ' ') . ' €';
    }

    private function formatDate($value): string
    {
        if ($value instanceof DateTimeInterface) return $value->format('d.m.Y');
        if (is_numeric($value)) {
            try {
                $dt = ExcelDate::excelToDateTimeObject((float)$value);
                return $dt->format('d.m.Y');
            } catch (\Throwable) {
                return '';
            }
        }
        return trim((string)$value);
    }

    private function isInvoice($value): bool
    {
        return is_string($value) && stripos($value, 'fakt') !== false;
    }
}
