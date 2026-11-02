import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import subprocess
import threading
import shutil
import re

APP_TITLE = "Basket Video Cutter"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("820x690")
        self.root.minsize(700, 600)
        self.video = tk.StringVar()
        self.output = tk.StringVar()
        self.before = tk.StringVar(value="5")
        self.after = tk.StringVar(value="11")
        self.quality = tk.StringVar(value="Alta (CRF 18)")
        self.ffmpeg = tk.StringVar(value=shutil.which("ffmpeg") or "")
        self.status = tk.StringVar(value="Seleziona un video e inserisci i tempi delle azioni.")
        self.busy = False
        self.build()

    def build(self):
        pad = {"padx": 12, "pady": 6}
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="BASKET VIDEO CUTTER", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="Taglia automaticamente le azioni usando i tempi del video.",
                  foreground="#555").pack(anchor="w", pady=(0, 10))

        ttk.Label(main, text="File video").pack(anchor="w")
        row = ttk.Frame(main); row.pack(fill="x", **pad)
        ttk.Entry(row, textvariable=self.video).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Sfoglia…", command=self.pick_video).pack(side="left", padx=(8, 0))

        ttk.Label(main, text="Cartella di destinazione").pack(anchor="w")
        row = ttk.Frame(main); row.pack(fill="x", **pad)
        ttk.Entry(row, textvariable=self.output).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Sfoglia…", command=self.pick_output).pack(side="left", padx=(8, 0))

        opts = ttk.Frame(main); opts.pack(fill="x", **pad)
        ttk.Label(opts, text="Taglia:").pack(side="left")
        ttk.Label(opts, text="secondi prima del riferimento").pack(side="left", padx=(8, 3))
        ttk.Entry(opts, textvariable=self.before, width=6).pack(side="left")
        ttk.Label(opts, text="secondi dopo").pack(side="left", padx=(12, 3))
        ttk.Entry(opts, textvariable=self.after, width=6).pack(side="left")

        quality_row = ttk.Frame(main); quality_row.pack(fill="x", **pad)
        ttk.Label(quality_row, text="Qualità video:").pack(side="left")
        self.quality_box = ttk.Combobox(
            quality_row, textvariable=self.quality, state="readonly", width=25,
            values=("Standard (CRF 20)", "Alta (CRF 18)", "Massima (CRF 16)")
        )
        self.quality_box.pack(side="left", padx=8)
        ttk.Label(quality_row, text="Più alta = file più grandi e codifica più lenta.",
                  foreground="#555").pack(side="left", padx=8)

        ttk.Label(main, text="Elenco azioni (formato MM:SS numero_giocatore)").pack(anchor="w", pady=(12, 2))
        self.text = tk.Text(main, height=12, font=("Consolas", 11), wrap="none")
        self.text.pack(fill="both", expand=True, padx=12)
        self.text.insert("1.0", "01:15 A\n02:20 D\n03:45 A\n10:25 D\n")

        ttk.Label(main, text="Con i valori iniziali, 08:50 6 crea un clip da 08:45 a 09:01. Il numero del giocatore compare nel nome del file.",
                  foreground="#555", wraplength=760).pack(anchor="w", padx=12, pady=5)

        ffrow = ttk.Frame(main); ffrow.pack(fill="x", **pad)
        ttk.Label(ffrow, text="FFmpeg:").pack(side="left")
        ttk.Entry(ffrow, textvariable=self.ffmpeg).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(ffrow, text="Seleziona…", command=self.pick_ffmpeg).pack(side="left")

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(12, 4))
        ttk.Label(main, textvariable=self.status, wraplength=760).pack(anchor="w", padx=12, pady=4)

        bottom = ttk.Frame(main); bottom.pack(fill="x", padx=12, pady=10)
        self.go = ttk.Button(bottom, text="GENERA TUTTI I TAGLI", command=self.start)
        self.go.pack(side="right")
        ttk.Button(bottom, text="Pulisci elenco", command=lambda: self.text.delete("1.0", "end")).pack(side="left")

    def pick_video(self):
        p = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi *.m4v"), ("Tutti i file", "*.*")])
        if p:
            self.video.set(p)
            if not self.output.get():
                self.output.set(str(Path(p).parent / (Path(p).stem + "_Tagli")))

    def pick_output(self):
        p = filedialog.askdirectory()
        if p: self.output.set(p)

    def pick_ffmpeg(self):
        p = filedialog.askopenfilename(filetypes=[("FFmpeg", "ffmpeg.exe"), ("Eseguibili", "*.exe"), ("Tutti i file", "*.*")])
        if p: self.ffmpeg.set(p)

    @staticmethod
    def to_seconds(value):
        m = re.fullmatch(r"\s*(\d+):([0-5]\d)(?::([0-5]\d))?\s*", value)
        if not m: raise ValueError(f"Tempo non valido: {value}")
        if m.group(3) is not None:
            return int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
        return int(m.group(1))*60 + int(m.group(2))

    def parse_actions(self):
        lines = self.text.get("1.0", "end").splitlines()
        actions = []
        for n, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(f"Riga {n}: usa il formato 08:50 6 oppure 21:00 20.")
            sec = self.to_seconds(parts[0])
            player = re.sub(r"[^0-9A-Za-z-]", "", parts[1])
            if not player:
                raise ValueError(f"Riga {n}: inserisci il numero del giocatore.")
            actions.append((sec, player))
        if not actions: raise ValueError("Inserisci almeno un'azione.")
        return actions

    def start(self):
        if self.busy: return
        video = Path(self.video.get())
        out = Path(self.output.get())
        ff = self.ffmpeg.get().strip()
        try:
            if not video.is_file(): raise ValueError("Seleziona un file video valido.")
            if not ff or not Path(ff).is_file():
                found = shutil.which("ffmpeg")
                if found: ff = found
                else: raise ValueError("FFmpeg non trovato. Seleziona ffmpeg.exe oppure installa FFmpeg.")
            before = float(self.before.get().replace(",", "."))
            after = float(self.after.get().replace(",", "."))
            if before < 0 or after < 0 or before + after <= 0 or before > 3600 or after > 3600:
                raise ValueError("I secondi prima/dopo devono essere non negativi e avere una durata totale maggiore di zero.")
            actions = self.parse_actions()
            quality_profiles = {
                "Standard (CRF 20)": ("20", "veryfast"),
                "Alta (CRF 18)": ("18", "medium"),
                "Massima (CRF 16)": ("16", "slow"),
            }
            crf, preset = quality_profiles[self.quality.get()]
            out.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Controllo dati", str(e)); return
        self.busy = True
        self.go.configure(state="disabled")
        self.progress["maximum"] = len(actions); self.progress["value"] = 0
        threading.Thread(target=self.process, args=(str(video), str(out), ff, before, after, actions, crf, preset), daemon=True).start()

    def process(self, video, out, ff, before, after, actions, crf, preset):
        errors = []
        for i, (point, player) in enumerate(actions, 1):
            start = max(0, point-before)
            end = point+after
            if end <= start:
                errors.append(f"Azione {i}: intervallo non valido"); continue
            name = f"{i:03d}_G{player}_{point//60:02d}-{point%60:02d}.mp4"
            target = str(Path(out) / name)
            cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start),
                   "-i", video, "-t", str(end-start), "-map", "0:v:0", "-map", "0:a?",
                   "-c:v", "libx264", "-preset", preset, "-crf", crf,
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", target]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    errors.append(f"{name}: {result.stderr.strip()[-500:]}")
            except Exception as e:
                errors.append(f"{name}: {e}")
            self.root.after(0, self.update_progress, i, len(actions), name)
        self.root.after(0, self.finish, errors, out)

    def update_progress(self, value, total, name):
        self.progress["value"] = value
        self.status.set(f"Elaborazione {value}/{total}: {name}")

    def finish(self, errors, out):
        self.busy = False
        self.go.configure(state="normal")
        if errors:
            self.status.set(f"Completato con {len(errors)} errore/i. Controlla il messaggio.")
            messagebox.showwarning("Elaborazione terminata", f"Cartella: {out}\n\nErrori:\n" + "\n".join(errors[:8]))
        else:
            self.status.set(f"Completato: {int(self.progress['value'])} clip creati in {out}")
            messagebox.showinfo("Fatto!", f"Tutti i tagli sono stati creati.\n\nCartella:\n{out}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
