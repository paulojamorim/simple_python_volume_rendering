'''

Modified by Paulo Henrique Junqueira Amorim (paulojamorim at gmail.com)

'''

import vtk
import gdcm
import vtkgdcm
import glob
import os
import numpy as np
from vtk.util import numpy_support

def DICOMReaderToNumpy(directory):
    file_list = glob.glob(directory + os.sep + '*')
    file_list = sorted(file_list)
  
    ipp = gdcm.IPPSorter()
    ipp.SetComputeZSpacing(True)
    ipp.Sort(file_list)

    file_list = ipp.GetFilenames()

    array = vtk.vtkStringArray()

    for x in xrange(len(file_list)):
        array.InsertValue(x,file_list[x])


    read = vtkgdcm.vtkGDCMImageReader()
    read.SetFileNames(array)
    read.Update()

    img = vtk.vtkImageData()
    img.DeepCopy(read.GetOutput())
    img.SetSpacing(1, 1, 1)           
    img.Update()

    ex = img.GetExtent()
    image = vtk.util.numpy_support.vtk_to_numpy(img.GetPointData().GetScalars())
    image = image.reshape((ex[5] +1, ex[1]+1, ex[3]+1))

    return ApplyWindowLevel(image, 2000, 300)


def ApplyWindowLevel(data, window, level):
    return np.piecewise(data,[data <= (level - 0.5 - (window-1)/2),\
                              data > (level - 0.5 + (window-1)/2)],\
                             [0, 255, lambda data: ((data - (level - 0.5))/(window-1) + 0.5)*(255-0)])
