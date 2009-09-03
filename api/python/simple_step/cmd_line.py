"""
-----------------------------------------------------------------------
simple_step
Copyright (C) William Dickson, 2008.
  
wbd@caltech.edu
www.willdickson.com

Released under the LGPL Licence, Version 3

This file is part of simple_step.

simple_step is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
    
simple_step is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with simple_step.  If not, see
<http://www.gnu.org/licenses/>.

------------------------------------------------------------------------

Purpose: Provides command line interface for the at90usb based stepper
motor controller.

Author: William Dickson 

------------------------------------------------------------------------
"""
import sys
import optparse
import atexit
from simple_step import Simple_Step


DEFAULT_ACCEL = 15000

class Simple_Step_Cmd_Line:
    
    
    """
    Command line interface for simple_step stepper motor controller
    """

    def __init__(self):

        # Table of command strings to command methods
        self.cmd_table = {
            'dfu-mode'    : self.dfu_mode,
            'dio-hi'      : self.dio_hi,
            'dio-lo'      : self.dio_lo,
            'print-vals'  : self.print_vals,
            'start'       : self.start,
            'stop'        : self.stop,
            'enable'      : self.enable,
            'disable'     : self.disable,
            'move-to-pos' : self.move_to_pos,
            'move-by'     : self.move_by,
            'ramp-to-pos' : self.ramp_to_pos,
            'set-vel'     : self.set_vel,
            'ramp-to-vel' : self.ramp_to_vel,
            'zero'        : self.zero,
            'help'        : self.help,
            'set-ext-int' : self.set_ext_int,
            'get-ext-int' : self.get_ext_int,
            }

        # Table of command strings to help strings
        self.help_table = {
            'dfu-mode'    : Simple_Step_Cmd_Line.dfu_mode_help_str,
            'dio-hi'      : Simple_Step_Cmd_Line.dio_hi_help_str,
            'dio-lo'      : Simple_Step_Cmd_Line.dio_lo_help_str,
            'print-vals'  : Simple_Step_Cmd_Line.print_vals_help_str,
            'start'       : Simple_Step_Cmd_Line.start_help_str,
            'stop'        : Simple_Step_Cmd_Line.stop_help_str,
            'enable'      : Simple_Step_Cmd_Line.enable_help_str,
            'disable'     : Simple_Step_Cmd_Line.disable_help_str,
            'move-to-pos' : Simple_Step_Cmd_Line.move_to_pos_help_str,
            'move-by'     : Simple_Step_Cmd_Line.move_by_help_str,
            'ramp-to-pos' : Simple_Step_Cmd_Line.ramp_to_pos_help_str,
            'set-vel'     : Simple_Step_Cmd_Line.set_vel_help_str,
            'ramp-to-vel' : Simple_Step_Cmd_Line.ramp_to_vel_help_str,
            'zero'        : Simple_Step_Cmd_Line.zero_help_str,
            'help'        : Simple_Step_Cmd_Line.help_help_str,
            'set-ext-int' : Simple_Step_Cmd_Line.set_ext_int_help_str,
            'get-ext-int' : Simple_Step_Cmd_Line.get_ext_int_help_str,
            }

        # Set up option parser
        self.parser = optparse.OptionParser(usage=Simple_Step_Cmd_Line.usage)

        self.parser.add_option('-v', '--verbose',
                          action='store_true',
                          dest = 'verbose',
                          help = 'verbose mode - print additional information',
                          default = False)

        self.options, self.args = self.parser.parse_args()
        
        # Open device
        self.dev = Simple_Step()        
        atexit.register(self.atexit)
        return 

    def atexit(self):
        self.dev.close()

    def run_cmd(self):
        """
        Run specified command. If no commandis given print device
        values.
        """
        if len(self.args) == 0:
            self.print_vals()
        else:

            try:
                cmd_str = self.args[0]
            except IndexError:
                print "ERROR: no command argument"
                print 
                self.parser.print_help()
                sys.exit(1)

            try:
                cmd = self.cmd_table[cmd_str]
            except KeyError:
                print "ERROR: command, %s, not found"%(cmd_str,)
                print 
                self.parser.print_help()
                sys.exit(1)
            cmd()

    def dfu_mode(self):
        """
        Place device in programming mode
        """
        self.dev.enter_dfu_mode()

    def set_ext_int(self):
        """
        Enable/Disable external interupts
        """
        if len(self.args) < 2:
            print "ERROR: command 'set-ext-int' requires an argument"
            sys.exit(1)
        val = self.args[1]
        if not val.lower() in ('enabled','disabled'):
            try:
                val = int(val)
            except Exception, err:
                print "ERROR: unable to convert exteral interrupt value to integer,", err
                sys.exit(1)
        try:
            self.dev.set_ext_int(val)
        except Exception, err:
            print "ERROR: setting external interrupt, ", err
            sys.exit(1)

    def get_ext_int(self):
        """
        Return current external interrupt setting.
        """
        print self.dev.get_ext_int()

    def dio_hi(self):
        """
        Set DIO pin to logic high
        """
        if len(self.args) < 2:
            print "ERROR: command 'dio-hi' requires pin # argument"
            sys.exit(1)
        try:
            pin = int(self.args[1])
        except Exception, err:
            print "ERROR: unable to convert pin to integer, ", err
            sys.exit(1)
        try:
            self.dev.set_dio_lo(pin)
        except Exception, err:
            print "ERROR: setting dio, ", err
            sys.exit(1)

        self.dev.set_dio_hi(pin)
    
    def dio_lo(self):
        """
        Set DIO pin to logic low
        """
        if len(self.args) < 2:
            print "ERROR: command 'dio-hi' requires pin # argument"
            sys.exit(1)
        try:
            pin = int(self.args[1])
        except Exception, err:
            print "ERROR: unable to convert pin to integer, ", err
            sys.exit(1)
        try:
            self.dev.set_dio_lo(pin)
        except Exception, err:
            print "ERROR: setting dio, ", err
            sys.exit(1)
        
    def print_vals(self):
        """
        Print current device values
        """
        self.dev.print_values()
        print 
    
    def start(self):
        """
        Set device mode to running
        """
        self.dev.start()
        
    def stop(self):
        """
        Set device mode to stopped
        """
        self.dev.stop()

    def enable(self):
        """
        Enable stepper drive
        """
        self.dev.enable()
    
    def disable(self):
        """
        Disable stepper drive
        """
        self.dev.disable()
    
    def move_to_pos(self):
        """
        Perform point-to-point move
        """
        # Extract desired position
        if len(self.args) < 2:
            print "ERROR: position argument not given"
            sys.exit(1)
        
        pos = self.args[1]
        if pos[0] == 'n':
            pos = '-%s'%(pos[1:],)
        try:
            pos = int(pos)
        except ValueError:
            print 'ERROR: unable to convert position to integer'
            sys.exit(1)
        
        # Handle additional optional arguments
        vel = None

        if len(self.args) > 2:
            opt_args = get_opt_args(self.args[2:])
            vel = get_arg(opt_args, 'vel')
            
            # We should have no more optional arguments
            if len(opt_args)!=0:
                print "ERROR: unkown optional argument for command"
                for k,v in opt_args.iteritems():
                    print '%s = %s'%(k,v)
                sys.exit(1)

        # Perform point-to-point move
        self.dev.move_to_pos(pos,pos_vel=vel)

    def move_by(self):
        """
        Move motor by specified ammount
        """
        # Extract change in position
        if len(self.args) < 2:
            print "ERROR: change in position not given"
            sys.exit(1)
        dpos = self.args[1]
        if dpos[0] == 'n':
            dpos = '-%s'%(dpos[1:],)
        try:
            dpos = int(dpos)
        except ValueError:
            print "ERROR: unable to convert move amount to integer"
            sys.exit(1)

        # Handle optional arguments
        vel = None
        if len(self.args) > 2:
            opt_args = get_opt_args(self.args[2:])
            vel = get_arg(opt_args, 'vel')
            
            if len(opt_args)!=0:
                print "ERROR: unkown optional argument for command"
                for k,v in opt_args.iteritems():
                    print '%s = %s'%(k,v)
                sys.exit(1)
        
        # Perform move
        self.dev.move_by(dpos,pos_vel=vel)
        

    def ramp_to_pos(self):
        """
        Perform point-to-point move with velocity ramp
        """
        # Extract position argument
        if len(self.args) < 2:
            print "ERROR: position argument not given"
            sys.exit(1)
        pos = self.args[1]
        if pos[0] == 'n':
            pos = '-%s'%(pos[1:],)
        try:
            pos = int(pos)
        except ValueError:
            print 'ERROR: unable to convert position to integer'
            sys.exit(1)
        
        # Handle additional optional arguments
        vel = None
        accel = None
    
        if len(self.args) > 2:
            opt_args = get_opt_args(self.args[2:])
            vel = get_arg(opt_args,'vel')
            accel = get_arg(opt_args, 'accel')
            
            # We should have no more optional arguments
            if len(opt_args)!=0:
                print "ERROR: unkown optional argument for command"
                for k,v in opt_args.iteritems():
                    print '%s = %s'%(k,v)
                sys.exit(1)
        
        # If no acceleration given set accel to defualt
        if accel==None:
            accel = DEFAULT_ACCEL
        # Perform move
        self.dev.soft_ramp_to_pos(pos,accel,pos_vel=vel)
        

    def set_vel(self):
        """
        Set motor velocity
        """
        # Extract motor velocity
        if len(self.args) < 2:
            print "ERROR: velocity argument not given"
            sys.exit(1)
        vel = self.args[1]
        if vel[0] == 'n':
            vel = '-%s'%(vel[1:],)
        try:
            vel = int(vel)
        except ValueError:
            print "ERROR: unable to convert velocity to integer"
            sys.exit(1)
        
        # Get direction
        if vel > 0:
            direction = 'positive'
        else:
            direction = 'negative'
        vel = abs(vel)
        
        # Peform move
        self.dev.set_vel_and_dir(vel,direction)
        
        
    def ramp_to_vel(self):
        """
        Set motor velocity using ramp
        """
        # Extract motor velocity
        if len(self.args) < 2:
            print "ERROR: velocity argument not given"
            sys.exit(1)
        vel = self.args[1]
        if vel[0] == 'n':
            vel = '-%s'%(vel[1:],)
        try:
            vel = int(vel)
        except ValueError:
            print "ERROR: unable to convert velocity to integer"
            sys.exit(1)
        
        # Get direction
        if vel > 0:
            direction = 'positive'
        else:
            direction = 'negative'
        vel = abs(vel)

        # Handle optional arguments
        accel = None
        if len(self.args) > 2:
            opt_args = get_opt_args(self.args[2:])
            accel = get_arg(opt_args, 'accel')
            
            # We should have no more optional arguments
            if len(opt_args)!=0:
                print "ERROR: unkown optional argument for command"
                for k,v in opt_args.iteritems():
                    print '%s = %s'%(k,v)
                sys.exit(1)
            
        # If no acceleration given set accel to defualt
        if accel==None:
            accel = DEFAULT_ACCEL

        # Perform move
        self.dev.soft_ramp_to_vel(vel,direction,accel)
        

    def zero(self):
        """
        Set motor zero position
        """
        
        # Get position for zero - if none given use current position
        if len(self.args) < 2:
            pos = self.dev.get_pos()
        elif len(self.args) == 2:
            pos = self.args[1]
            if pos[0] == 'n':
                pos = '-%s'%(pos[1:],)
            try:
                pos = int(pos)
            except ValueError:
                print 'ERROR: unable to convert position to integer'
                sys.exit(1)
        
        # Zero motor
        self.dev.set_zero_pos(pos)
        

    def help(self):
        """
        Print help information
        """
        if len(self.args) == 1:
            self.parser.print_help()
        else:
            try:
                help_str = self.help_table[self.args[1]]
            except KeyError:
                print "ERROR: can't get help, command '%s' unkown"%(self.args[1],)
                print 
                print Simple_Step_Cmd_Line.help_help_str
                sys.exit(1)
            print help_str
            
        
    

    # Help strings ---------------------------------

    usage = """%prog [OPTION] command <arg0> <arg1> ...

%prog is a command line utility for controlling a stepper motor via USB.

Command Summary:
 
 dfu-mode       - place the at90usb device in programming mode
 dio-hi         - set DIO pin to logic high
 dio-lo         - set DIO pin to logic low
 disable        - disbale the stepper drive
 enable         - enable the stepper drive
 help           - get help 
 move-by        - move motor by the specified amount
 move-to_pos    - move motor to the specified position
 print-vals     - print current device values
 ramp-to-pos    - move motor to specified position using a ramp
 ramp-to-vel    - set motor velocity using a ramp
 set-vel        - set motor velocity 
 start          - start controller
 stop           - stop controller
 zero           - set the zero position of the motor
 set-ext-int    - enable/disable external interrupt
 get-ext-int    - get current external interrupt setting


* To get help for a specific command type: %prog help cmd.
* If no command is given the current device values are printed.
"""
    
    dfu_mode_help_str = """\
command: enter-dfu-mode

usage: simple-step dfu-mode

Places the Atmel at90usb device into programming mode. Note, usb
communication with the device will no longer be possible until device
is restarted.

Example:
 simple-step dfu-mode
"""

    set_ext_int_help_str = """\
command: set-ext-int

usage: simple-step set-ext-int value

Enables or disables external interrupts. Where value should be strings 
enable or disable strings  or integers 1 or 0.
"""

    get_ext_int_help_str = """\
command: get-ext-int

usage: simple-set get-ext-int

Returns the current external interrupt setting (enabled or disabled)
"""

    dio_hi_help_str = """\
command: dio-hi

usage: simple-step dio-hi pin

Set DIO pin to logic high. DIO pin must be in range 0-7.
"""

    dio_lo_help_str = """\
command: dio-lo

usage: simple-step dio-lo pin

Set DIO pin to logic low. DIO pin must be in range 0-7.
"""

    print_vals_help_str = """\
command: print-vals

usage: simple-step print-vals

Prints current device values to standard output.

Example:
 simple-step print-vals
"""
    start_help_str = """\
command: start

usage: simple-step start

Starts motor controller - sets motor controller's mode to 'running'.

Example:
 simple-step start
"""
    stop_help_str = """\
commmand: stop

usage: simple-step stop

Stops motor controller - sets motor controller's mode to 'stopped'.

Example:
 simple-step stop
"""
    enable_help_str = """\
command: enable

usage: simple-step enable

Enables stepper motor drive by setting the enable pin high.

Example:
 simple-step enable
"""
    disable_help_str = """\
command: disable

usgae: simple-step disable

Disables stepper motor drive by setting the enable pin low.

Example:
 simple-step disable
"""
    move_to_pos_help_str = """\
command: move-to-pos

usage: simple-step move-to-pos pos [vel=velocity]

Peform a point-to-point move from current position to pos. Negative
positions are specified by placing a 'n' infront of the position,
pos. The optional argument vel can be used to set the positioning
velocity.

Examples:

 simple-step move-to-pos 1000       # move to position 1000
 simple-step move-to-pos n500       # move to position -500

 # move to position 0 w/ velocity of  1000 ind/sec
 simple-step move-to-pos 0 vel=1000 

"""
    move_by_help_str = """\
command: move-by

usage: simple-step move-by dpos [vel=velocity]

Move motor by amount dpos. Negative position changes are specified by
placing an 'n' in front of the change in position, dpos. The optional
argument vel can be used to set the positioning velocity.

Examples:

 simple-step move-by 100           # move 100 indicies 
 simple-step move-by n500          # move -500 indicies 

 # move 200 ind w/ velocity of 1000 ind/sec 
 simple-step move-by 200 vel=1000  
                                  
"""
    ramp_to_pos_help_str = """\
command: ramp-to-pos

usage: simple-step ramp-to-pos pos [accel=acceleration] [vel=velocity] 

Peform a point-to-point move from current position to pos using a
ramp. Negative positions are specified by placing a 'n' infront of the
position, pos. The optional arguments accel and vel can be used to set
the acceleration and positioning velocity respectively. If the acceleration
is not specified than the default values is used.

Examples:
 
 simple-step ramp-to-pos 100             # move to position 100 
 simple-step ramp-to-pos n200            # move to position -200
 simple-step ramp-to-pos 500 accel=10000 # move to position 500 w/ 
                                         # acceleration 10000 ind/sec**2

 simple-step ramp-to-pos 330 vel=15000   # move to position 330 w/ 
                                         # velocity 1500 ind/sec 

# move to positon 110, accel=50000 ind/sec**2, vel= 20000 ind/sec
 simple-step ramp-to-pos 110 accel=50000 vel=20000  
"""
    set_vel_help_str = """\
command: set-vel

usage: simple-step set-vel vel

Set motor velocity to vel. Negative velocities are specified by
placing a 'n' in from of the velocity, vel. 

Examples:
 simple-step set-vel 100  # set velocity to 100 ind/sec
 simple-step set-vel n200 # set velocity to -200 ind/sec
"""
    ramp_to_vel_help_str = """\
command: ramp-to-vel

usage: simple-step ramp-to-vel vel [accel=acceleration]

Set motor velocity to vel using a ramp. Negative velocities are
specified by placing an 'n' in front of the velocity vel. The optional
argument vel can be used to set the positioning velocity.

Examples:

 simple-step ramp-to-vel 100  # set velocity to 100 ind/sec 
 simple-step ramp-to-vel n200 # set velocity to -200 ind/sec

 # set velocity to 100 ind/sec w/ acceleration 1000 ind/sec**2
 simple-step ramp-to-vel 100 accel=1000 

"""
    zero_help_str = """\
command: zero

usage: simple-step zero [pos]

Sets the motor zero position. If no argument is given then the current
position is set to zero. If an argument, pos, is given then pos is set
to the zero position. Negative numbers are specified by placing an 'n'
in front of the position [pos].

Examples:
 simple-step zero      # Set the current position to zero
 simple-step zero 100  # Set the position pos to zero
"""
    help_help_str = """\
command: help

usage: simple-step help [cmd]

Prints help information. If no cmd is given then general help
information is printed. If a command is specified then help for that
command is given.

Example:
 simple-step help          # prints general help information
 simple-step help move-by  # prints help for the move-by command 
"""


def get_arg(opt_args, arg_str):
    """
    Get optional argument from opt_args dictionary.
    """
    arg_val = None
    try:
        arg_val = opt_args[arg_str]
        opt_args.pop(arg_str)
    except KeyError:
        return         
    
    # Is vel negative
    if arg_val[0] == 'n':
        print "ERROR: optional argumen vel must be greater than zero"
        sys.exit(1)

    # Convert to integer
    try:
        arg_val = int(arg_val)
    except:
        print "ERROR: unable to convert vel to integer"
        sys.exit(1)
        
    return arg_val

def get_opt_args(arg_list):
    """
    Get optional arguments given to this command
    """
    arg_dict = {}
    for arg in arg_list:
        arg_split = arg.split('=')
        if len(arg_split) != 2 or arg_split[1]=='':
            print "ERROR: incorrent optional argument, '%s'"%(arg,)
            sys.exit(1)
        arg_dict[arg_split[0].lower()] = arg_split[1]
    return arg_dict


def cmd_line_main():
    cmd_line = Simple_Step_Cmd_Line()
    cmd_line.run_cmd()




