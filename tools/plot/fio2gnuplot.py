#!/usr/bin/python
#
#  Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#  Author: Erwan Velu  <erwan@enovance.com>
#
#  The license below covers all files distributed with fio unless otherwise
#  noted in the file itself.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 2 as
#  published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os
import fnmatch
import sys
import getopt
import re
import math

def find_file(path, pattern):
	fio_data_file=[]
	# For all the local files
	for file in os.listdir(path):
	    # If the file math the regexp
	    if fnmatch.fnmatch(file, pattern):
		# Let's consider this file
		fio_data_file.append(file)

	return fio_data_file

def generate_gnuplot_script(fio_data_file,title,gnuplot_output_filename,mode,disk_perf):
	f=open("mygraph",'w')
	if len(fio_data_file) > 1:
        	f.write("call \'graph3D.gpm\' \'%s' \'%s\' \'\' \'%s\' \'%s\'\n" % (title,gnuplot_output_filename,gnuplot_output_filename,mode))

        pos=0
        # Let's create a temporary file for each selected fio file
        for file in fio_data_file:
                tmp_filename = "gnuplot_temp_file.%d" % pos
                png_file=file.replace('.log','')
                raw_filename = "%s-2Draw" % (png_file)
                smooth_filename = "%s-2Dsmooth" % (png_file)
                trend_filename = "%s-2Dtrend" % (png_file)
                avg  = average(disk_perf[pos])
                f.write("call \'graph2D.gpm\' \'%s' \'%s\' \'\' \'%s\' \'%s\' \'%s\' \'%s\' \'%f\'\n" % (title,tmp_filename,raw_filename,mode,smooth_filename,trend_filename,avg))
                pos = pos +1

	f.close()

def generate_gnuplot_math_script(title,gnuplot_output_filename,mode,average):
	f=open("mymath",'a')
        f.write("call \'math.gpm\' \'%s' \'%s\' \'\' \'%s\' \'%s\' %s\n" % (title,gnuplot_output_filename,gnuplot_output_filename,mode,average))
	f.close()

def compute_aggregated_file(fio_data_file, gnuplot_output_filename):
	temp_files=[]
	pos=0
	# Let's create a temporary file for each selected fio file
	for file in fio_data_file:
		tmp_filename = "gnuplot_temp_file.%d" % pos
		temp_files.append(open(tmp_filename,'r'))
		pos = pos +1

	f = open(gnuplot_output_filename, "w")
	index=0
	# Let's add some information
	for tempfile in temp_files:
		    f.write("# Disk%d was coming from %s\n" % (index,fio_data_file[index]))
		    f.write(tempfile.read())
		    f.write("\n")
		    tempfile.close()
		    index = index + 1
	f.close()

def average(s): return sum(s) * 1.0 / len(s)

def compute_temp_file(fio_data_file,disk_perf):
	files=[]
	temp_outfile=[]
	blk_size=0
	for file in fio_data_file:
		files.append(open(file))
		pos = len(files) - 1
		tmp_filename = "gnuplot_temp_file.%d" % pos
		gnuplot_file=open(tmp_filename,'w')
		temp_outfile.append(gnuplot_file)
		gnuplot_file.write("#Temporary file based on file %s\n" % file)
		disk_perf.append([])

	shall_break = False
	while True:
		current_line=[]
		nb_empty_files=0
		nb_files=len(files)
		for file in files:
			s=file.readline().replace(',',' ').split()
			if not s:
				nb_empty_files+=1
				s="-1, 0, 0, 0'".replace(',',' ').split()

			if (nb_empty_files == nb_files):
				shall_break=True
				break;

			current_line.append(s);

		if shall_break == True:
			break

		last_time = -1
		index=0
		perfs=[]
		for line in current_line:
			time, perf, x, block_size = line
			if (blk_size == 0):
				blk_size=int(block_size)

			# We ignore the first 500msec as it doesn't seems to be part of the real benchmark
			# Time < 500 usually reports BW=0 breaking the min computing
			if (((int(time)) > 500) or (int(time)==-1)):
				disk_perf[index].append(int(perf))
				perfs.append("%s %s"% (time, perf))
				index = index + 1

		# If we reach this point, it means that all the traces are coherent
		for p in enumerate(perfs):
			perf_time,perf = p[1].split()
			if (perf_time != "-1"):
				temp_outfile[p[0]].write("%s %.2f %s\n" % (p[0], float(float(perf_time)/1000), perf))


	for file in files:
		file.close()
	for file in temp_outfile:
                file.close()
	return blk_size

def compute_math(fio_data_file, title,gnuplot_output_filename,mode,disk_perf):
	global_min=[]
	global_max=[]
	average_file=open(gnuplot_output_filename+'.average', 'w')
	min_file=open(gnuplot_output_filename+'.min', 'w')
	max_file=open(gnuplot_output_filename+'.max', 'w')
	stddev_file=open(gnuplot_output_filename+'.stddev', 'w')
	global_file=open(gnuplot_output_filename+'.global','w')

	min_file.write('DiskName %s\n' % mode)
	max_file.write('DiskName %s\n'% mode)
	average_file.write('DiskName %s\n'% mode)
	stddev_file.write('DiskName %s\n'% mode )
	for disk in xrange(len(fio_data_file)):
#		print disk_perf[disk]
	    	min_file.write("# Disk%d was coming from %s\n" % (disk,fio_data_file[disk]))
	    	max_file.write("# Disk%d was coming from %s\n" % (disk,fio_data_file[disk]))
	    	average_file.write("# Disk%d was coming from %s\n" % (disk,fio_data_file[disk]))
	    	stddev_file.write("# Disk%d was coming from %s\n" % (disk,fio_data_file[disk]))
		avg  = average(disk_perf[disk])
		variance = map(lambda x: (x - avg)**2, disk_perf[disk])
		standard_deviation = math.sqrt(average(variance))
#		print "Disk%d [ min=%.2f max=%.2f avg=%.2f stddev=%.2f \n" % (disk,min(disk_perf[disk]),max(disk_perf[disk]),avg, standard_deviation)
		average_file.write('%d %d\n' % (disk, avg))
		stddev_file.write('%d %d\n' % (disk, standard_deviation))
		local_min=min(disk_perf[disk])
		local_max=max(disk_perf[disk])
		min_file.write('%d %d\n' % (disk, local_min))
		max_file.write('%d %d\n' % (disk, local_max))
		global_min.append(int(local_min))
		global_max.append(int(local_max))

	global_disk_perf = sum(disk_perf, [])
	avg  = average(global_disk_perf)
	variance = map(lambda x: (x - avg)**2, global_disk_perf)
	standard_deviation = math.sqrt(average(variance))

	global_file.write('min=%.2f\n' % min(global_disk_perf))
	global_file.write('max=%.2f\n' % max(global_disk_perf))
	global_file.write('avg=%.2f\n' % avg)
	global_file.write('stddev=%.2f\n' % standard_deviation)
	global_file.write('values_count=%d\n' % len(global_disk_perf))
	global_file.write('disks_count=%d\n' % len(fio_data_file))
	#print "Global [ min=%.2f max=%.2f avg=%.2f stddev=%.2f \n" % (min(global_disk_perf),max(global_disk_perf),avg, standard_deviation)

	average_file.close()
	min_file.close()
	max_file.close()
	stddev_file.close()
	global_file.close()
	try:
		os.remove('mymath')
	except:
		True

	generate_gnuplot_math_script("Average values of "+title,gnuplot_output_filename+'.average',mode,int(avg))
	generate_gnuplot_math_script("Min values of "+title,gnuplot_output_filename+'.min',mode,average(global_min))
	generate_gnuplot_math_script("Max values of "+title,gnuplot_output_filename+'.max',mode,average(global_max))
	generate_gnuplot_math_script("Standard Deviation of "+title,gnuplot_output_filename+'.stddev',mode,int(standard_deviation))

def parse_global_files(fio_data_file, global_search):
	max_result=0
	max_file=''
	for file in fio_data_file:
		f=open(file)
		disk_count=0
		search_value=-1

		# Let's read the complete file
		while True:
			try:
				# We do split the name from the value
				name,value=f.readline().split("=")
			except:
				f.close()
				break
			# If we ended the file
			if not name:
				# Let's process what we have
				f.close()
				break
			else:
				# disks_count is not global_search item
				# As we need it for some computation, let's save it
				if name=="disks_count":
					disks_count=int(value)

				# Let's catch the searched item
				if global_search in name:
					search_value=float(value)

		# Let's process the avg value by estimated the global bandwidth per file
		# We keep the biggest in memory for reporting
		if global_search == "avg":
			if (disks_count > 0) and (search_value != -1):
				result=disks_count*search_value
				if (result > max_result):
					max_result=result
					max_file=file
	# Let's print the avg output
	if global_search == "avg":
		print "Biggest aggregated value of %s was %2.f in file %s\n" % (global_search, max_result, max_file)
	else:
		print "Global search %s is not yet implemented\n" % global_search

def render_gnuplot():
	print "Running gnuplot Rendering\n"
	try:
		os.system("gnuplot mymath")
		os.system("gnuplot mygraph")
	except:
		print "Could not run gnuplot on mymath or mygraph !\n"
		sys.exit(1);

def print_help():
    print 'fio2gnuplot.py -ghbio -t <title> -o <outputfile> -p <pattern>'
    print
    print '-h --help                           : Print this help'
    print '-p <pattern> or --pattern <pattern> : A pattern in regexp to select fio input files'
    print '-b           or --bandwidth         : A predefined pattern for selecting *_bw.log files'
    print '-i           or --iops              : A predefined pattern for selecting *_iops.log files'
    print '-g           or --gnuplot           : Render gnuplot traces before exiting'
    print '-o           or --outputfile <file> : The basename for gnuplot traces'
    print '                                       - Basename is set with the pattern if defined'
    print '-t           or --title <title>     : The title of the gnuplot traces'
    print '                                       - Title is set with the block size detected in fio traces'
    print '-G		or --Global <type>     : Search for <type> in .global files match by a pattern'
    print '                                       - Available types are : min, max, avg, stddev'
    print '                                       - The .global extension is added automatically to the pattern'

def main(argv):
    mode='unknown'
    pattern=''
    pattern_set_by_user=False
    title='No title'
    gnuplot_output_filename='result'
    disk_perf=[]
    run_gnuplot=False
    parse_global=False
    global_search=''

    try:
	    opts, args = getopt.getopt(argv[1:],"ghbio:t:p:G:")
    except getopt.GetoptError:
	 print_help()
         sys.exit(2)

    for opt, arg in opts:
      if opt in ("-b", "--bandwidth"):
         pattern='*_bw.log'
      elif opt in ("-i", "--iops"):
         pattern='*_iops.log'
      elif opt in ("-p", "--pattern"):
         pattern_set_by_user=True
	 pattern=arg
	 pattern=pattern.replace('\\','')
      elif opt in ("-o", "--outputfile"):
         gnuplot_output_filename=arg
      elif opt in ("-t", "--title"):
         title=arg
      elif opt in ("-g", "--gnuplot"):
	 run_gnuplot=True
      elif opt in ("-G", "--Global"):
	 parse_global=True
	 global_search=arg
      elif opt in ("-h", "--help"):
	  print_help()
	  sys.exit(1)

    # Adding .global extension to the file
    if parse_global==True:
	    if not gnuplot_output_filename.endswith('.global'):
	    	pattern = pattern+'.global'

    fio_data_file=find_file('.',pattern)
    if len(fio_data_file) == 0:
	    print "No log file found with pattern %s!" % pattern
	    sys.exit(1)

    fio_data_file=sorted(fio_data_file, key=str.lower)
    for file in fio_data_file:
	print 'Selected %s' % file
	if "_bw.log" in file :
		mode="Bandwidth (KB/sec)"
	if "_iops.log" in file :
		mode="IO per Seconds (IO/sec)"
    if (title == 'No title') and (mode != 'unknown'):
	    if "Bandwidth" in mode:
		    title='Bandwidth benchmark with %d fio results' % len(fio_data_file)
	    if "IO" in mode:
		    title='IO benchmark with %d fio results' % len(fio_data_file)

    #We need to adjust the output filename regarding the pattern required by the user
    if (pattern_set_by_user == True):
	    gnuplot_output_filename=pattern
	    # As we do have some regexp in the pattern, let's make this simpliest
	    # We do remove the simpliest parts of the expression to get a clear file name
	    gnuplot_output_filename=gnuplot_output_filename.replace('-*-','-')
	    gnuplot_output_filename=gnuplot_output_filename.replace('*','-')
	    gnuplot_output_filename=gnuplot_output_filename.replace('--','-')
	    gnuplot_output_filename=gnuplot_output_filename.replace('.log','')
	    # Insure that we don't have any starting or trailing dash to the filename
	    gnuplot_output_filename = gnuplot_output_filename[:-1] if gnuplot_output_filename.endswith('-') else gnuplot_output_filename
	    gnuplot_output_filename = gnuplot_output_filename[1:] if gnuplot_output_filename.startswith('-') else gnuplot_output_filename

    if parse_global==True:
	parse_global_files(fio_data_file, global_search)
    else:
    	blk_size=compute_temp_file(fio_data_file,disk_perf)
    	title="%s @ Blocksize = %dK" % (title,blk_size/1024)
    	compute_aggregated_file(fio_data_file, gnuplot_output_filename)
    	compute_math(fio_data_file,title,gnuplot_output_filename,mode,disk_perf)
    	generate_gnuplot_script(fio_data_file,title,gnuplot_output_filename,mode,disk_perf)

    	if (run_gnuplot==True):
    		render_gnuplot()

    # Cleaning temporary files
    try:
	os.remove('gnuplot_temp_file.*')
    except:
	True

#Main
if __name__ == "__main__":
    sys.exit(main(sys.argv))
