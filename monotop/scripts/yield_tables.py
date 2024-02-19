import re
import ROOT


#ROOT.gROOT.SetBatch(ROOT.kTRUE)

TEST_FILE = "/nfs/dust/cms/user/mwassmer/MonoTop/NanoAOD/Fit/monotop-datacards-v2/combined_cards/v29_hadronic/all_years/Mphi_1000_Mchi_150/fits/fitDiagnosticsdatacard_hadronic_all_years_Mphi_1000_Mchi_150_bkg_asimov_toy_postfituncs.root"
BIN_KEY_PATTERN = r"^YEAR_(\d((preVFP)|(postVFP))?)_((PASS)|(FAIL))_(\w)_(.*)_bin_(\d+)$"


f = ROOT.TFile.Open(TEST_FILE, "READ")
keys = [str(k) for k in f.GetListOfKeys()]


for key in f.GetListOfKeys():
    if re.match()


processes = [
    "DYJetsToLL",
    "G1Jet_Ptbinned",
    "ZJetsToNuNu",
    "diboson",
    "qcd",
    "SingleTop",
    "WJetsToLNu_stitched",
    "ttbar",
]



class Region():

    def __init__(self, name):
        self.name = name
