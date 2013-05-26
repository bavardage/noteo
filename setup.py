#!/usr/bin/env python

from distutils.core import setup
import glob

setup(name='Noteo-fork',
        version='0.1.3',
        description='A notifications system (fork of the noteo system)',
        author='Nuno Cardoso',
        author_email='nunopcardoso@gmail.com',
        url='https://github.com/npcardoso/noteo',
        classifiers=[
            'Intended Audience :: End Users/Desktop',
            'License :: GNU General Public License (GPL)',
            'Operating System :: Linux',
            'Programming Language :: Python',
            ],
        py_modules=["Noteo"],
        scripts = ['noteo'],
        data_files = [('share/pixmaps', ['noteo.png']),
                      ('share/noteo/modules', glob.glob('modules/*'))]
        )
