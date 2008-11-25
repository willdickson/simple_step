// simple_step.c
//
// Purpose: firmware for simple stepper motor controller w/ USB interface based 
// on the at90usb1287 microcontroller. 
//
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
  // Set data direction of trigger pins to output
  VEL_TRIG_DDR |= (1 << VEL_TRIG_DDR_PIN);

  // Set all PINS on clock and direction port low
  CLK_DIR_PORT = 0x0; 

  // Turn off Clock and Direction Pins
  Clk_Dir_Off();

  // Set Clock high time 
  TIMER_OCR = TIMER_TOP_MAX/2; 
  
  // Set TOP high
  TIMER_TOP = TIMER_TOP_MAX;  // 10 msec (100 Hz)

  // Set timer control registers, connect OCnB to pin and set 
  // to fast PWM mode with double buffering of TOP
  TIMER_TCCRA = 0x23; 
  TIMER_TCCRB = 0x18; 
 
  // Set Timer prescaler
  switch (TIMER_PRESCALER) {
  case 0:
    TIMER_TCCRB |= 0x1;
    break;
 
  case 8:
    TIMER_TCCRB |= 0x2;
    break;

  case 64:
    TIMER_TCCRB |= 0x3;
    break;

  case 256:
    TIMER_TCCRB |= 0x4;
    break;
    
  case 1024:
    TIMER_TCCRB |= 0x5;
    break;

  default:
    // We shouldn't be here - but just in case set it
    // to some values - same a TIMER_PRESCALER 8
    TIMER_TCCRB |= 0x2;
    break;
  }

  // Enable Timer3 overflow interrupts
  TIMER_TIMSK = 0x00; 
  TIMER_TIMSK |= (1<<TIMER_TOIE); 
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

// --------------------------------------------------------------
// Function: USB_Process_Packet
//
// Purpose: Handles USB communications. This is basically a big
// switch yard for the USB commands. 
//
// --------------------------------------------------------------
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
	USB_In.Data.int32_t = Sys_State.Pos_Mode.Pos_SetPt;
	break;
	
      case USB_CMD_GET_POS_SETPT:
	USB_In.Header.Control_Byte = USB_CTL_INT32;
	USB_In.Data.int32_t = Sys_State.Pos_Mode.Pos_SetPt;
	break;

      case USB_CMD_SET_VEL_SETPT:
	Set_Vel_SetPt(USB_Out.Data.uint16_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel_Mode.Vel_SetPt;
	break;
	  
      case USB_CMD_GET_VEL_SETPT:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel_Mode.Vel_SetPt;
	break;

      case USB_CMD_GET_VEL:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Vel;
	break;
	
      case USB_CMD_SET_DIR_SETPT:
	Set_Dir_SetPt(USB_Out.Data.uint8_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Vel_Mode.Dir_SetPt;
	break;
	
      case USB_CMD_GET_DIR_SETPT:
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Vel_Mode.Dir_SetPt;
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
	
      case USB_CMD_SET_POS_VEL:
	Set_Pos_Vel(USB_Out.Data.uint16_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Pos_Mode.Pos_Vel;
       	break;

      case USB_CMD_GET_POS_VEL:
	USB_In.Header.Control_Byte = USB_CTL_UINT16;
	USB_In.Data.uint16_t = Sys_State.Pos_Mode.Pos_Vel;
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

      case USB_CMD_GET_STATUS:
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Status;
	break;

      case USB_CMD_SET_STATUS:
	Set_Status(USB_Out.Data.uint8_t);
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Status;
	break;

      case USB_CMD_GET_DIR:
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = Sys_State.Dir;
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
	USB_In.Header.Control_Byte = USB_CTL_UINT8;
	USB_In.Data.uint8_t = 1;
	break;

      default:
	break;

      } // End switch(USB_Out.Header.Command_ID)

      // Update IO Settings based on operating mode
      switch (Sys_State.Mode) {
	
      case POS_MODE:
	Pos_Mode_IO_Update();
	break;
	
      case VEL_MODE:
	Vel_Mode_IO_Update();
	break;

      default:
	break;
      }

      // Write the return USB packet 
      USB_Packet_Write();
      
      // Indicate ready 
      LEDs_SetAllLEDs(LEDS_LED2 | LEDS_LED4);
    }
  }
  return;
}

// -------------------------------------------------------------
// Function: Vel_Trig_Hi
//
// Purpose: Sets the velocity trigger pin high.
//
// -------------------------------------------------------------
static void Vel_Trig_Hi(void)
{
  VEL_TRIG_PORT |= (1 << VEL_TRIG_PIN);
  return;
}

// -------------------------------------------------------------
// Function: Vel_Trig_Lo
//
// Purpose: Sets the velocity trigger pin low.
//
// -------------------------------------------------------------
static void Vel_Trig_Lo(void)
{
  VEL_TRIG_PORT &= ~(1 << VEL_TRIG_PIN);
  return;
}

// -------------------------------------------------------------
// Function: Set_Status
//
// Purpose: Sets the device status - to RUNNING or STOPPED.
//
// -------------------------------------------------------------
static void Set_Status(uint8_t Status)
{
  uint8_t sreg;

  if ((Status == RUNNING) || (Status == STOPPED)) {
    sreg = SREG;
    cli();
    Sys_State.Status = Status;
    SREG = sreg;
  }
  return;
}

// ------------------------------------------------------------
// Function: Set_Pos_SetPt
//
// Purpose: Set the position set-point. When the device is in
// position mode the device tries to move the motor into this
// position with velocity Pos_Vel. 
//
// ------------------------------------------------------------
static void Set_Pos_SetPt(int32_t Pos)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  Sys_State.Pos_Mode.Pos_SetPt = Pos;
  SREG = sreg;
  return;
}

// -------------------------------------------------------------
// Function: Set_vel
//
// Purpose: Sets the current velocity in indices/sec.
//
// -------------------------------------------------------------
static void Set_Vel_SetPt(uint16_t Vel)
{
  uint16_t Max_Vel;
  uint8_t sreg;

  Max_Vel = Get_Max_Vel();
  // We are in velocity mode - change Sys_State velocity
  sreg = SREG;
  cli();
  Sys_State.Vel_Mode.Vel_SetPt = Vel < Max_Vel ? Vel : Max_Vel;
  SREG = sreg;

  return;
}

// --------------------------------------------------------------
// Function: Set_Dir_SetPt
//
// Purpose: Sets the devices direction set-point - used in 
// velocity mode to determine the direction of motor rotation.
// Allowed values for the direction, Dir, are DIR_POS, and
// DIR_NEG. 
//
// --------------------------------------------------------------
static void Set_Dir_SetPt(uint8_t Dir)
{
  uint8_t sreg;  
  
  sreg = SREG;
  cli();
  if ((Dir == DIR_POS) || (Dir == DIR_NEG)) {
    Sys_State.Vel_Mode.Dir_SetPt = Dir;
  }
  SREG = sreg;
  return;
}

// ------------------------------------------------------------
// Function: Set_Pos_Vel
//
// Purpose: Sets the positioning velocity. When in position 
// mode this value is used to determine the move velocity. 
//
// -------------------------------------------------------------
static void Set_Pos_Vel(uint16_t Pos_Vel)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  if (Pos_Vel <= Get_Max_Vel()) {
    Sys_State.Pos_Mode.Pos_Vel = Pos_Vel;
  }
  else {
    Sys_State.Pos_Mode.Pos_Vel = Get_Max_Vel();
  }
  SREG = sreg;
  return;
}

// -------------------------------------------------------------
// Function: Set_Mode
//
// Purpose: Sets the systems operating mode. Allowed value for 
// operating mode are VEL_MODE or POS_MODE.
//
// -------------------------------------------------------------
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

// --------------------------------------------------------------
// Function: Get_Pos_Err
//
// Purpose: Computes the position error.
//
// --------------------------------------------------------------
static int32_t Get_Pos_Err(void)
{
  return Sys_State.Pos_Mode.Pos_SetPt - Sys_State.Pos;
}

// --------------------------------------------------------------
// Function: Set_Zero_Pos
//
// Purpose: Set the systems zero position to the given value.
//
// --------------------------------------------------------------
static void Set_Zero_Pos(int32_t Pos)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  Sys_State.Pos_Mode.Pos_SetPt -= Pos;
  Sys_State.Pos -= Pos;
  SREG = sreg;
  return;
}

// --------------------------------------------------------------
// Function: Get_Max_Vel
//
// Purpose: Gets maximum allowed velocity in indices/sec.
//
// --------------------------------------------------------------
static uint16_t Get_Max_Vel(void)
{
  double Vel;
  Vel = ((double)F_CPU)/(((double)TIMER_PRESCALER)*(1.0+(double)TIMER_TOP_MIN));
  return (uint16_t) Vel;
}

// ---------------------------------------------------------------
// Function: Get_Min_vel
//
// Purpose: Gets minimum allowed velocity in indices/sec.
//
// ---------------------------------------------------------------
static uint16_t Get_Min_Vel(void)
{
  double Vel;
  Vel = ((double)F_CPU)/(((double)TIMER_PRESCALER)*(1.0+(double)TIMER_TOP_MAX));
  return (uint16_t) Vel;

}

// ---------------------------------------------------------------
// Function: Get_Top
//
// Purpose: Gets the timer top given the desired velocity in 
// indices/sec.
// 
// ----------------------------------------------------------------
static uint16_t Get_Top(uint16_t Vel)
{
  double top;
  top =  ((double)F_CPU)/(((double)TIMER_PRESCALER)*((double)Vel))-1.0;
  return (uint16_t) top;
}

// ---------------------------------------------------------------
// Function: Clk_Dir_On
//
// Purpose: Enables clock and direction pins
//
// ---------------------------------------------------------------
static void Clk_Dir_On(void)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  CLK_DIR_DDR |= (1<<CLK_DDR_PIN);
  CLK_DIR_DDR |= (1<<DIR_DDR_PIN);
  SREG = sreg;
  return;
}

// ---------------------------------------------------------------
// Function: Clk_Dir_Off
//
// Purpose: Disables clock and direction pins
//
// ---------------------------------------------------------------
static void Clk_Dir_Off(void)
{
  uint8_t sreg;
  sreg = SREG;
  cli();
  CLK_DIR_DDR &= ~(1<<CLK_DDR_PIN);
  CLK_DIR_DDR &= ~(1<<DIR_DDR_PIN);
  SREG = sreg;
  return;
}

// -----------------------------------------------------------------
// Function: IO_Upate
//
// Purpose: Updates the clock and direction pins, sets the output
// compare register, and the timer top. 
//
// -----------------------------------------------------------------
static void IO_Update(void)
{
  uint8_t sreg;
  uint16_t timer_top;

  sreg = SREG;
  cli();

  // Set direction line
  if (Sys_State.Dir == DIR_NEG) {
    CLK_DIR_PORT |= (1 << DIR_PORT_PIN);
  }
  else {
    CLK_DIR_PORT &= ~(1 << DIR_PORT_PIN);
  }

  // Compute top
  timer_top = Get_Top(Sys_State.Vel);
  timer_top = timer_top > TIMER_TOP_MIN ? timer_top : TIMER_TOP_MIN;
  timer_top = timer_top < TIMER_TOP_MAX ? timer_top : TIMER_TOP_MAX;

  // Update clock frequency and pulse width 
  TIMER_OCR = timer_top/2;
  TIMER_TOP = timer_top;
  SREG = sreg;

  return;
}

// ------------------------------------------------------------------
// Function: Pos_Mode_IO_Update
//
// Purpose: Updates IO for position mode. Sets direction based on the
// sign of the position error. If not already at the set point sets
// the velocity to the positioning velocity and enables clock and 
// direction output.
//
// ------------------------------------------------------------------
static void Pos_Mode_IO_Update(void)
{
  int32_t Pos_Err;

  // Set direction based on position error
  Pos_Err = Get_Pos_Err();
  if (Pos_Err > 0) {
    Sys_State.Dir = DIR_POS;
  }
  else {
    Sys_State.Dir = DIR_NEG;
  }

  // If we are not at the set point set velocity, turn on clock and 
  // direction commands, and set status to RUNNING.
  if ((Pos_Err != 0) && (Sys_State.Status==RUNNING)) {
    Clk_Dir_On();
    Sys_State.Vel = Sys_State.Pos_Mode.Pos_Vel;
  }
  else {
    Sys_State.Vel = 0;
    Clk_Dir_Off();
  }
  IO_Update();
  return;
}

// --------------------------------------------------------------------
// Function: Vel_Mode_IO_Update
//
// Purpose: Upates IO for velocity mode. If velocity is greater than 
// minimum allowed value then the clock and direction commands are 
// turned on.
//
// -------------------------------------------------------------------- 
static void Vel_Mode_IO_Update(void)
{
  Sys_State.Dir = Sys_State.Vel_Mode.Dir_SetPt;

  // Set velocity to set-point velocity
  if ((Sys_State.Status==RUNNING) && 
      (Sys_State.Vel_Mode.Vel_SetPt > Get_Min_Vel())) {       
    Sys_State.Vel = Sys_State.Vel_Mode.Vel_SetPt;
    Clk_Dir_On();
    Vel_Trig_Hi();
  }
  else {
    Sys_State.Vel = 0;
    Clk_Dir_Off();
    Vel_Trig_Lo();
  }
  IO_Update();
  return;
}

// ------------------------------------------------------------------
// Function: USB_Packet_Read
//
// Purpose: Reads a USB data packect.
// ------------------------------------------------------------------
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

// -------------------------------------------------------------------
// Function: USB_Packet_Write
//
// Purpose: Writes a USB data packet.
// -------------------------------------------------------------------
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

// ------------------------------------------------------------------
// Function: REG_16bit_Write
//
// Purpose: Writes data to 16 bit register disabling and 
// re-enabling inerrupts.
//
// -------------------------------------------------------------------
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

// ------------------------------------------------------------------
// Function: ISR(TIMER3_OVF_vect)  
//
// Purpose: Timer overflow interrupt. Increments/Decrement the 
// position counter if system is running. If position mode is set 
// the current position is compared with the set-point. If they are 
// equal the clock and direction commands and disabled, the 
// velocity is set to zero and the status is set to Stopped.
//
// ------------------------------------------------------------------  
ISR(TIMER3_OVF_vect) {

  // If Stopped do nothing
  if ((Sys_State.Status == RUNNING) && (Sys_State.Vel > 0)) {

    // Update Position
    if (Sys_State.Dir == DIR_POS) {
      Sys_State.Pos += (int32_t)1;
    }
    else {
      Sys_State.Pos -= (int32_t)1;
    }

    if (Sys_State.Mode == POS_MODE) {
      // When we hit the set-point stop the clock and direction commands
      if (Sys_State.Pos == Sys_State.Pos_Mode.Pos_SetPt) {
	Clk_Dir_Off();
	Sys_State.Vel = 0;
      }
    }
  } // if ((Sys_State.Status == RUNNING) && ...
  return;
}
