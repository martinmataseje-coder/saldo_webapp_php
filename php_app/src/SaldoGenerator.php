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
    private const DATE_FORMAT = 'DD.MM.YY';

    private const THEMES = [
        'blue' => ['header' => '#25B3AD', 'alt' => '#F9FEFD', 'grid' => '#E2E8F0'],
        'gray' => ['header' => '#4A5568', 'alt' => '#F7F7F7', 'grid' => '#D9D9D9'],
        'warm' => ['header' => '#C6A875', 'alt' => '#FFF9F2', 'grid' => '#EADDC8'],
    ];

    /**
     * @throws \RuntimeException
     */
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

        $headers = [];
        $maxColumnIndex = Coordinate::columnIndexFromString($sheet->getHighestColumn());
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

        $missing = [];
        foreach ([
            'Číslo dokladu' => $cDoc,
            'Číslo Faktúry/číslo Faktúry' => $cInv,
            'Dátum vystavenia / Pripísania platby / Dátum zadania' => $cDz,
            'Dátum účtovania' => $cDu,
            'Splatnosť netto' => $cSn,
            'Typ dokladu' => $cTyp,
            'Čiastka' => $cAmt,
            'Zostatok' => $cBal,
        ] as $name => $col) {
            if ($col === null) {
                $missing[] = $name;
            }
        }

        if (!empty($missing)) {
            throw new \RuntimeException(
                'V TEMPLATE chýba niektorý povinný stĺpec. Chýbajú: ' . implode(', ', $missing)
            );
        }

        $dzHeaderCell = $sheet->getCellByColumnAndRow($cDz, self::HEADER_ROW);
        $dzHeaderNorm = $this->normalize((string)$dzHeaderCell->getValue());
        if (in_array($dzHeaderNorm, [
            $this->normalize('Dátum zadania'),
            $this->normalize('Dátum vystavenia/Pripísania platby'),
            $this->normalize('Dátum vystavenia / Pripísania platby'),
        ], true)) {
            $dzHeaderCell->setValue('Dátum vystavenia / Pripísania platby');
            $sheet->getStyleByColumnAndRow($cDz, self::HEADER_ROW)->getAlignment()
                ->setWrapText(true)
                ->setHorizontal(Alignment::HORIZONTAL_CENTER)
                ->setVertical(Alignment::VERTICAL_CENTER);
        }

        $helper = $this->loadSpreadsheetFromString($helperBytes);
        $helperSheet = $helper->getSheet(0);
        $helperHeaders = [];
        $helperMaxCol = Coordinate::columnIndexFromString($helperSheet->getHighestColumn());
        for ($c = 1; $c <= $helperMaxCol; $c++) {
            $helperHeaders[$c] = $helperSheet->getCellByColumnAndRow($c, 1)->getValue();
        }

        $hSrc = $this->findExactColumn($helperHeaders, 'Označenie pôvodu');
        $hDst = $this->findExactColumn($helperHeaders, 'Typ dokladu');
        if (!$hSrc || !$hDst) {
            throw new \RuntimeException("V pomôcke chýba 'Označenie pôvodu' alebo 'Typ dokladu'.");
        }

        $mapping = [];
        $helperLastRow = $helperSheet->getHighestRow();
        for ($r = 2; $r <= $helperLastRow; $r++) {
            $srcValue = $helperSheet->getCellByColumnAndRow($hSrc, $r)->getValue();
            $dstValue = $helperSheet->getCellByColumnAndRow($hDst, $r)->getValue();
            if (is_string($srcValue) && trim($srcValue) !== '') {
                $mapping[trim($srcValue)] = is_string($dstValue) ? trim($dstValue) : $dstValue;
            }
        }

        $src1 = $this->loadSpreadsheetFromString($src1Bytes);
        $src1Sheet = $src1->getSheet(0);
        $src1Headers = [];
        $src1MaxCol = Coordinate::columnIndexFromString($src1Sheet->getHighestColumn());
        for ($c = 1; $c <= $src1MaxCol; $c++) {
            $src1Headers[$c] = $src1Sheet->getCellByColumnAndRow($c, 1)->getValue();
        }

        $idxDoc = $this->findExactColumn($src1Headers, 'Číslo dokladu');
        $idxDz = $this->findExactColumn($src1Headers, 'Dátum zadania');
        $idxDu = $this->findExactColumn($src1Headers, 'Dátum účtovania');
        $idxSn = $this->findExactColumn($src1Headers, 'Splatnosť netto');
        $idxOp = $this->findExactColumn($src1Headers, 'Označenie pôvodu');
        $idxAmt = $this->findExactColumn($src1Headers, 'Čiastka');

        $currentLastRow = $sheet->getHighestRow();
        if ($currentLastRow > self::HEADER_ROW) {
            $sheet->removeRow(self::HEADER_ROW + 1, $currentLastRow - self::HEADER_ROW);
        }

        $writeRow = self::HEADER_ROW + 1;
        $src1LastRow = $src1Sheet->getHighestRow();
        for ($r = 2; $r <= $src1LastRow; $r++) {
            $rowHasData = false;
            for ($c = 1; $c <= $src1MaxCol; $c++) {
                $value = $src1Sheet->getCellByColumnAndRow($c, $r)->getValue();
                if ($value !== null && $value !== '') {
                    $rowHasData = true;
                    break;
                }
            }
            if (!$rowHasData) {
                continue;
            }

            $oznPov = $idxOp ? $src1Sheet->getCellByColumnAndRow($idxOp, $r)->getValue() : null;
            $mappedTyp = null;
            if ($oznPov !== null) {
                $key = is_string($oznPov) ? trim($oznPov) : $oznPov;
                if (is_string($key) && array_key_exists($key, $mapping)) {
                    $mappedTyp = $mapping[$key];
                } elseif ($key !== null && array_key_exists($key, $mapping)) {
                    $mappedTyp = $mapping[$key];
                }
            }

            $sheet->setCellValueByColumnAndRow($cDoc, $writeRow, $idxDoc ? $src1Sheet->getCellByColumnAndRow($idxDoc, $r)->getValue() : null);
            $sheet->setCellValueByColumnAndRow($cDz, $writeRow, $idxDz ? $src1Sheet->getCellByColumnAndRow($idxDz, $r)->getValue() : null);
            $sheet->setCellValueByColumnAndRow($cDu, $writeRow, $idxDu ? $src1Sheet->getCellByColumnAndRow($idxDu, $r)->getValue() : null);

            if ($mappedTyp !== null && is_string($mappedTyp) && $this->normalize($mappedTyp) === $this->normalize('Faktúra')) {
                $sheet->setCellValueByColumnAndRow($cSn, $writeRow, $idxSn ? $src1Sheet->getCellByColumnAndRow($idxSn, $r)->getValue() : null);
            } else {
                $sheet->setCellValueByColumnAndRow($cSn, $writeRow, null);
            }

            $sheet->setCellValueByColumnAndRow($cTyp, $writeRow, $mappedTyp ?? null);
            $sheet->setCellValueByColumnAndRow($cAmt, $writeRow, $idxAmt ? $src1Sheet->getCellByColumnAndRow($idxAmt, $r)->getValue() : null);
            $writeRow++;
        }

        $lastRow = $this->lastDataRow($sheet, $cDoc);
        $colAmtLetter = Coordinate::stringFromColumnIndex($cAmt);
        $colBalLetter = Coordinate::stringFromColumnIndex($cBal);
        for ($r = self::HEADER_ROW + 1; $r <= $lastRow; $r++) {
            $formula = $r === self::HEADER_ROW + 1
                ? sprintf('=%s%d', $colAmtLetter, $r)
                : sprintf('=%s%d+%s%d', $colBalLetter, $r - 1, $colAmtLetter, $r);
            $sheet->setCellValueByColumnAndRow($cBal, $r, $formula);
        }

        foreach ([$cDz, $cDu, $cSn] as $column) {
            if ($column === null) {
                continue;
            }
            for ($r = self::HEADER_ROW + 1; $r <= $lastRow; $r++) {
                $sheet->getStyleByColumnAndRow($column, $r)
                    ->getNumberFormat()
                    ->setFormatCode(self::DATE_FORMAT);
            }
        }

        $src2 = $this->loadSpreadsheetFromString($src2Bytes);
        $src2Sheet = $src2->getSheet(0);
        $src2Headers = [];
        $src2MaxCol = Coordinate::columnIndexFromString($src2Sheet->getHighestColumn());
        for ($c = 1; $c <= $src2MaxCol; $c++) {
            $src2Headers[$c] = $src2Sheet->getCellByColumnAndRow($c, 1)->getValue();
        }

        $idx2Doc = $this->findExactColumn($src2Headers, 'Číslo dokladu');
        $idx2Ref = $this->findExactColumn($src2Headers, 'Doplnková referencia');
        if (!$idx2Doc || !$idx2Ref) {
            throw new \RuntimeException("V zdroji 2 chýba 'Číslo dokladu' alebo 'Doplnková referencia'.");
        }

        $refMap = [];
        $src2LastRow = $src2Sheet->getHighestRow();
        for ($r = 2; $r <= $src2LastRow; $r++) {
            $doc = $src2Sheet->getCellByColumnAndRow($idx2Doc, $r)->getValue();
            $ref = $src2Sheet->getCellByColumnAndRow($idx2Ref, $r)->getValue();
            if ($doc === null || $doc === '') {
                continue;
            }
            $key = trim((string)$doc);
            $value = '';
            if (is_string($ref)) {
                $value = trim($ref);
                $upper = strtoupper($value);
                if (str_starts_with($upper, 'VBRK')) {
                    $value = trim(substr($value, 4));
                }
            } elseif ($ref !== null) {
                $value = (string)$ref;
            }
            $refMap[$key] = $value;
        }

        for ($r = self::HEADER_ROW + 1; $r <= $lastRow; $r++) {
            $docValue = $sheet->getCellByColumnAndRow($cDoc, $r)->getValue();
            $typValue = $sheet->getCellByColumnAndRow($cTyp, $r)->getValue();
            if ($this->isInvoice($typValue)) {
                $key = trim((string)$docValue);
                $sheet->setCellValueByColumnAndRow(
                    $cInv,
                    $r,
                    $key !== '' && array_key_exists($key, $refMap) ? ($refMap[$key] ?: null) : null
                );
            } else {
                $sheet->setCellValueByColumnAndRow($cInv, $r, null);
            }
        }

        $sheet->setCellValue('B1', $hdrSap);
        $sheet->setCellValue('B2', $hdrMeno);
        $sheet->setCellValue('B3', $hdrSpol);
        $sheet->setCellValue('B4', $hdrUcet);

        $this->insertLogo($sheet, $logoBytes);
        $this->styleWorksheet($sheet, $cDoc, $cInv, $cDz, $cDu, $cSn, $cTyp, $cAmt, $cBal, $lastRow, $theme);

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

    private function normalize(?string $value): string
    {
        if ($value === null) {
            return '';
        }
        $s = str_replace("\u{00A0}", ' ', (string)$value);
        $s = trim($s);
        $s = mb_strtolower($s, 'UTF-8');
        $transliterated = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $s);
        if ($transliterated !== false) {
            $s = $transliterated;
        }
        return preg_replace('/\s+/', ' ', $s) ?? '';
    }

    private function findColumn(array $headers, string $name): ?int
    {
        $target = $this->normalize($name);
        foreach ($headers as $idx => $header) {
            if ($this->normalize((string)$header) === $target) {
                return (int)$idx;
            }
        }
        return null;
    }

    private function findExactColumn(array $headers, string $name): ?int
    {
        foreach ($headers as $idx => $header) {
            if (is_string($header) && trim($header) === $name) {
                return (int)$idx;
            }
        }
        return null;
    }

    private function lastDataRow(Worksheet $sheet, int $keyColumn): int
    {
        $last = self::HEADER_ROW;
        $maxRow = $sheet->getHighestRow();
        for ($r = self::HEADER_ROW + 1; $r <= $maxRow; $r++) {
            $value = $sheet->getCellByColumnAndRow($keyColumn, $r)->getValue();
            if ($value !== null && $value !== '') {
                $last = $r;
            }
        }
        return $last;
    }

    private function isInvoice($value): bool
    {
        if (!is_string($value)) {
            return false;
        }
        return $this->normalize($value) === $this->normalize('Faktúra');
    }

    private function styleWorksheet(
        Worksheet $sheet,
        int $cDoc,
        int $cInv,
        int $cDz,
        int $cDu,
        int $cSn,
        int $cTyp,
        int $cAmt,
        int $cBal,
        int $lastRow,
        string $theme
    ): void {
        $maxColumn = $sheet->getHighestColumn();
        $headerRange = sprintf('A%d:%s%d', self::HEADER_ROW, $maxColumn, self::HEADER_ROW);
        $headerStyle = $sheet->getStyle($headerRange);
        $headerStyle->getFont()->setBold(true)->getColor()->setRGB('0F172A');
        $headerStyle->getFill()->setFillType(Fill::FILL_SOLID)->getStartColor()->setRGB('EAFBF9');
        $headerStyle->getAlignment()
            ->setHorizontal(Alignment::HORIZONTAL_CENTER)
            ->setVertical(Alignment::VERTICAL_CENTER)
            ->setWrapText(true);
        $headerStyle->getBorders()->getAllBorders()->setBorderStyle(Border::BORDER_THIN)->getColor()->setRGB('D0D7E1');

        $widths = [
            $cDoc => 16,
            $cInv => 18,
            $cDz => 18,
            $cDu => 16,
            $cSn => 16,
            $cTyp => 22,
            $cAmt => 14,
            $cBal => 14,
        ];
        foreach ($widths as $column => $width) {
            if ($column !== null) {
                $sheet->getColumnDimension(Coordinate::stringFromColumnIndex($column))->setWidth($width);
            }
        }

        if ($cAmt !== null) {
            $sheet->getStyleByColumnAndRow($cAmt, self::HEADER_ROW + 1, $cAmt, $lastRow)
                ->getNumberFormat()->setFormatCode('#,##0.00');
        }
        if ($cBal !== null) {
            $sheet->getStyleByColumnAndRow($cBal, self::HEADER_ROW + 1, $cBal, $lastRow)
                ->getNumberFormat()->setFormatCode('#,##0.00');
        }

        $borderStyle = [
            'borders' => [
                'allBorders' => [
                    'borderStyle' => Border::BORDER_THIN,
                    'color' => ['rgb' => 'D0D7E1'],
                ],
            ],
        ];

        $zebraFill = 'F7FDFB';
        $maxColumnLetter = $sheet->getHighestColumn();
        for ($r = self::HEADER_ROW + 1; $r <= $lastRow; $r++) {
            $range = sprintf('A%d:%s%d', $r, $maxColumnLetter, $r);
            $sheet->getStyle($range)->applyFromArray($borderStyle);
            if ((($r - (self::HEADER_ROW + 1)) % 2) === 0) {
                $sheet->getStyle($range)->getFill()
                    ->setFillType(Fill::FILL_SOLID)
                    ->getStartColor()->setRGB($zebraFill);
            }
        }
    }

    private function insertLogo(Worksheet $sheet, ?string $logoBytes): void
    {
        if ($logoBytes === null || $logoBytes === '') {
            return;
        }
        $tmp = tempnam(sys_get_temp_dir(), 'saldo_logo');
        $extension = $this->detectImageExtension($logoBytes) ?? 'png';
        $path = $tmp . '.' . $extension;
        file_put_contents($path, $logoBytes);

        $drawing = new Drawing();
        $drawing->setPath($path);
        $drawing->setCoordinates('A1');
        $drawing->setWorksheet($sheet);
    }

    private function detectImageExtension(string $bytes): ?string
    {
        $finfo = new \finfo(FILEINFO_MIME_TYPE);
        $mime = $finfo->buffer($bytes);
        return match ($mime) {
            'image/png' => 'png',
            'image/jpeg' => 'jpg',
            'image/gif' => 'gif',
            default => null,
        };
    }

    private function formatDate($value): string
    {
        if ($value instanceof DateTimeInterface) {
            return $value->format('d.m.Y');
        }
        if (is_numeric($value)) {
            try {
                $dt = ExcelDate::excelToDateTimeObject((float)$value);
                if ($dt instanceof DateTimeInterface) {
                    return $dt->format('d.m.Y');
                }
            } catch (\Throwable) {
                // ignore
            }
        }
        if ($value === null) {
            return '';
        }
        $s = trim((string)$value);
        if ($s === '') {
            return '';
        }
        if (str_contains($s, ' ')) {
            $parts = explode(' ', $s);
            $s = $parts[0];
        }
        if (str_contains($s, '-')) {
            $parts = explode('-', $s);
            if (count($parts) === 3) {
                return sprintf('%s.%s.%s', $parts[2], $parts[1], $parts[0]);
            }
        }
        return $s;
    }

    private function formatMoney(?float $value): string
    {
        if ($value === null) {
            return '';
        }
        $formatted = number_format($value, 2, ',', ' ');
        return $formatted . '\u{00A0}€';
    }

    private function toFloat($value): ?float
    {
        if ($value === null || $value === '') {
            return null;
        }
        if (is_numeric($value)) {
            return (float)$value;
        }
        $s = str_replace([' ', '\u{00A0}'], '', (string)$value);
        $s = str_replace(',', '.', $s);
        return is_numeric($s) ? (float)$s : null;
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
            $dz = $sheet->getCellByColumnAndRow($cDz, $r)->getValue();
            $du = $sheet->getCellByColumnAndRow($cDu, $r)->getValue();
            $sn = $sheet->getCellByColumnAndRow($cSn, $r)->getValue();
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

        $total = $this->formatMoney($running);
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
        $escapedSap = $this->escapeHtml($hdrSap);
        $escapedUcet = $this->escapeHtml($hdrUcet);
        $escapedSpol = $this->escapeHtml($hdrSpol);

        $rowsHtml = '';
        foreach ($dataRows as $row) {
            $rowsHtml .= '<tr>';
            foreach ($row as $idx => $cell) {
                $classes = '';
                if (in_array($idx, [2, 3, 4], true)) {
                    $classes = ' class="text-center"';
                }
                if (in_array($idx, [6, 7], true)) {
                    $classes = ' class="text-right"';
                }
                $rowsHtml .= sprintf('<td%s>%s</td>', $classes, nl2br(htmlspecialchars((string)$cell, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')));
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
    .header { display: flex; gap: 12px; align-items: flex-start; }
    .header-text { flex: 1; }
    .title { font-size: 18px; font-weight: bold; margin: 0 0 4px 0; }
    .meta { margin: 0; }
    table { border-collapse: collapse; width: 100%; }
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
    <div class="logo">$logoHtml</div>
    <div class="header-text">
        <h1 class="title">Náhľad na fakturačný účet – saldo</h1>
        <p class="meta">Dátum generovania: <strong>{$generatedDate}</strong></p>
        <p class="meta">{$escapedSpol} — <strong>Meno:</strong> {$escapedMeno} • <strong>SAP ID:</strong> {$escapedSap} • <strong>Zmluvný účet:</strong> {$escapedUcet}</p>
    </div>
</div>
<table>
    <thead>
        <tr>{$headerHtml}</tr>
    </thead>
    <tbody>
        {$rowsHtml}
    </tbody>
    <tfoot>
        <tr>
            <td colspan="6"></td>
            <td class="text-right">Súčet</td>
            <td class="text-right">{$this->escapeHtml($total)}</td>
        </tr>
    </tfoot>
</table>
</body>
</html>
HTML;

        $options = new Options();
        $options->set('isRemoteEnabled', true);
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
}
