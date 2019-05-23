#!/usr/bin/env python

import sys, getopt
import datetime, os, subprocess
import GMesh
import imp
import netCDF4
import numpy as np

def write_topog(h,hstd,hmin,hmax,fnam=None,format='NETCDF3_CLASSIC',description=None,history=None,source=None,no_changing_meta=None):
    import netCDF4 as nc

    if fnam is None:
      fnam='topog.nc'
    fout=nc.Dataset(fnam,'w',format=format)

    ny=h.shape[0]; nx=h.shape[1]
    print ('Writing netcdf file with ny,nx= ',ny,nx)

    ny=fout.createDimension('ny',ny)
    nx=fout.createDimension('nx',nx)
    ntiles=fout.createDimension('ntiles',1)
    depth=fout.createVariable('depth','f8',('ny','nx'))
    depth.units='meters'
    depth[:]=-h
    height=fout.createVariable('height','f8',('ny','nx'))
    height.units='meters'
    height[:]=h
    h_std=fout.createVariable('std','f8',('ny','nx'))
    h_std.units='meters'
    h_std[:]=hstd
    h_min=fout.createVariable('h_min','f8',('ny','nx'))
    h_min.units='meters'
    h_min[:]=hmin
    h_max=fout.createVariable('h_max','f8',('ny','nx'))
    h_max.units='meters'
    h_max[:]=hmax
#    string=fout.createDimension('string',255)    
#    tile=fout.createVariable('tile','S1',('string'))
#    tile[0]='t'
#    tile[1]='i'
#    tile[2]='l'
#    tile[3]='e'
#    tile[4]='1'
    
    #global attributes
    if(not no_changing_meta):
    	fout.history = history
    	fout.description = description
    	fout.source =  source

    fout.sync()
    fout.close()

def plot():
    pl.clf()
    display.clear_output(wait=True)
    plt.figure(figsize=(10,10))
    lonc = (lon[0,0]+lon[0,-1])/2
    latc = 90
    ax = plt.subplot(111, projection=cartopy.crs.NearsidePerspective(central_longitude=lonc, central_latitude=latc))
    ax.set_global()
    ax.stock_img()
    ax.coastlines()
    ax.gridlines()
    target_mesh.plot(ax,subsample=100, transform=cartopy.crs.Geodetic())
    plt.show(block=False)
    plt.pause(1)
    display.display(pl.gcf())


def usage(scriptbasename):
    print(scriptbasename + ' --hgridfilename <input_hgrid_filepath> --outputfilename <output_topog_filepath>  [--plot --no_changing_meta]')


def main(argv):
    import socket
    host = str(socket.gethostname())
    scriptpath = sys.argv[0]
    scriptbasename = subprocess.check_output("basename "+ scriptpath,shell=True).decode('ascii').rstrip("\n")
    scriptdirname = subprocess.check_output("dirname "+ scriptpath,shell=True).decode('ascii').rstrip("\n")

    plotem = False
    no_changing_meta = False
    try:
        opts, args = getopt.getopt(sys.argv[1:],"h",["tilefiles=","outputfilename=","plot","no_changing_meta"])
    except getopt.GetoptError as err:
        print(err)
        usage(scriptbasename)
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("--tilefiles"):
            tilefiles = arg
        elif opt in ("--outputfilename"):
            outputfilename= arg
        elif opt in ("--plot"):
            plotem = True
        elif opt in ("--no_changing_meta"):
            no_changing_meta = True
        else:
            assert False, "unhandled option"


    #Information to write in file as metadata
    scriptgithash = subprocess.check_output("cd "+scriptdirname +";git rev-parse HEAD; exit 0",stderr=subprocess.STDOUT,shell=True).decode('ascii').rstrip("\n")
    scriptgitMod  = subprocess.check_output("cd "+scriptdirname +";git status --porcelain "+scriptbasename+" | awk '{print $1}' ; exit 0",stderr=subprocess.STDOUT,shell=True).decode('ascii').rstrip("\n")
    if("M" in str(scriptgitMod)):
        scriptgitMod = " , But was localy Modified!"

    hist = "This file was generated via command " + ' '.join(sys.argv)
    if(not no_changing_meta):
        hist = hist + " on "+ str(datetime.date.today()) + " on platform "+ host

    desc = "This is a model topography file generated by the refine-sampling method from source topography. "
    
    source =""
    if(not no_changing_meta):
        source =  source + scriptpath + " had git hash " + scriptgithash + scriptgitMod 
        source =  source + ". To obtain the grid generating code do: git clone  https://github.com/nikizadehgfdl/thin-wall-topography.git ; cd thin-wall-topography;  git checkout "+scriptgithash

    tiles = tilefiles.split(',')
    heights = []
    h_stds = []
    h_mins = []
    h_maxs = []
    for tilefile in tiles:
        print(" Reading ", tilefile)
        tiledata = netCDF4.Dataset(tilefile)
        heights.append(np.array(tiledata.variables['height'][:]))
        h_stds.append(np.array(tiledata.variables['h_std'][:]))
        h_mins.append(np.array(tiledata.variables['h_min'][:]))
        h_maxs.append(np.array(tiledata.variables['h_max'][:]))

    height=heights[0]
    cats = 0 #count number of joins
    print(" h.shape=",height.shape,"  h.first=",height[0,0]," h.last=",height[-1,0])
    for h in heights[1:] :
        print(" h.shape=",h.shape," h.first=",h[0,0]," h.last=",h[-1,0])
        height = np.concatenate((height[:-1,:],h),axis=0) 
        cats = cats + 1

    h_min=h_mins[0]
    for h in h_mins[1:] :
        h_min = np.concatenate((h_min[:-1,:],h),axis=0)    

    h_max=h_maxs[0]
    for h in h_maxs[1:] :
        h_max = np.concatenate((h_max[:-1,:],h),axis=0)    

    h_std=h_stds[0]
    for h in h_stds[1:] :
        h_std = np.concatenate((h_std[:-1,:],h),axis=0)    

    #This is on supergrid. Topography is needed on tracer cells. 
    #Sample every other point to get it. 
    #Drop the last x (corresponds to x0+360)  and y (why?)
    #Niki: Is this correct?
    height= height[:-1:2,:-1:2]
    h_std =  h_std[:-1:2,:-1:2]
    h_max =  h_max[:-1:2,:-1:2]
    h_min =  h_min[:-1:2,:-1:2]
    

    write_topog(height,h_std,h_min,h_max,fnam=outputfilename,description=desc,history=hist,source=source,no_changing_meta=no_changing_meta)


if __name__ == "__main__":
    main(sys.argv[1:])

