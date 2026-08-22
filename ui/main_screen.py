import tkinter as tk
from tkinter import font as tkfont
from config import config

# Styling Constants for the Premium Kiosk Dark Theme
BG_DARK = "#121212"
BG_CARD = "#1E1E1E"
FG_PRIMARY = "#FFFFFF"
FG_SECONDARY = "#A0A0A0"
COLOR_ACCENT = "#00D2FC"   # Modern Neon Cyan
COLOR_TEMP = "#FF9100"     # Warm Amber for Temperature
COLOR_SPO2 = "#00E676"     # Green for healthy oxygenation
COLOR_ECG = "#FF1744"      # Red/Pink for heart/ECG
COLOR_WARNING = "#FFEA00"  # Yellow for warnings

# Languages mapping name -> code
LANGUAGES = {
    "English": "en",
    "தமிழ் / Tamil": "ta",
    "हिन्दी / Hindi": "hi",
    "മലയാളം / Malayalam": "ml",
    "తెలుగు / Telugu": "te"
}

class MainScreen(tk.Frame):
    """
    Renders the welcome screen of the kiosk. Allows the user to select their
    preferred language and start the assessment.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        # Configure grid expansion
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=4)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Top Header
        self.header_frame = tk.Frame(self, bg=BG_DARK)
        self.header_frame.grid(row=0, column=0, sticky="nsew", pady=10)
        
        self.title_label = tk.Label(
            self.header_frame, 
            text="HEALTHCARE AI ASSISTANT", 
            font=("Helvetica", 20, "bold"), 
            bg=BG_DARK, 
            fg=FG_PRIMARY
        )
        self.title_label.pack(pady=20)
        
        # 2. Main Content Frame
        self.content_frame = tk.Frame(self, bg=BG_CARD, bd=1, relief="flat", highlightbackground="#333333", highlightthickness=1)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(2, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.assessment_label = tk.Label(
            self.content_frame, 
            text="Welcome! Please configure and start your assessment below.", 
            font=("Helvetica", 12), 
            bg=BG_CARD, 
            fg=FG_SECONDARY
        )
        self.assessment_label.grid(row=0, column=0, sticky="s", pady=(15, 5))
        
        # Language selection frame in row 1
        self.lang_frame = tk.Frame(self.content_frame, bg=BG_CARD)
        self.lang_frame.grid(row=1, column=0, sticky="n", pady=5)
        
        # Label set to English only as requested
        self.lang_label = tk.Label(
            self.lang_frame,
            text="Select Language:",
            font=("Helvetica", 11, "bold"),
            bg=BG_CARD,
            fg=FG_PRIMARY
        )
        self.lang_label.pack(pady=2)
        
        self.lang_var = tk.StringVar(value="English")
        self.lang_menu = tk.OptionMenu(
            self.lang_frame,
            self.lang_var,
            *LANGUAGES.keys(),
            command=self.on_lang_changed
        )
        self.lang_menu.config(
            font=("Helvetica", 12, "bold"),
            bg="#2A2A2A",
            fg=COLOR_ACCENT,
            activebackground="#3A3A3A",
            activeforeground=COLOR_ACCENT,
            bd=0,
            highlightthickness=0,
            padx=12,
            pady=6,
            cursor="hand2"
        )
        self.lang_menu["menu"].config(
            bg="#2A2A2A",
            fg=FG_PRIMARY,
            activebackground=COLOR_ACCENT,
            activeforeground="#000000",
            font=("Helvetica", 11)
        )
        self.lang_menu.pack(pady=5)
        
        # Buttons container in row 2
        self.buttons_frame = tk.Frame(self.content_frame, bg=BG_CARD)
        self.buttons_frame.grid(row=2, column=0, sticky="n", pady=(10, 20))
        
        # Recording Button
        self.recording_btn = tk.Button(
            self.buttons_frame, 
            text="RECORDING", 
            font=("Helvetica", 11, "bold"), 
            bg=COLOR_ACCENT, 
            fg="#000000", 
            activebackground="#00B0D0",
            activeforeground="#000000",
            bd=0, 
            padx=20, 
            pady=15, 
            width=15,
            cursor="hand2",
            command=self.on_recording_clicked
        )
        self.recording_btn.grid(row=0, column=0, padx=10, pady=5)
        
        # Capture Camera Button
        self.camera_btn = tk.Button(
            self.buttons_frame, 
            text="CAPTURE CAMERA &\nTELL UR ILLNESS", 
            font=("Helvetica", 11, "bold"), 
            bg="#444444", 
            fg=FG_PRIMARY, 
            activebackground="#555555",
            activeforeground=FG_PRIMARY,
            bd=0, 
            padx=20, 
            pady=15, 
            width=22,
            cursor="hand2",
            command=self.on_camera_clicked
        )
        self.camera_btn.grid(row=0, column=1, padx=10, pady=5)

        # 3. Bottom Status Frame
        self.status_frame = tk.Frame(self, bg=BG_DARK)
        self.status_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=(0, 15))
        
        self.system_status_container = tk.Frame(self.status_frame, bg=BG_DARK)
        self.system_status_container.pack(anchor="center")
        
        self.status_dot = tk.Label(
            self.system_status_container,
            text="●",
            font=("Helvetica", 12),
            bg=BG_DARK,
            fg="#00FF66"
        )
        self.status_dot.pack(side="left")
        
        self.status_text = tk.Label(
            self.system_status_container,
            text=" System Ready",
            font=("Helvetica", 12, "bold"),
            bg=BG_DARK,
            fg=FG_SECONDARY
        )
        self.status_text.pack(side="left")
        
    def on_lang_changed(self, choice):
        lang_code = LANGUAGES.get(choice)
        if lang_code:
            self.controller.set_selected_language(lang_code)
            
    def on_recording_clicked(self):
        self.on_lang_changed(self.lang_var.get())
        self.controller.start_assessment_workflow(mode="recording")
        
    def on_camera_clicked(self):
        self.on_lang_changed(self.lang_var.get())
        self.controller.start_assessment_workflow(mode="camera")
