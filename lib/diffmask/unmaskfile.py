#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

import codecs, os.path

from portage.util import new_protect_filename

from diffmask.maskfile import MaskFile

class UnmaskFile(MaskFile):
	def __init__(self, path):
		if os.path.exists(path):
			data = codecs.open(path, 'r', 'utf8').readlines()
		else:
			data = []
		MaskFile.__init__(self, data)
		self.path = path

	def write(self, path = None):
		if path is None:
			path = self.path

		c = self.toString()

		try:
			origf = codecs.open(path, 'r', 'utf8')
		except (OSError, IOError):
			pass
		else:
			if origf.read().strip() == c.strip():
				origf.close()
				print('The unmask file is up-to-date.')
				return path
			else:
				origf.close()

		newfn = new_protect_filename(path)
		# Always try hard to get a diff.
		if newfn == path:
			open(newfn, 'w').close()
			newfn = new_protect_filename(path)
		newf = codecs.open(newfn, 'w', 'utf8')
		newf.write(c)

		print('New package.unmask saved as %s.\nPlease run dispatch-conf or etc-update to merge it.' % newfn)
		return newfn
