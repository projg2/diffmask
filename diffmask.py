#!/usr/bin/python
#	vim:fileencoding=utf-8
# Create merged 'package.mask' file and maintain 'package.unmask' using it
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

MY_PN='diffmask'
MY_PV='0.3'

import os, os.path, sys, tempfile
import optparse
import portage

class Suicide:
	pass

class MaskFile:
	class MaskRepo:
		class MaskBlock:
			def __eq__(self, other):
				return (self.comment == other.comment and self.atoms == other.atoms)

			def __str__(self):
				return ''.join(self.before + self.comment + self.atoms + self.after)

			def __init__(self, data):
				self.before = []
				self.comment = []
				self.atoms = []
				self.after = []

				for l in data:
					if len(self.atoms) == 0:
						if len(self.comment) == 0 and l.strip() == '':
							self.before.append(l)
						elif l.startswith('#') or l.strip() == '':
							self.comment.append(l)
						else:
							self.atoms.append(l)
					elif l.startswith('#') or l.strip() == '':
						self.after.append(l)
					else:
						self.atoms.append(l)

		def AppendBlock(self, data):
			self.blocks.append(self.MaskBlock(data))

		def __str__(self):
			out = []
			if self.name:
				out.append('\n## *%s*\n\n' % self.name)
			out.extend([str(x) for x in self.blocks])
			return ''.join(out)

		def __init__(self, name):
			self.name = name
			self.blocks = []

	def GetRepo(self, name):
		for r in self.repos:
			if r.name == name:
				return r
		raise KeyError('No such repo')

	def __str__(self):
		return ''.join([str(x) for x in self.repos])

	def __init__(self, data):
		repo = self.MaskRepo(None)
		self.repos = [repo]
		buf = []
		gotatoms = False

		for l in data:
			if l.startswith('#'):
				newrepo = (l.startswith('## *') and l.endswith('*\n')) # repo name

				if gotatoms or newrepo:
					repo.AppendBlock(buf)
					buf = []
					gotatoms = False
				if newrepo:
					repo = self.MaskRepo(l[4:-2])
					self.repos.append(repo)
					continue
			elif ''.join(l).strip() != '':
				gotatoms = True
			buf.append(l)

		if ''.join(buf).strip() != '':
			repo.AppendBlock(buf)

		# cleanup leading/trailing whitespace (one belonging to repo header)
		for r in self.repos:
			try:
				if r.blocks[0].before[0] == '\n':
					del r.blocks[0].before[0]
			except IndexError:
				pass
			try:
				if r.blocks[-1].after[-1] == '\n':
					del r.blocks[-1].after[-1]
			except IndexError:
				pass

class UnmaskFileClean:
	class UnmaskRepoClean:
		def __str__(self):
			out = []
			if self.name:
				out.append('\n## *%s*\n\n' % self.name)
			out.extend([str(x) for x in self.blocks])
			return ''.join(out)

		def __init__(self, maskr, unmaskr, noner):
			""" Try to match blocks in unmaskr (unmask entries associated with repo)
				and noner (unassociated unmask entries) to those in maskr (mask entries
				associated with repo). Create blocklist containing matched entries. """
			self.name = maskr.name
			self.blocks = []
			inblocks = []
			tblocks = []

			if unmaskr is not None:
				inblocks.extend(unmaskr.blocks)
			if noner is not None:
				inblocks.extend(noner.blocks)

			for b in inblocks:
				# first try to get exact match
				for cb in maskr.blocks:
					if cb == b:
						tblocks.append(cb)
						break
				else:
					# then try partial matches
					for cb in maskr.blocks:
						if cb.comment == b.comment:
							tblocks.append(cb)
							break
					for a in b.atoms:
						for cb in maskr.blocks:
							if a in cb.atoms:
								tblocks.append(cb)
								break

			# sort & unify, now we have to get exact matches
			for b in tblocks:
				for cb in maskr.blocks:
					if cb == b:
						for ub in self.blocks: # unify
							if cb == ub:
								break
						else:
							self.blocks.append(cb)
						break
				else:
					raise AssertionError('Match failed in sorting loop')

	def __str__(self):
		return ''.join([str(x) for x in self.repos])

	def __init__(self, mask, unmask):
		""" Update and cleanup 'unmask' file to match 'mask' file. """
		self.repos = []

		# find the repo containing unmatched entries
		# (in fact it should be always the first one but better safe than sorry)
		for r in unmask.repos:
			if r.name is None:
				nonerepo = r
				break
		else:
			nonerepo = None

		for mr in mask.repos:
			if mr.name is not None:
				try:
					r = unmask.GetRepo(mr.name)
				except KeyError: # repo only in mask file
					r = None

				outr = self.UnmaskRepoClean(mr, r, nonerepo)
				if len(outr.blocks):
					self.repos.append(outr)

		# repos which are only in unmask file are dropped implicitly

class MaskMerge:
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
			elif mf[i].strip() == '':
				gotwhite = True
			else: # package atom
				if ccb is not None:
					del mf[:ccb]
				break

		self.tempfile.write('\n## *%s*\n\n' % header)
		self.tempfile.writelines(mf)

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
		self.tempfile.flush()

	def __str__(self):
		return ''.join(self.GetLines())

	def GetPath(self):
		return self.tempfile.name

	def GetLines(self):
		f = self.tempfile
		f.seek(0, os.SEEK_SET)
		return f.readlines()

	def __init__(self):
		self.tempfile = tempfile.NamedTemporaryFile()
		self.ProcessAll()

def update(unmaskpath):
	""" Update unmasks according to current package.mask file and remove old ones. """
	mask = MaskFile(MaskMerge().GetLines())
	unmask = MaskFile(open(unmaskpath, 'r').readlines())
	cmp = UnmaskFileClean(mask, unmask)

	newfn = portage.util.new_protect_filename(unmaskpath)
	newf = open(newfn, 'w')
	newf.write(str(cmp))
	newf.close()

	print 'New package.unmask saved as %s.\nPlease run dispatch-conf or etc-update to merge it.' % newfn

def vimdiff(vimdiffcmd, unmaskpath):
	""" vimdiff merged package.mask with package.unmask. """
	m = MaskMerge()
	os.system('%s "%s" "%s"' % (vimdiffcmd, m.GetPath(), unmaskpath))

def main(argv):
	defpunmask = '%setc/portage/package.unmask' % portage.settings['PORTAGE_CONFIGROOT']
	parser = optparse.OptionParser(version=MY_PV, usage='%prog <action> [options]')
	parser.add_option('-U', '--unmask-file', action='store',
			dest='unmask', default=defpunmask,
			help='package.unmask file location (default: %s)' % defpunmask)

	gr = optparse.OptionGroup(parser, 'Actions')
	gr.add_option('-u', '--update', action='store_const',
			dest='mode', const='update', help=update.__doc__.strip())
	gr.add_option('-v', '--vimdiff', action='store_const',
			dest='mode', const='vimdiff', help=vimdiff.__doc__.strip())
	parser.add_option_group(gr)

	gr = optparse.OptionGroup(parser, 'Options related to vimdiff')
	gr.add_option('--vimdiffcmd', action='store',
			dest='vimdiff', default='vimdiff', help='vimdiff command')
	parser.add_option_group(gr)

	(opts, args) = parser.parse_args(args=argv[1:])

	if opts.mode is None:
		if os.path.basename(argv[0]).startswith('vimdiff'):
			opts.mode = 'vimdiff'
		else:
			parser.print_help()
			return 2

	if opts.mode == 'vimdiff':
		vimdiff(opts.vimdiff, opts.unmask)
	elif opts.mode == 'update':
		update(opts.unmask)

	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
