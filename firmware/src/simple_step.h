/* ------------------------------------------------------------------------
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

----------------------------------------------------------------------------

Purpose: firmware for simple stepper motor controller w/ USB
interface based on the at90usb1287 microcontroller.

Author: Will Dickson

----------------------------------------------------------------------------*/
#ifndef _SIMPLE_STEP_H_
#define _SIMPLE_STEP_H_

#include <math.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <util/atomic.h>
#include "descriptors.h"
#include <MyUSB/Version.h>          // Library Version Information
#include <MyUSB/Common/ButtLoadTag.h>   // PROGMEM tags readable by the ButtLoad project
#include <MyUSB/Drivers/USB/USB.h>  // USB Functionality
#include <MyUSB/Drivers/Board/LEDs.h>   // LEDs driver
#include <MyUSB/Scheduler/Scheduler.h>  // Simple scheduler for task management

// USB Command IDs 
#define USB_CMD_GET_POS          0
#define USB_CMD_SET_POS_SETPT    1
#define USB_CMD_GET_POS_SETPT    2
#define USB_CMD_SET_VEL_SETPT    3
#define USB_CMD_GET_VEL_SETPT    4
#define USB_CMD_GET_VEL          5
#define USB_CMD_SET_DIR_SETPT    6
#define USB_CMD_GET_DIR_SETPT    7
#define USB_CMD_SET_MODE         8
#define USB_CMD_GET_MODE         9
#define USB_CMD_SET_POS_VEL     10
#define USB_CMD_GET_POS_VEL     11
#define USB_CMD_GET_POS_ERR     12
#define USB_CMD_SET_ZERO_POS    13
#define USB_CMD_GET_MAX_VEL     14
#define USB_CMD_GET_MIN_VEL     15
#define USB_CMD_GET_STATUS      16
#define USB_CMD_SET_STATUS      17
#define USB_CMD_GET_DIR         18
#define USB_CMD_SET_ENABLE      19
#define USB_CMD_GET_ENABLE      20
#define USB_CMD_SET_DIO_HI      21
#define USB_CMD_SET_DIO_LO      22
#define USB_CMD_GET_EXT_INT     23
#define USB_CMD_SET_EXT_INT     24
#define USB_CMD_AVR_RESET      200
#define USB_CMD_AVR_DFU_MODE   201
#define USB_CMD_TEST           251

// Usb ctl values for bulk in packets - used to determine data type
#define USB_CTL_UINT8  0
#define USB_CTL_UINT16 1
#define USB_CTL_INT32  2

// Usb ctl value for USB bulk out packects
#define USB_CTL_UPDATE 200
#define USB_CTL_NO_UPDATE 201

// Opertaing modes
#define VEL_MODE 0
#define POS_MODE 1

// Motor directions
#define DIR_POS 0
#define DIR_NEG 1

// Default positioning velocity 
#define DEFAULT_POS_VEL 5000

// Prescaler for pwm timer
#define TIMER_PRESCALER 8

// Max and min values allowed for the timer.
// Sets the min and max frequencies.
#define TIMER_TOP_MIN 19      // 19 => 50kHz
#define TIMER_TOP_MAX 65535   // 65535 => 15.52Hz

// Timer top and output compare registers
#define TIMER_TOP OCR3A  // Using OCR3A gives double buffering of top  
#define TIMER_OCR OCR3B  // Sets PWM (Clock) high time

// Timer control registers
#define TIMER_TCCRA TCCR3A
#define TIMER_TCCRB TCCR3B

// Timer interrupt mask register and enable
#define TIMER_TIMSK TIMSK3 // Mask register
#define TIMER_TOIE  TOIE3  // Enable

// Clock and direction DDR register and pins
#define CLK_DIR_DDR DDRC
#define CLK_DDR_PIN DDC5
#define DIR_DDR_PIN DDC4

// Clock and Direction port and pins
#define CLK_DIR_PORT PORTC
#define CLK_PORT_PIN PC5
#define DIR_PORT_PIN PC4 

// States for run status flag
#define RUNNING 1
#define STOPPED 0

// States for enable
#define ENABLED 1
#define DISABLED 0

// Velocity mode trigger DDR register and pins
#define VEL_TRIG_DDR DDRC
#define VEL_TRIG_DDR_PIN DDC0

// Velocity mode trigger io port and pins
#define VEL_TRIG_PORT PORTC
#define VEL_TRIG_PIN PC0

// Motor enable DDR register and pins
#define ENABLE_DDR DDRC
#define ENABLE_DDR_PIN DDC1

// Motor enable io port and pins
#define ENABLE_PORT PORTC
#define ENABLE_PIN PC1  

// DIO DDR register
#define DIO_DDR DDRA
#define DIO_DDR_PINS {DDA0,DDA1,DDA2,DDA3,DDA4,DDA5,DDA6,DDA7}  

// DIO PORT
#define DIO_PORT PORTA
#define DIO_PORT_PINS {PA0,PA1,PA2,PA3,PA4,PA5,PA6,PA7}

////////////////////////////////////////////////////////////////// 
// DEBUG --
// Changed DIO port because of conflict with external interrupts. 
// This means other users - meaning peter and marie will have
// to wire up the DIO to another port when upgrading the firmware.
//////////////////////////////////////////////////////////////////

// External interrupt polarities
#define EXT_INT_HI2LO 0
#define EXT_INT_LO2HI 1

// External interrupt
#define EXT_INT INT0

// External interrupt DIO DDR register, and DDR pin
#define EXT_INT_DDR DDRD 
#define EXT_INT_DDR_PIN DDD0

// External interupt port, pin and interrupt vector
#define EXT_INT_OUT_REG PORTD
#define EXT_INT_OUT_PIN PD0
#define EXT_INT_INP_REG PIND
#define EXT_INT_INP_PIN PIND0
#define EXT_INT_VECT INT0_vect

// External interupt polarity (EXT_INT_HI2LO or EXT_INT_LO2HI)
#define EXT_INT_POLARITY EXT_INT_HI2LO 

// Software reset 
#define AVR_RESET() wdt_enable(WDTO_30MS); while(1) {}
#define AVR_IS_WDT_RESET()  ((MCUSR&(1<<WDRF)) ? 1:0)
#define DFU_BOOT_KEY_VAL 0xAA55AA55

// USB packet header information
typedef struct {
    uint8_t Command_ID;
    uint8_t Control_Byte;
} Header_t;

// USB packet data
typedef union {
    uint8_t  uint8_t;
    uint16_t uint16_t;
    int32_t  int32_t;
} Data_t;

// USB packet structure
typedef struct {
    Header_t Header;
    Data_t   Data;
} USB_InOut_t; 

// Position mode parameter structure
typedef struct {
    int32_t   Pos_SetPt;   // Set-point motor position 
    uint16_t  Pos_Vel;     // Positioning velocity     
} Pos_Mode_t;

// Velocity mode parameter structure
typedef struct {
    uint16_t  Vel_SetPt;   // Set-point velocity       
    uint8_t   Dir_SetPt;   // Set-point direction   
} Vel_Mode_t;

// Sytem state structure
typedef struct {
    uint8_t    Mode;        // Operating mode
    uint8_t    Dir;         // Motor Direction
    uint16_t   Vel;         // Actual motor velocity
    int32_t    Pos;         // Actual motor position
    Pos_Mode_t Pos_Mode;    // Position mode parameters
    Vel_Mode_t Vel_Mode;    // Velocity mode parameters
    uint8_t    Status;      // Motor status (RUNNING or STOPPED)
    uint8_t    Enable;      // Motor enable pin 
    uint8_t    Ext_Int;     // External interrupts (ENABLED or DISABLED)
} Sys_State_t;

/// Global variables
USB_InOut_t USB_Out; 
USB_InOut_t USB_In; 
const uint8_t dio_port_pins[] = DIO_PORT_PINS;

volatile Sys_State_t Sys_State = {
    Mode:      VEL_MODE, 
    Dir:       DIR_POS,
    Vel:       0,
    Pos:       0,
    Pos_Mode:  {Pos_SetPt: 0, Pos_Vel: DEFAULT_POS_VEL},
    Vel_Mode:  {Vel_SetPt: 0, Dir_SetPt: DIR_POS},
    Status:    STOPPED,
    Enable:    ENABLED,
    Ext_Int:   DISABLED,
};

// Task Definitions: 
TASK(USB_Process_Packet);

// Event Handlers:
HANDLES_EVENT(USB_Connect);
HANDLES_EVENT(USB_Disconnect);
HANDLES_EVENT(USB_CreateEndpoints);

// Function Prototypes
static void USB_Packet_Read(void);
static void USB_Packet_Write(void);
static void REG_16bit_Write(volatile uint16_t * reg, volatile uint16_t val);
static void IO_Init(void);
static void Set_Pos_SetPt(int32_t Pos);
static void Set_Vel_SetPt(uint16_t Vel);
static void Set_Dir_SetPt(uint8_t Dir);
static void Set_Pos_Vel(uint16_t Pos_Vel);
static void Set_Mode(uint8_t Mode);
static void Set_Zero_Pos(int32_t Pos);
static void Set_Status(uint8_t Status);
static int32_t Get_Pos_Err(void);
static uint16_t Get_Max_Vel(void);
static uint16_t Get_Min_Vel(void);
static uint16_t Get_Top(uint16_t Vel);
static void Clk_Dir_On(void);
static void Clk_Dir_Off(void);
static void IO_Update(uint16_t Vel, uint8_t Dir);
static void Vel_Mode_IO_Update(void);
static void Pos_Mode_IO_Update(void);
static void Vel_Trig_Hi(void);
static void Vel_Trig_Lo(void);
static void Set_Enable(uint8_t value);
static int32_t Get_Pos(void);
static void Set_DIO_Hi(uint8_t pin);
static void Set_DIO_Lo(uint8_t pin);
static void Set_Ext_Int(uint8_t val);

#endif // _SIMPLE_STEP_H_
