Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function Clamp-Channel {
  param([double]$Value)
  return [Math]::Max(0, [Math]::Min(255, [int][Math]::Round($Value)))
}

function Is-NearWhite {
  param([System.Drawing.Color]$Color)
  return ($Color.R -ge 245 -and $Color.G -ge 245 -and $Color.B -ge 245)
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

function Get-Luminance {
  param([System.Drawing.Color]$Color)
  return (0.299 * $Color.R) + (0.587 * $Color.G) + (0.114 * $Color.B)
}

function Get-AverageColor {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect
  )

  $sumR = 0.0
  $sumG = 0.0
  $sumB = 0.0
  $count = 0.0
  for ($x = $Rect.Left; $x -lt [Math]::Min($Rect.Right, $Bitmap.Width); $x++) {
    for ($y = $Rect.Top; $y -lt [Math]::Min($Rect.Bottom, $Bitmap.Height); $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      $sumR += $pixel.R
      $sumG += $pixel.G
      $sumB += $pixel.B
      $count += 1
    }
  }

  if ($count -eq 0) {
    return [System.Drawing.Color]::White
  }

  return [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($sumR / $count)),
    (Clamp-Channel ($sumG / $count)),
    (Clamp-Channel ($sumB / $count))
  )
}

function Tone-Region {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$BaseColor,
    [double]$Amount = 0.60,
    [switch]$AffectNearWhite
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8) { continue }
      if (-not $AffectNearWhite -and (Is-NearWhite $pixel)) { continue }

      $luminance = (Get-Luminance $pixel) / 255.0
      $shade = 0.30 + ((1.0 - $luminance) * 0.28)
      $target = [System.Drawing.Color]::FromArgb(
        255,
        (Clamp-Channel ($BaseColor.R * (0.90 + ($luminance * 0.10)))),
        (Clamp-Channel ($BaseColor.G * (0.90 + ($luminance * 0.10)))),
        (Clamp-Channel ($BaseColor.B * (0.90 + ($luminance * 0.10))))
      )
      $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $target ($Amount + $shade * 0.12)))
    }
  }
}

function Shade-Vertical {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$TopColor,
    [System.Drawing.Color]$BottomColor,
    [double]$Amount = 0.42
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $t = ($y - $Rect.Top) / [double]([Math]::Max(1, $Rect.Height))
      $target = Mix-Color $TopColor $BottomColor $t
      $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $target $Amount))
    }
  }
}

function Add-HairHighlights {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$HighlightColor,
    [double]$Amount = 0.24
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $rx = ($x - $Rect.Left) / [double]([Math]::Max(1, $Rect.Width))
      $ry = ($y - $Rect.Top) / [double]([Math]::Max(1, $Rect.Height))
      $band = [Math]::Abs(($rx * 0.78 + $ry * 0.38) - 0.34)
      if ($band -lt 0.045) {
        $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $HighlightColor ($Amount + ((0.045 - $band) * 2.2))))
      }
    }
  }
}

function Fill-RegionColor {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$Color,
    [double]$Amount = 0.74,
    [switch]$AffectNearWhite
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8) { continue }
      if (-not $AffectNearWhite -and (Is-NearWhite $pixel)) { continue }
      $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $Color $Amount))
    }
  }
}

function Draw-SoftBlush {
  param(
    [System.Drawing.Bitmap]$Bitmap,
    [System.Drawing.Rectangle]$Rect,
    [System.Drawing.Color]$Color
  )

  for ($x = $Rect.Left; $x -lt $Rect.Right; $x++) {
    for ($y = $Rect.Top; $y -lt $Rect.Bottom; $y++) {
      $pixel = $Bitmap.GetPixel($x, $y)
      if ($pixel.A -lt 8 -or (Is-NearWhite $pixel)) { continue }

      $rx = (($x - $Rect.Left) / [double]([Math]::Max(1, $Rect.Width))) - 0.5
      $ry = (($y - $Rect.Top) / [double]([Math]::Max(1, $Rect.Height))) - 0.5
      $distance = [Math]::Sqrt(($rx * $rx * 2.2) + ($ry * $ry))
      if ($distance -lt 0.48) {
        $amount = (0.48 - $distance) * 0.44
        $Bitmap.SetPixel($x, $y, (Mix-Color $pixel $Color $amount))
      }
    }
  }
}

function Save-Png {
  param([System.Drawing.Bitmap]$Bitmap, [string]$Path)
  $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
}

$root = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $root "haru_greeter_pro_jp\haru_greeter_pro_jp\runtime\haru_greeter_t05.2048\texture_00.png"
$targetPath = Join-Path $root "haru_greeter_pro_jp\haru_greeter_pro_jp\runtime\haru_greeter_t05.2048\texture_00_zenportrait.png"
$portraitPath = Join-Path $root "anh2.jpg"
$modelSource = Join-Path $root "haru_greeter_pro_jp\haru_greeter_pro_jp\runtime\haru_greeter_t05_inspired.model3.json"
$modelTarget = Join-Path $root "haru_greeter_pro_jp\haru_greeter_pro_jp\runtime\haru_greeter_t05_zenportrait.model3.json"

$portrait = [System.Drawing.Bitmap]::FromFile($portraitPath)
$source = [System.Drawing.Bitmap]::FromFile($sourcePath)
$output = New-Object System.Drawing.Bitmap($source)

try {
  $skinBase = Get-AverageColor -Bitmap $portrait -Rect (New-Object System.Drawing.Rectangle(
    [int]($portrait.Width * 0.36),
    [int]($portrait.Height * 0.22),
    [int]($portrait.Width * 0.22),
    [int]($portrait.Height * 0.20)
  ))
  $hairBase = Get-AverageColor -Bitmap $portrait -Rect (New-Object System.Drawing.Rectangle(
    [int]($portrait.Width * 0.28),
    [int]($portrait.Height * 0.04),
    [int]($portrait.Width * 0.32),
    [int]($portrait.Height * 0.18)
  ))
  $lipBase = Get-AverageColor -Bitmap $portrait -Rect (New-Object System.Drawing.Rectangle(
    [int]($portrait.Width * 0.42),
    [int]($portrait.Height * 0.49),
    [int]($portrait.Width * 0.10),
    [int]($portrait.Height * 0.05)
  ))

  $skinColor = [System.Drawing.Color]::FromArgb(255, 214, 194, 187)
  $skinShade = [System.Drawing.Color]::FromArgb(255, 197, 173, 166)
  $hairColor = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel (($hairBase.R * 0.40) + 54)),
    (Clamp-Channel (($hairBase.G * 0.40) + 38)),
    (Clamp-Channel (($hairBase.B * 0.40) + 34))
  )
  $hairDark = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($hairColor.R * 0.66)),
    (Clamp-Channel ($hairColor.G * 0.66)),
    (Clamp-Channel ($hairColor.B * 0.66))
  )
  $hairHighlight = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($hairColor.R * 1.24)),
    (Clamp-Channel ($hairColor.G * 1.20)),
    (Clamp-Channel ($hairColor.B * 1.16))
  )
  $lipColor = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel (($lipBase.R * 0.30) + 120)),
    (Clamp-Channel (($lipBase.G * 0.30) + 80)),
    (Clamp-Channel (($lipBase.B * 0.30) + 92))
  )
  $browColor = [System.Drawing.Color]::FromArgb(
    255,
    (Clamp-Channel ($hairDark.R * 0.88)),
    (Clamp-Channel ($hairDark.G * 0.78)),
    (Clamp-Channel ($hairDark.B * 0.78))
  )

  $faceRect = New-Object System.Drawing.Rectangle(1178, 25, 435, 527)
  $frontHairRect = New-Object System.Drawing.Rectangle(738, 22, 403, 384)
  $backHairRect = New-Object System.Drawing.Rectangle(665, 411, 535, 623)
  $sideHairLeftRect = New-Object System.Drawing.Rectangle(654, 1018, 160, 305)
  $sideHairRightRect = New-Object System.Drawing.Rectangle(1055, 1019, 145, 305)
  $neckRect = New-Object System.Drawing.Rectangle(761, 1092, 344, 489)
  $browLeftRect = New-Object System.Drawing.Rectangle(1235, 990, 138, 26)
  $browRightRect = New-Object System.Drawing.Rectangle(1431, 987, 138, 26)
  $eyeLeftRect = New-Object System.Drawing.Rectangle(1243, 1050, 130, 44)
  $eyeRightRect = New-Object System.Drawing.Rectangle(1434, 1054, 130, 45)
  $pupilLeftRect = New-Object System.Drawing.Rectangle(1281, 1085, 31, 54)
  $pupilRightRect = New-Object System.Drawing.Rectangle(1497, 1089, 33, 54)
  $mouthRect = New-Object System.Drawing.Rectangle(1219, 818, 130, 68)
  $noseRect = New-Object System.Drawing.Rectangle(1380, 829, 54, 57)
  $hohoRect = New-Object System.Drawing.Rectangle(1135, 1638, 480, 180)

  Tone-Region -Bitmap $output -Rect $frontHairRect -BaseColor $hairColor -Amount 0.66
  Tone-Region -Bitmap $output -Rect $backHairRect -BaseColor $hairColor -Amount 0.68
  Tone-Region -Bitmap $output -Rect $sideHairLeftRect -BaseColor $hairColor -Amount 0.68
  Tone-Region -Bitmap $output -Rect $sideHairRightRect -BaseColor $hairColor -Amount 0.68

  Shade-Vertical -Bitmap $output -Rect $frontHairRect -TopColor $hairDark -BottomColor $hairColor -Amount 0.30
  Shade-Vertical -Bitmap $output -Rect $backHairRect -TopColor $hairColor -BottomColor $hairDark -Amount 0.18
  Add-HairHighlights -Bitmap $output -Rect $frontHairRect -HighlightColor $hairHighlight -Amount 0.26
  Add-HairHighlights -Bitmap $output -Rect $backHairRect -HighlightColor $hairHighlight -Amount 0.20
  Add-HairHighlights -Bitmap $output -Rect $sideHairLeftRect -HighlightColor $hairHighlight -Amount 0.18
  Add-HairHighlights -Bitmap $output -Rect $sideHairRightRect -HighlightColor $hairHighlight -Amount 0.18

  Fill-RegionColor -Bitmap $output -Rect $faceRect -Color $skinColor -Amount 0.30 -AffectNearWhite
  Shade-Vertical -Bitmap $output -Rect $faceRect -TopColor $skinColor -BottomColor $skinShade -Amount 0.22
  Fill-RegionColor -Bitmap $output -Rect $neckRect -Color $skinColor -Amount 0.18 -AffectNearWhite

  Draw-SoftBlush -Bitmap $output -Rect (New-Object System.Drawing.Rectangle(1210, 200, 105, 90)) -Color ([System.Drawing.Color]::FromArgb(255, 227, 166, 170))
  Draw-SoftBlush -Bitmap $output -Rect (New-Object System.Drawing.Rectangle(1485, 200, 105, 90)) -Color ([System.Drawing.Color]::FromArgb(255, 227, 166, 170))

  Fill-RegionColor -Bitmap $output -Rect $mouthRect -Color $lipColor -Amount 0.80
  Fill-RegionColor -Bitmap $output -Rect $noseRect -Color ([System.Drawing.Color]::FromArgb(255, 194, 145, 150)) -Amount 0.40
  Fill-RegionColor -Bitmap $output -Rect $browLeftRect -Color $browColor -Amount 0.86
  Fill-RegionColor -Bitmap $output -Rect $browRightRect -Color $browColor -Amount 0.86
  Fill-RegionColor -Bitmap $output -Rect $eyeLeftRect -Color ([System.Drawing.Color]::FromArgb(255, 84, 36, 44)) -Amount 0.70
  Fill-RegionColor -Bitmap $output -Rect $eyeRightRect -Color ([System.Drawing.Color]::FromArgb(255, 84, 36, 44)) -Amount 0.70
  Fill-RegionColor -Bitmap $output -Rect $pupilLeftRect -Color ([System.Drawing.Color]::FromArgb(255, 40, 24, 20)) -Amount 0.85
  Fill-RegionColor -Bitmap $output -Rect $pupilRightRect -Color ([System.Drawing.Color]::FromArgb(255, 40, 24, 20)) -Amount 0.85
  Fill-RegionColor -Bitmap $output -Rect $hohoRect -Color ([System.Drawing.Color]::FromArgb(255, 238, 195, 196)) -Amount 0.18

  Save-Png -Bitmap $output -Path $targetPath

  $modelJson = Get-Content -LiteralPath $modelSource -Raw
  $modelJson = $modelJson -replace 'haru_greeter_t05\.2048/texture_00_inspired\.png\?v=20260406-inspired-v2', 'haru_greeter_t05.2048/texture_00_zenportrait.png?v=20260508-zenportrait-v1'
  Set-Content -LiteralPath $modelTarget -Value $modelJson
}
finally {
  $portrait.Dispose()
  $source.Dispose()
  $output.Dispose()
}
