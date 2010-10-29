#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

from portage.dep import Atom, match_from_list
from portage.exception import InvalidAtom

from diffmask.util import DiffmaskList

class MaskFile(DiffmaskList):
	class MaskRepo(DiffmaskList):
		class MaskBlock(DiffmaskList):
			""" A single block of package.mask file. Basically a list of
				atoms, keeping the comments as well. """

			class MaskAtom:
				def __init__(self, s):
					# XXX: Read and pass the EAPI
					try:
						try:
							self.atom = Atom(s, allow_wildcard = True)
						except TypeError: # portage-2.1.8 compat
							self.atom = Atom(s)
					except InvalidAtom:
						self.atom = s
					else:
						if self.atom != s:
							raise AssertionError('Atom(%s) stringifies to %s' \
									% (s.rstrip(), self.atom.rstrip()))

				def toString(self):
					return self.atom

				def __contains__(self, cpv):
					if not isinstance(self.atom, Atom):
						return False
					else:
						return match_from_list(self.atom, [cpv])

			def __eq__(self, other):
				return (self.comment == other.comment and DiffmaskList.__eq__(self, other))

			def __contains__(self, cpv):
				if isinstance(cpv, self.MaskAtom):
					return DiffmaskList.__contains__(self, cpv)

				for atom in self:
					if cpv in atom:
						return True
				return False

			def toString(self):
				l = [DiffmaskList.toString(self)]
				return ''.join(self.before + self.comment + l + self.after)

			def append(self, data):
				if not isinstance(data, self.MaskAtom):
					data = self.MaskAtom(data)
				DiffmaskList.append(self, data)

			def __init__(self, data):
				DiffmaskList.__init__(self)
				self.before = []
				self.comment = []
				self.after = []

				for l in data:
					if not self:
						if not self.comment and not l.strip():
							self.before.append(l)
						elif l.startswith('#') or not l.strip():
							self.comment.append(l)
						else:
							self.append(l)
					elif l.startswith('#') or not l.strip():
						self.after.append(l)
					else:
						self.append(l)

				# We require each entry to end with a blank line
				if not self.after or not self.after[-1].endswith('\n'):
					self.after.append('\n')

		def append(self, data):
			if not isinstance(data, self.MaskBlock):
				data = self.MaskBlock(data)
			DiffmaskList.append(self, data)

		def extend(self, l):
			for x in l:
				self.append(x)

		def toString(self):
			out = []
			if self.name:
				out.append('## *%s*\n' % self.name)
			out.extend([x.toString() for x in self])
			return ''.join(out)

		def __init__(self, name):
			DiffmaskList.__init__(self)
			self.name = name

	def toString(self):
		out = DiffmaskList.toString(self)
		# If the file ends with a blank line, drop it.
		if out.endswith('\n\n'):
			return out[:-1]
		else:
			return out

	def __getitem__(self, name):
		if isinstance(name, int):
			return DiffmaskList.__getitem__(self, name)
		else:
			for r in self:
				if r.name == name:
					return r
			raise KeyError('No such repo')

	def __init__(self, data):
		repo = self.MaskRepo(None)
		DiffmaskList.__init__(self, [repo])
		buf = []
		pbuf = None
		tmprepo = []
		tmprepos = [(None, tmprepo)]
		gotatoms = False

		for l in data:
			if l.startswith('#'):
				newrepo = (l.startswith('## *') and l.endswith('*\n')) # repo name
				newmask = ('<' in l and '>' in l) # a mask header

				if gotatoms:
					tmprepo.append(buf)
					pbuf = buf
					buf = []
					gotatoms = False
				if newrepo:
					pbuf = None
					buf = []
					tmprepo = []
					tmprepos.append((l[4:-2], tmprepo))
					continue
				elif not gotatoms and newmask and pbuf is not None:
					pbuf.extend(buf)
					pbuf = None
					buf = []
			elif l.strip():
				gotatoms = True
			buf.append(l)

		if ''.join(buf).strip():
			tmprepo.append(buf)

		for reponame, entries in tmprepos:
			repo = self.MaskRepo(reponame)
			repo.extend(entries)
			self.append(repo)
