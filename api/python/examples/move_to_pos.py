#!/usr/bin/env python
"""
Simple example demonstrating simple point to point moves.

"""
from simple_step import Simple_Step

pos_0 = 0
pos_1 = 2*6400

# Positioning velocity  (Optional argument)
pos_vel = 10000 

# Open device 
dev = Simple_Step()

# Get current position
pos = dev.get_pos()

print 'current pos:', pos, 

# Perform move based on current position 
if pos == 0:
    print ', moving to pos: ', pos_1
    dev.move_to_pos(pos_1,pos_vel=pos_vel)
else:
    print ', moving to pos: ', pos_0
    dev.move_to_pos(pos_0,pos_vel=pos_vel)

# Print information
dev.print_values()

# Close device
dev.close()

