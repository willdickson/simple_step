#!/usr/bin/env python
"""
Example demonstrating how to zero the motor indices. In this case
the zero is set to the current position.
"""
from simple_step import Simple_Step

# Open device 
dev = Simple_Step()

print 
print 'Before Zeroing'
print '='*60
dev.print_values()

# Get current position
pos = dev.get_pos()

# Zero indices  
dev.set_zero_pos(pos)

print
print 'After Zeroing' 
print '='*60
dev.print_values()

# Close device
dev.close()

