import time, tempfile, os, subprocess
from pathlib import Path
from typing import List, Tuple
from moviepy import VideoFileClip, CompositeVideoClip

FFPROBE_BINARY = os.environ.get("FFPROBE_BINARY")
FFMPEG_BINARY = os.environ.get("FFMPEG_BINARY")
FFPLAY_BINARY = os.environ.get("FFPLAY_BINARY")

TEMP_DIR = ".."
INPUT_VIDEO = "../input/video_output.mp4"
OUTPUT_FOLDER = "../output"

class Moviepy():

    def cut_out_video(self, input_path: Path, subclip_times :  List[Tuple[(float,float)]], output : Path) -> float:
        chrono_start = time.time()
        clip = VideoFileClip(input_path)
        subclips = [clip.subclipped(*cpl) for cpl in subclip_times]
        for i in range(1,len(subclips)):
            subclips[i] = subclips[i].with_start(subclips[i-1].end)
        final_clip = CompositeVideoClip(subclips)
        final_clip.write_videofile(output, codec = "libx264", audio_codec= "libmp3lame", audio_bitrate="127k", audio_fps=44100, preset="medium")
        clip.close()
        chrono_count = time.time() - chrono_start
        return chrono_count

class FFMPEG():

    def cut_out_video(self, input_path: Path, subclip_times : List[Tuple[(float,float)]], output : Path) -> float:
        chrono_start = time.time()
        filter_chain = "[0:v]trim=start={0}:end={1},setpts=PTS-STARTPTS[v{2}]; [0:a]atrim=start={0}:end={1},asetpts=PTS-STARTPTS[a{2}];"
        filter_graph = "\n".join([filter_chain.format(cpl[0],cpl[1],i+1) for i,cpl in enumerate(subclip_times)])
        filter_graph +=  "\n" + "".join([f"[v{i+1}][a{i+1}]" for i in range(len(subclip_times))])
        filter_graph += f"concat=n={len(subclip_times)}:v=1:a=1[outv][outa]"
        cmd = [FFMPEG_BINARY,'-i', f'{input_path}', '-filter_complex', filter_graph, 
               "-map", "[outv]","-map","[outa]", 
               "-c:v", "libx264", 
               "-c:a","libmp3lame", "-b:a", "127k", "-ar", "44100","-preset", "medium", # To respect the same encoding than moviepy
               output, '-y']
        subprocess.run(cmd, stdout=subprocess.DEVNULL)
        chrono_count = time.time() - chrono_start
        return chrono_count
    
    def cut_out_video_without_transcoding_using_copy_paramter(self, input_path: Path, subclip_times : List[Tuple[(float,float)]], output : Path, tmpdir) -> float:
        chrono_start = time.time()
        list_of_files = []
        # Create subclips and write them in separate files
        for i,cpl in enumerate(subclip_times):
            file_name = str(os.path.join(tmpdir,"output"+"_"+str(i)+".mp4"))
            list_of_files.append(file_name)
            cmd = [FFMPEG_BINARY,'-ss', str(cpl[0]),'-to', str(cpl[1]),'-i', f'{input_path}', '-c','copy', file_name, '-y']
            subprocess.run(cmd, stdout=subprocess.DEVNULL)
        # Write all the sublcips' filepath in a file 'liste.txt'
        with open(os.path.join(tmpdir,"liste.txt"), "w") as f:
            for file_name in list_of_files:
                f.write("file '" + file_name + "'\n")
        # Concate all the subclips in one output
        subprocess.run([FFMPEG_BINARY, '-f', 'concat', '-safe', "0", '-i', str(os.path.join(tmpdir,"liste.txt")), "-c", "copy", output ,"-y"], stdout=subprocess.DEVNULL)
        chrono_count = time.time() - chrono_start
        return chrono_count

if __name__ == "__main__":
    ffmpeg = FFMPEG()
    mvpy = Moviepy()
    test_sets = [ 
        [(1,11), (16,20), (37,55), (214.75, 236), (281.5, 284.7)],
         [(0, 10), (12, 25), (30, 45), (50, 60), (75, 90), (120, 150), (180, 200), (210, 215), (220, 230)],
          [(0, 5), (10, 15), (20, 25), (30, 35), (40, 45), (50, 55), (60, 65), (70, 75),
            (80, 85), (90, 95), (100, 105), (110, 115), (120, 125), (130, 135), (140, 145),
            (150, 155), (160, 165), (170, 175), (180, 185), (190, 195), (200, 205), (210, 215),
            (220, 225), (230, 235), (240, 245), (250, 255), (260, 265), (270, 275), (280, 285),
            (290, 295), (300, 305), (310, 315), (320, 325), (330, 335), (340, 345), (350, 355),
            (360, 365), (370, 375), (380, 385), (390, 395), (400, 405), (410, 415), (420, 425),
            (430, 435), (440, 445), (450, 455), (460, 465), (470, 475), (480, 485), (490, 495)]
 ]

    times = []
    for subclip_times in test_sets:
        subtimes =  []

        with tempfile.TemporaryDirectory(dir=TEMP_DIR) as tmpdirname:
            subtimes.append(mvpy.cut_out_video(INPUT_VIDEO, subclip_times, os.path.join(OUTPUT_FOLDER, "output_moviepy.mp4")))
            subtimes.append(ffmpeg.cut_out_video(INPUT_VIDEO, subclip_times, os.path.join(OUTPUT_FOLDER, "output_ffmpeg.mp4")))
            subtimes.append(ffmpeg.cut_out_video_without_transcoding_using_copy_paramter(INPUT_VIDEO, subclip_times, os.path.join(OUTPUT_FOLDER, "output_ffmpeg_without_transcoding.mp4"), tmpdir = tmpdirname))
        
        times.append([round(value, 3) for value in subtimes])


    for i in range(len(test_sets)):
        print("Subclip de longueur :", len(test_sets[i]))
        print("Times : ", times[i])

    # Output ( Time for : Moviepy, FFmpeg with re-encoding, and FFmpeg uing -c copy):
    # Subclip de longueur : 5
    # Times :  [7.18, 2.365, 0.443]
    # Subclip de longueur : 9
    # Times :  [16.42, 3.632, 0.797]
    # Subclip de longueur : 50
    # Times :  [37.245, 16.605, 3.757]