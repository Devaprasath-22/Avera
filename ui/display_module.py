"""
Pygame Dashboard UI for MedGemma Medical Kiosk.
Renders real-time ECG line plot, patient vitals, camera preview, language selector, and chat UI.
"""

import sys
import os
import time
import numpy as np

try:
    import pygame
    import cv2
except ImportError as exc:
    print(f"Missing dependency for display_module: {exc}")
    raise exc


# Color Tokens
BG_DARK = (15, 20, 30)
CARD_BG = (25, 33, 48)
CARD_BORDER = (40, 52, 75)
TEXT_WHITE = (245, 245, 250)
TEXT_MUTED = (140, 155, 180)
CYAN_ACCENT = (0, 210, 255)
GREEN_HEALTH = (0, 230, 118)
RED_ALERT = (255, 82, 82)
YELLOW_WARN = (255, 193, 7)
BUTTON_BG = (35, 48, 70)
BUTTON_HOVER = (50, 68, 98)
BUTTON_ACTIVE = (0, 180, 230)


class KioskDisplayUI:
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("MedGemma Medical Kiosk - Jetson Orin Nano")

        self.font_title = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_header = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_body = pygame.font.SysFont("Arial", 14)
        self.font_small = pygame.font.SysFont("Arial", 12)

        self.clock = pygame.time.Clock()

        # Language Buttons (10 languages)
        self.languages = ["en", "hi", "ta", "te", "bn", "gu", "kn", "ml", "mr", "pa"]
        self.current_lang = "en"
        
        # Clickable Rects
        self.lang_rects = {}
        self.btn_voice_rect = pygame.Rect(720, 660, 140, 45)
        self.btn_camera_rect = pygame.Rect(870, 660, 160, 45)

        # State storage
        self.chat_history = []
        self.status_message = "Ready. Select language or tap 'Speak Voice' / 'Snap Image'."

    def render(
        self,
        vitals: dict,
        ecg_buffer: np.ndarray,
        camera_frame: np.ndarray,
        reply_text: str = "",
        user_prompt: str = "",
        is_thinking: bool = False,
    ):
        self.screen.fill(BG_DARK)

        # 1. Header Bar
        self._draw_header()

        # 2. Vitals Cards Panel (Top Left)
        self._draw_vitals_panel(vitals)

        # 3. Live ECG Waveform Plot (Middle Left)
        self._draw_ecg_plot(ecg_buffer)

        # 4. Camera Live Feed (Top Right)
        self._draw_camera_feed(camera_frame)

        # 5. Language Selector Bar (Bottom Bar)
        self._draw_language_bar()

        # 6. Medical Chat & AI Diagnosis Box (Middle Right)
        self._draw_chat_box(user_prompt, reply_text, is_thinking)

        # 7. Action Buttons
        self._draw_action_buttons(is_thinking)

        pygame.display.flip()

    def _draw_header(self):
        header_rect = pygame.Rect(10, 10, self.width - 20, 45)
        pygame.draw.rect(self.screen, CARD_BG, header_rect, border_radius=8)
        pygame.draw.rect(self.screen, CARD_BORDER, header_rect, width=1, border_radius=8)

        txt_title = self.font_title.render("MedGemma Offline Medical Kiosk", True, CYAN_ACCENT)
        self.screen.blit(txt_title, (25, 20))

        txt_sub = self.font_small.render("NVIDIA Jetson Orin Nano (8GB) | Bhashini 10-Language Speech Engine", True, TEXT_MUTED)
        self.screen.blit(txt_sub, (420, 25))

    def _draw_vitals_panel(self, vitals: dict):
        panel_rect = pygame.Rect(10, 65, 520, 140)
        pygame.draw.rect(self.screen, CARD_BG, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, CARD_BORDER, panel_rect, width=1, border_radius=10)

        # Title
        txt = self.font_header.render("Patient Real-Time Vitals", True, TEXT_WHITE)
        self.screen.blit(txt, (25, 75))

        spo2 = vitals.get("spo2", 98.0)
        hr = vitals.get("heart_rate", 74)
        temp_c = vitals.get("temp_c", 36.6)
        status = vitals.get("status", "Normal")

        # SpO2 Card
        c1 = pygame.Rect(25, 105, 115, 80)
        pygame.draw.rect(self.screen, BUTTON_BG, c1, border_radius=6)
        self.screen.blit(self.font_small.render("SpO2 Blood O2", True, TEXT_MUTED), (35, 112))
        self.screen.blit(self.font_title.render(f"{spo2:.1f}%", True, GREEN_HEALTH if spo2 >= 95 else RED_ALERT), (35, 138))

        # Heart Rate Card
        c2 = pygame.Rect(150, 105, 115, 80)
        pygame.draw.rect(self.screen, BUTTON_BG, c2, border_radius=6)
        self.screen.blit(self.font_small.render("Heart Rate", True, TEXT_MUTED), (160, 112))
        self.screen.blit(self.font_title.render(f"{hr} BPM", True, CYAN_ACCENT), (160, 138))

        # Temp Card
        c3 = pygame.Rect(275, 105, 115, 80)
        pygame.draw.rect(self.screen, BUTTON_BG, c3, border_radius=6)
        self.screen.blit(self.font_small.render("Body Temp", True, TEXT_MUTED), (285, 112))
        self.screen.blit(self.font_title.render(f"{temp_c:.1f}°C", True, RED_ALERT if temp_c >= 37.5 else TEXT_WHITE), (285, 138))

        # Status Badge
        c4 = pygame.Rect(400, 105, 115, 80)
        pygame.draw.rect(self.screen, BUTTON_BG, c4, border_radius=6)
        self.screen.blit(self.font_small.render("Vitals Status", True, TEXT_MUTED), (410, 112))
        status_color = GREEN_HEALTH if status == "Normal" else RED_ALERT
        self.screen.blit(self.font_small.render(status[:14], True, status_color), (410, 142))

    def _draw_ecg_plot(self, ecg_buffer: np.ndarray):
        ecg_rect = pygame.Rect(10, 215, 520, 260)
        pygame.draw.rect(self.screen, CARD_BG, ecg_rect, border_radius=10)
        pygame.draw.rect(self.screen, CARD_BORDER, ecg_rect, width=1, border_radius=10)

        txt = self.font_header.render("ECG Live Waveform (0.5 - 40 Hz Filtered)", True, GREEN_HEALTH)
        self.screen.blit(txt, (25, 225))

        # Draw Graph Grid Line Background
        graph_box = pygame.Rect(25, 260, 490, 200)
        pygame.draw.rect(self.screen, (15, 22, 32), graph_box, border_radius=6)

        for x in range(25, 515, 40):
            pygame.draw.line(self.screen, (25, 38, 55), (x, 260), (x, 460), 1)
        for y in range(260, 460, 40):
            pygame.draw.line(self.screen, (25, 38, 55), (25, y), (515, y), 1)

        # Plot ECG waveform points
        if len(ecg_buffer) > 2:
            num_pts = len(ecg_buffer)
            step_x = 490.0 / float(num_pts)
            points = []
            baseline_y = 360.0  # Center line inside graph box

            for i in range(num_pts):
                px = 25 + int(i * step_x)
                py = baseline_y - int(ecg_buffer[i] * 65.0)
                py = max(265, min(455, py))
                points.append((px, py))

            if len(points) >= 2:
                pygame.draw.lines(self.screen, GREEN_HEALTH, False, points, 2)

    def _draw_camera_feed(self, camera_frame: np.ndarray):
        cam_rect = pygame.Rect(540, 65, 350, 260)
        pygame.draw.rect(self.screen, CARD_BG, cam_rect, border_radius=10)
        pygame.draw.rect(self.screen, CARD_BORDER, cam_rect, width=1, border_radius=10)

        txt = self.font_header.render("Camera & Medical Imaging", True, TEXT_WHITE)
        self.screen.blit(txt, (555, 75))

        if camera_frame is not None and camera_frame.size > 0:
            try:
                # Convert BGR (OpenCV) to RGB (Pygame)
                rgb_frame = cv2.cvtColor(camera_frame, cv2.COLOR_BGR2RGB)
                rgb_frame = cv2.resize(rgb_frame, (320, 200))
                surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
                self.screen.blit(surface, (555, 110))
            except Exception:
                pass

    def _draw_language_bar(self):
        bar_rect = pygame.Rect(10, 485, 520, 220)
        pygame.draw.rect(self.screen, CARD_BG, bar_rect, border_radius=10)
        pygame.draw.rect(self.screen, CARD_BORDER, bar_rect, width=1, border_radius=10)

        txt = self.font_header.render("Select Language (Bhashini Engine)", True, CYAN_ACCENT)
        self.screen.blit(txt, (25, 495))

        lang_labels = {
            "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali",
            "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "pa": "Punjabi"
        }

        cols = 5
        start_x = 25
        start_y = 530
        w = 92
        h = 35

        for idx, code in enumerate(self.languages):
            row = idx // cols
            col = idx % cols
            x = start_x + col * (w + 8)
            y = start_y + row * (h + 10)

            rect = pygame.Rect(x, y, w, h)
            self.lang_rects[code] = rect

            is_active = (code == self.current_lang)
            btn_color = BUTTON_ACTIVE if is_active else BUTTON_BG
            pygame.draw.rect(self.screen, btn_color, rect, border_radius=6)
            pygame.draw.rect(self.screen, CYAN_ACCENT if is_active else CARD_BORDER, rect, width=1, border_radius=6)

            txt_lbl = self.font_small.render(lang_labels[code], True, TEXT_WHITE if is_active else TEXT_MUTED)
            self.screen.blit(txt_lbl, (x + 10, y + 10))

    def _draw_chat_box(self, user_prompt: str, reply_text: str, is_thinking: bool):
        chat_rect = pygame.Rect(540, 335, 730, 310)
        pygame.draw.rect(self.screen, CARD_BG, chat_rect, border_radius=10)
        pygame.draw.rect(self.screen, CARD_BORDER, chat_rect, width=1, border_radius=10)

        txt = self.font_header.render("MedGemma AI Diagnosis & Advice", True, CYAN_ACCENT)
        self.screen.blit(txt, (555, 345))

        if is_thinking:
            txt_think = self.font_body.render("Thinking & Analyzing Patient Context...", True, YELLOW_WARN)
            self.screen.blit(txt_think, (555, 380))
            return

        if user_prompt:
            txt_u = self.font_body.render(f"Patient: {user_prompt[:70]}", True, TEXT_WHITE)
            self.screen.blit(txt_u, (555, 380))

        if reply_text:
            lines = [reply_text[i:i+85] for i in range(0, min(len(reply_text), 400), 85)]
            curr_y = 415
            for line in lines:
                txt_r = self.font_body.render(line, True, GREEN_HEALTH)
                self.screen.blit(txt_r, (555, curr_y))
                curr_y += 22

    def _draw_action_buttons(self, is_thinking: bool):
        # Voice Button
        pygame.draw.rect(self.screen, BUTTON_ACTIVE if not is_thinking else BUTTON_BG, self.btn_voice_rect, border_radius=8)
        self.screen.blit(self.font_header.render("🎤 Speak Voice", True, TEXT_WHITE), (732, 672))

        # Camera Snapshot Button
        pygame.draw.rect(self.screen, BUTTON_HOVER if not is_thinking else BUTTON_BG, self.btn_camera_rect, border_radius=8)
        self.screen.blit(self.font_header.render("📷 Snap Image", True, TEXT_WHITE), (882, 672))

    def handle_click(self, pos: tuple[int, int]) -> dict:
        """Checks mouse clicks on language buttons, voice button, or camera snapshot button."""
        action = {"type": None, "value": None}
        x, y = pos

        # Check language buttons
        for code, rect in self.lang_rects.items():
            if rect.collidepoint(x, y):
                self.current_lang = code
                action = {"type": "set_language", "value": code}
                return action

        # Check Voice button
        if self.btn_voice_rect.collidepoint(x, y):
            action = {"type": "speak_voice", "value": self.current_lang}
            return action

        # Check Camera Snapshot button
        if self.btn_camera_rect.collidepoint(x, y):
            action = {"type": "snap_camera", "value": True}
            return action

        return action
