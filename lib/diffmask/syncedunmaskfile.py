#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

from copy import copy

from diffmask.maskfile import MaskFile
from diffmask.unmaskfile import UnmaskFile
from diffmask.util import DiffmaskList

class SyncedUnmaskFile(UnmaskFile):
	""" The package.unmask file with forced sync to package.mask files.
		In other words, this class is going to accept only package
		entries which match package.mask, and will output them in
		package.mask order. """
	class SyncedUnmaskRepo(MaskFile.MaskRepo):
		""" A single repository within SyncedUnmaskFile. """
		def __init__(self, origrepo):
			""" Instantiate the SyncedUnmaskRepo, copying the entries
				from `origrepo' (MaskRepo instance). """
			self.name = origrepo.name
			for e in origrepo:
				ce = copy(e)
				ce._enabled = False
				DiffmaskList.append(self, ce)

		def append(self, entry):
			""" `Append' a block to the repository, checking if it does
				match the package.mask file. Technically, this function
				simply enables appropriate entries copied in __init__().
				"""
			if not isinstance(entry, self.MaskBlock):
				entry = self.MaskBlock(entry)

			e = self.find(entry)
			if e is not None:
				e._enabled = True
			else:
				# Now try to get a partial match as atoms floating
				# around might have been appended to the block.
				for e in self:
					if e.comment == entry.comment:
						e._enabled = True
					for a in entry:
						if a in e:
							e._enabled = True

		def extend(self, entries):
			for e in entries:
				self.append(e)

		def toString(self):
			out = [x.toString() for x in self if x._enabled]
			if out and self.name:
				out.insert(0, '## *%s*\n\n' % self.name)
			return ''.join(out)

	def append(self, repo):
		if not isinstance(repo, self.SyncedUnmaskRepo):
			repo = self.SyncedUnmaskRepo(repo)
		DiffmaskList.append(self, repo)

	def __init__(self, mask, unmask):
		""" Instantiate the SyncedUnmaskFile using a package.mask file
			instance `mask' and UnmaskFile instance `unmask'. """
		DiffmaskList.__init__(self)
		self.path = unmask.path

		for r in mask:
			self.append(r)
		for ur in unmask:
			if ur.name is None:
				for r in self:
					r.extend(ur)
			elif ur.name in self:
				self[ur.name].extend(ur)
