"""
Concurrent Image Processor — WebSocket Worker
=============================================
This program implements the worker-side behaviors from the design:

  ReceiveJobInWorker1/2/3        — wait for a job dispatched by the server
  ApplyEdgeDetection             — apply FIND_EDGES filter (Worker 1)
  ApplyGaussianBlur              — apply GaussianBlur filter (Worker 2)
  ApplyBlackAndWhite             — convert to grayscale (Worker 3)
  WriteToSharedDatabaseInWorker1/2/3  — send result back to server

The design shows WriteToSharedDatabase* looping back to ReceiveJobInWorker*,
which is exactly the worker_loop() below: it processes jobs indefinitely until
the connection is closed.

Each worker is a separate process parameterized by --type.  Three instances
must be running alongside the server:

    python image_processor_ws_worker.py --type edge
    python image_processor_ws_worker.py --type blur
    python image_processor_ws_worker.py --type bw

Image processing is done with Pillow.  Synchronous Pillow calls run in a
thread pool via asyncio.to_thread() so the event loop stays responsive.
"""

import argparse
import asyncio
import json
import logging
import os

import websockets
from PIL import Image, ImageFilter

SERVER_URI = "ws://localhost:8765"

# ---------------------------------------------------------------------------
# Worker metadata — maps each type to its design behavior names
# ---------------------------------------------------------------------------

WORKER_META = {
    "edge": {
        "name":             "Worker1-EdgeDetection",
        "receive_behavior": "ReceiveJobInWorker1",
        "apply_behavior":   "ApplyEdgeDetection",
        "write_behavior":   "WriteToSharedDatabaseInWorker1",
        "log_file":         "logs/worker_edge.log",
        "output_suffix":    "edge",
    },
    "blur": {
        "name":             "Worker2-GaussianBlur",
        "receive_behavior": "ReceiveJobInWorker2",
        "apply_behavior":   "ApplyGaussianBlur",
        "write_behavior":   "WriteToSharedDatabaseInWorker2",
        "log_file":         "logs/worker_blur.log",
        "output_suffix":    "blur",
    },
    "bw": {
        "name":             "Worker3-BlackAndWhite",
        "receive_behavior": "ReceiveJobInWorker3",
        "apply_behavior":   "ApplyBlackAndWhite",
        # Note: the design uses "WriteTheResultToSharedDatabaseInWOrker3"
        # (with both "TheResult" and the typo "WOrker3") — preserved faithfully.
        "write_behavior":   "WriteTheResultToSharedDatabaseInWorker3",
        "log_file":         "logs/worker_bw.log",
        "output_suffix":    "bw",
    },
}


# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------

def setup_logger(worker_type: str) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    meta = WORKER_META[worker_type]
    log = logging.getLogger(meta["name"])
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")
    fh = logging.FileHandler(meta["log_file"])
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    return log


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _output_path(job_id: str, suffix: str) -> str:
    os.makedirs("output", exist_ok=True)
    return os.path.join("output", f"{job_id}_{suffix}.png")


# ---------------------------------------------------------------------------
# Behavior: ReceiveJobInWorker1/2/3
# ---------------------------------------------------------------------------

def receive_job_in_worker(job: dict, meta: dict, logger: logging.Logger) -> dict:
    """
    Design behavior: ReceiveJobInWorker1 / ReceiveJobInWorker2 / ReceiveJobInWorker3
    Receive the job dispatched by the server.
    Goes to: Apply* behavior.
    """
    behavior = meta["receive_behavior"]
    logger.info(
        f"[Behavior: {behavior}] Received job {job['job_id'][:8]}... "
        f"image_path={job['image_path']}"
    )
    return job


# ---------------------------------------------------------------------------
# Behavior: ApplyEdgeDetection
# ---------------------------------------------------------------------------

def apply_edge_detection_sync(job: dict, meta: dict, logger: logging.Logger) -> dict:
    """
    Design behavior: ApplyEdgeDetection
    Apply the edge detection to the image using Pillow's FIND_EDGES filter.
    Goes to: WriteToSharedDatabaseInWorker1.
    """
    behavior = meta["apply_behavior"]
    logger.info(f"[Behavior: {behavior}] Opening image: {job['image_path']}")
    img = Image.open(job["image_path"])
    logger.info(f"[Behavior: {behavior}] Applying FIND_EDGES filter")
    result = img.filter(ImageFilter.FIND_EDGES)
    output_path = _output_path(job["job_id"], meta["output_suffix"])
    logger.info(f"[Behavior: {behavior}] Saving processed image to: {output_path}")
    result.save(output_path)
    job["output_path"] = output_path
    return job


# ---------------------------------------------------------------------------
# Behavior: ApplyGaussianBlur
# ---------------------------------------------------------------------------

def apply_gaussian_blur_sync(job: dict, meta: dict, logger: logging.Logger) -> dict:
    """
    Design behavior: ApplyGaussianBlur
    Apply the gaussian blur to the image using Pillow's GaussianBlur filter
    (radius=5).
    Goes to: WriteToSharedDatabaseInWorker2.
    """
    behavior = meta["apply_behavior"]
    logger.info(f"[Behavior: {behavior}] Opening image: {job['image_path']}")
    img = Image.open(job["image_path"])
    logger.info(f"[Behavior: {behavior}] Applying GaussianBlur filter (radius=5)")
    result = img.filter(ImageFilter.GaussianBlur(radius=5))
    output_path = _output_path(job["job_id"], meta["output_suffix"])
    logger.info(f"[Behavior: {behavior}] Saving processed image to: {output_path}")
    result.save(output_path)
    job["output_path"] = output_path
    return job


# ---------------------------------------------------------------------------
# Behavior: ApplyBlackAndWhite
# ---------------------------------------------------------------------------

def apply_black_and_white_sync(job: dict, meta: dict, logger: logging.Logger) -> dict:
    """
    Design behavior: ApplyBlackAndWhite
    Convert the image to grayscale using Pillow's convert("L").
    Note: the design's _description for this behavior is empty; grayscale
    conversion is inferred from the behavior name and menu description.
    Goes to: WriteTheResultToSharedDatabaseInWorker3.
    """
    behavior = meta["apply_behavior"]
    logger.info(f"[Behavior: {behavior}] Opening image: {job['image_path']}")
    img = Image.open(job["image_path"])
    logger.info(f"[Behavior: {behavior}] Converting image to grayscale (L mode)")
    result = img.convert("L")
    output_path = _output_path(job["job_id"], meta["output_suffix"])
    logger.info(f"[Behavior: {behavior}] Saving processed image to: {output_path}")
    result.save(output_path)
    job["output_path"] = output_path
    return job


# Dispatch table: worker_type → synchronous apply function
APPLY_FNS = {
    "edge": apply_edge_detection_sync,
    "blur": apply_gaussian_blur_sync,
    "bw":   apply_black_and_white_sync,
}


# ---------------------------------------------------------------------------
# Behavior: WriteToSharedDatabaseInWorker1/2/3
# ---------------------------------------------------------------------------

async def write_to_shared_database(
    ws,
    job: dict,
    meta: dict,
    logger: logging.Logger,
) -> None:
    """
    Design behavior: WriteToSharedDatabaseInWorker1 / WriteToSharedDatabaseInWorker2
                   / WriteTheResultToSharedDatabaseInWorker3
    Write the result to the shared database by sending it back to the server.
    Goes to: ReceiveJobInWorker* (the worker loop continues).
    """
    behavior = meta["write_behavior"]
    logger.info(
        f"[Behavior: {behavior}] Sending result for job {job['job_id'][:8]}... "
        f"to shared database (server) — output_path={job['output_path']}"
    )
    await ws.send(json.dumps({
        "type":        "result",
        "job_id":      job["job_id"],
        "output_path": job["output_path"],
    }))
    logger.info(
        f"[Behavior: {behavior}] Result sent to server. "
        f"Looping back to {meta['receive_behavior']}."
    )


# ---------------------------------------------------------------------------
# Worker loop: ReceiveJobInWorker → Apply → WriteToSharedDatabase → (repeat)
# ---------------------------------------------------------------------------

async def worker_loop(ws, worker_type: str, logger: logging.Logger) -> None:
    """
    Implements the worker's behavioral loop from the design:
      ReceiveJobInWorker* → Apply* → WriteToSharedDatabase* → (loop back)
    """
    meta = WORKER_META[worker_type]
    apply_fn = APPLY_FNS[worker_type]

    try:
        async for raw in ws:
            msg = json.loads(raw)

            if msg["type"] == "registered":
                logger.info(
                    f"[Worker] Registered with server as '{worker_type}' worker"
                )
                logger.info(
                    f"[Behavior: {meta['receive_behavior']}] "
                    f"Waiting for jobs from server..."
                )
                continue

            if msg["type"] != "job":
                continue

            job = dict(msg)

            # --- ReceiveJobInWorker* ---
            job = receive_job_in_worker(job, meta, logger)

            # --- Apply* (run in thread pool to avoid blocking the event loop) ---
            logger.info(
                f"[Behavior: {meta['apply_behavior']}] "
                f"Starting processing for job {job['job_id'][:8]}..."
            )
            try:
                job = await asyncio.to_thread(apply_fn, job, meta, logger)
                logger.info(
                    f"[Behavior: {meta['apply_behavior']}] "
                    f"Processing complete for job {job['job_id'][:8]}..."
                )

                # --- WriteToSharedDatabase* ---
                await write_to_shared_database(ws, job, meta, logger)

            except Exception as exc:
                logger.error(
                    f"[Behavior: {meta['apply_behavior']}] "
                    f"Job {job['job_id'][:8]}... FAILED: {exc}"
                )
                await ws.send(json.dumps({
                    "type":   "result",
                    "job_id": job["job_id"],
                    "error":  str(exc),
                }))

            logger.info(
                f"[Behavior: {meta['receive_behavior']}] "
                f"Waiting for next job..."
            )

    except websockets.exceptions.ConnectionClosed:
        logger.warning("[Worker] Connection to server closed")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(worker_type: str) -> None:
    os.makedirs("output", exist_ok=True)
    logger = setup_logger(worker_type)
    meta = WORKER_META[worker_type]

    logger.info(f"[Worker] {meta['name']} starting. Connecting to {SERVER_URI}")
    async with websockets.connect(SERVER_URI) as ws:
        logger.info(f"[Worker] Connected. Registering as '{worker_type}' worker.")
        await ws.send(json.dumps({"type": "register_worker", "worker_type": worker_type}))
        await worker_loop(ws, worker_type, logger)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image Processor WebSocket Worker")
    parser.add_argument(
        "--type", "-t",
        required=True,
        choices=["edge", "blur", "bw"],
        help="Worker type: edge (edge detection), blur (gaussian blur), bw (black and white)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.type))
