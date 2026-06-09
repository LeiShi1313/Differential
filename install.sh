#!/bin/bash
set -e

SUDO=$(if [ "$(id -u)" -gt 0 ]; then echo "sudo "; fi)

get_distribution() {
	lsb_dist=""
	# Every system that we officially support has /etc/os-release
	if [ -r /etc/os-release ]; then
		lsb_dist="$(. /etc/os-release && echo "$ID")"
	fi
	# Returning an empty string here should be alright since the
	# case statements don't act unless you provide an actual value
	echo "$lsb_dist"
}

command_exists() {
	command -v "$@" > /dev/null 2>&1
}

reload_path() {
  for file in ~/.bashrc ~/.bash_profile ~/.profile; do
  if [ -f "$file" ]; then
    . "$file"
  fi
done
}

BDINFO_VERSION="${BDINFO_VERSION:-1.0.5}"

install_bdinfo() {
	if command_exists BDInfo; then
		echo "BDInfo已安装"
		return
	fi

	case "$(uname -m)" in
		x86_64|amd64)
			bdinfo_runtime="linux-x64"
			;;
		aarch64|arm64)
			bdinfo_runtime="linux-arm64"
			;;
		*)
			echo "当前架构暂未自动安装BDInfo，请从 https://github.com/tetrahydroc/BDInfoCLI/releases 手动安装"
			return
			;;
	esac

	tmp_dir="$(mktemp -d)"
	bdinfo_url="https://github.com/tetrahydroc/BDInfoCLI/releases/download/v${BDINFO_VERSION}/BDInfo-${bdinfo_runtime}.tar.gz"
	echo "正在安装BDInfo ${BDINFO_VERSION}..."
	curl -fsSL "$bdinfo_url" -o "$tmp_dir/BDInfo.tar.gz"
	tar -xzf "$tmp_dir/BDInfo.tar.gz" -C "$tmp_dir"
	bdinfo_binary="$(find "$tmp_dir" -type f -name BDInfo | head -n 1)"
	if [ -z "$bdinfo_binary" ]; then
		echo "BDInfo安装包中未找到可执行文件"
		rm -rf "$tmp_dir"
		exit 1
	fi
	$SUDO install -m 755 "$bdinfo_binary" /usr/local/bin/BDInfo
	rm -rf "$tmp_dir"
}

do_install() {
    lsb_dist=$( get_distribution )
	lsb_dist="$(echo "$lsb_dist" | tr '[:upper:]' '[:lower:]')"

	case "$lsb_dist" in
		ubuntu)
			if command_exists lsb_release; then
				dist_version="$(lsb_release --codename | cut -f2)"
			fi
			if [ -z "$dist_version" ] && [ -r /etc/lsb-release ]; then
				dist_version="$(. /etc/lsb-release && echo "$DISTRIB_CODENAME")"
			fi
			case "$dist_version" in
				focal)
					dist_version="focal"
				;;
				bionic)
					dist_version="bionic"
				;;
				xenial)
					dist_version="xenial"
				;;
				*)
					dist_version="focal"
				;;
			esac
		;;

		debian|raspbian)
			dist_version="$(sed 's/\/.*//' /etc/debian_version | sed 's/\..*//')"
			case "$dist_version" in
				10)
					dist_version="buster"
				;;
				9)
					dist_version="stretch"
				;;
				8)
					dist_version="jessie"
				;;
				*)
					dist_version="buster"
				;;
			esac
		;;

		centos|rhel|sles|amzn)
			if [ -z "$dist_version" ] && [ -r /etc/os-release ]; then
				dist_version="$(. /etc/os-release && echo "$VERSION_ID")"
			fi
		;;

		*)
			if command_exists lsb_release; then
				dist_version="$(lsb_release --release | cut -f2)"
			fi
			if [ -z "$dist_version" ] && [ -r /etc/os-release ]; then
				dist_version="$(. /etc/os-release && echo "$VERSION_ID")"
			fi
		;;
	esac

    case "$lsb_dist" in
	    ubuntu | debian | raspbian)
			echo "正在更新依赖..."
			export DEBIAN_FRONTEND=noninteractive
			$SUDO apt-get update -qq >/dev/null
		    pre_reqs="ffmpeg mediainfo zlib1g-dev libjpeg-dev python3 pipx curl"

			if [ "$lsb_dist" = "ubuntu" ]; then
				# TODO ubuntu:18.04 Cannot install due to pymediainfo error, might need install newer python
				TZ=Etc/UTC $SUDO apt-get install -y -qq gnupg ca-certificates apt-utils >/dev/null
			elif [ "$lsb_dist" = "debian" ] || [ "$lsb_dist" = "raspbian" ]; then
				$SUDO apt-get install -y -qq apt-transport-https dirmngr gnupg ca-certificates apt-utils >/dev/null

				case "$dist_version" in
				    stretch|jessie)
						# TODO: Jessie is haveing some SSL issue
						# might need to install openssl as well
						# pip is configured with locations that require TLS/SSL, however the ssl module in Python is not available.
						echo "正在安装python3.8..."  && \
						$SUDO apt-get install -y -qq wget build-essential checkinstall libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev && \
						pushd /tmp && \
						$SUDO wget https://www.python.org/ftp/python/3.8.12/Python-3.8.12.tgz && \
						$SUDO tar xzf Python-3.8.12.tgz && \
						cd Python-3.8.12 && \
						$SUDO ./configure --enable-optimizations > /dev/null && \
						$SUDO make altinstall
						;;
				esac
			fi

			echo "正在更新安装包..." && \
			$SUDO apt-get update -qq >/dev/null && \
			echo "正在安装依赖..." && \
			TZ=Etc/UTC $SUDO apt-get install -y -qq $pre_reqs >/dev/null && \
			install_bdinfo && \
			echo "正在安装差速器..."
			$SUDO pipx ensurepath && reload_path
			pipx install Differential
			;;

		centos | fedora | rhel)
			if [ "$lsb_dist" = "fedora" ]; then
				pkg_manager="dnf"
				pre_reqs="ffmpeg mediainfo python3 pipx curl"

				$SUDO $pkg_manager install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
				$SUDO $pkg_manager config-manager --enable PowerTools && dnf install --nogpgcheck && \
				$SUDO $pkg_manager install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
			else
				pkg_manager="yum"
				pre_reqs="ffmpeg mediainfo python3 pipx zlib-devel libjpeg-devel gcc python3-devel curl"

				$SUDO $pkg_manager install -y -qq epel-release
				case "$dist_version" in
					8)
						echo "Enabling PowerTools" && \
						$SUDO dnf -y install dnf-plugins-core 2>&1 > /dev/null && \
						$SUDO dnf upgrade -y 2>&1 > /dev/null && \
						$SUDO dnf -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
						$SUDO dnf config-manager --set-enabled powertools && \
						$SUDO dnf -y install mediainfo 2>&1 > /dev/null
						$SUDO $pkg_manager install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
						;;
					7)
						$SUDO rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
						$SUDO rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm
						;;
					6)
						$SUDO rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
						$SUDO rpm -Uvh http://li.nux.ro/download/nux/dextop/el6/x86_64/nux-dextop-release-0-2.el6.nux.noarch.rpm
						;;
				esac
			fi

			echo "正在更新安装包..." && \
			$SUDO $pkg_manager update -y -qq > /dev/null && \
			echo "正在安装依赖..." && \
			$SUDO $pkg_manager install -y -qq $pre_reqs > /dev/null && \
			install_bdinfo && \
			echo "正在安装差速器..."
			$SUDO pipx ensurepath && reload_path
			pipx install Differential
			;;
		arch)
			echo "正在安装依赖..." && \
			$SUDO pacman -Sy --noconfirm vlc python3 python-pipx mediainfo ffmpeg curl > /dev/null 2>&1
			# TODO cleanup ffmpeg ?
			install_bdinfo
			echo "正在安装差速器..." && \
			$SUDO pipx ensurepath && reload_path
			pipx install Differential
			;;
		*)
			echo "系统版本 $lsb_dist $dist_version 还未支持！"
			;;

	esac

	if command_exists dft; then
		dft_version="$(dft -v | awk '{print $2}')"
		echo "差速器$dft_version安装成功"
	else
		echo "差速器安装失败"
	fi
}

do_install
