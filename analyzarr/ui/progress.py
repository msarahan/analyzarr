from traits.api import Instance, Int, HasTraits
from pyface.api import ProgressDialog

# TODO: this should be abstracted to use whatever graphical 
#       or command-line environment we're in.

class IProgress(HasTraits):
    """
    An interface class to guide the creation of other progress indicators.  All progress
    indicators must implement this API.  They're free to implement any other members or
    functions to get the job done, but these are the ones that get called elsewhere in the code
    on progress objects.
    """
    progress = Instance(ProgressDialog)
    current_idx = Int(0)
    def initialize(title, max_index):
        raise NotImplementedError("initialize not implemented in interface!")
    
    def increment():
        raise NotImplementedError("increment not implemented in interface!")

class PyFaceProgress(IProgress):
    def initialize(title, max_index):
        self.progress = ProgressDialog(title="Characterizing %d peaks on current image"%max_index, 
                          max=int(max_index), show_time=True, can_cancel=False)
        self.progress.open()
        
    def increment():
        self.current_idx+=1
        self.progress.update(self.current_idx)

class TextProgress(IProgress):
    pass

