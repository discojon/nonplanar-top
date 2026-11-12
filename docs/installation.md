# Installation

## Windows (recommended path)

### 1. Install Python
Download Python 3.10 or newer from <https://www.python.org/downloads/>. In the installer, tick **Add python.exe to PATH**.

### 2. Run the installer
Download the latest zip from [Releases](https://github.com/discojon/nonplanar-top/releases), unzip it and double-click **`install_windows.bat`**. It:

- installs `numpy`, `scipy`, `shapely` and `opencv-python`
- copies `nonplanar_top.py` and `nonplanar_top.ini` to `C:\PrusaTools\nonplanar\` (an existing `.ini` is kept)
- prints the post-processing line for PrusaSlicer and copies it to your clipboard

### 3. Measure your shroud
Follow [Measuring your toolhead](measuring.md) and put the number in `C:\PrusaTools\nonplanar\nonplanar_top.ini`:

```ini
shroud_height_mm = 2.4
```

### 4. Add the script to PrusaSlicer
1. Switch PrusaSlicer to **Expert** mode.
2. **Print Settings > Output options > Post-processing scripts**: paste the line from the installer. It looks like:
   ```
   "C:\Users\you\AppData\Local\Programs\Python\Python312\python.exe" "C:\PrusaTools\nonplanar\nonplanar_top.py"
   ```
   One line, with the quotes, and no semicolon at the end.

### 5. Make a print profile that switches it on
1. Still in Print Settings, open **Notes** and type: `nonplanar`
2. Save the profile under a new name, for example `0.20mm NONPLANAR @COREONEINDX`.

The script does nothing for print profiles without that word, so your normal profiles are unaffected.

**Shortcut:** `profiles/NONPLANAR_print_profile.ini` is a config bundle with all of this. Edit its `post_process` line to match your paths, then **File > Import > Import Config Bundle**.

### 6. Slice and export
Export as usual (to a file, USB or PrusaLink).

- Converted files start with a line like `; nonplanar_top 0.2.0: 1 region(s) smoothed, ...`
- **Binary G-code:** if your printer profile exports `.bgcode`, the converted file is saved as plain `.gcode` instead. The Core One prints both.
- PrusaSlicer's normal preview shows the file *before* conversion. Open the exported file with **File > G-code preview** to see the skin.
- A log of the last run is written next to the script: `nonplanar_top_last.log`.

## Manual installation (any OS)

```
pip install numpy scipy shapely opencv-python
```

Put `nonplanar_top.py` and `nonplanar_top.ini` in one folder, then add to PrusaSlicer's post-processing scripts:

- **macOS:** `/usr/local/bin/python3 /Users/you/PrusaTools/nonplanar_top.py` (use `which python3` for your path)
- **Linux:** `/usr/bin/python3 /home/you/PrusaTools/nonplanar_top.py`

The script writes its log next to itself, so pick a folder you can write to.

## Updating
Replace `nonplanar_top.py` with the new version. Keep your `nonplanar_top.ini`; new settings fall back to built-in defaults.

## Uninstalling
Remove the line from Post-processing scripts (or just use a print profile without `nonplanar` in its notes) and delete `C:\PrusaTools\nonplanar`.
