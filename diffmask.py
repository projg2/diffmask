#!/usr/bin/python
#	vim:fileencoding=utf-8
# Create merged 'package.mask' file and maintain 'package.unmask' using it
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

MY_PN='diffmask'
MY_PV='0.3'

import os, os.path, sys, tempfile

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

	def __init__(self):
		self.tempfile = tempfile.NamedTemporaryFile()
		self.ProcessAll()

def main(argv):
	merge = MaskMerge()
	print merge
	return 0

sys.exit(main(sys.argv))
