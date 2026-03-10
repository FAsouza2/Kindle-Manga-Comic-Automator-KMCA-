# Manga Chapter to Volume Converter

Converts manga chapters organized in separate folders into consolidated volume-based CBZ archives for digital reading.

## Overview

This script automates the process of converting manga downloads organized by chapter into volume-based CBZ files, which are the standard format for digital comic/manga readers.

### What it does:

1. **Scans** your manga directory for chapter folders
2. **Renames** images to prevent conflicts during consolidation
3. **Consolidates** chapters into volume directories
4. **Renumbers** images sequentially within each volume
5. **Creates** CBZ archives (one per volume)
6. **Cleans up** temporary directories

## Requirements

- **Python 3.8+** (no external dependencies required)
- Standard library modules only: `pathlib`, `zipfile`, `re`, `shutil`, `argparse`, `logging`

## Expected Directory Structure

Your manga directory should follow this naming pattern:

```
Manga_Name/
├── Vol.01 Ch.0001 - Chapter Title (pt-br) [Group Name]/
│   ├── 01.jpg
│   ├── 02.jpg
│   ├── 03.jpg
│   └── ...
├── Vol.01 Ch.0002 - Another Chapter/
│   ├── 01.jpg
│   ├── 02.jpg
│   └── ...
├── Vol.02 Ch.0006 - Different Volume/
│   ├── 01.jpg
│   └── ...
└── ...
```

**Pattern**: `Vol.XX Ch.YYYY - Title`

- Volume number: 2 digits (e.g., `Vol.01`, `Vol.12`)
- Chapter number: 3+ digits (e.g., `Ch.0001`, `Ch.0123`)
- Title portion is ignored (can contain any characters)

## Installation

1. Download `manga_chapter_to_volume_converter.py`
2. Make it executable (optional):
   ```bash
   chmod +x manga_chapter_to_volume_converter.py
   ```

## Usage

### Basic Workflow

**IMPORTANT**: Always backup your data before running!

1. **Dry-run first** (preview changes without modifying files):
   ```bash
   python manga_chapter_to_volume_converter.py /path/to/manga --dry-run
   ```

2. **Review the output** to ensure it looks correct

3. **Execute with confirm flag**:
   ```bash
   python manga_chapter_to_volume_converter.py /path/to/manga --confirm
   ```

### Command-Line Options

```
usage: manga_chapter_to_volume_converter.py [-h] [--dry-run] [--confirm] [--verbose] [--version] target_dir

positional arguments:
  target_dir     Path to manga directory containing chapter folders

optional arguments:
  -h, --help     show this help message and exit
  --dry-run      Preview changes without modifying files
  --confirm      Confirm execution (required for actual changes)
  --verbose, -v  Show detailed file-by-file operations
  --version      show program's version number and exit
```

### Examples

#### Preview changes (dry-run):
```bash
python manga_chapter_to_volume_converter.py ~/Downloads/Tsugumomo --dry-run
```

#### Execute conversion:
```bash
python manga_chapter_to_volume_converter.py ~/Downloads/Tsugumomo --confirm
```

#### Execute with verbose output:
```bash
python manga_chapter_to_volume_converter.py ~/Downloads/Tsugumomo --confirm --verbose
```

## Output

After successful execution, your directory will contain:

```
Manga_Name/
├── Volume 01.cbz
├── Volume 02.cbz
├── Volume 03.cbz
└── ...
```

All original chapter folders will be deleted, and only the CBZ files remain.

## Processing Details

### Phase 1: Scan & Parse
- Lists all subdirectories
- Extracts volume/chapter numbers using regex
- Validates folder names match expected pattern
- Reports invalid folders (will be skipped)

### Phase 2: Rename Images
- Filters for valid image extensions (`.jpg`, `.jpeg`, `.png`, `.webp`)
- Ignores system files (`.DS_Store`, `Thumbs.db`)
- Renames images to temporary format: `V{vol}C{ch}I{img}.ext`
- Example: `01.jpg` in `Vol.01 Ch.0001` → `V01C001I01.jpg`

### Phase 3: Consolidate Volumes
- Creates `Volume XX/` directories
- Moves all chapter images to corresponding volume directory
- Verifies image counts before/after move
- Deletes empty chapter directories

### Phase 4: Finalize & Archive
- Sorts images naturally (numeric-aware: V01C001I2 comes before V01C001I10)
- Renumbers sequentially: `01.jpg`, `02.jpg`, `03.jpg`...
- Zero-padding adjusts to image count (<100: 2 digits, <1000: 3 digits, etc.)
- Creates CBZ archive (ZIP with DEFLATE compression level 6)
- Validates archive integrity
- Moves CBZ to root directory
- Deletes volume directory

## Safety Features

- **Dry-run mode**: Preview all changes before executing
- **Confirmation required**: Must use `--confirm` to make actual changes
- **Validation checks**: Verifies image counts at each step
- **Existing file detection**: Prompts before overwriting existing CBZ files
- **Error handling**: Graceful failures with clear error messages
- **Interruption handling**: CTRL+C provides guidance on cleanup

## Troubleshooting

### "No valid chapter folders found"
- Ensure folder names follow pattern: `Vol.XX Ch.YYYY - Title`
- Check that volume/chapter numbers are numeric

### "Permission denied" errors
- Ensure you have read/write permissions on the directory
- On macOS, you may need to grant Terminal full disk access

### "Image count mismatch"
- This indicates a failed move operation
- Check disk space availability
- Re-run with `--verbose` to identify which files failed

### "CBZ file already exists"
- The script will prompt you to overwrite or skip
- Use dry-run mode first to avoid this situation

### Folders with non-standard names
- The script will list invalid folders and ask if you want to continue
- Invalid folders will be skipped (not processed)

## Supported Image Formats

- `.jpg` / `.jpeg` (most common)
- `.png`
- `.webp`

## CBZ Format

CBZ is essentially a ZIP archive with a `.cbz` extension containing sequential images. It's supported by most comic/manga readers including:

- **Desktop**: Calibre, CDisplay Ex, YACReader, ComicRack
- **Mobile**: Tachiyomi, Perfect Viewer, CDisplayEx
- **Kindle**: Can be converted using Kindle Comic Converter

## Technical Details

- **Language**: Python 3.8+
- **Compression**: ZIP DEFLATE (level 6)
- **Natural sorting**: Numeric-aware sorting ensures correct image order
- **Two-phase rename**: Prevents filename collisions during sequential renumbering
- **Atomic operations**: File operations are atomic at filesystem level

## Limitations

- Only processes folders matching `Vol.XX Ch.YYYY` pattern
- Images must have numeric filenames (e.g., `01.jpg`, `042.png`)
- No support for nested subdirectories within chapter folders
- No image editing/optimization (resize, format conversion)

## Before/After Example

**Before**:
```
Tsugumomo/
├── Vol.01 Ch.0001 - Lembranças da Mamãe/
│   ├── 01.jpg (45 images)
├── Vol.01 Ch.0002 - Mestre/
│   ├── 01.jpg (38 images)
├── Vol.02 Ch.0006 - Braço de Ferro/
│   ├── 01.jpg (42 images)
└── ...
```

**After**:
```
Tsugumomo/
├── Volume 01.cbz (83 images: Ch.0001 + Ch.0002)
├── Volume 02.cbz (42 images: Ch.0006)
└── ...
```

## License

Generated with Claude Code. Free to use and modify.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run with `--verbose` flag for detailed logs
3. Ensure you're using Python 3.8 or higher
