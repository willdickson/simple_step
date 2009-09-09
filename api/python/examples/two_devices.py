#!/usr/bin/env python
import simple_step

devA = simple_step.Simple_Step(serial_number='A.0.0.0.0.0.0')
devB = simple_step.Simple_Step(serial_number='B.0.0.0.0.0.0')

devA.print_values()
print
devB.print_values()
print

print 
print 'starting device A'
devA.start()
print 'setting velocity setpoint of device B'
devB.set_vel_setpt(1000)

devA.print_values()
print
devB.print_values()
print


