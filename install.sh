#!/bin/bash
set -euo pipefail

BDINFO_VERSION="${BDINFO_VERSION:-1.0.5}"
DIFFERENTIAL_PACKAGE="${DIFFERENTIAL_PACKAGE:-Differential}"
DIFFERENTIAL_SKIP_INSTALL="${DIFFERENTIAL_SKIP_INSTALL:-0}"

SUDO=()

command_exists() {
	command -v "$1" >/dev/null 2>&1
}

setup_sudo() {
	if [ "$(id -u)" -eq 0 ]; then
		return
	fi
	if ! command_exists sudo; then
		echo "当前用户不是root，且未找到sudo，无法安装系统依赖。"
		exit 1
	fi
	SUDO=(sudo)
}

run_as_root() {
	"${SUDO[@]}" "$@"
}

add_pipx_bin_to_path() {
	local pipx_bin_dir="${PIPX_BIN_DIR:-$HOME/.local/bin}"
	case ":$PATH:" in
		*":$pipx_bin_dir:"*) ;;
		*) PATH="$PATH:$pipx_bin_dir" ;;
	esac
	export PATH
}

pipx_run() {
	if command_exists pipx; then
		pipx "$@"
	else
		python3 -m pipx "$@"
	fi
}

load_os_release() {
	if [ ! -r /etc/os-release ]; then
		return 1
	fi

	# shellcheck disable=SC1091
	. /etc/os-release
	DIST_ID="${ID:-}"
	DIST_ID_LIKE="${ID_LIKE:-}"
	DIST_VERSION_ID="${VERSION_ID:-}"
	DIST_PRETTY_NAME="${PRETTY_NAME:-$DIST_ID $DIST_VERSION_ID}"
}

is_distro_like() {
	local target="$1"
	case " $DIST_ID $DIST_ID_LIKE " in
		*" $target "*) return 0 ;;
		*) return 1 ;;
	esac
}

bdinfo_runtime() {
	case "$(uname -s):$(uname -m)" in
		Linux:x86_64|Linux:amd64)
			echo "linux-x64"
			;;
		Linux:aarch64|Linux:arm64)
			echo "linux-arm64"
			;;
		Darwin:x86_64|Darwin:amd64)
			echo "osx-x64"
			;;
		Darwin:aarch64|Darwin:arm64)
			echo "osx-arm64"
			;;
		*)
			return 1
			;;
	esac
}

install_bdinfo() {
	if command_exists BDInfo; then
		echo "BDInfo已安装"
		return
	fi

	local runtime
	if ! runtime="$(bdinfo_runtime)"; then
		echo "当前系统架构暂未自动安装BDInfo，请从 https://github.com/tetrahydroc/BDInfoCLI/releases 手动安装"
		return
	fi

	local tmp_dir
	tmp_dir="$(mktemp -d)"
	local bdinfo_url="https://github.com/tetrahydroc/BDInfoCLI/releases/download/v${BDINFO_VERSION}/BDInfo-${runtime}.tar.gz"

	echo "正在安装BDInfo ${BDINFO_VERSION} (${runtime})..."
	curl -fsSL "$bdinfo_url" -o "$tmp_dir/BDInfo.tar.gz"
	tar -xzf "$tmp_dir/BDInfo.tar.gz" -C "$tmp_dir"

	local bdinfo_binary
	bdinfo_binary="$(find "$tmp_dir" -type f -name BDInfo | head -n 1)"
	if [ -z "$bdinfo_binary" ]; then
		echo "BDInfo安装包中未找到可执行文件"
		rm -rf "$tmp_dir"
		exit 1
	fi

	run_as_root mkdir -p /usr/local/bin
	run_as_root install -m 755 "$bdinfo_binary" /usr/local/bin/BDInfo
	rm -rf "$tmp_dir"
}

install_differential() {
	if [ "$DIFFERENTIAL_SKIP_INSTALL" = "1" ]; then
		echo "已跳过差速器安装"
		return
	fi

	add_pipx_bin_to_path
	if command_exists dft; then
		echo "差速器已安装"
		return
	fi

	echo "正在安装差速器..."
	pipx_run ensurepath >/dev/null || true
	pipx_run install "$DIFFERENTIAL_PACKAGE"
	add_pipx_bin_to_path
}

install_apt_dependencies() {
	echo "正在安装Debian/Ubuntu依赖..."
	export DEBIAN_FRONTEND=noninteractive
	run_as_root apt-get update -qq >/dev/null
	run_as_root apt-get install -y -qq \
		ca-certificates \
		curl \
		ffmpeg \
		libicu-dev \
		libjpeg-dev \
		mediainfo \
		pipx \
		python3 \
		zlib1g-dev >/dev/null
}

install_fedora_dependencies() {
	echo "正在安装Fedora依赖..."
	local packages=(ca-certificates curl libicu mediainfo pipx python3)
	if ! run_as_root dnf install -y "${packages[@]}" ffmpeg-free; then
		run_as_root dnf install -y "${packages[@]}" ffmpeg
	fi
}

enable_rhel_builder_repo() {
	if ! command_exists dnf; then
		return
	fi

	run_as_root dnf install -y dnf-plugins-core >/dev/null || true
	run_as_root dnf config-manager --set-enabled crb >/dev/null 2>&1 || \
		run_as_root dnf config-manager --set-enabled powertools >/dev/null 2>&1 || \
		true
}

install_rhel_like_dependencies() {
	echo "正在安装RHEL/CentOS/Rocky/AlmaLinux依赖..."
	local pkg_manager="dnf"
	if ! command_exists dnf; then
		pkg_manager="yum"
	fi

	local major="${DIST_VERSION_ID%%.*}"
	run_as_root "$pkg_manager" install -y ca-certificates >/dev/null
	if ! command_exists curl; then
		run_as_root "$pkg_manager" install -y curl-minimal || run_as_root "$pkg_manager" install -y curl
	fi
	enable_rhel_builder_repo

	if ! run_as_root "$pkg_manager" install -y epel-release; then
		run_as_root "$pkg_manager" install -y "https://dl.fedoraproject.org/pub/epel/epel-release-latest-${major}.noarch.rpm"
	fi

	run_as_root "$pkg_manager" install -y "https://download1.rpmfusion.org/free/el/rpmfusion-free-release-${major}.noarch.rpm" || true
	run_as_root "$pkg_manager" install -y \
		ffmpeg \
		gcc \
		libicu \
		libjpeg-devel \
		mediainfo \
		pipx \
		python3 \
		python3-devel \
		zlib-devel
}

install_arch_dependencies() {
	echo "正在安装Arch依赖..."
	run_as_root pacman -Sy --noconfirm --needed \
		ca-certificates \
		curl \
		ffmpeg \
		icu \
		mediainfo \
		python \
		python-pipx >/dev/null
}

install_macos_dependencies() {
	echo "正在安装macOS依赖..."
	if ! command_exists brew; then
		echo "macOS一键安装需要先安装Homebrew: https://brew.sh/"
		exit 1
	fi

	brew update
	brew install ffmpeg mediainfo pipx
}

install_linux_dependencies() {
	if ! load_os_release; then
		echo "无法读取 /etc/os-release，暂不支持当前Linux发行版。"
		exit 1
	fi

	echo "检测到系统: $DIST_PRETTY_NAME"
	if is_distro_like debian || is_distro_like ubuntu; then
		install_apt_dependencies
	elif is_distro_like fedora && [ "$DIST_ID" = "fedora" ]; then
		install_fedora_dependencies
	elif is_distro_like rhel || is_distro_like centos || is_distro_like fedora; then
		install_rhel_like_dependencies
	elif is_distro_like arch; then
		install_arch_dependencies
	else
		echo "系统版本 $DIST_PRETTY_NAME 还未支持！"
		exit 1
	fi
}

verify_install() {
	if [ "$DIFFERENTIAL_SKIP_INSTALL" = "1" ]; then
		echo "依赖安装检查已跳过差速器命令验证"
		return
	fi

	add_pipx_bin_to_path
	if command_exists dft; then
		echo "差速器安装成功"
	else
		echo "差速器安装失败"
		exit 1
	fi
}

do_install() {
	setup_sudo
	case "$(uname -s)" in
		Linux)
			install_linux_dependencies
			;;
		Darwin)
			install_macos_dependencies
			;;
		*)
			echo "当前系统 $(uname -s) 还未支持！"
			exit 1
			;;
	esac

	install_bdinfo
	install_differential
	verify_install
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	do_install
fi
