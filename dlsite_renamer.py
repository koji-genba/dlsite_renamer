#!/usr/bin/env python3
"""
DLsite Folder Renaming Tool

Renames folders based on RJ number to Japanese title from CSV export.
Handles multi-part folders and Windows filename restrictions.
"""

import csv
import json
import logging
import os
import re
import sys
import time
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
    DEFAULT_CSV = 'dlsite_purchases_20260118_204640.csv'

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


class DuplicateTitleError(RenamingError):
    """Duplicate target names"""
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
    log_file = log_path / f'rename_{timestamp}.log'

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


def find_matching_folders(base_dir: Path, rj_number: str) -> List[Path]:
    """
    Find folders matching rj_number or rj_number.partN pattern

    Args:
        base_dir: Base directory to search in
        rj_number: RJ number to match

    Returns:
        List of matching folder paths
    """
    matching_folders = []

    # Pattern: exact match or with .partN suffix
    # Example: RJ243414 or RJ243414.part1, RJ243414.part2
    pattern = re.compile(rf'^{re.escape(rj_number)}(\.part\d+)?$', re.IGNORECASE)

    # Search in base directory
    if not base_dir.exists():
        logger.error(f"Base directory does not exist: {base_dir}")
        return []

    for item in base_dir.iterdir():
        if item.is_dir() and pattern.match(item.name):
            matching_folders.append(item)

    return sorted(matching_folders)  # Sort for consistent ordering


def find_folders_by_title(base_dir: Path, sanitized_title: str) -> List[Path]:
    """
    Find folders matching sanitized title or title.partN pattern

    Args:
        base_dir: Base directory to search in
        sanitized_title: Sanitized title to match

    Returns:
        List of matching folder paths
    """
    matching_folders = []

    # Pattern: exact match or with .partN suffix
    # Example: タイトル or タイトル.part1, タイトル.part2
    pattern = re.compile(rf'^{re.escape(sanitized_title)}(\.part\d+)?$', re.IGNORECASE)

    # Search in base directory
    if not base_dir.exists():
        logger.error(f"Base directory does not exist: {base_dir}")
        return []

    for item in base_dir.iterdir():
        if item.is_dir() and pattern.match(item.name):
            matching_folders.append(item)

    return sorted(matching_folders)  # Sort for consistent ordering


def generate_renaming_plan(base_dir: Path,
                          renaming_map: Dict[str, Tuple[str, Optional[str]]],
                          max_length: int = Config.MAX_FILENAME_LENGTH,
                          remove_suffix: bool = False,
                          update_mtime: bool = False) -> List[Tuple[Path, Path, Optional[float]]]:
    """
    Generate complete renaming plan

    Args:
        base_dir: Base directory containing folders
        renaming_map: Dictionary of rj_number -> (title, purchase_date)
        max_length: Maximum filename length
        remove_suffix: If True, remove .partN suffix when only one folder exists for an RJ number
        update_mtime: If True, also find already-renamed folders for mtime update

    Returns:
        List of (old_path, new_path, timestamp) tuples
    """
    plan = []
    not_found = []
    sanitization_errors = []

    for rj_number, (title, purchase_date) in renaming_map.items():
        # Sanitize title
        try:
            sanitized_title = sanitize_filename(title, max_length)
        except ValueError as e:
            logger.error(f"Failed to sanitize title for {rj_number}: {e}")
            sanitization_errors.append(rj_number)
            continue

        # Parse purchase date
        timestamp = parse_purchase_date(purchase_date) if purchase_date else None

        # Find matching folders (by RJ number)
        matching_folders = find_matching_folders(base_dir, rj_number)

        if not matching_folders and update_mtime:
            # If update_mtime is enabled, also search for already-renamed folders
            # This allows updating mtime on folders that have already been renamed
            matching_folders = find_folders_by_title(base_dir, sanitized_title)

        if not matching_folders:
            not_found.append(rj_number)
            logger.debug(f"No folder found for {rj_number}")
            continue

        # Determine if we should keep suffixes
        # Keep suffixes if multiple folders exist OR if remove_suffix is False
        has_multiple_parts = len(matching_folders) > 1
        keep_suffix = has_multiple_parts or not remove_suffix

        # Generate rename operations for each match
        for old_path in matching_folders:
            # Preserve .partN suffix if present
            suffix_match = re.search(r'(\.part\d+)$', old_path.name, re.IGNORECASE)
            suffix = suffix_match.group(1) if suffix_match else None

            # Generate new name
            # Only add suffix if we should keep it AND a suffix exists
            if suffix and keep_suffix:
                new_name = f"{sanitized_title}{suffix}"
            else:
                new_name = sanitized_title

            new_path = old_path.parent / new_name

            plan.append((old_path, new_path, timestamp))

    # Report summary
    if not_found:
        logger.info(f"Folders not found for {len(not_found)} RJ numbers (this is normal if you don't have all items downloaded)")

    if sanitization_errors:
        logger.warning(f"Sanitization errors for {len(sanitization_errors)} RJ numbers")

    return plan


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
        print("RENAMING PREVIEW")
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


def confirm_execution(plan: List[Tuple[Path, Path, Optional[float]]]) -> bool:
    """
    Ask user to confirm before executing

    Args:
        plan: List of (old_path, new_path) tuples

    Returns:
        True if user confirms, False otherwise
    """
    preview_renaming(plan)

    response = input("\nProceed with renaming? (yes/no): ").strip().lower()

    return response in ['yes', 'y']


def log_operation(old_path: Path, new_path: Path, success: bool, error: Optional[str] = None):
    """
    Log individual rename operation

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


def execute_renaming(plan: List[Tuple[Path, Path, Optional[float]]],
                    dry_run: bool = False,
                    update_mtime: bool = False) -> List[Tuple[Path, Path, bool, Optional[str]]]:
    """
    Execute renaming operations

    Args:
        plan: List of (old_path, new_path, timestamp) tuples
        dry_run: If True, don't actually rename
        update_mtime: If True, update folder modification time to purchase date

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

            # Execute rename
            if not dry_run:
                if not is_mtime_only:
                    old_path.rename(new_path)

                    # Verify
                    if not new_path.exists():
                        raise RenamingError("Verification failed: target not found after rename")

                # Update modification time if requested and timestamp is available
                # For mtime-only operations, update the old_path directly
                target_path = new_path if not is_mtime_only else old_path
                if update_mtime and timestamp is not None:
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
    logger.info("RENAMING SUMMARY")
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


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main execution function"""
    import argparse

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Rename DLsite folders based on CSV export',
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
        help='Directory containing folders to rename'
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
    parser.add_argument(
        '--update-mtime',
        action='store_true',
        help='Update folder modification time to purchase date (date only, time set to 00:00:00)'
    )
    parser.add_argument(
        '--remove-suffix',
        action='store_true',
        help='Remove .partN suffix when only one folder exists for an RJ number (prevents conflicts)'
    )

    args = parser.parse_args()

    # Setup logging
    global logger
    logger = setup_logging(args.log_dir)

    logger.info("="*80)
    logger.info("DLsite Folder Renaming Tool")
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
    if args.remove_suffix:
        logger.info("Suffix removal enabled: .partN will be removed when safe (only one folder per RJ number)")
    if args.update_mtime:
        logger.info("Mtime update mode: Will also search for already-renamed folders to update their dates")
    plan = generate_renaming_plan(args.directory, renaming_map, args.max_length, args.remove_suffix, args.update_mtime)
    logger.info(f"Generated plan with {len(plan)} operations")

    if not plan:
        logger.warning("No renaming operations to perform")
        logger.info("This could mean:")
        logger.info("  - No folders matching RJ numbers from CSV were found")
        logger.info("  - All folders are already renamed")
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
        if not confirm_execution(plan):
            logger.info("Operation cancelled by user")
            sys.exit(0)

    # Execute
    logger.info("Executing renaming operations...")
    if args.update_mtime:
        logger.info("Modification times will be updated to purchase dates (00:00:00)")
    results = execute_renaming(plan, dry_run=False, update_mtime=args.update_mtime)

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
