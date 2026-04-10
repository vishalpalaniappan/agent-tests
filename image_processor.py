"""
Concurrent Image Processor
==========================
Implemented directly from concurrent_design_only_behaviors.dal.

Design → Code mapping
---------------------
Each function below corresponds to a named behavior node in the design graph.
The three "Accept" behaviors are marked _isDesignFork:true in the design,
meaning each one splits into two concurrent paths:
  1. The main thread immediately returns to PresentMenuAndAcceptChoice.
  2. A dedicated worker thread continues with ReceiveJobInWorker → Apply → WriteToSharedDatabase.

This is realised with Python threads and per-worker queues:
  - The main thread drives the menu loop.
  - Worker 1 handles edge-detection jobs (queue: edge_queue).
  - Worker 2 handles gaussian-blur jobs  (queue: blur_queue).
  - Worker 3 handles black-and-white jobs (queue: bw_queue).

The "shared database" from the design is an in-memory dictionary protected by
a threading.Lock so that all three workers can write results concurrently and
the main thread can read them safely.
"""

import os
import sys
import threading
import queue
import uuid

from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Shared database (behaviour: WriteToSharedDatabase*)
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
    print("\n=== Image Processor ===")
    print("1. Edge Detection")
    print("2. Gaussian Blur")
    print("3. Black and White")
    print("4. View completed jobs")
    print("5. Exit")
    return input("Choice: ").strip()


def accept_edge_detection() -> str:
    """
    Design behavior: AcceptEdgeDetection  [_isDesignFork: true]
    Accept an image to apply edge detection and send it to the worker to apply
    the edge detection.
    Fork paths:
      → PresentMenuAndAcceptChoice  (main thread continues immediately)
      → ReceiveJobInWorker1         (worker 1 thread picks this up)
    """
    image_path = input("Image path: ").strip()
    job_id = str(uuid.uuid4())
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
    image_path = input("Image path: ").strip()
    job_id = str(uuid.uuid4())
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
    image_path = input("Image path: ").strip()
    job_id = str(uuid.uuid4())
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
    return edge_queue.get()


def apply_edge_detection(job: dict) -> dict:
    """
    Design behavior: ApplyEdgeDetection
    Apply the edge detection to the image using Pillow's FIND_EDGES filter.
    Goes to: WriteToSharedDatabaseInWorker1
    """
    img = Image.open(job["image_path"])
    result = img.filter(ImageFilter.FIND_EDGES)
    output_path = _output_path(job["job_id"], "edge")
    result.save(output_path)
    job["output_path"] = output_path
    return job


def write_to_shared_database_worker1(job: dict) -> None:
    """
    Design behavior: WriteToSharedDatabaseInWorker1
    Write the image to the shared database with the jobid for the result.
    Goes to: ReceiveJobInWorker1 (worker loop continues)
    """
    _write_result(job)


def worker1_loop() -> None:
    """Worker 1 thread: ReceiveJobInWorker1 → ApplyEdgeDetection → WriteToSharedDatabaseInWorker1 → (loop)"""
    while True:
        job = receive_job_in_worker1()
        if job is _STOP:
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
    return blur_queue.get()


def apply_gaussian_blur(job: dict) -> dict:
    """
    Design behavior: ApplyGaussianBlur
    Apply the gaussian blur to the image using Pillow's GaussianBlur filter.
    Goes to: WriteToSharedDatabaseInWorker2
    """
    img = Image.open(job["image_path"])
    result = img.filter(ImageFilter.GaussianBlur(radius=5))
    output_path = _output_path(job["job_id"], "blur")
    result.save(output_path)
    job["output_path"] = output_path
    return job


def write_to_shared_database_worker2(job: dict) -> None:
    """
    Design behavior: WriteToSharedDatabaseInWorker2
    Write the result to a shared database in worker 2 with the jobid.
    Goes to: ReceiveJobInWorker2 (worker loop continues)
    """
    _write_result(job)


def worker2_loop() -> None:
    """Worker 2 thread: ReceiveJobInWorker2 → ApplyGaussianBlur → WriteToSharedDatabaseInWorker2 → (loop)"""
    while True:
        job = receive_job_in_worker2()
        if job is _STOP:
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
    return bw_queue.get()


def apply_black_and_white(job: dict) -> dict:
    """
    Design behavior: ApplyBlackAndWhite
    Apply a black and white (grayscale) conversion to the image.
    NOTE: The design's _description field for this behavior is empty; the
    algorithm is inferred from the behavior name and the menu description
    ("making it black and white"). Pillow's convert("L") is used.
    Goes to: WriteTheResultToSharedDatabaseInWorker3
    """
    img = Image.open(job["image_path"])
    result = img.convert("L")
    output_path = _output_path(job["job_id"], "bw")
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
    _write_result(job)


def worker3_loop() -> None:
    """Worker 3 thread: ReceiveJobInWorker3 → ApplyBlackAndWhite → WriteTheResultToSharedDatabaseInWorker3 → (loop)"""
    while True:
        job = receive_job_in_worker3()
        if job is _STOP:
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
    print(f"[Worker] Job {job['job_id'][:8]}... FAILED: {exc}", file=sys.stderr)


# ===========================================================================
# Entry point
# ===========================================================================

def main() -> None:
    os.makedirs("output", exist_ok=True)

    # Start the three worker threads (daemon so they exit when main exits)
    workers = [
        threading.Thread(target=worker1_loop, name="Worker-1-EdgeDetection", daemon=True),
        threading.Thread(target=worker2_loop, name="Worker-2-GaussianBlur",  daemon=True),
        threading.Thread(target=worker3_loop, name="Worker-3-BlackAndWhite", daemon=True),
    ]
    for w in workers:
        w.start()

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
            with shared_db_lock:
                if not shared_db:
                    print("No completed jobs yet.")
                else:
                    for jid, out in shared_db.items():
                        print(f"  {jid[:8]}...  →  {out}")
        elif choice == "5":
            # Signal workers to stop and wait for any in-flight jobs to finish
            edge_queue.put(_STOP)
            blur_queue.put(_STOP)
            bw_queue.put(_STOP)
            for w in workers:
                w.join(timeout=10)
            print("Goodbye.")
            break
        else:
            print("Invalid choice. Please enter 1–5.")


if __name__ == "__main__":
    main()
