#!/usr/bin/env python3
"""CachyOS Uygulama Yöneticisi — yüklü paketleri listeler, arar ve kaldırır."""

import configparser
import os
import subprocess
import sys
from dataclasses import dataclass, field

from PyQt6.QtCore import (QAbstractTableModel, QModelIndex, QProcess,
                          QSortFilterProxyModel, Qt, QThread, pyqtSignal)
from PyQt6.QtGui import QAction, QFont, QGuiApplication, QIcon, QKeySequence
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                             QDialog, QDialogButtonBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter,
                             QTableView, QVBoxLayout, QWidget)

APP_NAME = "CachyOS Uygulama Yöneticisi"
LOCAL_DB = "/var/lib/pacman/local"
ENV_C = {**os.environ, "LC_ALL": "C"}

ARCH_REPOS = {"core", "extra", "multilib", "core-testing", "extra-testing", "multilib-testing"}

# Kaldırılması sistemi bozabilecek paketler — ek uyarı gösterilir.
CRITICAL = {
    "base", "base-devel", "glibc", "linux-firmware", "systemd", "pacman", "sudo",
    "bash", "coreutils", "filesystem", "grub", "limine", "refind", "systemd-boot-manager",
    "mesa", "networkmanager", "plasma-desktop", "plasma-workspace", "sddm", "kwin",
    "cachyos-settings", "cachyos-keyring", "cachyos-mirrorlist", "archlinux-keyring",
    "mkinitcpio", "dracut", "xorg-server", "wayland", "dbus", "polkit",
}

CATEGORIES = [
    ("all", "Tümü", "view-list-details"),
    ("apps", "Masaüstü Uygulamaları", "applications-all"),
    ("cachyos", "CachyOS Deposu", "cachyos"),
    ("arch", "Arch Deposu (core/extra)", "archlinux"),
    ("aur", "AUR / Harici", "package-x-generic"),
    ("other", "Diğer Depolar", "folder-remote"),
]


@dataclass
class Package:
    name: str
    version: str
    size: int
    desc: str
    repo: str            # pacman deposu veya "AUR"
    group: str           # cachyos / arch / aur / other
    explicit: bool
    app_name: str = ""   # .desktop dosyasındaki görünen ad
    icon: str = ""
    desktop_files: list = field(default_factory=list)


def human_size(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV_C).stdout


def parse_desktop(path):
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    try:
        cp.read(path, encoding="utf-8")
        e = cp["Desktop Entry"]
    except Exception:
        return None
    if e.get("NoDisplay", "false").lower() == "true" or e.get("Hidden", "false").lower() == "true":
        return None
    if e.get("Type", "Application") != "Application":
        return None
    return e.get("Name[tr]") or e.get("Name", ""), e.get("Icon", "")


def load_packages():
    # Hangi paket hangi depodan: kurulu sürümle eşleşen ilk depo kazanır.
    repo_of, fallback = {}, {}
    for line in run(["pacman", "-Sl"]).splitlines():
        parts = line.split(" ", 3)
        if len(parts) < 4:
            continue
        repo, name, _ver, mark = parts
        if mark == "[installed]":
            repo_of.setdefault(name, repo)
        elif mark.startswith("[installed:"):
            fallback.setdefault(name, repo)

    foreign = set(run(["pacman", "-Qqm"]).split())
    explicit = set(run(["pacman", "-Qqe"]).split())

    # Masaüstü uygulamaları: pacman yerel veritabanındaki dosya listeleri
    desktop = {}
    try:
        entries = os.listdir(LOCAL_DB)
    except OSError:
        entries = []
    for d in entries:
        files_path = os.path.join(LOCAL_DB, d, "files")
        if not os.path.isfile(files_path):
            continue
        name = d.rsplit("-", 2)[0]
        try:
            with open(files_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("usr/share/applications/") and line.endswith(".desktop"):
                        desktop.setdefault(name, []).append("/" + line)
        except OSError:
            pass

    pkgs = []
    for line in run(["expac", "-Q", "%n\t%v\t%m\t%d"]).splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        name, ver, size, desc = parts
        if name in foreign or (name not in repo_of and name not in fallback):
            repo, group = "AUR", "aur"
        else:
            repo = repo_of.get(name) or fallback[name]
            if repo.startswith("cachyos"):
                group = "cachyos"
            elif repo in ARCH_REPOS:
                group = "arch"
            else:
                group = "other"
        p = Package(name, ver, int(size or 0), desc, repo, group, name in explicit)
        for path in desktop.get(name, []):
            info = parse_desktop(path)
            if info:
                p.desktop_files.append(path)
                if not p.app_name:
                    p.app_name, p.icon = info
        pkgs.append(p)
    pkgs.sort(key=lambda p: (p.app_name or p.name).lower())
    return pkgs


class Loader(QThread):
    loaded = pyqtSignal(list)

    def run(self):
        self.loaded.emit(load_packages())


class PackageModel(QAbstractTableModel):
    HEADERS = ["Uygulama", "Paket", "Sürüm", "Kaynak", "Boyut", "Açıklama"]

    def __init__(self):
        super().__init__()
        self.pkgs: list[Package] = []
        self._icons = {}

    def set_packages(self, pkgs):
        self.beginResetModel()
        self.pkgs = pkgs
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.pkgs)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]

    def icon_for(self, p: Package):
        key = p.icon or ("__app" if p.app_name else "__pkg")
        if key not in self._icons:
            if p.icon and os.path.isabs(p.icon):
                ic = QIcon(p.icon)
            elif p.icon:
                ic = QIcon.fromTheme(p.icon)
            else:
                ic = QIcon()
            if ic.isNull():
                ic = QIcon.fromTheme("application-x-executable" if p.app_name else "package-x-generic")
            self._icons[key] = ic
        return self._icons[key]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        p = self.pkgs[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return [p.app_name or p.name, p.name, p.version, p.repo,
                    human_size(p.size), p.desc][col]
        if role == Qt.ItemDataRole.UserRole:  # sıralama anahtarı
            return [(p.app_name or p.name).lower(), p.name, p.version, p.repo,
                    p.size, p.desc.lower()][col]
        if role == Qt.ItemDataRole.DecorationRole and col == 0:
            return self.icon_for(p)
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{p.name} {p.version}\n{p.desc}\nKaynak: {p.repo}" + \
                ("" if p.explicit else "\n(bağımlılık olarak yüklendi)")
        if role == Qt.ItemDataRole.ForegroundRole and col == 3 and p.group == "aur":
            return QGuiApplication.palette().link()
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 4:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


class PackageFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.category = "apps"
        self.text = ""
        self.show_deps = False
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def matches(self, p: Package, category=None):
        cat = category or self.category
        if not self.show_deps and not p.explicit and cat != "apps":
            return False
        if cat == "apps" and not p.app_name:
            return False
        if cat not in ("all", "apps") and p.group != cat:
            return False
        if self.text:
            hay = f"{p.name} {p.app_name} {p.desc}".lower()
            return all(w in hay for w in self.text.split())
        return True

    def filterAcceptsRow(self, row, parent):
        return self.matches(self.sourceModel().pkgs[row])


class OutputDialog(QDialog):
    """pkexec pacman komutunu çalıştırır ve çıktısını canlı gösterir."""

    def __init__(self, parent, title, args):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 420)
        self.succeeded = False
        lay = QVBoxLayout(self)
        self.status = QLabel("Yetki isteniyor… (parolanızı girin)")
        lay.addWidget(self.status)
        self.out = QPlainTextEdit(readOnly=True)
        self.out.setFont(QFont("monospace"))
        lay.addWidget(self.out)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        self.buttons.setEnabled(False)
        lay.addWidget(self.buttons)

        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.on_output)
        self.proc.finished.connect(self.on_finished)
        self.out.appendPlainText("$ " + " ".join(args) + "\n")
        self.proc.start(args[0], args[1:])

    def on_output(self):
        self.status.setText("Çalışıyor…")
        text = bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        self.out.moveCursor(self.out.textCursor().MoveOperation.End)
        self.out.insertPlainText(text)
        self.out.ensureCursorVisible()

    def on_finished(self, code, _status):
        self.buttons.setEnabled(True)
        if code == 0:
            self.succeeded = True
            self.status.setText("✔ İşlem başarıyla tamamlandı.")
        elif code in (126, 127):
            self.status.setText("✖ Yetkilendirme iptal edildi veya reddedildi.")
        else:
            self.status.setText(f"✖ İşlem başarısız oldu (çıkış kodu {code}).")

    def reject(self):
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            return  # pacman çalışırken pencere kapatılmasın
        super().reject()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon.fromTheme("system-software-install"))
        self.resize(1200, 720)

        self.model = PackageModel()
        self.proxy = PackageFilter()
        self.proxy.setSourceModel(self.model)

        # Sol: kategoriler
        self.cats = QListWidget()
        self.cats.setMaximumWidth(260)
        self.cats.setIconSize(self.cats.iconSize() * 1.4)
        for key, label, icon in CATEGORIES:
            it = QListWidgetItem(QIcon.fromTheme(icon, QIcon.fromTheme("folder")), label)
            it.setData(Qt.ItemDataRole.UserRole, key)
            self.cats.addItem(it)
        self.cats.setCurrentRow(1)
        self.cats.currentItemChanged.connect(self.on_category)

        self.deps_cb = QCheckBox("Bağımlılık olarak\nyüklenenleri de göster")
        self.deps_cb.toggled.connect(self.on_deps)

        orphan_btn = QPushButton(QIcon.fromTheme("edit-clear-all"), "Gereksiz bağımlılıkları\ntemizle")
        orphan_btn.clicked.connect(self.remove_orphans)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(self.cats)
        ll.addWidget(self.deps_cb)
        ll.addWidget(orphan_btn)

        # Sağ: arama + tablo + butonlar
        self.search = QLineEdit()
        self.search.setPlaceholderText("Uygulama ara…  (Ctrl+F)")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(QIcon.fromTheme("edit-find"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self.on_search)
        self.search.returnPressed.connect(lambda: self.table.setFocus())

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setIconSize(self.table.iconSize().expandedTo(self.table.iconSize() * 1.5))
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        for col, w in enumerate((240, 200, 130, 110, 90)):
            self.table.setColumnWidth(col, w)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.table.doubleClicked.connect(lambda _: self.show_info())
        self.table.selectionModel().selectionChanged.connect(self.update_buttons)

        self.info_btn = QPushButton(QIcon.fromTheme("help-about"), "Bilgi")
        self.info_btn.clicked.connect(self.show_info)
        self.remove_btn = QPushButton(QIcon.fromTheme("edit-delete"), "Seçilenleri Kaldır")
        self.remove_btn.setStyleSheet("QPushButton:enabled { font-weight: bold; }")
        self.remove_btn.clicked.connect(self.remove_selected)
        refresh_btn = QPushButton(QIcon.fromTheme("view-refresh"), "Yenile")
        refresh_btn.clicked.connect(self.reload)

        btns = QHBoxLayout()
        self.sel_label = QLabel()
        btns.addWidget(self.sel_label)
        btns.addStretch()
        btns.addWidget(refresh_btn)
        btns.addWidget(self.info_btn)
        btns.addWidget(self.remove_btn)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.search)
        rl.addWidget(self.table)
        rl.addLayout(btns)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([230, 970])
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.addWidget(split)
        self.setCentralWidget(central)

        find = QAction(self, shortcut=QKeySequence.StandardKey.Find)
        find.triggered.connect(lambda: (self.search.setFocus(), self.search.selectAll()))
        delete = QAction(self, shortcut=QKeySequence.StandardKey.Delete)
        delete.triggered.connect(self.remove_selected)
        refresh = QAction(self, shortcut=QKeySequence.StandardKey.Refresh)
        refresh.triggered.connect(self.reload)
        self.addActions([find, delete, refresh])

        self.update_buttons()
        self.reload()
        self.search.setFocus()

    # ---- veri ----
    def reload(self):
        self.statusBar().showMessage("Paketler yükleniyor…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.loader = Loader()
        self.loader.loaded.connect(self.on_loaded)
        self.loader.start()

    def on_loaded(self, pkgs):
        QApplication.restoreOverrideCursor()
        self.model.set_packages(pkgs)
        self.proxy.sort(self.proxy.sortColumn(), self.proxy.sortOrder())
        self.update_counts()

    def update_counts(self):
        pkgs = self.model.pkgs
        for i in range(self.cats.count()):
            it = self.cats.item(i)
            key = it.data(Qt.ItemDataRole.UserRole)
            n = sum(1 for p in pkgs if self.proxy.matches(p, key))
            label = next(l for k, l, _ in CATEGORIES if k == key)
            it.setText(f"{label}  ({n})")
            if key == "other":
                it.setHidden(not any(p.group == "other" for p in pkgs))
        shown = self.proxy.rowCount()
        total = sum(self.model.pkgs[self.proxy.mapToSource(self.proxy.index(r, 0)).row()].size
                    for r in range(shown))
        self.statusBar().showMessage(
            f"{shown} öğe gösteriliyor · toplam {human_size(total)} · sistemde {len(pkgs)} paket yüklü")

    def on_category(self, item, _prev):
        if item:
            self.proxy.category = item.data(Qt.ItemDataRole.UserRole)
            self.proxy.invalidateFilter()
            self.update_counts()

    def on_search(self, text):
        self.proxy.text = text.lower().strip()
        self.proxy.invalidateFilter()
        self.update_counts()

    def on_deps(self, on):
        self.proxy.show_deps = on
        self.proxy.invalidateFilter()
        self.update_counts()

    def selected(self):
        rows = {self.proxy.mapToSource(i).row() for i in self.table.selectionModel().selectedRows()}
        return [self.model.pkgs[r] for r in sorted(rows)]

    def update_buttons(self):
        sel = self.selected()
        self.remove_btn.setEnabled(bool(sel))
        self.info_btn.setEnabled(len(sel) == 1)
        self.sel_label.setText(f"{len(sel)} seçili · {human_size(sum(p.size for p in sel))}" if sel else "")

    # ---- eylemler ----
    def context_menu(self, pos):
        if not self.selected():
            return
        m = QMenu(self)
        m.addAction(QIcon.fromTheme("help-about"), "Paket bilgisi", self.show_info)
        m.addAction(QIcon.fromTheme("edit-copy"), "Paket adını kopyala",
                    lambda: QGuiApplication.clipboard().setText(" ".join(p.name for p in self.selected())))
        m.addSeparator()
        m.addAction(QIcon.fromTheme("edit-delete"), "Kaldır", self.remove_selected)
        m.exec(self.table.viewport().mapToGlobal(pos))

    def show_info(self):
        sel = self.selected()
        if len(sel) != 1:
            return
        text = run(["pacman", "-Qi", sel[0].name])
        if sel[0].desktop_files:
            text += "\nMasaüstü dosyaları:\n  " + "\n  ".join(sel[0].desktop_files)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Bilgi — {sel[0].name}")
        dlg.resize(700, 520)
        lay = QVBoxLayout(dlg)
        out = QPlainTextEdit(text, readOnly=True)
        out.setFont(QFont("monospace"))
        lay.addWidget(out)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def remove_selected(self):
        sel = self.selected()
        if not sel:
            return
        names = [p.name for p in sel]

        # Kuru çalıştırma: neler kaldırılacak, bağımlılık kırılıyor mu?
        r = subprocess.run(["pacman", "-Rs", "-p", "--print-format", "%n\t%v"] + names,
                           capture_output=True, text=True, env=ENV_C)
        if r.returncode != 0:
            blockers = [l.replace(":: removing ", "").strip() for l in r.stderr.splitlines()
                        if "breaks dependency" in l]
            msg = "Bu paket(ler) kaldırılamıyor çünkü başka paketler onlara ihtiyaç duyuyor:\n\n"
            msg += "\n".join("• " + b.replace(" breaks dependency ", " → gerekli: ")
                             .replace(" required by ", ", kullanan: ") for b in blockers[:15])
            if len(blockers) > 15:
                msg += f"\n… ve {len(blockers) - 15} tane daha"
            if not blockers:
                msg = r.stderr.strip()
            QMessageBox.warning(self, "Kaldırılamıyor", msg +
                                "\n\nİpucu: Önce onu kullanan paketleri kaldırın.")
            return

        to_remove = [l.split("\t") for l in r.stdout.splitlines() if "\t" in l]
        sizes = {p.name: p.size for p in self.model.pkgs}
        total = sum(sizes.get(n, 0) for n, _ in to_remove)
        extra = [n for n, _ in to_remove if n not in names]

        dlg = QDialog(self)
        dlg.setWindowTitle("Kaldırmayı onayla")
        dlg.resize(520, 440)
        lay = QVBoxLayout(dlg)
        crit = [n for n in names if n in CRITICAL or n.startswith("linux")]
        if crit:
            w = QLabel(f"⚠ <b>DİKKAT:</b> {', '.join(crit)} sistem için kritik olabilir! "
                       "Kaldırmak sistemin açılmamasına yol açabilir.")
            w.setWordWrap(True)
            w.setStyleSheet("color: #e5534b;")
            lay.addWidget(w)
        lay.addWidget(QLabel(f"<b>{len(to_remove)}</b> paket kaldırılacak, "
                             f"<b>{human_size(total)}</b> alan boşalacak:"))
        lst = QPlainTextEdit(readOnly=True)
        lst.setFont(QFont("monospace"))
        lst.setPlainText("\n".join(f"{n} {v}" + ("   (artık gereksiz bağımlılık)" if n in extra else "")
                                   for n, v in to_remove))
        lay.addWidget(lst)
        nosave = QCheckBox("Sistem yapılandırma dosyalarını da sil (.pacsave bırakma)")
        nosave.setChecked(True)
        lay.addWidget(nosave)
        bb = QDialogButtonBox()
        ok = bb.addButton("Kaldır", QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setIcon(QIcon.fromTheme("edit-delete"))
        bb.addButton("İptal", QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        flags = "-Rns" if nosave.isChecked() else "-Rs"
        self.run_root("Kaldırılıyor", ["pkexec", "pacman", flags, "--noconfirm"] + names)

    def remove_orphans(self):
        orphans = run(["pacman", "-Qqdt"]).split()
        if not orphans:
            QMessageBox.information(self, "Temiz", "Gereksiz (yetim) bağımlılık bulunamadı. 👍")
            return
        sizes = {p.name: p.size for p in self.model.pkgs}
        total = sum(sizes.get(n, 0) for n in orphans)
        box = QMessageBox(QMessageBox.Icon.Question, "Gereksiz bağımlılıklar",
                          f"Hiçbir paketin artık ihtiyaç duymadığı {len(orphans)} paket bulundu "
                          f"({human_size(total)}). Kaldırılsın mı?", parent=self)
        box.setDetailedText("\n".join(orphans))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.run_root("Gereksiz bağımlılıklar kaldırılıyor",
                          ["pkexec", "pacman", "-Rns", "--noconfirm"] + orphans)

    def run_root(self, title, args):
        dlg = OutputDialog(self, title, args)
        dlg.exec()
        if dlg.succeeded:
            self.table.clearSelection()
            self.reload()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName("cachyos-app-manager")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
