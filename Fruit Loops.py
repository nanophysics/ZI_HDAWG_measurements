### Fruit Loops 

#im main und imports in program 2 
#look up table, depending on input does different things

#just pulse with 50 reps 

import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: Fruit Loops.py <variable>")
       return
    
    received_variable = sys.argv[1] #converts argumetn to an integer 
    print(f"Program 2 received variable: {received_variable}")

    #processing in program 2 

    #general imports 
    import numpy as np
    import time
    import zhinst.core 
    import laboneq
    from laboneq.simple import * 
    import ctypes
    import helpers
    from picosdk.ps5000a import ps5000a as ps 
    from picosdk.functions import adc2mV, assert_pico_ok, mVadc 
    import picoscope_module as pm 
    DO_EMULATION = False # run in emulation mode by default 

    #defining parameters 
    times_map = {
        'pulse_time': 10e-3, 
        'dead_time': 10e-3, 
        'trigger_time': 1e-3
    }

    #picoscope 
    timebase = 628
    preTriggerSamples = 10
    pico_sampling_rate = (timebase - 3)/62500000
    postTriggerSamples = int(np.ceil(20e-3/pico_sampling_rate))
    TriggerLevel=1
    NUM_REP = 50

    maxSamples = preTriggerSamples + postTriggerSamples
    ready = ctypes.c_int16(0)
    check = ctypes.c_int16(0)
    maxADC = ctypes.c_int16()

    chandle, status = pm.initialize_picoscope()
    chARange, chBRange, status = pm.setup_channels(chandle)

    pm.setup_trigger(chandle, chARange, chBRange, maxADC, TriggerLevel)


    # assign amplitude to received variable
    x = np.linspace(0, 0.1, 51)
    y = np.linspace(0, 0.1, 51)

    x_mesh, y_mesh = np.meshgrid(x, y)
    tensor_product = np.column_stack((x_mesh.ravel(), y_mesh.ravel()))

    read_amplitude=tensor_product[received_variable]
    #read_amplitude=tensor_product[0]


    #Create device setup -HDAWG 
    descriptor="""
    instrument_list:
    HDAWG:
    - address: DEV8721
        uid: device_hdawg
        interface: usb
    connections:
    device_hdawg:
        - rf_signal: q0/fg4_line
        ports: [SIGOUTS/0]
        - rf_signal: q0/fg6_line
        ports: [SIGOUTS/1]
    """
    device_setup = DeviceSetup.from_descriptor(
        descriptor, 
        serivce_host="127.0.0.1", 
        server_port="8004",
        setup_name="ZI_HDAWG",
    )

    #define pulse shapes
    @pulse_library.register_pulse_functional
    def ramp(x,start=0,stop=1,**_):
        pulse=start+ (stop-start)*(x+1)/2
        return pulse
    
    compress_level_pulse=pulse_library.const(uid="compress_level",length=times_map['pulse_time'],amplitude=1,can_compress=True)

    # Experiment
    exp = Experiment(
        "Pulse Experiment",
        signals=[
            ExperimentSignal("gate1"),
            ExperimentSignal("gate2"),
        ],
    )

    with exp.acquire_loop_rt(
        uid=("pulse"), count=NUM_REP, averaging_mode=AveragingMode.SEQUENTIAL
    ):
        with exp.section(
            uid=("unload"),
            length=times_map['pulse_time'],
            trigger={"gate1":{"state":1}},
            alignment=SectionAlignment.LEFT,
        ):
            exp.play(signal="gate1",pulse=compress_level_pulse,amplitude=-0.1)
            exp.play(signal="gate2",pulse=compress_level_pulse,amplitude=-0.1)
        with exp.section(
            uid=("load"),
            length=times_map['pulse_time'],
            alignment=SectionAlignment.LEFT,
        ):
            exp.play(signal="gate1",pulse=compress_level_pulse,amplitude=0.05)
            exp.play(signal="gate2",pulse=compress_level_pulse,amplitude=-0.1)
        with exp.section(
            uid=("measure"),
            length=times_map['dead_time'],
            alignment=SectionAlignment.LEFT, 
        ): 
            exp.play(signal="gate1",pulse=compress_level_pulse,amplitude=read_amplitude[0])
            exp.play(signal="gate2",pulse=compress_level_pulse,amplitude=read_amplitude[1])

    #shortcut to the logical signal group q0
    lsg = device_setup.logical_signal_groups["q0"].logical_signals

    #define signal map
    map_signals ={
        "gate1" : lsg["fg4_line"],
        "gate2" : lsg["fg6_line"]
    }

    source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
    noOfCaptures = NUM_REP
    status,timeIntervalns = pm.capture_rapid_data_block(chandle, preTriggerSamples, postTriggerSamples, timebase, maxSamples,noOfCaptures)

    # create and connect to session
    session = Session(device_setup=device_setup)
    session.connect(do_emulation=DO_EMULATION)
    # set experiment calibration and signal map
    exp.set_signal_map(map_signals)

    if not session.connection_state.emulated:
        instrument_serial = device_setup.instrument_by_uid("device_hdawg").address
        device = session.devices[instrument_serial]
        device.triggers.out[2].delay(23.9e-9)
    print("Loaded exp")
    session.run(exp)
    print("Running exp finished")
    # Check for data collection to finish using ps5000aIsReady
    while ready.value == check.value:
        status["isReady"] = ps.ps5000aIsReady(chandle, ctypes.byref(ready))

    buffersMax, buffersMin = pm.create_rapid_buffer(chandle, source, maxSamples, noOfCaptures)
    pm.getValuesRapid(chandle,maxSamples,noOfCaptures)

    #postprocessing
    # convert ADC counts data to mV
    cmaxSamples = ctypes.c_int32(maxSamples)

    # Create time data
    time_stamp=int(time.time())
    time_array = np.linspace(0, (cmaxSamples.value - 1) * timeIntervalns.value, cmaxSamples.value)
    with open('Data/pulses_%s_a=%s.npy'%(time_stamp,read_amplitude), 'wb') as f:
        np.save(f,time_array)
        for i in range(noOfCaptures):
            np.save(f,adc2mV(buffersMax[i], chARange, maxADC))


    with open('Data/data_%s.txt'%(time_stamp), 'w') as f:
        f.write(str(points_map)+'\n')
        f.write(str(times_map)+'\n')

    # Stop the scope
    status["stop"] = ps.ps5000aStop(chandle)
    assert_pico_ok(status["stop"])

    # Close unit Disconnect the scope 
    status["close"]=ps.ps5000aCloseUnit(chandle)
    assert_pico_ok(status["close"])



if __name__ == "__main__":
    main()