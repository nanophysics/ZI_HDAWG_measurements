# picoscope_module.py
import ctypes
from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import numpy as np

def initialize_picoscope():
    # Create chandle and status ready for use
    chandle = ctypes.c_int16()
    status = {}

    # Open 5000 series PicoScope
    # Resolution set to 12 Bit
    resolution =ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
    # Returns handle to chandle for use in future API functions
    status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(chandle), None, resolution)

    try:
        assert_pico_ok(status["openunit"])
    except: # PicoNotOkError:

        powerStatus = status["openunit"]

        if powerStatus == 286:
            status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
        elif powerStatus == 282:
            status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
        else:
            raise

        assert_pico_ok(status["changePowerSource"])
    return chandle, status

def setup_channels(chandle,status):
    # Set up channel A
    # handle = chandle
    channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
    # enabled = 1
    coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
    chARange = ps.PS5000A_RANGE["PS5000A_10V"]
    # analogue offset = 0 V
    status["setChA"] = ps.ps5000aSetChannel(chandle, channel, 1, coupling_type, chARange, 0)
    assert_pico_ok(status["setChA"])

    # Set up channel B
    # handle = chandle
    channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
    # enabled = 1
    # coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
    chBRange = ps.PS5000A_RANGE["PS5000A_5V"]
    # analogue offset = 0 V
    status["setChB"] = ps.ps5000aSetChannel(chandle, channel, 1, coupling_type, chBRange, 0)
    assert_pico_ok(status["setChB"])

    return status,chARange, chBRange

def setup_trigger(chandle, chARange, chBange, TriggerLevel,status):
    handle = chandle
    maxADC = ctypes.c_int16()
    # pointer to value = ctypes.byref(maxADC)
    
    status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
    assert_pico_ok(status["maximumValue"])

    # # Set up an advanced trigger
    adcTriggerLevel = mV2adc(TriggerLevel*1000, chARange, maxADC)
    # Trigger on channel A
    triggerProperties = ps.PS5000A_TRIGGER_CHANNEL_PROPERTIES_V2(adcTriggerLevel,
                                                                10,
                                                                0,
                                                                10,
                                                                ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"])  # The trigger channel is hardcoded. Will be improved in the future.
                                                                
    status["setTriggerChannelPropertiesV2"] = ps.ps5000aSetTriggerChannelPropertiesV2(chandle, ctypes.byref(triggerProperties), 1, 0)

    triggerConditions = ps.PS5000A_CONDITION(ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"],
                                                            ps.PS5000A_TRIGGER_STATE["PS5000A_CONDITION_TRUE"])

    clear = 1
    add = 2
                                                            
    status["setTriggerChannelConditionsV2"] = ps.ps5000aSetTriggerChannelConditionsV2(chandle, ctypes.byref(triggerConditions), 1, (clear + add))

    triggerDirections = ps.PS5000A_DIRECTION(ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"], 
                                                                ps.PS5000A_THRESHOLD_DIRECTION["PS5000A_RISING"], 
                                                                ps.PS5000A_THRESHOLD_MODE["PS5000A_LEVEL"])

    status["setTriggerChannelDirections"] = ps.ps5000aSetTriggerChannelDirectionsV2(chandle, ctypes.byref(triggerDirections), 1)

    return status,maxADC



def setup_trigger_noTrigger(chandle, chARange, chBange, maxADC, TriggerLevel): #added 31.07.2023
    status = {}

    handle = chandle
    # pointer to value = ctypes.byref(maxADC)
    
    status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
    assert_pico_ok(status["maximumValue"])

    # # Set up an advanced trigger
    adcTriggerLevel = mV2adc(TriggerLevel*1000, chARange, maxADC)
    # Trigger on channel A
    triggerProperties = ps.PS5000A_TRIGGER_CHANNEL_PROPERTIES_V2(adcTriggerLevel,
                                                                10,
                                                                0,
                                                                10,
                                                                ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]) 
                                                                
    status["setTriggerChannelPropertiesV2"] = ps.ps5000aSetTriggerChannelPropertiesV2(chandle, ctypes.byref(triggerProperties), 1, 1)

    triggerConditions = ps.PS5000A_CONDITION(ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"],
                                                            ps.PS5000A_TRIGGER_STATE["PS5000A_CONDITION_TRUE"])

    clear = 1
    add = 2
                                                            
    status["setTriggerChannelConditionsV2"] = ps.ps5000aSetTriggerChannelConditionsV2(chandle, ctypes.byref(triggerConditions), 1, (clear + add))

    triggerDirections = ps.PS5000A_DIRECTION(ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"], 
                                                                ps.PS5000A_THRESHOLD_DIRECTION["PS5000A_RISING"], 
                                                                ps.PS5000A_THRESHOLD_MODE["PS5000A_LEVEL"])

    status["setTriggerChannelDirections"] = ps.ps5000aSetTriggerChannelDirectionsV2(chandle, ctypes.byref(triggerDirections), 1)

    return status

def capture_data_block(chandle, preTriggerSamples, postTriggerSamples, timebase, maxSamples):
    status = {}
    timeIntervalns = ctypes.c_float()
    returnedMaxSamples = ctypes.c_int32()
    cmaxSamples = ctypes.c_int32(maxSamples)

    status["getTimebase2"] = ps.ps5000aGetTimebase2(chandle, timebase, maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
    assert_pico_ok(status["getTimebase2"])
    status["runBlock"] = ps.ps5000aRunBlock(chandle, preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)
    assert_pico_ok(status["runBlock"])
    return status, timeIntervalns

def capture_rapid_data_block(chandle, preTriggerSamples, postTriggerSamples, timebase, maxSamples,noOfCaptures):
    status = {}
    timeIntervalns = ctypes.c_float()
    returnedMaxSamples = ctypes.c_int32()
    cmaxSamples = ctypes.c_int32(maxSamples)
    
    status["MemorySegments"] = ps.ps5000aMemorySegments(chandle, noOfCaptures, ctypes.byref(cmaxSamples))
    assert_pico_ok(status["MemorySegments"])
    status["SetNoOfCaptures"] = ps.ps5000aSetNoOfCaptures(chandle, noOfCaptures)
    assert_pico_ok(status["SetNoOfCaptures"])

    status["getTimebase2"] = ps.ps5000aGetTimebase2(chandle, timebase, maxSamples, ctypes.byref(timeIntervalns), ctypes.byref(returnedMaxSamples), 0)
    assert_pico_ok(status["getTimebase2"])
    status["runBlock"] = ps.ps5000aRunBlock(chandle, preTriggerSamples, postTriggerSamples, timebase, None, 0, None, None)
    assert_pico_ok(status["runBlock"])
    return status, timeIntervalns


def create_buffer(chandle, source, maxSamples, segment_index):
    status={}
    # Create buffers ready for assigning pointers for data collection
    bufferAMax = (ctypes.c_int16 * maxSamples)()
    bufferAMin = (ctypes.c_int16 * maxSamples)() # Assuming you have bufferAMin for each max. Not shown in your code

    # Setting the data buffer location for data collection from source = channel A
    status_key = f"SetDataBuffers_{segment_index}" 
    status[status_key] = ps.ps5000aSetDataBuffers(chandle, source, ctypes.byref(bufferAMax), ctypes.byref(bufferAMin), maxSamples, segment_index,0)
    assert_pico_ok(status[status_key])

    return bufferAMax, bufferAMin

def create_rapid_buffer(chandle, source, maxSamples, noOfCaptures):
    status={}
    buffersMax = []
    buffersMin = []
    
    for segment_index in range(noOfCaptures):  # Iterating 10 times for segment indices from 0 to 9
        # Create buffers ready for assigning pointers for data collection
        bufferMax = (ctypes.c_int16 * maxSamples)()
        bufferMin = (ctypes.c_int16 * maxSamples)()  # You seem to have missed initializing the bufferMin in some of your code snippets. Make sure to include it if necessary.
        
        # Setting the data buffer location for data collection from channel A
        # status["SetDataBuffers"] = ps.ps5000aSetDataBufferBulk(chandle, source, ctypes.byref(bufferMax), ctypes.byref(bufferMin), maxSamples, segment_index,0)
        status["SetDataBuffers"] = ps.ps5000aSetDataBuffers(chandle, source, ctypes.byref(bufferMax), ctypes.byref(bufferMin), maxSamples, segment_index,0)
        assert_pico_ok(status["SetDataBuffers"])
    
        buffersMax.append(bufferMax)
        buffersMin.append(bufferMin)
    
    return buffersMax, buffersMin


def getValuesRapid(chandle,maxSamples,noOfCaptures):
    status = {}
    # create overflow loaction
    overflow = (ctypes.c_int16 * noOfCaptures)()
    cmaxSamples = ctypes.c_int32(maxSamples)
    

    # Handle = chandle
    # noOfSamples = ctypes.byref(cmaxSamples)
    # fromSegmentIndex = 0
    # ToSegmentIndex = 9
    # DownSampleRatio = 0
    # DownSampleRatioMode = 0
    # Overflow = ctypes.byref(overflow)

    status["GetValuesBulk"] = ps.ps5000aGetValuesBulk(chandle, ctypes.byref(cmaxSamples), 0, noOfCaptures-1, 0, 0, ctypes.byref(overflow))
    assert_pico_ok(status["GetValuesBulk"])
    
    return status



def getValues(chandle,maxSamples):
    status = {}
    # Set data buffer location for data collection from channel A
    source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
    bufferAMax, bufferAMin = create_buffer(chandle, source, maxSamples, 0)

    # Set data buffer location for data collection from channel B
    source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
    bufferBMax, bufferBMin = create_buffer(chandle, source, maxSamples, 0)

    # create overflow loaction
    overflow = ctypes.c_int16()
    cmaxSamples = ctypes.c_int32(maxSamples)
    # Retried data from scope to buffers assigned above
    # handle = chandle
    # start index = 0
    # pointer to number of samples = ctypes.byref(cmaxSamples)
    # downsample ratio = 0
    # downsample ratio mode = PS5000A_RATIO_MODE_NONE
    # pointer to overflow = ctypes.byref(overflow))
    status["getValues"] = ps.ps5000aGetValues(chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))
    assert_pico_ok(status["getValues"])
    
    return bufferAMax, bufferAMin, bufferBMax, bufferBMin,cmaxSamples


def check_ready(chandle, status):
    ready = ctypes.c_int16(0)
    check = ctypes.c_int16(0)
    while ready.value == check.value:
        status["isReady"] = ps.ps5000aIsReady(chandle, ctypes.byref(ready))
    return status

def create_time_data(maxSamples, timeIntervalns):
    cmaxSamples = ctypes.c_int32(maxSamples)
    time_array = np.linspace(0, (cmaxSamples.value - 1) * timeIntervalns.value, cmaxSamples.value)
    return time_array

def stop_picoscope(chandle,status):
    status["stop"] = ps.ps5000aStop(chandle)
    assert_pico_ok(status["stop"])
    return status


def close_picoscope(chandle,status):
    status["close"] = ps.ps5000aStop(chandle)
    assert_pico_ok(status["close"])
    return status