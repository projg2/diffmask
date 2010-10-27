#!/usr/bin/python
#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 3-clause BSD license.

from distutils.core import setup

import os.path, sys

setup(
		name = 'diffmask',
		version = '0.3.2',
		author = 'Michał Górny',
		author_email = 'mgorny@gentoo.org',
		url = 'http://github.com/mgorny/diffmask',

		scripts = ['diffmask'],

		classifiers = [
			'Development Status :: 3 - Alpha',
			'Environment :: Console',
			'Intended Audience :: System Administrators',
			'License :: OSI Approved :: BSD License',
			'Operating System :: POSIX',
			'Programming Language :: Python',
			'Topic :: System :: Installation/Setup'
		]
)
