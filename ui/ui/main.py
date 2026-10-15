"""OmniOS desktop application launcher."""
from __future__ import annotations
import threading
import traceback
import tkinter as tk
from typing import Optional
import customtkinter as ctk
from app import process_command
from core.schemas import ExecutionResult, ResultStatus, Route, RoutingDecision, Intent
from ui.state import AppState
from ui.styles import COLORS, DIMS
from ui.components.central_panel import CentralPanel
from ui.components.right_sidebar import RightSidebar

class OmniOSApp(ctk.CTk):
    """Two-column desktop UI matching the approved OmniOS reference."""
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("OmniOS")
        self.geometry("1536x1024")
        self.minsize(1100, 720)
        self.configure(fg_color=COLORS["window_bg"])
        self.state_store = AppState()
        self._closing = False
        self._workers: set[threading.Thread] = set()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3, minsize=700)
        self.grid_columnconfigure(1, weight=1, minsize=330)
        self.central_panel = CentralPanel(self, state=self.state_store, on_submit=self.submit_command)
        self.central_panel.grid(row=0, column=0, sticky="nsew")
        self.right_sidebar = RightSidebar(self, state=self.state_store, width=360)
        self.right_sidebar.grid(row=0, column=1, sticky="nsew")
        self.right_sidebar.grid_propagate(False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def submit_command(self, command: str) -> None:
        command = command.strip()
        if not command or self._closing or self.state_store.is_processing:
            return
        self.state_store.set_processing(True)
        worker = threading.Thread(target=self._execute_command, args=(command,), name="OmniOSCommandWorker", daemon=True)
        self._workers.add(worker)
        worker.start()

    def _execute_command(self, command: str) -> None:
        try:
            decision, result = process_command(command)
        except Exception as exc:
            traceback.print_exc()
            decision = RoutingDecision(intent=Intent.UNKNOWN, route=Route.NONE, confidence=0.0,
                                       explanation="Command execution raised an exception.")
            result = ExecutionResult(status=ResultStatus.ERROR, output=None,
                                     error=f"{type(exc).__name__}: {exc}", used_llm=False)
        try:
            self.after(0, lambda d=decision, r=result, c=command: self._finish_command(d, r, c))
        except (tk.TclError, RuntimeError):
            pass

    def _finish_command(self, decision: RoutingDecision, result: Optional[ExecutionResult], command: str) -> None:
        self._workers = {worker for worker in self._workers if worker.is_alive()}
        if self._closing:
            return
        try:
            self.state_store.update_result(decision, result, command)
        except Exception:
            traceback.print_exc()
        finally:
            self.state_store.set_processing(False)

    def _on_close(self) -> None:
        self._closing = True
        self.destroy()

def main() -> None:
    app = OmniOSApp()
    app.mainloop()

if __name__ == "__main__":
    main()
