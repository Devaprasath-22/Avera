# State constants
IDLE = "IDLE"
INITIALIZING = "INITIALIZING"
MEASURING_TEMPERATURE = "MEASURING_TEMPERATURE"
MEASURING_OXIMETER = "MEASURING_OXIMETER"
MEASURING_ECG = "MEASURING_ECG"
VITALS_COMPLETE = "VITALS_COMPLETE"
CAMERA_CAPTURE = "CAMERA_CAPTURE"
ANALYZING_IMAGE = "ANALYZING_IMAGE"
DOCUMENT_CAPTURE = "DOCUMENT_CAPTURE"
PLAYING_DOCUMENT_AUDIO = "PLAYING_DOCUMENT_AUDIO"
VOICE_INITIALIZING = "VOICE_INITIALIZING"
PLAYING_PATIENT_AUDIO = "PLAYING_PATIENT_AUDIO"
PROCESSING_SPEECH = "PROCESSING_SPEECH"
DETECTING_LANGUAGE = "DETECTING_LANGUAGE"
ANALYZING_SYMPTOMS = "ANALYZING_SYMPTOMS"
GENERATING_RESPONSE = "GENERATING_RESPONSE"
WAITING_FOR_PATIENT = "WAITING_FOR_PATIENT"
PREPARING_RESPONSE_AUDIO = "PREPARING_RESPONSE_AUDIO"
PLAYING_RESPONSE = "PLAYING_RESPONSE"
ASSESSMENT_COMPLETE = "ASSESSMENT_COMPLETE"
ERROR = "ERROR"

class StateManager:
    """
    Manages the application's active state, transitions, and the user-selected language.
    """
    def __init__(self):
        self._current_state = IDLE
        self._selected_lang = "en"
        self._callbacks = []
        
    def register_callback(self, callback):
        self._callbacks.append(callback)
        
    def set_state(self, new_state):
        if new_state == self._current_state:
            return
            
        old_state = self._current_state
        self._current_state = new_state
        print(f"[State Transition] {old_state} -> {new_state}")
        
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                print(f"[StateManager Error] Callback failed: {e}")
                
    def get_state(self) -> str:
        return self._current_state
        
    def set_selected_language(self, lang_code: str):
        self._selected_lang = lang_code.lower()
        print(f"[StateManager] Language set to: {self._selected_lang}")
        
    def get_current_language(self) -> str:
        return self._selected_lang
