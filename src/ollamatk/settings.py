from dataclasses import dataclass
from tkinter import Misc, StringVar
from tkinter.ttk import Combobox, Entry, Frame


@dataclass
class Settings:
    ollama_address: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"


class TkSettingsControls(Frame):
    def __init__(self, parent: Misc, settings: Settings) -> None:
        super().__init__(parent)

        self.grid_columnconfigure("0 1", weight=1)

        self.settings = settings

        self.address_var = StringVar(self)
        self.address = Entry(self, textvariable=self.address_var)
        self.address.grid(row=0, column=0, padx=(0, 20))

        self.model_var = StringVar(self)
        self.model = Combobox(self, textvariable=self.model_var)
        self.model.grid(row=0, column=1)

        self.refresh()

        self.address_var.trace_add("write", self._on_address_var_write)
        self.model_var.trace_add("write", self._on_model_var_write)

    def refresh(self) -> None:
        self.address_var.set(self.settings.ollama_address)
        self.model_var.set(self.settings.ollama_model)

    def set_model_options(self, options: list[str]) -> None:
        self.model.configure(values=options)

    def disable(self) -> None:
        self.address.state(["disabled"])
        self.model.state(["disabled"])

    def enable(self) -> None:
        self.address.state(["!disabled"])
        self.model.state(["!disabled"])

    def _on_address_var_write(self, name1: str, name2: str, op: str) -> None:
        self.settings.ollama_address = self.address_var.get()

    def _on_model_var_write(self, name1: str, name2: str, op: str) -> None:
        self.settings.ollama_model = self.model_var.get()
