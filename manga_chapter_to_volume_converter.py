#!/usr/bin/env python3
"""
Manga Chapter to Volume Converter
==================================

Converts manga chapters organized in separate folders into consolidated
volume-based CBZ archives for digital reading.

Processes manga directories with the structure:
    Vol.XX Ch.YYYY - Title/
        01.jpg
        02.jpg
        ...

Generates:
    Volume 01.cbz
    Volume 02.cbz
    ...

Author: Generated with Claude Code
Version: 1.0.0
Python: 3.8+
"""

import sys
import re
import argparse
import logging
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


# ============================================================================
# CONSTANTS
# ============================================================================

VERSION = "1.0.0"

# Regex pattern to extract volume and chapter from folder names
# Matches: "Vol.01 Ch.0001 - Title..." -> volume=1, chapter=1
CHAPTER_FOLDER_PATTERN = re.compile(r'Vol\.(\d+)\s+Ch\.(\d+)')

# Valid image file extensions (case-insensitive)
VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# System files to ignore
IGNORED_FILES = {'.DS_Store', 'Thumbs.db', '._.DS_Store', 'desktop.ini'}

# ZIP compression settings
ZIP_COMPRESSION_TYPE = zipfile.ZIP_DEFLATED
ZIP_COMPRESSION_LEVEL = 6


# ============================================================================
# LOGGING SETUP
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for different log levels."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[34m',      # Blue
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'SUCCESS': '\033[32m',   # Green
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color based on level
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"

        # Handle SUCCESS level (custom)
        if hasattr(record, 'success') and record.success:
            record.msg = f"{self.COLORS['SUCCESS']}{record.msg}{self.RESET}"

        return super().format(record)


def setup_logging(verbose: bool = False):
    """Configure logging with colored output and verbosity levels."""
    level = logging.DEBUG if verbose else logging.INFO

    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        fmt='%(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def log_success(message: str):
    """Log a success message with green color."""
    logger = logging.getLogger()
    record = logger.makeRecord(
        logger.name, logging.INFO, '', 0, message, (), None
    )
    record.success = True
    logger.handle(record)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ChapterInfo:
    """Metadata for a manga chapter folder."""
    volume: int
    chapter: int
    folder_path: Path
    folder_name: str

    def __repr__(self):
        return f"Vol.{self.volume:02d} Ch.{self.chapter:03d}"


# ============================================================================
# ARGUMENT PARSING
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Setup and parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Convert manga chapters to volume-based CBZ archives.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run (preview without changes)
  %(prog)s /path/to/manga --dry-run

  # Execute conversion
  %(prog)s /path/to/manga --confirm

  # Verbose output
  %(prog)s /path/to/manga --confirm --verbose

Recommended Workflow:
  1. Backup your manga directory
  2. Run with --dry-run to preview changes
  3. Run with --confirm to execute
  4. Verify CBZ files in a comic reader

Expected Directory Structure:
  Manga/
    Vol.01 Ch.0001 - Chapter Title/
      01.jpg, 02.jpg, ...
    Vol.01 Ch.0002 - Chapter Title/
      01.jpg, 02.jpg, ...
    Vol.02 Ch.0003 - Chapter Title/
      01.jpg, 02.jpg, ...
        """
    )

    parser.add_argument(
        'target_dir',
        type=str,
        help='Path to manga directory containing chapter folders'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )

    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirm execution (required for actual changes)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed file-by-file operations'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}'
    )

    return parser.parse_args()


# ============================================================================
# PHASE 1: SCAN & PARSE
# ============================================================================

def scan_directory(target_dir: Path) -> List[Path]:
    """
    List all subdirectories in the target directory.

    Args:
        target_dir: Path to the manga directory

    Returns:
        List of subdirectory paths
    """
    logger = logging.getLogger()
    logger.debug(f"Scanning directory: {target_dir}")

    subdirs = [item for item in target_dir.iterdir() if item.is_dir()]
    logger.info(f"Found {len(subdirs)} subdirectories")

    return subdirs


def parse_chapter_folder(folder_path: Path) -> Optional[ChapterInfo]:
    """
    Parse chapter folder name to extract volume and chapter numbers.

    Args:
        folder_path: Path to the chapter folder

    Returns:
        ChapterInfo object if valid, None if doesn't match pattern
    """
    folder_name = folder_path.name
    match = CHAPTER_FOLDER_PATTERN.search(folder_name)

    if not match:
        return None

    volume = int(match.group(1))
    chapter = int(match.group(2))

    return ChapterInfo(
        volume=volume,
        chapter=chapter,
        folder_path=folder_path,
        folder_name=folder_name
    )


def validate_structure(chapters: List[ChapterInfo], all_folders: List[Path]) -> bool:
    """
    Validate directory structure and report invalid folders.

    Args:
        chapters: List of successfully parsed chapter info
        all_folders: List of all subdirectories found

    Returns:
        True if validation passes, False otherwise
    """
    logger = logging.getLogger()

    # Find folders that didn't match the pattern
    parsed_paths = {ch.folder_path for ch in chapters}
    invalid_folders = [f for f in all_folders if f not in parsed_paths]

    if invalid_folders:
        logger.warning(f"Found {len(invalid_folders)} folder(s) that don't match expected pattern:")
        for folder in invalid_folders:
            logger.warning(f"  - {folder.name}")
        logger.warning("These folders will be skipped.")
        logger.warning("Expected pattern: 'Vol.XX Ch.YYYY - Title'")

        # Ask user if they want to continue
        response = input("\nContinue processing valid folders? (y/n): ")
        if response.lower() != 'y':
            logger.info("Processing aborted by user")
            return False

    if not chapters:
        logger.error("No valid chapter folders found!")
        logger.error("Expected pattern: 'Vol.XX Ch.YYYY - Title'")
        return False

    logger.info(f"Validated {len(chapters)} chapter folder(s)")
    return True


def group_chapters_by_volume(chapters: List[ChapterInfo]) -> Dict[int, List[ChapterInfo]]:
    """
    Group chapters by their volume number.

    Args:
        chapters: List of chapter info

    Returns:
        Dictionary mapping volume number to list of chapters
    """
    logger = logging.getLogger()

    volumes = defaultdict(list)
    for chapter in chapters:
        volumes[chapter.volume].append(chapter)

    # Sort chapters within each volume
    for volume_num in volumes:
        volumes[volume_num].sort(key=lambda ch: ch.chapter)

    logger.info(f"Found {len(volumes)} volume(s): {sorted(volumes.keys())}")

    # Log volume details
    for volume_num in sorted(volumes.keys()):
        chapter_list = volumes[volume_num]
        logger.debug(
            f"  Volume {volume_num:02d}: {len(chapter_list)} chapter(s) "
            f"(Ch.{chapter_list[0].chapter:03d} - Ch.{chapter_list[-1].chapter:03d})"
        )

    return dict(volumes)


# ============================================================================
# PHASE 2: RENAME IMAGES
# ============================================================================

def get_image_files(folder_path: Path) -> List[Path]:
    """
    Get all valid image files from a folder, filtering by extension.

    Args:
        folder_path: Path to the folder to scan

    Returns:
        List of image file paths
    """
    logger = logging.getLogger()

    image_files = []
    for file_path in folder_path.iterdir():
        # Skip if not a file
        if not file_path.is_file():
            continue

        # Skip system/hidden files
        if file_path.name in IGNORED_FILES or file_path.name.startswith('.'):
            logger.debug(f"Ignoring system file: {file_path.name}")
            continue

        # Check if extension is valid (case-insensitive)
        if file_path.suffix.lower() in VALID_IMAGE_EXTENSIONS:
            image_files.append(file_path)
        else:
            logger.debug(f"Ignoring non-image file: {file_path.name}")

    return image_files


def validate_numeric_filename(file_path: Path) -> bool:
    """
    Check if the base filename (without extension) is numeric.

    Args:
        file_path: Path to the file

    Returns:
        True if filename is numeric, False otherwise
    """
    base_name = file_path.stem  # filename without extension
    return base_name.isdigit()


def rename_image_to_temp_format(
    file_path: Path,
    volume: int,
    chapter: int,
    dry_run: bool = False
) -> Optional[Path]:
    """
    Rename image file to temporary format V{vol}C{ch}I{img}.ext

    Args:
        file_path: Path to the image file
        volume: Volume number
        chapter: Chapter number
        dry_run: If True, only log what would happen

    Returns:
        New file path if successful, None if skipped
    """
    logger = logging.getLogger()

    # Validate filename is numeric
    if not validate_numeric_filename(file_path):
        logger.warning(f"Non-numeric filename detected: {file_path.name} - skipping")
        return None

    # Get original image number and extension
    original_num = file_path.stem
    extension = file_path.suffix  # Preserve case-sensitive extension

    # Format: V{vol:02d}C{ch:03d}I{img}.ext
    # Volume: 2 digits, Chapter: 3 digits, Image: preserve original
    new_name = f"V{volume:02d}C{chapter:03d}I{original_num}{extension}"
    new_path = file_path.parent / new_name

    if dry_run:
        logger.info(f"  Would rename: {file_path.name} → {new_name}")
        return new_path

    try:
        file_path.rename(new_path)
        logger.debug(f"  Renamed: {file_path.name} → {new_name}")
        return new_path
    except PermissionError as e:
        logger.error(f"Permission denied renaming {file_path.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error renaming {file_path.name}: {e}")
        return None


def rename_chapter_images(
    chapter: ChapterInfo,
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """
    Rename all images in a chapter folder to temporary format.

    Args:
        chapter: Chapter information
        dry_run: If True, only preview changes
        verbose: If True, show detailed logging

    Returns:
        Number of images successfully renamed
    """
    logger = logging.getLogger()

    image_files = get_image_files(chapter.folder_path)

    if not image_files:
        logger.warning(f"No image files found in {chapter.folder_name}")
        return 0

    if verbose or dry_run:
        action = "Would rename" if dry_run else "Renaming"
        logger.info(f"{action} {len(image_files)} images in {chapter}")

    renamed_count = 0
    for image_file in image_files:
        result = rename_image_to_temp_format(
            image_file,
            chapter.volume,
            chapter.chapter,
            dry_run=dry_run
        )
        if result:
            renamed_count += 1

    return renamed_count


# ============================================================================
# PHASE 3: CONSOLIDATE VOLUMES
# ============================================================================

def create_volume_directories(
    target_dir: Path,
    volume_numbers: List[int],
    dry_run: bool = False
) -> Dict[int, Path]:
    """
    Create "Volume XX/" directories for each volume.

    Args:
        target_dir: Parent directory where volume folders will be created
        volume_numbers: List of volume numbers to create
        dry_run: If True, only preview changes

    Returns:
        Dictionary mapping volume number to volume directory path
    """
    logger = logging.getLogger()

    volume_dirs = {}

    for vol_num in sorted(volume_numbers):
        volume_dir_name = f"Volume {vol_num:02d}"
        volume_dir = target_dir / volume_dir_name

        if volume_dir.exists():
            logger.warning(f"Volume directory already exists: {volume_dir_name}")
        else:
            if dry_run:
                logger.info(f"  Would create: {volume_dir_name}/")
            else:
                volume_dir.mkdir(exist_ok=True)
                logger.debug(f"  Created: {volume_dir_name}/")

        volume_dirs[vol_num] = volume_dir

    return volume_dirs


def move_images_to_volume(
    chapter: ChapterInfo,
    volume_dir: Path,
    dry_run: bool = False,
    verbose: bool = False
) -> Tuple[int, int]:
    """
    Move renamed images from chapter folder to volume directory.

    Args:
        chapter: Chapter information
        volume_dir: Target volume directory
        dry_run: If True, only preview changes
        verbose: If True, show detailed logging

    Returns:
        Tuple of (images_moved, images_failed)
    """
    logger = logging.getLogger()

    # Get all files in chapter folder (should be renamed images)
    image_files = get_image_files(chapter.folder_path)

    if not image_files:
        logger.debug(f"No images to move in {chapter}")
        return (0, 0)

    moved_count = 0
    failed_count = 0

    for image_file in image_files:
        dest_path = volume_dir / image_file.name

        if dry_run:
            if verbose:
                logger.info(f"  Would move: {image_file.name} → {volume_dir.name}/")
            moved_count += 1
        else:
            try:
                # Use shutil.move to preserve modification time
                shutil.move(str(image_file), str(dest_path))
                if verbose:
                    logger.debug(f"  Moved: {image_file.name} → {volume_dir.name}/")
                moved_count += 1
            except PermissionError as e:
                logger.error(f"Permission denied moving {image_file.name}: {e}")
                failed_count += 1
            except Exception as e:
                logger.error(f"Error moving {image_file.name}: {e}")
                failed_count += 1

    return (moved_count, failed_count)


def verify_move_integrity(
    chapters: List[ChapterInfo],
    volume_dir: Path
) -> bool:
    """
    Verify that all images were successfully moved to volume directory.

    Args:
        chapters: List of chapters that should have been moved
        volume_dir: Volume directory to check

    Returns:
        True if image counts match, False otherwise
    """
    logger = logging.getLogger()

    # Count expected images from chapter folders (before move)
    expected_count = 0
    for chapter in chapters:
        expected_count += len(get_image_files(chapter.folder_path))

    # Count actual images in volume directory
    actual_count = len(get_image_files(volume_dir))

    if expected_count != actual_count:
        logger.error(
            f"Image count mismatch for {volume_dir.name}: "
            f"expected {expected_count}, found {actual_count}"
        )
        return False

    logger.debug(f"Integrity check passed: {actual_count} images in {volume_dir.name}")
    return True


def delete_chapter_directories(
    chapters: List[ChapterInfo],
    dry_run: bool = False
) -> int:
    """
    Delete chapter directories after successful move.

    Args:
        chapters: List of chapters whose directories should be deleted
        dry_run: If True, only preview changes

    Returns:
        Number of directories deleted
    """
    logger = logging.getLogger()

    deleted_count = 0

    for chapter in chapters:
        folder_path = chapter.folder_path

        # Check if directory still has files
        remaining_files = list(folder_path.iterdir())

        if remaining_files:
            # Check if only non-image files remain
            non_image_files = [
                f for f in remaining_files
                if f.is_file() and f.suffix.lower() not in VALID_IMAGE_EXTENSIONS
            ]
            if non_image_files:
                logger.warning(
                    f"Chapter folder still contains non-image files: {chapter.folder_name}"
                )
                logger.warning(f"  Files: {[f.name for f in non_image_files]}")
                continue

        if dry_run:
            logger.info(f"  Would delete: {chapter.folder_name}/")
            deleted_count += 1
        else:
            try:
                shutil.rmtree(folder_path)
                logger.debug(f"  Deleted: {chapter.folder_name}/")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting {chapter.folder_name}: {e}")

    return deleted_count


# ============================================================================
# PHASE 4: FINALIZE & ARCHIVE
# ============================================================================

def natural_sort_key(filename: str) -> Tuple:
    """
    Generate a sort key for natural (numeric-aware) sorting.

    Parses V{vol}C{ch}I{img} format and extracts numeric components.

    Args:
        filename: Filename to parse (e.g., "V01C001I042.jpg")

    Returns:
        Tuple of (volume, chapter, image_num) for sorting
    """
    # Pattern: V{vol}C{ch}I{img}.ext
    pattern = re.compile(r'V(\d+)C(\d+)I(\d+)')
    match = pattern.match(filename)

    if match:
        vol = int(match.group(1))
        ch = int(match.group(2))
        img = int(match.group(3))
        return (vol, ch, img)

    # Fallback: lexicographic sort
    return (0, 0, 0)


def sort_images_in_volume(volume_dir: Path) -> List[Path]:
    """
    Sort images in volume directory by chapter and image number.

    Args:
        volume_dir: Path to volume directory

    Returns:
        List of image paths in sorted order
    """
    image_files = get_image_files(volume_dir)

    # Sort using natural sort key (numeric-aware)
    sorted_images = sorted(image_files, key=lambda p: natural_sort_key(p.name))

    return sorted_images


def calculate_padding_width(image_count: int) -> int:
    """
    Calculate zero-padding width based on total image count.

    Args:
        image_count: Total number of images

    Returns:
        Width for zero-padding (2, 3, or 4)
    """
    if image_count < 100:
        return 2
    elif image_count < 1000:
        return 3
    else:
        return 4


def renumber_images_sequentially(
    volume_dir: Path,
    dry_run: bool = False,
    verbose: bool = False
) -> int:
    """
    Renumber images sequentially (01, 02, 03...) using two-phase rename.

    Args:
        volume_dir: Path to volume directory
        dry_run: If True, only preview changes
        verbose: If True, show detailed logging

    Returns:
        Number of images renumbered
    """
    logger = logging.getLogger()

    # Get sorted images
    sorted_images = sort_images_in_volume(volume_dir)

    if not sorted_images:
        logger.warning(f"No images found in {volume_dir.name}")
        return 0

    # Calculate padding width
    padding_width = calculate_padding_width(len(sorted_images))

    if dry_run:
        logger.info(f"  Would renumber {len(sorted_images)} images in {volume_dir.name}")
        for idx, image_file in enumerate(sorted_images, start=1):
            new_name = f"{idx:0{padding_width}d}{image_file.suffix}"
            logger.info(f"    {image_file.name} → {new_name}")
        return len(sorted_images)

    # Two-phase rename to prevent collisions
    # Phase 1: Rename to temporary names
    temp_paths = []
    for idx, image_file in enumerate(sorted_images, start=1):
        temp_name = f".tmp_{idx:0{padding_width}d}{image_file.suffix}"
        temp_path = volume_dir / temp_name

        try:
            image_file.rename(temp_path)
            temp_paths.append((temp_path, idx, image_file.suffix))
            if verbose:
                logger.debug(f"  Phase 1: {image_file.name} → {temp_name}")
        except Exception as e:
            logger.error(f"Error in phase 1 renaming {image_file.name}: {e}")
            return 0

    # Phase 2: Rename from temporary to final names
    renamed_count = 0
    for temp_path, idx, extension in temp_paths:
        final_name = f"{idx:0{padding_width}d}{extension}"
        final_path = volume_dir / final_name

        try:
            temp_path.rename(final_path)
            if verbose:
                logger.debug(f"  Phase 2: {temp_path.name} → {final_name}")
            renamed_count += 1
        except Exception as e:
            logger.error(f"Error in phase 2 renaming {temp_path.name}: {e}")

    logger.debug(f"Renumbered {renamed_count} images in {volume_dir.name}")
    return renamed_count


def create_cbz_archive(
    volume_dir: Path,
    output_dir: Path,
    dry_run: bool = False
) -> Optional[Path]:
    """
    Create CBZ archive from volume directory.

    Args:
        volume_dir: Path to volume directory containing images
        output_dir: Directory where CBZ will be created
        dry_run: If True, only preview changes

    Returns:
        Path to created CBZ file, or None if failed
    """
    logger = logging.getLogger()

    # Get sorted images
    sorted_images = sort_images_in_volume(volume_dir)

    if not sorted_images:
        logger.error(f"No images to archive in {volume_dir.name}")
        return None

    # Generate CBZ filename
    # Extract volume number from directory name "Volume XX"
    volume_num_match = re.search(r'Volume (\d+)', volume_dir.name)
    if not volume_num_match:
        logger.error(f"Cannot extract volume number from {volume_dir.name}")
        return None

    volume_num = int(volume_num_match.group(1))
    cbz_name = f"Volume {volume_num:02d}.cbz"
    cbz_path = output_dir / cbz_name

    if dry_run:
        size_mb = sum(f.stat().st_size for f in sorted_images) / (1024 * 1024)
        logger.info(f"  Would create: {cbz_name} ({len(sorted_images)} images, ~{size_mb:.1f}MB)")
        return cbz_path

    try:
        with zipfile.ZipFile(
            cbz_path,
            mode='w',
            compression=ZIP_COMPRESSION_TYPE,
            compresslevel=ZIP_COMPRESSION_LEVEL
        ) as zf:
            for image_file in sorted_images:
                # Add to archive with just the filename (no path)
                zf.write(image_file, arcname=image_file.name)

        logger.debug(f"Created CBZ: {cbz_name} ({len(sorted_images)} images)")
        return cbz_path

    except Exception as e:
        logger.error(f"Error creating CBZ {cbz_name}: {e}")
        return None


def validate_cbz_integrity(cbz_path: Path, expected_image_count: int) -> bool:
    """
    Validate that CBZ archive is readable and contains expected images.

    Args:
        cbz_path: Path to CBZ file
        expected_image_count: Expected number of images

    Returns:
        True if valid, False otherwise
    """
    logger = logging.getLogger()

    if not cbz_path.exists():
        logger.error(f"CBZ file does not exist: {cbz_path.name}")
        return False

    if cbz_path.stat().st_size == 0:
        logger.error(f"CBZ file is empty: {cbz_path.name}")
        return False

    try:
        with zipfile.ZipFile(cbz_path, mode='r') as zf:
            # Check archive integrity
            if zf.testzip() is not None:
                logger.error(f"CBZ archive is corrupted: {cbz_path.name}")
                return False

            # Count entries
            actual_count = len(zf.namelist())
            if actual_count != expected_image_count:
                logger.error(
                    f"CBZ image count mismatch: expected {expected_image_count}, "
                    f"found {actual_count}"
                )
                return False

        logger.debug(f"CBZ integrity validated: {cbz_path.name}")
        return True

    except zipfile.BadZipFile:
        logger.error(f"Invalid ZIP file: {cbz_path.name}")
        return False
    except Exception as e:
        logger.error(f"Error validating CBZ {cbz_path.name}: {e}")
        return False


def cleanup_volume_directory(volume_dir: Path, dry_run: bool = False) -> bool:
    """
    Delete volume directory after successful CBZ creation.

    Args:
        volume_dir: Path to volume directory to delete
        dry_run: If True, only preview changes

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger()

    if dry_run:
        logger.info(f"  Would delete: {volume_dir.name}/")
        return True

    try:
        shutil.rmtree(volume_dir)
        logger.debug(f"Deleted volume directory: {volume_dir.name}/")
        return True
    except Exception as e:
        logger.error(f"Error deleting {volume_dir.name}: {e}")
        return False


def check_existing_cbz(cbz_path: Path) -> bool:
    """
    Check if CBZ file already exists and prompt user for action.

    Args:
        cbz_path: Path to CBZ file

    Returns:
        True to proceed (overwrite), False to skip
    """
    logger = logging.getLogger()

    if not cbz_path.exists():
        return True

    logger.warning(f"CBZ file already exists: {cbz_path.name}")
    response = input("Overwrite? (y/n): ")

    return response.lower() == 'y'


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main entry point for the script."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    logger = setup_logging(verbose=args.verbose)

    # Display banner
    print("=" * 70)
    print(f"Manga Chapter to Volume Converter v{VERSION}")
    print("=" * 70)
    print()

    # Determine mode
    dry_run = args.dry_run
    confirm = args.confirm
    verbose = args.verbose

    # Validate execution mode
    if not dry_run and not confirm:
        logger.error("Must specify either --dry-run or --confirm")
        logger.info("For safety, use --dry-run first to preview changes")
        sys.exit(1)

    # Validate target directory
    target_dir = Path(args.target_dir)

    if not target_dir.exists():
        logger.error(f"Target directory does not exist: {target_dir}")
        sys.exit(1)

    if not target_dir.is_dir():
        logger.error(f"Target path is not a directory: {target_dir}")
        sys.exit(1)

    logger.info(f"Target directory: {target_dir}")
    logger.info(f"Mode: {'DRY-RUN (preview only)' if dry_run else 'EXECUTE (will modify files)'}")
    print()

    # Statistics tracking
    stats = {
        'volumes_processed': 0,
        'cbz_created': 0,
        'errors': 0,
        'total_images': 0
    }

    try:
        # =====================================================================
        # PHASE 1: SCAN & PARSE
        # =====================================================================
        logger.info("=== PHASE 1: Scanning and Parsing ===")

        all_folders = scan_directory(target_dir)

        # Parse chapter folders
        chapters = []
        for folder in all_folders:
            chapter_info = parse_chapter_folder(folder)
            if chapter_info:
                chapters.append(chapter_info)

        # Validate structure
        if not validate_structure(chapters, all_folders):
            logger.error("Validation failed. Aborting.")
            sys.exit(1)

        # Group by volume
        volumes = group_chapters_by_volume(chapters)

        print()

        # =====================================================================
        # PHASE 2: RENAME IMAGES
        # =====================================================================
        logger.info("=== PHASE 2: Renaming Images ===")

        for chapter in chapters:
            renamed = rename_chapter_images(chapter, dry_run=dry_run, verbose=verbose)
            stats['total_images'] += renamed

        log_success(f"✓ Renamed {stats['total_images']} images")
        print()

        # =====================================================================
        # PHASE 3: CONSOLIDATE VOLUMES
        # =====================================================================
        logger.info("=== PHASE 3: Consolidating Volumes ===")

        # Create volume directories
        volume_dirs = create_volume_directories(
            target_dir,
            list(volumes.keys()),
            dry_run=dry_run
        )

        # Move images to volumes
        for volume_num, chapter_list in volumes.items():
            volume_dir = volume_dirs[volume_num]

            logger.info(f"Processing Volume {volume_num:02d} ({len(chapter_list)} chapters)")

            for chapter in chapter_list:
                moved, failed = move_images_to_volume(
                    chapter,
                    volume_dir,
                    dry_run=dry_run,
                    verbose=verbose
                )

                if failed > 0:
                    logger.error(f"Failed to move {failed} images from {chapter}")
                    stats['errors'] += failed

        # Delete chapter directories
        if not dry_run:
            logger.info("Cleaning up chapter directories...")

        for chapter_list in volumes.values():
            deleted = delete_chapter_directories(chapter_list, dry_run=dry_run)

        log_success(f"✓ Consolidated {len(volumes)} volume(s)")
        print()

        # =====================================================================
        # PHASE 4: FINALIZE & ARCHIVE
        # =====================================================================
        logger.info("=== PHASE 4: Creating CBZ Archives ===")

        for volume_num in sorted(volumes.keys()):
            volume_dir = volume_dirs[volume_num]

            logger.info(f"Processing Volume {volume_num:02d}...")

            # Renumber images sequentially
            renumbered = renumber_images_sequentially(
                volume_dir,
                dry_run=dry_run,
                verbose=verbose
            )

            if renumbered == 0:
                logger.warning(f"No images to renumber in Volume {volume_num:02d}")
                continue

            # Check for existing CBZ
            cbz_name = f"Volume {volume_num:02d}.cbz"
            cbz_path = target_dir / cbz_name

            if not dry_run and cbz_path.exists():
                if not check_existing_cbz(cbz_path):
                    logger.info(f"Skipping Volume {volume_num:02d}")
                    continue

            # Create CBZ
            cbz_result = create_cbz_archive(
                volume_dir,
                target_dir,
                dry_run=dry_run
            )

            if cbz_result is None:
                logger.error(f"Failed to create CBZ for Volume {volume_num:02d}")
                stats['errors'] += 1
                continue

            # Validate CBZ (only in execute mode)
            if not dry_run:
                if not validate_cbz_integrity(cbz_result, renumbered):
                    logger.error(f"CBZ integrity check failed for Volume {volume_num:02d}")
                    stats['errors'] += 1
                    continue

                # Cleanup volume directory
                if cleanup_volume_directory(volume_dir, dry_run=dry_run):
                    stats['cbz_created'] += 1
                    stats['volumes_processed'] += 1
                else:
                    logger.error(f"Failed to cleanup Volume {volume_num:02d}")
                    stats['errors'] += 1
            else:
                stats['volumes_processed'] += 1

        print()

        # =====================================================================
        # SUMMARY REPORT
        # =====================================================================
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)

        if dry_run:
            print("Mode: DRY-RUN (no changes made)")
        else:
            print("Mode: EXECUTE (changes applied)")

        print(f"Volumes processed: {stats['volumes_processed']}")

        if not dry_run:
            print(f"CBZ files created: {stats['cbz_created']}")

        print(f"Total images: {stats['total_images']}")

        if stats['errors'] > 0:
            logger.warning(f"Errors encountered: {stats['errors']}")
        else:
            log_success("✓ Completed successfully with no errors!")

        print("=" * 70)

        if dry_run:
            print("\nTo execute changes, run again with --confirm flag")
            print("Recommendation: Backup your data before executing!")

    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
        logger.info("You may need to manually clean up partial changes")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error("Process aborted. Check logs above for details.")
        sys.exit(1)


if __name__ == '__main__':
    main()
