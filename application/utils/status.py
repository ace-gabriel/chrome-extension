
# the follow code is for key handover
KEY_ACCEPTED = 1
KEY_NOT_ACCEPTED = 0
KEY_DESTINATION = 0
KEY_ESTATE = 1
KEY_ILOCK = 2 
KEY_OTHER = 3 

# the follow code is for note
NOTE_USED = 1
NOTE_DISCARDED = 0
NOTE_TYPE_HOME = 0
NOTE_TYPE_OFFER = 1
NOTE_TYPE_USER = 2

# the follow code is for Utility
UTILITY_USED = 1
UTILITY_DISCARDED = 0

# 0 =>discard, 1=>used
IS_ACTIVE_USED = 1
IS_ACTIVE_DISCARDED = 0

# sms message type 
OFFER_READY_MESSAGE = 0
OFFER_FINISHED_MESSAGE = 1
INSPECTION_START = 2
INSPECTION_NEED_FIXATION = 3
INSPECTION_FINISHED = 4
PAYMENT_CONFIRMATION = 5
OFFER_PRIING_MESSAGE = 6
OFFER_FINISHED_MESSAGE_LINK = 'http://www.wehome.io/key-handling?home_id={}'
INSPECTION_FINISHED_LINK = 'http://www.wehome.io/payment?home_id={}'
OFFER_READY_MESSAGE_LINK = 'http://www.wehome.io/myhouse'

# pm progress status
PM_PROGRESS_INIT = 0
PM_PROGRESS_FIRST = 10
PM_PROGRESS_SECOND = 20
PM_PROGRESS_THIRD = 30

# property status
PROPERTY_PENDINNG_STATUS = 0 #default
PROPERTY_INSPECTING_STATUS = 1 #start inspection
PROPERTY_MAINTANENCE_STATUS = 2 #3.4
PROPERTY_APPROVED_STATUS = 3 #3.3
PROPERTY_LEASING_STATUS = 4 # yes
PROPERTY_REJECTED_STATUS = 5 # no
PROPERTY_LEASED_STATUS = 6 #3.5

# wehome status
# 1** => home info status
# 2** => princing status
# 3** => inspection status
DEAL_NOT_PAY_FOR_PM = '310'
DEAL_PAY_FOR_PM = '311'
# 4** => deal status
# 410 => deal agreed
DEAL_AGREED = '410'
# 42* => deal utility info status
DEAL_UTILITY_INFO_WITHOUT_HOA = '420'
DEAL_UTILITY_INFO_WITH_HOA = '421'
# 430 => deal payment info status
DEAL_PAYMENT_INFO = '430'
# 440 => deal closed
DEAL_CLOSED = '440'
# 5** => rented status