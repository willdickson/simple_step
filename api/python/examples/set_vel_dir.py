#!/usr/bin/env python
"""
Simple example demonstrating how to set the velocity and direction
of the motor.
"""
from simple_step import Simple_Step

# Velocity
vel = 20000

# Open device 
dev = Simple_Step()

dir_setpt = dev.get_dir_setpt()

if dir_setpt == 'positive':
    dev.set_vel_and_dir(vel,'negative')
else:
    dev.set_vel_and_dir(vel,'positive')

dev.print_values()

# Close device
dev.close()
