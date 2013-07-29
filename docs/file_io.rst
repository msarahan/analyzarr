File import and internal data handling
======================================

Your data in analyzarr is stored in "chests."  These are HDF5 files with a 
particular folder and descriptor structure.  Think of chests more like a project
than as a single file.  They contain all of the tabulated information regarding
peak locations and characteristics, as well as the log of all the actions you've
taken, so you can go back and repeat your experiments if need be.

For manually viewing the contents of chest files, you can use any HDF5-capable 
program.  Internally, analyzarr uses PyTables.  In analyzarr's development,
HDFView was useful to make sure that the chests contained the correct data.  Note
that you will have to manually tell HDFview's file filter to "All files" so that
files with the .chest extension will show up.

You can also use any HDF5-capable tool to extract data from analyzarr into your 
own preferred tool (Matlab?).  But really, with analyzarr being as much fun as 
it is, why would you want to do that?  If you find yourself pulling data out of 
analyzarr often, consider making a feature request to improve analyzarr for 
everyone.

File Structure
*******************
From the root of the file, there are 3 groups and 5 datasets (HDF5 terminology.) 
Groups can contain multiple datasets.

* rawdata (group): The group that holds your imported data.  Your original 
  data type (float, integer, depth, etc.) is maintained at this point.
 
* image_description (dataset): a table for tracking the data imported into the
  chest.  This is currently nothing more than an index and a filename.
 
* cells (group): The group that holds cropped cell images.  There is one 3D dataset
  for each parent image from which cells are cropped.  There are two additional 
  datasets: the template used in cropping cells, and the average of all cropped cells.
 
* cell_description (dataset): a table for tracking the cell metadata.  Namely,
  the image from which the cell was cropped and the location on that image.  
  The file_idx column is a local file index.  Each cell has a global, unique index 
  and this local index.  The "omit" column is an omission flag that suppresses individual
  cells from being plotted or included in MDA processing.
 
* cell_peaks (dataset): a table containing the results of characterizing peaks.
  Presently, these are derived from individual cells, and this table reflects
  that layout.  Each row represents one cell.  There are 3 static columns for the
  filename, local file index, and omission flag.  The other fields are dynamically
  generated when analysis is performed.  There are 7 additional columns for each peak:
 
  * x0 and y0 represent the cell-local coordinates of the first peak in the cell.  
  
  * dx0 and dy0 are the relative difference between this peak's coordinates on 
    this cell and the coordinates of the same peak on the average cell.
	
  * h0 is the peak height
  
  * o0 is the peak orientation in degrees.  It will be between 0 and 360.
  
  * e0 is a measure of eccentricity - how far from round a peak is.
  
  * sx0 and sy0 are skew - how much the peak "leans" to one side more than the other.
  
* mda_results (group): the factors and scores from MDA analysis.  These can 
  take different forms depending on whether the MDA is done on peaks, or on
  raw image data.  In either case, there will be a group for each parent image
  from which cells were cropped, and each group will contain separate datasets
  for factors and scores.  Any analysis-specific datasets will also be saved in
  this subgroup.  For example, PCA will have an additional dataset for the 
  derived eigenvalues.
 
* mda_description (dataset): a table tracking the types, dates, data included, 
  and parameters used for all of your MDA runs.
 
* log (dataset): A log of all of the commands issued to analyzarr.  The action
  is a plain text description of the function that was used.  The parameters
  column is parseable as a Python dictionary, and can be passed directly to the
  appropriate function to replicate the behavior.  The version column allows
  specification of the version of analyzarr used for that step, in case any 
  functionality changes over time (e.g. bugs fixed...)

