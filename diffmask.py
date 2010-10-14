#!/usr/bin/python
#	vim:fileencoding=utf-8
# Create merged 'package.mask' file and maintain 'package.unmask' using it
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

MY_PN='diffmask'
MY_PV='0.3'

import codecs, os, os.path, sys, tempfile
import optparse
import portage

class MaskFile:
	class MaskRepo:
		class MaskBlock:
			def __eq__(self, other):
				return (self.comment == other.comment and self.atoms == other.atoms)

			def toString(self):
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

		def toString(self):
			out = []
			if self.name:
				out.append('\n## *%s*\n\n' % self.name)
			out.extend([x.toString() for x in self.blocks])
			return ''.join(out)

		def __init__(self, name):
			self.name = name
			self.blocks = []

	def GetRepo(self, name):
		for r in self.repos:
			if r.name == name:
				return r
		raise KeyError('No such repo')

	def toString(self):
		return ''.join([x.toString() for x in self.repos])

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
		def toString(self):
			out = []
			if self.name:
				out.append('\n## *%s*\n\n' % self.name)
			out.extend([x.toString() for x in self.blocks])
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

	def toString(self):
		return ''.join([x.toString() for x in self.repos])

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

		self.data.extend(['\n', '## *%s*\n' % header, '\n'])
		self.data.extend(mf)

	def ProcessRepo(self, path):
		try:
			maskf = codecs.open(os.path.join(path, 'profiles', 'package.mask'), 'r', 'utf8')
		except IOError:
			pass
		else:
			try:
				namef = codecs.open(os.path.join(path, 'profiles', 'repo_name'), 'r', 'utf8')
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
				maskf = codecs.open(os.path.join(p, 'package.mask'), 'r', 'utf8')
			except IOError:
				pass
			else:
				profname = 'profile: %s' % os.path.relpath(p, os.path.join(self.portdir, 'profiles'))
				self.ProcessMaskFile(maskf, profname)

	def ProcessAll(self):
		self.portdir = portage.settings['PORTDIR']

		self.ProcessOverlays()
		self.ProcessProfiles()
		self.ProcessRepo(self.portdir)

	def toString(self):
		return ''.join(self.data)

	def GetLines(self):
		return self.data

	def __init__(self):
		self.data = []
		self.ProcessAll()

def update(unmaskpath, unmaskfile = None):
	""" Update unmasks according to current package.mask file and remove old ones. """
	mask = MaskFile(MaskMerge().GetLines())
	if unmaskfile is not None:
		unmask = unmaskfile
	else:
		unmask = MaskFile(codecs.open(unmaskpath, 'r', 'utf8').readlines())
	cmp = UnmaskFileClean(mask, unmask)

	scmp = cmp.toString()
	if scmp.strip() == unmask.toString().strip():
		print('The unmask file is up-to-date.')
	else:
		newfn = portage.util.new_protect_filename(unmaskpath)
		newf = codecs.open(newfn, 'w', 'utf8')
		newf.write(cmp.toString())

		print('New package.unmask saved as %s.\nPlease run dispatch-conf or etc-update to merge it.' % newfn)

def vimdiff(vimdiffcmd, unmaskpath):
	""" vimdiff merged package.mask with package.unmask. """
	m = MaskMerge()
	t = tempfile.NamedTemporaryFile()
	t.write(m.toString().encode('utf8'))
	t.flush()
	os.system('%s "%s" "%s"' % (vimdiffcmd, t.name, unmaskpath))

def add(pkgs, unmaskpath):
	""" Unmask specified packages. """
	unmask = MaskFile(codecs.open(unmaskpath, 'r', 'utf8').readlines())
	nonerepo = unmask.GetRepo(None)

	for pkg in pkgs:
		matches = portage.portdb.xmatch('match-all', pkg)
		if len(matches) == 0:
			print('No packages match %s.' % pkg)
			return

		while len(matches) > 0:
			bm = portage.best(matches)
			ms = portage.getmaskingstatus(bm)

			if len(ms) == 0:
				print('%s is visible, skipping.' % bm)
			elif 'package.mask' not in ms or len(ms) > 1:
				print('%s is masked by: %s; skipping.' % (bm, ', '.join(ms)))
			else:
				mr = portage.getmaskingreason(bm).splitlines(True)
				if not mr[0].startswith('#'):
					raise AssertionError("portage.getmaskingreason() didn't return a comment")

				print('Trying to unmask %s.' % bm)
				# getmaskingreason() can sometime provide a broken comment
				# so let's hope it or =pkg match will occur
				mr.extend(['=%s\n' % bm, '\n'])
				nonerepo.AppendBlock(mr)
				break

			matches.remove(bm)
		else:
			print('No packages matching %s and being only package.mask-masked were found.' % pkg)

	update(unmaskpath, unmask)

def main(argv):
	defpunmask = os.path.join(portage.settings['PORTAGE_CONFIGROOT'],
			'etc', 'portage', 'package.unmask')
	parser = optparse.OptionParser(version=MY_PV, usage='%prog <action> [options]')
	parser.add_option('-U', '--unmask-file', action='store',
			dest='unmask', default=defpunmask,
			help='package.unmask file location (default: %s)' % defpunmask)

	gr = optparse.OptionGroup(parser, 'Actions')
	gr.add_option('-a', '--add', action='store_const',
			dest='mode', const='add', help=add.__doc__.strip())
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
	elif opts.mode == 'add':
		if len(args) == 0:
			print('--add requires at least one package name.')
			return 2
		add(args, opts.unmask)

	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
