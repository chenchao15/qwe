import re
import numpy as np
from collections import OrderedDict
import pykeops


############################################################
#     define backend
############################################################

class SetBackend():
    """
    This class is  used to centralized the options used in PyKeops.
    """

    dev = OrderedDict([('CPU',0),('GPU',1)])
    grid = OrderedDict([('1D',0),('2D',1)])
    memtype = OrderedDict([('host',0), ('device',1)])

    possible_options_list = ['auto',
                             'CPU',
                             'GPU',
                             'GPU_1D', 'GPU_1D_device', 'GPU_1D_host',
                             'GPU_2D', 'GPU_2D_device', 'GPU_2D_host'
                             ]

    def define_tag_backend(self, backend, variables, output):
        """
        Try to make a good guess for the backend...  available methods are: (host means Cpu, device means Gpu)
           CPU : computations performed with the host from host arrays
           GPU_1D_device : computations performed on the device from device arrays, using the 1D scheme
           GPU_2D_device : computations performed on the device from device arrays, using the 2D scheme
           GPU_1D_host : computations performed on the device from host arrays, using the 1D scheme
           GPU_2D_host : computations performed on the device from host data, using the 2D scheme

        :param backend (str)
        :param variables (tuple)

        :return (tagCPUGPU, tag1D2D, tagHostDevice)
        """

        # check that the option is valid
        if (backend not in self.possible_options_list):
            raise ValueError('Invalid backend. Should be one of ', self.possible_options_list)

        # auto : infer everything
        if backend == 'auto':
            return int(pykeops.gpu_available), self._find_grid(), self._find_mem(variables, output)

        split_backend = re.split('_',backend)
        if len(split_backend) == 1:     # CPU or GPU
            return self.dev[split_backend[0]], self._find_grid(), self._find_mem(variables, output)
        elif len(split_backend) == 2:   # GPU_1D or GPU_2D
            return self.dev[split_backend[0]], self.grid[split_backend[1]], self._find_mem(variables, output)
        elif len(split_backend) == 3:   # the option is known
            return self.dev[split_backend[0]], self.grid[split_backend[1]], self.memtype[split_backend[2]]

    def define_backend(self, backend, variables, output):
        tagCPUGPU, tag1D2D, tagHostDevice = self.define_tag_backend(backend, variables, output)
        return self.dev[tagCPUGPU], self.grid[tag1D2D], self.memtype[tagHostDevice]

    @staticmethod
    def _find_dev():
        return int(pykeops.gpu_available)

    @staticmethod
    def _find_mem(variables, output):
        """Infer location of the input variables"""
        if output is not None:
            variables = list(variables) + [output]
        # Infer if numpy arrays or torch tensors
        if all([type(var) is np.ndarray for var in variables]):
            MemType = 0
        elif pykeops.torch_found: 
            import torch

            if all([type(var) in {torch.Tensor, torch.nn.parameter.Parameter} for var in variables]):
                from pykeops.torch.utils import is_on_device
                vars_on_gpu = [is_on_device(var) for var in variables]
                if all(vars_on_gpu):
                    MemType = 1
                elif not any(vars_on_gpu):
                    MemType = 0
                else:
                    raise ValueError('At least two variables have different memory locations (Cpu/Gpu).')
        else:
            raise TypeError('All variables should either be numpy arrays or torch tensors.')

        return MemType

    @staticmethod
    def _find_grid():
        return 0


def get_tag_backend(backend, variables, output=None, str=False):
    """
    entry point to get the correct backend
    """
    res = SetBackend()
    if not str:
        return res.define_tag_backend(backend, variables, output)
    else:
        return res.define_backend(backend, variables, output)
