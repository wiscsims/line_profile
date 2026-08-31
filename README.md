# Line Profile

A QGIS plugin for creating line profiles from vector and raster layers.

## Contents

- [Contents](#contents)
- [Requirement](#requirement)
- [Installation](#installation)
  - [Install from QGIS Plugin Repository](#install-from-qgis-plugin-repository)
  - [Install from ZIP file](#install-from-zip-file)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Creating Line Profiles](#creating-line-profiles)
  - [Plot Options](#plot-options)
  - [Profile Lines](#profile-lines)
  - [Tieline](#tieline)
  - [Tracking Marker](#tracking-marker)
  - [Peak / Valley Detection](#peak--valley-detection)
  - [Save Plot](#save-plot)
- [Options](#options)
  - [Export Data](#export-data)
  - [Import/Export Profile Line](#import/export-profile-line)
  - [Scaling](#scaling)
- [Manual QGIS Test](#manual-qgis-test)
- [Developmental Features](#developmental-features)
  - [Checking sampling points and area visually](#checking-sampling-points-and-area-visually)
  - [Normalize to `Profile Line 1`](#normalize-to-`profile-line-1`)
    - [By length](#by-length)
    - [By segment](#by-segment)

## Requirement

- QGIS 3.10 or newer. The plugin metadata declares the same minimum version.

For `QGIS 2` users, use [older version]('htts://github.com/saburo/LineProfile_QGIS2').

## Installation

There are two ways to install `Line Profile`.

### Install from QGIS Plugin Repository

1. Open QGIS.

2. From the QGIS menu, select `Plugins` > `Manege and Install Plugins`.
   <a href="img/readme/plugin_install_menu.png" target="_blank"><img src="img/readme/plugin_install_menu.png" width="500" alt=""></a>

3. Select the `All` tab on the far left. Search/find `Line Profile` from the plugin list and click `Install Plugin` button on the right bottom of `Manege and Install Plugins` window.
   <a href="img/readme/plugin_install.png" target="_blank"><img src="img/readme/plugin_install.png" width="600" alt="Install Line Profile from the list"></a>

4. Select `Installed Plugins` to make sure `Line Profile` was correctly installed. If it is not checked, click the checkbox (on the left of green puzzle piece icon) to activate the plugin. You also see `Line Profile` icon in the QGIS toolbar.

### Install from ZIP file

Manual installation is also available.

1. Download `Line Profile` (line_profile.zip) from [WiscSIMS GitHub repository](https://github.com/wiscsims/line_profile/releases/latest).

2. Open QGIS.

3. From the QGIS menu, select `Plugins` > `Manege and Install Plugins`.
   <a href="img/readme/plugin_install_menu.png" target="_blank"><img src="img/readme/plugin_install_menu.png" width="500" alt=""></a>

4. Select `Intall from ZIP` and hit `...` button to select downloaded `line_profile.zip` file.
   <a href="img/readme/plugin_install_zip.png" target="_blank"><img src="img/readme/plugin_install_zip.png" width="600" alt="Install Line Profile from zip file"></a>

5. Hit `Install Plugin` to install `Line Profile`.
6. Select `Installed Plugins` to make sure `Line Profile` was correctly installed. You also see `Line Profile` icon in the QGIS toolbar.

## Quick Start

- Select a layer from the layer panel.
- Hit `Add Data` button, then choose an item you want to plot.
- Make a profile line with:
  - Click on canvas to start your profile line (circle marker: ●).
  - You can add vertics by clicking on canvas (●).
  - Right click on canvas to terminate the profile line (square marker: ■).
- Done! 🎉 - The line profile is generated automatically.

## Usage

### Creating Line Profiles

You can create profile lines with clicking on canvas.

- **Start profile line/Create vertics**: `Left Click`
- **Terminate profile line**: `Right Click`
- **Cancel/Clear profile line**: `Double Click`

### Plot Options

- #### Raster Layer

  TBU

- #### Vector Layers

  TBU

### Profile Lines

There are two profile lines (<span style="color:red;">Profile Line 1</span> and <span style="color:blue;">Profile Line 2</span>).

### Tieline

A thin yellow line indicating where the each data point in the vector layer is projected on the profile line. `Default: On`.

### Tracking Marker

A marker on the profile line indicating the location of the data in the plot. `Default: Off`.

### Peak / Valley Detection

Select a plotted raster profile, then use **Auto Detect** to find peaks and valleys or use **+ Peak**, **+ Valley**, and **Delete** to curate points directly on the plot. Manual additions snap to a local extremum within the configured sample range. Points are synchronized with temporary map markers and can be exported to a QGIS memory point layer.

Automatic detection uses SciPy. SciPy is optional and is loaded only when **Auto Detect** is requested. If it is unavailable, Line Profile asks before installing it into the active QGIS user's `python/dependencies` directory; manual editing remains available without SciPy.

### Save Plot

Plots can be saved as raster or vector file with various format (jpg, png, pdf, svg).

## Options

You can export data and profile line, and import profile line

### Export Data

Data used in the plot can be exported as text data with csv format.

### Import/Export Profile Line

TBU

### Scaling

Pixel size (px/map unit) can be set manually. You can also import alignment files which you used in WiscSIMS session to set pixel size. For non-square raster pixels, full-resolution sampling uses the finer of the raster X/Y resolutions so the profile is not undersampled.

Profile lines are also exportable as shape file. You can reproduce the profile line and plots.

## Manual QGIS Test

On macOS with QGIS installed in `/Applications/QGIS.app`, run:

```sh
tests/run_qgis_manual_test.sh
```

The launcher uses an isolated QGIS profile under `/private/tmp`, loads this working tree directly, and creates a sample raster, vector points, and a horizontal profile. Use **Auto Detect**, the manual point tools, **Clear Auto**, and **Create Point Layer** to exercise the complete peak/valley workflow without changing the normal QGIS profile.

## Developmental Features

### Checking sampling points and area visually

_Heavy processing, though._

- as a shaded area
- as points

<!-- ### Normalize to `Profile Line 1` -->

### Normalization of profile lines

Select checkbox if you want to normalize the Profile Line 2 to Profile Line 1.

#### By length

The length of profile line 2 is normalized by the `Profile Line 1`

#### By segment

This option needs profile lines which have same number of segments.
