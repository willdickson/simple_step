/* ----------------------------------------------------------------------
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
  
------------------------------------------------------------------------*/
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

/* Serial Number */
#define SERIAL_NUMBER {SN0,'.',SN1,'.',SN2,'.',SN3,'.',SN4,'.',SN5,'.',SN6} 

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
