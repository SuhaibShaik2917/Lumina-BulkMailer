import tkinter as tk
from tkinter import filedialog, messagebox
import smtplib
import os
import re
import json
import time
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
from email.utils import formatdate, make_msgid

EMAIL_RE        = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
HEADER_INJECT   = re.compile(r"[\r\n]")
MAX_RECIPIENTS  = 500
MAX_SUBJECT     = 200
MAX_BODY        = 100_000
MAX_ATTACH_MB   = 20
SEND_DELAY_S    = 10
SMTP_TIMEOUT    = 30
SAFE_FILENAME   = re.compile(r"[^A-Za-z0-9._\-]")


class LuminaMailer:
    def __init__(self, root):
        self.root = root
        self.root.title("LUMINA")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)

        self.colors = {
            "bg":         "#0B1020",
            "surface":    "#141B2D",
            "surface_hi": "#1B2337",
            "border":     "#28324A",
            "border_hi":  "#3A4763",
            "accent":     "#00E5FF",
            "accent_dim": "#0891B2",
            "text":       "#EAF0FA",
            "text_muted": "#8A96AC",
            "success":    "#4ADE80",
            "error":      "#F87171",
            "field_bg":   "#0F1524",
        }
        self.root.configure(bg=self.colors["bg"])

        self.resume_path  = None
        self.resume_bytes = None
        self.resume_name  = None
        self._sending     = False

        self._setup_logging()
        self._build_ui()
        self._load_config()

    def _setup_logging(self):
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lumina.log")
        logging.basicConfig(
            filename=log_path, level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )

    def _font(self, size=10, weight="normal"):
        return ("Segoe UI", size, weight)

    def _card(self, parent, title=None, padding=(22, 20)):
        card = tk.Frame(
            parent,
            bg=self.colors["surface"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0,
        )
        if title:
            tk.Label(
                card,
                text=title.upper(),
                font=self._font(9, "bold"),
                fg=self.colors["accent"],
                bg=self.colors["surface"],
            ).pack(anchor="w", padx=padding[0], pady=(padding[1], 0))

        inner = tk.Frame(card, bg=self.colors["surface"])
        inner.pack(
            fill="both",
            expand=True,
            padx=padding[0],
            pady=(12 if title else padding[1], padding[1]),
        )
        return card, inner

    def _label(self, parent, text):
        return tk.Label(
            parent, text=text,
            font=self._font(9),
            fg=self.colors["text_muted"],
            bg=self.colors["surface"],
        )

    def _entry(self, parent, show=None):
        e = tk.Entry(
            parent,
            bg=self.colors["field_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            font=self._font(11),
        )
        if show:
            e.config(show=show)
        return e

    def _text(self, parent, height=8):
        return tk.Text(
            parent,
            height=height,
            bg=self.colors["field_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            font=self._font(11),
            padx=10, pady=8,
            wrap="word",
        )

    def _button(self, parent, text, command, primary=False):
        bg = self.colors["accent"] if primary else self.colors["surface_hi"]
        fg = self.colors["bg"]      if primary else self.colors["text"]
        hover = self.colors["accent_dim"] if primary else self.colors["border_hi"]

        btn = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
            font=self._font(11, "bold" if primary else "normal"),
            relief="flat", bd=0, cursor="hand2",
            highlightthickness=0, padx=18, pady=12,
        )
        btn.bind("<Enter>", lambda _e: btn.config(bg=hover))
        btn.bind("<Leave>", lambda _e: btn.config(bg=bg))
        return btn

    def _build_ui(self):
        root_wrap = tk.Frame(self.root, bg=self.colors["bg"], padx=32, pady=26)
        root_wrap.pack(fill="both", expand=True)

        header = tk.Frame(root_wrap, bg=self.colors["bg"])
        header.pack(fill="x", pady=(0, 22))

        tk.Label(
            header, text="LUMINA",
            font=self._font(26, "bold"),
            fg=self.colors["text"], bg=self.colors["bg"],
        ).pack(side="left")

        tk.Label(
            header, text="  •  Bulk Email Dispatcher",
            font=self._font(11),
            fg=self.colors["text_muted"], bg=self.colors["bg"],
        ).pack(side="left", pady=(8, 0))

        split = tk.Frame(root_wrap, bg=self.colors["bg"])
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=1, uniform="split")
        split.columnconfigure(1, weight=1, uniform="split")
        split.rowconfigure(0, weight=1)

        left  = tk.Frame(split, bg=self.colors["bg"])
        right = tk.Frame(split, bg=self.colors["bg"])
        left.grid (row=0, column=0, sticky="nsew", padx=(0, 12))
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        auth_card, auth = self._card(left, "Authentication")
        auth_card.pack(fill="x", pady=(0, 14))

        auth.columnconfigure(1, weight=1)
        self._label(auth, "Email").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        self.ent_email = self._entry(auth)
        self.ent_email.grid(row=0, column=1, sticky="ew", pady=6, ipady=6)

        self._label(auth, "App Password").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        self.ent_pass = self._entry(auth, show="•")
        self.ent_pass.grid(row=1, column=1, sticky="ew", pady=6, ipady=6)

        asset_card, asset = self._card(left, "Attachment")
        asset_card.pack(fill="x", pady=14)

        self.btn_file = self._button(asset, "📎  Select Resume PDF", self.select_file)
        self.btn_file.pack(anchor="w")

        self.lbl_file = tk.Label(
            asset, text="No file selected",
            font=self._font(9),
            fg=self.colors["text_muted"], bg=self.colors["surface"],
        )
        self.lbl_file.pack(anchor="w", pady=(10, 0))

        status_card, status = self._card(left, "Live Status")
        status_card.pack(fill="x", pady=14)

        self.lbl_status = tk.Label(
            status, text="System Ready",
            font=self._font(12),
            fg=self.colors["text"], bg=self.colors["surface"],
        )
        self.lbl_status.pack(anchor="w")

        self.lbl_counter = tk.Label(
            status, text="SENT: 0   ·   REMAINING: 0   ·   TOTAL: 0",
            font=("Consolas", 12, "bold"),
            fg=self.colors["accent"], bg=self.colors["surface"],
        )
        self.lbl_counter.pack(anchor="w", pady=(8, 0))

        self.btn_send = self._button(
            left, "🚀  LAUNCH CAMPAIGN",
            self.start_sending_thread, primary=True,
        )
        self.btn_send.pack(fill="x", pady=(18, 0))

        comp_card, comp = self._card(right, "Message Composition")
        comp_card.pack(fill="both", expand=True)

        self._label(comp, "Subject").pack(anchor="w")
        self.ent_subject = self._entry(comp)
        self.ent_subject.pack(fill="x", pady=(4, 16), ipady=7)

        self._label(comp, "Body").pack(anchor="w")
        self.txt_body = self._text(comp, height=12)
        self.txt_body.pack(fill="both", expand=True, pady=(4, 16))

        self._label(comp, "Recipients  (one per line)").pack(anchor="w")
        self.txt_targets = self._text(comp, height=9)
        self.txt_targets.pack(fill="both", expand=True, pady=(4, 0))

    def _load_config(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.ent_email.insert(0, str(cfg.get("auth_email", ""))[:254])
            self.ent_pass.insert(0, str(cfg.get("auth_pass", ""))[:128])
        except Exception as e:
            logging.warning("Config load failed: %s", e)

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Select Resume PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            messagebox.showerror("Invalid file", "Only PDF files are allowed.")
            return
        try:
            size = os.path.getsize(path)
        except OSError as e:
            messagebox.showerror("File error", str(e))
            return
        if size > MAX_ATTACH_MB * 1024 * 1024:
            messagebox.showerror("Too large", f"PDF exceeds {MAX_ATTACH_MB} MB.")
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as e:
            messagebox.showerror("File error", str(e))
            return

        self.resume_path  = path
        self.resume_bytes = data
        self.resume_name  = SAFE_FILENAME.sub("_", os.path.basename(path)) or "resume.pdf"
        self.lbl_file.config(text=self.resume_name, fg=self.colors["accent"])

    def _validate(self, email, pw, subject, body, targets):
        errs = []
        if not EMAIL_RE.match(email):
            errs.append("• Sender email address is invalid.")
        if len(pw) < 8:
            errs.append("• App password must be at least 8 characters.")
        if HEADER_INJECT.search(subject):
            errs.append("• Subject must not contain line breaks.")
        if len(subject) > MAX_SUBJECT:
            errs.append(f"• Subject exceeds {MAX_SUBJECT} characters.")
        if len(body) > MAX_BODY:
            errs.append(f"• Body exceeds {MAX_BODY:,} characters.")
        if len(targets) > MAX_RECIPIENTS:
            errs.append(f"• Too many recipients (max {MAX_RECIPIENTS}).")
        bad = [t for t in targets
               if not EMAIL_RE.match(t) or "," in t or ";" in t]
        if bad:
            shown = ", ".join(bad[:3]) + ("…" if len(bad) > 3 else "")
            errs.append(f"• {len(bad)} invalid recipient(s): {shown}")
        return errs

    def start_sending_thread(self):
        if self._sending:
            return

        email   = self.ent_email.get().strip()[:254]
        pw      = self.ent_pass.get().strip()[:128]
        subject = self.ent_subject.get().strip()
        body    = self.txt_body.get("1.0", tk.END).strip()
        raw     = self.txt_targets.get("1.0", tk.END).strip()

        if not all([email, pw, subject, body, raw]):
            messagebox.showerror("Missing input", "All fields are required.")
            return

        targets = [t.strip() for t in raw.splitlines() if t.strip()]

        errs = self._validate(email, pw, subject, body, targets)
        if errs:
            messagebox.showerror("Validation failed", "\n".join(errs))
            return

        self._sending = True
        self.btn_send.config(state="disabled", text="TRANSMITTING…",
                             bg=self.colors["text_muted"], disabledforeground=self.colors["bg"])
        threading.Thread(
            target=self._run_campaign,
            args=(email, pw, subject, body, targets),
            daemon=True,
        ).start()

    def _run_campaign(self, email, pw, subject, body, targets):
        total  = len(targets)
        sent   = 0
        failed = []

        server = None
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=SMTP_TIMEOUT)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(email, pw)
        except smtplib.SMTPAuthenticationError:
            self._ui(lambda: messagebox.showerror(
                "Auth error", "Authentication failed. Check Gmail address & App Password."))
            self._ui(self._reset_ui)
            return
        except Exception as e:
            logging.exception("SMTP connect failed")
            self._ui(lambda e=e: messagebox.showerror("Connection error", str(e)))
            self._ui(self._reset_ui)
            return

        try:
            for i, target in enumerate(targets):
                remaining = total - i
                self._ui(lambda t=target, s=sent, r=remaining, n=total:
                         self._update_status(t, s, r, n))

                try:
                    msg = MIMEMultipart()
                    msg["Subject"]    = Header(subject, "utf-8")
                    msg["From"]       = email
                    msg["To"]         = target
                    msg["Date"]       = formatdate(localtime=True)
                    msg["Message-ID"] = make_msgid()
                    msg.attach(MIMEText(body, "plain", "utf-8"))

                    if self.resume_bytes:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(self.resume_bytes)
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition",
                                        "attachment", filename=self.resume_name)
                        msg.attach(part)

                    server.send_message(msg)
                    sent += 1
                except Exception as e:
                    failed.append(target)
                    logging.error("Send failed → %s : %s", target, e)

                self._ui(lambda s=sent, r=total - sent - len(failed), n=total:
                         self._update_counter(s, r, n))

                if i < total - 1:
                    time.sleep(SEND_DELAY_S)
        finally:
            try:
                server.quit()
            except Exception:
                pass
            self._ui(lambda: self._finalize(sent, failed, total))
            self._ui(self._reset_ui)

    def _ui(self, fn):
        self.root.after(0, fn)

    def _update_status(self, target, sent, remaining, total):
        self.lbl_status.config(text=f"Dispatching → {target}", fg=self.colors["text"])
        self._update_counter(sent, remaining, total)

    def _update_counter(self, sent, remaining, total):
        self.lbl_counter.config(
            text=f"SENT: {sent}   ·   REMAINING: {remaining}   ·   TOTAL: {total}"
        )

    def _finalize(self, sent, failed, total):
        ok = (sent == total)
        self.lbl_status.config(
            text="CAMPAIGN COMPLETED" if ok else f"COMPLETED — {len(failed)} FAILED",
            fg=self.colors["success"] if ok else self.colors["error"],
        )
        self.lbl_counter.config(
            text=f"SENT: {sent}   ·   FAILED: {len(failed)}   ·   TOTAL: {total}"
        )
        msg = f"Sent {sent} of {total}."
        if failed:
            msg += f"\n\nFailed ({len(failed)}):\n" + "\n".join(failed[:10])
            if len(failed) > 10:
                msg += f"\n… +{len(failed) - 10} more"
        messagebox.showinfo("Campaign finished", msg)

    def _reset_ui(self):
        self._sending = False
        self.btn_send.config(
            state="normal", text="🚀  LAUNCH CAMPAIGN",
            bg=self.colors["accent"], disabledforeground=self.colors["bg"],
        )


if __name__ == "__main__":
    root = tk.Tk()
    LuminaMailer(root)
    root.mainloop()