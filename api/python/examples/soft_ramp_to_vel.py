#!/usr/bin/env python
"""
Simple example demonstrating how to set the velocity and direction
using the soft_ramp_to_vel method.
"""
from simple_step import Simple_Step

# Velocity and acceleration
vel = 20000
accel = 50000

# Open device 
dev = Simple_Step()

dir_setpt = dev.get_dir_setpt()

if dir_setpt == 'positive':
    dev.soft_ramp_to_vel(vel,'negative',accel)
else:
    dev.soft_ramp_to_vel(vel,'positive', accel)

dev.print_values()

# Close device
dev.close()

