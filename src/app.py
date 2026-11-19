import ipaddress
import socket
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from urllib.parse import urlsplit
from nas import Synology
from lan import start_receiver, send_file

BG = "#17191f"
PANEL = "#252932"
FG = "#f2f4f8"
ACCENT = "#65b2f7"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IZI Transfer")
        self.geometry("710x680")
        self.configure(bg=BG)
        self.files = []
        self.receiver = None
        self.mode = tk.StringVar(value="internet")
        self.name = tk.StringVar()
        self.url = tk.StringVar(value="http://192.168.1.31:5000")
        self.username = tk.StringVar(value="izi-transfer")
        self.password = tk.StringVar()
        self.host = tk.StringVar()
        self.token = tk.StringVar()
        self.status = tk.StringVar(value="Pronto")
        self.make_ui()

    def label(self, text):
        return tk.Label(self, text=text, bg=BG, fg=FG, anchor="w")

    def entry(self, variable, secret=False):
        return tk.Entry(self, textvariable=variable, show="*" if secret else "",
                        bg=PANEL, fg=FG, insertbackground=FG, relief="flat", font=("Arial", 11))

    def make_ui(self):
        tk.Label(self, text="IZI  TRANSFER", bg=BG, fg=FG,
                 font=("Arial", 22, "bold")).pack(anchor="w", padx=24, pady=(22, 5))
        tk.Label(self, text="Invio diretto LAN o consegna tramite Synology",
                 bg=BG, fg=ACCENT).pack(anchor="w", padx=24)
        options = tk.Frame(self, bg=BG)
        options.pack(fill="x", padx=24, pady=16)
        for text, value in (("Internet · NAS", "internet"), ("Locale · diretto", "local")):
            tk.Radiobutton(options, text=text, value=value, variable=self.mode,
                           command=self.refresh, bg=BG, fg=FG, selectcolor=PANEL,
                           activebackground=BG, activeforeground=FG).pack(side="left", padx=(0, 25))
        self.label("Nome del trasferimento").pack(fill="x", padx=24)
        self.entry(self.name).pack(fill="x", padx=24, pady=(3, 10), ipady=7)
        self.label("File selezionati").pack(fill="x", padx=24)
        self.files_label = tk.Label(self, text="Nessun file", bg=PANEL, fg=FG,
                                    anchor="w", padx=12, height=2)
        self.files_label.pack(fill="x", padx=24, pady=5)
        tk.Button(self, text="Aggiungi file", command=self.add_files).pack(anchor="w", padx=24)
        self.internet_frame = tk.Frame(self, bg=BG)
        self.local_frame = tk.Frame(self, bg=BG)
        self.field(self.internet_frame, "Indirizzo NAS", self.url)
        self.field(self.internet_frame, "Utente", self.username)
        self.field(self.internet_frame, "Password (non salvata)", self.password, True)
        self.field(self.local_frame, "IP del destinatario", self.host)
        self.field(self.local_frame, "Codice temporaneo del destinatario", self.token)
        tk.Button(self.local_frame, text="Avvia ricezione file", command=self.receive).pack(anchor="w", pady=8)
        self.info = tk.Label(self, text="", bg=BG, fg=ACCENT, wraplength=650, justify="left")
        self.info.pack(fill="x", padx=24, pady=7)
        tk.Button(self, text="AVVIA TRASFERIMENTO", command=self.transfer,
                  bg=ACCENT, fg="#10151e", font=("Arial", 11, "bold"), pady=10).pack(fill="x", padx=24, pady=10)
        tk.Label(self, textvariable=self.status, bg=BG, fg=FG,
                 wraplength=650, justify="left").pack(fill="x", padx=24)
        self.refresh()

    def field(self, parent, label, variable, secret=False):
        tk.Label(parent, text=label, bg=BG, fg=FG).pack(anchor="w")
        tk.Entry(parent, textvariable=variable, show="*" if secret else "",
                 bg=PANEL, fg=FG, insertbackground=FG, relief="flat").pack(fill="x", pady=(3, 9), ipady=5)

    def refresh(self):
        self.internet_frame.pack_forget()
        self.local_frame.pack_forget()
        if self.mode.get() == "internet":
            self.internet_frame.pack(fill="x", padx=24)
            self.info.config(text="Caricamento sul NAS. Per ora solo indirizzi LAN; accesso remoto da implementare.")
        else:
            self.local_frame.pack(fill="x", padx=24)
            self.info.config(text="Trasferimento diretto tra due computer nella stessa rete, senza NAS.")

    def add_files(self):
        selected = filedialog.askopenfilenames()
        self.files.extend(f for f in selected if f not in self.files)
        self.files_label.config(text=f"{len(self.files)} file selezionati")

    def set_status(self, value):
        self.after(0, lambda: self.status.set(value))

    def receive(self):
        if self.receiver:
            return
        folder = filedialog.askdirectory(title="Cartella di ricezione")
        if not folder:
            return
        try:
            self.receiver, code = start_receiver(folder)
            ip = socket.gethostbyname(socket.gethostname())
            self.set_status(f"Ricezione attiva sulla porta 8765. IP indicativo: {ip}\nCodice: {code}\nComunica IP e codice al mittente.")
        except Exception as e:
            messagebox.showerror("Ricezione", str(e))

    def transfer(self):
        if not self.files:
            messagebox.showwarning("IZI Transfer", "Seleziona almeno un file")
            return
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            if self.mode.get() == "local":
                if not self.host.get().strip() or not self.token.get().strip():
                    raise ValueError("Inserisci IP e codice del destinatario")
                for i, file in enumerate(self.files, 1):
                    self.set_status(f"Invio LAN {i}/{len(self.files)}: {Path(file).name}")
                    send_file(self.host.get().strip(), 8765, self.token.get().strip(), file)
                self.set_status("Trasferimento LAN completato")
            else:
                url = self.url.get().strip()
                parsed = urlsplit(url)
                if parsed.scheme != "https":
                    if parsed.scheme != "http":
                        raise ValueError("Indirizzo NAS non valido")
                    try:
                        ip = ipaddress.ip_address(parsed.hostname)
                        if not ip.is_private:
                            raise ValueError("HTTP consentito soltanto per IP privati LAN")
                    except ValueError as e:
                        raise ValueError("Usa HTTPS oppure un IP privato LAN con HTTP") from e
                if not self.name.get().strip():
                    raise ValueError("Inserisci il nome del trasferimento")
                nas = Synology(url, self.username.get(), self.password.get())
                try:
                    self.set_status("Accesso al NAS...")
                    nas.login()
                    destination = nas.create_transfer(self.name.get())
                    for i, file in enumerate(self.files, 1):
                        self.set_status(f"Caricamento {i}/{len(self.files)}: {Path(file).name}")
                        nas.upload(destination, file)
                    link = nas.share(destination)
                    self.set_status("Trasferimento completato. Link: " + link)
                finally:
                    nas.logout()
        except Exception as e:
            self.set_status("Errore: " + str(e))

if __name__ == "__main__":
    App().mainloop()
