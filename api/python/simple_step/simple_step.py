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

Purpose: Provides and API for the at90usb based stepper motor
controller. 

Author: William Dickson 

------------------------------------------------------------------------
"""
import pylibusb as usb
import ctypes
import sys
import time
import math
import struct

def swap_dict(in_dict):
    """
    Swap key and values in dictionary
    
    Arguments:
      in_dict = input dictionary
      
    Return: dictionary w/ keys and values swapped.
    """
    return dict([(v,k) for k,v in in_dict.iteritems()])


# Constants
# ------------------------------------------------------------------
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
USB_CMD_SET_ENABLE = 19
USB_CMD_GET_ENABLE = 20
USB_CMD_SET_DIO_HI=21
USB_CMD_SET_DIO_LO=22
USB_CMD_GET_EXT_INT=23
USB_CMD_SET_EXT_INT=24
USB_CMD_AVR_RESET = 200
USB_CMD_AVR_DFU_MODE = 201
USB_CMD_TEST = 251

# Control values for bulk in packets
USB_CTL_UINT8 = 0
USB_CTL_UINT16 = 1
USB_CTL_INT32 = 2

# Control values for bulk out packets
USB_CTL_UPDATE = 200
USB_CTL_NO_UPDATE = 201

# Integer values for opertaing modes - usb in usb set/get
VELOCITY_MODE = 0
POSITION_MODE = 1

# Integer values for dircetions - used in usb set/get
POSITIVE = 0
NEGATIVE = 1

# Status Constants
RUNNING = 1
STOPPED = 0

# Enable Constants
ENABLED = 1
DISABLED = 0

# Mapping for enable strings to integer values
ENABLE2VAL_DICT = {
    'enabled'  : ENABLED,
    'disabled' : DISABLED,
}
VAL2ENABLE_DICT = swap_dict(ENABLE2VAL_DICT)

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
    USB_CMD_SET_ENABLE: 'uint8',
    USB_CMD_SET_DIO_HI : 'uint8',
    USB_CMD_SET_DIO_LO : 'uint8',
    USB_CMD_SET_EXT_INT : 'uint8',
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
    'running' : RUNNING,
    'stopped' : STOPPED,
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
    USB interface to the at90usb based stepper motor controller board.
    """

    def __init__(self,serial_number=None):
        """
        Open and initialize usb device.
        
        Arguments: None
        
        Return: None.
        """
        usb.init()

        #usb.set_debug(3)
        
        # Get usb busses
        if not usb.get_busses():
            usb.find_busses()            
            usb.find_devices()
        busses = usb.get_busses()

        # Find device by IDs
        found = False
        dev_list = []
        for bus in busses:
            for dev in bus.devices:
                if (dev.descriptor.idVendor == USB_VENDOR_ID and
                    dev.descriptor.idProduct == USB_PRODUCT_ID):
                    dev_list.append(dev)
                    found = True
                    #break
            #if found:
            #    break
        if not found:
            raise RuntimeError("Cannot find device.")

        if serial_number == None:
            # No serial number specified - take first device
            dev = dev_list[0]
            self.libusb_handle = usb.open(dev)
            self.dev = dev
        else:
            # Try and find device with specified serial number
            found = False
            for dev in dev_list:
                self.dev = dev
                self.libusb_handle = usb.open(dev)
                sn = self.get_serial_number()
                if sn == serial_number:
                    found = True
                    break
                else:
                    ret = usb.close(self.libusb_handle)
            if not found:
                raise RuntimeError("Cannot find device w/ serial number %s."%(serial_number,))

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
        
        Arguments: None
        
        Return: None
        """
        ret = usb.close(self.libusb_handle)
        return

    # -------------------------------------------------------------------------
    # Methods for low level USB communication 
        
    def __send_and_receive(self,in_timeout=200,out_timeout=9999):
        """
        Send bulkout and and receive bulkin as a response.
        
        Arguments: None
        
        Keywords: 
          in_timeout  = bulkin timeout in ms
          out_timeout = bilkin timeout in ms
          
        Return: the data returned by the usb device.
        """
        done = False
        while not done:
            val = self.__send_output(timeout=out_timeout)
            if val < 0 :
                raise IOError, "error sending usb output"

            # DEBUG: sometimes get no data here. I Reduced the timeout to 200 
            # which makes problem less apparent, but doesn't get rod out it. 
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
        """
        Send output data to the usb device.
        
        Arguments: None
        
        Keywords:
          timeout = the timeout in ms
          
        Return: number of bytes written on success or < 0 on error.
        """
        buf = self.output_buffer # shorthand
        val = usb.bulk_write(self.libusb_handle, USB_BULKOUT_EP_ADDRESS, buf, timeout)
        return val

    def __read_input(self, timeout=1000):
        """
        Read input data from the usb device.
        
        Arguments: None
        
        Keywords:
          timeout = the timeout in ms
          
        Return: the raw data read from the usb device.
        """
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
        Get header from returned usb data. Header consists of the command id and 
        the control byte. 
        
        Arguments:
          data = the returned usb data
          
        Return: (cmd_id, ctl_byte)
                 cmd_id   = the usb header command id
                 ctl_byte = the usb header control byte 
        """
        cmd_id = self.__bytes_to_int(data[0:1],'uint8')
        ctl_byte = self.__bytes_to_int(data[1:2],'uint8')
        return cmd_id, ctl_byte
        
    def __get_usb_value(self,ctl_byte,data):
        """
        Get the value sent from usb data.
        
        Arguments:
          ctl_byte = the returned control byte
          data     = the returned data buffer
          
        Return: the value return by the usb device.
        """
        return self.__bytes_to_int(data[2:], USB_CTL2TYPE_DICT[ctl_byte])
        
    def __int_to_bytes(self,val,int_type):
        """
        Convert integer value to bytes based on type specifier.

        Arguments:
          val      = the integer value to convert
          int_type = the integer type specifier
                     'uint8'  = unsigned 8 bit integer
                     'uint16' = unsigned 16 bit integer
                     'int32'  = signed 32 bit integer
                     
        Return: the integer converted to bytes.
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

        Arguments:
          bytes    = the bytes to convert
          int_type = the integer type specifier
                     'uint8'  = unsigned 8 bit integer
                     'uint16' = unsigned 16 bit integer
                     'int32'  = signed 32 bit integer
        
        Return: the integer value
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
                # Reverse twos complement for negatives
                val = val - 2**32
        else:
            raise ValueError, "unknown int_type %s"%(int_type,)
        return val


    def usb_set_cmd(self,cmd_id,val,io_update=True):
        """
        Generic usb set command. Sends set command w/ value to device
        and extracts the value returned

        Arguments:
          cmd_id = the integer command id for the usb command
          val    = the value to send to the usb device.
          
        Keywords:
          io_update = True or False. Determines whether or not thr 
                      change in value will have an immediate effect. 
                      The default value is True.

        """
        # Get value type from CMD_ID and convert to CTL_VAL
        val_type = SET_TYPE_DICT[cmd_id]
    
        # Send command + value and receive data
        self.output_buffer[0] = chr(cmd_id%0x100)
        if io_update == True:
            ctl_val = USB_CTL_UPDATE
        elif io_update == False:
            ctl_val = USB_CTL_NO_UPDATE
        else:
            raise ValueError, "io_update must be True or False"
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

        Arguments:
          cmd_id = the integer command id for usb command
          
        Return: the value returned fromt the usb device.
        """
        # Send command and receive data
        self.output_buffer[0] = chr(cmd_id%0x100)
        data = self.__send_and_receive()
        # Extract returned data
        cmd_id_received, ctl_byte = self.__get_usb_header(data)
        check_cmd_id(cmd_id, cmd_id_received)
        val = self.__get_usb_value(ctl_byte, data)
        return val

    def get_serial_number(self):
        """
        Get serial number of device.
        
        Arguments: None

        Return: serial number of device - a string
        """
        return  usb.get_string_simple(self.libusb_handle, self.dev.descriptor.iSerialNumber)

    def get_manufacturer(self):
        """
        Get manufacturer of device

        Arguments: None

        Return: manufacturer string
        """
        return usb.get_string_simple(self.libusb_handle, self.dev.descriptor.iManufacturer)

    def get_product(self):
        """
        Get decive product string

        Arguments: None

        Return: product string
        """
        return usb.get_string_simple(self.libusb_handle, self.dev.descriptor.iProduct)

    # -----------------------------------------------------------------
    # Methods for USB Commands specified  by command IDs

    def enter_dfu_mode(self):
        """
        Places the at90usb device in programming mode for upgrading the 
        firmware. Note, after entering dfu mode no further communications
        with the device will be possible.

        Arguments: None
        
        Return: None
        """
        self.output_buffer[0] = chr(USB_CMD_AVR_DFU_MODE%0x100)
        val = self.__send_output()
        return

    def reset_device(self):
        """
        Resets the at90usb device. Note, currently this function has
        some problems. First, after resetting the device no further
        usb communications with the device are possible. Second, after
        reset the device occasionally fails to enumerate correctly and
        the only way I have found which fixes this is to reset the linux
        usb system. It is probably best not to use this function. 

        Arguments: None
        
        Return: None
        """
        ###############################
        # DEBUG - has issues, see above
        ###############################

        self.output_buffer[0] = chr(USB_CMD_AVR_RESET%0x100)
        val = self.__send_output()        
        self.close()
        return

    def get_pos(self):
        """
        Returns the current motor position.
        
        Arguments: None

        Return: motor position. (indices)
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
          
        Return: position set-point. (indices)
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

        Arguments: None
        
        Return: motor position set-point. (indices)
        """
        set_pt = self.usb_get_cmd(USB_CMD_GET_POS_SETPT)
        return set_pt

    def set_vel_setpt(self,vel_setpt,io_update=True):
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
        
        Keywords:
          io_update = True (Default) or False. If true the change in 
                      parameter will have an immediate effect on the 
                      output of at90usb board. If False the change will 
                      will have an effect on the output only after the 
                      next command with io_update=True. io_update is 
                      implicitly True for all commands other then those
                      which exciplity have it as a keyword argument.
                      
        Return: the actual motor velocity obtained indices/sec. 
        """
        try:
            vel_setpt = int(vel_setpt)
        except:
            raise ValueError, "unable to convert vel_setpt to integer"
        if vel_setpt < 0:
            raise ValueError, "vel_sept must be >= 0"

        # Send usb command
        vel_setpt = self.usb_set_cmd(USB_CMD_SET_VEL_SETPT,
                                     vel_setpt,
                                     io_update=io_update)
        return vel_setpt

    def get_vel_setpt(self):
        """
        Returns the motors current velocity set-point in indices/sec. 
        Note, this is  always a positive number. The direction of rotation 
        is determined by the direction value.

        Arguments: None

        Return: the velocity set-point. (indices/sec)
        """
        vel_setpt = self.usb_get_cmd(USB_CMD_GET_VEL_SETPT)
        return vel_setpt

    def get_vel(self):
        """
        Returns the motor's current velocity in indices/sec. 

        Arguments: None

        Return: current motor velocity. (indices/sec)
        """
        vel = self.usb_get_cmd(USB_CMD_GET_VEL)
        return vel
        
    def set_dir_setpt(self,dir_setpt,io_update=True):
        """
        Sets the set-point motor rotation direction used when the device
        is in velocity mode. The value can be set using the strings, 
        'positive'/'negative', or by using the the integer values, 
        POSITIVE/NEGATIVE. 

        Argument: 

          dir = the set-point motor rotation direction either strings, 
                'positive'/'negative',  or integers, POSITIVE or NEGATIVE.


        Keywords:
          io_update = True (Default) or False. If true the change in 
                      parameter will have an immediate effect on the 
                      output of at90usb board. If False the change will 
                      will have an effect on the output only after the 
                      next command with io_update=True. io_update is 
                      implicitly True for all commands other then those
                      which exciplity have it as a keyword argument.
          
        Return: the motor rotation direction set-point
                'positive' or 'negative' if type(dir_setpt) == str
                 POSITIVE  or  NEGATIVE  if type(dir_setpt) == int 
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
        dir_setpt_val = self.usb_set_cmd(USB_CMD_SET_DIR_SETPT,
                                         dir_setpt_val,
                                         io_update=io_update)

        # If input direction is a string we return a string 
        if type(dir_setpt) == str:
            return VAL2DIR_DICT[dir_setpt_val]
        else:
            return dir_setpt_val
        
    def get_dir_setpt(self,ret_type='str'):
        """
        Returns the set-point motor rotation direction used in
        velocity mode.  The return values can be strings, 'positive'/
        'negative', or integer values, POSITIVE/NEGATIVE depending
        on the keyword argument ret_type. 
        
        Keywords:
          ret_type = 'str' or 'int'

        Return: the set-point motor rotation direction.
                'positive' or 'negative' if ret_type == 'str'
                 POSITIVE  or  NEGATIVE  if ret_type == 'int'
        """

        dir_setpt_val = self.usb_get_cmd(USB_CMD_GET_DIR_SETPT)
        if ret_type == 'int':
            return dir_setpt_val
        else:
            return VAL2DIR_DICT[dir_setpt_val] 
    
    def set_mode(self,mode):
        """
        Sets the at90usb device operating mode. There are two possible
        operating modes: velocity and position. In velocity mode the
        motor will spin and the set velocity in the set direction. In
        position mode the motor will track the position set-point.
        
        Argument: 
          mode = the operating mode. Can be set using the the strings, 
                 'position'/'velocity', or the integers, POSITION_MODE/ 
                 VELOCITY_MODE.

        Return: operating mode
                'position' or 'velocity' if type(mode)==str
                 POSITION  or  VELOCITY  if type(mode)==int
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
                'position' or 'velocity' if ret_type == 'str'
                 POSITION  or  VELOCITY  if ret_type == 'int'

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

        Return: the current positioning velocity (indices/sec). 
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
        
        Arguments: None
        
        Return: position velocity. (indices/sec)
        """
        pos_vel = self.usb_get_cmd(USB_CMD_GET_POS_VEL)
        return pos_vel

    def get_pos_err(self):
        """
        Returns the position error in indices. The position error is
        the difference bewteen the position set-point and the current
        position. When the device is in position mode it will try to
        drive the position error to zero.
        
        Arguments: None

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

        Return: 0 (indices)
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
        
        Arguments: None
        
        Return: The maximum allowed velocity. (indices/sec)
        """
        max_vel = self.usb_get_cmd(USB_CMD_GET_MAX_VEL)
        return max_vel

    def get_min_vel(self):
        """
        Returns the minium allowed velocity in indices/sec to the
        nearest integer value.

        Arguments: None
        
        Return: minimum allowed velocity. (indices/sec)
        """
        min_vel = self.usb_get_cmd(USB_CMD_GET_MIN_VEL)
        return min_vel

    def get_status(self,ret_type='str'):
        """
        Returns the device status. 
        
        Keywords:
          ret_type = sets the return type 'str' or 'int' 

        Return: 'running' or 'stopped' if ret_type = 'str'
                 RUNNING  or  STOPPED  if ret_type = 'int' 
        """
        status_val = self.usb_get_cmd(USB_CMD_GET_STATUS)
        if ret_type == 'str':
            return VAL2STATUS_DICT[status_val]
        else:
            return status_val

    def set_status(self, status):
        """
        Sets the device status. 

        Argument:
          status = the device status either a string, 'running'/'stopped',
                   or an integer,RUNNING/STOPPED.

        Return: the new device status. 
                'running' or 'stopped' if type(status) == str
                 RUNNING  or  STOPPED  if type(status) == int 
        """
        if type(status) == str:
            try:
                status_val = STATUS2VAL_DICT[status.lower()]
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
            return VAL2STATUS_DICT[status_val]
        else:
            return status_val

    def start(self):
        """
        Starts the device - sets system status to running.

        Arguments: None
        
        Return: None
        """
        self.set_status('running')
        return

    def stop(self):
        """
        Stops the device - sets system status to stop.
        
        Arguments: None
        
        Return: None
        """
        self.set_status('stopped')
        return

    def get_dir(self,ret_type='str'):
        """
        Gets the current motor direction. Can return either a string value,
        "positive"/"negative", or an integer value, POSITIVE/NEGATIVE, 
        depending on the value of the keyword argument ret_type.
        
        Arguments: None

        Keywords:
          ret_type = determines the return type of the function. 
                     If ret_type = 'str' the a string is returned. 
                     If ret_tyep = 'int' an integer is returned.

        Return: the current motor direction (string or integer)
        """
        dir_val = self.usb_get_cmd(USB_CMD_GET_DIR)
        if ret_type == 'str':
            return VAL2DIR_DICT[dir_val]
        elif ret_type == 'int':
            return dir_val
        else:
            raise ValueError, "unknown ret_type %s"%(ret_type,)


    def set_enable(self,enable):
        """
        Enables the stepper motor drive by setting the enable pin to high
        (enabled) or low (disabled).

        Arguments:
          enable_val =  enable string or integer value
                        either 'enable' or 'disable' if string
                        either  ENABLE  or  DISABLE  if integer
                 
        Return: the new enable status
                'enable' or 'disable' if type(val) == str
                 ENABLE  or  DISABLE  if type(val) == int
                
        """
        if type(enable) == str:
            try:
                enable_val = ENABLE2VAL_DICT[enable.lower()]
            except:
                raise ValueError, "unknown enable string %s"%(enable,)
        else:
            try:
                enable_val = int(enable)
            except:
                raise ValueError, "unable to convert enable to integer"
            if not (enable_val in (ENABLED,DISABLED)):
                raise ValueError, "unknown enable integer %d"%(enable_val,)
        
        # Send usb command
        enable_val = self.usb_set_cmd(USB_CMD_SET_ENABLE,enable_val)
        if type(enable) == str:
            return VAL2ENABLE_DICT[enable_val]
        else:
            return enable_val

    def get_enable(self,ret_type='str'):
        """
        Returns drive enable motor enable status.

        Arguments: None
        
        Return: the motor enable status.
                'enable' or 'disable' if ret_type == 'str'
                 ENABLE  or  DISABLE  if ret_type == 'int'
                
        """
        enable_val = self.usb_get_cmd(USB_CMD_GET_ENABLE)
        if ret_type == 'str':
            return VAL2ENABLE_DICT[enable_val]
        elif ret_type == 'int':
            return enable_val
        else:
            raise ValueError, "unknown ret_type %s"%(ret_type,)


    def enable(self):
        """
        Enables stepper motor drive.
        
        Arguments: None
        
        Return: None
        """
        self.set_enable('enabled')
        
    def disable(self):
        """
        Disables stepper motor drive.
        
        Arguments: None
        
        Return: None
        """
        self.set_enable('disabled')


    def set_dio_hi(self,pin):
        """
        Sets DIO pin to logic high.

        Arguments:
         pin = DIO pin number (0-7)
         
        Return: None 
        """
        if pin < 0 or pin > 7:
            raise ValueError, "pin # out of range"
        val = self.usb_set_cmd(USB_CMD_SET_DIO_HI,pin)

    def set_dio_lo(self,pin):
        """
        Sets DIO pin to logic low.

        Arguments:
         pin = DIO pin number (0-7)
         
        Return: None 
        """
        if pin < 0 or pin > 7:
            raise ValueError, "pin # out of range"
        val = self.usb_set_cmd(USB_CMD_SET_DIO_LO,pin)

    def set_ext_int(self,ext_int):
        """
        Enable or disables external interrupts.

        Argument:
         ext_int = ENABLE or DISABLE, 'enable' or 'disable'

        Return: the new external interrupt setting 
                'enable' or 'disable' if type(val) == str
                 ENABLE  or  DISABLE  if type(val) == int
        """

        if type(ext_int) == str:
            try:
                ext_int_val = ENABLE2VAL_DICT[ext_int.lower()]
            except:
                raise ValueError, "unknown ext_int string %s"%(ext_int,)
        else:
            try:
                ext_int_val = int(ext_int)
            except:
                raise ValueError, "unable to convert ext_int to integer"
            if not (ext_int_val in (ENABLED,DISABLED)):
                raise ValueError, "unknown ext_int integer %d"%(ext_int_val,)
        
        # Send usb command
        ext_int_val = self.usb_set_cmd(USB_CMD_SET_EXT_INT,ext_int_val)
        if type(ext_int) == str:
            return VAL2ENABLE_DICT[ext_int_val]
        else:
            return ext_int_val

    def get_ext_int(self, ret_type='str'):
        """
        Returns current external interrupt setting.

        Arguments: None
        
        Return: current external interrupt setting. 
                'ext_int' or 'disable' if ret_type == 'str'
                 ENABLE  or  DISABLE  if ret_type == 'int'
                
        """
        ext_int_val = self.usb_get_cmd(USB_CMD_GET_EXT_INT)
        if ret_type == 'str':
            return VAL2ENABLE_DICT[ext_int_val]
        elif ret_type == 'int':
            return ext_int_val
        else:
            raise ValueError, "unknown ret_type %s"%(ret_type,)
        

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
        Move the motor by the specified ammount.  The motor is stopped
        and placed in positioning mode before the move begins. After
        the move is complete the motor is stopped. The positioning
        velocity used for the move is specifed by the keyword argument
        pos_vel. If the pos_vel is equal to None (defualt) then half
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
        
        Arguments:
          vel = the desired motor velocity, must be > 0.
          dir = the desired motor direction 'positive'/'negative' or POSITIVE/
                NEGATIVE.

        Return: None
        """
        mode_cur = self.get_mode()
        if mode_cur != 'velocity':
            self.set_status('stopped')
            self.set_mode('velocity')
        else:
            dir_cur = self.get_dir()
            if dir_cur != 'dir':
                self.set_status('stopped')
                self.set_dir_setpt(dir)

        self.set_vel_setpt(vel)
        self.start()
        return


    def soft_ramp_to_vel(self,vel,dir,accel,dt=0.1):
        """
        Performs a ramp (constant acceleration) from the current
        velocity to the specified velocity. The ramp is performed in
        software on the PC side by setting a time course of velocity
        set-points.  For this reason the time course of accelerations
        will not be exact.  The purpose of this function is to aid
        changing the velocity of loads with a lot of inertia.  Note,
        this function will place the at90usb device in velocity mode
        and will start the device.

        Arguments:
          vel   = the desired velocity in ind/sec
          dir   = the desired direction ('positive'/'negative') or 
                  (POSITIVE/NEGATIVE).
          accel = the desired acceleration in ind/sec**2
          
        Keywords:
          dt    = time step for velocity updates is sec.  
                  
        Return: None.
        """
        # Check input arguments
        vel = int(vel)
        if vel < 0 :
            raise ValueError, "vel must be >= 0"            
                  
        accel = int(accel)
        if accel <= 0:
            raise ValueError, "accel must > 0"
    
        dt = float(dt)
        if dt <= 0:
            raise ValueError, "dt must be > 0"
        
        if not dir in ('positive', 'negative'):
            try:
                dir = VAL2DIR_DICT[dir]
            except:
                raise ValueError, "dir must be valid direction"
                
        # Get signed version of desired velocity 
        if dir == 'positive':
            vel_new = vel
        else:
            vel_new = -vel

        # Set stop device and set mode if necessary
        if self.get_mode() == 'position':
            self.stop()
            self.set_vel_setpt(0)
            self.set_mode('velocity')
            
        # Get signed version of current velocity 
        dir_cur = self.get_dir()
        if dir_cur == 'positive':
            vel_cur = self.get_vel()
        else:
            vel_cur = -self.get_vel()
        
        # If we are currently at the desired velocity do nothing
        if vel_new == vel_cur:
            return

        # Set the sign of the acceleration 
        if vel_new < vel_cur:
            accel = -accel

        # Get acceleration time and number of acceleration points
        T = abs(vel_new-vel_cur)/float(accel)
        N = abs(int(T/dt))

        # We won't quite make it with even time steps - this is for the last step
        dt_last = abs(vel_new - int(vel_cur + dt*N*accel))/abs(float(accel))

        # Start device if it is stopped
        if self.get_status() == 'stopped':
            self.start()

        # Ramp to desired velocity
        for i in range(0,N):

            # Set direction and velocity
            v = int(vel_cur + dt*(i+1)*accel)
            if v < 0:
                self.set_dir_setpt('negative', io_update=False)    
            else:
                self.set_dir_setpt('positive', io_update=False)   
            self.set_vel_setpt(abs(v))

            # Sleep until next update
            if i < N-1:
                time.sleep(dt)
            else:
                time.sleep(dt_last)
        
        # Set to final velocity and direction
        self.set_dir_setpt(dir, io_update=False)
        self.set_vel_setpt(vel)            
        return
        

    def soft_ramp_to_pos(self,pos,accel,pos_vel=None,dt=0.1):
        """
        Performs a ramp from the the current position to the specified
        position. The ramp consists of three phases: 1. constant
        acceleration (specified by accel), 2. a constant velocity
        (specified by pos_vel), and 3. constant decceleration
        (specified by accel).  The constant velocity phase may or may
        not occur depending on the acceleration and the distance of
        the final position from the starting position. The constant
        velocity The ramp is performed in software on the PC side (not
        in the firmware) by setting the motor velocity based on the
        distance from the starting and final positions. For this
        reason the time course of the the ramp may not be exact. The
        main purpose of the ramp is to enable the position of inertial
        loads. 

        Arguments:
          pos     = the desired final position of the motor in indices.
          accel   = the ramp acceleration in indices/sec**2
          
        Keywords: 

          pos_vel = the peak ramp velocity in indices/sec. If pos_vel=
                    None (default) then the peak ramp velocity if set to  
                    half the maximum allowed velocity.

        Return: None        
        """
        # Cast and check input arguments
        pos = int(pos)
        accel = int(accel)
        if accel <= 0:
            raise ValueError, "accel must be > 0"
        if pos_vel != None:
            pos_vel = int(pos_vel)
        else:
            pos_vel = 0.5*self.max_vel
        if pos_vel <=0:
            raise ValueError, "pos_vel must be > 0"
        dt = float(dt)
        if dt <= 0:
            raise ValueError, "dt must be > 0"

        # Stop device, set to positioning mode and set position set-point 
        self.set_status('stopped')
        self.set_mode('position')
        self.set_pos_setpt(pos)
        
        # Compute acceleration time and distance
        time_accel = float(pos_vel)/float(accel) 
        dist_accel = 0.5*float(accel)*time_accel**2
        
        # Getting start position
        pos_start = self.get_pos()
        dist_total = abs(pos - pos_start)
        if dist_total == 0:
            return

        # Set intial velocity
        self.set_pos_vel(0)
        self.start()        

        # Ramp to position
        cnt = 0
        while abs(self.get_pos_err()) != 0:
            
            # Get current position
            pos_cur = self.get_pos()
            cnt +=1
            
            # Compute distance from start and desired position
            dist_from_start = abs(pos_cur - pos_start)
            dist_from_final = abs(pos_cur - pos)
            
            # Compute next positioning velocity
            if dist_total < 2.0*dist_accel:
                if dist_from_start < 0.5*dist_total:
                    t = math.sqrt(2.0*dist_from_start/float(accel))
                    t = max([cnt*dt,t])
                    v = abs(int(accel*t))
                else:
                    t = math.sqrt(2.0*dist_from_final/float(accel))
                    v = abs(int(accel*t))
            else:
                
                if dist_from_final < dist_accel:
                    t = math.sqrt(2.0*dist_from_final/float(accel))
                    v = abs(int(accel*t))
                elif dist_from_start < dist_accel:
                    t = math.sqrt(2.0*dist_from_start/float(accel))
                    t = max(cnt*dt, t)
                    v = abs(int(accel*t))
                else:
                    v = pos_vel    
        
            # Set positioning velocity
            self.set_pos_vel(max([v,self.min_vel]))
            time.sleep(dt)
            
        # Ramp complete
        self.stop()    
        return
            
    def print_values(self):
        """
        Prints the current device values.
        
        Arguments: None
        
        Return None.
        """
        print 
        print 'device information'
        print ' '+ '-'*35
        print '   manufacturer:', self.get_manufacturer()
        print '   product:', self.get_product()
        print '   serial number:', self.get_serial_number()
        print
        print ' system state'
        print ' '+ '-'*35
        print '   operating mode:', self.get_mode()
        print '   status:', self.get_status()
        print '   drive:', self.get_enable()
        print '   position:', self.get_pos()
        print '   velocity:', self.get_vel()
        print '   direction:', self.get_dir()
        print '   position error:', self.get_pos_err()
        print '   maximum velocity:', self.get_max_vel()
        print '   minimum velocity:', self.get_min_vel()
        print '   external interrupts:', self.get_ext_int()
        
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
    """
    Compares expected and received command ids.
    
    Arguments:
      expected_id = expected command id
      received_is = received command id
      
    Return: None
    """
    if not expected_id == received_id:
        msg = "received incorrect command ID %d expected %d"%(received_id,expected_id)
        raise IOError, msg
    return


def print_LGPL():    
    msg = """
simple_step
Copyright (C) William Dickson, 2008.
  
wbd@caltech.edu
www.willdickson.com

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
"""
    print msg


# ------------------------------------------------------------------





    
    
