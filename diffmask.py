#!/usr/bin/python
#	vim:fileencoding=utf-8
# Create merged 'package.mask' file and maintain 'package.unmask' using it
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

MY_PN='diffmask'
MY_PV='0.3'

import os, os.path, sys, tempfile
from optparse import OptionParser, OptionGroup

import portage

class MaskMerge:
	def ProcessMaskFile(self, file, header):
		self.tempfile.write('\n## *%s*\n\n' % header)
		self.tempfile.writelines(file.readlines())

	def ProcessRepo(self, path):
		try:
			maskf = open('%s/profiles/package.mask' % path, 'r')
		except IOError:
			pass
		else:
			try:
				namef = open('%s/profiles/repo_name' % path, 'r')
				reponame = namef.readline().strip()
			except IOError:
				reponame = os.path.basename(path)

			self.ProcessMaskFile(maskf, reponame)

	def ProcessOverlays(self):
		overlays = portage.settings['PORTDIR_OVERLAY'].split()
		for o in overlays:
			self.ProcessRepo(o)

	def ProcessProfiles(self):
		for p in portage.settings.profiles:
			try:
				maskf = open('%s/package.mask' % p, 'r')
			except IOError:
				pass
			else:
				profname = 'profile: %s' % os.path.relpath(p, '%s/profiles' % self.portdir)
				self.ProcessMaskFile(maskf, profname)

	def ProcessAll(self):
		self.portdir = portage.settings['PORTDIR']

		self.ProcessOverlays()
		self.ProcessProfiles()
		self.ProcessRepo(self.portdir)

	def __str__(self):
		f = self.tempfile
		f.seek(0, os.SEEK_SET)
		return ''.join(f.readlines())

	def GetPath(self):
		return self.tempfile.name

	def __init__(self):
		self.tempfile = tempfile.NamedTemporaryFile()
		self.ProcessAll()

def vimdiff():
	m = MaskMerge()
	os.system('%s "%s" "%s"' % ('vimdiff', m.GetPath(), '/etc/portage/package.unmask'))

def main(argv):
	parser = OptionParser(version=MY_PV, usage='%prog <action> [options]')
	actions = OptionGroup(parser, 'Actions')
	actions.add_option('-v', '--vimdiff', action='store_const', dest='mode', const='vimdiff',
			help='vimdiff merged package.mask with package.unmask')
	parser.add_option_group(actions)
	(opts, args) = parser.parse_args(args=argv[1:])

	if opts.mode is None:
		if os.path.basename(argv[0]).startswith('vimdiff'):
			opts.mode = 'vimdiff'
		else:
			parser.print_help()
			return 2

	if opts.mode == 'vimdiff':
		vimdiff()

	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
