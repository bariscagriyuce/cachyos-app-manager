# Maintainer: bariscagriyuce <https://github.com/bariscagriyuce>
pkgname=cachyos-app-manager
pkgver=1.1.0
pkgrel=1
pkgdesc="GUI to view, search and uninstall installed packages, grouped by CachyOS, Arch and AUR"
arch=('any')
url="https://github.com/bariscagriyuce/cachyos-app-manager"
license=('GPL-3.0-or-later')
depends=('python' 'python-pyqt6' 'pacman' 'expac' 'polkit')
optdepends=('qt6-translations: translated Qt dialog buttons')
source=('cachyos_app_manager.py'
        'cachyos-app-manager.desktop'
        'cachyos-app-manager.svg'
        'LICENSE')
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
  install -Dm755 cachyos_app_manager.py "$pkgdir/usr/bin/$pkgname"
  install -Dm644 cachyos-app-manager.desktop "$pkgdir/usr/share/applications/$pkgname.desktop"
  install -Dm644 cachyos-app-manager.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/$pkgname.svg"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
