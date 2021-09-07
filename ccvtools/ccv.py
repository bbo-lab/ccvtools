# (c) 2021 Kay-Michael Voit <kay@voits.net>

import os,sys
import numpy as np
import imageio
from ccvtools import rawio
import random
import string
import mutagen
import json

def fill(full_times_file,ccv_file,ccv_times_file):
    ccv_out_file = ccv_file[0:-4]+'_filled'+ccv_file[-4:]

    ccv_times = np.loadtxt(ccv_times_file)
    full_times = np.loadtxt(full_times_file)

    assert ccv_times[0] > full_times[0] - 0.001
    doesnotexist = np.zeros(full_times.size,dtype=np.bool)
    ccv_times_idx = 0
    for i,t in enumerate(full_times):
        if len(ccv_times) <= ccv_times_idx:
            doesnotexist[i:] = True
            break
        if not np.abs(ccv_times[ccv_times_idx]-t) < 0.001:
            doesnotexist[i] = True
        else:
            ccv_times_idx = ccv_times_idx+1

    reader = imageio.get_reader(ccv_file)

    camera_type_len = reader.header.camera_type.length+5
    image_type_len = reader.header.image_type.length+5
    frcount_offset = int((8*32 + 64 +8)/8 + camera_type_len + image_type_len)

    blackframe = np.zeros(reader.header.frame_bytes_on_disk,dtype=np.uint8)

    with open(ccv_file,'rb') as sourcefile:
        with open(ccv_out_file,'wb') as targetfile:
            targetfile.write(sourcefile.read(frcount_offset))
            targetfile.write(np.uint32(len(full_times)))
            sourcefile.seek(frcount_offset+4,os.SEEK_SET)
            targetfile.write(sourcefile.read(reader.header.header_size - 4 - frcount_offset))
            
            for writeblack in tqdm(doesnotexist):
                if writeblack:
                    targetfile.write(blackframe)
                else:
                    targetfile.write(sourcefile.read(reader.header.frame_bytes_on_disk))


def truncate(ccv_file,idx_range,ccv_out_file=None):
    reader = imageio.get_reader(ccv_file)
    camera_type_len = reader.header.camera_type.length+5
    image_type_len = reader.header.image_type.length+5
    frcount_offset = int((8*32 + 64 +8)/8 + camera_type_len + image_type_len)

    if ccv_out_file is None:
        ccv_tmp_file = f'.{ccv_file[0:-4]}_{"".join(random.choices(string.ascii_uppercase + string.digits, k=5))}_truncate.tmp'
    else:
        ccv_tmp_file = f'.{ccv_out_file[0:-4]}_{"".join(random.choices(string.ascii_uppercase + string.digits, k=5))}_truncate.tmp'
        
    with open(ccv_file,'rb') as sourcefile:
        with open(ccv_tmp_file,'wb') as targetfile:
            # Copy header
            targetfile.write(sourcefile.read(reader.header.header_size))
            
            # Write frame number to header
            targetfile.seek(frcount_offset,os.SEEK_SET)
            targetfile.write(np.uint32(len(idx_range)))
            targetfile.seek(reader.header.header_size,os.SEEK_SET)
            
            # Copy desired frames
            prev_fr_idx = None
            for (i,fr_idx) in enumerate(idx_range):
                # Save first frame from iterator
                if i==0:
                    start_frame = fr_idx
                
                # Set point in case iterator is not consecutive
                if prev_fr_idx is None or not fr_idx-prev_fr_idx==1:
                    sourcefile.seek(reader.header.header_size+reader.header.frame_bytes_on_disk*fr_idx,os.SEEK_SET) 
                    
                targetfile.write(sourcefile.read(reader.header.frame_bytes_on_disk))
                prev_fr_idx = fr_idx
            
            # Save last frame from iterator
            end_frame = fr_idx
            
    # Rename tmp file to final file name
    if ccv_out_file is None:
        ccv_out_file = "{ccv_file[0:-4]}_truncated_{start_frame}-{end_frame}.ccv".format(ccv_file=ccv_file,start_frame=start_frame,end_frame=end_frame)
    os.rename(ccv_tmp_file,ccv_out_file)

    
def convert(ccv_file,video_file,idx_range,fps=25,codec="libx264",quality=10,min_contrast=0,max_contrast=None,out_type=np.uint8):
    reader = imageio.get_reader(ccv_file)
    writer = imageio.get_writer(video_file, fps=fps, codec=codec, quality=quality)

    prev_fr_idx=None
    indices = np.zeros(shape=len(idx_range),dtype=int)
    timestamps = np.zeros(shape=len(idx_range),dtype=np.float)
    for (i,fr_idx) in enumerate(idx_range):
        # Set point in case iterator is not consecutive
        if prev_fr_idx is None or not fr_idx-prev_fr_idx==1:
            im = reader.get_data(fr_idx)
        else:
            im = reader.get_next_data()
        
        meta = reader.get_meta_data(fr_idx);
        indices[i] = meta["index"];
        timestamps[i] = meta["timestamp"];
        
        # Get max value of movie if not specified
        if i==0 and max_contrast is None:
            max_contrast = np.iinfo(np.asarray(im).dtype).max
                
        # Adjust contrast / Reduce to 8 bit
        im = np.uint64(im)
        im = (im-min_contrast)*np.iinfo(out_type).max/(max_contrast-min_contrast)
        im[im<0] = 0
        im[im>max_contrast] = np.iinfo(out_type).max
        writer.append_data(out_type(im))
        prev_fr_idx = fr_idx

    writer.close()

    headerdict = dict(reader.header)
    del headerdict['_io']
    headerdict['camera_type'] = headerdict['camera_type'].data.decode("ascii")
    headerdict['image_type'] = headerdict['image_type'].data.decode("ascii")
    headerdict['sensor'] = {'offset': list(headerdict['sensor'].offset),
                            'size': list(headerdict['sensor'].size),
                            'clock': headerdict['sensor'].clock,
                            'exposure': headerdict['sensor'].exposure,
                            'gain': headerdict['sensor'].gain
                           }
    headerdict['indices'] = [int(val) for val in indices]
    print(timestamps)
    headerdict['timestamps'] = [float(val) for val in timestamps]
    print(headerdict['timestamps'])
    
    if len(headerdict['sensor']['offset'])==1: headerdict['sensor']['offset'].append(headerdict['sensor']['offset'][0])
    if len(headerdict['sensor']['size'])==1: headerdict['sensor']['size'].append(headerdict['sensor']['size'][0])
    
    with open(video_file, 'r+b') as file:
        media_file = mutagen.File(file, easy=True)
        media_file['description'] = json.dumps(headerdict)
        media_file.save(file)
