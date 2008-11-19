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
USB_CMD_SET_VEL = 3
USB_CMD_GET_VEL = 4
USB_CMD_SET_DIR = 5
USB_CMD_GET_DIR = 6
USB_CMD_SET_MODE = 7
USB_CMD_GET_MODE = 8
USB_CMD_SET_VEL_LIM = 9
USB_CMD_GET_VEL_LIM = 10
USB_CMD_GET_POS_ERR = 11
USB_CMD_SET_ZERO_POS = 12
USB_CMD_GET_MAX_VEL = 13
USB_CMD_GET_MIN_VEL = 14
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
    USB_CMD_SET_VEL : 'uint16',
    USB_CMD_SET_DIR : 'uint8',
    USB_CMD_SET_MODE : 'uint8',
    USB_CMD_SET_VEL_LIM : 'uint16',
    USB_CMD_SET_ZERO_POS : 'int32',
    }

# Dictionary from type to USB_CTL values
TYPE2USB_CTL_DICT = {
    'uint8' : USB_CTL_UINT8,
    'uint16' : USB_CTL_UINT16,
    'int32' : USB_CTL_INT32,
    }
USB_CTL2TYPE_DICT = swap_dict(TYPE2USB_CTL_DICT)

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
    controller.
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
                #print 'idVendor: 0x%04x idProduct: 0x%04x'%(dev.descriptor.idVendor,
                #                                            dev.descriptor.idProduct)
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
            
    def close(self):
        """
        Close usb device.
        """
        ret = usb.close(self.libusb_handle)
        
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
        pos_setpt = self.usb_set_cmd(USB_CMD_SET_POS_SETPT,pos_setpt)
        return pos_setpt
    
    def get_pos_setpt(self):
        """
        Returns the current motor position set-point in indices.
        """
        set_pt = self.usb_get_cmd(USB_CMD_GET_POS_SETPT)
        return set_pt

    def set_vel(self,vel):
        """
        Sets the motor velocity in indices/sec.  The velocity is
        always nonnegative - the direction of rotation is determined
        by setting the direction value. The motor will spin at this
        velocity in the set direction (see the get_dir and set_dir
        commands) when the device is in velocity mode. Note, The motor
        velocity can only be set when the device is in velocity mode.
        Also, the velocity is limited by the velocity limit setting.
        Trying to set the motor velocity to a value greater then
        velocity limit will result in the velocity being set to the
        velocity limit.
        
        Argument: 
          vel = the motor velocity (indices/sec),  always >= 0
        
        Return: the actual motor velocity obtained indice/sec. 
        """
        if vel < 0:
            raise ValueError, "vel must be >= 0"
        vel = self.usb_set_cmd(USB_CMD_SET_VEL,vel)
        return vel

    def get_vel(self):
        """
        Returns the motors current velocity in indices/sec. Note, this is 
        always a positive number. The direction of rotation is determined 
        by the direction value.
        """
        vel = self.usb_get_cmd(USB_CMD_GET_VEL)
        return vel

    def set_dir(self,dir):
        """
        Sets the motor rotation direction. The value can be set using
        the strings 'positive'/'negative' or by using the the integer 
        values POSITIVE/NEGATIVE.

        Argument: 

          dir = the motor rotation direction either strings 
          ('positive'/'negative') or integers (POSITIVE or NEGATIVE)
          
        Return: the motor rotation direction
        """
        # If direction is string convert to integer direction value
        if type(dir) == str:
            dir_val = DIR2VAL_DICT[dir.lower()]
        else:
            dir_val = dir
        dir_val = self.usb_set_cmd(USB_CMD_SET_DIR,dir_val)
        # If input direction is a string we return a string 
        if type(dir) == str:
            return VAL2DIR_DICT[dir_val]
        else:
            return dir_val
        
    def get_dir(self,ret_type = 'str'):
        """
        Returns the motor rotation direction. The return values can be
        strings ('positive', 'negative') or integer values (POSITIVE,
        NEGATIVE) depending on the keyword  argument ret_type.
        
        Keywords:
          ret_type = 'str' or 'int'

        Return: the motor rotation direction.
        """

        dir_val = self.usb_get_cmd(USB_CMD_GET_DIR)
        if ret_type == 'int':
            return dir_val
        else:
            return VAL2DIR_DICT[dir_val] 
    
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
            mode_val = MODE2VAL_DICT[mode.lower()]
        else:
            mode_val = mode
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
            
    def set_vel_lim(self,vel_lim):
        """
        Sets the velocity limit for the device in indices/sec. This
        will be the velocity used for moving the motor when the device
        is in position mode. It is the maximum allowed velocity when
        the device is in velocity mode. The velocity limit is always
        >= 0.

        Arguments:
          vel_lim = the velocity limit (indices/sec), always >= 0

        Return:  the current velocity limit setting. 
        """
        if vel_lim < 0:
            raise ValueError, "vel_lim must be >= 0"
        vel_lim = self.usb_set_cmd(USB_CMD_SET_VEL_LIM,vel_lim)
        return vel_lim

    def get_vel_lim(self):
        """
        Returns the current velocity limit setting in indices/sec.
        """
        vel_lim = self.usb_get_cmd(USB_CMD_GET_VEL_LIM)
        return vel_lim

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

    def usb_set_cmd(self,cmd_id,val):
        """
        Generic usb set command. Sends set command w/ value to device
        and extracts the value returned

        Example:
        
        vel_lim = dev.usb_set_cmd(USB_SET_VEL_LIM, vel_lim)

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

    def cmd_test(self):
        """
        Dummy usb command for debugging.
        """
        val = self.usb_get_cmd(USB_CMD_TEST)
        return val

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

    def print_values(self):
        """
        Prints the current device values 
        """
        print 'position:', self.get_pos()
        print 'velocity:', self.get_vel()
        print 'direction:', self.get_dir()
        print 'velocity limit:', self.get_vel_lim()
        print 'position error:', self.get_pos_err()
        print 'position set-point:', self.get_pos_setpt()
        print 'operating mode:', self.get_mode()
        print 'maximum velocity:', self.get_max_vel()
        print 'minimum velocity:', self.get_min_vel()


def check_cmd_id(expected_id,received_id):
    if not expected_id == received_id:
        msg = "received incorrect command ID %d expected %d"%(received_id,expected_id)
        raise IOError, msg

# -------------------------------------------------------------------------
if __name__=='__main__':

    # Some simple testing
    import time

    if 0:

        N = 2
        
        dev = Simple_Step()
        
        print 'set_vel_lim: ', dev.set_vel_lim(40000)
        print 'set_zero_pos:', dev.set_zero_pos(0)
        print 'set_pos_setpt:', dev.set_pos_setpt(1000)
        print 'set_vel:', dev.set_vel(40002)
        print 'set_dir:', dev.set_dir('negative')
        print 'set_dir:', dev.set_dir(POSITIVE)
        print 'set_mode:', dev.set_mode('position')
        print 'set_mode:', dev.set_mode(VELOCITY_MODE)
        print 
        
        t0 = time.time()
        for i in range(0,N):
            print '(%d/%d)'%(i,N)
            dev.print_values()
            print

            
        t1 = time.time()
        dt = (t1-t0)/float(N)
        print 'avg time: ', 1.0/dt
        print 

        dev.close()


    if 1:
        
        dev = Simple_Step()
        dev.print_values()
        dev.close()
    
