#!/usr/bin/env python
"""
Simple example demonstrating the move by method.

"""
from simple_step import Simple_Step

# Move size in indices (use delta_pos < 0 to move the negative direction)
delta_pos = 6400

# Positioning velocity (Optional argument)
pos_vel = 15000

# Open device 
dev = Simple_Step()

# Get current position
pos = dev.get_pos()

# Perform move  
dev.move_by(delta_pos, pos_vel=pos_vel)

# Print information
dev.print_values()

# Close device
dev.close()

