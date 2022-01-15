#!/bin/bash
set -e

SUDO=$(if [ $(id -u $whoami) -gt 0 ]; then echo "sudo "; fi)

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
		;;

		debian|raspbian)
			dist_version="$(sed 's/\/.*//' /etc/debian_version | sed 's/\..*//')"
			case "$dist_version" in
				11)
					dist_version="bullseye"
				;;
				10)
					dist_version="buster"
				;;
				9)
					dist_version="stretch"
				;;
				8)
					dist_version="jessie"
				;;
			esac
		;;

		centos|rhel|sles)
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

	echo $dist_version
    case "$lsb_dist" in
	    ubuntu | debian | raspbian)
			echo "正在更新依赖..."
			$SUDO apt-get update -qq >/dev/null
		    pre_reqs="ffmpeg mediainfo zlib1g-dev libjpeg-dev python3 python3-pip"

			if [ "$lsb_dist" = "ubuntu" ]; then
				# TODO ubuntu:18.04 Cannot install due to pymediainfo error, might need install newer python
				case "$dist_version" in
			    	bionic|focal)
						$SUDO apt-get install -y -qq gnupg ca-certificates >/dev/null
						;;
				esac
				$SUDO apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
				echo "deb https://download.mono-project.com/repo/ubuntu stable-$dist_version main" | $SUDO tee /etc/apt/sources.list.d/mono-official-stable.list
			elif [ "$lsb_dist" = "debian" ] || [ "$lsb_dist" = "raspbian" ]; then
				$SUDO apt-get install -y -qq apt-transport-https dirmngr gnupg ca-certificates >/dev/null
				$SUDO apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
				echo "deb https://download.mono-project.com/repo/debian stable-$dist_version main" | $SUDO tee /etc/apt/sources.list.d/mono-official-stable.list

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
			$SUDO apt-get install -y -qq $pre_reqs >/dev/null && \
			echo "正在安装Mono..." && \
			$SUDO apt-get install -y -qq mono-devel && \
			echo "正在安装差速器..."
			if command_exists pip3; then
				pip3 install Differential
			elif command_exists pip; then
				pip install Differential
			elif command_exists pip3.8; then
				pip3.8 install Differential
			fi
			;;

		centos | fedora | rhel)
			if [ "$lsb_dist" = "fedora" ]; then
				pkg_manager="dnf"
				pre_reqs="ffmpeg mediainfo python3 python3-pip"

				$SUDO rpm --import "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"
				if [[ $dist_version -gt 28 ]]; then
					$SUDO su -c "curl https://download.mono-project.com/repo/centos8-stable.repo | $SUDO tee /etc/yum.repos.d/mono-centos8-stable.repo"
				else
					$SUDO su -c "curl https://download.mono-project.com/repo/centos7-stable.repo | $SUDO tee /etc/yum.repos.d/mono-centos7-stable.repo"
				fi
				$SUDO $pkg_manager install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
				$SUDO $pkg_manager config-manager --enable PowerTools && dnf install --nogpgcheck && \
				$SUDO $pkg_manager install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
			else
				pkg_manager="yum"
				pre_reqs="ffmpeg mediainfo python3 python3-pip zlib-devel libjpeg-devel gcc python3-devel"

				$SUDO $pkg_manager install -y -qq epel-release
				case "$dist_version" in
					8)
						echo "Enabling PowerTools" && \
						$SUDO dnf -y install dnf-plugins-core 2>&1 > /dev/null && \
						$SUDO dnf upgrade -y 2>&1 > /dev/null && \
						$SUDO dnf -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
						$SUDO dnf config-manager --set-enabled powertools && \
						$SUDO dnf -y install mediainfo 2>&1 > /dev/null
						$SUDO rpmkeys --import "http://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"
						$SUDO $pkg_manager install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
						;;
					7)
						$SUDO rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
						$SUDO rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-5.el7.nux.noarch.rpm
						$SUDO rpmkeys --import "http://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"
						;;
					6)
						$SUDO rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
						$SUDO rpm -Uvh http://li.nux.ro/download/nux/dextop/el6/x86_64/nux-dextop-release-0-2.el6.nux.noarch.rpm
						$SUDO rpm --import "http://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"	
						;;
				esac
				$SUDO su -c "curl https://download.mono-project.com/repo/centos$dist_version-stable.repo | $SUDO tee /etc/yum.repos.d/mono-centos$dist_version-stable.repo"
			fi

			echo "正在更新安装包..." && \
			$SUDO $pkg_manager update -y -qq > /dev/null && \
			echo "正在安装依赖..." && \
			$SUDO $pkg_manager install -y -qq $pre_reqs > /dev/null && \
			echo "正在安装Mono..." && \
			$SUDO $pkg_manager install -y mono-devel && \
			echo "正在安装差速器..."
			if command_exists pip3; then
				pip3 install Differential
			else
				pip install Differential
			fi
			;;
		arch)
			echo "正在安装依赖..." && \
			$SUDO pacman -Sy --noconfirm vlc python3 python-pip mediainfo 2>&1 > /dev/null
			# TODO cleanup ffmpeg ?
			echo "正在安装差速器..." && \
			pip install Differential
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