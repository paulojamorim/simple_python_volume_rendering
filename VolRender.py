'''
A rudimentary example of rendering basic MRI data 
using PyOpenGL and a 3D texture.

Author: Stou Sandalski

Modified by Paulo Henrique Junqueira Amorim (paulojamorim at gmail.com)

Source: http://www.siafoo.net/snippet/310
License: New BSD


'''

import sys
import numpy, wx
from numpy import arange, array, float32, int8
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.ARB.vertex_buffer_object import *

#from VolRenderSkel import *
import VolRenderSkel
import reader

class RenderHead(VolRenderSkel.VolumeRenderSkeleton):
       
    def __init__(self, parent):
        VolRenderSkel.VolumeRenderSkeleton.__init__(self, parent)

        self.data_scale = None
        self.iso_value = 0.0
        self.noise = True

        # Shader names (if you have your own source)
        self.fragment_src_file = ''
        self.vertex_src_file = ''
        
        self.fragment_shader_src = '''
        // Core
        uniform sampler1D TransferFunction;
        uniform sampler3D VolumeData;
        uniform vec3 DataScale;

        // Passed in from Vertex shader
        varying vec3 ecPosition;
        
        // Flags
        uniform bool EnableLighting;
        uniform int  NumberOfLights;
        uniform float IsoWeight;

        // Lighting Constants (We should get these from the materials?)
        float k_a = 0.1; // Ambient
        float k_d = 0.7; // Diffuse
        float k_s = 0.2; // Specular
        float alpha = 1.1; // shininess

        const float cellSize = 0.005;

        vec3 getGradient(vec3 at)
        {
            return normalize(vec3(texture3D(VolumeData, at + vec3(cellSize, 0.0, 0.0)).w
                                    - texture3D(VolumeData, at - vec3(cellSize, 0.0, 0.0)).w,
                                  texture3D(VolumeData, at + vec3(0.0, cellSize, 0.0)).w
                                    - texture3D(VolumeData, at - vec3(0.0, cellSize, 0.0)).w,
                                  texture3D(VolumeData, at + vec3(0.0, 0.0, cellSize)).w
                                    - texture3D(VolumeData, at - vec3(0.0, 0.0, cellSize)).w
                                 ));
        }
        
        vec3 getPhongBlinnLighting(vec3 N, vec3 V)
        {
            vec3 I = vec3(0.0);
        
            for (int i = 0; i < 1; ++i)
            {
                vec3 L = normalize(gl_LightSource[i].position.xyz - V);
                vec3 R = reflect(L, N);
                vec3 H = (L+V) / length(L+V);
        
                I += k_a*gl_LightSource[i].ambient
                   + k_d*dot(L, N)*gl_LightSource[i].diffuse
                   + k_s*pow(abs(dot(N, H)), alpha)*gl_LightSource[i].specular;
        //           + k_s*pow(abs(dot(R, V)), alpha)*gl_LightSource[i].specular; // Phong
            }
        
            return I;
        }
        
        void main(void)
        {
            // This is a hack isn't it...
            if (gl_TexCoord[0].p < 0.0)
            {
                gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
                return;
            }
            
            // Switch the order of the `stp` to like `spt`, etc. if the 
            // image is in a weird orientation... but you also need
            // to rearange the DataScale.xyz in the same way
            vec3 lookup = gl_TexCoord[0].stp;

            float weight = texture3D(VolumeData, lookup).w;

            if (weight >= IsoWeight + 0.02 || weight <= IsoWeight - 0.02)
            {
//                Using ISO Weight one could potentially generate
//                fake iso-surfaces which could serve as a preview mechanism
//                for real surface extraction algorithms like MarchingCubes, etc.

//                gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
//                return
            }
            
            vec4 color = texture1D(TransferFunction, weight);

            if (EnableLighting)
            {
                color.rgb *= getPhongBlinnLighting(getGradient(lookup), ecPosition);
            }

            gl_FragColor = color;
        }
        '''
        
        self.vertex_shader_src = '''
        uniform vec3 DataScale;
        varying vec3 ecPosition;
        
        void main(void)
        {
            gl_TexCoord[0] = vec4((gl_Vertex.xyz / DataScale) + DataScale - 1.0, 0.0);
            ecPosition = vec3(gl_ModelViewMatrix * gl_Vertex);
            gl_Position = ftransform();
        }
        '''

    def SetupUniforms(self):
        VolRenderSkel.VolumeRenderSkeleton.SetupUniforms(self)
        
        # Init the texture units
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_3D, self.vol_data)
        # Setup VolumeData on Texture Unit 2 (we are using 1 for TransferFunction)
        glUniform1i(glGetUniformLocation(self.program, "VolumeData"), 1)
        glUniform1f(glGetUniformLocation(self.program, "IsoWeight"), self.iso_value)
        glUniform3f(glGetUniformLocation(self.program, "DataScale"), self.data_scale[0], self.data_scale[1], self.data_scale[2])

    def LoadVolumeData(self): #Implementation?
        VolRenderSkel.VolumeRenderSkeleton.LoadVolumeData(self)

        data = reader.DICOMReaderToNumpy(self.data_set)
        
        #invert axis
        data = data.reshape(data.shape[2], data.shape[1], data.shape[0])

        """
        if self.data_set.endswith('nii') or self.data_set.endswith('nii.gz'):
            try:
                from nifti import NiftiImage
            except ImportError:
                print "Apparently you don't have PyNIfTI installed, see http://www.siafoo.net/snippet/310 for instructions"
                exit(1)
                
            nim = NiftiImage(canvas.data_set)
            data = nim.data.reshape(nim.data.shape[2], nim.data.shape[1], nim.data.shape[0])
        elif self.data_set.endswith('vol'):
            print "Sorry I can't read '.vol' files yet, why don't you submit a patch?"
            exit(1) 
        elif self.data_set.endswith('hdr'):
            # Use the header to figure out the shape of the data
            # then load the raw data and reshape the array 
            data = numpy.frombuffer(open(self.data_set.replace('.hdr', '.dat'), 'rb').read(), 
                                    numpy.int8)\
                        .reshape([int(x) for x in open(self.data_set).readline().split()])
        else:
            print "Sorry I can't read your file, why don't you submit a patch?"
            exit(1) """

        #from original code
        #self.data_scale = self.data_set_size / self.data_set_size.max()
     
        self.data_set_size = array(data.shape, dtype=numpy.float32)
        self.data_scale = [0.49, 1, 0.49]
        
        print 'Running with: ', self.data_set, self.data_set_size, self.data_scale, self.data_set_size.max()
        
        #import pylab 
        #pylab.imshow(data[1])
        #pylab.show() 
 
        # Create Texture    
        self.vol_data = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glBindTexture(GL_TEXTURE_3D, self.vol_data)
        
        glTexParameterf(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP)
        
        glTexParameterf(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    
        #from original code
        glTexImage3D(GL_TEXTURE_3D, 0, GL_ALPHA, 
                     self.data_set_size[0], self.data_set_size[1], self.data_set_size[2], 
                     0, GL_ALPHA, GL_UNSIGNED_BYTE, data)


        #glTexImage3D(GL_TEXTURE_3D, 0, GL_ALPHA, 
        #             self.data_set_size[1], self.data_set_size[2], self.data_set_size[0], 
        #             0, GL_ALPHA, GL_UNSIGNED_BYTE, data)
 
        
        self.texture_list.append(self.vol_data)
        
        return

    def OnKeyDown(self, event):
        VolRenderSkel.VolumeRenderSkeleton.OnKeyDown(self, event)
        
        if event.GetKeyCode() == ord('n'):
            self.noise = not self.noise
            print 'Noise', self.noise 
            self.Refresh()

if __name__ == '__main__':
    app = wx.App()
    frame = wx.Frame(None, -1, 'Volume Data Visualizer', wx.DefaultPosition, wx.Size(600, 600))
    canvas = RenderHead(frame)
    
    #try:
    canvas.data_set = sys.argv[1]
    #except:
    #canvas.data_set = 'avg152T1_RL_nifti.nii' # NIfTI file
    #canvas.data_set = './Data/TemplateXBAMbet.hdr'
    
    frame.Show()
    app.MainLoop()
