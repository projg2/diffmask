#!/usr/bin/python
#	vim:fileencoding=utf-8
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

from portage.dep import Atom, match_from_list, match_to_list
from portage.exception import InvalidAtom

from diffmask.util import DiffmaskList

class MaskFile(DiffmaskList):
	""" A package.mask format file. A list of repository blocks. """
	class MaskRepo(DiffmaskList):
		""" A single repository in MaskFile. A list of entries. """
		class MaskBlock(DiffmaskList):
			""" A single block of package.mask file. Basically a list of
				atoms, preserving the comments as well. """
			class MaskAtom(object):
				""" A single atom in the package.mask block. It can
					either point to an Atom() instance or a string, if
					the atom is incorrect. """
				def __init__(self, s):
					""" Try to parse the atom string s. If it's a
						correct atom, an internal instance of Atom()
						would be instantiated. Otherwise, the atom
						string will be kept. """
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
					""" Check whether the atom matches the given cpv.
						If it was incorrect, simply return False. """
					if not isinstance(self.atom, Atom):
						return False
					else:
						return match_from_list(self.atom, [cpv])

			def __eq__(self, other):
				""" Check whether two mask entries exactly match each
					other. This implies checking both the comment block
					and the complete atom list. Trailing whitespace is
					not taken into account. """
				return (self.toString().strip() == other.toString().strip())

			def __contains__(self, cpv):
				""" When passed a cpv, check whether at least one
					of the atoms in the mask entry match the given cpv.
					
					When passed a MaskAtom instance, check whether
					the particular Atom is contained within the entry.
					"""
				if isinstance(cpv, self.MaskAtom):
					return DiffmaskList.__contains__(self, cpv)

				atoms = [x.atom for x in self if isinstance(x.atom, Atom)]
				return match_to_list(cpv, atoms)

			def toString(self):
				l = [DiffmaskList.toString(self)]
				return ''.join(self.comment + l + self.after)

			def append(self, data):
				""" Append the atom to the entry, taking care
					of conversion into MaskAtom if necessary. """
				if not isinstance(data, self.MaskAtom):
					data = self.MaskAtom(data)
				DiffmaskList.append(self, data)

			def __init__(self, data):
				""" Instantiate a new MaskBlock from string list.
					The list is required to contain only the contents
					of a single mask entry. """
				DiffmaskList.__init__(self)
				self.comment = []
				self.after = []

				for l in data:
					if not self:
						if l.startswith('#'): # a comment
							self.comment.append(l)
						elif l.strip(): # the first atom
							self.append(l)
						elif self.comment: # a non-leading whitespace
							self.comment.append(l)
					elif l.startswith('#') or not l.strip():
						self.after.append(l)
					else:
						self.append(l)

				# We require each entry to end with a blank line
				if not self.after or not self.after[-1].endswith('\n'):
					self.after.append('\n')

		def append(self, data):
			""" Append the given block to the repository, taking care
				of casting into MaskBlock if necessary. """
			if not isinstance(data, self.MaskBlock):
				data = self.MaskBlock(data)
			DiffmaskList.append(self, data)

		def extend(self, l):
			for x in l:
				self.append(x)

		def toString(self):
			out = []
			if self.name:
				out.append('## *%s*\n\n' % self.name)
			out.extend([x.toString() for x in self])
			return ''.join(out)

		def __init__(self, name):
			""" Instiantate a new MaskRepo named 'name'. The repository
				will be empty and needs to be fed manually. """
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
		""" Get the repository by the numeric index or name. """
		if isinstance(name, int):
			return DiffmaskList.__getitem__(self, name)
		else:
			for r in self:
				if r.name == name:
					return r
			raise KeyError('No such repo')

	def __contains__(self, repo):
		if isinstance(repo, self.MaskRepo):
			return DiffmaskList.__contains__(self, repo)
		else:
			for r in self:
				if r.name == repo:
					return True
			return False

	def __init__(self, data):
		""" Instiantate a new MaskFile. Parse the contents of string
			list data, and feed the subclasses with it. """
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
