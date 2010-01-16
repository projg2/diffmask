#!/bin/sh
# Create merged 'package.mask' file and vimdiff it with 'package.unmask'
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

# If you don't like vim, you can set VIMDIFFCMD to some other editor/script.
# It will be called with merged temporary file path as first arg and (guessed)
# package.unmask path as the second one.
# EXAMPLE: VIMDIFFCMD='diff -u' vimdiffmask.sh

MY_PN=diffmask
MY_PV=0.2

die() {
	echo "$@" >&2
	exit 1
}

get_tempfile() {
	if ! mktemp -q 2>/dev/null; then
		local tmpfn
		tmpfn="${TMPDIR:-/tmp}/tmp.$(basename "$0")-$$"
		touch "${tmpfn}" || die 'Unable to create temporary file.'
		echo "${tmpfn}"
	fi
}

cleanup() {
	[ -n "${TEMPFILE}" ] && rm -f "${TEMPFILE}"
	trap - EXIT # avoid re-calling
	exit 0
}

get_repo_name() {
	local dir
	dir="$1"

	cat "${dir}"/profiles/repo_name 2>/dev/null \
		|| echo x-"$(basename "${dir}")"
}

process_repo() {
	local repo pmf

	repo="$1"
	pmf="${repo}"/profiles/package.mask

	if [ -f "${pmf}" ]; then
		echo "## $(get_repo_name "${repo}")"
		echo
		cat "${pmf}"
		echo
	fi
}

process_overlays() {
	local overlay overlays

	overlays="$(portageq portdir_overlay)"
	[ $? -eq 0 ] || die 'Unable to query portage for overlay list.'

	for overlay in ${overlays}; do
		process_repo ${overlay}
	done
}

process_profile() {
	local profile parent
	
	cd -P "${1}"
	profile="${PWD}"

	if [ -f package.mask ]; then
		echo "## make.profile: ${profile#${PORTDIR}/profiles/}"
		echo
		cat package.mask
		echo
	fi

	if [ -f parent ]; then
		# we prefer to have the list in reverse order but that is not obligatory
		# so try to use 'tac' and fallback to 'cat' if it is not available
		for parent in $(tac parent 2>/dev/null || cat parent); do
			# recurring
			process_profile ${parent}

			cd "${profile}"
		done
	fi
}

process_profiles() {
	local profpath

	profpath="${PORTAGE_CONFIGROOT}"/etc/make.profile

	[ -d "${profpath}" ] || die "${PORTAGE_CONFIGROOT}/etc/make.profile does not point to a valid directory."
	[ -L "${profpath}" ] || echo "WARNING: ${PORTAGE_CONFIGROOT}/etc/make.profile is not a symlink." >&2

	process_profile "${profpath}"
}

process_all() {
	process_overlays
	process_profiles
	process_repo "${PORTDIR}"
}

usage() {
	cat >&2 <<__EOF__
Synopsis: $0 <action> ...

Where action is:
	vimdiff		edit package.unmask using \${VIMDIFFCMD} or vimdiff

	install ...	behave like 'make install', passing options
			(default: DESTDIR= PREFIX=/usr SYMLINKS=1)
__EOF__

	exit 0
}

ACTION="$1"

NEEDMASK=1

case "${ACTION}" in
	vimdiff)
		shift
		;;
	install)
		shift
		NEEDMASK=0
		;;
	*)
		case "$(basename "$0")" in
			vim*)
				ACTION=vimdiff
				;;
			*)
				usage
				;;
		esac
		;;
esac

if [ ${NEEDMASK} -eq 1 ]; then
	PORTDIR="$(portageq portdir)"
	[ -n "${PORTDIR}" ] || die 'Unable to get PORTDIR.'
	[ -d "${PORTDIR}" ] || die 'PORTDIR does not point to a valid directory.'
	PORTAGE_CONFIGROOT="$(portageq envvar PORTAGE_CONFIGROOT)"
fi

TEMPFILE=
trap cleanup EXIT HUP INT QUIT TERM
TEMPFILE="$(get_tempfile)"

if [ ${NEEDMASK} -eq 1 ]; then
	process_all > "${TEMPFILE}"
fi

case "${ACTION}" in
	vimdiff)
		${VIMDIFFCMD:-vimdiff} "${TEMPFILE}" "${PORTAGE_CONFIGROOT}"/etc/portage/package.unmask
		;;
	install)
		cat > "${TEMPFILE}" << __EOF__
DESTDIR =
PREFIX = /usr/local
SYMLINKS = 1
MY_PN = ${MY_PN}

BINDIR = \$(PREFIX)/bin

DMASK = 022
FMOD = 0755

install:
	umask \$(DMASK) && mkdir -p "\$(DESTDIR)\$(BINDIR)"
	cp -f "$0" "\$(DESTDIR)\$(BINDIR)"/\$(MY_PN)
	chmod \$(FMOD) "\$(DESTDIR)\$(BINDIR)"/\$(MY_PN)
	[ \$(SYMLINKS) -ne 1 ] || ln -fs \$(MY_PN) "\$(DESTDIR)\$(BINDIR)"/vim\$(MY_PN)

.PHONY: install
__EOF__

		make -f "${TEMPFILE}" "$@" install 
		;;
esac

exit 0
