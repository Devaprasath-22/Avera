import tkinter as tk
from ui.main_screen import BG_DARK, BG_CARD, FG_PRIMARY, FG_SECONDARY, COLOR_ACCENT, COLOR_WARNING

# Translations of "Tell your illness"
ILLNESS_PROMPTS = {
    "en": "Tell your illness",
    "ta": "உங்கள் நோயைக் கூறவும் (Tell your illness)",
    "hi": "अपनी बीमारी बताएं (Tell your illness)",
    "ml": "നിങ്ങളുടെ രോഗം പറയുക (Tell your illness)",
    "te": "మీ అనారోగ్యం గురించి చెప్పండి (Tell your illness)"
}

class VoiceScreen(tk.Frame):
    """
    Renders the speech interface screen. Displays the "Tell your illness" prompt in
    the user-selected language and counts down for 7 seconds.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=4)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header Frame (Removed demo headers)
        self.header_frame = tk.Frame(self, bg=BG_DARK)
        self.header_frame.grid(row=0, column=0, sticky="nsew", pady=10)
        
        self.title_label = tk.Label(
            self.header_frame,
            text="CLINICAL AUDIO RESPONSE",
            font=("Consolas", 18, "bold"),
            bg=BG_DARK,
            fg=COLOR_ACCENT
        )
        self.title_label.pack(pady=15)

        # 2. Main Content Card
        self.content_frame = tk.Frame(self, bg=BG_CARD, bd=3, relief="ridge", highlightbackground="#00FF00", highlightthickness=1)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        self.card_inner = tk.Frame(self.content_frame, bg=BG_CARD)
        self.card_inner.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        self.card_inner.grid_columnconfigure(0, weight=1)
        
        # Mic pulsing indicator
        self.mic_badge = tk.Frame(self.card_inner, bg="#FF1744", padx=15, pady=8)
        self.mic_label = tk.Label(self.mic_badge, text="🎙 RECORDING SPEECH", font=("Consolas", 12, "bold"), bg="#FF1744", fg="#FFFFFF")
        self.mic_label.pack()
        
        # Large Illness Prompt
        self.prompt_label = tk.Label(
            self.card_inner, 
            text="Tell your illness", 
            font=("Consolas", 16, "bold"), 
            bg=BG_CARD, 
            fg=FG_PRIMARY,
            wraplength=380,
            justify="center"
        )
        self.prompt_label.pack(pady=20)
        
        # Countdown label
        self.countdown_label = tk.Label(
            self.card_inner, 
            text="7", 
            font=("Consolas", 32, "bold"), 
            bg=BG_CARD, 
            fg=COLOR_WARNING
        )
        self.countdown_label.pack(pady=10)
        
        # 3. Footer Status Frame
        self.footer_frame = tk.Frame(self, bg=BG_DARK)
        self.footer_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)
        
        self.status_label = tk.Label(
            self.footer_frame,
            text="Initializing dialog...",
            font=("Consolas", 12, "italic"),
            bg=BG_DARK,
            fg=FG_SECONDARY
        )
        self.status_label.pack(side="left")
        
        self.mic_flash_state = True

    def show_preparing(self):
        """
        Renders initial loading screen for voice.
        """
        self.status_label.config(text="Preparing voice system...")
        self.mic_badge.pack_forget()
        self.prompt_label.pack_forget()
        self.countdown_label.pack_forget()
        
        self.loading_lbl = tk.Label(self.card_inner, text="Initializing audio output...", font=("Consolas", 13), bg=BG_CARD, fg=FG_SECONDARY)
        self.loading_lbl.pack(pady=40)

    def show_listening(self, lang_code):
        """
        Displays the "Tell your illness" prompt in the selected language and triggers the mic pulse.
        """
        if hasattr(self, "loading_lbl"):
            self.loading_lbl.pack_forget()
            
        # Get language-specific prompt
        prompt_text = ILLNESS_PROMPTS.get(lang_code, "Tell your illness")
        self.prompt_label.config(text=prompt_text)
        
        self.status_label.config(text="Listening for user speech...")
        self.mic_badge.pack(pady=(10, 10))
        self.prompt_label.pack(pady=15)
        self.countdown_label.config(text="7", fg=COLOR_WARNING)
        self.countdown_label.pack(pady=10)
        
        self.flash_mic_indicator()

    def flash_mic_indicator(self):
        """
        Flashes the recording label background colors.
        """
        if not self.winfo_exists():
            return
        
        state = self.controller.get_current_state()
        if state == "PLAYING_PATIENT_AUDIO" or state == "WAITING_FOR_PATIENT":
            bg_color = "#FF1744" if self.mic_flash_state else "#800B22"
            self.mic_badge.config(bg=bg_color)
            self.mic_label.config(bg=bg_color)
            self.mic_flash_state = not self.mic_flash_state
            self.after(500, self.flash_mic_indicator)
        else:
            self.mic_badge.config(bg="#FF1744")
            self.mic_label.config(bg="#FF1744")

    def show_countdown(self, seconds_left):
        """
        Updates the 7-second countdown digits.
        """
        self.countdown_label.config(text=str(seconds_left))

    def show_processing(self, status_msg="Analyzing symptoms..."):
        """
        Switches screen to show clinical analysis statuses.
        """
        self.mic_badge.pack_forget()
        self.countdown_label.pack_forget()
        self.prompt_label.config(text=status_msg, fg=COLOR_ACCENT)
        self.status_label.config(text=status_msg)
