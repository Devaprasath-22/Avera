import tkinter as tk
import cv2
from PIL import Image, ImageTk
from ui.main_screen import BG_DARK, BG_CARD, FG_PRIMARY, FG_SECONDARY, COLOR_ACCENT

class CameraScreen(tk.Frame):
    """
    Renders the simulated Camera view for taking a picture of the skin condition.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        self.cap = None
        self.is_capturing = False
        self.current_frame = None
        self.current_mode = "camera"
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=5)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header
        self.header_frame = tk.Frame(self, bg=BG_DARK)
        self.header_frame.grid(row=0, column=0, sticky="nsew", pady=10)
        
        self.title_label = tk.Label(
            self.header_frame,
            text="SKIN ISSUE CAPTURE",
            font=("Consolas", 16, "bold"),
            bg=BG_DARK,
            fg=COLOR_ACCENT
        )
        self.title_label.pack(pady=10)
        
        # 2. Camera Viewfinder
        self.content_frame = tk.Frame(self, bg=BG_CARD, bd=3, relief="ridge", highlightbackground="#00FF00", highlightthickness=1)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=5)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.camera_box = tk.Frame(self.content_frame, bg="#081008")
        self.camera_box.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.camera_box.grid_rowconfigure(0, weight=1)
        self.camera_box.grid_columnconfigure(0, weight=1)
        
        self.viewfinder_label = tk.Label(
            self.camera_box,
            text="[ Camera Feed Loading... ]",
            font=("Consolas", 12, "italic"),
            bg="#081008",
            fg="#777777"
        )
        self.viewfinder_label.grid(row=0, column=0)
        
        self.overlay_label = tk.Label(
            self.camera_box,
            text="",
            font=("Consolas", 14, "bold"),
            bg="#081008",
            fg="#00E676"
        )
        # We will pack this over the viewfinder when analyzing
        
        # 3. Footer with Capture Button
        self.footer_frame = tk.Frame(self, bg=BG_DARK)
        self.footer_frame.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_columnconfigure(1, weight=1)
        
        # Center the buttons by creating an inner frame
        self.buttons_frame = tk.Frame(self.footer_frame, bg=BG_DARK)
        self.buttons_frame.pack(expand=True)
        
        self.capture_btn = tk.Button(
            self.buttons_frame, 

            text="📷 CAPTURE", 
            font=("Consolas", 12, "bold"), 
            bg="#FF1744", 
            fg="#FFFFFF", 
            activebackground="#D50000",
            activeforeground="#FFFFFF",
            bd=1, relief="solid", 
            padx=20, 
            pady=10, 
            cursor="hand2",
            command=self._on_capture_clicked
        )
        self.capture_btn.grid(row=0, column=0, padx=10)
        
        self.skip_btn = tk.Button(
            self.buttons_frame, 
            text="⏭ SKIP", 
            font=("Consolas", 12, "bold"), 
            bg="#555555", 
            fg="#FFFFFF", 
            activebackground="#777777",
            activeforeground="#FFFFFF",
            bd=1, relief="solid", 
            padx=20, 
            pady=10, 
            cursor="hand2",
            command=self._on_skip_clicked
        )
        self.skip_btn.grid(row=0, column=1, padx=10)

    def _on_capture_clicked(self):
        self.is_capturing = False # Stop the live feed loop
        self.controller.run_camera_capture(self.current_mode)
        
    def _on_skip_clicked(self):
        self.is_capturing = False # Stop the live feed loop
        self.controller.run_camera_skip(self.current_mode)

    def show_ready(self, mode="camera"):
        self.current_mode = mode
        if mode == "document":
            self.title_label.config(text="X-RAY / LAB REPORT CAPTURE")
            self.capture_btn.config(text="📷 CAPTURE DOC")
        else:
            self.title_label.config(text="SKIN ISSUE CAPTURE")
            self.capture_btn.config(text="📷 CAPTURE ISSUE")
            
        self.overlay_label.place_forget()
        self.capture_btn.config(state="normal", bg="#FF1744")
        self.skip_btn.config(state="normal", bg="#555555")
        self.is_capturing = True
        
        if self.cap is None:
            # Open default webcam (0)
            self.cap = cv2.VideoCapture(0)
            
        self._update_frame()
        
    def _update_frame(self):
        if not self.is_capturing:
            return
            
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Convert BGR to RGB
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to fit the box (approx 400x300)
                img = Image.fromarray(cv2image).resize((400, 300), Image.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                self.viewfinder_label.imgtk = imgtk
                self.viewfinder_label.configure(image=imgtk, text="")
        
        self.after(30, self._update_frame)
        
    def show_analyzing(self, countdown, message="Analyzing skin condition..."):
        self.capture_btn.config(state="disabled", bg="#555555")
        self.skip_btn.config(state="disabled", bg="#333333")
        self.overlay_label.place(relx=0.5, rely=0.5, anchor="center")
        
        if countdown > 0:
            self.overlay_label.config(
                text=f"Image Captured!\n\n{message}\n{countdown} seconds remaining"
            )
        else:
            self.overlay_label.config(text="Analysis Complete!\nGenerating Diagnosis...")
            self.stop_camera()

    def stop_camera(self):
        self.is_capturing = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
