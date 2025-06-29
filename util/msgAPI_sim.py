#*********************************************************************
#
#   MODULE NAME:
#       msgAPI.py - message API core object
#
#   DESCRIPTION:
#       Provides message API functionality
#
#   Copyright 2024 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              IMPORTS
#---------------------------------------------------------------------
import time

#---------------------------------------------------------------------
#                             VARIABLES
#---------------------------------------------------------------------
crc8_table = [
0x00, 0x91, 0xE3, 0x72, 0x07, 0x96, 0xE4, 0x75, 0x0E, 0x9F, 0xED, 0x7C, 0x09, 0x98, 0xEA, 0x7B,
0x1C, 0x8D, 0xFF, 0x6E, 0x1B, 0x8A, 0xF8, 0x69, 0x12, 0x83, 0xF1, 0x60, 0x15, 0x84, 0xF6, 0x67,
0x38, 0xA9, 0xDB, 0x4A, 0x3F, 0xAE, 0xDC, 0x4D, 0x36, 0xA7, 0xD5, 0x44, 0x31, 0xA0, 0xD2, 0x43,
0x24, 0xB5, 0xC7, 0x56, 0x23, 0xB2, 0xC0, 0x51, 0x2A, 0xBB, 0xC9, 0x58, 0x2D, 0xBC, 0xCE, 0x5F,
0x70, 0xE1, 0x93, 0x02, 0x77, 0xE6, 0x94, 0x05, 0x7E, 0xEF, 0x9D, 0x0C, 0x79, 0xE8, 0x9A, 0x0B,
0x6C, 0xFD, 0x8F, 0x1E, 0x6B, 0xFA, 0x88, 0x19, 0x62, 0xF3, 0x81, 0x10, 0x65, 0xF4, 0x86, 0x17,
0x48, 0xD9, 0xAB, 0x3A, 0x4F, 0xDE, 0xAC, 0x3D, 0x46, 0xD7, 0xA5, 0x34, 0x41, 0xD0, 0xA2, 0x33,
0x54, 0xC5, 0xB7, 0x26, 0x53, 0xC2, 0xB0, 0x21, 0x5A, 0xCB, 0xB9, 0x28, 0x5D, 0xCC, 0xBE, 0x2F,
0xE0, 0x71, 0x03, 0x92, 0xE7, 0x76, 0x04, 0x95, 0xEE, 0x7F, 0x0D, 0x9C, 0xE9, 0x78, 0x0A, 0x9B,
0xFC, 0x6D, 0x1F, 0x8E, 0xFB, 0x6A, 0x18, 0x89, 0xF2, 0x63, 0x11, 0x80, 0xF5, 0x64, 0x16, 0x87,
0xD8, 0x49, 0x3B, 0xAA, 0xDF, 0x4E, 0x3C, 0xAD, 0xD6, 0x47, 0x35, 0xA4, 0xD1, 0x40, 0x32, 0xA3,
0xC4, 0x55, 0x27, 0xB6, 0xC3, 0x52, 0x20, 0xB1, 0xCA, 0x5B, 0x29, 0xB8, 0xCD, 0x5C, 0x2E, 0xBF,
0x90, 0x01, 0x73, 0xE2, 0x97, 0x06, 0x74, 0xE5, 0x9E, 0x0F, 0x7D, 0xEC, 0x99, 0x08, 0x7A, 0xEB,
0x8C, 0x1D, 0x6F, 0xFE, 0x8B, 0x1A, 0x68, 0xF9, 0x82, 0x13, 0x61, 0xF0, 0x85, 0x14, 0x66, 0xF7,
0xA8, 0x39, 0x4B, 0xDA, 0xAF, 0x3E, 0x4C, 0xDD, 0xA6, 0x37, 0x45, 0xD4, 0xA1, 0x30, 0x42, 0xD3,
0xB4, 0x25, 0x57, 0xC6, 0xB3, 0x22, 0x50, 0xC1, 0xBA, 0x2B, 0x59, 0xC8, 0xBD, 0x2C, 0x5E, 0xCF]

LORA_FIFO_SIZE = 0x80 

#---------------------------------------------------------------------
#                              CLASSES
#---------------------------------------------------------------------
class messageAPI:
    # ==================================
    # Constructor
    # ==================================
	def __init__(self, bus, chip_select, currentModule, listOfModules):
		print(" WARNING: this is a simulation ONLY messageAPI")
		#setup local var's
		self.currentModule = currentModule
		self.module_all = len(listOfModules) + 1
		self.listOfModules = listOfModules
		self.version_num = 2
		self.curr_key = 0x00
		self.debug_prints = True
		self.last_fifo_idx = 0;
	
		self.rx_return_data = []

    # ==================================
    # InitAPI()
    # ==================================
	def InitAPI(self):
		self.__LoraInit()
		self.__LoraSetRxMode()

    # ==================================
    # TXMessage()
    # ==================================
	def TXMessage(self, message, destination):
		#Verify variables
		message_size = len(message)
		if( message_size > 10):
			#message is too large to send, return false
			return False
		if( int(destination) not in self.listOfModules ) and ( int(destination) != self.module_all):  #
			return False

		version_size_var = (self.version_num << 4 ) | message_size
		# Build message: 
		# Byte 0 -- destination byte
		# Byte 1 -- source byte
		# Byte 2 -- pad (future expantion)
		# Byte 3 -- version/size byte (upper/lower bits)
		# Byte 4 -- key byte
		# Byte 5 -- start of data region
		# Byte X -- crc (last byte)
		message.insert(0, destination)
		message.insert(1, self.currentModule)
		message.insert(2, 0x00 )
		message.insert(3, version_size_var )
		message.insert(4, self.curr_key )
		message.append(self.__updateCRC(message))

		#send message
		print("Sending: {",end =" ")
		for x in message:
		    print(hex(x),end = " ")
		print("}")

		

    # ==================================
    # RX_Single()
    # ==================================
	def RX_Single(self):
            #todo add functionaility to mock Rx'ed data 
			return False, 0xFF, [], True
	
			#print full message
			if self.debug_prints:
				print("Full message received: {",end =" ")
				for x in return_msg:
					print(hex(x),end = " ")
				print("}")

			#Message too small to parse
			if len( return_msg ) < 6:
				return False, 0xFF, [], False
			# Parse message
			# Byte 0 -- destination byte
			# Byte 1 -- source byte
			# Byte 2 -- pad (future expantion)
			# Byte 3 -- version/size byte (upper/lower bits)
			# Byte 4 -- key byte
			# Byte 5 -- start of data region
			# Byte X -- crc (last byte)
			destination = return_msg[0]
			if destination != self.currentModule:
				return False, 0xFF, [], True

			source = return_msg[1]
			version = ( return_msg[3] & 0xF0 ) >> 4
			dataSize = return_msg[3] & 0x0F
			key = return_msg[4]
			data = return_msg[5:-1]
			crc = return_msg[ len( return_msg ) - 1 ]

			#confirm key & crc
			if key != self.curr_key:
				valid = False
			elif crc != self.__updateCRC( return_msg[:-1] ):
				valid = False
			else:
				valid = True

			return True, source, data, valid

            #no data
			return False, 0xFF, [], True

    # ==================================
    # RX_multi()
    # ==================================
	def RX_Multi(self):
		if len(self.rx_return_data) == 0:
			return None
		else:
			# [ num_msg, [source, data, valid] ]
			rtn_data = [ len(self.rx_return_data), self.rx_return_data ]
			self.rx_return_data = []
			return rtn_data
		
		
	def rx_data_fill( self, data, src, validity ):
		msg = [ src, data, validity ]
		self.rx_return_data.append( msg )



    # ==================================
    # RXMessage()
    # ==================================
	def RXMessage(self):
		print( "RX Message as been depricated")
		return self.RX_single()
	
    # ==================================
    # updateKey()
    # ==================================
	def updateKey(self, newKey):
		self.curr_key = newKey	

    # ==================================
    # __updateCRC()
    # ==================================
	def __updateCRC(self, message):
		crc = 0
		for i in message:
			crc = crc8_table[ crc ^ i ]
		return crc

    # ==================================
    # __parseRawLora()
    # ==================================
	def __parseRawLora(self, message):
		#return format [ numRx, [[source, data, validity]] ]
		num_rx = 0
		start_index = 0
		parsed_data = []
		curr_msg = message 

		#Message too small to parse
		if len( curr_msg ) < 6:
			return None

		while( len(curr_msg) > 6 ):
			# Parse message
			# Byte 0 -- destination byte
			# Byte 1 -- source byte
			# Byte 2 -- pad (future expantion)
			# Byte 3 -- version/size byte (upper/lower bits)
			# Byte 4 -- key byte
			# Byte 5 -- start of data region
			# Byte X -- crc (last byte)
			dataSize = curr_msg[3] & 0x0F
			curr_msg = message[start_index:(start_index + 6 + dataSize)]

			destination = curr_msg[0]
			if destination == self.currentModule:
				source = curr_msg[1]
				version = ( curr_msg[3] & 0xF0 ) >> 4
				key = curr_msg[4]
				data = curr_msg[5:-1]
				crc = curr_msg[ len( curr_msg ) - 1 ]

				#confirm key & crc
				if key != self.curr_key:
					valid = False
				elif crc != self.__updateCRC( curr_msg[:-1] ):
					valid = False
				elif version != self.version_num:
					valid = False
				else:
					valid = True

				parsed_data.append( [source, data, valid] )
				num_rx = num_rx + 1

			start_index = start_index + 6 + dataSize
			curr_msg = message[start_index:]

		if num_rx != 0:
			return num_rx, parsed_data
		else:
			return None



#Test API
#module = messageAPI( bus=0, chip_select=0, currentModule=0x00, listOfModules=[0x00,0x01] )
#module.InitAPI()
#module.TXMessage( message=[0x11,0x22,0x33], destination=0x01 )

#while True:
#	return_tpl = module.RXMessage()
#	if return_tpl[0] == True:
#		print("source:", return_tpl[1], "data recvied: ", return_tpl[2]," valid: ", return_tpl[3] )
#
