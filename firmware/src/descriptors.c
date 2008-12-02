/* ------------------------------------------------------------------------
  simple_step
  Copyright (C) William Dickson, 2008.
  
  wbd [at] caltech [dot] edu
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

----------------------------------------------------------------------------*/
#include "descriptors.h"

USB_Descriptor_Device_t DeviceDescriptor PROGMEM = {
  Header: {Size: sizeof (USB_Descriptor_Device_t), Type:DTYPE_Device},
  USBSpecification: 0x0101,
  Class: 0x00,
  SubClass: 0x00,
  Protocol: 0x00,
  Endpoint0Size: 32,
  VendorID: 0x1781,
  ProductID: 0x0BB0,
  ReleaseNumber: 0x1000,
  ManafacturerStrIndex: 0x01,
  ProductStrIndex: 0x02,
  SerialNumStrIndex: 0x03,
  NumberOfConfigurations: 1
};

USB_Descriptor_Configuration_t ConfigurationDescriptor PROGMEM = {
  Config:{
    Header: {Size: sizeof(USB_Descriptor_Configuration_Header_t), Type:DTYPE_Configuration},
    TotalConfigurationSize:sizeof (USB_Descriptor_Configuration_t),
    TotalInterfaces:1,
    ConfigurationNumber:1,
    ConfigurationStrIndex:NO_DESCRIPTOR_STRING,
    ConfigAttributes:(USB_CONFIG_ATTR_BUSPOWERED |USB_CONFIG_ATTR_SELFPOWERED),
    MaxPowerConsumption:USB_CONFIG_POWER_MA (100)
  },

  Interface:{
    Header:{Size:sizeof(USB_Descriptor_Interface_t),Type:DTYPE_Interface},
    InterfaceNumber:0,
    AlternateSetting:0,
    TotalEndpoints:2,
    Class:0xFF,
    SubClass:0xFF,
    Protocol:0xFF,
    InterfaceStrIndex:NO_DESCRIPTOR_STRING
  },

  DataInEndpoint:{
    Header: {Size: sizeof(USB_Descriptor_Endpoint_t), Type:DTYPE_Endpoint},
    EndpointAddress:(ENDPOINT_DESCRIPTOR_DIR_IN | SIMPLE_IN_EPNUM),
    Attributes:EP_TYPE_BULK,
    EndpointSize:SIMPLE_IN_EPSIZE,
    PollingIntervalMS:0x00
  },

  DataOutEndpoint:{
    Header: {Size: sizeof(USB_Descriptor_Endpoint_t), Type:DTYPE_Endpoint},
    EndpointAddress:(ENDPOINT_DESCRIPTOR_DIR_OUT | SIMPLE_OUT_EPNUM),
    Attributes:EP_TYPE_BULK,
    EndpointSize:SIMPLE_OUT_EPSIZE,
    PollingIntervalMS:0x00
  }
};

USB_Descriptor_Language_t LanguageString PROGMEM = {
  Header: {Size: sizeof (USB_Descriptor_Language_t), Type:DTYPE_String},
  LanguageID:LANGUAGE_ID_ENG
};

USB_Descriptor_String_t ManafacturerString PROGMEM = {
  Header: {Size: USB_STRING_LEN(12), Type: DTYPE_String},
  UnicodeString:{'W','i','l','l',' ','D','i','c','k','s','o','n'}
};

USB_Descriptor_String_t ProductString PROGMEM = {
  Header: {Size: USB_STRING_LEN(11), Type: DTYPE_String},
  UnicodeString:{'S', 'i', 'm', 'p', 'l', 'e', ' ', 'S', 't', 'e', 'p'}
};

USB_Descriptor_String_t SerialNumberString PROGMEM = {
  Header: {Size: USB_STRING_LEN(13), Type:DTYPE_String},
  UnicodeString:{'0','.','0','.','0','.','0','.','0','.','0','.','0'}
};

bool
USB_GetDescriptor (const uint8_t Type, const uint8_t Index,
		   void **const DescriptorAddr, uint16_t * const Size)
{
  void *DescriptorAddress = NULL;
  uint16_t DescriptorSize = 0;

  switch (Type)
    {
    case DTYPE_Device:
      DescriptorAddress = DESCRIPTOR_ADDRESS (DeviceDescriptor);
      DescriptorSize = sizeof (USB_Descriptor_Device_t);
      break;
    case DTYPE_Configuration:
      DescriptorAddress = DESCRIPTOR_ADDRESS (ConfigurationDescriptor);
      DescriptorSize = sizeof (USB_Descriptor_Configuration_t);
      break;
    case DTYPE_String:
      switch (Index)
	{
	case 0x00:
	  DescriptorAddress = DESCRIPTOR_ADDRESS (LanguageString);
	  DescriptorSize = sizeof (USB_Descriptor_Language_t);
	  break;
	case 0x01:
	  DescriptorAddress = DESCRIPTOR_ADDRESS (ManafacturerString);
	  DescriptorSize = pgm_read_byte (&ManafacturerString.Header.Size);
	  break;
	case 0x02:
	  DescriptorAddress = DESCRIPTOR_ADDRESS (ProductString);
	  DescriptorSize = pgm_read_byte (&ProductString.Header.Size);
	  break;
	case 0x03:
	  DescriptorAddress = DESCRIPTOR_ADDRESS (SerialNumberString);
	  DescriptorSize = pgm_read_byte (&SerialNumberString.Header.Size);
	  break;
	}

      break;
    }

  if (DescriptorAddress != NULL)
    {
      *DescriptorAddr = DescriptorAddress;
      *Size = DescriptorSize;
      return true;
    }
  return false;
}
