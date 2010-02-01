#!/usr/bin/env python
"""
Simple example demonstrating how to set the velocity and direction
of the motor.
"""
import time
import scipy
from simple_step import Simple_Step

N = 500
vel = 20000

# Open device 
dev = Simple_Step()

dev.start()

dt_array = scipy.zeros((N,))
print dt_array.shape
for i in range(0,N):
    t0 = time.time()
    dev.set_vel_setpt(100)
    t1 = time.time()
    dt_array[i] = t1-t0
    
print 'mean dt:', dt_array.mean()



# Close device
dev.close()

