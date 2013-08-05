Working with analyzarr's GUI
=============================

File I/O
*********************

Starting a new chest
-----------------------------

From the "File" menu, select "New Chest..."  This will close any currently open chests 
and create a blank, new chest.  You should proceed now to importing data.

Importing data to a chest 
--------------------------- 

Once you have a chest
open, the menu option for importing files will be enabled. You can now import
image files into your chest. You can add data at any later time//date. The
ability to remove data is under development.

Supported file formats
++++++++++++++++++++++++++++++

 * common image file formats (tif, jpg, bmp, etc.)
 * Gatan DM3 files. 

Bit depths up to 64 bits/8 bytes are supported.  Complex images are not supported.


Loading an existing chest
---------------------------------

From the "File" menu, select "Open Chest..."  This will close any currently open chests 
and load the data from the existing chest. You can add more files to any open
chest at any time.

Test pattern generation
-------------------------

For you to verify that analyzarr is working, there is a test pattern
generator. From the file menu, select "Test Data." You'll get a simple
structure that includes changes in peak heights, positions, orientations and
eccentricity.

Plotting output
--------------------

The upper-left menu has four buttons: Images, Cells, Factors, and Scores.
Each of these toggles the viewing pane for that particular plot. The borders
between these plots can be dragged to resize the view of any plot.

Interacting with plots
************************

Zooming is done with the mouse wheel. You can also press the Z key and select
a rectangle to zoom in on. To get back to the original zoom level, push your
keyboard\'s escape key.

Panning is done by clicking with the left mouse button and dragging.

Every plot pane has a save button. This will open a dialog allowing you to
specify a plot title, plot resolution (dpi), and plot size. As a general rule
of thumb, 300 dpi is good for printing figures. The physical size of your
image on paper is your plot size divided by your dpi.

Each plot has plot-specific buttons that allow you to add additional
information to the plot. These specific options are detailed below.

Parent image plots (peak mapping)
------------------------------------

Parent image plots serve as your reference for interpreting the peak data
that analyzarr provides. To overlay this data, you\'ll use Peak ID, Color
Map, and Vector Map panels.

Peak ID
++++++++

This is either \'all\' or an integer index. For the value \'all\', the map
shows data for the selected color map trait and vector map trait for all
peaks. For an integer index, the map shows only the corresponding labeled
peak from the Cell view pane.

.. note:: 

    You can\'t select an integer index until you have cropped cells and
    identified the peaks on your cells.

.. note:: 

    The \'expression\' color map type shows its data at the peak location
    corresponding to the index that you select. You should select this
    carefully. For expression maps, the data best fits on a cell, so try to
    choose a central peak for the location.

Color Map
++++++++++++

Color maps allow you to choose a characteristic to map.  The characteristics you have to choose from are:

 * peak height (h)
 * peak orientation (o)
 * peak eccentricity (e)
 * expression
 
The location of the mapped data corresponds to the location of the peak (the
colored spots should sit on top of the peaks that they are representing.)

The expression characteristic is an arbitrary characteristic that you define.
You need to specify peaks using a simple syntax::

    (characteristic_type)(peak_id)
    For example, eccentricity from peak 1: e1
    
There is currently one helpful shorthand for euclidean distance expressions::

    dist( peak_id_1, peak_id_2)
    
You can combine any number of expressions together::

    h0 / o3 + dist(2,4)

Vector Map
+++++++++++++

This shows a two-component map as a vector field. It is used to show either
shifts of peaks relative to the average position for that peak, or skew,
which is a description of how far the peak leans to one direction.

.. note:: 

    There is a bug in Analyzarr's plotting library that does not update the
    vector lengths when zooming.

Cell image plots (peak identification)
---------------------------------------

Once you have cropped cells, this plot view shows you all of your cells from
all of your parent images. When you crop cells, an average image is
automatically calculated, and an attempt to identify peaks is made on that
average. The **show** checkbox shows or hides the labels of the peak IDs. The
labels can be moved around by left-click-dragging them.

Factor image plots (TODO)
----------------------------

Score image plots (TODO)
---------------------------