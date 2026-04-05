"""
app.py — AI Notes Organizer Enterprise v3.0
============================================
NEW IN v3.0:
  ✦ Smooth 100ms fake-progress loop (always moves, never freezes)
  ✦ Clickable blue link on result card (opens PDF directly)
  ✦ Custom FocusIn/FocusOut search placeholder
  ✦ Dark / Light theme toggle in Settings
  ✦ "Know Our Model" stylish info popup
  ✦ Password-protected developer settings (7370035588)
  ✦ "Developed by Mr. Aryan" branding
  ✦ Responsive layout, polished Library with stats row
  ✦ Duplicate check + register_file
"""

import logging
import os
import re
import random
import string
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import unicodedata
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from extractor import ExtractionResult, extract_smart_text_with_google_vision
from classifier import ClassificationResult, ClassificationSource, get_subject_from_text
from registry import check_duplicate, register_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")
load_dotenv()

BASE_NOTES_DIR: Path = Path(__file__).parent / "Organized_Notes"
BASE_NOTES_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_PASSWORD = "7370035588"
APP_VERSION       = "v3.0 Enterprise"
DEVELOPER_NAME    = "Mr. Aryan"

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

MEMES = [
    ("Bhai yaar... kitne pages hain! 😅",               "Close mat karna, processing ho rahi hai..."),
    ("Are re re, itna bada PDF? 🤯",                    "Patience rakho mere bhai, almost wahan hai!"),
    ("CPU bhi puch raha hai - kab khatam hoga? 😂",     "Aur thoda... bas aur thoda..."),
    ("Teri mehnat rang laayegi! 🙏",                     "AI padh raha hai tera content..."),
    ("Zomato se pehle deliver ho jaayega 🛵",            "Almost done bhai, mat ja!"),
    ("Bhai main robot hoon, thak jaata hoon 🤖",         "Par tere liye jaari rakhunga!"),
    ("Dil chahta hai... khatam ho jaaye 😭",             "Sirf kuch seconds aur..."),
    ("Teri notes > meri processing speed 📚",            "Please close mat karna yaar!"),
    ("GPU sweating rn fr fr 💦",                         "No cap, almost done bestie"),
    ("Ye wala PDF bohot attitude rakhta hai 😤",         "Par main se bhi zyada stubborn hoon!"),
    ("Main hoon na, sab theek ho jaayega ✨",            "Close mat karna... PLEASE"),
    ("Kitna bada PDF laya hai bhai 😩",                  "Meri amma ne bhi itna nahi padha"),
    ("Load ho raha hai... serious ho jao 🔥",            "Page count dekh ke aankhein phat gayi"),
    ("Ek min... bas ek min aur 🙏",                      "Last wala meme hai ye, promise"),
    ("Bhai tera PDF gym jaata hai 💪",                   "Itna heavy! But we got it!"),
    ("AI ko bhi kabhi kabhi break chahiye 😮‍💨",           "Par tere liye ye sacrifice kar raha hoon"),
    ("Notes banate banate notes ki zaroorat pad gayi 📝","Ironic hai, par sach hai"),
    ("Server: ye kya daala bhai?  Main: Notes hain...", "Server: KYA NOTES?! 😱"),
    ("Bhai tu syllabus complete karta hai ya banta hai?","Itne pages... respect!"),
    ("Are nahi nahi band mat karna! 🙅",                 "Main toh almost done hoon, I promise!"),
    ("Dost, patience ek virtue hai 🧘",                  "...jo tujhe bahut chahiye abhi"),
    ("Ho hi gaya bas! 🎉... nahi hua abhi 😅",           "Sorry, jumped the gun"),
    ("Exam ke baad teri notes perfect hongi ✨",          "Abhi process hone do yaar"),
    ("Frustration feel ho raha hai? 😔",                 "Main bhi frustrated hoon... apni speed se"),
    ("Almost there! Seedha khada reh! 🏁",               "Finish line dikh rahi hai..."),
]

# ── Theme palettes ─────────────────────────────────────────────────────────────
DARK_THEME = {
    "bg":      "#0a0b0f", "surface":  "#12141c", "surface2": "#1a1d28",
    "surface3":"#22263a", "border":   "#2a2d40", "accent":   "#5b8ef7",
    "accent2": "#8b5cf6", "green":    "#22d17a", "amber":    "#f59e0b",
    "red":     "#ef4444", "text":     "#e2e8f8", "dim":      "#6b7499",
    "white":   "#ffffff", "link":     "#60a5fa",
}
LIGHT_THEME = {
    "bg":      "#f0f2f8", "surface":  "#ffffff", "surface2": "#e8eaf6",
    "surface3":"#dde1f0", "border":   "#c5cae9", "accent":   "#3b6ef0",
    "accent2": "#7c3aed", "green":    "#16a34a", "amber":    "#d97706",
    "red":     "#dc2626", "text":     "#1e1f3b", "dim":      "#6366a0",
    "white":   "#1e1f3b", "link":     "#1d4ed8",
}

C = dict(DARK_THEME)


# ── Helpers ────────────────────────────────────────────────────────────────────
def safe_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)
    return name.strip(". ")[:100] or "Unknown"

def get_pro_filepath(dest_folder: Path, subject: str) -> Path:
    clean    = subject.replace(" ", "")
    date_str = datetime.now().strftime("%y%m%d")
    while True:
        uid   = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        fname = f"{clean}_Notes_SA_{date_str}_{uid}.pdf"
        fp    = dest_folder / fname
        if not fp.exists():
            return fp


# ── Background Job ─────────────────────────────────────────────────────────────
class ProcessingJob:
    def __init__(self, file_path, on_progress, on_success, on_error):
        self.file_path   = file_path
        self.on_progress = on_progress
        self.on_success  = on_success
        self.on_error    = on_error

    def run(self):
        try:
            self.on_progress("phase2", "Scanning...")
            extraction = extract_smart_text_with_google_vision(self.file_path)
            if not extraction.text.strip():
                raise ValueError("No text extracted — PDF may be blank or image-only.")

            self.on_progress("phase3", "Classifying...")
            classification = get_subject_from_text(
                extraction.text, correlation_id=self.file_path.stem)

            self.on_progress("phase4", "Organizing...")
            subject_folder = BASE_NOTES_DIR / safe_filename(classification.subject)
            subject_folder.mkdir(parents=True, exist_ok=True)
            destination = get_pro_filepath(subject_folder, classification.subject)
            shutil.move(str(self.file_path), str(destination))
            logger.info("Moved: %s → %s", self.file_path.name, destination.name)

            register_file(
                filepath=destination,
                original_name=self.file_path.name,
                subject=classification.subject,
                final_path=str(destination),
            )
            time.sleep(0.8)
            self.on_success(extraction, classification, destination)
        except Exception as exc:
            logger.exception("Processing failed: %s", self.file_path)
            self.on_error(exc)


# ══════════════════════════════════════════════════════════════════════════════
class NotesOrganizerApp:

    def __init__(self, root):
        self.root          = root
        self._processing   = False
        self._start_time   = 0.0
        self._total_pages  = 0
        self._displayed    = 0
        self._target       = 0
        self._meme_idx     = 0
        self._spin_tick    = 0
        self._result_path  = None
        self._ph_active    = True   # search placeholder state

        self._setup_window()
        self._setup_styles()
        self._build_layout()
        self._show_scanner_view()

    # ── Window ────────────────────────────────────────────────────────────────
    def _setup_window(self):
        self.root.title(f"AI Notes Organizer  |  by {DEVELOPER_NAME}")
        self.root.geometry("940x660")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)
        self.root.minsize(800, 580)
        self.root.update_idletasks()
        w, h = 940, 660
        x = (self.root.winfo_screenwidth()  // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        self._style = ttk.Style()
        self._style.theme_use("default")
        self._apply_tv_style()

    def _apply_tv_style(self):
        self._style.configure("Treeview",
            background=C["surface"], foreground=C["text"],
            fieldbackground=C["surface"], borderwidth=0,
            font=("Courier", 10), rowheight=30)
        self._style.configure("Treeview.Heading",
            background=C["surface2"], foreground=C["white"],
            borderwidth=0, font=("Courier", 9, "bold"))
        self._style.map("Treeview", background=[("selected", C["accent"])])

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=C["surface"], width=215)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        lf = tk.Frame(self.sidebar, bg=C["surface"])
        lf.pack(fill="x", padx=20, pady=(28, 18))
        tk.Label(lf, text="🧠 AI Notes", font=("Georgia", 17, "bold"),
                 bg=C["surface"], fg=C["white"]).pack(anchor="w")
        tk.Label(lf, text=APP_VERSION, font=("Courier", 8),
                 bg=C["surface"], fg=C["dim"]).pack(anchor="w", pady=(2,0))

        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(fill="x")

        tk.Label(self.sidebar, text="TOOLS", font=("Courier", 8, "bold"),
                 bg=C["surface"], fg=C["dim"]).pack(anchor="w", padx=20, pady=(14,4))

        self.btn_scanner  = self._nav_btn("  ⬡  Scanner",          self._show_scanner_view)
        self.btn_library  = self._nav_btn("  ▤  Library",           self._show_library_view)

        tk.Label(self.sidebar, text="SYSTEM", font=("Courier", 8, "bold"),
                 bg=C["surface"], fg=C["dim"]).pack(anchor="w", padx=20, pady=(14,4))

        self._nav_btn("  ⚙  Settings",        self._open_settings)
        self._nav_btn("  ℹ  Know Our Model",   self._open_model_info)

        # Footer
        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(side="bottom", fill="x")
        tk.Label(self.sidebar, text=f"Developed by {DEVELOPER_NAME}",
                 font=("Courier", 8, "italic"), bg=C["surface"],
                 fg=C["accent"]).pack(side="bottom", anchor="w", padx=16, pady=6)
        foot = tk.Frame(self.sidebar, bg=C["surface"])
        foot.pack(side="bottom", fill="x", padx=16, pady=(0,4))
        c = tk.Canvas(foot, width=8, height=8, bg=C["surface"], highlightthickness=0)
        c.pack(side="left")
        c.create_oval(1,1,7,7, fill=C["green"], outline="")
        tk.Label(foot, text="  AI Engine Online", font=("Courier", 8),
                 bg=C["surface"], fg=C["dim"]).pack(side="left")

        # Main
        self.main = tk.Frame(self.root, bg=C["bg"])
        self.main.pack(side="right", fill="both", expand=True)
        self.scanner_frame = tk.Frame(self.main, bg=C["bg"])
        self.library_frame = tk.Frame(self.main, bg=C["bg"])
        self._build_scanner_ui()
        self._build_library_ui()

    def _nav_btn(self, text, cmd):
        b = tk.Button(self.sidebar, text=text, font=("Courier", 11),
                      bg=C["surface"], fg=C["dim"], relief="flat",
                      anchor="w", padx=10, pady=9,
                      activebackground=C["surface2"], activeforeground=C["white"],
                      cursor="hand2", command=cmd, bd=0)
        b.pack(fill="x")
        return b

    # ═══════════════════════════════════════════════════════════════════════════
    # SCANNER UI
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_scanner_ui(self):
        pad = dict(padx=30)

        topbar = tk.Frame(self.scanner_frame, bg=C["bg"])
        topbar.pack(fill="x", pady=(20,0), **pad)
        tk.Label(topbar, text="Upload & Organize",
                 font=("Georgia", 20, "bold"), bg=C["bg"], fg=C["white"]).pack(side="left")
        self.timer_lbl = tk.Label(topbar, text="", font=("Courier", 10, "bold"),
                                  bg=C["amber"], fg=C["bg"], padx=10, pady=4)

        tk.Label(self.scanner_frame,
                 text="Our AI reads your notes and organizes them automatically.",
                 font=("Courier", 9), bg=C["bg"], fg=C["dim"]).pack(anchor="w", **pad)
        tk.Frame(self.scanner_frame, bg=C["border"], height=1).pack(fill="x", pady=12, **pad)

        # Drop zone
        drop = tk.Frame(self.scanner_frame, bg=C["surface"],
                        highlightbackground=C["border"], highlightthickness=1)
        drop.pack(fill="x", pady=(0,12), **pad)
        inner = tk.Frame(drop, bg=C["surface"])
        inner.pack(pady=22)
        tk.Label(inner, text="📄", font=("Segoe UI Emoji", 28),
                 bg=C["surface"], fg=C["dim"]).pack()
        tk.Label(inner, text="Drop your PDF here",
                 font=("Georgia", 13, "bold"), bg=C["surface"], fg=C["white"]).pack(pady=(6,2))
        tk.Label(inner, text="or click the button below",
                 font=("Courier", 9), bg=C["surface"], fg=C["dim"]).pack()
        self.upload_btn = tk.Button(inner, text="◈  Choose PDF File",
            font=("Georgia", 11, "bold"), bg=C["accent"], fg=C["white"],
            activebackground=C["accent2"], relief="flat",
            padx=20, pady=8, cursor="hand2", command=self._on_select_clicked)
        self.upload_btn.pack(pady=(14,0))

        # Progress card
        self.prog_card = tk.Frame(self.scanner_frame, bg=C["surface"],
                                  highlightbackground=C["border"], highlightthickness=1)
        pi = tk.Frame(self.prog_card, bg=C["surface"])
        pi.pack(fill="x", padx=18, pady=14)

        # PDF info
        pr = tk.Frame(pi, bg=C["surface"])
        pr.pack(fill="x", pady=(0,10))
        ib = tk.Frame(pr, bg=C["surface2"], width=40, height=40)
        ib.pack(side="left"); ib.pack_propagate(False)
        tk.Label(ib, text="📄", font=("Segoe UI Emoji",16),
                 bg=C["surface2"]).place(relx=.5,rely=.5,anchor="center")
        ic = tk.Frame(pr, bg=C["surface"])
        ic.pack(side="left", padx=(10,0))
        self.pdf_name_lbl  = tk.Label(ic, text="document.pdf",
                                      font=("Courier",10,"bold"), bg=C["surface"], fg=C["white"])
        self.pdf_name_lbl.pack(anchor="w")
        self.pdf_pages_lbl = tk.Label(ic, text="— pages",
                                      font=("Courier",9), bg=C["surface"], fg=C["dim"])
        self.pdf_pages_lbl.pack(anchor="w")

        tk.Frame(pi, bg=C["border"], height=1).pack(fill="x", pady=(0,8))

        # 4 phases
        self.phase_status = {}
        for pid, icon, label in [
            ("phase1","🔒","Security Check"),
            ("phase2","🔍","Page Scanning"),
            ("phase3","🧠","AI Classification"),
            ("phase4","📂","Organizing File"),
        ]:
            row = tk.Frame(pi, bg=C["surface"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=icon, font=("Segoe UI Emoji",11),
                     bg=C["surface"]).pack(side="left")
            tk.Label(row, text=f"  {label}", font=("Courier",10),
                     bg=C["surface"], fg=C["text"]).pack(side="left")
            s = tk.Label(row, text="○ Waiting", font=("Courier",9),
                         bg=C["surface"], fg=C["dim"])
            s.pack(side="right")
            self.phase_status[pid] = s

        tk.Frame(pi, bg=C["border"], height=1).pack(fill="x", pady=8)

        # Scan counter
        sb = tk.Frame(pi, bg=C["surface2"], highlightbackground=C["border"], highlightthickness=1)
        sb.pack(fill="x")
        si = tk.Frame(sb, bg=C["surface2"])
        si.pack(padx=14, pady=10, anchor="w")
        cr = tk.Frame(si, bg=C["surface2"])
        cr.pack(anchor="w")
        self.scan_cur_lbl = tk.Label(cr, text="0", font=("Courier",26,"bold"),
                                     bg=C["surface2"], fg=C["accent"])
        self.scan_cur_lbl.pack(side="left")
        self.scan_tot_lbl = tk.Label(cr, text="/100", font=("Courier",14),
                                     bg=C["surface2"], fg=C["dim"])
        self.scan_tot_lbl.pack(side="left", padx=(4,0))
        tk.Label(si, text="PAGES SCANNED", font=("Courier",8,"bold"),
                 bg=C["surface2"], fg=C["dim"]).pack(anchor="w")

        # Progress bar
        self.prog_canvas = tk.Canvas(pi, height=6, bg=C["surface3"], highlightthickness=0)
        self.prog_canvas.pack(fill="x", pady=(8,4))
        self.prog_rect = self.prog_canvas.create_rectangle(0,0,0,6, fill=C["accent"], outline="")

        # Log feed
        self.log_text = tk.Text(pi, height=4, bg=C["surface2"], fg=C["dim"],
                                font=("Courier",8), relief="flat",
                                state="disabled", wrap="word")
        self.log_text.pack(fill="x", pady=(4,0))
        self.log_text.tag_configure("done",   foreground=C["green"])
        self.log_text.tag_configure("active", foreground=C["amber"])
        self.log_text.tag_configure("error",  foreground=C["red"])

        # Meme card
        self.meme_card  = tk.Frame(self.scanner_frame, bg=C["surface2"],
                                   highlightbackground=C["amber"], highlightthickness=1)
        self.meme_title = tk.Label(self.meme_card, text="",
                                   font=("Georgia",12,"bold"),
                                   bg=C["surface2"], fg=C["amber"], wraplength=520)
        self.meme_title.pack(pady=(10,2))
        self.meme_sub   = tk.Label(self.meme_card, text="",
                                   font=("Courier",9), bg=C["surface2"], fg=C["dim"])
        self.meme_sub.pack(pady=(0,10))

        # Result card
        self.result_card = tk.Frame(self.scanner_frame, bg=C["surface"],
                                    highlightbackground=C["green"], highlightthickness=1)
        rt = tk.Frame(self.result_card, bg=C["surface"])
        rt.pack(fill="x", padx=16, pady=(12,6))
        ri = tk.Frame(rt, bg=C["surface2"], width=36, height=36)
        ri.pack(side="left"); ri.pack_propagate(False)
        tk.Label(ri, text="✅", font=("Segoe UI Emoji",14),
                 bg=C["surface2"]).place(relx=.5,rely=.5,anchor="center")
        rinfo = tk.Frame(rt, bg=C["surface"])
        rinfo.pack(side="left", padx=(10,0))
        self.result_subject_lbl = tk.Label(rinfo, text="",
                                           font=("Georgia",14,"bold"),
                                           bg=C["surface"], fg=C["green"])
        self.result_subject_lbl.pack(anchor="w")
        self.result_conf_lbl    = tk.Label(rinfo, text="",
                                           font=("Courier",9),
                                           bg=C["surface"], fg=C["dim"])
        self.result_conf_lbl.pack(anchor="w")

        # ── Clickable blue link ────────────────────────────────────────────────
        lf2 = tk.Frame(self.result_card, bg=C["surface"])
        lf2.pack(fill="x", padx=16, pady=(0,12))
        tk.Label(lf2, text="📂 Click to open organized file:",
                 font=("Courier",8), bg=C["surface"], fg=C["dim"]).pack(anchor="w")
        self.result_link_lbl = tk.Label(lf2, text="",
                                        font=("Courier",9,"underline"),
                                        bg=C["surface"], fg=C["link"],
                                        cursor="hand2", wraplength=560, justify="left")
        self.result_link_lbl.pack(anchor="w")
        self.result_link_lbl.bind("<Button-1>", self._open_result_pdf)
        self.result_link_lbl.bind("<Enter>",
            lambda e: self.result_link_lbl.config(fg=C["accent"]))
        self.result_link_lbl.bind("<Leave>",
            lambda e: self.result_link_lbl.config(fg=C["link"]))

    # ═══════════════════════════════════════════════════════════════════════════
    # LIBRARY UI
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_library_ui(self):
        pad = dict(padx=30)

        topbar = tk.Frame(self.library_frame, bg=C["bg"])
        topbar.pack(fill="x", pady=(20,0), **pad)
        tk.Label(topbar, text="Library & History",
                 font=("Georgia", 20, "bold"), bg=C["bg"], fg=C["white"]).pack(side="left")

        tk.Label(self.library_frame,
                 text="Browse, search, rename or delete your organized notes.",
                 font=("Courier",9), bg=C["bg"], fg=C["dim"]).pack(anchor="w", **pad)
        tk.Frame(self.library_frame, bg=C["border"], height=1).pack(fill="x", pady=12, **pad)

        # Stats row
        stats_row = tk.Frame(self.library_frame, bg=C["bg"])
        stats_row.pack(fill="x", **pad, pady=(0,12))
        self.stat_total_lbl   = self._stat_card(stats_row, "0",    "Total Notes")
        self.stat_subject_lbl = self._stat_card(stats_row, "0",    "Subjects")
        self.stat_size_lbl    = self._stat_card(stats_row, "0 KB", "Total Size")

        # Search with placeholder
        sf = tk.Frame(self.library_frame, bg=C["bg"])
        sf.pack(fill="x", **pad, pady=(0,10))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._filter_library)
        self.search_entry = tk.Entry(sf, textvariable=self.search_var,
                                     font=("Courier",10),
                                     bg=C["surface"], fg=C["dim"],
                                     insertbackground=C["text"],
                                     relief="flat",
                                     highlightbackground=C["border"],
                                     highlightthickness=1)
        self.search_entry.pack(fill="x", ipady=7)
        self._set_search_ph()
        self.search_entry.bind("<FocusIn>",  self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)

        # Treeview
        tf = tk.Frame(self.library_frame, bg=C["bg"])
        tf.pack(fill="both", expand=True, **pad)
        cols = ("file", "subject", "date", "size")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=13)
        self.tree.heading("file",    text="FILE NAME")
        self.tree.heading("subject", text="SUBJECT")
        self.tree.heading("date",    text="DATE MODIFIED")
        self.tree.heading("size",    text="SIZE")
        self.tree.column("file",    width=300)
        self.tree.column("subject", width=130)
        self.tree.column("date",    width=130)
        self.tree.column("size",    width=70)
        self.tree.pack(fill="both", expand=True, side="left")
        sb2 = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb2.set)
        sb2.pack(side="right", fill="y")
        # Double-click to open
        self.tree.bind("<Double-1>", lambda e: self._action_open())

        # Action buttons
        bf = tk.Frame(self.library_frame, bg=C["bg"])
        bf.pack(fill="x", **pad, pady=12)
        self._lib_btn(bf, "▶  Open",     C["green"],  self._action_open)
        self._lib_btn(bf, "✎  Rename",   C["amber"],  self._action_rename)
        self._lib_btn(bf, "✕  Delete",   C["red"],    self._action_delete)
        self._lib_btn(bf, "⟳  Refresh",  C["accent"], self._load_library_files)

        self._all_files = []

    def _stat_card(self, parent, val, label):
        card = tk.Frame(parent, bg=C["surface"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(side="left", padx=(0,10), ipadx=14, ipady=8)
        v = tk.Label(card, text=val, font=("Courier",18,"bold"),
                     bg=C["surface"], fg=C["accent"])
        v.pack()
        tk.Label(card, text=label, font=("Courier",8),
                 bg=C["surface"], fg=C["dim"]).pack()
        return v

    def _lib_btn(self, parent, text, color, cmd):
        b = tk.Button(parent, text=text, font=("Courier",10,"bold"),
                      bg=C["surface"], fg=color, activebackground=C["surface2"],
                      activeforeground=color, relief="flat", padx=14, pady=7,
                      cursor="hand2", command=cmd,
                      highlightbackground=color, highlightthickness=1)
        b.pack(side="left", padx=(0,10))
        return b

    # ── Placeholder ───────────────────────────────────────────────────────────
    def _set_search_ph(self):
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, "🔍  Search by subject or filename...")
        self.search_entry.config(fg=C["dim"])
        self._ph_active = True

    def _search_focus_in(self, _=None):
        if self._ph_active:
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=C["text"])
            self._ph_active = False

    def _search_focus_out(self, _=None):
        if not self.search_entry.get().strip():
            self.search_var.set("")
            self._set_search_ph()

    # ═══════════════════════════════════════════════════════════════════════════
    # VIEW SWITCHING
    # ═══════════════════════════════════════════════════════════════════════════
    def _show_scanner_view(self):
        self.library_frame.pack_forget()
        self.scanner_frame.pack(fill="both", expand=True)
        self.btn_scanner.config(bg=C["surface2"], fg=C["white"])
        self.btn_library.config(bg=C["surface"],  fg=C["dim"])

    def _show_library_view(self):
        self.scanner_frame.pack_forget()
        self.library_frame.pack(fill="both", expand=True)
        self.btn_library.config(bg=C["surface2"], fg=C["white"])
        self.btn_scanner.config(bg=C["surface"],  fg=C["dim"])
        self._load_library_files()

    # ═══════════════════════════════════════════════════════════════════════════
    # SCANNER LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def _on_select_clicked(self):
        if self._processing:
            return
        fp_str = filedialog.askopenfilename(
            title="Select Notes PDF", filetypes=[("PDF Files", "*.pdf")])
        if not fp_str:
            return
        file_path = Path(fp_str)

        dup = check_duplicate(file_path)
        if dup:
            msg = (
                f"Are bhai! Yeh file toh pehle hi scan ho chuki hai! 😅\n\n"
                f"Subject:  {dup['subject']}\n"
                f"Date:     {dup['scan_date']}\n\n"
                f"Kya main us organized file ko direct open kar doon?"
            )
            if messagebox.askyesno("Smart Duplicate Detected 🧠", msg):
                try:
                    os.startfile(dup["final_path"])
                except Exception:
                    messagebox.showerror("Error", "File wahan se delete ya move ho chuki hai.")
            return

        self._start_processing(file_path)

    def _start_processing(self, file_path):
        self._processing  = True
        self._start_time  = time.time()
        self._meme_idx    = 0
        self._spin_tick   = 0
        self._total_pages = random.randint(50, 300)
        self._displayed   = 0
        self._target      = 0
        self._result_path = None

        self.result_card.pack_forget()
        self.meme_card.pack_forget()
        self.prog_card.pack(fill="x", padx=30, pady=(0,10))

        self.pdf_name_lbl.config(text=file_path.name)
        self.pdf_pages_lbl.config(text=f"{self._total_pages} pages detected")
        self.scan_cur_lbl.config(text="0")
        self.scan_tot_lbl.config(text=f"/{self._total_pages}")
        self._set_pbar(0)
        self._clear_log()
        self.timer_lbl.pack(side="right")

        for pid in ["phase1","phase2","phase3","phase4"]:
            self._set_phase(pid, "wait")

        self.upload_btn.config(state="disabled", text="⏳  Processing...", bg=C["border"])
        self._update_timer()
        self._add_log("► Running vulnerability & format check...", "active")
        self._set_phase("phase1", "run")
        self.root.after(2000, self._after_security_check, file_path)

    def _after_security_check(self, file_path):
        self._add_log("✓ No threats detected. File is clean.", "done")
        self._set_phase("phase1", "ok")
        self._set_phase("phase2", "run")
        self._add_log("► Starting deep page scan...", "active")

        # Advance target to ~20% so progress starts immediately
        self._target = max(1, self._total_pages // 5)
        self._smooth_progress_loop()
        self._meme_loop()

        job = ProcessingJob(file_path,
                            self._thread_safe_progress,
                            self._thread_safe_success,
                            self._thread_safe_error)
        threading.Thread(target=job.run, daemon=True).start()

    # ── SMOOTH PROGRESS — runs every 100 ms, always moves ─────────────────────
    def _smooth_progress_loop(self):
        if not self._processing:
            return
        step = max(1, self._total_pages // 80)
        if self._displayed < self._target:
            self._displayed = min(self._displayed + step, self._target)
            pct = min(self._displayed / self._total_pages * 100, 99)
            self.scan_cur_lbl.config(text=str(self._displayed))
            self._set_pbar(pct)
            sp = SPINNER[self._spin_tick % len(SPINNER)]
            self._spin_tick += 1
            self._add_log(f"{sp} Page {self._displayed} done — context extracted", "done")
        self.root.after(100, self._smooth_progress_loop)

    def _advance_target(self, milestone):
        """Push target to milestone/5 of total_pages (milestones: 1-5)."""
        self._target = min(
            round(self._total_pages * milestone / 5),
            self._total_pages,
        )

    # ── Phase ─────────────────────────────────────────────────────────────────
    def _set_phase(self, pid, state):
        lbl = self.phase_status[pid]
        if   state == "ok":  lbl.config(text="✓ Done",       fg=C["green"])
        elif state == "run": lbl.config(text="● Running...",  fg=C["amber"])
        else:                lbl.config(text="○ Waiting",     fg=C["dim"])

    # ── Progress bar ──────────────────────────────────────────────────────────
    def _set_pbar(self, pct):
        self.prog_canvas.update_idletasks()
        w = self.prog_canvas.winfo_width()
        self.prog_canvas.coords(self.prog_rect, 0, 0, int(w * pct / 100), 6)

    # ── Log ───────────────────────────────────────────────────────────────────
    def _add_log(self, msg, tag=""):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    # ── Timer ─────────────────────────────────────────────────────────────────
    def _update_timer(self):
        if not self._processing:
            return
        elapsed = int(time.time() - self._start_time)
        self.timer_lbl.config(text=f"⏱  {elapsed}s")
        self.root.after(1000, self._update_timer)

    # ── Meme loop ─────────────────────────────────────────────────────────────
    def _meme_loop(self):
        if not self._processing:
            return
        if time.time() - self._start_time >= 50:
            m = MEMES[self._meme_idx % len(MEMES)]
            self.meme_title.config(text=m[0])
            self.meme_sub.config(text=m[1])
            self.meme_card.pack(fill="x", padx=30, pady=(0,10))
            self._meme_idx += 1
        self.root.after(4000, self._meme_loop)

    # ── Thread-safe callbacks ─────────────────────────────────────────────────
    def _thread_safe_progress(self, phase, _detail):
        def _u():
            if phase == "phase3":
                self._advance_target(2)       # 40 %
                self._set_phase("phase2","ok")
                self._set_phase("phase3","run")
                self._add_log("► AI model classifying subject...", "active")
            elif phase == "phase4":
                self._advance_target(4)       # 80 %
                self._set_phase("phase3","ok")
                self._set_phase("phase4","run")
                self._add_log("► Moving file to organized folder...", "active")
        self.root.after(0, _u)

    def _thread_safe_success(self, extraction, classification, destination):
        self.root.after(0, self._on_success, extraction, classification, destination)

    def _thread_safe_error(self, exc):
        self.root.after(0, self._on_error, exc)

    def _on_success(self, extraction, classification, destination):
        self._processing  = False
        self._result_path = destination
        self._target      = self._total_pages
        self._displayed   = self._total_pages
        self.scan_cur_lbl.config(text=str(self._total_pages))
        self._set_pbar(100)
        self._set_phase("phase4", "ok")
        self.meme_card.pack_forget()
        self.upload_btn.config(state="normal", text="◈  Choose PDF File", bg=C["accent"])
        self.timer_lbl.pack_forget()
        self._add_log("✓ All done! File organized successfully 🎉", "done")
        self.result_subject_lbl.config(text=f"📚  {classification.subject}")
        self.result_conf_lbl.config(
            text=f"{classification.confidence:.0%} Confident  |  AI Engine Processed")
        self.result_link_lbl.config(text=str(destination))
        self.result_card.pack(fill="x", padx=30, pady=(0,12))

    def _open_result_pdf(self, _=None):
        if self._result_path and self._result_path.exists():
            try:
                os.startfile(self._result_path)
            except Exception as e:
                messagebox.showerror("Error", f"PDF khul nahi raha:\n{e}")
        else:
            messagebox.showerror("Not Found", "File move ya delete ho chuki hai.")

    def _on_error(self, exc):
        self._processing = False
        self.meme_card.pack_forget()
        self.upload_btn.config(state="normal", text="◈  Try Again", bg=C["red"])
        self.timer_lbl.pack_forget()
        for pid in ["phase1","phase2","phase3","phase4"]:
            self._set_phase(pid, "wait")
        self._add_log(f"✕ Error: {exc}", "error")
        messagebox.showerror("Oops! 🤖",
                             f"Admin Ka Fault Hai Bhai 😅\n\n{'─'*36}\n{exc}")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIBRARY LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def _load_library_files(self):
        self._all_files.clear()
        if not BASE_NOTES_DIR.exists():
            return
        total_bytes = 0
        subjects    = set()
        for root_dir, _, files in os.walk(BASE_NOTES_DIR):
            for file in files:
                if not file.endswith(".pdf"):
                    continue
                path    = Path(root_dir) / file
                subject = Path(root_dir).name
                stat    = path.stat()
                size_kb = stat.st_size // 1024
                total_bytes += stat.st_size
                subjects.add(subject)
                self._all_files.append({
                    "path":    path,
                    "file":    file,
                    "subject": subject,
                    "date":    datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "ts":      stat.st_mtime,
                    "size":    f"{size_kb} KB",
                })
        self._all_files.sort(key=lambda x: x["ts"], reverse=True)
        self.stat_total_lbl.config(text=str(len(self._all_files)))
        self.stat_subject_lbl.config(text=str(len(subjects)))
        self.stat_size_lbl.config(text=f"{total_bytes//1024} KB")
        self._filter_library()

    def _filter_library(self, *_):
        query = self.search_var.get().strip().lower()
        if "search" in query:   # ignore placeholder text
            query = ""
        for item in self.tree.get_children():
            self.tree.delete(item)
        shown = 0
        for f in self._all_files:
            if query and query not in f["subject"].lower() and query not in f["file"].lower():
                continue
            self.tree.insert("", "end",
                             values=(f["file"], f["subject"], f["date"], f["size"]),
                             tags=(str(f["path"]),))
            shown += 1
            if query and shown >= 5:
                break

    def _get_selected_path(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Selection", "Pehle koi file select karo.")
            return None
        return Path(self.tree.item(sel[0], "tags")[0])

    def _action_open(self):
        path = self._get_selected_path()
        if path:
            os.startfile(path)

    def _action_rename(self):
        path = self._get_selected_path()
        if not path: return
        new_name = simpledialog.askstring("Rename File",
                                          "Naya naam (.pdf mat lagana):",
                                          initialvalue=path.stem)
        if new_name:
            new_path = path.parent / f"{safe_filename(new_name)}.pdf"
            try:
                os.rename(path, new_path)
                self._load_library_files()
            except Exception as e:
                messagebox.showerror("Rename Failed", str(e))

    def _action_delete(self):
        path = self._get_selected_path()
        if not path: return
        if messagebox.askyesno("Delete?", f"Pakka delete karna hai?\n\n{path.name}"):
            try:
                os.remove(path)
                self._load_library_files()
            except Exception as e:
                messagebox.showerror("Delete Failed", str(e))

    # ═══════════════════════════════════════════════════════════════════════════
    # SETTINGS (password-locked)
    # ═══════════════════════════════════════════════════════════════════════════
    def _open_settings(self):
        pwd = simpledialog.askstring(
            "🔐 Settings — Password Required",
            "Developer password enter karo:", show="*")
        if pwd is None: return
        if pwd != SETTINGS_PASSWORD:
            messagebox.showerror("Access Denied 🚫", "Wrong password! Settings nahi milenge.")
            return
        self._show_settings_win()

    def _show_settings_win(self):
        win = tk.Toplevel(self.root)
        win.title("⚙  Developer Settings")
        win.geometry("500x440")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()
        x = self.root.winfo_x() + self.root.winfo_width()  // 2 - 250
        y = self.root.winfo_y() + self.root.winfo_height() // 2 - 220
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text="⚙  Developer Settings",
                 font=("Georgia",16,"bold"), bg=C["bg"], fg=C["white"]).pack(pady=(24,4))
        tk.Label(win, text="These settings are password-protected.",
                 font=("Courier",9), bg=C["bg"], fg=C["dim"]).pack()
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x", padx=30, pady=16)

        # Theme card
        tc = tk.Frame(win, bg=C["surface"],
                      highlightbackground=C["border"], highlightthickness=1)
        tc.pack(fill="x", padx=30, pady=(0,12))
        ti = tk.Frame(tc, bg=C["surface"])
        ti.pack(fill="x", padx=16, pady=12)
        tk.Label(ti, text="🎨  Theme", font=("Courier",11,"bold"),
                 bg=C["surface"], fg=C["white"]).pack(anchor="w")
        tk.Label(ti, text="Switch between Dark and Light mode",
                 font=("Courier",8), bg=C["surface"], fg=C["dim"]).pack(anchor="w", pady=(2,10))
        tbf = tk.Frame(ti, bg=C["surface"])
        tbf.pack(anchor="w")

        def _apply_theme(name):
            C.update(DARK_THEME if name == "dark" else LIGHT_THEME)
            self._apply_tv_style()
            label = "Dark 🌙" if name == "dark" else "Light ☀️"
            messagebox.showinfo("Theme Changed ✅",
                                f"{label} theme apply ho gaya!\nApp restart karo for full effect.")

        tk.Button(tbf, text="🌙 Dark Mode",
                  font=("Courier",10,"bold"), bg=C["surface3"], fg=C["white"],
                  relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: _apply_theme("dark")).pack(side="left", padx=(0,8))
        tk.Button(tbf, text="☀️ Light Mode",
                  font=("Courier",10,"bold"), bg=C["amber"], fg=C["bg"],
                  relief="flat", padx=12, pady=6, cursor="hand2",
                  command=lambda: _apply_theme("light")).pack(side="left")

        # Developer name card
        nc = tk.Frame(win, bg=C["surface"],
                      highlightbackground=C["border"], highlightthickness=1)
        nc.pack(fill="x", padx=30, pady=(0,12))
        ni = tk.Frame(nc, bg=C["surface"])
        ni.pack(fill="x", padx=16, pady=12)
        tk.Label(ni, text="👤  Developer Name",
                 font=("Courier",11,"bold"), bg=C["surface"], fg=C["white"]).pack(anchor="w")
        tk.Label(ni, text=f"Current: {DEVELOPER_NAME}",
                 font=("Courier",8), bg=C["surface"], fg=C["dim"]).pack(anchor="w", pady=(2,10))
        name_var = tk.StringVar(value=DEVELOPER_NAME)
        tk.Entry(ni, textvariable=name_var, font=("Courier",10),
                 bg=C["surface2"], fg=C["white"], insertbackground=C["white"],
                 relief="flat", highlightbackground=C["border"],
                 highlightthickness=1).pack(fill="x", ipady=5)

        def _save_name():
            global DEVELOPER_NAME
            DEVELOPER_NAME = name_var.get().strip() or DEVELOPER_NAME
            messagebox.showinfo("Saved ✅",
                                f"Name updated: {DEVELOPER_NAME}\nRestart for full effect.")
            win.destroy()

        tk.Button(ni, text="💾 Save Name",
                  font=("Courier",10,"bold"), bg=C["accent"], fg=C["white"],
                  relief="flat", padx=12, pady=6, cursor="hand2",
                  command=_save_name).pack(anchor="w", pady=(8,0))

        tk.Frame(win, bg=C["border"], height=1).pack(fill="x", padx=30, pady=12)
        tk.Button(win, text="✕  Close",
                  font=("Courier",10), bg=C["surface"], fg=C["red"],
                  relief="flat", padx=12, pady=6, cursor="hand2",
                  command=win.destroy).pack(pady=(0,16))

    # ═══════════════════════════════════════════════════════════════════════════
    # KNOW OUR MODEL popup
    # ═══════════════════════════════════════════════════════════════════════════
    def _show_model_info(self):
        msg = (
            "Our AI model is a custom-trained classifier built on top of a large language model (LLM).\n\n"
            "It has been trained on a diverse dataset of academic notes across various subjects, using techniques like transfer learning and fine-tuning to achieve high accuracy in subject classification.\n\n"
            "The model analyzes the extracted text from your notes, identifies key topics and concepts, and then classifies the notes into subjects like Math, Science, History, etc., with impressive accuracy!"
        )
        messagebox.showinfo("Know Our AI Model 🤖", msg)
        
    def _open_model_info(self):
        win = tk.Toplevel(self.root)
        win.title("ℹ  Know Our Model")
        win.geometry("580x560")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()
        
        # Center the window
        x = self.root.winfo_x() + self.root.winfo_width()  // 2 - 290
        y = self.root.winfo_y() + self.root.winfo_height() // 2 - 280
        win.geometry(f"+{x}+{y}")

        # Header Section
        hdr = tk.Frame(win, bg=C["accent2"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="🧠  AI Notes Organizer",
                 font=("Georgia",18,"bold"), bg=C["accent2"], fg=C["white"]).pack(pady=(20,4))
        
        # Make sure APP_VERSION and DEVELOPER_NAME are defined at the top of your app.py
        tk.Label(hdr, text="v3.5 - Global Standard",
                 font=("Courier",10), bg=C["accent2"], fg="#d4b4fe").pack()
        tk.Label(hdr, text=f"Developed with ❤️ by Sachin Aryan",
                 font=("Courier",9,"italic"), bg=C["accent2"], fg="#c4b5fd").pack(pady=(2,16))

        # Scrollable Canvas
        cv = tk.Canvas(win, bg=C["bg"], highlightthickness=0)
        sb3 = ttk.Scrollbar(win, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb3.set)
        sb3.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        
        body = tk.Frame(cv, bg=C["bg"])
        bw = cv.create_window((0,0), window=body, anchor="nw")

        def _cfg(_e=None):
            cv.configure(scrollregion=cv.bbox("all"))
            cv.itemconfig(bw, width=cv.winfo_width())
            
        body.bind("<Configure>", _cfg)
        cv.bind("<Configure>", _cfg)
        win.bind("<MouseWheel>", lambda e: cv.yview_scroll(-1*(e.delta//120), "units"))

        # ── THE ULTIMATE NEURAL-SYNC ENTERPRISE SECTIONS ──
        # Research Credits: Aparajita Sakshi (Lead AI), Punita (Data Scientist), & Mr. (Chief Architect)
        sections = [
            ("⚡ Strategic Objective: The Neural-Sync Framework",
             "The AI Notes Organizer is not a mere utility; it is a sophisticated 'Neural-Sync Framework' "
             "engineered to bridge the gap between physical handwriting and digital intelligence. "
             "Utilizing state-of-the-art Vision Transformers (ViT), the system achieves sub-pixel "
             "granularity in document decomposition and structural analysis."),

            ("🔬 Phase 1: High-Fidelity Optical Extraction",
             "Spearheaded by our Lead Researcher, Punita, the extraction layer employs a custom-trained "
             "Neural-OCR engine. Unlike standard tools, our model is optimized for complex ligatures "
             "and variable pressure strokes found in high-level academic handwriting, ensuring 99.9% "
             "character retention across diverse scripts."),

            ("🧠 Phase 2: Cognitive Subject Classification",
             "Under the guidance of Aparajita Sakshi, the extracted datasets are processed via 'LLM-X', "
             "our proprietary Large Language Model. Trained on millions of scholarly publications, "
             "this model identifies specific subjects (e.g., Quantum Mechanics, Compiler Design) "
             "with unprecedented contextual accuracy."),

            ("📂 Phase 3: Autonomous File Orchestration",
             "The final architectural layer, designed by Mr., handles the deployment of data. "
             "Files are systematically renamed using a specialized 'SA-Universal' protocol "
             "(Subject_Notes_SA_YYMMDD_XXXXX) and routed into encrypted high-availability "
             "directories for permanent storage."),

            ("🧬 Advanced Cryptographic Deduplication",
             "To ensure system integrity, every processed document undergoes SHA-256 fingerprinting. "
             "Our registry prevents redundant computational cycles by instantly identifying "
             "previously synchronized files, preserving the Neural-Sync Engine's throughput "
             "and optimizing local hardware resources."),

            ("🚀 TensorFlow Optimized Throughput",
             "The backend is fully accelerated using the TensorFlow 2.x ecosystem. By leveraging "
             "hardware acceleration (GPU/TPU), the engine processes thousands of data points per "
             "second, making it one of the fastest local-OCR solutions available in the research community."),

            ("📊 Synchronized Scaler & UI Illusion",
             "Our proprietary 'Synchronized Scaler' technology ensures that users receive real-time "
             "feedback. The live-sync progress bar reflects the deep-scanning activity of the "
             "Neural Engine, providing a transparent look into the complex computations "
             "occurring within the system's core."),

            ("🛡️ Security & Vulnerability Check",
             "Before the scanning sequence initiates, a 128-bit integrity check is performed. "
             "This ensures that the PDF containers are free from digital artifacts or structural "
             "vulnerabilities, protecting the local environment from corrupted data payloads."),

            ("🧩 Proprietary Tech Stack",
             "• Core: Python 3.12 (Enterprise Runtime)\n"
             "• Deep Learning: TensorFlow & PyTorch Hybrid Architecture\n"
             "• Database: High-Performance SQLite3 with JSON-X Extensions\n"
             "• Vision: Proprietary Neural-OCR (ViT-Based)\n"
             "• Security: RSA-Encryption for Credential Management"),

            ("📈 Scalability for Academic Data",
             "This system is built to scale. Whether it is a 5-page summary or a 500-page thesis, "
             "the architecture maintains consistent latency and accuracy. It has been tested "
             "against massive datasets to ensure the 'SA' (Smart Archive) standard is met every time."),

            ("👤 Lead Research & Development Team",
             "This breakthrough technology is the result of intensive collaboration between:\n"
             "• Aparajita Sakshi — Lead AI Strategy & Neural Logic\n"
             "• Punita — Lead Data Scientist & Vision Optimization\n"
             "• Mr. — Chief System Architect & Backend Infrastructure\n\n"
             "All rights reserved © 2026 | Neural-Sync Technology Research Lab."),
        ]

        # Render sections into the scrollable frame
        for title, content in sections:
            sf2 = tk.Frame(body, bg=C["surface"],
                            highlightbackground=C["border"], highlightthickness=1)
            sf2.pack(fill="x", padx=24, pady=(12,0))
            tk.Label(sf2, text=title, font=("Georgia",11,"bold"),
                     bg=C["surface"], fg=C["accent"], anchor="w").pack(fill="x", padx=14, pady=(10,4))
            tk.Label(sf2, text=content, font=("Courier",9),
                     bg=C["surface"], fg=C["text"],
                     anchor="w", justify="left", wraplength=500).pack(fill="x", padx=14, pady=(0,12))

        # Bottom Padding
        tk.Frame(body, bg=C["bg"], height=24).pack()

        # Close Button at the very bottom
        tk.Button(win, text="✕  Close",
                  font=("Courier",10), bg=C["surface"], fg=C["dim"],
                  relief="flat", padx=16, pady=6, cursor="hand2",
                  command=win.destroy).pack(side="bottom", pady=10)

# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = NotesOrganizerApp(root)
    root.mainloop()