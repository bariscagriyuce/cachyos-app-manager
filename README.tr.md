# CachyOS Uygulama Yöneticisi

[English](README.md) | **Türkçe** | [Português (Brasil)](README.pt-BR.md)

CachyOS'ta (ve diğer Arch tabanlı dağıtımlarda) **yüklü paketleri görüntülemek, aramak ve kaldırmak** için basit bir grafik arayüz. `pacman` komutlarını ezberlemenize gerek kalmaz.

## Diller

Arayüz, sistem dilinize göre kendiliğinden açılır:

- 🇬🇧 İngilizce (varsayılan)
- 🇹🇷 Türkçe
- 🇧🇷 Brezilya Portekizcesi

Belirli bir dilde açmak için örneğin `LANGUAGE=pt_BR cachyos-app-manager` komutunu kullanın.
Yeni bir dil eklemek için `cachyos_app_manager.py` dosyasının başındaki `TRANSLATIONS` sözlüğüne yeni bir bölüm, `.desktop` dosyasına da `Name[xx]`/`Comment[xx]` satırları eklemek yeterlidir.

## Özellikler

- Kenar çubuğunda, her birinin yanında paket sayısı yazan **kategoriler**:
  - **Masaüstü Uygulamaları**: görünür bir `.desktop` kısayolu olan paketler (uygulama menünüzde gördükleriniz)
  - **CachyOS Deposu**: `cachyos`, `cachyos-v3`, `cachyos-core-v3`, `cachyos-extra-v3` vb. depolardan gelen paketler
  - **Arch Deposu**: `core`, `extra`, `multilib` depolarından gelen paketler
  - **AUR / Harici**: hiçbir depoda bulunmayan paketler (`pacman -Qm`)
  - **Diğer Depolar**: özel depolar (yalnızca varsa gösterilir)
  - **Tümü**
- Uygulama adında, paket adında ve açıklamada **anında arama** (`Ctrl+F`).
- Seçilen bir veya birden fazla paketi **tek tıkla kaldırma** (`Delete` tuşu veya düğme):
  - Kaldırılacak her şeyi, artık gereksiz kalan bağımlılıklar dahil, önceden gösterir ve ne kadar yer açılacağını söyler.
  - Parolayı `pkexec` ile grafik bir pencerede sorar, ardından `pacman -Rns` komutunu çalıştırıp çıktısını canlı gösterir.
  - Seçilen paketlere başka paketler ihtiyaç duyuyorsa, sessizce hata vermek yerine hangileri olduğunu açıklar.
  - Kritik sistem paketleri (`glibc`, `systemd`, çekirdekler, `plasma-desktop` vb.) için ek uyarı gösterir.
- **Gereksiz bağımlılıkları temizleme**: artık hiçbir paketin ihtiyaç duymadığı bağımlılıkları kaldırır (`pacman -Qdt`).
- Çift tıklayınca paket bilgisi (`pacman -Qi`), sıralanabilir sütunlar (örneğin boyuta göre), sağ tık menüsü.
- Bağımlılık olarak yüklenen paketler varsayılan olarak gizlidir; onay kutusuyla gösterilebilir.

## Kurulum

Repoda bir `PKGBUILD` dosyası var, bu yüzden uygulama normal bir pacman paketi olarak kurulur (program, menü kısayolu ve simge `/usr` altına yerleşir):

```bash
git clone https://github.com/bariscagriyuce/cachyos-app-manager.git
cd cachyos-app-manager
makepkg -si
```

Ardından **CachyOS Uygulama Yöneticisi**'ni uygulama menüsünden açın veya `cachyos-app-manager` komutunu çalıştırın.

Güncellemek için: `git pull && makepkg -si`. Kaldırmak için: `sudo pacman -R cachyos-app-manager`.

Bağımlılıklar (`python-pyqt6`, `expac`, `polkit`) `makepkg -s` tarafından otomatik kurulur; hepsi CachyOS KDE'de zaten yüklü gelir.

### Kurmadan çalıştırma

```bash
python3 cachyos_app_manager.py
```

## Nasıl çalışır

| Bilgi | Kaynak |
|---|---|
| Yüklü paketler, sürüm, boyut, açıklama | `expac -Q '%n\t%v\t%m\t%d'` |
| Paketin hangi depodan geldiği | `pacman -Sl` (sürümü yüklü olanla eşleşen ilk depo) |
| AUR / harici paketler | `pacman -Qqm` |
| Doğrudan mı yoksa bağımlılık olarak mı yüklendiği | `pacman -Qqe` |
| Uygulama adı ve simgesi | `/var/lib/pacman/local/*/files` içinde listelenen `.desktop` dosyaları |
| Kaldırma önizlemesi | `pacman -Rs -p` (deneme çalıştırması, root gerekmez) |
| Kaldırma | `pkexec pacman -Rns --noconfirm <paketler>` |

Uygulama verileri yalnızca normal kullanıcı olarak okur; root yetkisi sadece bir kaldırma işlemini onayladığınızda polkit üzerinden istenir.

## Lisans

Bu proje [GNU Genel Kamu Lisansı v3.0 veya sonrası](LICENSE) ile lisanslanmıştır.
