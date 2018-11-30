#!/bin/env python

import plottery_wrapper as p
import ROOT as r
import sys
from errors import E

#______________________________________________________________________________
def frac_syst_hists(h, error, errordn=None):
    # The error, and errordn can take many format

    # If the error provided is a list
    if isinstance(error, list):

        # Checking various input
        if len(error) != h.GetNbinsX():
            raise ValueError("provided list of error list, but the list don't match the number of bins in the histogram.")
        if errordn:
            if not isinstance(errordn, list):
                raise ValueError("provided list of errordn but the type of errordn is not list, while error is.")
            if len(error) != len(errordn):
                raise ValueError("provided list of errordn but the length do not match error.")

        # loop over the fractional errors and set the histogram bin content based on it
        hup = h.Clone()
        for i in xrange(len(error)):
            bc = hup.GetBinContent(i+1)
            nb = bc + error[i] * bc
            hup.SetBinContent(i+1, nb if nb > 0 else 1e-6)

        # loop over the fractional errordn (or error if errordn wasn't provided) and set the histogram bin content based on it
        hdn = h.Clone()
        for i in xrange(len(errordn if errordn else error)):
            bc = hdn.GetBinContent(i+1)
            nb = bc - error[i] * bc
            hdn.SetBinContent(i+1, nb if nb > 0 else 1e-6)

        # Return systematic histograms
        return [hup, hdn]

#______________________________________________________________________________
def apply_sf(h, sfs, file_name, hist_name):
    labels = h.GetXaxis().GetLabels()
    if labels:
        h.GetXaxis().SetRange(1, h.GetXaxis().GetNbins())
        h.GetXaxis().SetCanExtend(False)
    for key in sfs:
        if key in file_name:
            for rptn in sfs[key]:
                if rptn in hist_name:
                    for i in xrange(0, h.GetNbinsX()+2):
                        bc, be = h.GetBinContent(i), h.GetBinError(i)
                        nb = E(bc, be) * E(sfs[key][rptn][0], sfs[key][rptn][1])
                        h.SetBinContent(i, nb.val)
                        #h.SetBinError(i, nb.err)

#______________________________________________________________________________
def get_histograms(list_of_file_names, hist_name, sfs={}):
    hists = []
    for file_name in list_of_file_names:
        f = r.TFile(file_name)
        try:
            h = f.Get(hist_name).Clone(hist_name)
            h.SetDirectory(0)
            apply_sf(h, sfs, file_name, hist_name.split("_")[0])
            hists.append(h)
        except:
            print "Could not find", hist_name, "in", file_name
        f.Close()
    return hists

#______________________________________________________________________________
def get_list_of_histograms(list_of_file_names, hist_names, sfs={}):
    hists = []
    for file_name in list_of_file_names:
        f = r.TFile(file_name)
        for hist_name in hist_names:
            try:
                h = f.Get(hist_name).Clone(hist_name)
                h.SetDirectory(0)
                apply_sf(h, sfs, file_name, hist_name.split("_")[0])
                hists.append(h)
            except:
                print "Could not find", hist_name, "in", file_name
        #print file_name
        f.Close()
    return hists

#______________________________________________________________________________
def get_yield_histogram(list_of_file_names, regions, hsuffix="_cutflow", sfs={}):
    final_h = r.TH1F("yields", "", len(regions), 0, len(regions))
    yields = []
    for i in xrange(len(regions)):
        yields.append(E(0, 0))
    for file_name in list_of_file_names:
        f = r.TFile(file_name)
        for index, region in enumerate(regions):
            try:
                prefix = region.split("(")[0]
                h = f.Get(prefix + hsuffix)
                apply_sf(h, sfs, file_name, prefix)
                binoffset = int(region.split("(")[1].split(")")[0]) if len(region.split("(")) > 1 else h.GetNbinsX()
                bc = h.GetBinContent(binoffset)
                be = h.GetBinError(binoffset)
                yields[index] += E(bc, be)
            except:
                print "Could not find", region+hsuffix, "in", file_name
        #print file_name
        f.Close()
    for i in xrange(len(regions)):
        final_h.SetBinContent(i+1, yields[i].val)
        final_h.SetBinError(i+1, yields[i].err)
    return final_h

#______________________________________________________________________________
def get_summed_histogram(list_of_file_names, hist_names, sfs={}):
    if isinstance(hist_names, list):
        hists = []
        #for hist_name in hist_names:
        #    hists.extend(get_histograms(list_of_file_names, hist_name))
        hists.extend(get_list_of_histograms(list_of_file_names, hist_names, sfs))
        hist_name = hist_names[0] + "_plus_etc"
    else:
        hists = get_histograms(list_of_file_names, hist_names, sfs)
        hist_name = hist_names
    if len(hists) == 0:
        print "error no histograms are found query=", list_of_file_names, hist_names
        raise ValueError("No histograms are found with the query")
        sys.exit()
    rtn_hist = hists[0].Clone(hist_name)
    rtn_hist.Reset()
    rtn_hist.SetDirectory(0)
    for h in hists:
        rtn_hist.Add(h)
    return rtn_hist

#______________________________________________________________________________
def get_yield_from_cutflow_histogram(list_of_file_names, reg_name):
    hist = get_summed_histograms(list_of_file_names, reg_name + "_cutflow")
    return hist.GetBinContent(hist.GetNbinsX())

#______________________________________________________________________________
def get_shape_reweighting_histogram(numerator, denominator):
    ratio = numerator.Clone("ratio")
    ratio.Divide(denominator)
    if numerator.Integral() == 0:
        raise ValueError("numerator histogram has integral of zero")
    scale = denominator.Integral() / numerator.Integral() 
    ratio.Scale(scale)
    return ratio

#______________________________________________________________________________
def get_sf(h_proc, h_data, h_sub):

    if isinstance(h_proc, list):
        if len(h_proc) == 0:
            raise ValueError("provided histogram list is null")
        h_proc_tmp = h_proc[0].Clone()
        h_proc_tmp.Reset()
        for h in h_proc:
            h_proc_tmp.Add(h)
        h_proc = h_proc_tmp

    if isinstance(h_sub, list):
        if len(h_sub) == 0:
            h_sub = None
        else:
            h_sub_tmp = h_sub[0].Clone()
            h_sub_tmp.Reset()
            for h in h_sub:
                h_sub_tmp.Add(h)
            h_sub = h_sub_tmp

    if isinstance(h_data, list):
        if len(h_data) == 0:
            raise ValueError("provided histogram list is null")
        h_data_tmp = h_data[0].Clone()
        h_data_tmp.Reset()
        for h in h_data:
            h_data_tmp.Add(h)
        h_data = h_data_tmp

    h_ddproc = h_data.Clone()
    if h_sub:
        h_ddproc.Add(h_sub, -1)
    h_ddproc.Divide(h_proc)

    return h_ddproc

#______________________________________________________________________________
def submit_metis(job_tag, samples_map, sample_list=[], arguments_map="", exec_script="metis.sh", tar_files=[], hadoop_dirname="testjobs", files_per_output=1, globber="*.root"):

    import time
    import json
    import metis

    from time import sleep

    from metis.Sample import DirectorySample
    from metis.CondorTask import CondorTask

    from metis.StatsParser import StatsParser

    import os
    import glob
    import subprocess


    # file/dir paths
    main_dir             = os.getcwd()
    metis_path           = os.path.dirname(os.path.dirname(metis.__file__))
    tar_path             = os.path.join(metis_path, "package.tar")
    tar_gz_path          = tar_path + ".gz"
    metis_dashboard_path = os.path.join(metis_path, "dashboard")
    exec_path            = os.path.join(main_dir, exec_script)
    hadoop_path          = "metis/{}/{}".format(hadoop_dirname, job_tag) # The output goes to /hadoop/cms/store/user/$USER/"hadoop_path"

    # Create tarball
    os.chdir(main_dir)
    print os.getcwd()
    print "tar -chzf {} {}".format(tar_gz_path, " ".join(tar_files))
    os.system("tar -chzf {} {}".format(tar_gz_path, " ".join(tar_files)))

    # Change directory to metis
    os.chdir(metis_path)

    total_summary = {}

    # if no sample_list is provided then we form it via the keys of the samples_map
    if len(sample_list) == 0:
        for key in samples_map:
            sample_list.append(key)

    samples_to_run = []
    for key in sample_list:
        samples_to_run.append(
                DirectorySample(
                    dataset=key,
                    location=samples_map[key],
                    globber=globber,
                    )
                )

    # Loop over datasets to submit
    while True:

        all_tasks_complete = True

        #for sample in sorted(samples):
        for sample in samples_to_run:

            # define the task
            maker_task = CondorTask(
                    sample               = sample,
                    tag                  = job_tag,
                    arguments            = arguments_map[sample.get_datasetname()] if arguments_map else "",
                    executable           = exec_path,
                    tarfile              = tar_gz_path,
                    special_dir          = hadoop_path,
                    output_name          = "output.root",
                    files_per_output     = files_per_output,
                    condor_submit_params = {"sites" : "T2_US_UCSD,LOCAL"},
                    open_dataset         = False,
                    flush                = True,
                    #no_load_from_backup  = True,
                    )


            # process the job (either submits, checks for resubmit, or finishes etc.)
            maker_task.process()

            # save some information for the dashboard
            total_summary[maker_task.get_sample().get_datasetname()] = maker_task.get_task_summary()

            # Aggregate whether all tasks are complete
            all_tasks_complete = all_tasks_complete and maker_task.complete()


        # parse the total summary and write out the dashboard
        StatsParser(data=total_summary, webdir=metis_dashboard_path).do()

        # Print msummary table so I don't have to load up website
        os.system("msummary -r | tee summary.txt")
        os.system("chmod -R 755 {}".format(metis_dashboard_path))
        os.system("chmod 644 {}/images/*".format(metis_dashboard_path))

        # If all done exit the loop
        if all_tasks_complete:
            print ""
            print "Job={} finished".format(job_tag)
            print ""
            break

        # Neat trick to not exit the script for force updating
        print 'Press Ctrl-C to force update, otherwise will sleep for 300 seconds'
        try:
            for i in range(0,60):
                sleep(1) # could use a backward counter to be preeety :)
        except KeyboardInterrupt:
            raw_input("Press Enter to force update, or Ctrl-C to quit.")
            print "Force updating..."

#______________________________________________________________________________
def write_shape_fit_datacard(sig=None, bgs=[], data=None, datacard_filename="datacard.txt", region_name="SR", hist_filename="hist.root", systs={}):

    # Checking arguments
    if not sig:
        print "Error: No signal histogram provided for the statistics datacard writing."
        return

    if len(bgs) == 0:
        print "Error: No background histograms provided for the statistics datacard writing."
        return

    if not data:
        print "Warning: No data histogram provided for the statistics datacard writing."
        print "data will be set to total bkg expectation. (of course rounded."
        fakedata = bgs[0].Clone()
        fakedata.Reset()
        for b in bgs:
            fakedata.Add(b)
        for i in xrange(1,fakedata.GetNbinsX()+2):
            b = fakedata.GetBinContent(i)
            fakedata.SetBinContent(i, int(b) if b > 0 else 0)
        data = fakedata


    """
    imax 1 number of bins
    jmax * number of processes
    kmax * number of nuisance parameters
    ----------------------------------------------------------------------------------------------------------------------------------
    shapes * * statinputs/hist_sm.root $PROCESS $PROCESS_$SYSTEMATIC
    ----------------------------------------------------------------------------------------------------------------------------------
    bin          SR
    observation  48.0
    ----------------------------------------------------------------------------------------------------------------------------------
    bin                                     SR           SR           SR           SR           SR           SR           SR           SR
    process                                 0            1            2            3            4            5            6            7
    process                                 www          fake         photon       lostlep      qflip        prompt       ttw          vbsww
    rate                                    11.691       7.186        2.654        31.690       1.654        1.190        3.470        7.837
    ----------------------------------------------------------------------------------------------------------------------------------
    JEC                     shape           1            -            1            -            -            1            1            1
    LepSF                   shape           1            -            1            -            -            1            1            1
    TrigSF                  shape           1            -            1            -            -            1            1            1
    BTagHF                  shape           1            -            1            -            -            1            1            1
    BTagLF                  shape           1            -            1            -            -            1            1            1
    Pileup                  shape           1            -            1            -            -            1            1            1
    FakeRateEl              shape           -            1            -            -            -            -            -            -
    FakeRateMu              shape           -            1            -            -            -            -            -            -
    FakeClosureEl           shape           -            1            -            -            -            -            -            -
    FakeClosureMu           shape           -            1            -            -            -            -            -            -
    LostLepSyst             shape           -            -            -            1            -            -            -            -
    MjjModeling             shape           -            -            -            1            -            -            -            -
    MllSSModeling           shape           -            -            -            1            -            -            -            -
    Mll3lModeling           shape           -            -            -            1            -            -            -            -
    SigXSec                 lnN             1.06         -            -            -            -            -            -            -
    LumSyst                 lnN             1.025        -            1.025        -            1.025        1.025        1.025        1.025
    vbsww_xsec              lnN             -            -            -            -            -            -            -            1.20
    vbsww_validation        lnN             -            -            -            -            -            -            -            1.22
    ttw_xsec                lnN             -            -            -            -            -            -            1.20         -
    ttw_validation          lnN             -            -            -            -            -            -            1.18         -
    photon_syst             lnN             -            -            1.50         -            -            -            -            -
    qflip_syst              lnN             -            -            -            -            1.50         -            -            -
    www_stat_in_ee          shape           1            -            -            -            -            -            -            -
    www_stat_in_em          shape           1            -            -            -            -            -            -            -
    www_stat_in_mm          shape           1            -            -            -            -            -            -            -
    www_stat_out_ee         shape           1            -            -            -            -            -            -            -
    """

    # Check that the histograms have no zero or negative yields
    for x in ([sig] + bgs):
        for i in xrange(0, x.GetNbinsX()+2):
            bc = x.GetBinContent(i)
            if bc <= 0:
                x.SetBinContent(i, 0)
                x.SetBinError(i, 0)

    # Processes that will be written out in each column
    hists = [sig] + bgs
    hists_names = [ x.GetTitle() for x in hists ]
    hists_rates = [ x.Integral() for x in hists ]

    # Create output file
    f = open(datacard_filename, "w")

    # Write the header
    f.write("""imax 1 number of bins
jmax * number of processes
kmax * number of nuisance parameters
----------------------------------------------------------------------------------------------------------------------------------
shapes * * {} $PROCESS $PROCESS_$SYSTEMATIC
----------------------------------------------------------------------------------------------------------------------------------
""".format(hist_filename))

    # Write the total observed data number
    f.write("""bin          {}
observation  {}
----------------------------------------------------------------------------------------------------------------------------------
""".format(region_name, data.Integral()))

    # Write the column header with region name
    f.write("""bin                                     {}
""".format("".join(["{:13s}".format(region_name)]*(len(hists)))))

    # Write the index of processes
    f.write("""process                                 {}
""".format("".join(["{:<13d}".format(i) for i in xrange(len(hists))])))

    # Write the names of processes
    f.write("""process                                 {}
""".format("".join(["{:13s}".format(i) for i in hists_names]))) # TH1::SetTitle is set to the short name of a process not TH1::SetName

    # Write the rates of processes
    f.write("""rate                                    {}
----------------------------------------------------------------------------------------------------------------------------------
""".format("".join(["{:<13f}".format(i) for i in hists_rates])))

    # Write the statistical uncertainties (the naming convention is {proc}_stat_{ibin})
    for index, x in enumerate(hists):
        for i in xrange(1, x.GetNbinsX() + 1):
            f.write("""{:24s}shape           {}
""".format(x.GetTitle()+"_stat_"+str(i), "".join(["{:13s}".format("1" if index == j else "-") for j in xrange(len(hists))])))

    # Write the histograms to the hist file
    tf = r.TFile(hist_filename, "recreate")
    tf.cd()

    # Write the nominal rate histograms
    for h in hists:
        h.SetName(h.GetTitle()) # The title was set to the short names of the process
        h.SetTitle("rates histogram") # Just to give some description
        h.Write()

    # Write the statistcal uncertainty histograms
    for h in hists:
        for i in xrange(1, x.GetNbinsX() + 1):
            for var in ["Up", "Down"]:
                name = h.GetName() # TH1::SetName() is now the process name
                stat_error_hist_name = name + "_" + name + "_stat_" + str(i) + var # The TH1 naming convention is defined in datacard.txt line of "shapes * * .... "
                eh = h.Clone(stat_error_hist_name)
                nc = eh.GetBinContent(i + 1) + eh.GetBinError(i + 1) if var == "Up" else eh.GetBinContent(i + 1) - eh.GetBinError(i + 1)
                eh.SetBinContent(i + 1, nc if nc > 0 else 1e-6)
                eh.Write()

    # Treat the systematic histograms
    for proc in systs:
        for syst in systs[proc]:

            # Write the line that declares the systematic
            f.write("""{:24s}shape           {}
""".format(proc + "_" + syst, "".join(["{:13s}".format("1" if proc == iproc else "-") for iproc in hists_names])))

            # Then write the histograms to the output file
            for index, h in enumerate(systs[proc][syst]): # There are two histograms to loop over and they are up and down variations
                histname = proc + "_" + proc + "_" + syst + ("Up" if index == 0 else "Down")
                h.SetName(histname)
                h.SetTitle(syst)
                h.Write()

    # Write the data histogram
    data.SetName("data_obs") # HiggsCombineTool wants data histograms to set to exactly this name
    data.SetTitle("observed data")
    data.Write()
    tf.Close()
    os.chdir(main_dir)

if __name__ == "__main__":
    main()

#eof
