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

# Example usage
old_file = 'hnl_genfragment.py'
target_line = 'args'
for m in ['1','1p5','2','4','7']:
    for ctau in [10,100,1000,10000]:
        gridpack = f"root://cmsxrootd.fnal.gov//store/user/kkwok/llp/gridpack/run3/HNL_tau_mN_{m}_ctau_{ctau}_13p6TeV_slc7_amd64_gcc10_CMSSW_12_4_8_tarball.tar.xz"
        new_line = f'   args = cms.vstring(\'{gridpack}\'),'
        new_file = f'hnl_tau_mN_{m}_ctau_{ctau}_13p6TeV_fragment.py'
        replace_line_in_file(old_file,new_file, target_line, new_line)
