def replace_line_in_file(old_file,new_file, target_line, new_line):
    # Read all lines from the file
    with open(old_file, 'r') as file:
        lines = file.readlines()

    # Replace the target line with the new line
    with open(new_file, 'w') as file:
        for line in lines:
            if target_line.strip() in line:
                file.write(new_line + '\n')
            else:
                file.write(line)

old_file = 'EXO-RunIII2024Summer24wmLHEGS-00259_1_cfg.py'
target_line = 'args'
import glob

files = glob.glob("/eos/uscms/store/user/kkwok/llp/gridpack/run3/*")
for f in files:
    gridpack = f.replace("/eos/uscms","root://cmsxrootd.fnal.gov/")
    m = f.split('_')[3]
    ctau = f.split('_')[5]
    decay = f.split('_')[1]
    print(gridpack, decay,m,ctau)
    new_line = f'   args = cms.vstring(\'{gridpack}\'),'
    new_file = f'EXO-RunIII2024Summer24_hnl_{decay}_mN_{m}_ctau_{ctau}.py'
    replace_line_in_file(old_file,new_file, target_line, new_line)


