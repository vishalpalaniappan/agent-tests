"""
Concurrent Image Processor — WebSocket Server
==============================================
This is the central hub of the WebSocket-based implementation.

Design behaviors handled here:
  - Routes jobs submitted by the main client to the appropriate worker,
    implementing the server-side of the fork (AcceptEdgeDetection,
    AcceptGaussianBlur, AcceptBlackandWhite).
  - Acts as the shared database for WriteToSharedDatabase* behaviors:
    stores results from workers and makes them queryable.

Architecture (separate programs connected over WebSocket):
  image_processor_ws_server.py  ← run this first
  image_processor_ws_main.py    ← menu / Accept* behaviors
  image_processor_ws_worker.py  ← ReceiveJob / Apply / WriteToSharedDB per worker

Message protocol (all JSON):
  Client → Server:
    {"type": "register_main"}
    {"type": "register_worker", "worker_type": "edge"|"blur"|"bw"}
    {"type": "submit", "job_type": "...", "job_id": "...", "image_path": "..."}
    {"type": "result", "job_id": "...", "output_path": "..."}
    {"type": "result", "job_id": "...", "error": "..."}
    {"type": "query_results"}
  Server → Client:
    {"type": "registered", "role": "main"|"worker"}
    {"type": "job", "job_id": "...", "image_path": "..."}
    {"type": "results", "data": {...}}
    {"type": "job_complete", "job_id": "...", "output_path": "...", "error": ""}

Run:
    python image_processor_ws_server.py
"""

import asyncio
import json
import logging
import os

import websockets

HOST = "localhost"
PORT = 8765

os.makedirs("logs", exist_ok=True)
os.makedirs("output", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/server.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("server")

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

# Shared database: job_id → {"status": "done"|"error", "output_path"?: "...", "error"?: "..."}
shared_db: dict = {}

# Connected workers: worker_type → websocket
workers: dict = {}

# Connected main clients
main_clients: set = set()

# Pending job queues (buffers jobs until the worker type connects)
pending_queues: dict[str, asyncio.Queue] = {
    "edge": asyncio.Queue(),
    "blur": asyncio.Queue(),
    "bw":   asyncio.Queue(),
}


# ---------------------------------------------------------------------------
# Background routing tasks (one per worker type)
# ---------------------------------------------------------------------------

async def route_jobs(worker_type: str) -> None:
    """
    Background task that implements the server-side of the fork:
    pulls jobs from pending_queues[worker_type] and forwards them to the
    appropriate connected worker.

    This task stays alive for the lifetime of the server so that jobs
    submitted before a worker connects are delivered once the worker arrives.
    """
    logger.info(
        f"[Behavior: ReceiveJobInWorker({worker_type})] "
        f"Job routing task started for worker type '{worker_type}'"
    )
    while True:
        logger.info(
            f"[Behavior: ReceiveJobInWorker({worker_type})] "
            f"Routing task waiting for next job in queue"
        )
        job = await pending_queues[worker_type].get()

        logger.info(
            f"[Behavior: AcceptEdgeDetection/AcceptGaussianBlur/AcceptBlackandWhite] "
            f"[FORK] Job {job['job_id'][:8]}... dequeued for worker '{worker_type}', "
            f"waiting for worker to be available"
        )

        # Block until a worker of this type connects
        while worker_type not in workers:
            logger.warning(
                f"[Server] Worker '{worker_type}' not yet connected — retrying in 0.5s"
            )
            await asyncio.sleep(0.5)

        ws = workers[worker_type]
        try:
            logger.info(
                f"[Behavior: ReceiveJobInWorker({worker_type})] "
                f"Dispatching job {job['job_id'][:8]}... to worker '{worker_type}'"
            )
            await ws.send(json.dumps({"type": "job", **job}))
        except Exception as exc:
            logger.error(
                f"[Server] Failed to dispatch job {job['job_id'][:8]}... "
                f"to worker '{worker_type}': {exc}. Re-queuing."
            )
            await pending_queues[worker_type].put(job)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def notify_main_clients(message: dict) -> None:
    """Push a notification to all connected main clients."""
    for ws in list(main_clients):
        try:
            await ws.send(json.dumps(message))
        except Exception:
            main_clients.discard(ws)


# ---------------------------------------------------------------------------
# Connection handler
# ---------------------------------------------------------------------------

async def handle_connection(websocket) -> None:
    """Handle a single WebSocket connection (either main client or worker)."""
    role = None
    worker_type = None

    try:
        async for raw in websocket:
            msg = json.loads(raw)
            mtype = msg.get("type")

            # ---- Registration ----
            if mtype == "register_main":
                role = "main"
                main_clients.add(websocket)
                logger.info("[Server] Main client registered")
                await websocket.send(json.dumps({"type": "registered", "role": "main"}))

            elif mtype == "register_worker":
                role = "worker"
                worker_type = msg["worker_type"]
                workers[worker_type] = websocket
                logger.info(f"[Server] Worker '{worker_type}' registered")
                await websocket.send(
                    json.dumps({"type": "registered", "role": "worker", "worker_type": worker_type})
                )

            # ---- Job submission from main client (fork point) ----
            elif mtype == "submit":
                job_type = msg["job_type"]
                job = {
                    "job_id":     msg["job_id"],
                    "image_path": msg["image_path"],
                    "job_type":   job_type,
                }
                logger.info(
                    f"[Behavior: AcceptEdgeDetection/AcceptGaussianBlur/AcceptBlackandWhite] "
                    f"[FORK] Job {job['job_id'][:8]}... type='{job_type}' received from main client, "
                    f"enqueueing for worker"
                )
                await pending_queues[job_type].put(job)

            # ---- Result from worker (WriteToSharedDatabase*) ----
            elif mtype == "result":
                job_id = msg["job_id"]
                error = msg.get("error")
                output_path = msg.get("output_path", "")

                if error:
                    shared_db[job_id] = {"status": "error", "error": error}
                    logger.error(
                        f"[Behavior: WriteToSharedDatabase] "
                        f"Job {job_id[:8]}... ERROR stored in shared database: {error}"
                    )
                else:
                    shared_db[job_id] = {"status": "done", "output_path": output_path}
                    logger.info(
                        f"[Behavior: WriteToSharedDatabase] "
                        f"Job {job_id[:8]}... result written to shared database → {output_path}"
                    )

                await notify_main_clients({
                    "type":        "job_complete",
                    "job_id":      job_id,
                    "output_path": output_path,
                    "error":       error or "",
                })

            # ---- Results query from main client ----
            elif mtype == "query_results":
                logger.info("[Server] Main client queried shared database")
                await websocket.send(json.dumps({"type": "results", "data": shared_db}))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if role == "main":
            main_clients.discard(websocket)
            logger.info("[Server] Main client disconnected")
        elif role == "worker" and worker_type:
            workers.pop(worker_type, None)
            logger.info(f"[Server] Worker '{worker_type}' disconnected")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    # Start one routing background task per worker type
    for wt in ("edge", "blur", "bw"):
        asyncio.create_task(route_jobs(wt))

    logger.info(f"[Server] Starting WebSocket server on ws://{HOST}:{PORT}")
    async with websockets.serve(handle_connection, HOST, PORT):
        logger.info("[Server] Ready — waiting for connections")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
