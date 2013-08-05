Setting up Analyzarr 
======================================

..
    Installation from binaries:
    ***************

.. 
    For Windows Vista, 7 or 8, x64, there is a pre-built self-contained Python 
    installation, thanks to the WinPython project.  You can download it here:

.. http://analyzarr.org/static/WinPython-64bit-2.7.3.3.7z

.. 
    This is the base WinPython distribution with some additional libraries that 
    Analyzarr requires.  It does not have an up-to-date installation of analyzarr!  

..  
    To install the latest version, download the following file:
    http://t3hmikez0r.com/static/analyzarr-0.1.win-amd64-py2.7.exe
..
    1. Open the WinPython control panel
    2. Uninstall the old analyzarr package from the "uninstall packages" tab
    3. Drag and drop the new one into the control panel's "install/upgrade" tab

..
    Note that this is probably also somewhat out of date! The best way to install
    things is from source.

Installing from source
***********************
Grab the source code from Github: https://github.com/msarahan/analyzarr

Clone or download a copy of the repository, then navigate to the folder where
you have the source code. These instructions assume that you have pip. If you
don't, run ``easy_install pip`` to get it. Run either:

For a real installation where files are copied into your python
site_packages folder::

    pip install .

or for development installation, where it will be easier to keep
current, simply by pulling from Git::

    pip install -e ./

Starting up Analyzarr
***********************
You want to run the **analyzarr_gui.py** file that lives int the
analyzarr/analyzarr folder. 

..
    For the pre-built Windows installation, there is
    a shortcut (analyzarr.bat) for this that lives in the **scripts** folder of the root of the
    extracted installation.

On the first startup, it takes quite a long time (maybe 2-3 minutes.) A
progress bar will be implemented soon. Subsequent runs are much faster (10-20
seconds.)

For Linux, the installation copies a script, analyzarr, to the bin folder of
your python installation. Since this folder is probably already on your PATH,
you just have to type **analyzarr** at the command line, and you will be
cooking with gas.


