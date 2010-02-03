#!/usr/bin/python
#	vim:fileencoding=utf-8
# Create merged 'package.mask' file and maintain 'package.unmask' using it
# (C) 2010 Michał Górny, distributed under the terms of 3-clause BSD license

MY_PN='diffmask'
MY_PV='0.3'

import os, os.path, sys, tempfile
import optparse
import portage

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

	def __str__(self):
		f = self.tempfile
		f.seek(0, os.SEEK_SET)
		return ''.join(f.readlines())

	def GetPath(self):
		return self.tempfile.name

	def __init__(self):
		self.tempfile = tempfile.NamedTemporaryFile()
		self.ProcessAll()

def vimdiff(vimdiffcmd, unmaskpath):
	""" vimdiff merged package.mask with package.unmask """
	m = MaskMerge()
	os.system('%s "%s" "%s"' % (vimdiffcmd, m.GetPath(), unmaskpath))

def main(argv):
	defpunmask = '%setc/portage/package.unmask' % portage.settings['PORTAGE_CONFIGROOT']
	parser = optparse.OptionParser(version=MY_PV, usage='%prog <action> [options]')

	gr = optparse.OptionGroup(parser, 'Actions')
	gr.add_option('-v', '--vimdiff', action='store_const',
			dest='mode', const='vimdiff', help=vimdiff.__doc__.strip())
	parser.add_option_group(gr)

	gr = optparse.OptionGroup(parser, 'Options related to vimdiff')
	gr.add_option('--vimdiffcmd', action='store',
			dest='vimdiff', default='vimdiff', help='vimdiff command')
	gr.add_option('-u', '--unmask-file', action='store',
			dest='unmask', default=defpunmask,
			help='package.unmask file location (default: %s)' % defpunmask)
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

	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
