# Hey Emacs, this is a -*- makefile -*-
#------------------------------------------------------------------------
# 
# Makefile for simple_step firmware. 
#
# Modify the variable MYUSB_SRC_DIR so that it gives the absolute path
# to the the location of the MyUSB source.
# 
# -----------------------------------------------------------------------
# On command line:
#
# make all = Make software.
#
# make clean = Clean out built project files.
#
# make program = Download the hex file to the device, using avrdude.
#                Please customize the avrdude settings below first!
#
# To rebuild project do "make clean" then "make all".
# 
# -----------------------------------------------------------------------
SRC_DIR=src/
PWD=$(shell pwd)
MYUSB_SRC_DIR = /usr/local/src/avr/MyUSB_1.4.1/MyUSB

default: firmware

firmware:
	$(MAKE) MYUSB_SRC_DIR=$(MYUSB_SRC_DIR) -C $(PWD)/$(SRC_DIR)

.PHONY: clean program

clean:
	$(MAKE) clean -C $(PWD)/$(SRC_DIR)	
	-rm *~

program:
	$(MAKE) program -C $(PWD)/$(SRC_DIR)