// simple_step.c
//
// Purpose: firmware for simple stepper motor controller w/ USB interface based 
// on the at90usb1287 microcontroller. 
//
// Author: Will Dickson
//
// ------------------------------------------------------------------------------
#include "simple_step.h"

// Project Tags, for reading out using the ButtLoad project 
BUTTLOADTAG(ProjName, "Simple Step");
BUTTLOADTAG(BuildTime, __TIME__);
BUTTLOADTAG(BuildDate, __DATE__);
BUTTLOADTAG(MyUSBVersion, "MyUSB V" MYUSB_VERSION_STRING);

// Scheduler Task List 
TASK_LIST {
  {Task: USB_USBTask,        TaskStatus: TASK_STOP},
  {Task: USB_Process_Packet, TaskStatus: TASK_STOP},
};

// DFU Bootloader Declarations 
uint32_t boot_key __attribute__ ((section (".noinit")));
void (*start_bootloader) (void) = (void (*)(void)) 0xf000;

int main(void)
{
  // After reset start bootloader? 
  if ((AVR_IS_WDT_RESET ()) && (boot_key == DFU_BOOT_KEY_VAL))
    {
      boot_key = 0;
      (*start_bootloader) ();
    }

  // Disable watchdog if enabled by bootloader/fuses 
  MCUSR &= ~(1 << WDRF);
  wdt_disable();

  // Disable Clock Division 
  SetSystemClockPrescaler(0);

  // Hardware Initialization 
  LEDs_Init();

  // Indicate USB not ready 
  LEDs_SetAllLEDs(LEDS_LED1|LEDS_LED3);

  //Initialize Scheduler so that it can be used 
  Scheduler_Init();

  // Initialize USB Subsystem 
  USB_Init();

  IO_Init();

  // Scheduling - routine never returns, so put this last in the main function 
  Scheduler_Start();
  return 0;
}

static void IO_Init(void)
{
  PORTC &= 0x9F; // pin C6, C5 is set low to start (PWM A,B of Timer/Counter 3)
 
  DDRC = 0x0;
  DDRC |= (1<<PC5);
  DDRC |= (1<<PC6);

/*   CLK_DIR_DDR = 0x0; */
/*   CLK_DIR_DDR |= (1<<CLK0_DDR_PIN); */
/*   CLK_DIR_DDR |= (1<<CLK1_DDR_PIN); */
/*   CLK_DIR_DDR |= (1<<DIR0_DDR_PIN); */
/*   CLK_DIR_DDR |= (1<<DIR1_DDR_PIN);   */

  // Set Clock high time 
  OCR3A = TIMER_CLOCK_HIGH; 
  OCR3B = TIMER_CLOCK_HIGH; 

  // Set TOP high
  ICR3 = TIMER_TOP_MIN;  // 10 msec (100 Hz)

  // ---- set TCCRA_motor ----------
  // set Compare Output Mode for Fast PWM
  // COM1A1:0 = 1,0 clear OC1A on compare match
  // COM1B1:0 = 1,0 clear OC1B on compare match
  // COM1C1:0 = 0,0 OCR1C disconnected
  // WGM11, WGM10 = 1,0
  TCCR3A= 0xA2;

  // ---- set TCCRB_motor ----------
  // high bits = 0,0,0
  //WGM33, WGM32 = 1,1
  TCCR3B = 0x18;

  // Set Timer prescaler
  switch (TIMER_PRESCALER) {
  case 0:
    TCCR3B |= 0x1;
    break;
 
  case 8:
    TCCR3B |= 0x2;
    break;

  case 64:
    TCCR3B |= 0x3;
    break;

  case 256:
    TCCR3B |= 0x4;
    break;
    
  case 1024:
    TCCR3B |= 0x5;
    break;

  default:
    // We shouldn't be here - but just in case set it
    // to some values
    TCCR3B |= 0x2;
    break;
  }
  
  return;
}

EVENT_HANDLER(USB_Connect)
{
  // Start USB management task 
  Scheduler_SetTaskMode(USB_USBTask, TASK_RUN);
  // Indicate USB enumerating 
  LEDs_SetAllLEDs(LEDS_LED1 | LEDS_LED4);
  return;
}

EVENT_HANDLER(USB_Disconnect)
{
  // Stop running ProcessPacket and USB management tasks
  Scheduler_SetTaskMode(USB_Process_Packet, TASK_STOP);
  Scheduler_SetTaskMode(USB_USBTask, TASK_STOP);

  // Stop the timers and reset I/O lines to reduce current draw
  //IO_Disconnect();

  // Indicate USB not ready
  LEDs_SetAllLEDs(LEDS_LED1 | LEDS_LED3);
  return;
}

EVENT_HANDLER(USB_CreateEndpoints)
{
  // Setup USB In and Out Endpoints
  Endpoint_ConfigureEndpoint(SIMPLE_IN_EPNUM,
			     EP_TYPE_BULK,
			     ENDPOINT_DIR_IN,
			     SIMPLE_IN_EPSIZE,
			     ENDPOINT_BANK_DOUBLE);

  Endpoint_ConfigureEndpoint(SIMPLE_OUT_EPNUM,
			     EP_TYPE_BULK,
			     ENDPOINT_DIR_OUT,
			     SIMPLE_OUT_EPSIZE,
			     ENDPOINT_BANK_DOUBLE);

  // Indicate USB connected and ready
  LEDs_SetAllLEDs(LEDS_LED2 | LEDS_LED4);

  // Start ProcessPacket task
  Scheduler_SetTaskMode(USB_Process_Packet, TASK_RUN);
  return;
}

TASK(USB_Process_Packet)
{
  // Check if the USB System is connected to a Host  
  if (USB_IsConnected) {
    // Select the Data Out Endpoint 
    Endpoint_SelectEndpoint(SIMPLE_OUT_EPNUM);
    
    // Check to see if a command from the host has been issued 
    if (Endpoint_ReadWriteAllowed()) {
      // Indicate busy 
      LEDs_TurnOnLEDs(LEDS_LED3 | LEDS_LED4);
      
      // Read USB packet from the host 
      USB_Packet_Read();
      
      // Return the same CommandID that was received 
      USB_In.Header.Command_ID = USB_Out.Header.Command_ID;
      
      // Process USB packet 
      switch(USB_Out.Header.Command_ID) {

      case USB_CMD_GET_POS:
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = Sys_State.Pos;
	break;

      case USB_CMD_SET_POS_SETPT:
	Set_Pos_SetPt(USB_Out.Data.int32_t);
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = Sys_State.Pos_SetPt;
	break;
	
      case USB_CMD_GET_POS_SETPT:
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = Sys_State.Pos_SetPt;
	break;

      case USB_CMD_SET_VEL:
	Set_Vel(USB_Out.Data.uint16_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel;
	break;
	  
      case USB_CMD_GET_VEL:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel;
	break;
	
      case USB_CMD_SET_DIR:
	Set_Dir(USB_Out.Data.uint8_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Dir;
	break;
	
      case USB_CMD_GET_DIR:
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Dir;
	break;
	
      case USB_CMD_SET_MODE:
	Set_Mode(USB_Out.Data.uint8_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Mode;
	break;
	  
      case USB_CMD_GET_MODE:
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Mode;
	break;
	
      case USB_CMD_SET_VEL_LIM:
	Set_Vel_Lim(USB_Out.Data.uint16_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel_Lim;
       	break;

      case USB_CMD_GET_VEL_LIM:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel_Lim;
	break;

      case USB_CMD_GET_POS_ERR:
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = Get_Pos_Err();
	break;

      case USB_CMD_SET_ZERO_POS:
	Set_Zero_Pos(USB_Out.Data.int32_t);
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = 0;
	break;

      case USB_CMD_GET_MAX_VEL:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Get_Max_Vel();
	break;

      case USB_CMD_GET_MIN_VEL:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Get_Min_Vel();
	break;
	
      case USB_CMD_AVR_RESET:    
	USB_Packet_Write();
	AVR_RESET();
	break;

      case USB_CMD_AVR_DFU_MODE:
	USB_Packet_Write();
	boot_key = DFU_BOOT_KEY_VAL;
	AVR_RESET();
	break;

      case USB_CMD_TEST:
	// Test command for debugging
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = -503210;
	break;

      default:
	break;

      } // End Switch

      // Write the return USB packet 
      USB_Packet_Write();
      
      // Indicate ready 
      LEDs_SetAllLEDs(LEDS_LED2 | LEDS_LED4);
    }
  }
  return;
}

static void Set_Pos_SetPt(int32_t Pos)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  Sys_State.Pos_SetPt = Pos;
  SREG = sreg;
  return;
}

static void Set_Vel(uint16_t Vel)
{
  uint8_t sreg;
  uint16_t _Vel;
  
  if (Sys_State.Mode == POS_MODE) {
    return;
  }

  sreg = SREG;
  cli();
  if (Vel > Sys_State.Vel_Lim) {
    _Vel = Sys_State.Vel_Lim;
  }
  else {
    _Vel = Vel;
  }
  Sys_State.Vel = _Vel;
  SREG = sreg;
  return;
}

static void Set_Dir(uint8_t Dir)
{
  uint8_t sreg;
  
  sreg = SREG;
  cli();
  if ((Dir == DIR_POS) || (Dir == DIR_NEG)) {
    Sys_State.Dir = Dir;
  }
  SREG = sreg;
  return;
}

static void Set_Vel_Lim(uint16_t Vel_Lim)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  if (Vel_Lim <= VEL_LIM_MAX) {
    Sys_State.Vel_Lim = Vel_Lim;
  }
  SREG = sreg;
  return;
}

static void Set_Mode(uint8_t Mode)
{
  uint8_t sreg;
  
  sreg = SREG;
  cli();
  if ((Mode == VEL_MODE) || (Mode == POS_MODE)) {
    Sys_State.Mode = Mode;
  }
  SREG = sreg;
  return;
}

static int32_t Get_Pos_Err(void)
{
  if (Sys_State.Mode == VEL_MODE) {
    return 0;
  }
  return Sys_State.Pos_SetPt - Sys_State.Pos;
}

static void Set_Zero_Pos(int32_t Pos)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  Sys_State.Pos_SetPt -= Pos;
  Sys_State.Pos -= Pos;
  SREG = sreg;
  return;
}

// Get maximum number of indices per second
static uint16_t Get_Max_Vel(void)
{
  return F_CPU/(TIMER_PRESCALER*(1+TIMER_TOP_MIN));
}

// Get minimum number of indices per second
static uint16_t Get_Min_Vel(void)
{
  return F_CPU/(TIMER_PRESCALER*(1+TIMER_TOP_MAX));

}

// Get Timer top given the desired velocity in indices/sec
static uint16_t Get_Top(uint16_t Vel)
{
  return F_CPU/(TIMER_PRESCALER*Vel)-1;
}

static void USB_Packet_Read(void)
{
  uint8_t *USB_OutPtr = (uint8_t *) &USB_Out;

  // Select the Data Out endpoint 
  Endpoint_SelectEndpoint(SIMPLE_OUT_EPNUM);
  // Read in USB packet header 
  Endpoint_Read_Stream_LE(USB_OutPtr, sizeof(USB_Out));
  // Clear the endpoint 
  Endpoint_FIFOCON_Clear();
  return;
}

static void USB_Packet_Write(void)
{
  uint8_t *USB_InPtr = (uint8_t *) &USB_In;

  // Select the Data Out endpoint 
  Endpoint_SelectEndpoint(SIMPLE_OUT_EPNUM);

  // While data pipe is stalled, process control requests 
  while(Endpoint_IsStalled())
    {
      USB_USBTask();
      Endpoint_SelectEndpoint(SIMPLE_OUT_EPNUM);
    }

  // Select the Data In endpoint 
  Endpoint_SelectEndpoint(SIMPLE_IN_EPNUM);

  // While data pipe is stalled, process control requests 
  while (Endpoint_IsStalled())
    {
      USB_USBTask();
      Endpoint_SelectEndpoint(SIMPLE_IN_EPNUM);
    }

  // Wait until read/write to IN data endpoint allowed 
  while(!(Endpoint_ReadWriteAllowed ()));

  // Write the return data to the endpoint 
  Endpoint_Write_Stream_LE(USB_InPtr, sizeof(USB_In));

  // Send the CSW 
  Endpoint_FIFOCON_Clear();
  return;
}

static void REG_16bit_Write (volatile uint16_t * reg, volatile uint16_t val)
{
  // See "Accessing 16-bit Registers" of the AT90USB1287 datasheet 
  uint8_t sreg;
  // Save global interrupt flag 
  sreg = SREG;
  // Disable interrupts 
  cli ();
  *reg = val;
  // Restore global interrupt flag 
  SREG = sreg;
  return;
}

