import tkinter as tk
from tkinter import ttk
import time
from ui.main_screen import BG_DARK, BG_CARD, FG_PRIMARY, FG_SECONDARY, COLOR_ACCENT, COLOR_TEMP, COLOR_SPO2, COLOR_ECG, COLOR_WARNING

class VitalsScreen(tk.Frame):
    """
    Manages the vitals measurement UI screens. Supports the interactive CHECK and NEXT flow,
    and draws a vector body diagram for ECG electrode placement guides.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=4)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header Frame
        self.header_frame = tk.Frame(self, bg=BG_DARK)
        self.header_frame.grid(row=0, column=0, sticky="nsew", pady=10)
        
        self.title_label = tk.Label(
            self.header_frame,
            text="SYSTEM INITIALIZATION",
            font=("Helvetica", 18, "bold"),
            bg=BG_DARK,
            fg=COLOR_ACCENT
        )
        self.title_label.pack(pady=15)

        # 2. Main Content Card
        self.content_frame = tk.Frame(self, bg=BG_CARD, bd=1, relief="flat", highlightbackground="#333333", highlightthickness=1)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        
        # Configure grid for content frame
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.ecg_buffer = []  # Holds ECG signal points for scrolling graph

        # 3. Bottom Status bar
        self.footer_frame = tk.Frame(self, bg=BG_DARK)
        self.footer_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)
        
        self.status_label = tk.Label(
            self.footer_frame,
            text="Preparing assessment...",
            font=("Helvetica", 12, "italic"),
            bg=BG_DARK,
            fg=FG_SECONDARY
        )
        self.status_label.pack(side="left")
        
        self.action_btn = tk.Button(
            self.footer_frame,
            text="CONTINUE",
            font=("Helvetica", 12, "bold"),
            bg=COLOR_ACCENT,
            fg="#000000",
            activebackground="#00B0D0",
            activeforeground="#000000",
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.on_continue_clicked
        )
        self.action_btn.pack(side="right")
        self.action_btn.pack_forget()

    def clear_content_frame(self):
        """
        Wipes out all child widgets of the main card frame.
        """
        for child in self.content_frame.winfo_children():
            child.destroy()

    def show_initialization(self, components):
        """
        Renders the checklist screen during system checks.
        """
        self.title_label.config(text="INITIALIZING SYSTEM", fg=COLOR_ACCENT)
        self.status_label.config(text="Initializing healthcare assessment...")
        self.action_btn.pack_forget()
        
        self.clear_content_frame()
        
        init_frame = tk.Frame(self.content_frame, bg=BG_CARD)
        init_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        init_frame.grid_columnconfigure(0, weight=1)
        init_frame.grid_columnconfigure(1, weight=1)
        
        row = 0
        col = 0
        for name, checked in components.items():
            symbol = "✓" if checked else "●"
            color = "#00FF66" if checked else FG_SECONDARY
            
            lbl = tk.Label(
                init_frame, 
                text=f"{symbol} {name}", 
                font=("Helvetica", 13), 
                bg=BG_CARD, 
                fg=color,
                anchor="w"
            )
            lbl.grid(row=row, column=col, sticky="w", padx=20, pady=6)
            
            col += 1
            if col > 1:
                col = 0
                row += 1

    # ==========================================
    # TEMPERATURE VIEW SUB-STEPS
    # ==========================================
    def show_temperature_prompt(self):
        self.title_label.config(text="TEMPERATURE MEASUREMENT", fg=COLOR_TEMP)
        self.status_label.config(text="Waiting for temperature check...")
        self.action_btn.pack_forget()
        self.clear_content_frame()
        
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        
        icon_lbl = tk.Label(frame, text="🌡", font=("Helvetica", 48), bg=BG_CARD, fg=COLOR_TEMP)
        icon_lbl.pack(pady=10)
        
        desc_lbl = tk.Label(
            frame, 
            text="Place the sensor near to forehead", 
            font=("Helvetica", 14, "bold"), 
            bg=BG_CARD, 
            fg=COLOR_WARNING
        )
        desc_lbl.pack(pady=10)
        
        check_btn = tk.Button(
            frame,
            text="CHECK",
            font=("Helvetica", 13, "bold"),
            bg=COLOR_TEMP,
            fg="#000000",
            activebackground="#D07000",
            activeforeground="#000000",
            bd=0,
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.controller.run_temperature_check
        )
        check_btn.pack(pady=15)

    def show_temperature_analysis(self, percent):
        self.clear_content_frame()
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        
        icon_lbl = tk.Label(frame, text="🌡", font=("Helvetica", 48), bg=BG_CARD, fg=COLOR_TEMP)
        icon_lbl.pack(pady=10)
        
        desc_lbl = tk.Label(frame, text="Analyzing temperature...", font=("Helvetica", 13), bg=BG_CARD, fg=FG_PRIMARY)
        desc_lbl.pack(pady=5)
        
        bar_len = 15
        filled = int(percent * bar_len)
        bar_str = "█" * filled + "░" * (bar_len - filled)
        
        bar_lbl = tk.Label(
            frame, 
            text=f"[{bar_str}] {int(percent * 100)}%", 
            font=("Courier", 16, "bold"), 
            bg=BG_CARD, 
            fg=COLOR_TEMP
        )
        bar_lbl.pack(pady=10)
        self.status_label.config(text="Reading forehead sensor...")

    def show_temperature_result(self, temp_val):
        self.status_label.config(text="Temperature recorded.")
        self.clear_content_frame()
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        
        icon_lbl = tk.Label(frame, text="✓ Temperature complete", font=("Helvetica", 13, "bold"), bg=BG_CARD, fg="#00FF66")
        icon_lbl.pack(pady=10)
        
        val_lbl = tk.Label(frame, text=f"{temp_val} °C", font=("Helvetica", 36, "bold"), bg=BG_CARD, fg=COLOR_TEMP)
        val_lbl.pack(pady=10)
        
        next_btn = tk.Button(
            frame,
            text="NEXT",
            font=("Helvetica", 13, "bold"),
            bg=COLOR_TEMP,
            fg="#000000",
            activebackground="#D07000",
            activeforeground="#000000",
            bd=0,
            padx=35,
            pady=10,
            cursor="hand2",
            command=lambda: self.controller.advance_next_sensor("oximeter")
        )
        next_btn.pack(pady=10)

    # ==========================================
    # OXIMETER VIEW SUB-STEPS
    # ==========================================
    def show_oximeter_prompt(self):
        self.title_label.config(text="PULSE OXIMETER", fg=COLOR_SPO2)
        self.status_label.config(text="Waiting for oximeter check...")
        self.clear_content_frame()
        
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        
        icon_lbl = tk.Label(frame, text="🫁", font=("Helvetica", 48), bg=BG_CARD, fg=COLOR_SPO2)
        icon_lbl.pack(pady=5)
        
        desc_lbl = tk.Label(
            frame, 
            text="Place finger on the oximeter sensor", 
            font=("Helvetica", 14, "bold"), 
            bg=BG_CARD, 
            fg=COLOR_WARNING
        )
        desc_lbl.pack(pady=10)
        
        check_btn = tk.Button(
            frame,
            text="CHECK",
            font=("Helvetica", 13, "bold"),
            bg=COLOR_SPO2,
            fg="#000000",
            activebackground="#00B050",
            activeforeground="#000000",
            bd=0,
            padx=30,
            pady=10,
            cursor="hand2",
            command=self.controller.run_oximeter_check
        )
        check_btn.pack(pady=15)

    def show_oximeter_analysis(self, percent):
        self.clear_content_frame()
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_columnconfigure(0, weight=1)
        
        icon_lbl = tk.Label(frame, text="🫁", font=("Helvetica", 48), bg=BG_CARD, fg=COLOR_SPO2)
        icon_lbl.pack(pady=5)
        
        desc_lbl = tk.Label(frame, text="Analyzing SpO2 & Pulse...", font=("Helvetica", 13), bg=BG_CARD, fg=FG_PRIMARY)
        desc_lbl.pack(pady=5)
        
        bar_len = 15
        filled = int(percent * bar_len)
        bar_str = "█" * filled + "░" * (bar_len - filled)
        
        bar_lbl = tk.Label(
            frame, 
            text=f"[{bar_str}] {int(percent * 100)}%", 
            font=("Courier", 16, "bold"), 
            bg=BG_CARD, 
            fg=COLOR_SPO2
        )
        bar_lbl.pack(pady=5)
        self.status_label.config(text="Reading pulse sensor...")

    def show_oximeter_result(self, spo2_val, pulse_val):
        self.status_label.config(text="Oximeter recorded.")
        self.clear_content_frame()
        
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        frame.grid_columnconfigure(0, weight=1)
        
        desc_lbl = tk.Label(frame, text="✓ SpO2 Complete", font=("Helvetica", 13, "bold"), bg=BG_CARD, fg="#00FF66")
        desc_lbl.pack(pady=5)
        
        results_frame = tk.Frame(frame, bg=BG_CARD)
        results_frame.pack(pady=10)
        
        spo2_lbl = tk.Label(results_frame, text=f"SpO2: {spo2_val} %", font=("Helvetica", 20, "bold"), bg=BG_CARD, fg=COLOR_SPO2)
        spo2_lbl.grid(row=0, column=0, padx=20)
        
        pulse_lbl = tk.Label(results_frame, text=f"Pulse: {pulse_val} BPM", font=("Helvetica", 20, "bold"), bg=BG_CARD, fg=COLOR_SPO2)
        pulse_lbl.grid(row=0, column=1, padx=20)
        
        next_btn = tk.Button(
            frame,
            text="NEXT",
            font=("Helvetica", 13, "bold"),
            bg=COLOR_SPO2,
            fg="#000000",
            activebackground="#00B050",
            activeforeground="#000000",
            bd=0,
            padx=35,
            pady=10,
            cursor="hand2",
            command=lambda: self.controller.advance_next_sensor("ecg")
        )
        next_btn.pack(pady=10)

    # ==========================================
    # ECG VIEW SUB-STEPS & GRAPHICS
    # ==========================================
    def show_ecg_prompt(self):
        self.title_label.config(text="ECG MEASUREMENT", fg=COLOR_ECG)
        self.status_label.config(text="Follow wire placement diagram...")
        self.clear_content_frame()
        
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        
        desc_lbl = tk.Label(
            frame, 
            text="Place ECG electrodes correctly as shown below", 
            font=("Helvetica", 12, "bold"), 
            bg=BG_CARD, 
            fg=COLOR_WARNING
        )
        desc_lbl.pack(pady=2)
        
        # 1. Custom Vector Body Placement Canvas
        canvas_width = 440
        canvas_height = 145
        guide_canvas = tk.Canvas(
            frame,
            width=canvas_width,
            height=canvas_height,
            bg="#171717",
            bd=0,
            highlightthickness=1,
            highlightbackground="#333333"
        )
        guide_canvas.pack(pady=5)
        
        # Draw Torso
        # Head
        guide_canvas.create_oval(190, 8, 220, 38, outline="#888888", fill="#262626", width=2)
        # Neck
        guide_canvas.create_line(205, 38, 205, 45, fill="#888888", width=3)
        # Torso body block
        guide_canvas.create_polygon(170, 45, 240, 45, 230, 95, 180, 95, outline="#888888", fill="#262626", width=2)
        # Left Leg (user's right leg - left on canvas)
        guide_canvas.create_line(185, 95, 185, 120, fill="#888888", width=4)
        # Right Leg (user's left leg - right on canvas) - Place green electrode here
        guide_canvas.create_line(225, 95, 225, 130, fill="#888888", width=4)
        # Right Arm (left on canvas) - Place red electrode here
        guide_canvas.create_line(170, 50, 110, 80, fill="#888888", width=4)
        # Left Arm (right on canvas) - Place yellow electrode here
        guide_canvas.create_line(240, 50, 300, 80, fill="#888888", width=4)
        
        # Electrodes points (Blinks/dots)
        # RED: RA (Right Arm wrist) -> Left on canvas
        guide_canvas.create_oval(105, 75, 115, 85, fill="#FF1744", outline="#FFFFFF", width=1)
        # YELLOW: LA (Left Arm wrist) -> Right on canvas
        guide_canvas.create_oval(295, 75, 305, 85, fill="#FFEA00", outline="#FFFFFF", width=1)
        # GREEN: LL (Left Leg ankle) -> Right leg on canvas
        guide_canvas.create_oval(220, 125, 230, 135, fill="#00E676", outline="#FFFFFF", width=1)
        
        # Right Side Legends
        guide_canvas.create_text(20, 25, text="🔴 RED Wire: Right Wrist", fill="#FF1744", font=("Helvetica", 9, "bold"), anchor="w")
        guide_canvas.create_text(20, 55, text="🟡 YELLOW Wire: Left Wrist", fill="#FFEA00", font=("Helvetica", 9, "bold"), anchor="w")
        guide_canvas.create_text(20, 85, text="🟢 GREEN Wire: Left Ankle", fill="#00E676", font=("Helvetica", 9, "bold"), anchor="w")
        
        # Action check button
        check_btn = tk.Button(
            frame,
            text="CHECK",
            font=("Helvetica", 12, "bold"),
            bg=COLOR_ECG,
            fg="#FFFFFF",
            activebackground="#B01030",
            activeforeground="#FFFFFF",
            bd=0,
            padx=35,
            pady=8,
            cursor="hand2",
            command=self.controller.run_ecg_check
        )
        check_btn.pack(pady=2)

    def show_ecg_analysis(self):
        self.clear_content_frame()
        self.ecg_frame = tk.Frame(self.content_frame, bg=BG_CARD)
        self.ecg_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        self.ecg_frame.grid_columnconfigure(0, weight=1)
        
        header_row = tk.Frame(self.ecg_frame, bg=BG_CARD)
        header_row.pack(fill="x", pady=5)
        
        icon_lbl = tk.Label(header_row, text="❤️", font=("Helvetica", 20), bg=BG_CARD, fg=COLOR_ECG)
        icon_lbl.pack(side="left", padx=10)
        
        desc_lbl = tk.Label(header_row, text="Analyzing ECG signal...", font=("Helvetica", 13), bg=BG_CARD, fg=FG_PRIMARY)
        desc_lbl.pack(side="left")
        
        self.canvas_width = 440
        self.canvas_height = 140
        self.canvas = tk.Canvas(
            self.ecg_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#000000",
            bd=0,
            highlightthickness=1,
            highlightbackground="#444444"
        )
        self.canvas.pack(pady=10, fill="both", expand=True)
        
        for x in range(0, self.canvas_width, 25):
            self.canvas.create_line(x, 0, x, self.canvas_height, fill="#221111")
        for y in range(0, self.canvas_height, 25):
            self.canvas.create_line(0, y, self.canvas_width, y, fill="#221111")
            
        self.status_label.config(text="Recording chest signals...")

    def show_ecg_result(self, heart_rate, rhythm):
        self.status_label.config(text="ECG recorded.")
        self.clear_content_frame()
        
        frame = tk.Frame(self.content_frame, bg=BG_CARD)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        
        desc_lbl = tk.Label(frame, text="✓ ECG Complete", font=("Helvetica", 13, "bold"), bg=BG_CARD, fg="#00FF66")
        desc_lbl.pack(pady=5)
        
        results_frame = tk.Frame(frame, bg=BG_CARD)
        results_frame.pack(pady=10)
        
        hr_lbl = tk.Label(results_frame, text=f"Heart Rate: {heart_rate} BPM", font=("Helvetica", 18, "bold"), bg=BG_CARD, fg=COLOR_ECG)
        hr_lbl.grid(row=0, column=0, padx=20)
        
        rhythm_lbl = tk.Label(results_frame, text=f"Rhythm: {rhythm}", font=("Helvetica", 14, "bold"), bg=BG_CARD, fg=COLOR_ACCENT)
        rhythm_lbl.grid(row=0, column=1, padx=20)
        
        next_btn = tk.Button(
            frame,
            text="NEXT",
            font=("Helvetica", 13, "bold"),
            bg=COLOR_ECG,
            fg="#FFFFFF",
            activebackground="#B01030",
            activeforeground="#FFFFFF",
            bd=0,
            padx=35,
            pady=10,
            cursor="hand2",
            command=lambda: self.controller.advance_next_sensor("summary")
        )
        next_btn.pack(pady=10)

    # ==========================================
    # ECG WAVEFORM GRAPH UTILS
    # ==========================================
    def update_ecg_canvas(self, points):
        self.ecg_buffer.extend(points)
        max_buffer = 150
        if len(self.ecg_buffer) > max_buffer:
            self.ecg_buffer = self.ecg_buffer[-max_buffer:]
            
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
            
        self.canvas.delete("wave")
        
        if len(self.ecg_buffer) < 2:
            return
            
        center_y = self.canvas_height / 2.0
        x_step = self.canvas_width / max_buffer
        
        coords = []
        for i, val in enumerate(self.ecg_buffer):
            x = i * x_step
            y = center_y - (val * 45)
            coords.extend([x, y])
            
        self.canvas.create_line(coords, fill="#39FF14", width=2, tags="wave")

    # ==========================================
    # VITALS SUMMARY SECTION
    # ==========================================
    def show_vitals_summary(self, temp, spo2, pulse, rhythm):
        self.title_label.config(text="VITAL SIGNS SUMMARY", fg=COLOR_ACCENT)
        self.status_label.config(text="Vitals collection complete.")
        self.action_btn.pack(side="right")
        
        self.clear_content_frame()
        
        grid_frame = tk.Frame(self.content_frame, bg=BG_CARD)
        grid_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)
        
        card_t = tk.Frame(grid_frame, bg="#2A2A2A", bd=1, relief="flat", padx=15, pady=10)
        card_t.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        tk.Label(card_t, text="🌡 Temperature", font=("Helvetica", 12), bg="#2A2A2A", fg=FG_SECONDARY).pack(anchor="w")
        tk.Label(card_t, text=f"{temp} °C", font=("Helvetica", 20, "bold"), bg="#2A2A2A", fg=COLOR_TEMP).pack(pady=5, anchor="center")
        
        card_o = tk.Frame(grid_frame, bg="#2A2A2A", bd=1, relief="flat", padx=15, pady=10)
        card_o.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        tk.Label(card_o, text="🫁 SpO2", font=("Helvetica", 12), bg="#2A2A2A", fg=FG_SECONDARY).pack(anchor="w")
        tk.Label(card_o, text=f"{spo2} %", font=("Helvetica", 20, "bold"), bg="#2A2A2A", fg=COLOR_SPO2).pack(pady=5, anchor="center")
        
        card_p = tk.Frame(grid_frame, bg="#2A2A2A", bd=1, relief="flat", padx=15, pady=10)
        card_p.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        tk.Label(card_p, text="❤️ Pulse", font=("Helvetica", 12), bg="#2A2A2A", fg=FG_SECONDARY).pack(anchor="w")
        tk.Label(card_p, text=f"{pulse} BPM", font=("Helvetica", 20, "bold"), bg="#2A2A2A", fg=COLOR_SPO2).pack(pady=5, anchor="center")
        
        card_e = tk.Frame(grid_frame, bg="#2A2A2A", bd=1, relief="flat", padx=15, pady=10)
        card_e.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        tk.Label(card_e, text="❤️ ECG Rhythm", font=("Helvetica", 12), bg="#2A2A2A", fg=FG_SECONDARY).pack(anchor="w")
        tk.Label(card_e, text=f"{pulse} BPM", font=("Helvetica", 20, "bold"), bg="#2A2A2A", fg=COLOR_ECG).pack(pady=5, anchor="center")
        tk.Label(card_e, text=rhythm, font=("Helvetica", 10, "bold"), bg="#2A2A2A", fg=COLOR_ACCENT).pack(anchor="center")

    def on_continue_clicked(self):
        self.controller.advance_from_vitals_summary()
