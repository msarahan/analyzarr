import numpy as np
from pylab import mgrid
from matplotlib import pyplot as plt
from scipy.ndimage import rotate

plt.ion()

def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x,y: height*np.exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)
                
test_array = np.zeros((1024,1024))
# establish first the regular positions
initial_position = np.array([16, 16])
positionX = initial_position[1]
positionY = initial_position[0]
# the offset between peaks
offset = 32
peak_size = 17
frame_size = 32

# the normal gaussian
xg, yg = mgrid[0:peak_size*2, 0:peak_size*2]
data = gaussian(255, (frame_size/2)+1, (frame_size/2)+1, (peak_size/4)+1, 
        (peak_size/4)+1)(xg, yg)

while positionY < (test_array.shape[1]-data.shape[1]):
    while positionX < (test_array.shape[1]-data.shape[0]):
        test_array[positionY:positionY+data.shape[0], 
                    positionX:positionX+data.shape[1]] += data
        positionX+=offset
    positionX = initial_position[1]
    positionY+=offset
# do the distorted peaks                
initial_position = initial_position + offset/2
positionX = initial_position[1]
positionY = initial_position[0]
data = gaussian(191, (frame_size/2), (frame_size/2), (peak_size/4)+1, 
        (peak_size/4)+1)(xg, yg)

xOffset=0
yOffset=0

while positionY < (test_array.shape[0]-data.shape[0]):
    # tweak data depending on position in image
    if positionY < test_array.shape[0]/4:
        # vary peak heights
        data = gaussian(positionY/float(test_array.shape[0]/4)*255, (frame_size/2), 
                        (frame_size/2), (peak_size/4)+1, 
                        (peak_size/4)+1)(xg, yg)
        print "cycle 1: height = %.1f"%(positionY/(float(test_array.shape[0]/4))*255)
    elif positionY < test_array.shape[0]/2:
        # skew the image more or less (eccentricity)
        data = gaussian(191, (frame_size/2), (frame_size/2), (peak_size/4)+1, 
                (peak_size/4)+(peak_size/4*(positionY-test_array.shape[0]/2)/(test_array.shape[0]/4))+1)(xg, yg)
        print "cycle 2: skewed dimension width = %.1f"%((peak_size/4)+(peak_size/4*(positionY-test_array.shape[0]/2)/float(test_array.shape[0]/4))+1)
    elif positionY < test_array.shape[0]:
        # test rotation of skewed peak
        data = gaussian(191, (frame_size/2)+1, (frame_size/2)+1, (peak_size/8)+1, 
                (peak_size/4)+1)(xg, yg)
        rotation = (positionY-test_array.shape[0]/2)/float(test_array.shape[0]/2)*180
        # apply affine rotation matrix - go from 0 to 90 degrees, depending on our Y position        
        data = rotate(data, rotation, reshape=False)
        #plt.imshow(data)
        print "cycle 3: data rotation angle = %.1f"%(rotation)
    else:
        data = gaussian(191, (frame_size/2), (frame_size/2), (peak_size/4)+1, 
                (peak_size/4)+1)(xg, yg)        
    while positionX < (test_array.shape[1]-data.shape[1]):
        test_array[positionY:positionY+data.shape[0]+yOffset, 
                    positionX:positionX+data.shape[1]+xOffset] += data
        positionX+=offset
    positionX = initial_position[1]
    xOffset=0
    yOffset=0
    positionY+=offset
    
plt.imshow(test_array)
