#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""CachyOS App Manager — list, search and uninstall installed packages."""

import configparser
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

from PyQt6.QtCore import (QAbstractTableModel, QLibraryInfo, QLocale,
                          QModelIndex, QProcess, QSortFilterProxyModel, Qt,
                          QThread, QTranslator, pyqtSignal)
from PyQt6.QtGui import QAction, QFont, QGuiApplication, QIcon, QKeySequence
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                             QDialog, QDialogButtonBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QSplitter,
                             QTableView, QVBoxLayout, QWidget)

__version__ = "1.1.0"

# ---- Translations -----------------------------------------------------------
# Source strings are English; add a new language by adding a dict here.
TRANSLATIONS = {
    "tr": {
        "CachyOS App Manager": "CachyOS Uygulama Yöneticisi",
        "All": "Tümü",
        "Desktop Applications": "Masaüstü Uygulamaları",
        "CachyOS Repository": "CachyOS Deposu",
        "Arch Repository (core/extra)": "Arch Deposu (core/extra)",
        "AUR / Foreign": "AUR / Harici",
        "Other Repositories": "Diğer Depolar",
        "Application": "Uygulama",
        "Package": "Paket",
        "Version": "Sürüm",
        "Source": "Kaynak",
        "Size": "Boyut",
        "Description": "Açıklama",
        "Source: {repo}": "Kaynak: {repo}",
        "(installed as a dependency)": "(bağımlılık olarak yüklendi)",
        "Requesting authorization… (enter your password)": "Yetki isteniyor… (parolanızı girin)",
        "Running…": "Çalışıyor…",
        "✔ Operation completed successfully.": "✔ İşlem başarıyla tamamlandı.",
        "✖ Authorization was cancelled or denied.": "✖ Yetkilendirme iptal edildi veya reddedildi.",
        "✖ Operation failed (exit code {code}).": "✖ İşlem başarısız oldu (çıkış kodu {code}).",
        "Show packages installed\nas dependencies": "Bağımlılık olarak\nyüklenenleri de göster",
        "Clean unneeded\ndependencies": "Gereksiz bağımlılıkları\ntemizle",
        "Search applications…  (Ctrl+F)": "Uygulama ara…  (Ctrl+F)",
        "Info": "Bilgi",
        "Remove Selected": "Seçilenleri Kaldır",
        "Refresh": "Yenile",
        "Loading packages…": "Paketler yükleniyor…",
        "{shown} items shown · {size} total · {total} packages installed":
            "{shown} öğe gösteriliyor · toplam {size} · sistemde {total} paket yüklü",
        "{n} selected · {size}": "{n} seçili · {size}",
        "Package info": "Paket bilgisi",
        "Copy package name": "Paket adını kopyala",
        "Remove": "Kaldır",
        "Info — {name}": "Bilgi — {name}",
        "Desktop files:": "Masaüstü dosyaları:",
        "Cannot remove": "Kaldırılamıyor",
        "These package(s) cannot be removed because other packages need them:":
            "Bu paket(ler) kaldırılamıyor çünkü başka paketler onlara ihtiyaç duyuyor:",
        "{pkg} is required by {by}": "{pkg} → kullanan: {by}",
        "… and {n} more": "… ve {n} tane daha",
        "Tip: Remove the packages that use it first.": "İpucu: Önce onu kullanan paketleri kaldırın.",
        "⚠ <b>WARNING:</b> {pkgs} may be critical for the system! Removing it could make the system unbootable.":
            "⚠ <b>DİKKAT:</b> {pkgs} sistem için kritik olabilir! Kaldırmak sistemin açılmamasına yol açabilir.",
        "Confirm removal": "Kaldırmayı onayla",
        "<b>{n}</b> packages will be removed, freeing <b>{size}</b>:":
            "<b>{n}</b> paket kaldırılacak, <b>{size}</b> alan boşalacak:",
        "(no longer needed dependency)": "(artık gereksiz bağımlılık)",
        "Also delete system configuration files (no .pacsave backups)":
            "Sistem yapılandırma dosyalarını da sil (.pacsave bırakma)",
        "Cancel": "İptal",
        "Removing": "Kaldırılıyor",
        "Clean": "Temiz",
        "No unneeded (orphan) dependencies found. 👍": "Gereksiz (yetim) bağımlılık bulunamadı. 👍",
        "Unneeded dependencies": "Gereksiz bağımlılıklar",
        "Found {n} packages that no other package needs anymore ({size}). Remove them?":
            "Hiçbir paketin artık ihtiyaç duymadığı {n} paket bulundu ({size}). Kaldırılsın mı?",
        "Removing unneeded dependencies": "Gereksiz bağımlılıklar kaldırılıyor",
    },
    "pt_BR": {
        "CachyOS App Manager": "Gerenciador de Aplicativos CachyOS",
        "All": "Todos",
        "Desktop Applications": "Aplicativos de Desktop",
        "CachyOS Repository": "Repositório CachyOS",
        "Arch Repository (core/extra)": "Repositório Arch (core/extra)",
        "AUR / Foreign": "AUR / Externos",
        "Other Repositories": "Outros Repositórios",
        "Application": "Aplicativo",
        "Package": "Pacote",
        "Version": "Versão",
        "Source": "Origem",
        "Size": "Tamanho",
        "Description": "Descrição",
        "Source: {repo}": "Origem: {repo}",
        "(installed as a dependency)": "(instalado como dependência)",
        "Requesting authorization… (enter your password)": "Solicitando autorização… (digite sua senha)",
        "Running…": "Executando…",
        "✔ Operation completed successfully.": "✔ Operação concluída com sucesso.",
        "✖ Authorization was cancelled or denied.": "✖ A autorização foi cancelada ou negada.",
        "✖ Operation failed (exit code {code}).": "✖ A operação falhou (código de saída {code}).",
        "Show packages installed\nas dependencies": "Mostrar pacotes instalados\ncomo dependências",
        "Clean unneeded\ndependencies": "Limpar dependências\ndesnecessárias",
        "Search applications…  (Ctrl+F)": "Pesquisar aplicativos…  (Ctrl+F)",
        "Info": "Informações",
        "Remove Selected": "Remover Selecionados",
        "Refresh": "Atualizar",
        "Loading packages…": "Carregando pacotes…",
        "{shown} items shown · {size} total · {total} packages installed":
            "{shown} itens exibidos · {size} no total · {total} pacotes instalados",
        "{n} selected · {size}": "{n} selecionado(s) · {size}",
        "Package info": "Informações do pacote",
        "Copy package name": "Copiar nome do pacote",
        "Remove": "Remover",
        "Info — {name}": "Informações — {name}",
        "Desktop files:": "Arquivos .desktop:",
        "Cannot remove": "Não é possível remover",
        "These package(s) cannot be removed because other packages need them:":
            "Este(s) pacote(s) não pode(m) ser removido(s) porque outros pacotes dependem dele(s):",
        "{pkg} is required by {by}": "{pkg} é necessário para {by}",
        "… and {n} more": "… e mais {n}",
        "Tip: Remove the packages that use it first.": "Dica: remova primeiro os pacotes que o utilizam.",
        "⚠ <b>WARNING:</b> {pkgs} may be critical for the system! Removing it could make the system unbootable.":
            "⚠ <b>ATENÇÃO:</b> {pkgs} pode ser crítico para o sistema! Removê-lo pode impedir que o sistema inicie.",
        "Confirm removal": "Confirmar remoção",
        "<b>{n}</b> packages will be removed, freeing <b>{size}</b>:":
            "<b>{n}</b> pacote(s) será(ão) removido(s), liberando <b>{size}</b>:",
        "(no longer needed dependency)": "(dependência não mais necessária)",
        "Also delete system configuration files (no .pacsave backups)":
            "Excluir também os arquivos de configuração do sistema (sem backups .pacsave)",
        "Cancel": "Cancelar",
        "Removing": "Removendo",
        "Clean": "Tudo limpo",
        "No unneeded (orphan) dependencies found. 👍": "Nenhuma dependência órfã encontrada. 👍",
        "Unneeded dependencies": "Dependências desnecessárias",
        "Found {n} packages that no other package needs anymore ({size}). Remove them?":
            "Foram encontrados {n} pacotes que nenhum outro pacote precisa mais ({size}). Removê-los?",
        "Removing unneeded dependencies": "Removendo dependências desnecessárias",
    },
}


def detect_language():
    """Pick a translation from LANGUAGE/LC_ALL/LC_MESSAGES/LANG or Qt's system locale."""
    candidates = []
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(var):
            candidates += os.environ[var].split(":")
            break
    candidates += QLocale.system().uiLanguages()
    for c in candidates:
        c = c.replace("-", "_").split(".")[0]
        if c in TRANSLATIONS:
            return c
        base = c.split("_")[0]
        if base == "en" or base == "C":
            return "en"
        if base == "pt":
            return "pt_BR"
        if base in TRANSLATIONS:
            return base
    return "en"


LANG = "en"


def _(text, **kw):
    text = TRANSLATIONS.get(LANG, {}).get(text, text)
    return text.format(**kw) if kw else text


# ---- Package data -----------------------------------------------------------
LOCAL_DB = "/var/lib/pacman/local"
ENV_C = {**os.environ, "LC_ALL": "C"}

ARCH_REPOS = {"core", "extra", "multilib", "core-testing", "extra-testing", "multilib-testing"}

# Packages whose removal could break the system — an extra warning is shown.
CRITICAL = {
    "base", "base-devel", "glibc", "linux-firmware", "systemd", "pacman", "sudo",
    "bash", "coreutils", "filesystem", "grub", "limine", "refind", "systemd-boot-manager",
    "mesa", "networkmanager", "plasma-desktop", "plasma-workspace", "sddm", "kwin",
    "cachyos-settings", "cachyos-keyring", "cachyos-mirrorlist", "archlinux-keyring",
    "mkinitcpio", "dracut", "xorg-server", "wayland", "dbus", "polkit",
}

CATEGORIES = [
    ("all", "All", "view-list-details"),
    ("apps", "Desktop Applications", "applications-all"),
    ("cachyos", "CachyOS Repository", "cachyos"),
    ("arch", "Arch Repository (core/extra)", "archlinux"),
    ("aur", "AUR / Foreign", "package-x-generic"),
    ("other", "Other Repositories", "folder-remote"),
]


@dataclass
class Package:
    name: str
    version: str
    size: int
    desc: str
    repo: str            # pacman repo or "AUR"
    group: str           # cachyos / arch / aur / other
    explicit: bool
    app_name: str = ""   # display name from the .desktop file
    icon: str = ""
    desktop_files: list = field(default_factory=list)


def human_size(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TiB"


def run(cmd, env=ENV_C):
    return subprocess.run(cmd, capture_output=True, text=True, env=env).stdout


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
    name = e.get(f"Name[{LANG}]") or e.get(f"Name[{LANG.split('_')[0]}]") or e.get("Name", "")
    return name, e.get("Icon", "")


def load_packages():
    # Which repo a package came from: the first repo whose version matches wins.
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

    # Desktop applications: file lists in pacman's local database
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
    HEADERS = ["Application", "Package", "Version", "Source", "Size", "Description"]

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
            return _(self.HEADERS[section])

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
        if role == Qt.ItemDataRole.UserRole:  # sort key
            return [(p.app_name or p.name).lower(), p.name, p.version, p.repo,
                    p.size, p.desc.lower()][col]
        if role == Qt.ItemDataRole.DecorationRole and col == 0:
            return self.icon_for(p)
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{p.name} {p.version}\n{p.desc}\n" + _("Source: {repo}", repo=p.repo) + \
                ("" if p.explicit else "\n" + _("(installed as a dependency)"))
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
    """Runs a pkexec pacman command and shows its output live."""

    def __init__(self, parent, title, args):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 420)
        self.succeeded = False
        lay = QVBoxLayout(self)
        self.status = QLabel(_("Requesting authorization… (enter your password)"))
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
        self.status.setText(_("Running…"))
        text = bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        self.out.moveCursor(self.out.textCursor().MoveOperation.End)
        self.out.insertPlainText(text)
        self.out.ensureCursorVisible()

    def on_finished(self, code, _status):
        self.buttons.setEnabled(True)
        if code == 0:
            self.succeeded = True
            self.status.setText(_("✔ Operation completed successfully."))
        elif code in (126, 127):
            self.status.setText(_("✖ Authorization was cancelled or denied."))
        else:
            self.status.setText(_("✖ Operation failed (exit code {code}).", code=code))

    def reject(self):
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            return  # don't close while pacman is running
        super().reject()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("CachyOS App Manager"))
        self.setWindowIcon(QIcon.fromTheme("cachyos-app-manager", QIcon.fromTheme("system-software-install")))
        self.resize(1200, 720)

        self.model = PackageModel()
        self.proxy = PackageFilter()
        self.proxy.setSourceModel(self.model)

        # Left: categories
        self.cats = QListWidget()
        self.cats.setMaximumWidth(260)
        self.cats.setIconSize(self.cats.iconSize() * 1.4)
        for key, label, icon in CATEGORIES:
            it = QListWidgetItem(QIcon.fromTheme(icon, QIcon.fromTheme("folder")), _(label))
            it.setData(Qt.ItemDataRole.UserRole, key)
            self.cats.addItem(it)
        self.cats.setCurrentRow(1)
        self.cats.currentItemChanged.connect(self.on_category)

        self.deps_cb = QCheckBox(_("Show packages installed\nas dependencies"))
        self.deps_cb.toggled.connect(self.on_deps)

        orphan_btn = QPushButton(QIcon.fromTheme("edit-clear-all"), _("Clean unneeded\ndependencies"))
        orphan_btn.clicked.connect(self.remove_orphans)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(self.cats)
        ll.addWidget(self.deps_cb)
        ll.addWidget(orphan_btn)

        # Right: search + table + buttons
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Search applications…  (Ctrl+F)"))
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
        self.table.doubleClicked.connect(lambda _index: self.show_info())
        self.table.selectionModel().selectionChanged.connect(self.update_buttons)

        self.info_btn = QPushButton(QIcon.fromTheme("help-about"), _("Info"))
        self.info_btn.clicked.connect(self.show_info)
        self.remove_btn = QPushButton(QIcon.fromTheme("edit-delete"), _("Remove Selected"))
        self.remove_btn.setStyleSheet("QPushButton:enabled { font-weight: bold; }")
        self.remove_btn.clicked.connect(self.remove_selected)
        refresh_btn = QPushButton(QIcon.fromTheme("view-refresh"), _("Refresh"))
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

    # ---- data ----
    def reload(self):
        self.statusBar().showMessage(_("Loading packages…"))
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
            label = next(l for k, l, _icon in CATEGORIES if k == key)
            it.setText(f"{_(label)}  ({n})")
            if key == "other":
                it.setHidden(not any(p.group == "other" for p in pkgs))
        shown = self.proxy.rowCount()
        total = sum(self.model.pkgs[self.proxy.mapToSource(self.proxy.index(r, 0)).row()].size
                    for r in range(shown))
        self.statusBar().showMessage(
            _("{shown} items shown · {size} total · {total} packages installed",
              shown=shown, size=human_size(total), total=len(pkgs)))

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
        self.sel_label.setText(_("{n} selected · {size}", n=len(sel), size=human_size(sum(p.size for p in sel)))
                               if sel else "")

    # ---- actions ----
    def context_menu(self, pos):
        if not self.selected():
            return
        m = QMenu(self)
        m.addAction(QIcon.fromTheme("help-about"), _("Package info"), self.show_info)
        m.addAction(QIcon.fromTheme("edit-copy"), _("Copy package name"),
                    lambda: QGuiApplication.clipboard().setText(" ".join(p.name for p in self.selected())))
        m.addSeparator()
        m.addAction(QIcon.fromTheme("edit-delete"), _("Remove"), self.remove_selected)
        m.exec(self.table.viewport().mapToGlobal(pos))

    def show_info(self):
        sel = self.selected()
        if len(sel) != 1:
            return
        text = run(["pacman", "-Qi", sel[0].name], env=os.environ)  # in the user's language
        if sel[0].desktop_files:
            text += "\n" + _("Desktop files:") + "\n  " + "\n  ".join(sel[0].desktop_files)
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Info — {name}", name=sel[0].name))
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

        # Dry run: what gets removed, and does it break any dependency?
        r = subprocess.run(["pacman", "-Rs", "-p", "--print-format", "%n\t%v"] + names,
                           capture_output=True, text=True, env=ENV_C)
        if r.returncode != 0:
            blockers = re.findall(r"removing (\S+) breaks dependency '[^']+' required by (\S+)", r.stderr)
            if blockers:
                msg = _("These package(s) cannot be removed because other packages need them:") + "\n\n"
                msg += "\n".join("• " + _("{pkg} is required by {by}", pkg=pkg, by=by)
                                 for pkg, by in blockers[:15])
                if len(blockers) > 15:
                    msg += "\n" + _("… and {n} more", n=len(blockers) - 15)
            else:
                msg = r.stderr.strip()
            QMessageBox.warning(self, _("Cannot remove"),
                                msg + "\n\n" + _("Tip: Remove the packages that use it first."))
            return

        to_remove = [l.split("\t") for l in r.stdout.splitlines() if "\t" in l]
        sizes = {p.name: p.size for p in self.model.pkgs}
        total = sum(sizes.get(n, 0) for n, _v in to_remove)
        extra = [n for n, _v in to_remove if n not in names]

        dlg = QDialog(self)
        dlg.setWindowTitle(_("Confirm removal"))
        dlg.resize(560, 440)
        lay = QVBoxLayout(dlg)
        crit = [n for n in names if n in CRITICAL or n.startswith("linux")]
        if crit:
            w = QLabel(_("⚠ <b>WARNING:</b> {pkgs} may be critical for the system! "
                         "Removing it could make the system unbootable.", pkgs=", ".join(crit)))
            w.setWordWrap(True)
            w.setStyleSheet("color: #e5534b;")
            lay.addWidget(w)
        lay.addWidget(QLabel(_("<b>{n}</b> packages will be removed, freeing <b>{size}</b>:",
                               n=len(to_remove), size=human_size(total))))
        lst = QPlainTextEdit(readOnly=True)
        lst.setFont(QFont("monospace"))
        lst.setPlainText("\n".join(f"{n} {v}" + ("   " + _("(no longer needed dependency)") if n in extra else "")
                                   for n, v in to_remove))
        lay.addWidget(lst)
        nosave = QCheckBox(_("Also delete system configuration files (no .pacsave backups)"))
        nosave.setChecked(True)
        lay.addWidget(nosave)
        bb = QDialogButtonBox()
        ok = bb.addButton(_("Remove"), QDialogButtonBox.ButtonRole.AcceptRole)
        ok.setIcon(QIcon.fromTheme("edit-delete"))
        bb.addButton(_("Cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        flags = "-Rns" if nosave.isChecked() else "-Rs"
        self.run_root(_("Removing"), ["pkexec", "pacman", flags, "--noconfirm"] + names)

    def remove_orphans(self):
        orphans = run(["pacman", "-Qqdt"]).split()
        if not orphans:
            QMessageBox.information(self, _("Clean"), _("No unneeded (orphan) dependencies found. 👍"))
            return
        sizes = {p.name: p.size for p in self.model.pkgs}
        total = sum(sizes.get(n, 0) for n in orphans)
        box = QMessageBox(QMessageBox.Icon.Question, _("Unneeded dependencies"),
                          _("Found {n} packages that no other package needs anymore ({size}). Remove them?",
                            n=len(orphans), size=human_size(total)), parent=self)
        box.setDetailedText("\n".join(orphans))
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.run_root(_("Removing unneeded dependencies"),
                          ["pkexec", "pacman", "-Rns", "--noconfirm"] + orphans)

    def run_root(self, title, args):
        dlg = OutputDialog(self, title, args)
        dlg.exec()
        if dlg.succeeded:
            self.table.clearSelection()
            self.reload()


def main():
    global LANG
    if "--version" in sys.argv:
        print(f"cachyos-app-manager {__version__}")
        return
    app = QApplication(sys.argv)
    LANG = detect_language()
    # Qt's own strings (Yes/No/Close buttons, context menus) in the same language
    qt_tr = QTranslator(app)
    if qt_tr.load(f"qtbase_{LANG}", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(qt_tr)
    app.setApplicationName("cachyos-app-manager")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("cachyos-app-manager")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
