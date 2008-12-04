#!/usr/bin/env python
"""
Example demonstrating enabling and disabling the stepper drive
by toggling the enable pin.

"""
from simple_step import Simple_Step

dev = Simple_Step()

print 'Toggling Enable'
print 
print 'Before'
print '='*60
dev.print_values()

enable = dev.get_enable()
if enable == 'enabled':
    dev.disable()
else:
    dev.enable()

print 
print 'After'
print '='*60
dev.print_values()

dev.close()

