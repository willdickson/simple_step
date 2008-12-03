#!/usr/bin/env python
"""
Simple example demonstrating the stop command

"""
from simple_step import Simple_Step

# Open device 
dev = Simple_Step()

dev.stop()

# Close device
dev.close()

