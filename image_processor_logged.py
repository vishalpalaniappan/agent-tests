"""
Concurrent Image Processor — Threaded version with behavior logging
===================================================================
This is the same threaded implementation as image_processor.py, but with a
logger added so that every behavior transition emits a [Behavior: <name>]
log line (to both stdout and logs/threaded.log) before the relevant code
executes.

The behaviors and their log entries mirror the design node names from
concurrent_design_only_behaviors.dal exactly, making it easy to compare the
log file against the design and see which behaviors fired, in what order, and
from which thread.

Run:
    python image_processor_logged.py
"""

import logging
import os
import queue
import sys
import threading
import uuid

from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Logger — writes to both console and logs/threaded.log
# ---------------------------------------------------------------------------

os.makedirs("logs", exist_ok=True)
os.makedirs("output", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/threaded.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("threaded")

# ---------------------------------------------------------------------------
# Shared database (behavior: WriteToSharedDatabase*)
# ---------------------------------------------------------------------------
shared_db: dict[str, str] = {}       # job_id → output_path
shared_db_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Per-worker job queues (the "channel" between Accept* and ReceiveJobInWorker*)
# ---------------------------------------------------------------------------
edge_queue: queue.Queue = queue.Queue()
blur_queue: queue.Queue = queue.Queue()
bw_queue: queue.Queue = queue.Queue()

# ---------------------------------------------------------------------------
# Sentinel value used to shut workers down cleanly
# ---------------------------------------------------------------------------
_STOP = object()


# ===========================================================================
# MAIN-THREAD BEHAVIORS
# ===========================================================================

def present_menu_and_accept_choice() -> str:
    """
    Design behavior: PresentMenuAndAcceptChoice
    Atomic, not a fork.
    Presents the user with a choice to process an image by either running an
    edge detection algorithm on it, applying gaussian blur to it, or making
    it black and white.
    Goes to: AcceptEdgeDetection | AcceptGaussianBlur | AcceptBlackandWhite
    """
    logger.info("[Behavior: PresentMenuAndAcceptChoice] Displaying menu options to user")
    print("\n=== Image Processor ===")
    print("1. Edge Detection")
    print("2. Gaussian Blur")
    print("3. Black and White")
    print("4. View completed jobs")
    print("5. Exit")
    logger.info("[Behavior: PresentMenuAndAcceptChoice] Waiting for user menu selection")
    choice = input("Choice: ").strip()
    logger.info(f"[Behavior: PresentMenuAndAcceptChoice] User selected: '{choice}'")
    return choice


def accept_edge_detection() -> str:
    """
    Design behavior: AcceptEdgeDetection  [_isDesignFork: true]
    Accept an image to apply edge detection and send it to the worker to apply
    the edge detection.
    Fork paths:
      → PresentMenuAndAcceptChoice  (main thread continues immediately)
      → ReceiveJobInWorker1         (worker 1 thread picks this up)
    """
    logger.info("[Behavior: AcceptEdgeDetection] Prompting user for image path")
    image_path = input("Image path: ").strip()
    job_id = str(uuid.uuid4())
    logger.info(
        f"[Behavior: AcceptEdgeDetection] Assigned job_id={job_id[:8]}... "
        f"image_path={image_path}"
    )
    logger.info(
        f"[Behavior: AcceptEdgeDetection] [FORK] Enqueuing job for Worker 1; "
        f"returning to PresentMenuAndAcceptChoice"
    )
    edge_queue.put({"job_id": job_id, "image_path": image_path})
    print(f"[Main]   Job {job_id[:8]}... submitted for edge detection.")
    return job_id  # main thread returns to menu; worker thread handles the rest


def accept_gaussian_blur() -> str:
    """
    Design behavior: AcceptGaussianBlur  [_isDesignFork: true]
    Accept an image to apply gaussian blur and send it to the worker to apply
    the blur with the jobid.
    Fork paths:
      → PresentMenuAndAcceptChoice  (main thread continues immediately)
      → ReceiveJobInWorker2         (worker 2 thread picks this up)
    """
    logger.info("[Behavior: AcceptGaussianBlur] Prompting user for image path")
    image_path = input("Image path: ").strip()
    job_id = str(uuid.uuid4())
    logger.info(
        f"[Behavior: AcceptGaussianBlur] Assigned job_id={job_id[:8]}... "
        f"image_path={image_path}"
    )
    logger.info(
        f"[Behavior: AcceptGaussianBlur] [FORK] Enqueuing job for Worker 2; "
        f"returning to PresentMenuAndAcceptChoice"
    )
    blur_queue.put({"job_id": job_id, "image_path": image_path})
    print(f"[Main]   Job {job_id[:8]}... submitted for gaussian blur.")
    return job_id


def accept_black_and_white() -> str:
    """
    Design behavior: AcceptBlackandWhite  [_isDesignFork: true]
    Accept an image to apply black and white filter and send it to the worker
    to apply black and white.
    Fork paths:
      → PresentMenuAndAcceptChoice  (main thread continues immediately)
      → ReceiveJobInWorker3         (worker 3 thread picks this up)
    """
    logger.info("[Behavior: AcceptBlackandWhite] Prompting user for image path")
    image_path = input("Image path: ").strip()
    job_id = str(uuid.uuid4())
    logger.info(
        f"[Behavior: AcceptBlackandWhite] Assigned job_id={job_id[:8]}... "
        f"image_path={image_path}"
    )
    logger.info(
        f"[Behavior: AcceptBlackandWhite] [FORK] Enqueuing job for Worker 3; "
        f"returning to PresentMenuAndAcceptChoice"
    )
    bw_queue.put({"job_id": job_id, "image_path": image_path})
    print(f"[Main]   Job {job_id[:8]}... submitted for black and white.")
    return job_id


# ===========================================================================
# WORKER 1 — Edge Detection
# ===========================================================================

def receive_job_in_worker1() -> dict | None:
    """
    Design behavior: ReceiveJobInWorker1
    Receive the job in worker 1. Blocks until a job is available.
    Goes to: ApplyEdgeDetection
    """
    logger.info("[Behavior: ReceiveJobInWorker1] Waiting for next job on edge_queue")
    job = edge_queue.get()
    if job is not _STOP:
        logger.info(
            f"[Behavior: ReceiveJobInWorker1] Received job {job['job_id'][:8]}... "
            f"image_path={job['image_path']}"
        )
    return job


def apply_edge_detection(job: dict) -> dict:
    """
    Design behavior: ApplyEdgeDetection
    Apply the edge detection to the image using Pillow's FIND_EDGES filter.
    Goes to: WriteToSharedDatabaseInWorker1
    """
    logger.info(f"[Behavior: ApplyEdgeDetection] Opening image: {job['image_path']}")
    img = Image.open(job["image_path"])
    logger.info("[Behavior: ApplyEdgeDetection] Applying FIND_EDGES filter")
    result = img.filter(ImageFilter.FIND_EDGES)
    output_path = _output_path(job["job_id"], "edge")
    logger.info(f"[Behavior: ApplyEdgeDetection] Saving result to: {output_path}")
    result.save(output_path)
    job["output_path"] = output_path
    return job


def write_to_shared_database_worker1(job: dict) -> None:
    """
    Design behavior: WriteToSharedDatabaseInWorker1
    Write the image to the shared database with the jobid for the result.
    Goes to: ReceiveJobInWorker1 (worker loop continues)
    """
    logger.info(
        f"[Behavior: WriteToSharedDatabaseInWorker1] Writing result for job "
        f"{job['job_id'][:8]}... to shared database → {job['output_path']}"
    )
    _write_result(job)
    logger.info(
        f"[Behavior: WriteToSharedDatabaseInWorker1] Done. "
        f"Looping back to ReceiveJobInWorker1."
    )


def worker1_loop() -> None:
    """Worker 1 thread: ReceiveJobInWorker1 → ApplyEdgeDetection → WriteToSharedDatabaseInWorker1 → (loop)"""
    while True:
        job = receive_job_in_worker1()
        if job is _STOP:
            logger.info("[Worker 1] Received stop signal. Exiting.")
            break
        try:
            job = apply_edge_detection(job)
            write_to_shared_database_worker1(job)
        except Exception as exc:
            _record_error(job, exc)


# ===========================================================================
# WORKER 2 — Gaussian Blur
# ===========================================================================

def receive_job_in_worker2() -> dict | None:
    """
    Design behavior: ReceiveJobInWorker2
    Receive the job in worker 2. Blocks until a job is available.
    Goes to: ApplyGaussianBlur
    """
    logger.info("[Behavior: ReceiveJobInWorker2] Waiting for next job on blur_queue")
    job = blur_queue.get()
    if job is not _STOP:
        logger.info(
            f"[Behavior: ReceiveJobInWorker2] Received job {job['job_id'][:8]}... "
            f"image_path={job['image_path']}"
        )
    return job


def apply_gaussian_blur(job: dict) -> dict:
    """
    Design behavior: ApplyGaussianBlur
    Apply the gaussian blur to the image using Pillow's GaussianBlur filter.
    Goes to: WriteToSharedDatabaseInWorker2
    """
    logger.info(f"[Behavior: ApplyGaussianBlur] Opening image: {job['image_path']}")
    img = Image.open(job["image_path"])
    logger.info("[Behavior: ApplyGaussianBlur] Applying GaussianBlur filter (radius=5)")
    result = img.filter(ImageFilter.GaussianBlur(radius=5))
    output_path = _output_path(job["job_id"], "blur")
    logger.info(f"[Behavior: ApplyGaussianBlur] Saving result to: {output_path}")
    result.save(output_path)
    job["output_path"] = output_path
    return job


def write_to_shared_database_worker2(job: dict) -> None:
    """
    Design behavior: WriteToSharedDatabaseInWorker2
    Write the result to a shared database in worker 2 with the jobid.
    Goes to: ReceiveJobInWorker2 (worker loop continues)
    """
    logger.info(
        f"[Behavior: WriteToSharedDatabaseInWorker2] Writing result for job "
        f"{job['job_id'][:8]}... to shared database → {job['output_path']}"
    )
    _write_result(job)
    logger.info(
        f"[Behavior: WriteToSharedDatabaseInWorker2] Done. "
        f"Looping back to ReceiveJobInWorker2."
    )


def worker2_loop() -> None:
    """Worker 2 thread: ReceiveJobInWorker2 → ApplyGaussianBlur → WriteToSharedDatabaseInWorker2 → (loop)"""
    while True:
        job = receive_job_in_worker2()
        if job is _STOP:
            logger.info("[Worker 2] Received stop signal. Exiting.")
            break
        try:
            job = apply_gaussian_blur(job)
            write_to_shared_database_worker2(job)
        except Exception as exc:
            _record_error(job, exc)


# ===========================================================================
# WORKER 3 — Black and White
# ===========================================================================

def receive_job_in_worker3() -> dict | None:
    """
    Design behavior: ReceiveJobInWorker3
    Receive the job in worker 3. Blocks until a job is available.
    Goes to: ApplyBlackAndWhite
    """
    logger.info("[Behavior: ReceiveJobInWorker3] Waiting for next job on bw_queue")
    job = bw_queue.get()
    if job is not _STOP:
        logger.info(
            f"[Behavior: ReceiveJobInWorker3] Received job {job['job_id'][:8]}... "
            f"image_path={job['image_path']}"
        )
    return job


def apply_black_and_white(job: dict) -> dict:
    """
    Design behavior: ApplyBlackAndWhite
    Apply a black and white (grayscale) conversion to the image.
    NOTE: The design's _description field for this behavior is empty; the
    algorithm is inferred from the behavior name and the menu description
    ("making it black and white"). Pillow's convert("L") is used.
    Goes to: WriteTheResultToSharedDatabaseInWorker3
    """
    logger.info(f"[Behavior: ApplyBlackAndWhite] Opening image: {job['image_path']}")
    img = Image.open(job["image_path"])
    logger.info("[Behavior: ApplyBlackAndWhite] Converting image to grayscale (L mode)")
    result = img.convert("L")
    output_path = _output_path(job["job_id"], "bw")
    logger.info(f"[Behavior: ApplyBlackAndWhite] Saving result to: {output_path}")
    result.save(output_path)
    job["output_path"] = output_path
    return job


def write_result_to_shared_database_worker3(job: dict) -> None:
    """
    Design behavior: WriteTheResultToSharedDatabaseInWorker3
    (Note: the original design node ID uses the typo "WOrker3".)
    Write the result to a shared database in worker 3.
    Goes to: ReceiveJobInWorker3 (worker loop continues)
    """
    logger.info(
        f"[Behavior: WriteTheResultToSharedDatabaseInWorker3] Writing result for job "
        f"{job['job_id'][:8]}... to shared database → {job['output_path']}"
    )
    _write_result(job)
    logger.info(
        f"[Behavior: WriteTheResultToSharedDatabaseInWorker3] Done. "
        f"Looping back to ReceiveJobInWorker3."
    )


def worker3_loop() -> None:
    """Worker 3 thread: ReceiveJobInWorker3 → ApplyBlackAndWhite → WriteTheResultToSharedDatabaseInWorker3 → (loop)"""
    while True:
        job = receive_job_in_worker3()
        if job is _STOP:
            logger.info("[Worker 3] Received stop signal. Exiting.")
            break
        try:
            job = apply_black_and_white(job)
            write_result_to_shared_database_worker3(job)
        except Exception as exc:
            _record_error(job, exc)


# ===========================================================================
# Shared helpers
# ===========================================================================

def _output_path(job_id: str, suffix: str) -> str:
    return os.path.join("output", f"{job_id}_{suffix}.png")


def _write_result(job: dict) -> None:
    """Write a completed job's result into the shared database."""
    with shared_db_lock:
        shared_db[job["job_id"]] = job["output_path"]
    print(f"[Worker] Job {job['job_id'][:8]}... done → {job['output_path']}")


def _record_error(job: dict, exc: Exception) -> None:
    with shared_db_lock:
        shared_db[job["job_id"]] = f"ERROR: {exc}"
    logger.error(
        f"[Worker] Job {job['job_id'][:8]}... FAILED: {exc}"
    )


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    logger.info("[Main] Starting image processor. Creating output directory.")
    os.makedirs("output", exist_ok=True)

    # Start the three worker threads (daemon so they exit when main exits)
    logger.info("[Main] Starting worker threads: Worker-1-EdgeDetection, Worker-2-GaussianBlur, Worker-3-BlackAndWhite")
    workers = [
        threading.Thread(target=worker1_loop, name="Worker-1-EdgeDetection", daemon=True),
        threading.Thread(target=worker2_loop, name="Worker-2-GaussianBlur",  daemon=True),
        threading.Thread(target=worker3_loop, name="Worker-3-BlackAndWhite", daemon=True),
    ]
    for w in workers:
        w.start()
        logger.info(f"[Main] Started thread: {w.name}")

    # Main thread: PresentMenuAndAcceptChoice loop
    while True:
        choice = present_menu_and_accept_choice()

        if choice == "1":
            accept_edge_detection()      # Fork → Worker 1; main returns to menu
        elif choice == "2":
            accept_gaussian_blur()       # Fork → Worker 2; main returns to menu
        elif choice == "3":
            accept_black_and_white()     # Fork → Worker 3; main returns to menu
        elif choice == "4":
            logger.info("[Main] User requested to view completed jobs")
            with shared_db_lock:
                if not shared_db:
                    print("No completed jobs yet.")
                else:
                    for jid, out in shared_db.items():
                        print(f"  {jid[:8]}...  →  {out}")
        elif choice == "5":
            logger.info("[Main] User requested exit. Sending stop signal to all workers.")
            # Signal workers to stop and wait for any in-flight jobs to finish
            edge_queue.put(_STOP)
            blur_queue.put(_STOP)
            bw_queue.put(_STOP)
            for w in workers:
                w.join(timeout=10)
            logger.info("[Main] All workers stopped. Exiting.")
            print("Goodbye.")
            break
        else:
            logger.warning(f"[Main] Invalid menu choice: '{choice}'")
            print("Invalid choice. Please enter 1–5.")


if __name__ == "__main__":
    main()
