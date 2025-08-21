import asyncio
import logging
import threading
import time
from typing import Optional


class CameraStreamer:
    """
    Captures frames from a camera device and serves them as an MJPEG stream over HTTP.

    - Uses OpenCV (`cv2.VideoCapture`) for portability.
    - Exposes two HTTP endpoints via aiohttp when started:
      - `/camera.mjpg`: continuous multipart/x-mixed-replace MJPEG stream
      - `/snapshot.jpg`: single JPEG snapshot

    Lifecycle:
      - Call `await start(host, port)` to start the HTTP server and the capture thread
      - Call `await stop()` to stop the server and release the camera
    """

    def __init__(
        self,
        camera_index: int = 0,
        frame_width: int = 640,
        frame_height: int = 480,
        target_fps: int = 20,
        jpeg_quality: int = 80,
        debug: bool = False,
    ) -> None:
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = max(1, target_fps)
        self.jpeg_quality = max(1, min(100, jpeg_quality))
        self.debug = debug

        self._cv2 = None  # Lazy import cv2
        self._cap = None
        self._capture_thread: Optional[threading.Thread] = None
        self._capture_stop = threading.Event()
        self._latest_jpeg_bytes: Optional[bytes] = None
        self._latest_lock = threading.Lock()

        # aiohttp server members
        self._aiohttp_web = None
        self._aiohttp_runner = None
        self._aiohttp_site = None
        self._server_started = False

    def _ensure_cv2(self) -> bool:
        if self._cv2 is not None:
            return True
        try:
            import cv2  # type: ignore
        except Exception as e:
            logging.error("OpenCV (cv2) is required for CameraStreamer but failed to import: %s", e)
            return False
        self._cv2 = cv2
        return True

    def _open_capture(self) -> bool:
        if not self._ensure_cv2():
            return False
        try:
            self._cap = self._cv2.VideoCapture(self.camera_index)
            if not self._cap or not self._cap.isOpened():
                logging.error("Failed to open camera device index %s", self.camera_index)
                return False
            # Configure resolution and FPS
            self._cap.set(self._cv2.CAP_PROP_FRAME_WIDTH, float(self.frame_width))
            self._cap.set(self._cv2.CAP_PROP_FRAME_HEIGHT, float(self.frame_height))
            self._cap.set(self._cv2.CAP_PROP_FPS, float(self.target_fps))
            if self.debug:
                logging.info(
                    "Camera opened: index=%s, %sx%s @ %sfps",
                    self.camera_index,
                    self.frame_width,
                    self.frame_height,
                    self.target_fps,
                )
            return True
        except Exception:
            logging.exception("Exception while opening camera device")
            return False

    def _close_capture(self) -> None:
        try:
            if self._cap is not None:
                self._cap.release()
        except Exception:
            pass
        self._cap = None

    def _capture_loop(self) -> None:
        assert self._cv2 is not None
        frame_interval_s = 1.0 / float(self.target_fps)
        encode_params = [self._cv2.IMWRITE_JPEG_QUALITY, int(self.jpeg_quality)]
        while not self._capture_stop.is_set():
            start = time.time()
            try:
                if self._cap is None:
                    if not self._open_capture():
                        time.sleep(1.0)
                        continue
                ok, frame = self._cap.read()
                if not ok or frame is None:
                    if self.debug:
                        logging.warning("Camera read failed; retrying")
                    time.sleep(0.05)
                    continue
                ok, buf = self._cv2.imencode(".jpg", frame, encode_params)
                if ok:
                    data = buf.tobytes()
                    with self._latest_lock:
                        self._latest_jpeg_bytes = data
                else:
                    if self.debug:
                        logging.warning("JPEG encode failed")
            except Exception:
                logging.exception("Error in camera capture loop")
            finally:
                elapsed = time.time() - start
                sleep_s = max(0.0, frame_interval_s - elapsed)
                if sleep_s > 0:
                    time.sleep(sleep_s)

    async def start(self, host: str = "0.0.0.0", port: int = 8081) -> None:
        if self._server_started:
            return

        # Start capture thread first
        if not self._ensure_cv2():
            raise RuntimeError("cv2 not available; cannot start CameraStreamer")
        self._capture_stop.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_loop, name="CameraCaptureThread", daemon=True
        )
        self._capture_thread.start()

        # Start aiohttp server
        try:
            from aiohttp import web  # type: ignore
        except Exception as e:
            logging.error("aiohttp is required for CameraStreamer HTTP server but failed to import: %s", e)
            raise

        async def snapshot_handler(_: "web.Request") -> "web.Response":
            content = self._get_latest_jpeg()
            if content is None:
                return web.Response(status=503, text="No frame available")
            return web.Response(body=content, content_type="image/jpeg")

        async def mjpeg_handler(_: "web.Request") -> "web.StreamResponse":
            boundary = "frame"
            resp = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": f"multipart/x-mixed-replace; boundary={boundary}"
                },
            )
            await resp.prepare(_)
            try:
                # Send frames until client disconnects
                while True:
                    frame = self._get_latest_jpeg()
                    if frame is None:
                        await asyncio.sleep(0.02)
                        continue
                    part = (
                        f"--{boundary}\r\n"
                        f"Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(frame)}\r\n\r\n"
                    ).encode("ascii") + frame + b"\r\n"
                    await resp.write(part)
                    await asyncio.sleep(1.0 / float(self.target_fps))
            except asyncio.CancelledError:
                raise
            except Exception:
                # Client disconnected or other error
                pass
            finally:
                try:
                    await resp.write_eof()
                except Exception:
                    pass
            return resp

        app = web.Application()
        app.router.add_get("/snapshot.jpg", snapshot_handler)
        app.router.add_get("/camera.mjpg", mjpeg_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        self._aiohttp_web = web
        self._aiohttp_runner = runner
        self._aiohttp_site = site
        self._server_started = True
        logging.info("Camera stream server running on %s:%s", host, port)

    async def stop(self) -> None:
        # Stop HTTP server
        if self._server_started and self._aiohttp_runner is not None:
            try:
                await self._aiohttp_runner.cleanup()
            except Exception:
                pass
        self._aiohttp_site = None
        self._aiohttp_runner = None
        self._server_started = False

        # Stop capture thread
        self._capture_stop.set()
        if self._capture_thread is not None and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._capture_thread = None
        self._close_capture()
        logging.info("Camera stream server stopped")

    def _get_latest_jpeg(self) -> Optional[bytes]:
        with self._latest_lock:
            return self._latest_jpeg_bytes

