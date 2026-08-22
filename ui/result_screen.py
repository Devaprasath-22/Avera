import tkinter as tk
from ui.main_screen import BG_DARK, BG_CARD, FG_PRIMARY, FG_SECONDARY, COLOR_ACCENT, COLOR_TEMP, COLOR_SPO2, COLOR_ECG, COLOR_WARNING

class ResultScreen(tk.Frame):
    """
    Renders the final clinical report screen listing collected vitals, voice transcripts,
    and actions to replay audio or launch a new assessment. Removed all warning labels.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header
        self.header_frame = tk.Frame(self, bg=BG_DARK)
        self.header_frame.grid(row=0, column=0, sticky="nsew", pady=5)
        
        self.title_label = tk.Label(
            self.header_frame,
            text="ASSESSMENT COMPLETE",
            font=("Helvetica", 18, "bold"),
            bg=BG_DARK,
            fg="#00FF66" # Green accent
        )
        self.title_label.pack(pady=15)

        # 2. Content Layout (Grid split into Vitals and Transcript/Response)
        self.content_frame = tk.Frame(self, bg=BG_CARD, bd=1, relief="flat", highlightbackground="#333333", highlightthickness=1)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=5)
        
        self.content_frame.grid_columnconfigure(0, weight=2) # Vitals (left)
        self.content_frame.grid_columnconfigure(1, weight=3) # Speech report (right)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Left Panel - Vitals List
        self.vitals_panel = tk.Frame(self.content_frame, bg=BG_CARD)
        self.vitals_panel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        tk.Label(self.vitals_panel, text="Patient Vitals", font=("Helvetica", 12, "bold"), bg=BG_CARD, fg=FG_PRIMARY).pack(anchor="w", pady=(0, 10))
        
        self.temp_lbl = self._create_vital_row(self.vitals_panel, "🌡 Temperature", "38.2 °C", COLOR_TEMP)
        self.spo2_lbl = self._create_vital_row(self.vitals_panel, "🫁 SpO2", "97 %", COLOR_SPO2)
        self.pulse_lbl = self._create_vital_row(self.vitals_panel, "❤️ Pulse", "82 BPM", COLOR_SPO2)
        self.ecg_lbl = self._create_vital_row(self.vitals_panel, "❤️ ECG", "82 BPM", COLOR_ECG)
        self.doc_lbl = self._create_vital_row(self.vitals_panel, "📄 Document", "Skipped", "#FFFFFF")
        self.rhythm_lbl = tk.Label(self.vitals_panel, text="Normal Sinus Rhythm", font=("Helvetica", 9, "bold"), bg=BG_CARD, fg=COLOR_ACCENT)
        self.rhythm_lbl.pack(pady=2, anchor="w", padx=25)
        
        # Right Panel - Dialogue log
        self.report_panel = tk.Frame(self.content_frame, bg=BG_CARD)
        self.report_panel.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        
        self.lang_lbl = tk.Label(self.report_panel, text="Language: English", font=("Helvetica", 11, "bold"), bg=BG_CARD, fg=COLOR_ACCENT)
        self.lang_lbl.pack(anchor="w", pady=(0, 5))
        
        tk.Label(self.report_panel, text="Patient Transcript:", font=("Helvetica", 10, "bold"), bg=BG_CARD, fg=FG_SECONDARY).pack(anchor="w")
        self.patient_box = tk.Label(
            self.report_panel, 
            text="...", 
            font=("Helvetica", 11, "italic"), 
            bg="#252525", 
            fg=FG_PRIMARY,
            wraplength=230,
            justify="left",
            anchor="w",
            padx=10,
            pady=6,
            bd=1,
            relief="solid"
        )
        self.patient_box.pack(fill="x", pady=(2, 8))
        
        tk.Label(self.report_panel, text="Assistant Recommendation:", font=("Helvetica", 10, "bold"), bg=BG_CARD, fg=FG_SECONDARY).pack(anchor="w")
        self.assistant_box = tk.Label(
            self.report_panel, 
            text="...", 
            font=("Helvetica", 11), 
            bg="#252525", 
            fg=COLOR_ACCENT,
            wraplength=230,
            justify="left",
            anchor="w",
            padx=10,
            pady=6,
            bd=1,
            relief="solid"
        )
        self.assistant_box.pack(fill="both", expand=True, pady=(2, 5))

        # 3. Footer controls
        self.footer_frame = tk.Frame(self, bg=BG_DARK)
        self.footer_frame.grid(row=2, column=0, sticky="nsew", padx=25, pady=10)
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_columnconfigure(1, weight=1)
        self.footer_frame.grid_columnconfigure(2, weight=1)
        
        # Action Buttons
        self.play_btn = tk.Button(
            self.footer_frame, 
            text="🔊 PLAY RESPONSE", 
            font=("Helvetica", 11, "bold"), 
            bg="#333333", 
            fg=FG_PRIMARY, 
            activebackground="#444444",
            activeforeground=FG_PRIMARY,
            bd=0, 
            padx=15, 
            pady=10, 
            cursor="hand2",
            command=self.controller.replay_response_audio
        )
        self.play_btn.grid(row=0, column=0, padx=10, sticky="ew")
        
        self.print_btn = tk.Button(
            self.footer_frame, 
            text="🖨️ PRINT", 
            font=("Helvetica", 11, "bold"), 
            bg="#007AFF", 
            fg="#FFFFFF", 
            activebackground="#005BBB",
            activeforeground="#FFFFFF",
            bd=0, 
            padx=15, 
            pady=10, 
            cursor="hand2",
            command=self.on_print_clicked
        )
        self.print_btn.grid(row=0, column=1, padx=10, sticky="ew")
        
        self.reset_btn = tk.Button(
            self.footer_frame, 
            text="NEW ASSESSMENT", 
            font=("Helvetica", 11, "bold"), 
            bg=COLOR_ACCENT, 
            fg="#000000", 
            activebackground="#00B0D0",
            activeforeground="#000000",
            bd=0, 
            padx=15, 
            pady=10, 
            cursor="hand2",
            command=self.controller.reset_to_idle
        )
        self.reset_btn.grid(row=0, column=2, padx=10, sticky="ew")

    def _create_vital_row(self, parent, label_text, val_text, color) -> tk.Label:
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=4)
        
        tk.Label(row, text=label_text, font=("Helvetica", 11), bg=BG_CARD, fg=FG_SECONDARY).pack(side="left")
        lbl = tk.Label(row, text=val_text, font=("Helvetica", 13, "bold"), bg=BG_CARD, fg=color)
        lbl.pack(side="right", padx=10)
        return lbl

    def on_print_clicked(self):
        import os
        import tempfile
        import subprocess
        from tkinter import messagebox
        
        if os.name == 'nt':
            # Check for printers using PowerShell
            try:
                res = subprocess.run(["powershell", "Get-WmiObject -Query 'SELECT * FROM Win32_Printer'"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if not res.stdout.strip():
                    messagebox.showerror("Printer Error", "No printers are installed on this computer.")
                    return
            except Exception:
                pass # Proceed anyway if WMI check fails
                
            try:
                # Generate text report
                report = f"HEALTHCARE AI ASSESSMENT REPORT\n"
                report += f"==============================\n\n"
                report += f"Patient Name: ___________________________\n"
                report += f"Patient Age:  _______\n"
                report += f"Date:         ___________________________\n\n"
                report += f"Temperature: {self.temp_lbl.cget('text')}\n"
                report += f"SpO2: {self.spo2_lbl.cget('text')}\n"
                report += f"Pulse: {self.pulse_lbl.cget('text')}\n"
                report += f"ECG: {self.ecg_lbl.cget('text')} ({self.rhythm_lbl.cget('text')})\n"
                report += f"Document: {self.doc_lbl.cget('text')}\n\n"
                report += f"Patient Transcript:\n{self.patient_box.cget('text')}\n\n"
                report += f"Assistant Recommendation:\n{self.assistant_box.cget('text')}\n\n"
                report += f"End of Report.\n"
                
                # Save to a temporary text file
                fd, path = tempfile.mkstemp(suffix=".txt")
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                # Send to default Windows printer
                os.startfile(path, "print")
                messagebox.showinfo("Print Job Sent", "The report has been sent to your printer!")
            except Exception as e:
                messagebox.showerror("Print Failed", f"An error occurred while printing: {e}")
        else:
            messagebox.showwarning("Not Supported", "Printing is only supported on Windows currently.")

    def populate_report(self, report):
        """
        Fills labels with scenario assessment metrics.
        """
        self.temp_lbl.config(text=report["temp"])
        self.spo2_lbl.config(text=report["spo2"])
        self.pulse_lbl.config(text=report["pulse"])
        self.ecg_lbl.config(text=report["pulse"] + " BPM")
        
        self.rhythm_lbl.config(text="Normal Sinus Rhythm")
        self.lang_lbl.config(text=f"Language: {report['lang_name']} ({report['native_name']})")
        
        # Display document result if present
        if "document_analysis" in report:
            self.doc_lbl.config(text=report["document_analysis"])
        
        # Display the patient's illness statement as the transcript
        self.patient_box.config(text=report["patient_text"])
        self.assistant_box.config(text=report["assistant_response"])
