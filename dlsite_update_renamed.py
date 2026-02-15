#!/usr/bin/env python3
"""
DLsite Auxiliary Update Script

Updates already-renamed folders (RJ番号_タイトル format) with latest CSV titles
and purchase dates. This is a standalone utility script for batch updates.

No dependencies on dlsite_renamer.py - completely independent.
"""

import csv
import json
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Configuration constants"""
    MAX_FILENAME_LENGTH = 200
    LOG_DIR = 'logs'
    DEFAULT_CSV = 'dlsite_purchases.csv'

    # Character replacements (full-width equivalents)
    CHAR_REPLACEMENTS = {
        '<': '＜',   # Full-width less than
        '>': '＞',   # Full-width greater than
        ':': '：',   # Full-width colon
        '"': '＂',   # Full-width quotation
        '/': '／',   # Full-width solidus
        '\\': '＼',  # Full-width reverse solidus
        '|': '｜',   # Full-width vertical line
        '?': '？',   # Full-width question mark
        '*': '＊',   # Full-width asterisk
    }


# ============================================================================
# Exceptions
# ============================================================================

class RenamingError(Exception):
    """Base exception for renaming errors"""
    pass


class FolderNotFoundError(RenamingError):
    """Folder not found"""
    pass


class TargetExistsError(RenamingError):
    """Target already exists"""
    pass


# ============================================================================
# Global Logger
# ============================================================================

logger = None


# ============================================================================
# Core Functions
# ============================================================================

def setup_logging(log_dir: str = Config.LOG_DIR,
                  level: int = logging.INFO) -> logging.Logger:
    """
    Setup logging configuration

    Args:
        log_dir: Directory for log files
        level: Logging level

    Returns:
        Configured logger
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Generate timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f'update_{timestamp}.log'

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    new_logger = logging.getLogger(__name__)
    new_logger.info(f"Log file: {log_file}")

    return new_logger


def load_renaming_map(csv_path: Path) -> Dict[str, Tuple[str, Optional[str]]]:
    """
    Load CSV and create rj_number -> (title, purchase_date) mapping

    Args:
        csv_path: Path to CSV file

    Returns:
        Dictionary mapping rj_number to (title, purchase_date)
    """
    renaming_map = {}

    # Use 'utf-8-sig' to automatically handle BOM
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            rj_number = row.get('rj_number', '').strip()
            title = row.get('title', '').strip()
            purchase_date = row.get('purchase_date', '').strip()

            # Validate data
            if not rj_number:
                logger.warning(f"Row {row_num}: Missing rj_number, skipping")
                continue

            if not title:
                logger.warning(f"Row {row_num}: Missing title for {rj_number}, skipping")
                continue

            renaming_map[rj_number] = (title, purchase_date if purchase_date else None)

    return renaming_map


def sanitize_filename(title: str,
                     max_length: int = Config.MAX_FILENAME_LENGTH) -> str:
    """
    Sanitize title for Windows/NTFS/ZFS compatibility

    Strategy:
    1. Replace Windows-forbidden characters with full-width equivalents
    2. Preserve Japanese characters (already valid UTF-8)
    3. Trim to safe path length
    4. Handle edge cases (trailing dots, spaces)

    Args:
        title: Original title from CSV
        max_length: Maximum filename length

    Returns:
        Sanitized filename

    Raises:
        ValueError: If title becomes empty after sanitization
    """
    sanitized = title

    # Replace forbidden characters
    for char, replacement in Config.CHAR_REPLACEMENTS.items():
        sanitized = sanitized.replace(char, replacement)

    # Normalize Unicode (NFC form for compatibility)
    sanitized = unicodedata.normalize('NFC', sanitized)

    # Remove leading/trailing whitespace
    sanitized = sanitized.strip()

    # Remove trailing dots and spaces (Windows restriction)
    sanitized = sanitized.rstrip('. ')

    # Truncate if too long (leave room for base path)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('. ')

    # Ensure not empty after sanitization
    if not sanitized:
        raise ValueError(f"Title became empty after sanitization: {title}")

    return sanitized


def parse_purchase_date(date_str: str) -> Optional[float]:
    """
    Parse purchase date from CSV and convert to Unix timestamp (midnight)

    Args:
        date_str: Date string in format "YYYY/MM/DD HH:MM"

    Returns:
        Unix timestamp for the date at 00:00:00, or None if parsing fails
    """
    if not date_str:
        return None

    try:
        # Parse the date string (format: "2019/01/21 21:56")
        dt = datetime.strptime(date_str, '%Y/%m/%d %H:%M')

        # Set time to midnight (00:00:00)
        dt_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert to Unix timestamp
        timestamp = dt_midnight.timestamp()

        return timestamp
    except ValueError as e:
        logger.warning(f"Failed to parse purchase date '{date_str}': {e}")
        return None


def check_for_duplicates(plan: List[Tuple[Path, Path, Optional[float]]]) -> Dict[str, List[Path]]:
    """
    Check for duplicate target names

    Args:
        plan: List of (old_path, new_path, timestamp) tuples

    Returns:
        Dictionary of {target_name: [source_folders]} for duplicates
    """
    targets = {}

    for source, target, _ in plan:
        target_name = target.name
        if target_name not in targets:
            targets[target_name] = []
        targets[target_name].append(source)

    # Find duplicates
    duplicates = {name: sources for name, sources in targets.items()
                  if len(sources) > 1}

    return duplicates


def preview_renaming(plan: List[Tuple[Path, Path, Optional[float]]],
                    output_format: str = 'table'):
    """
    Display preview of renaming operations

    Args:
        plan: List of (old_path, new_path, timestamp) tuples
        output_format: 'table' or 'json'
    """
    if output_format == 'table':
        print("\n" + "="*80)
        print("UPDATE PREVIEW")
        print("="*80)
        print(f"{'Old Name':<40} => {'New Name':<40}")
        print("-"*80)

        for old_path, new_path, _ in plan:
            old_name = old_path.name
            new_name = new_path.name

            # Truncate if too long for display
            if len(old_name) > 38:
                old_name = old_name[:35] + "..."
            if len(new_name) > 38:
                new_name = new_name[:35] + "..."

            print(f"{old_name:<40} => {new_name:<40}")

        print("="*80)
        print(f"Total operations: {len(plan)}")
        print("="*80 + "\n")

    elif output_format == 'json':
        preview = [
            {
                'old': str(old_path),
                'new': str(new_path),
                'old_name': old_path.name,
                'new_name': new_path.name,
                'timestamp': timestamp
            }
            for old_path, new_path, timestamp in plan
        ]
        print(json.dumps(preview, indent=2, ensure_ascii=False))


def log_operation(old_path: Path, new_path: Path, success: bool, error: Optional[str] = None):
    """
    Log individual update operation

    Args:
        old_path: Original path
        new_path: New path
        success: Whether operation succeeded
        error: Error message if failed
    """
    if success:
        if old_path == new_path:
            logger.info(f"SUCCESS (mtime only): {old_path.name}")
        else:
            logger.info(f"SUCCESS: {old_path.name} => {new_path.name}")
    else:
        logger.error(f"FAILED: {old_path.name} => {new_path.name}")
        if error:
            logger.error(f"  Error: {error}")


def generate_summary_report(results: List[Tuple[Path, Path, bool, Optional[str]]]):
    """
    Generate summary report after execution

    Args:
        results: List of (old_path, new_path, success, error) tuples
    """
    total = len(results)
    successful = sum(1 for _, _, success, _ in results if success)
    failed = total - successful

    logger.info("\n" + "="*80)
    logger.info("UPDATE SUMMARY")
    logger.info("="*80)
    logger.info(f"Total operations: {total}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if failed > 0:
        logger.info("\nFailed operations:")
        for old_path, new_path, success, error in results:
            if not success:
                logger.info(f"  {old_path.name} => {new_path.name}")
                logger.info(f"    Reason: {error}")

    logger.info("="*80 + "\n")


def extract_rj_number_from_folder(folder_name: str) -> Optional[str]:
    """
    Extract RJ number from folder name

    Supports:
    - RJ243414_タイトル
    - RJ243414_タイトル.part1
    - RJ243414 (edge case: folder without title)

    Args:
        folder_name: Folder name to extract from

    Returns:
        RJ number (uppercase normalized), or None if not found

    Examples:
        >>> extract_rj_number_from_folder("RJ243414_メイドと暮らそ♪")
        'RJ243414'
        >>> extract_rj_number_from_folder("RJ243414_メイドと暮らそ♪.part1")
        'RJ243414'
        >>> extract_rj_number_from_folder("rj01382778_小さなお姉さん")
        'RJ01382778'
        >>> extract_rj_number_from_folder("RJ243414")
        'RJ243414'
        >>> extract_rj_number_from_folder("some_other_folder")
        None
    """
    # Pattern: RJ + digits at start, optionally followed by underscore/content and .partN
    pattern = re.compile(r'^(RJ\d+)(?:_.*)?(?:\.part\d+)?$', re.IGNORECASE)
    match = pattern.match(folder_name)

    if match:
        return match.group(1).upper()  # Normalize to uppercase

    return None


def generate_update_plan(base_dir: Path,
                         renaming_map: Dict[str, Tuple[str, Optional[str]]],
                         max_length: int = Config.MAX_FILENAME_LENGTH) -> List[Tuple[Path, Path, Optional[float]]]:
    """
    Generate update plan for already-renamed folders

    Args:
        base_dir: Base directory containing folders
        renaming_map: Dictionary of rj_number -> (title, purchase_date)
        max_length: Maximum filename length

    Returns:
        List of (old_path, new_path, timestamp) tuples
    """
    plan = []
    not_found = []
    sanitization_errors = []
    invalid_format = []

    # Build folder cache (performance optimization)
    logger.debug("Building folder cache...")
    folder_cache = {}
    if base_dir.exists():
        for item in base_dir.iterdir():
            if item.is_dir():
                folder_cache[item.name] = item
    else:
        logger.error(f"Base directory does not exist: {base_dir}")
        return []
    logger.debug(f"Cached {len(folder_cache)} folders")

    # Filter folders matching RJ番号_* pattern (or just RJ番号)
    rj_pattern = re.compile(r'^RJ\d+', re.IGNORECASE)
    rj_folders = {
        name: path
        for name, path in folder_cache.items()
        if rj_pattern.match(name)
    }
    logger.info(f"Found {len(rj_folders)} folders with RJ numbers")

    # Process each folder
    for folder_name, folder_path in rj_folders.items():
        # Extract RJ number
        rj_number = extract_rj_number_from_folder(folder_name)

        if not rj_number:
            logger.warning(f"Could not extract RJ number from: {folder_name}")
            invalid_format.append(folder_name)
            continue

        # Look up in CSV
        if rj_number not in renaming_map:
            logger.debug(f"RJ number not in CSV: {rj_number}")
            not_found.append(rj_number)
            continue

        title, purchase_date = renaming_map[rj_number]

        # Sanitize title
        try:
            sanitized_title = sanitize_filename(title, max_length)
        except ValueError as e:
            logger.error(f"Failed to sanitize title for {rj_number}: {e}")
            sanitization_errors.append(rj_number)
            continue

        # Parse purchase date
        timestamp = parse_purchase_date(purchase_date) if purchase_date else None

        # Extract .partN suffix if present
        suffix_match = re.search(r'(\.part\d+)$', folder_name, re.IGNORECASE)
        suffix = suffix_match.group(1) if suffix_match else None

        # Generate new name: RJ番号_新タイトル[.partN]
        if suffix:
            new_name = f"{rj_number}_{sanitized_title}{suffix}"
        else:
            new_name = f"{rj_number}_{sanitized_title}"

        new_path = folder_path.parent / new_name

        # Add to plan
        plan.append((folder_path, new_path, timestamp))

    # Report summary
    if not_found:
        logger.info(f"RJ numbers not in CSV: {len(not_found)} (normal if CSV is not complete)")

    if invalid_format:
        logger.warning(f"Invalid folder format: {len(invalid_format)} folders")

    if sanitization_errors:
        logger.warning(f"Sanitization errors: {len(sanitization_errors)} RJ numbers")

    return plan


def execute_update(plan: List[Tuple[Path, Path, Optional[float]]],
                   dry_run: bool = False) -> List[Tuple[Path, Path, bool, Optional[str]]]:
    """
    Execute update operations (rename + mtime update)

    Args:
        plan: List of (old_path, new_path, timestamp) tuples
        dry_run: If True, don't actually execute

    Returns:
        List of (old_path, new_path, success, error) tuples
    """
    results = []

    for old_path, new_path, timestamp in plan:
        try:
            # Validation checks
            if not old_path.exists():
                raise FolderNotFoundError(f"Source not found: {old_path}")

            if not old_path.is_dir():
                raise RenamingError(f"Not a directory: {old_path}")

            # Check if this is just a mtime update (no rename needed)
            is_mtime_only = (old_path == new_path)

            if not is_mtime_only and new_path.exists():
                raise TargetExistsError(f"Target already exists: {new_path}")

            # Check parent directory is writable (only if renaming)
            if not is_mtime_only and not os.access(old_path.parent, os.W_OK):
                raise PermissionError(f"No write permission: {old_path.parent}")

            # Execute rename and mtime update
            if not dry_run:
                # Rename if needed
                if not is_mtime_only:
                    old_path.rename(new_path)

                    # Verify
                    if not new_path.exists():
                        raise RenamingError("Verification failed: target not found after rename")

                # Update modification time (always, if timestamp available)
                # For mtime-only operations, update the old_path directly
                target_path = new_path if not is_mtime_only else old_path
                if timestamp is not None:
                    try:
                        # Set both access time and modification time to the same timestamp
                        os.utime(target_path, (timestamp, timestamp))
                        logger.debug(f"Updated mtime for {target_path.name} to {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')}")
                    except Exception as e:
                        logger.warning(f"Failed to update mtime for {target_path.name}: {e}")

            # Log success
            log_operation(old_path, new_path, True)
            results.append((old_path, new_path, True, None))

        except Exception as e:
            # Log failure
            error_msg = str(e)
            log_operation(old_path, new_path, False, error_msg)
            results.append((old_path, new_path, False, error_msg))

    return results


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main execution function"""
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Update already-renamed DLsite folders with latest CSV titles and purchase dates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without executing
  %(prog)s /path/to/folders --dry-run

  # Execute with confirmation
  %(prog)s /path/to/folders --csv dlsite_purchases.csv

  # Execute without confirmation
  %(prog)s /path/to/folders --yes

  # JSON output
  %(prog)s /path/to/folders --dry-run --format json > preview.json
        """
    )
    parser.add_argument(
        'directory',
        type=Path,
        help='Directory containing "RJ番号_タイトル" folders to update'
    )
    parser.add_argument(
        '--csv',
        type=Path,
        default=Config.DEFAULT_CSV,
        help=f'CSV file with RJ numbers and titles (default: {Config.DEFAULT_CSV})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without executing'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )
    parser.add_argument(
        '--log-dir',
        type=Path,
        default=Config.LOG_DIR,
        help=f'Directory for log files (default: {Config.LOG_DIR})'
    )
    parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format for preview (default: table)'
    )
    parser.add_argument(
        '--max-length',
        type=int,
        default=Config.MAX_FILENAME_LENGTH,
        help=f'Maximum filename length (default: {Config.MAX_FILENAME_LENGTH})'
    )

    args = parser.parse_args()

    # Setup logging
    global logger
    logger = setup_logging(args.log_dir)

    logger.info("="*80)
    logger.info("DLsite Auxiliary Update Script")
    logger.info("="*80)

    # Validate inputs
    if not args.directory.exists():
        logger.error(f"Directory not found: {args.directory}")
        sys.exit(1)

    if not args.directory.is_dir():
        logger.error(f"Not a directory: {args.directory}")
        sys.exit(1)

    if not args.csv.exists():
        logger.error(f"CSV file not found: {args.csv}")
        sys.exit(1)

    # Load CSV
    logger.info(f"Loading CSV: {args.csv}")
    try:
        renaming_map = load_renaming_map(args.csv)
        logger.info(f"Loaded {len(renaming_map)} entries from CSV")
    except Exception as e:
        logger.error(f"Failed to load CSV: {e}")
        sys.exit(1)

    if not renaming_map:
        logger.error("No valid entries found in CSV")
        sys.exit(1)

    # Generate plan
    logger.info(f"Scanning directory: {args.directory}")
    logger.info("Update mode: Rename to latest CSV titles + Update mtime to purchase dates")
    plan = generate_update_plan(args.directory, renaming_map, args.max_length)
    logger.info(f"Generated plan with {len(plan)} operations")

    if not plan:
        logger.warning("No update operations to perform")
        logger.info("This could mean:")
        logger.info("  - No folders with RJ numbers were found")
        logger.info("  - All RJ numbers are not in the CSV")
        sys.exit(0)

    # Check for duplicates
    duplicates = check_for_duplicates(plan)
    if duplicates:
        logger.error("Duplicate target names detected:")
        for target_name, sources in duplicates.items():
            logger.error(f"  {target_name}:")
            for source in sources:
                logger.error(f"    - {source.name}")
        logger.error("Please resolve duplicates before proceeding")
        logger.error("This usually means multiple RJ numbers have the same title in the CSV")
        sys.exit(1)

    # Preview
    if not args.dry_run or args.format == 'table':
        preview_renaming(plan, args.format)

    # Dry run mode
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        sys.exit(0)

    # Confirm
    if not args.yes:
        response = input("\nProceed with updates? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            logger.info("Operation cancelled by user")
            sys.exit(0)

    # Execute
    logger.info("Executing update operations...")
    logger.info("Modification times will be updated to purchase dates (00:00:00)")
    results = execute_update(plan, dry_run=False)

    # Summary
    generate_summary_report(results)

    # Exit code
    failed = sum(1 for _, _, success, _ in results if not success)
    if failed > 0:
        logger.warning(f"Completed with {failed} failures")
        sys.exit(1)
    else:
        logger.info("All operations completed successfully")
        sys.exit(0)


if __name__ == '__main__':
    main()
