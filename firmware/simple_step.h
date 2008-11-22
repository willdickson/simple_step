// simple_step.h
//
// Author: Will Dickson
//
// -------------------------------------------------------------------------
#ifndef _SIMPLE_STEP_H_
#define _SIMPLE_STEP_H_

#include <math.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include "descriptors.h"
#include <MyUSB/Version.h>	        // Library Version Information
#include <MyUSB/Common/ButtLoadTag.h>	// PROGMEM tags readable by the ButtLoad project
#include <MyUSB/Drivers/USB/USB.h>	// USB Functionality
#include <MyUSB/Drivers/Board/LEDs.h>	// LEDs driver
#include <MyUSB/Scheduler/Scheduler.h>	// Simple scheduler for task management

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
#define USB_CMD_AVR_RESET      200
#define USB_CMD_AVR_DFU_MODE   201
#define USB_CMD_TEST           251

// Usb ctl values - used to determine data type
#define USB_CTL_UINT8  0
#define USB_CTL_UINT16 1
#define USB_CTL_INT32  2

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
#define TIMER_ICR ICR3  
#define TIMER_OCR OCR3B 

// Timer control registers
#define TIMER_TCCRA TCCR3A
#define TIMER_TCCRB TCCR3B

// Timer interrupt mask register and enable
#define TIMER_TIMSK TIMSK3 // Mask register
#define TIMER_TOIE  TOIE3  // Enable

// Clock and direction directions reg and pins
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
} Sys_State_t;

/// Global variables
USB_InOut_t USB_Out; 
USB_InOut_t USB_In; 

volatile Sys_State_t Sys_State = {
 Mode:      VEL_MODE, 
 Dir:       DIR_POS,
 Vel:       0,
 Pos:       0,
 Pos_Mode:  {Pos_SetPt: 0, Pos_Vel: DEFAULT_POS_VEL},
 Vel_Mode:  {Vel_SetPt: 0, Dir_SetPt: DIR_POS},
 Status:    STOPPED,
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
static void IO_Update(void);
static void Vel_Mode_IO_Update(void);
static void Pos_Mode_IO_Update(void);

#endif // _SIMPLE_STEP_H_
