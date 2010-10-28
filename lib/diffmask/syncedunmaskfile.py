#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

from diffmask.maskfile import MaskFile
from diffmask.unmaskfile import UnmaskFile
from diffmask.util import DiffmaskList

class SyncedUnmaskFile(UnmaskFile):
	class SyncedUnmaskRepo(MaskFile.MaskRepo):
		def __init__(self, maskr, unmaskr, noner):
			""" Try to match blocks in unmaskr (unmask entries associated with repo)
				and noner (unassociated unmask entries) to those in maskr (mask entries
				associated with repo). Create blocklist containing matched entries. """
			MaskFile.MaskRepo.__init__(self, maskr.name)
			tblocks = []

			for b in unmaskr + noner:
				# first try to get exact match
				cb = maskr.find(b)
				if cb is not None:
					tblocks.append(cb)
				else:
					# then try partial matches
					# (both comment & atoms as they might come
					# from a set of different masks)
					for cb in maskr:
						if cb.comment == b.comment:
							tblocks.append(cb)
							continue
						for a in b:
							if a in cb:
								tblocks.append(cb)
								break

			# sort & uniq, now we have to get exact matches
			for cb in maskr:
				if cb in tblocks:
					self.append(cb)
					tblocks.remove(cb)
			if tblocks:
				raise AssertionError('At least a single match failed in the sorting loop')

	def __init__(self, mask, unmask):
		""" Update and cleanup 'unmask' file to match 'mask' file. """
		DiffmaskList.__init__(self)
		self.path = unmask.path

		# find the repo containing unmatched entries
		# (in fact it should be always the first one but better safe than sorry)
		try:
			nonerepo = unmask[None]
		except KeyError:
			nonerepo = []

		for mr in mask:
			if mr.name is not None:
				try:
					r = unmask[mr.name]
				except KeyError: # repo only in mask file
					r = []

				outr = self.SyncedUnmaskRepo(mr, r, nonerepo)
				if outr:
					self.append(outr)

		# repos which are only in unmask file are dropped implicitly
