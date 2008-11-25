#!/usr/bin/env python
#
# simple_step.py 
#
# William Dickson 
# --------------------------------------------------------------------------- 
import pylibusb as usb
import ctypes
import sys
import time
import math
import struct

def swap_dict(in_dict):
    """
    Swap key and values in dictionary
    """
    return dict([(v,k) for k,v in in_dict.iteritems()])

DEBUG = False
INT32_MAX = (2**32-1)/2

# USB parameters
USB_VENDOR_ID = 0x1781 
USB_PRODUCT_ID = 0x0BB0
USB_BULKOUT_EP_ADDRESS = 0x01
USB_BULKIN_EP_ADDRESS = 0x82
USB_BUFFER_SIZE = 8

# USB Command IDs
USB_CMD_GET_POS = 0
USB_CMD_SET_POS_SETPT = 1
USB_CMD_GET_POS_SETPT = 2
USB_CMD_SET_VEL_SETPT = 3
USB_CMD_GET_VEL_SETPT = 4
USB_CMD_GET_VEL = 5
USB_CMD_SET_DIR_SETPT = 6
USB_CMD_GET_DIR_SETPT = 7
USB_CMD_SET_MODE = 8
USB_CMD_GET_MODE = 9
USB_CMD_SET_POS_VEL = 10
USB_CMD_GET_POS_VEL = 11
USB_CMD_GET_POS_ERR = 12
USB_CMD_SET_ZERO_POS = 13
USB_CMD_GET_MAX_VEL = 14
USB_CMD_GET_MIN_VEL = 15
USB_CMD_GET_STATUS = 16
USB_CMD_SET_STATUS = 17
USB_CMD_GET_DIR = 18
USB_CMD_AVR_RESET = 200
USB_CMD_AVR_DFU_MODE = 201
USB_CMD_TEST = 251

# Control values
USB_CTL_UINT8 = 0
USB_CTL_UINT16 = 1
USB_CTL_INT32 = 2

# Integer values for opertaing modes - usb in usb set/get
VELOCITY_MODE = 0
POSITION_MODE = 1

# Integer values for dircetions - used in usb set/get
POSITIVE = 0
NEGATIVE = 1

# Status C0nstants
RUNNING = 1
STOPPED = 0

# Mapping from mode strings to integer values
MODE2VAL_DICT = {
    'velocity' : VELOCITY_MODE,
    'position' : POSITION_MODE,
}
VAL2MODE_DICT = swap_dict(MODE2VAL_DICT)

# Mapping from direction strings to values
DIR2VAL_DICT = {
    'positive' : POSITIVE,
    'negative' : NEGATIVE,
    }
VAL2DIR_DICT = swap_dict(DIR2VAL_DICT)

# Dictionary of value types for set commands
SET_TYPE_DICT = {
    USB_CMD_SET_POS_SETPT : 'int32',
    USB_CMD_SET_VEL_SETPT : 'uint16',
    USB_CMD_SET_DIR_SETPT : 'uint8',
    USB_CMD_SET_MODE : 'uint8',
    USB_CMD_SET_POS_VEL : 'uint16',
    USB_CMD_SET_ZERO_POS : 'int32',
    USB_CMD_SET_STATUS : 'uint8',
    USB_CMD_TEST: 'uint8',
    }

# Dictionary from type to USB_CTL values
TYPE2USB_CTL_DICT = {
    'uint8' : USB_CTL_UINT8,
    'uint16' : USB_CTL_UINT16,
    'int32' : USB_CTL_INT32,
    }
USB_CTL2TYPE_DICT = swap_dict(TYPE2USB_CTL_DICT)

# Dictionary of status integets to strings 
STATUS2VAL_DICT = {
    RUNNING : 'running',
    STOPPED : 'stopped',
}
VAL2STATUS_DICT = swap_dict(STATUS2VAL_DICT)

def debug(val):
    if DEBUG==True:
        print >> sys.stderr, val

def debug_print(msg, comma=False):
    if DEBUG==True:
        if comma==True:
            print msg, 
        else:
            print msg
        sys.stdout.flush()

class Simple_Step:

    """
    USB communications interface to the at90usb based stepper motor 
    controller board.
    """

    def __init__(self):
        usb.init()
        
        # Get usb busses
        if not usb.get_busses():
            usb.find_busses()            
            usb.find_devices()
        busses = usb.get_busses()

        # Find device by IDs
        found = False
        for bus in busses:
            for dev in bus.devices:
                if (dev.descriptor.idVendor == USB_VENDOR_ID and
                    dev.descriptor.idProduct == USB_PRODUCT_ID):
                    found = True
                    break
            if found:
                break
        if not found:
            raise RuntimeError("Cannot find device.")

        self.libusb_handle = usb.open(dev)
        
        interface_nr = 0
        if hasattr(usb,'get_driver_np'):
            # non-portable libusb function available
            name = usb.get_driver_np(self.libusb_handle,interface_nr)
            if name != '':
                debug("attached to kernel driver '%s', detaching."%name )
                usb.detach_kernel_driver_np(self.libusb_handle,interface_nr)


        if dev.descriptor.bNumConfigurations > 1:
            debug("WARNING: more than one configuration, choosing first")
        
        usb.set_configuration(self.libusb_handle, dev.config[0].bConfigurationValue)
        usb.claim_interface(self.libusb_handle, interface_nr)
        
        self.output_buffer = ctypes.create_string_buffer(USB_BUFFER_SIZE)
        self.input_buffer = ctypes.create_string_buffer(USB_BUFFER_SIZE)
        for i in range(USB_BUFFER_SIZE):
            self.output_buffer[i] = chr(0x00)
            self.input_buffer[i] = chr(0x00)
        
        # Get max and min velocities
        self.max_vel = self.get_max_vel()
        self.min_vel = self.get_min_vel()
            
    def close(self):
        """
        Close usb device.
        """
        ret = usb.close(self.libusb_handle)

    # -------------------------------------------------------------------------
    # Methods for low level USB communication 
        
    def __send_and_receive(self,in_timeout=1000,out_timeout=9999):
        """
        Send bulkout and and receive bulkin as a response
        Note, probably want to and a max count so this will 
        timeout if al lof the reads fail.
        """
        done = False
        while not done:
            val = self.__send_output(timeout=out_timeout)
            data = self.__read_input(timeout=in_timeout)
            if data == None:
                debug_print('usb SR: fail', comma=False) 
                sys.stdout.flush()
                continue
            else:
                done = True
                debug_print('usb SR cmd_id: %d'%(ord(data[0]),), comma=False) 
        return data

    def __send_output(self,timeout=9999):
        buf = self.output_buffer # shorthand
        val = usb.bulk_write(self.libusb_handle, USB_BULKOUT_EP_ADDRESS, buf, timeout)
        return val

    def __read_input(self, timeout=1000):
        buf = self.input_buffer
        try:
            val = usb.bulk_read(self.libusb_handle, USB_BULKIN_EP_ADDRESS, buf, timeout)
            #print 'read', [ord(b) for b in buf]
            data = [x for x in buf]
        except usb.USBNoDataAvailableError:
            data = None
        return data

    def __get_usb_header(self,data):
        """
        Get header from usb data. Header consists of the command id and 
        the control byte. 
        """
        cmd_id = self.__bytes_to_int(data[0:1],'uint8')
        ctl_byte = self.__bytes_to_int(data[1:2],'uint8')
        return cmd_id, ctl_byte
        
    def __get_usb_value(self,ctl_byte,data):
        """
        Get the value sent from usb data.
        """
        return self.__bytes_to_int(data[2:], USB_CTL2TYPE_DICT[ctl_byte])
        
    def __int_to_bytes(self,val,int_type):
        """
        Convert integer value to bytes based on type. 
        """
        int_type = int_type.lower()
        if int_type == 'uint8':
            bytes = [chr(val&0xFF)]
        elif int_type == 'uint16':
            bytes = [chr(val&0xFF), chr((val&0xFF00)>>8)]
        elif int_type == 'int32':
            bytes = [chr((val&0xFF)),
                     chr((val&0xFF00) >> 8),
                     chr((val&0xFF0000) >> 16),
                     chr((val&0xFF000000) >> 24),]
        else:
            raise ValueError, "unknown int_type %s"%(int_type,)
        return bytes
        
    def __bytes_to_int(self,bytes,int_type):
        """
        Convert sequence of  bytes to intN or uintN based on the type
        specifier.
        """
        int_type = int_type.lower()
        if int_type == 'uint8':
            # This is unsigned 8 bit integer
            val = ord(bytes[0])
        elif int_type == 'uint16':
            # This is unsgned 16 bit integer
            val = ord(bytes[0]) 
            val += ord(bytes[1]) << 8
        elif int_type == 'int32':
            # This is signed 32 bit integer
            val = ord(bytes[0]) 
            val += ord(bytes[1]) << 8
            val += ord(bytes[2]) << 16
            val += ord(bytes[3]) << 24
            if val > INT32_MAX:
                # Reverse twos complement fot negatives
                val = val - 2**32
        else:
            raise ValueError, "unknown int_type %s"%(int_type,)
        return val


    def usb_set_cmd(self,cmd_id,val):
        """
        Generic usb set command. Sends set command w/ value to device
        and extracts the value returned

        Example:
        
        pos_vel= dev.usb_set_cmd(USB_SET_POS_VEL, pos_vel)

        """
        # Get value type from CMD_ID and convert to CTL_VAL
        val_type = SET_TYPE_DICT[cmd_id]
    
        # Send command + value and receive data
        self.output_buffer[0] = chr(cmd_id%0x100)
        ctl_val = TYPE2USB_CTL_DICT[val_type]
        self.output_buffer[1] = chr(ctl_val%0x100)
        val_bytes = self.__int_to_bytes(val,val_type)
        for i,byte in enumerate(val_bytes):
            self.output_buffer[i+2] = byte
        data = self.__send_and_receive()

        # Extract returned data
        cmd_id_received, ctl_byte = self.__get_usb_header(data)
        check_cmd_id(cmd_id, cmd_id_received)
        val = self.__get_usb_value(ctl_byte, data)
        return val        

    def usb_get_cmd(self,cmd_id):
        """
        Generic usb get command. Sends usb get command to device 
        w/ specified command id and extracts the value returned.

        Example:
        
        pos = dev.usb_get_cmd(USB_CMD_GET_POS)

        """
        # Send command and receive data
        self.output_buffer[0] = chr(cmd_id%0x100)
        data = self.__send_and_receive()
        # Extract returned data
        cmd_id_received, ctl_byte = self.__get_usb_header(data)
        check_cmd_id(cmd_id, cmd_id_received)
        val = self.__get_usb_value(ctl_byte, data)
        return val

    # -----------------------------------------------------------------
    # Methods for USB Commands specified  by command IDs

    def enter_dfu_mode(self):
        """
        Places the at90usb device in programming mode for upgrading the 
        firmware.
        """
        self.output_buffer[0] = chr(USB_CMD_AVR_DFU_MODE%0x100)
        val = self.__send_output()
        return

    def reset_device(self):
        """
        Resets the at90usb device.
        """
        pass

    def get_pos(self):
        """
        Returns the current motor position.
        """
        pos = self.usb_get_cmd(USB_CMD_GET_POS)
        return pos

    def set_pos_setpt(self,pos_setpt):
        """
        Sets the motor position set-point in indices. The motor will
        track that position set-point when the device is in position
        mode.
        
        Argument:
          pos_setpt = position set-point value (indices)
          
        Return: position set-point
        """
        try:
            pos_setpt = int(pos_setpt)
        except:
            raise ValueError, "unable to convert pos_setpt to integer"
        pos_setpt = int(pos_setpt)
        pos_setpt = self.usb_set_cmd(USB_CMD_SET_POS_SETPT,pos_setpt)
        return pos_setpt
    
    def get_pos_setpt(self):
        """
        Returns the current motor position set-point in indices.
        """
        set_pt = self.usb_get_cmd(USB_CMD_GET_POS_SETPT)
        return set_pt

    def set_vel_setpt(self,vel_setpt):
        """
        Sets the motor velocity set-point in indices/sec.  The velocity 
        is always nonnegative - the direction of rotation is determined
        by setting the direction value. The motor will spin at this
        velocity in the set direction (see the get_dir and set_dir
        commands) when the device is in velocity mode.  Trying to set
        the motor velocity to a value greater then maximum velocity 
        result in the velocity being set to the maximum velocity.
        
        Argument: 
          vel_setpt = the motor velocity (indices/sec),  always >= 0
        
        Return: the actual motor velocity obtained indice/sec. 
        """
        try:
            vel_setpt = int(vel_setpt)
        except:
            raise ValueError, "unable to convert vel_setpt to integer"
        if vel_setpt < 0:
            raise ValueError, "vel_sept must be >= 0"

        # Send usb command
        vel_setpt = self.usb_set_cmd(USB_CMD_SET_VEL_SETPT,vel_setpt)
        return vel_setpt

    def get_vel_setpt(self):
        """
        Returns the motors current velocity set-point in indices/sec. 
        Note, this is  always a positive number. The direction of rotation 
        is determined by the direction value.
        """
        vel_setpt = self.usb_get_cmd(USB_CMD_GET_VEL_SETPT)
        return vel_setpt

    def get_vel(self):
        """
        Returns the motors current velocity in indices/second. 
        """
        vel = self.usb_get_cmd(USB_CMD_GET_VEL)
        return vel
        
    def set_dir_setpt(self,dir_setpt):
        """
        Sets the set-point motor rotation direction used when the device
        is in velocity mode. The value can be set using the strings 
        'positive'/'negative' or by using the the integer values 
        POSITIVE/NEGATIVE. 

        Argument: 

          dir = the set-point motor rotation direction either strings 
          ('positive'/'negative') or integers (POSITIVE or NEGATIVE)
          
        Return: the motor rotation direction set-point
        """
        # If direction is string convert to integer direction value
        if type(dir_setpt) == str:
            try:
                dir_setpt_val = DIR2VAL_DICT[dir_setpt.lower()]
            except:
                raise ValueError, "unkown dir_setpt string '%s'"%(dir_setpt,)
        else:
            try:
                dir_setpt_val = int(dir_setpt)
            except:
                raise ValueError, "dir_setpt not string and unable to convert to int"
            if not (dir_setpt_val in (POSITIVE,NEGATIVE)):
                err_msg  = "dir_setpt integer must be either %d or %d"%(POSITIVE,NEGATIVE)
                raise ValueError, err_msg
                       
        # Send usb command
        dir_setpt_val = self.usb_set_cmd(USB_CMD_SET_DIR_SETPT,dir_setpt_val)

        # If input direction is a string we return a string 
        if type(dir_setpt) == str:
            return VAL2DIR_DICT[dir_setpt_val]
        else:
            return dir_setpt_val
        
    def get_dir_setpt(self,ret_type = 'str'):
        """
        Returns the set-point motor rotation direction used in
        velocity mode.  The return values can be strings ('positive',
        'negative') or integer values (POSITIVE, NEGATIVE) depending
        on the keyword argument ret_type. Note, the direction can only
        be set when the device is in velocity mode.
        
        Keywords:
          ret_type = 'str' or 'int'

        Return: the set-point motor rotation direction.
        """

        dir_setpt_val = self.usb_get_cmd(USB_CMD_GET_DIR_SETPT)
        if ret_type == 'int':
            return dir_setpt_val
        else:
            return VAL2DIR_DICT[dir_setpt_val] 
    
    def set_mode(self,mode):
        """
        Sets the at90usb device operating mode. There are two possible
        operating modes: velocity and posistion. In velocity mode the
        motor will spin and the set velocity in the set direction. In
        position mode the motor will track the position set-point.
        
        Argument: 
          mode = the operating mode. Can be set using the the strings 
                 ('position'/'velocity') or the integers (POSITION_MODE, 
                 VELOCITY_MODE)

        Return: operating mode
        """
        # If mode is string convert to integer value 
        if type(mode) == str:
            try:
                mode_val = MODE2VAL_DICT[mode.lower()]
            except:
                raise ValueError, "unknown mode '%s'"%(mode,)
        else:
            try:
                mode_val = int(mode)
            except:
                raise ValueError, "unable to convert mode to integer value"
            if not (mode_val in (POSITION_MODE,VELOCITY_MODE)):
                raise ValueError, "unknown mode integer %d"%(mode_val,)

        # Send usb commmand
        mode_val = self.usb_set_cmd(USB_CMD_SET_MODE,mode_val)

        # If input mode is a string we return a string
        if type(mode) == str:
            return VAL2MODE_DICT[mode_val]
        else:
            return mode_val

    def get_mode(self,ret_type = 'str'):
        """
        Returns the current operating mode of the at90usb device. 
        Return values can be either strings for integer values based
        on the keyword argument ret_type.
        
        Keywords:
          ret_type = set the type of the return values either 'str' or 'int'

        Return: operating mode

        """
        mode_val = self.usb_get_cmd(USB_CMD_GET_MODE)
        if ret_type == 'int':
            return mode_val
        else:
            return VAL2MODE_DICT[mode_val]
            
    def set_pos_vel(self,pos_vel):
        """
        Sets the positioning velocity for the device in indices/sec. This
        will be the velocity used for moving the motor when the device
        is in position mode. 

        Arguments:
          pos_vel = positioning velocity l(indices/sec), always >= 0

        Return:  the current positioning velocity. 
        """
        try:
            pos_vel = int(pos_vel)
        except:
            raise ValueError, "unable to convert pos_vel to integer"
        if pos_vel < 0:
            raise ValueError, "pos_vel must be >= 0"

        # Send usb command
        pos_vel = self.usb_set_cmd(USB_CMD_SET_POS_VEL,pos_vel)
        return pos_vel

    def get_pos_vel(self):
        """
        Returns the positioning velocity in indices/sec.
        """
        pos_vel = self.usb_get_cmd(USB_CMD_GET_POS_VEL)
        return pos_vel

    def get_pos_err(self):
        """
        Returns the position error in indices- the difference bewteen
        the position set-point and the current position. When the
        device is in position mode it will try to drive the position
        error to zero.
        
        Return: current position error (indices)
        """
        pos_err = self.usb_get_cmd(USB_CMD_GET_POS_ERR)
        return pos_err
    
    def set_zero_pos(self,zero_pos):
        """
        Sets the position zero of the motor to the given value in
        indices.  

        Argument:
          zero_pos = the desired zero position for the motor (indices)

        Return: 0

        Example: sets the current position of the motor to zero.
        
        cur_pos = dev.get_pos()
        dev.set_pos_zero(cur_pos)
        """
        try:
            zerp_pos = int(zero_pos)
        except:
            raise ValueError, "unable to convert zero_pos to integer value"
        
        # Send usb command
        zero_pos = self.usb_set_cmd(USB_CMD_SET_ZERO_POS,zero_pos)
        return zero_pos

    def get_max_vel(self):
        """
        Returns the maximum allowed velocity in indices/sec to the
        nearest integer value.
        """
        max_vel = self.usb_get_cmd(USB_CMD_GET_MAX_VEL)
        return max_vel

    def get_min_vel(self):
        """
        Returns the minium allowed velocity in indices/sec to the
        nearest integer value.
        """
        min_vel = self.usb_get_cmd(USB_CMD_GET_MIN_VEL)
        return min_vel

    def get_status(self,ret_type='str'):
        """
        Returns the device status. 
        
        keywords:
          ret_type = sets the return type 'str' or 'int' 

        Return: 'running' or 'stopped' if ret_type = 'str'
                 RUNNING  or  STOPPED  if ret_type = 'int' 
        """
        status_val = self.usb_get_cmd(USB_CMD_GET_STATUS)
        if ret_type == 'str':
            return STATUS2VAL_DICT[status_val]
        else:
            return status_val

    def set_status(self, status):
        """
        Sets the device status. 

        Argument:
          status = device status either 'running'/'stopped' or
                   RUNNING/STOPPED.

        Return: device status
        """
        if type(status) == str:
            try:
                status_val = VAL2STATUS_DICT[status.lower()]
            except:
                raise ValueError, "unknown status string %s"%(status,)
        else:
            try:
                status_val = int(status)
            except:
                raise ValueError, "unable to convert status to integer"
            if not (status_val in (RUNNING,STOPPED)):
                raise ValueError, "unknown status integer %d"%(status_val,)
        
        # Send usb command
        status_val = self.usb_set_cmd(USB_CMD_SET_STATUS,status_val)
        if type(status) == str:
            return STATUS2VAL_DICT[status_val]
        else:
            return status_val

    def start(self):
        """
        Starts the device - sets system status to running.
        """
        self.set_status('running')
    
    def stop(self):
        """
        Stops the device - sets system status to stop.
        """
        self.set_status('stopped')


    def get_dir(self,ret_type='str'):
        """
        Gets the current motor direction. Can return either a string value
        ("positive"/"negative") or an integer value (POSITIVE/NEGATIVE) 
        depending on the value of the keyword argument ret_type.
        """
        dir_val = self.usb_get_cmd(USB_CMD_GET_DIR)
        if ret_type == 'str':
            return VAL2DIR_DICT[dir_val]
        else:
            return dir_val
        
    def cmd_test(self):
        """
        Dummy usb command for debugging.
        """
        val = self.usb_set_cmd(USB_CMD_TEST,1)
        return val

    # -------------------------------------------------------------------
    # High level methods

    def move_to_pos(self,pos,pos_vel=None):
        """
        Moves the stepper motor to specified position. The motor is
        placed in stopped and positioning mode before the move
        begins. After the move is complete the motor is stopped. The
        positioning velocity is specified by the keyword argument
        pos_vel. If pos_vel is equal to None (default) then half the
        maximum allowed motor velocity is used for the move.

        Arguments:
          pos = new motor position in indices 
          
        keywords:
          pos_vel = positioning velocity to use for move. Default = None. 
                    If pos_vel is equal to None then half the maximum allowed 
                    motor velocity is used for the move.
          
        Return: None
        """
        
        # Stop device and setting to positioning mode
        self.set_status('stopped')
        self.set_mode('position')

        # Set position set-point and positioning velocity
        if pos_vel == None:
            self.set_pos_vel(self.max_vel/2.0)
        else:
            self.set_pos_vel(pos_vel)
        self.set_pos_setpt(pos)
        
        # Perform move
        self.start()
        while abs(self.get_pos_err())!=0:
            time.sleep(0.1)

        # Stop device
        self.stop()
        return

        
        
    def move_by(self,pos,pos_vel=None):
        """
        Move the motor by the specified ammount. The motor is stopped
        and placed in positioning mode before the move begins. After
        the move is complete the move is stopped. The positioning
        velocity used for the move is specifed by the keyword argument
        pos_vel. If the pos_vel is equal to None (defualt) the half
        the maximum allowed velocity is used for the move.

        Arguments:
          pos = the size of the move
          
        keywords:
          pos_vel = the positioning velocioty for the move. Default=None.
                    If pos_vel is equal to None then half the maximum
                    allowed velocity is used for the move.
        
        Return: None
        """
        pos_cur = self.get_pos()
        pos_new = pos_cur + pos
        self.move_to_pos(pos_new,pos_vel=pos_vel)
        return


    def set_vel_and_dir(self,vel,dir):
        """
        Sets the velocity and direction of the motor. The motor is placed in 
        velocity mode if necessary. 
        """
        mode_cur = dev.get_mode()
        if mode_cur != 'velocity':
            self.set_status('stopped')
            self.set_mode('velocity')
        else:
            dir_cur = self.get_dir()
            if dir_cur != 'dir':
                self.set_status('stopped')
                dev.set_dir_setpt(dir)

        dev.set_vel_setpt(vel)
        dev.start()
        return


    def soft_ramp_to_vel(self,vel,accel):
        pass


    def soft_ramp_to_pos(self,pos,accel,pos_vel=None,N=100):
        """

        !!!!!!! Note: Not completed yet !!!!!!!

        Move to given position using a ramp trajectory. The ramp is
        generated in software on PC side by changing the pos_vel. Thus
        the timing of the accelerations during the ramp may not be
        perfect however it should help when driving inertial loads.
        
        """
        # Stop device, set to positioning mode and set position set-point 
        dev.set_status('stopped')
        dev.set_mode('position')
        dev.set_pos_setpt(pos)
        
        
        # Compute acceleration time and distance
        time_accel = float(pos_vel)/float(accel) 
        dist_accel = 0.5*float(accel)*time_accel**2
        dt = time_accel/float(N)
        
        # Getting start position
        pos_start = dev.get_pos()
        dist_total = pos - pos_start

        # Set intial velocity
        dev.set_pos_vel(int(accel*dt))
        dev.start()
        
        while abs(dev.get_pos_err()) != 0:
            pos_cur = dev.get_pos()
            dist_cur = pos - pos_start
            
            t = math.sqrt(2.0*float(pos - pos_start)/float(accel))
            N = round(t/dt)
            
            vel = N*accel
            

        # --------------------------------------------------------
        # DEBUG - not finished yet
        # --------------------------------------------------------
        
        
        
        return
        
    def print_values(self):
        """
        Prints the current device values 
        """
        print
        print ' system state'
        print ' '+ '-'*35
        print '   operating mode:', self.get_mode()
        print '   status:', self.get_status()
        print '   position:', self.get_pos()
        print '   velocity:', self.get_vel()
        print '   direction:', self.get_dir()
        print '   position error:', self.get_pos_err()
        print '   maximum velocity:', self.get_max_vel()
        print '   minimum velocity:', self.get_min_vel()
        
        print 
        print ' position mode settings'
        print ' ' + '-'*35
        print '   position set-point:', self.get_pos_setpt()
        print '   positioning velocity:', self.get_pos_vel()
        print 
        print ' velocity mode settings'
        print ' ' + '-'*35
        print '   velocity set-point:', self.get_vel_setpt()
        print '   direction set-point:', self.get_dir_setpt()
        
        
def check_cmd_id(expected_id,received_id):
    if not expected_id == received_id:
        msg = "received incorrect command ID %d expected %d"%(received_id,expected_id)
        raise IOError, msg

# -------------------------------------------------------------------------
if __name__=='__main__':

    # Some simple testing
    if 0:
        
        dev = Simple_Step()
        
        dev.set_mode('velocity')
        dev.set_dir_setpt('negative')
        dev.set_vel_setpt(15300)
        dev.start()
        dev.print_values()    
        dev.close()

        
    if 0:

        IND_PER_REV = 6400

        dev = Simple_Step()
        
        pos = dev.get_pos()
        dev.set_zero_pos(pos)
        dev.print_values()


        time.sleep(1.0)

        for i in range(0,16):
            dev.move_by(IND_PER_REV/8)
            dev.print_values()

        time.sleep(1.0)
            
        for i in range(0,8):
            dev.move_by(IND_PER_REV/4)
            dev.print_values()
        
        time.sleep(1.0)

            
        for i in range(0,4):
            dev.move_by(IND_PER_REV/2)
            dev.print_values()

        time.sleep(1.0)

        for i in range(0,2):
            dev.move_by(IND_PER_REV)
            dev.print_values()
            

        dev.close()
    
    if 0:
        
        pos_vel = 10000 
        dev = Simple_Step()

        # Set current position to zero position
        pos = dev.get_pos()
        dev.set_zero_pos(pos)
        
        
        vel = 1000
        dir = 'positive'
        t = 5.0
        print '%s move @ vel = %d for %1.2f sec'%(dir,vel,t,)
        dev.set_vel_and_dir(vel,dir)
        time.sleep(t)
        print 'returning to zero'
        dev.move_to_pos(0,pos_vel=pos_vel)
        
        vel = 5000
        dir = 'positive'
        t = 5.0
        print '%s move @ vel = %d for %1.2f sec'%(dir,vel,t,)
        dev.set_vel_and_dir(vel,dir)
        time.sleep(t)
        print 'returning to zero'
        dev.move_to_pos(0,pos_vel=pos_vel)

        dev.print_values()
        dev.stop()
        
    if 1:

        dev = Simple_Step()

        dev.set_mode('velocity')
        dev.set_dir_setpt('positive')
        dev.set_vel_setpt(0)
        dev.start()

        print 'increasing velocity'
        for i in range(0,500):
            vel = i*100 + 100
            dev.set_vel_setpt(vel)
            time.sleep(0.01)

        print 'decreasing velocity'
        for i in range(500,0,-1):
            vel = i*100 - 100
            dev.set_vel_setpt(vel)
            time.sleep(0.01)
        
            
        dev.stop()
        dev.print_values()
        dev.close()
