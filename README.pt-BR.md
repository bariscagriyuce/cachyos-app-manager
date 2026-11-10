# Gerenciador de Aplicativos CachyOS

[English](README.md) | [Türkçe](README.tr.md) | **Português (Brasil)**

Uma ferramenta gráfica simples para **visualizar, pesquisar e desinstalar pacotes instalados** no CachyOS (e em outras distribuições baseadas no Arch), sem precisar decorar comandos do `pacman`.

## Idiomas

A interface segue automaticamente o idioma do sistema:

- 🇬🇧 Inglês (padrão)
- 🇹🇷 Turco
- 🇧🇷 Português do Brasil

Para forçar um idioma, inicie com, por exemplo, `LANGUAGE=pt_BR cachyos-app-manager`.
Para adicionar um idioma, basta incluir um novo dicionário em `TRANSLATIONS`, no início de `cachyos_app_manager.py`, e as linhas `Name[xx]`/`Comment[xx]` no arquivo `.desktop`.

## Recursos

- **Categorias** na barra lateral, cada uma com a contagem de pacotes:
  - **Aplicativos de Desktop**: pacotes que trazem um atalho `.desktop` visível (o que você vê no menu de aplicativos)
  - **Repositório CachyOS**: pacotes de `cachyos`, `cachyos-v3`, `cachyos-core-v3`, `cachyos-extra-v3`, …
  - **Repositório Arch**: pacotes de `core`, `extra`, `multilib`
  - **AUR / Externos**: pacotes que não estão em nenhum repositório (`pacman -Qm`)
  - **Outros Repositórios**: repositórios personalizados (exibido somente se existirem)
  - **Todos**
- **Pesquisa instantânea** por nome do aplicativo, nome do pacote e descrição (`Ctrl+F`).
- **Desinstalação com um clique** de um ou mais pacotes selecionados (tecla `Delete` ou botão):
  - Mostra uma prévia de tudo o que será removido, incluindo dependências órfãs, e quanto espaço será liberado.
  - Usa o `pkexec` para pedir a senha em uma janela gráfica e depois executa `pacman -Rns` mostrando a saída em tempo real.
  - Se outros pacotes dependerem da seleção, explica quais são em vez de falhar sem aviso.
  - Aviso extra para pacotes críticos do sistema (`glibc`, `systemd`, kernels, `plasma-desktop`, …).
- **Limpar órfãos**: remove dependências de que nada mais precisa (`pacman -Qdt`).
- Detalhes do pacote (`pacman -Qi`) com clique duplo, colunas ordenáveis (por exemplo, por tamanho) e menu de clique direito.
- Pacotes instalados como dependências ficam ocultos por padrão; podem ser exibidos pela caixa de seleção.

## Instalação

O repositório contém um `PKGBUILD`, então o aplicativo é instalado como um pacote normal do pacman (programa, atalho no menu e ícone vão para `/usr`):

```bash
git clone https://github.com/bariscagriyuce/cachyos-app-manager.git
cd cachyos-app-manager
makepkg -si
```

Depois, abra o **Gerenciador de Aplicativos CachyOS** pelo menu de aplicativos ou execute `cachyos-app-manager`.

Para atualizar: `git pull && makepkg -si`. Para desinstalar: `sudo pacman -R cachyos-app-manager`.

As dependências (`python-pyqt6`, `expac`, `polkit`) são instaladas automaticamente pelo `makepkg -s`; todas já vêm por padrão no CachyOS KDE.

### Executar sem instalar

```bash
python3 cachyos_app_manager.py
```

## Como funciona

| Informação | Origem |
|---|---|
| Pacotes instalados, versão, tamanho, descrição | `expac -Q '%n\t%v\t%m\t%d'` |
| De qual repositório o pacote veio | `pacman -Sl` (o primeiro repositório cuja versão corresponde à instalada) |
| Pacotes do AUR / externos | `pacman -Qqm` |
| Instalado explicitamente ou como dependência | `pacman -Qqe` |
| Nome e ícone do aplicativo | Arquivos `.desktop` listados em `/var/lib/pacman/local/*/files` |
| Prévia da remoção | `pacman -Rs -p` (simulação, não precisa de root) |
| Remoção | `pkexec pacman -Rns --noconfirm <pacotes>` |

O aplicativo lê os dados apenas como usuário comum; privilégios de root são solicitados via polkit somente quando você confirma uma remoção.

## Licença

Este projeto está licenciado sob a [Licença Pública Geral GNU v3.0 ou posterior](LICENSE).
