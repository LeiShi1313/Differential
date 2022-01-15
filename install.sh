#!/bin/bash
set -e

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
	    ubuntu|debian|raspbian)
		    pre_reqs="ffmpeg mediainfo zlib1g-dev libjpeg-dev python3 python3-pip"

			sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF
			if [ "$lsb_dist" = "ubuntu" ]; then
				case "$dist_version" in
			    	bionic|focal)
				    	pre_reqs="$pre_reqs gnupg ca-certificates"
				esac
				echo "deb https://download.mono-project.com/repo/ubuntu stable-$dist_version main" | sudo tee /etc/apt/sources.list.d/mono-official-stable.list
			else if [ "$lsb_dist" = "debian" ] || [ "$lsb_dist" = "raspbian" ]; then
			    pre_reqs="$pre_reqs apt-transport-https dirmngr gnupg ca-certificates"
				echo "deb https://download.mono-project.com/repo/debian stable-$dist_version main" | sudo tee /etc/apt/sources.list.d/mono-official-stable.list
			fi

			echo "正在更新安装包..." && \
			sudo apt update -qq >/dev/null && \
			echo "正在安装依赖..." && \
			sudo apt install -y -qq $pre_reqs >/dev/null && \
			echo "正在安装Mono..." && \
			sudo apt install mono-devel && \
			echo "正在安装差速器..." && \
			pip install Differential
		centos|fedora|rhel)
			if [ "$lsb_dist" = "fedora" ]; then
				pre_reqs="ffmpeg mediainfo python3 python3-pip"
				sudo rpm --import "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"
				if [[ $dist_version -gt 28 ]]; then
					sudo su -c "curl https://download.mono-project.com/repo/centos8-stable.repo | tee /etc/yum.repos.d/mono-centos8-stable.repo"
				else
					sudo su -c 'curl https://download.mono-project.com/repo/centos7-stable.repo | tee /etc/yum.repos.d/mono-centos7-stable.repo'
				fi
				pkg_manager="dnf"
			else
				pre_reqs="ffmpeg mediainfo python3 python3-pip"

				case "$dist_version" in
					7|8)
						sudo rpmkeys --import "http://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"
				case "$dist_version" in 
					6)
						sudo rpm --import "http://keyserver.ubuntu.com/pks/lookup?op=get&search=0x3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF"	
				esac
				sudo su -c "curl https://download.mono-project.com/repo/centos$dist_version-stable.repo | tee /etc/yum.repos.d/mono-centos$dist_version-stable.repo"
				pkg_manager="yum"
			fi

			echo "正在更新安装包..." && \
			sudo $pkg_manager update -y -qq > /dev/null && \
			echo "正在安装依赖..." && \
			sudo $pkg_manager install -y -q $pre_reqs > /dev/null && \
			echo "正在安装Mono..." && \
			sudo $pkg_manager install -y mono-devel
			echo "正在安装差速器..." && \
			pip install Differential
	esac

	if command_exists dft; then
		dft_version="$(dft -v | awk '{print $2}')"
		echo "差速器$dft_version安装成功"
	else
		echo "差速器安装失败"
}

do_install