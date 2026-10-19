#!/usr/bin/env python3
"""Batch Runner CLI for IncuBrix Long-Tail Distribution Network.

Usage:
    python scripts/batch_runner.py <file-or-folder> --out <dir>
"""

import argparse
import asyncio
import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import uuid

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition
from core.errors import IncuBrixError
from core.manifest_builder import build_output_manifest
from engine.publisher import publish_engine
from api.main import load_all_connectors

# Discover and register all connectors
load_all_connectors()


def setup_batch_logging(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("batch_runner")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def load_input_items(path: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """Loads input items from a single JSON/CSV file or a folder of files."""
    items: List[Tuple[str, Dict[str, Any]]] = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted([f for f in path.iterdir() if f.is_file() and f.suffix in (".json", ".csv")])
    else:
        raise ValueError(f"Path does not exist: {path}")

    for file_path in files:
        if file_path.suffix == ".json":
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for idx, el in enumerate(data):
                        item_id = el.get("id") or f"{file_path.stem}_{idx+1:03d}"
                        items.append((item_id, el))
                elif isinstance(data, dict):
                    item_id = data.get("id") or file_path.stem
                    items.append((item_id, data))
            except Exception as e:
                print(f"Error parsing JSON {file_path}: {e}")

        elif file_path.suffix == ".csv":
            try:
                with open(file_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        item_id = row.get("id") or f"{file_path.stem}_{idx+1:03d}"
                        items.append((item_id, row))
            except Exception as e:
                print(f"Error parsing CSV {file_path}: {e}")

    return items


async def process_item(
    item_id: str,
    raw_item: Dict[str, Any],
    logger: logging.Logger,
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """Processes a single item through pre-flight rules, publisher engine, and manifest generation."""
    logger.info(f"Processing item '{item_id}'...")

    # Extract or construct Rendition
    title = raw_item.get("title") or raw_item.get("rendition", {}).get("title") or f"Batch Item {item_id}"
    body = raw_item.get("body") or raw_item.get("rendition", {}).get("body") or "Batch content test body."
    canonical_url = raw_item.get("canonical_url") or raw_item.get("rendition", {}).get("canonical_url")
    ai_disclosure = raw_item.get("ai_disclosure") or raw_item.get("rendition", {}).get("ai_disclosure")

    rendition = Rendition(
        title=title,
        body=body,
        canonical_url=canonical_url,
        ai_disclosure=ai_disclosure,
    )

    # Extract or construct Destination
    dest_data = raw_item.get("destination") or {}
    dest_id = dest_data.get("id") or raw_item.get("destination_id") or f"dest_{item_id}"
    platform_key = dest_data.get("platform_key") or raw_item.get("platform_key") or "devto"
    name = dest_data.get("name") or raw_item.get("name") or f"Destination {platform_key}"
    parameters = dest_data.get("parameters") or raw_item.get("parameters") or {"base_url": "http://test/devto"}

    destination = DestinationPayload(
        id=dest_id,
        name=name,
        platform_key=platform_key,
        parameters=parameters,
    )

    # Connection
    conn_data = raw_item.get("connection") or {}
    connection = ConnectionPayload(
        base_url=conn_data.get("base_url") or parameters.get("base_url"),
        api_key=conn_data.get("api_key") or "batch_test_key_12345",
        token=conn_data.get("token"),
    )

    idempotency_key = raw_item.get("idempotency_key") or f"batch_{item_id}_{uuid.uuid4().hex[:8]}"

    try:
        start_time = datetime.now(timezone.utc)
        result = await publish_engine.publish(
            rendition=rendition,
            destination=destination,
            connection=connection,
            idempotency_key=idempotency_key,
        )
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Ensure manifest is included
        manifest = result.get("manifest") or build_output_manifest(
            providers={"connector": platform_key},
            settings={"item_id": item_id, "destination_id": dest_id},
            timings={
                "started_at": start_time.isoformat(),
                "completed_at": end_time.isoformat(),
                "duration_ms": duration_ms,
            },
            ai_generated=bool(ai_disclosure),
        )
        result["manifest"] = manifest
        logger.info(f"Item '{item_id}' succeeded: platform_post_id={result.get('platform_post_id')}")
        return True, result, None

    except IncuBrixError as ie:
        err_dict = ie.to_dict()
        err_dict["item_id"] = item_id
        logger.error(f"Item '{item_id}' failed with IncuBrixError: {ie.message}")
        return False, err_dict, ie.message
    except Exception as e:
        err_dict = {"item_id": item_id, "error": str(e), "type": type(e).__name__}
        logger.error(f"Item '{item_id}' failed with unhandled error: {e}")
        return False, err_dict, str(e)


async def run_batch(input_path: Path, out_dir: Path) -> int:
    """Main batch runner orchestration."""
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = out_dir / "inputs"
    outputs_dir = out_dir / "outputs"
    failures_dir = out_dir / "failures"
    logs_dir = out_dir / "logs"

    for d in (inputs_dir, outputs_dir, failures_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / "batch_execution.log"
    logger = setup_batch_logging(log_file)

    logger.info(f"Starting batch runner for: {input_path}")
    logger.info(f"Output directory: {out_dir}")

    items = load_input_items(input_path)
    logger.info(f"Loaded {len(items)} items to process.")

    succeeded_count = 0
    failed_count = 0
    start_all = datetime.now(timezone.utc)
    results_mapping: List[Dict[str, Any]] = []

    for item_id, raw_item in items:
        # 1. Write Input
        input_file = inputs_dir / f"{item_id}.json"
        input_file.write_text(json.dumps(raw_item, indent=2), encoding="utf-8")

        # 2. Process
        success, res_data, err_msg = await process_item(item_id, raw_item, logger)

        if success:
            succeeded_count += 1
            output_file = outputs_dir / f"{item_id}_result.json"
            output_file.write_text(json.dumps(res_data, indent=2), encoding="utf-8")
            results_mapping.append({
                "item_id": item_id,
                "input_file": str(input_file.relative_to(out_dir)),
                "output_file": str(output_file.relative_to(out_dir)),
                "status": "succeeded",
                "platform_post_id": res_data.get("platform_post_id"),
                "live_url": res_data.get("live_url"),
            })
        else:
            failed_count += 1
            failure_file = failures_dir / f"{item_id}_failure.json"
            failure_file.write_text(json.dumps(res_data, indent=2), encoding="utf-8")
            results_mapping.append({
                "item_id": item_id,
                "input_file": str(input_file.relative_to(out_dir)),
                "failure_file": str(failure_file.relative_to(out_dir)),
                "status": "failed",
                "error": err_msg,
            })

    end_all = datetime.now(timezone.utc)
    total_duration_ms = int((end_all - start_all).total_seconds() * 1000)

    # 3. Write Summary Report
    summary = {
        "batch_id": f"batch_{uuid.uuid4().hex[:10]}",
        "timestamp_start": start_all.isoformat(),
        "timestamp_end": end_all.isoformat(),
        "total_items": len(items),
        "succeeded": succeeded_count,
        "failed": failed_count,
        "duration_ms": total_duration_ms,
        "cost_estimate": "unknown",
        "results": results_mapping,
    }
    summary_file = out_dir / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    logger.info(f"Batch completed: {succeeded_count} succeeded, {failed_count} failed in {total_duration_ms}ms")
    logger.info(f"Summary written to: {summary_file}")
    return 0 if failed_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="IncuBrix Batch Runner CLI")
    parser.add_argument("input_path", type=str, help="Path to input JSON/CSV file or folder")
    parser.add_argument("--out", type=str, required=True, help="Path to output directory")
    args = parser.parse_args()

    input_path = Path(args.input_path).resolve()
    out_dir = Path(args.out).resolve()

    exit_code = asyncio.run(run_batch(input_path, out_dir))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
