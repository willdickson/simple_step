"""
simple_step.py

This file is part of simple_step.

simple_step is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
    
simple_step is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with Foobar.  If not, see
<http://www.gnu.org/licenses/>.

---------------------------------------------------------------------

Author: William Dickson 
"""
from setuptools import setup, find_packages

setup(name='simple_step',
      version='0.1', 
      description = 'provides an interface to the simpke_step at90usb stepper motor controller',
      author = 'William Dickson',
      author_email = 'wbd@caltech.edi',
      packages=find_packages(),
      #entry_points = {'console_scripts': ['sine-stim = sine_stimulus:sine_stim_main',]}
      )
      
