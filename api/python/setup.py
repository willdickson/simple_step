from setuptools import setup, find_packages

setup(name='simple_step',
      version='0.1', 
      description = 'provides an interface to the simpke_step at90usb stepper motor controller',
      author = 'William Dickson',
      author_email = 'wbd@caltech.edi',
      packages=find_packages(),
      #entry_points = {'console_scripts': ['sine-stim = sine_stimulus:sine_stim_main',]}
      )
      
