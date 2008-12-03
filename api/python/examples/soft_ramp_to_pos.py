#!/usr/bin/env python
"""
Simple example demonstrating the use of a soft ramp for point to point
moves.
"""
from simple_step import Simple_Step

pos_0 = 0
pos_1 = 2*6400

# Ramp acceleration (ind/sec**2)
accel = 10000

# Positioning velocity (ind/sec)
pos_vel = 20000

# Open device 
dev = Simple_Step()

# Get current position
pos = dev.get_pos()

# Perform move based on current position 
if pos == 0:
    dev.soft_ramp_to_pos(pos_1,accel,pos_vel=pos_vel)
else:
    dev.soft_ramp_to_pos(pos_0,accel,pos_vel=pos_vel)

# Print information
dev.print_values()

# Close device
dev.close()
