import numpy as np
import logging
import socketserver
import threading
import flask.cli
import numpy as np
from flask import Flask, request
from PyDAQmx.DAQmxFunctions import *
from PyDAQmx.DAQmxConstants import *
from laboneq.core.types.compiled_experiment import CompiledExperiment
from laboneq.pulse_sheet_viewer.pulse_sheet_viewer import PulseSheetViewer
from laboneq.simulator.output_simulator import OutputSimulator
from laboneq.simple import *

def interactive_psv(compiled_experiment, inline=True):


    name = compiled_experiment.experiment.uid
    html_text = PulseSheetViewer.generate_viewer_html_text(
        compiled_experiment.schedule, name, interactive=True
    )
    simulation = OutputSimulator(compiled_experiment)
    exp = compiled_experiment.experiment
    ds = compiled_experiment.device_setup

    app = Flask(__name__)

    @app.route("/get_signal")
    def get_sim():
        signal_id = request.args.get("signal_id")
        start = float(request.args.get("start"))
        stop = float(request.args.get("stop"))
        lsg, ls = exp.signals[signal_id].mapped_logical_signal_path.split("/")[2:]
        pc = ds.logical_signal_groups[lsg].logical_signals[ls].physical_channel
        snip = simulation.get_snippet(pc, start, stop - start)
        return {
            "time": snip.time.tolist(),
            "name_i": "I",
            "name_q": "Q" if np.iscomplexobj(snip.wave) else "",
            "samples_i": snip.wave.real.tolist(),
            "samples_q": snip.wave.imag.tolist() if np.iscomplexobj(snip.wave) else [],
        }

    @app.route("/psv.html")
    def psv_html():
        return html_text

    with socketserver.TCPServer(("127.0.0.1", 0), None) as s:
        free_port = s.server_address[1]
    # The free_port may still be taken here until server binds to it, but probability is acceptably low

    base_addr = f"127.0.0.1:{free_port}"
    url = f"http://{base_addr}/psv.html"
    app.config["SERVER_NAME"] = base_addr

    # Suppress flask/werkzeug console output
    flask.cli.show_server_banner = lambda *args, **kw: None
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    embed = False
    if inline:
        try:
            from IPython import get_ipython

            embed = get_ipython() is not None
        except ImportError:
            pass
    if embed:
        threading.Thread(target=app.run, daemon=True).start()
        # Not waiting for the server startup, browser seems to handle it.
        from IPython.display import IFrame, display

        display(IFrame(url, "100%", 700))
    else:
        print(f"Open PSV at: {url}")
        print("Press CTRL+C (or interrupt the kernel in jupyter) to stop the server.")
        app.run()


n_samples_real = 1024
n_samples_complex = 128

sample_list_real = np.random.randn(n_samples_real)
sample_list_complex = np.random.randn(n_samples_complex) + 1j * np.random.randn(
    n_samples_complex
)

sampled_pulse_real = pulse_library.PulseSampledReal(
    samples=sample_list_real, uid="real_pulse"
)

sampled_pulse_complex = pulse_library.PulseSampledComplex(
    samples=sample_list_complex, uid="complex_pulse"
)

@pulse_library.register_pulse_functional
def ramp(x,start=0,stop=1 , **_):
    pulse=start+ (stop-start)*(x+1)/2
    return pulse



class MultiChannelAnalogInput(object):
    """Class to create a multi-channel analog input
    
    Usage: AI = MultiChannelInput(physicalChannel)
        physicalChannel: a string or a list of strings
    optional parameter: limit: tuple or list of tuples, the AI limit values
                        reset: Boolean
    Methods:
        read(name), return the value of the input name
        readAll(), return a dictionary name:value
    """
    def __init__(self,physicalChannel, limit = None, reset = False):
        self.taskHandle = None
        if type(physicalChannel) == type(""):
            self.physicalChannel = [physicalChannel]
        else:
            self.physicalChannel  =physicalChannel
        self.nCh = physicalChannel.__len__()
        if limit is None:
            self.limit = dict([(name, (-10.0,10.0)) for name in self.physicalChannel])
        elif type(limit) == tuple:
            self.limit = dict([(name, limit) for name in self.physicalChannel])
        else:
            self.limit = dict([(name, limit[i]) for  i,name in enumerate(self.physicalChannel)])           
        if reset:
            DAQmxResetDevice(physicalChannel[0].split('/')[0] )
            
    def configure(self, address , rate=10000., nSample=1E3, trig=None, trigSlopePositive=True, trigLevel=0.0):
        # Create one task handle for all
        self.rate = rate
        self.nSample = nSample
        self.taskHandle = TaskHandle(0)
        DAQmxCreateTask("",byref(self.taskHandle))
        for name in self.physicalChannel:
            DAQmxCreateAIVoltageChan(self.taskHandle,name,"",DAQmx_Val_RSE,
                                     self.limit[name][0],self.limit[name][1],
                                     DAQmx_Val_Volts,None)
        print(nSample)
        DAQmxCfgSampClkTiming(self.taskHandle,"",float(rate),DAQmx_Val_Rising,DAQmx_Val_FiniteSamps,int(nSample))
        if trig is None:
            DAQmxDisableStartTrig(self.taskHandle)
        elif str(trig).startswith('%s/port' % address):
            # digital trigger
            trigEdge = DAQmx_Val_Rising if trigSlopePositive else DAQmx_Val_Falling 
            DAQmxCfgDigEdgeStartTrig(self.taskHandle,str(trig),trigEdge)
        else:
            # analog trigger
            trigSlope = DAQmx_Val_RisingSlope if trigSlopePositive else DAQmx_Val_FallingSlope 
            DAQmxCfgAnlgEdgeStartTrig(self.taskHandle,str(trig),trigSlope,trigLevel)

    def readAll(self):
        DAQmxStartTask(self.taskHandle)
        data = np.zeros((self.nCh*self.nSample,), dtype=np.float64)
#        data = AI_data_type()
        read = int32()
        DAQmxReadAnalogF64(self.taskHandle,self.nSample,10.0,DAQmx_Val_GroupByChannel,data,len(data),byref(read),None)
        DAQmxStopTask(self.taskHandle)
        # output data as dict
        dOut = dict()
        for n, name in enumerate(self.physicalChannel):
            dOut[name] = data[(n*self.nSample):((n+1)*self.nSample)]
        return dOut
    def closeAll(self):
        # close all channels
        if self.taskHandle is None:
            return
        DAQmxStopTask(self.taskHandle)
        DAQmxClearTask(self.taskHandle)  

def getTriggerSource(trigSource, trigLevel,lChName,lChDig): 
    print(trigSource)
    if trigSource == 'Immediate':
        trigSource = None
        trigSlopePositive = True
        trigLevel = 0.0
    else:
        # trig from channel
        iTrig = trigSource  
        if iTrig < len(lChName):
            trigSource = lChName[iTrig]
        else:
            trigSource = lChDig[iTrig-len(lChName)]

        trigSlopePositive = True
    return trigSource, trigSlopePositive ,trigLevel