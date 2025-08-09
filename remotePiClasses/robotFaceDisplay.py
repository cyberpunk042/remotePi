import math
import random
import logging
from typing import Tuple


class RobotFaceDisplay:
    """
    Draws and animates a simple robot face that can take over the screen.

    Features:
    - Fullscreen by default
    - Idle eye blinking
    - Pupil movement
    - Mouth idle breathing and speech animation

    Public flags (read every frame):
    - speaking: bool -> animate mouth like talking
    - expression: str in {"neutral", "happy", "sad", "angry"}
    """

    def __init__(
        self,
        fullscreen: bool = True,
        debug: bool = False,
        background_color: Tuple[int, int, int] = (8, 10, 18),
        face_color: Tuple[int, int, int] = (30, 144, 255),  # Dodger blue
        eye_white_color: Tuple[int, int, int] = (240, 240, 240),
        pupil_color: Tuple[int, int, int] = (25, 25, 25),
        mouth_color: Tuple[int, int, int] = (220, 64, 64),
    ) -> None:
        self.fullscreen = fullscreen
        self.debug = debug
        self.background_color = background_color
        self.face_color = face_color
        self.eye_white_color = eye_white_color
        self.pupil_color = pupil_color
        self.mouth_color = mouth_color

        # Runtime fields initialized in _initialize_display
        self.pg = None
        self.screen = None
        self.clock = None
        self.surface_width = 0
        self.surface_height = 0

        # Animation state
        self.time_since_last_blink_s = 0.0
        self.current_blink_duration_s = 0.0
        self.next_blink_in_s = self._random_blink_interval()
        self.blink_progress = 0.0  # 0=open, 1=closed
        self.pupil_phase = random.random() * math.tau
        self.idle_mouth_phase = random.random() * math.tau

        # Expression state
        self.expression = "neutral"

    def _random_blink_interval(self) -> float:
        return random.uniform(2.5, 6.0)

    def _initialize_display(self) -> None:
        import pygame as pg

        self.pg = pg
        pg.init()
        flags = pg.FULLSCREEN if self.fullscreen else 0
        info = pg.display.Info()
        width = info.current_w if self.fullscreen else 800
        height = info.current_h if self.fullscreen else 480
        self.screen = pg.display.set_mode((width, height), flags)
        pg.display.set_caption("Robot Face")
        self.clock = pg.time.Clock()
        self.surface_width = width
        self.surface_height = height
        logging.info(f"RobotFaceDisplay initialized: {width}x{height}, fullscreen={self.fullscreen}")

    def set_expression(self, expression: str) -> None:
        if expression in ("neutral", "happy", "sad", "angry"):
            self.expression = expression

    def _update_blink(self, delta_time_s: float) -> None:
        self.time_since_last_blink_s += delta_time_s
        if self.current_blink_duration_s > 0.0:
            # We are in a blink
            self.blink_progress += delta_time_s / self.current_blink_duration_s
            if self.blink_progress >= 1.0:
                # Blink complete
                self.blink_progress = 0.0
                self.current_blink_duration_s = 0.0
                self.time_since_last_blink_s = 0.0
                self.next_blink_in_s = self._random_blink_interval()
        else:
            # Not currently blinking; start a blink at random interval
            if self.time_since_last_blink_s >= self.next_blink_in_s:
                self.current_blink_duration_s = random.uniform(0.08, 0.14)
                self.blink_progress = 0.0001  # start closing

    def _blink_amount(self) -> float:
        # Easing: close then open symmetrical
        if self.current_blink_duration_s <= 0.0:
            return 0.0
        t = self.blink_progress
        if t <= 0.5:
            x = t / 0.5
        else:
            x = (1.0 - t) / 0.5
        # Smoothstep curve
        return max(0.0, min(1.0, x * x * (3.0 - 2.0 * x)))

    def _draw_face(self, speaking: bool, delta_time_s: float) -> None:
        pg = self.pg
        sw, sh = self.surface_width, self.surface_height
        self.screen.fill(self.background_color)

        # Face area
        face_margin = int(min(sw, sh) * 0.06)
        face_rect = pg.Rect(face_margin, face_margin, sw - 2 * face_margin, sh - 2 * face_margin)
        pg.draw.rect(self.screen, self.face_color, face_rect, border_radius=int(min(sw, sh) * 0.05))

        # Eyes parameters
        eye_radius = int(min(sw, sh) * 0.09)
        eye_offset_x = int(face_rect.width * 0.22)
        eye_center_y = int(face_rect.top + face_rect.height * 0.38)
        left_eye_center = (face_rect.centerx - eye_offset_x, eye_center_y)
        right_eye_center = (face_rect.centerx + eye_offset_x, eye_center_y)

        # Pupil parameters
        pupil_radius = int(eye_radius * 0.38)
        pupil_wobble = int(pupil_radius * 0.55)
        self.pupil_phase = (self.pupil_phase + delta_time_s * 0.8) % math.tau
        pupil_dx = int(math.cos(self.pupil_phase) * pupil_wobble)
        pupil_dy = int(math.sin(self.pupil_phase * 1.6) * (pupil_wobble * 0.45))

        # Blink
        self._update_blink(delta_time_s)
        blink_amt = self._blink_amount()

        def draw_eye(center: Tuple[int, int]) -> None:
            # Sclera
            pg.draw.circle(self.screen, self.eye_white_color, center, eye_radius)
            # Pupil
            pg.draw.circle(self.screen, self.pupil_color, (center[0] + pupil_dx, center[1] + pupil_dy), pupil_radius)
            # Eyelids (draw as rectangles covering from top and bottom)
            if blink_amt > 0.0:
                cover = int(eye_radius * blink_amt)
                # Top lid
                top_rect = pg.Rect(center[0] - eye_radius, center[1] - eye_radius, eye_radius * 2, cover)
                pg.draw.rect(self.screen, self.face_color, top_rect)
                # Bottom lid
                bot_rect = pg.Rect(center[0] - eye_radius, center[1] + eye_radius - cover, eye_radius * 2, cover)
                pg.draw.rect(self.screen, self.face_color, bot_rect)

        draw_eye(left_eye_center)
        draw_eye(right_eye_center)

        # Eyebrows / expression hint
        brow_length = int(eye_radius * 1.6)
        brow_thickness = max(2, int(eye_radius * 0.18))
        brow_y = eye_center_y - int(eye_radius * 1.4)
        angry_tilt = 0
        happy_arc = 0
        if self.expression == "angry":
            angry_tilt = int(eye_radius * 0.6)
        elif self.expression == "happy":
            happy_arc = int(eye_radius * 0.4)
        elif self.expression == "sad":
            happy_arc = -int(eye_radius * 0.3)
        # Left brow
        pg.draw.line(
            self.screen,
            self.pupil_color,
            (left_eye_center[0] - brow_length // 2, brow_y + angry_tilt),
            (left_eye_center[0] + brow_length // 2, brow_y + happy_arc),
            brow_thickness,
        )
        # Right brow
        pg.draw.line(
            self.screen,
            self.pupil_color,
            (right_eye_center[0] - brow_length // 2, brow_y + (-happy_arc)),
            (right_eye_center[0] + brow_length // 2, brow_y - angry_tilt),
            brow_thickness,
        )

        # Mouth
        mouth_width = int(face_rect.width * 0.42)
        mouth_height_base = int(face_rect.height * 0.05)
        mouth_center_y = int(face_rect.top + face_rect.height * 0.72)
        mouth_center_x = face_rect.centerx

        # Idle breathing or talking animation
        if speaking:
            self.idle_mouth_phase = (self.idle_mouth_phase + delta_time_s * 10.0) % math.tau
            amplitude = int(mouth_height_base * 1.8)
            mouth_height = int(mouth_height_base + (math.sin(self.idle_mouth_phase) * 0.5 + 0.5) * amplitude)
        else:
            self.idle_mouth_phase = (self.idle_mouth_phase + delta_time_s * 1.5) % math.tau
            amplitude = int(mouth_height_base * 0.7)
            mouth_height = int(mouth_height_base + (math.sin(self.idle_mouth_phase) * 0.5 + 0.5) * amplitude)

        mouth_rect = pg.Rect(
            mouth_center_x - mouth_width // 2,
            mouth_center_y - mouth_height // 2,
            mouth_width,
            mouth_height,
        )
        pg.draw.rect(self.screen, self.mouth_color, mouth_rect, border_radius=mouth_height // 2)

    def run(self, shared_properties) -> None:
        """Blocking loop. Call from a thread to not block asyncio.

        Exits when shared_properties.endOfProgram becomes truthy, or on ESC/QUIT.
        """
        try:
            self._initialize_display()
        except Exception as e:
            logging.exception("Failed to initialize RobotFaceDisplay:")
            return

        pg = self.pg
        try:
            while not getattr(shared_properties, "endOfProgram", 0):
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        shared_properties.endOfProgram = 1
                    elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                        shared_properties.endOfProgram = 1

                delta_time_s = self.clock.tick(60) / 1000.0
                speaking_flag = bool(getattr(shared_properties, "speaking", False))
                expr = str(getattr(shared_properties, "expression", "neutral"))
                self.set_expression(expr)
                self._draw_face(speaking=speaking_flag, delta_time_s=delta_time_s)
                pg.display.flip()
        finally:
            try:
                pg.display.quit()
                pg.quit()
            except Exception:
                pass

