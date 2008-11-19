/*
             MyUSB Library
     Copyright (C) Dean Camera, 2008.
              
  dean [at] fourwalledcubicle [dot] com
      www.fourwalledcubicle.com

 Released under the LGPL Licence, Version 3
*/

#ifndef _DESCRIPTORS_H_
#define _DESCRIPTORS_H_

/* Includes: */
#include <MyUSB/Drivers/USB/USB.h>

#include <avr/pgmspace.h>

/* Macros: */
#define SIMPLE_IN_EPNUM     2	
#define SIMPLE_OUT_EPNUM    1	
#define SIMPLE_IN_EPSIZE    8   
#define SIMPLE_OUT_EPSIZE   8

/* Type Defines: */
typedef struct
{
  USB_Descriptor_Configuration_Header_t Config;
  USB_Descriptor_Interface_t            Interface;
  USB_Descriptor_Endpoint_t             DataInEndpoint;
  USB_Descriptor_Endpoint_t             DataOutEndpoint;
} USB_Descriptor_Configuration_t;

/* External Variables: */
extern USB_Descriptor_Configuration_t ConfigurationDescriptor;

/* Function Prototypes: */
bool USB_GetDescriptor(const uint8_t Type, const uint8_t Index,
		       void** const DescriptorAddr, uint16_t* const Size)
  ATTR_WARN_UNUSED_RESULT ATTR_NON_NULL_PTR_ARG(3, 4);

#endif
