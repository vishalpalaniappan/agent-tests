"""
Concurrent Image Processor — WebSocket Main Client
==================================================
This program implements the main-thread behaviors from the design:

  PresentMenuAndAcceptChoice (atomic, not a fork)
  AcceptEdgeDetection        (_isDesignFork: true)
  AcceptGaussianBlur         (_isDesignFork: true)
  AcceptBlackandWhite        (_isDesignFork: true)

Each Accept* behavior is a fork: it sends the job to the server over
WebSocket (which routes it to the appropriate worker) and immediately
returns to the menu — so the main client never blocks on processing.

The listener task runs concurrently in the same asyncio event loop and
prints job_complete notifications as they arrive from the server.

Run (after starting the server and all three workers):
    python image_processor_ws_main.py
"""

import asyncio
import json
import logging
import os
import uuid

import websockets

SERVER_URI = "ws://localhost:8765"

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/main.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Behavior: PresentMenuAndAcceptChoice
# ---------------------------------------------------------------------------

async def present_menu_and_accept_choice() -> str:
    """
    Design behavior: PresentMenuAndAcceptChoice
    Atomic (_isDesignFork: false).
    Present user with a choice to process an image by either running an edge
    detection algorithm on it, applying gaussian blur to it or making it
    black and white.
    Goes to: AcceptEdgeDetection | AcceptGaussianBlur | AcceptBlackandWhite
    """
    logger.info("[Behavior: PresentMenuAndAcceptChoice] Displaying menu options to user")
    print("\n=== Image Processor ===")
    print("1. Edge Detection")
    print("2. Gaussian Blur")
    print("3. Black and White")
    print("4. View completed jobs")
    print("5. Exit")
    loop = asyncio.get_running_loop()
    logger.info("[Behavior: PresentMenuAndAcceptChoice] Waiting for user input")
    choice = await loop.run_in_executor(None, lambda: input("Choice: ").strip())
    logger.info(f"[Behavior: PresentMenuAndAcceptChoice] User selected: '{choice}'")
    return choice


# ---------------------------------------------------------------------------
# Behavior: AcceptEdgeDetection  [_isDesignFork: true]
# ---------------------------------------------------------------------------

async def accept_edge_detection(ws) -> str:
    """
    Design behavior: AcceptEdgeDetection  [_isDesignFork: true]
    Accept an image to apply edge detection and send it to the worker to
    apply the edge detection.
    Fork paths:
      → PresentMenuAndAcceptChoice  (this coroutine returns; main loop continues)
      → ReceiveJobInWorker1         (server routes job to Worker 1 via WebSocket)
    """
    logger.info("[Behavior: AcceptEdgeDetection] Prompting user for image path")
    loop = asyncio.get_running_loop()
    image_path = await loop.run_in_executor(None, lambda: input("Image path: ").strip())
    job_id = str(uuid.uuid4())
    logger.info(
        f"[Behavior: AcceptEdgeDetection] Assigned job_id={job_id[:8]}... "
        f"image_path={image_path}"
    )
    logger.info(
        f"[Behavior: AcceptEdgeDetection] [FORK] Sending job to server for Worker 1; "
        f"returning to menu (PresentMenuAndAcceptChoice)"
    )
    await ws.send(json.dumps({
        "type":       "submit",
        "job_type":   "edge",
        "job_id":     job_id,
        "image_path": image_path,
    }))
    print(f"[Main] Job {job_id[:8]}... submitted for edge detection.")
    return job_id


# ---------------------------------------------------------------------------
# Behavior: AcceptGaussianBlur  [_isDesignFork: true]
# ---------------------------------------------------------------------------

async def accept_gaussian_blur(ws) -> str:
    """
    Design behavior: AcceptGaussianBlur  [_isDesignFork: true]
    Accept an image to apply gaussian blur and send it to the worker to
    apply the blur with the jobid.
    Fork paths:
      → PresentMenuAndAcceptChoice  (this coroutine returns; main loop continues)
      → ReceiveJobInWorker2         (server routes job to Worker 2 via WebSocket)
    """
    logger.info("[Behavior: AcceptGaussianBlur] Prompting user for image path")
    loop = asyncio.get_running_loop()
    image_path = await loop.run_in_executor(None, lambda: input("Image path: ").strip())
    job_id = str(uuid.uuid4())
    logger.info(
        f"[Behavior: AcceptGaussianBlur] Assigned job_id={job_id[:8]}... "
        f"image_path={image_path}"
    )
    logger.info(
        f"[Behavior: AcceptGaussianBlur] [FORK] Sending job to server for Worker 2; "
        f"returning to menu (PresentMenuAndAcceptChoice)"
    )
    await ws.send(json.dumps({
        "type":       "submit",
        "job_type":   "blur",
        "job_id":     job_id,
        "image_path": image_path,
    }))
    print(f"[Main] Job {job_id[:8]}... submitted for gaussian blur.")
    return job_id


# ---------------------------------------------------------------------------
# Behavior: AcceptBlackandWhite  [_isDesignFork: true]
# ---------------------------------------------------------------------------

async def accept_black_and_white(ws) -> str:
    """
    Design behavior: AcceptBlackandWhite  [_isDesignFork: true]
    Accept an image to apply black and white filter and send it to the
    worker to apply black and white.
    Fork paths:
      → PresentMenuAndAcceptChoice  (this coroutine returns; main loop continues)
      → ReceiveJobInWorker3         (server routes job to Worker 3 via WebSocket)
    """
    logger.info("[Behavior: AcceptBlackandWhite] Prompting user for image path")
    loop = asyncio.get_running_loop()
    image_path = await loop.run_in_executor(None, lambda: input("Image path: ").strip())
    job_id = str(uuid.uuid4())
    logger.info(
        f"[Behavior: AcceptBlackandWhite] Assigned job_id={job_id[:8]}... "
        f"image_path={image_path}"
    )
    logger.info(
        f"[Behavior: AcceptBlackandWhite] [FORK] Sending job to server for Worker 3; "
        f"returning to menu (PresentMenuAndAcceptChoice)"
    )
    await ws.send(json.dumps({
        "type":       "submit",
        "job_type":   "bw",
        "job_id":     job_id,
        "image_path": image_path,
    }))
    print(f"[Main] Job {job_id[:8]}... submitted for black and white.")
    return job_id


# ---------------------------------------------------------------------------
# Background listener (receives job_complete notifications from the server)
# ---------------------------------------------------------------------------

async def listen_for_notifications(ws) -> None:
    """Receive and display messages pushed by the server."""
    try:
        async for raw in ws:
            msg = json.loads(raw)
            mtype = msg.get("type")
            if mtype == "registered":
                logger.info(f"[Main] Registered with server as role='{msg.get('role')}'")
            elif mtype == "job_complete":
                job_id = msg["job_id"]
                if msg.get("error"):
                    logger.error(
                        f"[Behavior: WriteToSharedDatabase] "
                        f"Job {job_id[:8]}... FAILED: {msg['error']}"
                    )
                    print(f"\n[✗] Job {job_id[:8]}... FAILED: {msg['error']}")
                else:
                    logger.info(
                        f"[Behavior: WriteToSharedDatabase] "
                        f"Job {job_id[:8]}... completed → {msg['output_path']}"
                    )
                    print(f"\n[✓] Job {job_id[:8]}... done → {msg['output_path']}")
            elif mtype == "results":
                data = msg.get("data", {})
                if not data:
                    print("No completed jobs yet.")
                else:
                    for jid, info in data.items():
                        status = info.get("status", "?")
                        out = info.get("output_path") or info.get("error", "?")
                        print(f"  {jid[:8]}...  [{status}]  →  {out}")
    except websockets.exceptions.ConnectionClosed:
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info(f"[Main] Connecting to WebSocket server at {SERVER_URI}")
    async with websockets.connect(SERVER_URI) as ws:
        logger.info("[Main] Connected. Registering as main client.")
        await ws.send(json.dumps({"type": "register_main"}))

        # Start the notification listener as a concurrent asyncio task
        listener = asyncio.create_task(listen_for_notifications(ws))

        logger.info("[Behavior: PresentMenuAndAcceptChoice] Starting menu loop")
        while True:
            choice = await present_menu_and_accept_choice()

            if choice == "1":
                # [_isDesignFork: true] → fork to Worker 1, return to menu
                await accept_edge_detection(ws)
            elif choice == "2":
                # [_isDesignFork: true] → fork to Worker 2, return to menu
                await accept_gaussian_blur(ws)
            elif choice == "3":
                # [_isDesignFork: true] → fork to Worker 3, return to menu
                await accept_black_and_white(ws)
            elif choice == "4":
                logger.info("[Main] Querying server for completed jobs")
                await ws.send(json.dumps({"type": "query_results"}))
                await asyncio.sleep(0.2)  # give listener time to print
            elif choice == "5":
                logger.info("[Main] User requested exit")
                print("Goodbye.")
                break
            else:
                print("Invalid choice. Please enter 1–5.")

        listener.cancel()


if __name__ == "__main__":
    asyncio.run(main())
