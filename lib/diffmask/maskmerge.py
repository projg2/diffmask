#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

import codecs, os.path
from diffmask.util import DiffmaskList

class MaskMerge(DiffmaskList):
	def ProcessMaskFile(self, file, header):
		mf = file.readlines()

		# try to drop copyright, examples etc.
		ccb = None # current comment block
		gotwhite = True # whitespace status

		for i in range(len(mf)):
			if mf[i].startswith('#'):
				if gotwhite:
					ccb = i
					gotwhite = False
			elif not mf[i].strip():
				gotwhite = True
			else: # package atom
				if ccb is not None:
					del mf[:ccb]
				break

		self.extend(['\n', '## *%s*\n' % header, '\n'])
		self.extend(mf)

	def ProcessRepos(self):
		for o in self.portdb.getRepositories():
			path = self.portdb.getRepositoryPath(o)
			try:
				maskf = codecs.open(os.path.join(path, 'profiles', 'package.mask'), 'r', 'utf8')
			except IOError:
				pass
			else:
				self.ProcessMaskFile(maskf, o)

	def ProcessProfiles(self):
		for p in self.portdb.settings.profiles:
			try:
				maskf = codecs.open(os.path.join(p, 'package.mask'), 'r', 'utf8')
			except IOError:
				pass
			else:
				profname = 'profile: %s' % os.path.relpath(p, os.path.join(self.portdb.porttree_root, 'profiles'))
				self.ProcessMaskFile(maskf, profname)

	def ProcessAll(self):
		self.ProcessRepos()
		self.ProcessProfiles()

	def __init__(self, dbapi):
		self.portdb = dbapi
		self.ProcessAll()
