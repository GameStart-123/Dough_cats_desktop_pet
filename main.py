import math
import random
import tkinter as tk
from ctypes import Structure, byref, windll
from ctypes.wintypes import LONG


TRANSPARENT = "#ff00ff"
CAT_WIDTH = 112
CAT_HEIGHT = 96
WINDOW_WIDTH = 210
WINDOW_HEIGHT = 172
GROUND_Y = 142


class Rect(Structure):
    _fields_ = [
        ('left', LONG),
        ('top', LONG),
        ('right', LONG),
        ('bottom', LONG),
    ]


class DoughCat:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("面团猫桌宠")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT)

        try:
            self.root.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            bg=TRANSPARENT,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.always_on_top = True
        self.walking_enabled = True
        self.bubbles_enabled = True
        self.appearance = "cream"
        self.themes = {
            "cream": {
                "menu_label": "小黑猫面团",
                "body": "#fff3df",
                "body_light": "#fff9ec",
                "shadow": "#efdcc5",
                "outline": "#8b6b55",
                "inner_ear": "#f6b3bf",
                "eye": "#3a2a24",
                "nose": "#8b6b55",
                "mouth": "#3a2a24",
                "blush": "#f6b3bf",
            },
            "black": {
                "menu_label": "奶白面团猫",
                "body": "#252225",
                "body_light": "#343037",
                "shadow": "#151316",
                "outline": "#0f0d10",
                "inner_ear": "#8b5c72",
                "eye": "#ffd86b",
                "nose": "#f0a6b5",
                "mouth": "#ffe7b7",
                "blush": "#b36b82",
            },
        }
        self.state = "idle"
        self.face = "normal"
        self.facing = 1
        self.tick = 0
        self.blink_until = 0
        self.next_blink = self._future_tick(90, 210)
        self.next_walk = self._future_tick(450, 1350)
        self.bubble_text = ""
        self.bubble_until = 0
        self.press_x = 0
        self.press_y = 0
        self.press_root_x = 0
        self.press_root_y = 0
        self.window_start_x = 0
        self.window_start_y = 0
        self.dragging = False
        self.squash = 0.0
        self.stretch_x = 0.0
        self.stretch_y = 0.0
        self.walk_target_x = 0
        self.walk_target_y = 0
        self.walk_vx = 0.0
        self.walk_vy = 0.0

        self.click_lines = [
            "miao~",
            "喵？",
            "我在",
            "写代码辛苦啦",
            "bug 会好的",
        ]
        self.pet_lines = [
            "miao miao~",
            "舒服喵",
            "再摸一下",
            "软乎乎",
            "被rua了",
            "呼噜呼噜",
        ]
        self.walk_lines = [
            "散步喵",
            "换个位置",
            "走两步",
        ]

        self.menu = tk.Menu(self.root, tearoff=0)
        self._build_menu()

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<ButtonPress-3>", self._show_menu)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self._place_bottom_right()
        self._draw()
        self._animate()

    def run(self) -> None:
        self.root.mainloop()

    def _future_tick(self, low: int, high: int) -> int:
        return self.tick + random.randint(low, high)

    def _build_menu(self) -> None:
        self.menu.delete(0, "end")
        self.menu.add_command(
            label="取消置顶" if self.always_on_top else "置顶",
            command=self._toggle_topmost,
        )
        self.menu.add_command(
            label="暂停走动" if self.walking_enabled else "恢复走动",
            command=self._toggle_walking,
        )
        self.menu.add_command(
            label="隐藏气泡" if self.bubbles_enabled else "显示气泡",
            command=self._toggle_bubbles,
        )
        self.menu.add_command(
            label=f"切换为{self.themes[self.appearance]['menu_label']}",
            command=self._toggle_appearance,
        )
        self.menu.add_command(label="重置位置", command=self._place_bottom_right)
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.root.destroy)

    def _toggle_topmost(self) -> None:
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        self._build_menu()

    def _toggle_walking(self) -> None:
        self.walking_enabled = not self.walking_enabled
        if not self.walking_enabled and self.state == "walk":
            self.state = "idle"
        self.next_walk = self._future_tick(450, 1350)
        self._build_menu()

    def _toggle_bubbles(self) -> None:
        self.bubbles_enabled = not self.bubbles_enabled
        if not self.bubbles_enabled:
            self.bubble_text = ""
        self._build_menu()

    def _toggle_appearance(self) -> None:
        self.appearance = "black" if self.appearance == "cream" else "cream"
        self._build_menu()
        self._draw()

    def _colors(self) -> dict[str, str]:
        return self.themes[self.appearance]

    def _show_menu(self, event: tk.Event) -> None:
        self._build_menu()
        self.menu.tk_popup(event.x_root, event.y_root)

    def _place_bottom_right(self) -> None:
        self.root.update_idletasks()
        left, top, right, bottom = self._get_work_area()
        x = right - WINDOW_WIDTH - 48
        y = bottom - WINDOW_HEIGHT - 36
        x, y = self._clamp_window_position(x, y)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _get_work_area(self) -> tuple[int, int, int, int]:
        rect = Rect()
        try:
            windll.user32.SystemParametersInfoW(0x0030, 0, byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _clamp_window_position(self, x: float, y: float) -> tuple[int, int]:
        left, top, right, bottom = self._get_work_area()
        max_x = max(left, right - WINDOW_WIDTH)
        max_y = max(top, bottom - WINDOW_HEIGHT)
        clamped_x = min(max(int(round(x)), left), max_x)
        clamped_y = min(max(int(round(y)), top), max_y)
        return clamped_x, clamped_y

    def _on_press(self, event: tk.Event) -> None:
        self.press_x = event.x
        self.press_y = event.y
        self.press_root_x = event.x_root
        self.press_root_y = event.y_root
        self.window_start_x = self.root.winfo_x()
        self.window_start_y = self.root.winfo_y()
        self.dragging = False
        self.state = "petting"
        self.face = "happy"
        self.squash = 1.0
        self.stretch_x = 0.0
        self.stretch_y = 0.0

    def _on_motion(self, event: tk.Event) -> None:
        dx = event.x_root - self.press_root_x
        dy = event.y_root - self.press_root_y
        if abs(dx) + abs(dy) > 8:
            self.dragging = True
            x, y = self._clamp_window_position(
                self.window_start_x + dx,
                self.window_start_y + dy,
            )
            self.root.geometry(f"+{x}+{y}")
        self.stretch_x = max(-1.0, min(1.0, dx / 90))
        self.stretch_y = max(-1.0, min(1.0, dy / 90))
        self.squash = 1.0

    def _on_release(self, event: tk.Event) -> None:
        if self.dragging:
            self._say(random.choice(self.pet_lines))
        else:
            self._say(random.choice(self.click_lines))
        self.state = "idle"
        self.face = "normal"
        self.dragging = False
        self.squash = 0.0
        self.stretch_x = 0.0
        self.stretch_y = 0.0
        self.next_walk = self._future_tick(450, 1350)

    def _say(self, text: str, duration: int = 75) -> None:
        if not self.bubbles_enabled:
            return
        self.bubble_text = text
        self.bubble_until = self.tick + duration

    def _animate(self) -> None:
        self.tick += 1
        self._update_blink()
        self._update_walk()

        self.squash *= 0.72
        self.stretch_x *= 0.72
        self.stretch_y *= 0.72
        if abs(self.squash) < 0.02:
            self.squash = 0.0
        if abs(self.stretch_x) < 0.02:
            self.stretch_x = 0.0
        if abs(self.stretch_y) < 0.02:
            self.stretch_y = 0.0

        if self.tick > self.bubble_until:
            self.bubble_text = ""
        self._draw()
        self.root.after(33, self._animate)

    def _update_blink(self) -> None:
        if self.state in {"petting", "walk"}:
            return
        if self.tick >= self.next_blink:
            self.blink_until = self.tick + 5
            self.next_blink = self._future_tick(90, 210)
        self.face = "blink" if self.tick < self.blink_until else "normal"

    def _update_walk(self) -> None:
        if not self.walking_enabled or self.state == "petting":
            return

        if self.state == "walk":
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            next_x, next_y = self._clamp_window_position(
                x + self.walk_vx,
                y + self.walk_vy,
            )
            reached = (
                abs(self.walk_target_x - next_x) <= abs(self.walk_vx) + 1
                and abs(self.walk_target_y - next_y) <= abs(self.walk_vy) + 1
            )
            if reached:
                target_x, target_y = self._clamp_window_position(
                    self.walk_target_x,
                    self.walk_target_y,
                )
                self.root.geometry(f"+{target_x}+{target_y}")
                self.state = "idle"
                self.next_walk = self._future_tick(450, 1350)
                return
            self.root.geometry(f"+{round(next_x)}+{round(next_y)}")
            return

        if self.tick < self.next_walk:
            return

        start_x, start_y = self._clamp_window_position(
            self.root.winfo_x(),
            self.root.winfo_y(),
        )
        distance = random.randint(40, 160) * random.choice([-1, 1])
        drift_y = random.randint(-24, 24)
        target_x, target_y = self._clamp_window_position(start_x + distance, start_y + drift_y)
        steps = max(35, min(95, abs(target_x - start_x) // 2 + 35))

        if target_x == start_x and target_y == start_y:
            self.next_walk = self._future_tick(300, 900)
            return

        self.walk_target_x = target_x
        self.walk_target_y = target_y
        self.walk_vx = (target_x - start_x) / steps
        self.walk_vy = (target_y - start_y) / steps
        self.facing = 1 if self.walk_vx >= 0 else -1
        self.state = "walk"
        if random.random() < 0.3:
            self._say(random.choice(self.walk_lines), duration=65)

    def _draw(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, fill=TRANSPARENT, outline=TRANSPARENT
        )

        bob = math.sin(self.tick / 10) * 2.3
        if self.state == "walk":
            bob = math.sin(self.tick / 3.2) * 4.2

        cx = WINDOW_WIDTH / 2
        cy = GROUND_Y + bob
        walk_sway = math.sin(self.tick / 3.0) * 3 if self.state == "walk" else 0
        body_w = CAT_WIDTH + self.squash * 14 + abs(self.stretch_x) * 14
        body_h = CAT_HEIGHT - self.squash * 13 + abs(self.stretch_y) * 8
        cx += self.stretch_x * 5 + walk_sway
        cy += self.squash * 5 + self.stretch_y * 4

        left = cx - body_w / 2
        right = cx + body_w / 2
        top = cy - body_h
        bottom = cy

        self._draw_tail(cx, cy, body_w, body_h)
        self._draw_ears(cx, top, body_w)
        self._draw_body(left, top, right, bottom)
        self._draw_paws(cx, cy, body_w)
        self._draw_face(cx, top, body_w, body_h)

        if self.bubble_text:
            self._draw_bubble(self.bubble_text)

    def _draw_body(self, left: float, top: float, right: float, bottom: float) -> None:
        c = self._colors()
        self.canvas.create_oval(
            left + 5,
            top + 8,
            right - 4,
            bottom,
            fill=c["body"],
            outline=c["outline"],
            width=3,
        )
        self.canvas.create_arc(
            left + 14,
            top + 44,
            right - 20,
            bottom + 6,
            start=200,
            extent=125,
            style="arc",
            outline=c["shadow"],
            width=2,
        )

    def _draw_ears(self, cx: float, top: float, body_w: float) -> None:
        c = self._colors()
        ear_y = top + 20
        left_ear = [
            cx - body_w * 0.39,
            ear_y + 18,
            cx - body_w * 0.20,
            ear_y - 32,
            cx - body_w * 0.04,
            ear_y + 20,
        ]
        right_ear = [
            cx + body_w * 0.04,
            ear_y + 20,
            cx + body_w * 0.20,
            ear_y - 32,
            cx + body_w * 0.39,
            ear_y + 18,
        ]
        self.canvas.create_polygon(left_ear, fill=c["body"], outline=c["outline"], width=3, smooth=True)
        self.canvas.create_polygon(right_ear, fill=c["body"], outline=c["outline"], width=3, smooth=True)
        self.canvas.create_polygon(
            [
                cx - body_w * 0.29,
                ear_y + 8,
                cx - body_w * 0.20,
                ear_y - 16,
                cx - body_w * 0.11,
                ear_y + 11,
            ],
            fill=c["inner_ear"],
            outline="",
            smooth=True,
        )
        self.canvas.create_polygon(
            [
                cx + body_w * 0.11,
                ear_y + 11,
                cx + body_w * 0.20,
                ear_y - 16,
                cx + body_w * 0.29,
                ear_y + 8,
            ],
            fill=c["inner_ear"],
            outline="",
            smooth=True,
        )

    def _draw_tail(self, cx: float, cy: float, body_w: float, body_h: float) -> None:
        c = self._colors()
        wag = math.sin(self.tick / 8) * 8
        if self.state == "walk":
            wag = math.sin(self.tick / 2.5) * 12
        base_x = cx + body_w * 0.38 * self.facing
        base_y = cy - body_h * 0.34
        tip_x = base_x + (28 + wag) * self.facing
        tip_y = base_y + 10 + abs(wag) * 0.15
        self.canvas.create_line(
            base_x,
            base_y,
            tip_x,
            tip_y,
            fill=c["outline"],
            width=12,
            capstyle="round",
            smooth=True,
        )
        self.canvas.create_line(
            base_x,
            base_y,
            tip_x,
            tip_y,
            fill=c["body"],
            width=8,
            capstyle="round",
            smooth=True,
        )

    def _draw_paws(self, cx: float, cy: float, body_w: float) -> None:
        c = self._colors()
        step = math.sin(self.tick / 3.0) * 5 if self.state == "walk" else 0
        paw_y = cy - 18
        for offset, lift in [(-22, step), (22, -step)]:
            self.canvas.create_oval(
                cx + offset - 9,
                paw_y - 6 + max(0, lift),
                cx + offset + 9,
                paw_y + 10 + max(0, lift),
                fill=c["body_light"],
                outline=c["outline"],
                width=2,
            )

    def _draw_face(self, cx: float, top: float, body_w: float, body_h: float) -> None:
        c = self._colors()
        eye_y = top + body_h * 0.46
        mouth_y = top + body_h * 0.60
        eye_dx = body_w * 0.18

        if self.face in {"blink", "happy"}:
            self.canvas.create_arc(
                cx - eye_dx - 8,
                eye_y - 4,
                cx - eye_dx + 8,
                eye_y + 9,
                start=200,
                extent=140,
                style="arc",
                outline=c["mouth"],
                width=3,
            )
            self.canvas.create_arc(
                cx + eye_dx - 8,
                eye_y - 4,
                cx + eye_dx + 8,
                eye_y + 9,
                start=200,
                extent=140,
                style="arc",
                outline=c["mouth"],
                width=3,
            )
        else:
            self.canvas.create_oval(
                cx - eye_dx - 4,
                eye_y - 5,
                cx - eye_dx + 4,
                eye_y + 5,
                fill=c["eye"],
                outline="",
            )
            self.canvas.create_oval(
                cx + eye_dx - 4,
                eye_y - 5,
                cx + eye_dx + 4,
                eye_y + 5,
                fill=c["eye"],
                outline="",
            )

        self.canvas.create_oval(cx - 4, mouth_y - 4, cx + 4, mouth_y + 3, fill=c["nose"], outline="")
        self.canvas.create_arc(
            cx - 14,
            mouth_y - 1,
            cx,
            mouth_y + 15,
            start=290,
            extent=145,
            style="arc",
            outline=c["mouth"],
            width=2,
        )
        self.canvas.create_arc(
            cx,
            mouth_y - 1,
            cx + 14,
            mouth_y + 15,
            start=105,
            extent=145,
            style="arc",
            outline=c["mouth"],
            width=2,
        )
        self.canvas.create_oval(cx - 38, mouth_y + 1, cx - 25, mouth_y + 11, fill=c["blush"], outline="")
        self.canvas.create_oval(cx + 25, mouth_y + 1, cx + 38, mouth_y + 11, fill=c["blush"], outline="")

    def _draw_bubble(self, text: str) -> None:
        c = self._colors()
        text_id = self.canvas.create_text(
            WINDOW_WIDTH / 2,
            25,
            text=text,
            fill=c["outline"],
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        bbox = self.canvas.bbox(text_id)
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        pad_x = 12
        pad_y = 7
        bx1 = max(8, x1 - pad_x)
        by1 = y1 - pad_y
        bx2 = min(WINDOW_WIDTH - 8, x2 + pad_x)
        by2 = y2 + pad_y
        self.canvas.delete(text_id)
        self._rounded_rect(bx1, by1, bx2, by2, radius=12, fill="#fffdf8", outline=c["outline"])
        self.canvas.create_polygon(
            WINDOW_WIDTH / 2 - 7,
            by2 - 1,
            WINDOW_WIDTH / 2 + 7,
            by2 - 1,
            WINDOW_WIDTH / 2,
            by2 + 10,
            fill="#fffdf8",
            outline=c["outline"],
        )
        self.canvas.create_text(
            (bx1 + bx2) / 2,
            (by1 + by2) / 2,
            text=text,
            fill=c["outline"],
            font=("Microsoft YaHei UI", 10, "bold"),
        )

    def _rounded_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        fill: str,
        outline: str,
    ) -> None:
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        self.canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, width=2)


if __name__ == "__main__":
    DoughCat().run()
