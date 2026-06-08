Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function Clamp-Channel {
  param([double]$Value)
  return [Math]::Max(0, [Math]::Min(255, [int][Math]::Round($Value)))
}

function Get-Luminance {
  param([System.Drawing.Color]$Color)
  return (0.299 * $Color.R) + (0.587 * $Color.G) + (0.114 * $Color.B)
}

function Is-NearWhite {
  param([System.Drawing.Color]$Color)
  return ($Color.R -ge 246 -and $Color.G -ge 246 -and $Color.B -ge 246)
}

function Mix-Color {
  param(
    [System.Drawing.Color]$A,
    [System.Drawing.Color]$B,
    [double]$Amount
  )

  $t = [Math]::Max(0.0, [Math]::Min(1.0, $Amount))
  return [System.Drawing.Color]::FromArgb(
    $A.A,
    (Clamp-Channel (($A.R * (1.0 - $t)) + ($B.R * $t))),
    (Clamp-Channel (($A.G * (1.0 - $t)) + ($B.G * $t))),
    (Clamp-Channel (($A.B * (1.0 - $t)) + ($B.B * $t)))
  )
}

function Tint-RegionPixels {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [double]$RedMultiplier,
    [double]$GreenMultiplier,
    [double]$BlueMultiplier,
    [switch]$IncludeNearWhite
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8) { continue }
      if (-not $IncludeNearWhite -and (Is-NearWhite $pixel)) { continue }

      $Bitmap.SetPixel(
        $x,
        $y,
        [System.Drawing.Color]::FromArgb(
          $pixel.A,
          (Clamp-Channel ($pixel.R * $RedMultiplier)),
          (Clamp-Channel ($pixel.G * $GreenMultiplier)),
          (Clamp-Channel ($pixel.B * $BlueMultiplier))
        )
      )
    }
  }
}

function Apply-StripedPattern {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$BaseColor,
    [System.Drawing.Color]$StripeColor,
    [int]$Spacing,
    [int]$Thickness,
    [int]$Slope = 1
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $lineIndex = ($x + ($y * $Slope)) % $Spacing
      $target = if ($lineIndex -lt $Thickness) { $StripeColor } else { $BaseColor }
      $brightness = (Get-Luminance $pixel) / 255.0
      $amount = 0.55 + ((1.0 - $brightness) * 0.20)
      $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $target $amount))
    }
  }
}

function Fill-RegionColor {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$Color
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }
      $blend = if ((Get-Luminance $pixel) -lt 80) { 0.45 } else { 0.72 }
      $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $Color $blend))
    }
  }
}

function Add-HairHighlights {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect
  )

  $highlight = [System.Drawing.Color]::FromArgb(255, 178, 148, 118)

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $rx = ($x - $Rect.Left) / [double]([Math]::Max(1, $Rect.Width))
      $ry = ($y - $Rect.Top) / [double]([Math]::Max(1, $Rect.Height))
      $band = [Math]::Abs(($rx * 0.85 + $ry * 0.55) - 0.42)
      if ($band -lt 0.045) {
        $amount = 0.22 + ((0.045 - $band) * 3.4)
        $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $highlight $amount))
      }
    }
  }
}

function Shade-RegionVertical {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$TopColor,
    [System.Drawing.Color]$BottomColor,
    [double]$Amount = 0.35
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $t = ($y - $Rect.Top) / [double]([Math]::Max(1, $Rect.Height))
      $target = Mix-Color $TopColor $BottomColor $t
      $strength = $Amount + ((1.0 - ((Get-Luminance $pixel) / 255.0)) * 0.12)
      $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $target $strength))
    }
  }
}

function Add-AccentStroke {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$Color,
    [double]$Threshold = 0.040,
    [double]$Amount = 0.42
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $rx = ($x - $Rect.Left) / [double]([Math]::Max(1, $Rect.Width))
      $ry = ($y - $Rect.Top) / [double]([Math]::Max(1, $Rect.Height))
      $band = [Math]::Abs(($rx * 0.95) - ($ry * 0.50) - 0.20)
      if ($band -lt $Threshold) {
        $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $Color ($Amount + (($Threshold - $band) * 2.4))))
      }
    }
  }
}

function Save-Png {
  param([System.Drawing.Bitmap]$Bitmap, [string]$Path)
  $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
}

$root = Split-Path -Parent $PSScriptRoot
$atlasDir = Join-Path $root "haru_greeter_pro_jp\haru_greeter_pro_jp\runtime\haru_greeter_t05.2048"

$sourceFace = Join-Path $atlasDir "texture_00.png"
$sourceClothes = Join-Path $atlasDir "texture_01.png"
$targetFace = Join-Path $atlasDir "texture_00_inspired.png"
$targetClothes = Join-Path $atlasDir "texture_01_inspired.png"

$faceBitmap = [System.Drawing.Bitmap]::FromFile($sourceFace)
$clothesBitmap = [System.Drawing.Bitmap]::FromFile($sourceClothes)

$faceOut = $null
$clothesOut = $null

try {
  $faceOut = New-Object System.Drawing.Bitmap($faceBitmap)
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(238, 12, 166, 136)) -RedMultiplier 0.44 -GreenMultiplier 0.34 -BlueMultiplier 0.22
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(197, 149, 257, 210)) -RedMultiplier 0.44 -GreenMultiplier 0.34 -BlueMultiplier 0.22
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(417, 12, 148, 179)) -RedMultiplier 0.44 -GreenMultiplier 0.34 -BlueMultiplier 0.22
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(581, 154, 151, 171)) -RedMultiplier 0.44 -GreenMultiplier 0.34 -BlueMultiplier 0.22
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(602, 336, 125, 228)) -RedMultiplier 0.44 -GreenMultiplier 0.34 -BlueMultiplier 0.22
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(441, 0, 188, 153)) -RedMultiplier 1.02 -GreenMultiplier 0.94 -BlueMultiplier 0.88 -IncludeNearWhite
  Tint-RegionPixels -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(254, 394, 151, 169)) -RedMultiplier 1.02 -GreenMultiplier 0.94 -BlueMultiplier 0.88 -IncludeNearWhite
  Fill-RegionColor -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(474, 313, 173, 94)) -Color ([System.Drawing.Color]::FromArgb(255, 54, 24, 28))
  Fill-RegionColor -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(486, 418, 143, 86)) -Color ([System.Drawing.Color]::FromArgb(255, 235, 228, 220))
  Fill-RegionColor -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(510, 370, 111, 60)) -Color ([System.Drawing.Color]::FromArgb(255, 132, 84, 88))
  Fill-RegionColor -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(300, 646, 170, 90)) -Color ([System.Drawing.Color]::FromArgb(255, 216, 168, 164))
  Add-HairHighlights -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(238, 12, 327, 340))
  Add-HairHighlights -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(581, 154, 151, 410))
  Add-AccentStroke -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(238, 12, 166, 136)) -Color ([System.Drawing.Color]::FromArgb(255, 182, 154, 129)) -Threshold 0.05 -Amount 0.34
  Add-AccentStroke -Bitmap $faceOut -Rect (New-Object System.Drawing.Rectangle(197, 149, 257, 210)) -Color ([System.Drawing.Color]::FromArgb(255, 164, 136, 112)) -Threshold 0.038 -Amount 0.22
  Save-Png -Bitmap $faceOut -Path $targetFace

  $clothesOut = New-Object System.Drawing.Bitmap($clothesBitmap)
  Shade-RegionVertical -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(0, 0, 260, 220)) -TopColor ([System.Drawing.Color]::FromArgb(255, 140, 124, 106)) -BottomColor ([System.Drawing.Color]::FromArgb(255, 96, 84, 72)) -Amount 0.56
  Shade-RegionVertical -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(0, 298, 273, 424)) -TopColor ([System.Drawing.Color]::FromArgb(255, 128, 111, 95)) -BottomColor ([System.Drawing.Color]::FromArgb(255, 94, 80, 69)) -Amount 0.60
  Shade-RegionVertical -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(294, 0, 260, 740)) -TopColor ([System.Drawing.Color]::FromArgb(255, 122, 104, 88)) -BottomColor ([System.Drawing.Color]::FromArgb(255, 86, 73, 63)) -Amount 0.58
  Shade-RegionVertical -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(544, 318, 222, 183)) -TopColor ([System.Drawing.Color]::FromArgb(255, 86, 73, 64)) -BottomColor ([System.Drawing.Color]::FromArgb(255, 58, 49, 42)) -Amount 0.55

  foreach ($rect in @(
    (New-Object System.Drawing.Rectangle(554, 0, 202, 182)),
    (New-Object System.Drawing.Rectangle(561, 181, 158, 122)),
    (New-Object System.Drawing.Rectangle(703, 633, 63, 133))
  )) {
    Apply-StripedPattern -Bitmap $clothesOut -Rect $rect -BaseColor ([System.Drawing.Color]::FromArgb(255, 110, 49, 59)) -StripeColor ([System.Drawing.Color]::FromArgb(255, 187, 178, 205)) -Spacing 17 -Thickness 5 -Slope 1
  }

  Apply-StripedPattern -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(607, 303, 87, 110)) -BaseColor ([System.Drawing.Color]::FromArgb(255, 243, 246, 249)) -StripeColor ([System.Drawing.Color]::FromArgb(255, 163, 188, 224)) -Spacing 11 -Thickness 2 -Slope 1
  Fill-RegionColor -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(134, 420, 70, 54)) -Color ([System.Drawing.Color]::FromArgb(255, 122, 100, 79))
  Add-AccentStroke -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(0, 298, 273, 424)) -Color ([System.Drawing.Color]::FromArgb(255, 176, 156, 135)) -Threshold 0.035 -Amount 0.20
  Add-AccentStroke -Bitmap $clothesOut -Rect (New-Object System.Drawing.Rectangle(294, 0, 260, 740)) -Color ([System.Drawing.Color]::FromArgb(255, 164, 145, 122)) -Threshold 0.028 -Amount 0.16
  Save-Png -Bitmap $clothesOut -Path $targetClothes
}
finally {
  if ($faceOut) { $faceOut.Dispose() }
  if ($clothesOut) { $clothesOut.Dispose() }
  $faceBitmap.Dispose()
  $clothesBitmap.Dispose()
}
