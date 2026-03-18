"""
╔══════════════════════════════════════════════════════════════╗
║       🤖 BOT ORGANIZADOR DE ARCHIVOS — Interfaz GUI          ║
║       Tkinter + Python 3.7+  |  Windows                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import shutil
import hashlib
import threading
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ─────────────────────────────────────────────
#  CATEGORÍAS
# ─────────────────────────────────────────────
CATEGORIAS = {
    "📷 Fotos":       [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".raw"],
    "🎬 Videos":      [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "🎵 Música":      [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "📄 Documentos":  [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"],
    "💻 Código":      [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".json", ".xml", ".sql"],
    "📦 Comprimidos": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso"],
    "🖋️ Diseño":      [".psd", ".ai", ".svg", ".fig", ".sketch", ".eps"],
    "⚙️ Ejecutables": [".exe", ".msi", ".apk"],
    "📁 Otros":       [],
}

COLORES = {
    "fondo":       "#0F0F1A",
    "panel":       "#1A1A2E",
    "card":        "#16213E",
    "acento":      "#E94560",
    "acento2":     "#F5A623",
    "verde":       "#0FCF8F",
    "texto":       "#E8E8F0",
    "texto_dim":   "#8888AA",
    "borde":       "#2A2A4A",
    "hover":       "#252545",
}

# ─────────────────────────────────────────────
#  LÓGICA DE ORGANIZACIÓN
# ─────────────────────────────────────────────
def detectar_categoria(ext: str) -> str:
    ext = ext.lower()
    for cat, exts in CATEGORIAS.items():
        if ext in exts:
            return cat
    return "📁 Otros"

def hash_archivo(ruta: Path) -> str:
    h = hashlib.md5()
    try:
        with open(ruta, "rb") as f:
            h.update(f.read(65536))
        return h.hexdigest()
    except Exception:
        return ""

def nombre_sin_colision(destino: Path) -> Path:
    if not destino.exists():
        return destino
    stem, suffix = destino.stem, destino.suffix
    i = 1
    while True:
        nuevo = destino.parent / f"{stem} ({i}){suffix}"
        if not nuevo.exists():
            return nuevo
        i += 1

def organizar(carpeta: Path, preview: bool, log_cb, prog_cb):
    if not carpeta.exists():
        log_cb(f"⚠️  No encontrada: {carpeta}", "warn")
        return {}

    archivos = [f for f in carpeta.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not archivos:
        log_cb(f"ℹ️  Sin archivos: {carpeta.name}", "info")
        return {}

    stats = defaultdict(int)
    hashes = {}
    papelera = carpeta / "_Duplicados"
    total = len(archivos)

    for i, archivo in enumerate(sorted(archivos), 1):
        prog_cb(i, total)

        # 🔍 DEBUG
        log_cb(f"🔍 Procesando: {archivo.name}", "info")

        # 🚫 Ignorar tu propio script
        if archivo.suffix == ".py":
            continue

        # 🧠 Detectar extensión (maneja mayúsculas y sin extensión)
        ext = archivo.suffix.lower() if archivo.suffix else ""

        if ext == "":
            log_cb(f"📂 Sin extensión: {archivo.name}", "warn")

        # 🔁 Duplicados
        try:
            h = hash_archivo(archivo)
        except Exception as e:
            log_cb(f"❌ Error calculando hash {archivo.name}: {e}", "warn")
            h = ""

        if h and h in hashes:
            try:
                if not preview:
                    papelera.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(archivo), str(nombre_sin_colision(papelera / archivo.name)))
                log_cb(f"🗑️  Duplicado: {archivo.name}", "warn")
                stats["_duplicados"] += 1
            except Exception as e:
                log_cb(f"❌ Error moviendo duplicado {archivo.name}: {e}", "warn")
            continue

        if h:
            hashes[h] = archivo

        # 📂 Categoría (fallback automático)
        cat = detectar_categoria(ext)
        fecha = datetime.fromtimestamp(archivo.stat().st_mtime).strftime("%Y/%m - %B")
        dest_dir = carpeta / cat / fecha
        dest = nombre_sin_colision(dest_dir / archivo.name)

        # 🚚 Mover archivo con control de errores
        try:
            if not preview:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(archivo), str(dest))

            log_cb(f"{'👁️' if preview else '✅'}  {archivo.name} → {cat}/", "ok")
            stats[cat] += 1

        except Exception as e:
            log_cb(f"❌ Error moviendo {archivo.name}: {e}", "warn")

    return dict(stats)

# ─────────────────────────────────────────────
#  APLICACIÓN GUI
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🤖 Organizador de Archivos")
        self.geometry("820x640")
        self.minsize(700, 560)
        self.configure(bg=COLORES["fondo"])
        self.resizable(True, True)

        # Estado
        self.carpetas: list[Path] = []
        self.corriendo = False
        self._agregar_carpetas_default()

        self._build_ui()

    # ── Carpetas default ──
    def _agregar_carpetas_default(self):
        home = Path.home()
        for nombre in ("Downloads", "Desktop"):
            p = home / nombre
            if p.exists() and p not in self.carpetas:
                self.carpetas.append(p)

    # ── UI ──
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORES["panel"], pady=14)
        header.pack(fill="x")
        tk.Label(header, text="🤖  Organizador de Archivos",
                 font=("Segoe UI", 17, "bold"),
                 bg=COLORES["panel"], fg=COLORES["texto"]).pack(side="left", padx=22)
        tk.Label(header, text="v2.0  •  Windows",
                 font=("Segoe UI", 9),
                 bg=COLORES["panel"], fg=COLORES["texto_dim"]).pack(side="right", padx=22)

        # Cuerpo
        body = tk.Frame(self, bg=COLORES["fondo"])
        body.pack(fill="both", expand=True, padx=18, pady=12)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        # ── Sección carpetas ──
        self._lbl_section(body, "📂  Carpetas a organizar", row=0)

        carpeta_frame = tk.Frame(body, bg=COLORES["card"],
                                  highlightbackground=COLORES["borde"],
                                  highlightthickness=1, bd=0)
        carpeta_frame.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        # Lista de carpetas
        lista_wrap = tk.Frame(carpeta_frame, bg=COLORES["card"])
        lista_wrap.pack(fill="x", padx=12, pady=10)

        self.lista_frame = tk.Frame(lista_wrap, bg=COLORES["card"])
        self.lista_frame.pack(fill="x")

        # Botones agregar/limpiar
        btn_row = tk.Frame(carpeta_frame, bg=COLORES["card"])
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        self._btn(btn_row, "＋  Agregar carpeta", self._agregar_carpeta,
                  COLORES["acento2"], side="left")
        self._btn(btn_row, "＋  Agregar ruta manual", self._agregar_manual,
                  COLORES["acento"], side="left", ml=8)
        self._btn(btn_row, "🗑  Limpiar lista", self._limpiar_lista,
                  COLORES["borde"], side="right")

        self._render_lista()

        # ── Log ──
        self._lbl_section(body, "📋  Registro de actividad", row=2, pady_top=4)

        log_frame = tk.Frame(body, bg=COLORES["card"],
                              highlightbackground=COLORES["borde"],
                              highlightthickness=1)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(4, 10))
        body.rowconfigure(3, weight=1)

        self.log_text = tk.Text(
            log_frame, bg=COLORES["card"], fg=COLORES["texto"],
            font=("Consolas", 9), bd=0, padx=10, pady=8,
            state="disabled", wrap="word",
            insertbackground=COLORES["texto"],
        )
        self.log_text.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set)

        # Tags de color
        self.log_text.tag_config("ok",   foreground=COLORES["verde"])
        self.log_text.tag_config("warn", foreground=COLORES["acento2"])
        self.log_text.tag_config("info", foreground=COLORES["texto_dim"])
        self.log_text.tag_config("head", foreground=COLORES["acento"],
                                  font=("Consolas", 9, "bold"))

        # ── Barra de progreso + opciones ──
        bottom = tk.Frame(body, bg=COLORES["fondo"])
        bottom.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        bottom.columnconfigure(1, weight=1)

        # Checkbox preview
        self.preview_var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(
            bottom, text="Modo Preview (no mueve archivos)",
            variable=self.preview_var,
            bg=COLORES["fondo"], fg=COLORES["texto_dim"],
            selectcolor=COLORES["card"],
            activebackground=COLORES["fondo"],
            activeforeground=COLORES["texto"],
            font=("Segoe UI", 9), bd=0,
        )
        chk.grid(row=0, column=0, sticky="w")

        self.prog_bar = ttk.Progressbar(bottom, mode="determinate", maximum=100)
        self.prog_bar.grid(row=0, column=1, sticky="ew", padx=12)

        # Estilo barra
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TProgressbar",
                         troughcolor=COLORES["card"],
                         background=COLORES["verde"],
                         thickness=10)

        self.btn_organizar = self._btn(
            bottom, "🚀  Organizar ahora", self._iniciar,
            COLORES["acento"], side=None, grid=(0, 2)
        )

    # ── Helpers UI ──
    def _lbl_section(self, parent, texto, row, pady_top=0):
        tk.Label(parent, text=texto,
                 font=("Segoe UI", 10, "bold"),
                 bg=COLORES["fondo"], fg=COLORES["texto_dim"]
                 ).grid(row=row, column=0, sticky="w", pady=(pady_top, 2))

    def _btn(self, parent, texto, cmd, color, side="left", ml=0, grid=None):
        b = tk.Button(
            parent, text=texto, command=cmd,
            bg=color, fg="#fff",
            font=("Segoe UI", 9, "bold"),
            bd=0, padx=12, pady=6, cursor="hand2",
            activebackground=COLORES["hover"],
            activeforeground="#fff", relief="flat",
        )
        if grid:
            b.grid(row=grid[0], column=grid[1], sticky="e")
        else:
            b.pack(side=side, padx=(ml, 0))
        return b

    def _render_lista(self):
        for w in self.lista_frame.winfo_children():
            w.destroy()

        if not self.carpetas:
            tk.Label(self.lista_frame,
                     text="  Sin carpetas. Agrega una arriba.",
                     font=("Segoe UI", 9), bg=COLORES["card"],
                     fg=COLORES["texto_dim"]).pack(anchor="w", pady=4)
            return

        for i, ruta in enumerate(self.carpetas):
            fila = tk.Frame(self.lista_frame, bg=COLORES["card"])
            fila.pack(fill="x", pady=2)

            exists = ruta.exists()
            color_ruta = COLORES["texto"] if exists else COLORES["acento"]
            icono = "📂" if exists else "⚠️"

            tk.Label(fila, text=icono, bg=COLORES["card"],
                     font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
            tk.Label(fila, text=str(ruta),
                     font=("Segoe UI", 9), bg=COLORES["card"],
                     fg=color_ruta).pack(side="left", fill="x", expand=True)

            idx = i
            tk.Button(
                fila, text="✕", command=lambda x=idx: self._quitar(x),
                bg=COLORES["card"], fg=COLORES["texto_dim"],
                font=("Segoe UI", 8), bd=0, cursor="hand2",
                activebackground=COLORES["acento"],
                activeforeground="#fff", relief="flat", padx=4,
            ).pack(side="right")

    def _agregar_carpeta(self):
        ruta = filedialog.askdirectory(title="Selecciona una carpeta")
        if ruta:
            p = Path(ruta)
            if p not in self.carpetas:
                self.carpetas.append(p)
                self._render_lista()

    def _agregar_manual(self):
        ventana = tk.Toplevel(self)
        ventana.title("Agregar ruta manual")
        ventana.geometry("480x130")
        ventana.configure(bg=COLORES["fondo"])
        ventana.resizable(False, False)
        ventana.grab_set()

        tk.Label(ventana, text="Escribe o pega la ruta completa:",
                 bg=COLORES["fondo"], fg=COLORES["texto"],
                 font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(14, 4))

        entrada = tk.Entry(ventana, font=("Consolas", 10),
                           bg=COLORES["card"], fg=COLORES["texto"],
                           insertbackground=COLORES["texto"],
                           relief="flat", bd=0)
        entrada.pack(fill="x", padx=18, ipady=6)
        entrada.focus()

        def confirmar():
            txt = entrada.get().strip()
            if txt:
                p = Path(txt)
                if p not in self.carpetas:
                    self.carpetas.append(p)
                    self._render_lista()
            ventana.destroy()

        entrada.bind("<Return>", lambda e: confirmar())
        self._btn(ventana, "Agregar", confirmar, COLORES["acento"], side="left")
        ventana.pack_slaves()[-1].pack(padx=18, pady=10, anchor="w")

    def _quitar(self, idx):
        if 0 <= idx < len(self.carpetas):
            self.carpetas.pop(idx)
            self._render_lista()

    def _limpiar_lista(self):
        self.carpetas.clear()
        self._render_lista()

    # ── Log ──
    def _log(self, msg, tag="info"):
        def _do():
            self.log_text.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{ts}]  {msg}\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _do)

    def _set_prog(self, val, total):
        pct = int(val / total * 100) if total else 0
        self.after(0, lambda: self.prog_bar.configure(value=pct))

    # ── Organizar ──
    def _iniciar(self):
        if self.corriendo:
            return
        if not self.carpetas:
            messagebox.showwarning("Sin carpetas", "Agrega al menos una carpeta.")
            return

        invalidas = [str(c) for c in self.carpetas if not c.exists()]
        if invalidas:
            if not messagebox.askyesno("Rutas no encontradas",
                f"Estas rutas no existen:\n" + "\n".join(invalidas) +
                "\n\n¿Continuar con las válidas?"):
                return

        self.corriendo = True
        self.btn_organizar.configure(state="disabled", text="⏳  Organizando...")
        self.prog_bar["value"] = 0

        preview = self.preview_var.get()
        carpetas = [c for c in self.carpetas if c.exists()]

        def tarea():
            self._log("═" * 52, "head")
            modo = "PREVIEW" if preview else "ORGANIZACIÓN"
            self._log(f"  🚀  Iniciando {modo}", "head")
            self._log("═" * 52, "head")

            total_stats = defaultdict(int)
            for carpeta in carpetas:
                self._log(f"\n📂  {carpeta}", "head")
                stats = organizar(carpeta, preview, self._log, self._set_prog)
                for k, v in stats.items():
                    total_stats[k] += v

            self._log("\n" + "═" * 52, "head")
            self._log("  ✅  COMPLETADO", "head")
            for cat, n in sorted(total_stats.items()):
                if cat == "_duplicados":
                    self._log(f"     🗑️  Duplicados movidos:  {n}", "warn")
                else:
                    self._log(f"     {cat:<32}  {n}", "ok")
            self._log("═" * 52, "head")

            self.after(0, self._finalizar)

        threading.Thread(target=tarea, daemon=True).start()

    def _finalizar(self):
        self.corriendo = False
        self.btn_organizar.configure(state="normal", text="🚀  Organizar ahora")
        self.prog_bar["value"] = 100
        messagebox.showinfo("¡Listo!", "Organización completada. Revisa el registro.")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()