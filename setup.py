from setuptools import setup
from Cython.Build import cythonize

setup(name='RHTCy', ext_modules=cythonize('HarmonyToolCy.pyx'), package_dir={'cython_test': ''})
