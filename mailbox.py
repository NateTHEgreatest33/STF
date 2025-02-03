#*********************************************************************
#
#   MODULE NAME:
#       mailbox.py - mailboxAPI Interfacing Class
#
#   DESCRIPTION:
#       Class to provide functionaility for interacting with the Raspberry
#		pi pico through the mailboxAPI
#
#   Copyright 2025 by Nate Lenze
#*********************************************************************

#---------------------------------------------------------------------
#                              IMPORTS
#--------------------------------------------------------------------- 
import time
import numpy as np # required for float32
from enum import IntEnum

# from msgAPI import messageAPI
from util.msgAPI_sim import messageAPI


#---------------------------------------------------------------------
#                              CONSTANTS
#--------------------------------------------------------------------- 
ACK_ID        = 0xFF
MSG_UPDATE_ID = 0xFE

#---------------------------------------------------------------------
#                            HELPER CLASSES
#--------------------------------------------------------------------- 
class modules(IntEnum):
    RPI_MODULE  = 0
    TIVA_MODULE = 1    
    PICO_MODULE = 2

    NUM_MODULES = 3
    MODULE_ALL  = 4

class special_response(IntEnum):
    ACK_ID = 0xFF
    MSG_UPDATE_ID = 0xFE

#---------------------------------------------------------------------
#                              VARIABLES
#--------------------------------------------------------------------- 
global_mailbox = [
# data, type,   flag,  dir,  src,                    dest
[ 0,   'ASYNC', False, 'RX', modules.RPI_MODULE,  modules.PICO_MODULE ],
[ 0.0, '1',     False, 'TX', modules.PICO_MODULE, modules.RPI_MODULE  ],
[ 0,   '5',     False, 'TX', modules.RPI_MODULE,  modules.PICO_MODULE ],
 ]

#---------------------------------------------------------------------
#                              CLASSES
#---------------------------------------------------------------------

class Mailbox():
    # ==================================
    # constructor() 
    # ==================================	
    def __init__(self, msg_conn, gbl_mailbox, manage_lst = None ):
        self.msg_conn          = msg_conn
        self.mailbox_map       = gbl_mailbox

        self.round_counter     = 0 # round counter always starts at 0 
        self.ack_list          = []
        self.expecting_ack_map = {}
        self.current_round     = 0
        self.tx_queue          = []

		# ------------------------------------
		# By default we only manage the
        # current module (ourself). However for
        # testing we can manage multiple modules
		# ------------------------------------
        self.manage_list       = [ msg_conn.currentModule ] if manage_lst is None else manage_lst
        if manage_lst != None:
            # we need to make changes to msgAPI to provide destination data before we can implement here
            raise( NotImplementedError )

	# ==================================
    # mailbox_runtime() 
    # ==================================	
    def mailbox_runtime( self ):
		# ------------------------------------
		# Call Rx and Tx Functions
		# ------------------------------------
        self.rx_runtime()
        self.tx_runtime()


	# ==================================
    # rx_runtime() 
    # ==================================	
    def rx_runtime( self ):
		# ------------------------------------
		# Determine if we have any new messages
        # and exit if not
		# ------------------------------------
        rtn_data = self.msg_conn.RX_Multi()
        if( rtn_data == None ):
            return
        
		# ------------------------------------
		# Parse new message data
		# ------------------------------------
        num_rx, data_rx = rtn_data

		# ------------------------------------
		# Loop through each message
		# ------------------------------------
        if num_rx != 0:
            for msg in data_rx:
                rx_src, rx_data, rx_validity = msg

                # -----------------------------
                # Do not handle if validity is
                # False
                # -----------------------------
                if rx_validity != True:
                    print("Invalid msg Rx'ed: src/{} data/{} valid/{}".format(rx_src, rx_data, rx_validity))
                    continue

                # -----------------------------
                # Parse raw MsgAPI
                # -----------------------------
                self.__parse_rx( rx_data )

	# ==================================
    # tx_runtime() 
    # ==================================
    def tx_runtime( self ):
		# ------------------------------------
		# Exit if it is not our turn to transmit
		# ------------------------------------
        if self.current_round != self.msg_conn.currentModule:
            return
        
		# ------------------------------------
		# Verify Acks
		# ------------------------------------
        for idx in self.expecting_ack_map:
            # ---------------------------------
            # If missing an ACK, report error &
            # clear for next round
            # ---------------------------------
            if self.expecting_ack_map[idx] == True:
                print("Missing ACK for idx {}".format( idx ) )
                self.expecting_ack_map[ idx ] = False

		# ------------------------------------
		# Loop through each entry in map and
        # handle any that need handling
		# ------------------------------------
        for idx, [data, rate, flag, dir, src, dest] in enumerate(self.mailbox_map):
            if( src == self.msg_conn.currentModule ):
                # ----------------------------
                # Only handle if:
                # 1) ASYNC and flagged 
                # *OR*
                # 2) Round % cntr == 0 
                # -----------------------------
                if ( rate == 'ASYNC' and flag == True ) or ( rate != 'ASYNC' and ( self.round_counter % int(rate) == 0) ):
                    self.tx_queue.append( ['data', idx] )
                    self.expecting_ack_map[ idx ] = True

		# ------------------------------------
		# Add round updater to tx queue
		# ------------------------------------
        self.tx_queue.append( [ 'round', 0 ] ) 

		# ------------------------------------
		# Pack and send Tx queue
		# ------------------------------------
        self.__msg_interface_pack_and_send()

		# ------------------------------------
		# Update round counter
        # 
        # NOTE: this is different than current
        # round, this is used to associate TX
        # rate by rate of tx_runtime()
		# ------------------------------------
        self.round_counter = (self.round_counter + 1) % 100

	# ==================================
    # __msg_interface_pack_and_send() 
    # ==================================	
    def __msg_interface_pack_and_send( self ):
		# ------------------------------------
		# setup local variables
		# ------------------------------------
        msg_data = []
        msg_dest = None

		# ------------------------------------
		# Loop through TX queue
		# ------------------------------------
        for data_type, data_idx in self.tx_queue:
            # --------------------------------
            # Switch case based upon TX type
            # --------------------------------
            match data_type:
                # ----------------------------
                # Data Type
                # ----------------------------
                case 'data':
                    data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                    data_size = 1 if type(data_var) is bool else 4
                    data_dest = dest

                    # ------------------------
                    # Because u32, flt and bool
                    # are formatted differently
                    # in binary, we need to
                    # handle formatting
                    # ------------------------
                    data_formated = self.__data_type_handler( data_var, data_idx )

                # ----------------------------
                # Ack Type
                # ----------------------------
                case 'ack':
                    data_var, rate, flag, dir, src, dest = self.mailbox_map[data_idx]
                    data_size = 1
                    data_dest = src

                    data_formated = [ACK_ID, data_idx]

                # ----------------------------
                # Round Update Type
                # ----------------------------
                case 'round':
                    data_size = 1
                    data_dest = modules.MODULE_ALL
                    # ------------------------
                    # Updates the current round
                    # and handles rollover
                    # ------------------------
                    self.__round_update()

                    data_formated = [ MSG_UPDATE_ID, self.current_round ]

                # ----------------------------
                # Default case error
                # ----------------------------
                case _:
                    raise( "Incorrect data type" )

            # --------------------------------
            # Update destination based upon:
            # if this is the first time updating
            # or if destinations do not match
            # --------------------------------
            if msg_dest == None:
                msg_dest = data_dest
            elif msg_dest != data_dest:
                msg_dest = modules.MODULE_ALL

            # --------------------------------
            # Determine if new data can fit
            # into current message. if not, TX
            # current message and begin building
            # new message
            # --------------------------------
            if (len(msg_data) + len(data_formated) ) > 10:
                # ----------------------------
                # Tx and update msg_data & 
                # msg_dest w/ new params
                # ----------------------------
                self.msg_conn.TXMessage( msg_data, msg_dest )

                msg_data = []
                msg_dest = data_dest
            
            # --------------------------------
            # Add formatted data to end of 
            # msg_data
            # --------------------------------
            for data_bytes in data_formated:
                msg_data.append( data_bytes )


		# ------------------------------------
		# Run this one last time incase we have
        # a half full message upon exit.
		# ------------------------------------
        if len(msg_data) != 0:
            self.msg_conn.TXMessage( msg_data, msg_dest )

		# ------------------------------------
		# Empty queue for next run
		# ------------------------------------
        self.tx_queue = []

	# ==================================
    # __data_type_handler()
    #
    # DESC: formats int32, float32, and
    #       bools into uint8 list
    # ==================================	
    def __data_type_handler( self, data, idx ):
		# ------------------------------------
		# switch based upon data type of data
		# ------------------------------------
        match( data ):
            # --------------------------------
            # integer
            # --------------------------------
            case int():
                return [ idx, (data >> 24 ), ((data >> 16) & 0x000000FF), ((data >> 8) & 0x000000FF), (data & 0x000000FF)]
            # --------------------------------
            # bool
            # --------------------------------
            case bool():
                return [ idx, int(data) ]
            # --------------------------------
            # float
            # --------------------------------
            case float():
                temp_data = np.float32(data)
                return [ idx, (temp_data >> 24 ), ((temp_data >> 16) & 0x000000FF), ((temp_data >> 8) & 0x000000FF), (temp_data & 0x000000FF)]
            # --------------------------------
            # Default case
            # --------------------------------
            case _:
                print(" unsupported data type")

	# ==================================
    # __round_update() 
    # ==================================	
    def __round_update( self ):
		# ------------------------------------
		# Update current round & account for
        # rollovers
		# ------------------------------------
        self.current_round = (self.current_round + 1 ) % len( self.msg_conn.listOfModules )

	# ==================================
    # __parse_rx() 
    # ==================================	
    def __parse_rx(self, rx_data ):
		# ------------------------------------
		# setup variables
		# ------------------------------------
        idx = 0

		# ------------------------------------
		# Loop through each index in rx_data
		# ------------------------------------
        while idx < len( rx_data):
            # --------------------------------
            # aquire first byte and switch 
            # based upon if it is an ACK, DATA,
            # or ROUND update
            # --------------------------------
            data_type = rx_data[idx]
            match( data_type ):
                # ----------------------------
                # ACK Handling
                # ----------------------------
                case special_response.ACK_ID:
                    idx = idx + 1
                    self.expecting_ack_map[ rx_data[idx] ] = False
                    idx = idx+1 # place index for next data
                # ----------------------------
                # UPDATE Handling
                # ----------------------------
                case special_response.MSG_UPDATE_ID:
                    raise( NotImplementedError )
                    idx = idx + 1 
                    new_rnd = rx_data[idx]
                    self.__round_update()
                    if new_rnd != self.current_round:
                        print("Missing RX? New Round Requested out of order") #ISSUE! what happens when instead of being by itself its in a dest ALL packet, we will reach here
                        self.current_round = new_rnd

                    idx = idx+1 #place index for next data
                # ----------------------------
                # DATA/Default Handling
                # ----------------------------
                case _:
                    idx = idx + self.__data_rx_handler( rx_data[idx+1:], data_type )
                    self.tx_queue.append( [ 'ack', data_type ] ) 

	# ==================================
    # __data_rx_handler() 
    # ==================================	
    def __data_rx_handler( self, data, idx ):
		# ------------------------------------
		# Aquire variables from mailbox map
		# ------------------------------------
        data_var, rate, flag, dir, src, dest = self.mailbox_map[ idx ]

		# ------------------------------------
		# Set flag to True for data RX
		# ------------------------------------
        flag = True

		# ------------------------------------
		# switch based upon data type and how
        # to reconstruct data
		# ------------------------------------
        match( data_var ):
            # --------------------------------
            # INT -- 4 bytes + idx byte = 5
            # --------------------------------
            case int():
                data_var = int( (data[0] << 24 ) | (data[1] << 16) | (data[2] << 8) | data[3] )
                return 5 # msg size
            
            # --------------------------------
            # BOOL -- 1 byte + idx byte = 2
            # --------------------------------
            case bool():
                data_var = bool( data[0] )
                return 2 # msg size
            
            # --------------------------------
            # FLOAT -- 4 bytes + idx byte = 5
            # --------------------------------
            case float():
                raise( NotImplementedError )
                data_var = np.float32(data)
                return 5 # msg size
            
            # --------------------------------
            # DEFAULT
            # --------------------------------
            case _:
                print(" unsupported data type")

#---------------------------------------------------------------------
#                               MAIN
#---------------------------------------------------------------------
def main():
    # pico = pi_pico()
    msg_conn = messageAPI(  bus = 0, 
                            chip_select = 0, 
                            currentModule = 0x00, 
                            listOfModules=[0x00,0x01,0x02] )
    mailbox = Mailbox( msg_conn, global_mailbox )

 

    while( True ):
        #run every 10ms
        time.sleep(.5)    
        mailbox.mailbox_runtime()
        #force it to be an us round everytime
        # mailbox.current_round = 0

        ack_msg = [ int(special_response.ACK_ID), 0x02 ]
        msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=ack_msg, validity=True)


        #send data to be acked
        #note bc we send 2x for every tx_runtime we need to ack 2-3 times
        msg_to_ack = [ 0, 0, 0, 0, 1] #data from index 1
        msg_conn.rx_data_fill(src=int(modules.PICO_MODULE), data=msg_to_ack, validity=True)

        #update rounds
        new_rnd = (mailbox.current_round + 1 )% modules.NUM_MODULES
        round_update_msg= [ int(special_response.MSG_UPDATE_ID), new_rnd ]
        msg_conn.rx_data_fill(src=int(modules.RPI_MODULE), data=round_update_msg, validity=True)


#---------------------------------------------------------------------
#                              RUN
#---------------------------------------------------------------------
if __name__ == "__main__":
    main()