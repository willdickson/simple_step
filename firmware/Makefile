SRC_DIR=src/
PWD=$(shell pwd)

default: firmware

firmware:
	$(MAKE) -C $(PWD)/$(SRC_DIR)

.PHONY: clean program

clean:
	$(MAKE) clean -C $(PWD)/$(SRC_DIR)	
	-rm *~

program:
	$(MAKE) program -C $(PWD)/$(SRC_DIR)